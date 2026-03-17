"""StockAnalysis (stockanalysis.com) data provider — ratios for KASE tickers.

Parses the Svelte JSON payload embedded in the ratios page HTML.
All ratios are currency-consistent (stockanalysis converts financials
to trading currency before computing P/E, P/B, etc.).
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from fin_toolkit.exceptions import ProviderUnavailableError, TickerNotFoundError
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData

_BASE_URL = "https://stockanalysis.com/quote/kase"
_HEADERS = {"User-Agent": "Mozilla/5.0 (fin-toolkit)"}

# Regex to extract the financialData object from Svelte payload.
_FINANCIAL_DATA_RE = re.compile(
    r"financialData:\{([^}]+(?:\{[^}]*\}[^}]*)*)\}",
)

# Fields we care about — maps Svelte key → (array regex, index 0 = TTM).
_RATIO_FIELDS = (
    "pe", "pb", "roe", "roa", "roic", "debtequity",
    "evebitda", "currentratio", "fcfyield", "dividendyield",
    "marketcap", "ev", "evrevenue",
)


def _extract_array(content: str, key: str) -> list[Any]:
    """Extract a JS array value for a given key from the financialData block."""
    pattern = re.compile(rf"(?:^|,){key}:\[([^\]]*)\]")
    match = pattern.search(content)
    if not match:
        return []
    raw = match.group(1)
    if not raw.strip():
        return []
    values: list[Any] = []
    for item in raw.split(","):
        item = item.strip()
        if item in ("null", "void 0", ""):
            values.append(None)
        elif item.startswith('"') or item.startswith("'"):
            values.append(item.strip("\"'"))
        else:
            try:
                values.append(float(item))
            except ValueError:
                values.append(None)
    return values


def _parse_ratios_payload(html: str) -> dict[str, Any] | None:
    """Parse Svelte financialData from HTML, return TTM values dict or None."""
    match = _FINANCIAL_DATA_RE.search(html)
    if not match:
        return None

    content = match.group(1)
    result: dict[str, Any] = {}
    for key in _RATIO_FIELDS:
        arr = _extract_array(content, key)
        result[key] = arr[0] if arr else None

    # If no data at all, return None
    if all(v is None for v in result.values()):
        return None

    return result


class StockAnalysisProvider:
    """Data provider using stockanalysis.com for KASE ticker ratios.

    Provides:
    - get_metrics: P/E, P/B, ROE, ROA, ROIC, D/E, EV/EBITDA, etc. from ratios page
    - get_prices: not supported (use KASE or Yahoo provider)
    - get_financials: not supported (use Yahoo or KASE provider)
    """

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        """Not supported — use KASE or Yahoo provider for prices."""
        raise ProviderUnavailableError(
            "stockanalysis", "No price data; use kase or yahoo provider",
        )

    async def get_financials(self, ticker: str) -> FinancialStatements:
        """Not supported — use Yahoo or KASE provider for financials."""
        raise ProviderUnavailableError(
            "stockanalysis", "No financials; use yahoo or kase provider",
        )

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        """Fetch key metrics from stockanalysis.com ratios page."""
        html = await self._fetch(ticker)
        data = _parse_ratios_payload(html)
        if data is None:
            raise TickerNotFoundError(ticker, provider="stockanalysis")

        return KeyMetrics(
            ticker=ticker,
            pe_ratio=data.get("pe"),
            pb_ratio=data.get("pb"),
            market_cap=data.get("marketcap"),
            dividend_yield=data.get("dividendyield"),
            roe=data.get("roe"),
            roa=data.get("roa"),
            debt_to_equity=data.get("debtequity"),
            enterprise_value=data.get("ev"),
            ev_ebitda=data.get("evebitda"),
            fcf_yield=data.get("fcfyield"),
        )

    async def _fetch(self, ticker: str) -> str:
        """Fetch the ratios page for a KASE ticker."""
        url = f"{_BASE_URL}/{ticker}/financials/ratios/"
        try:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=15.0,
            ) as client:
                resp = await client.get(url, headers=_HEADERS)
                resp.raise_for_status()
                return resp.text
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise TickerNotFoundError(ticker, provider="stockanalysis") from exc
            raise ProviderUnavailableError("stockanalysis", str(exc)) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("stockanalysis", str(exc)) from exc
