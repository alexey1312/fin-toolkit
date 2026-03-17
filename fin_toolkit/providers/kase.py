"""KASE (Kazakhstan Stock Exchange) data provider via kase.kz JSON API."""

from __future__ import annotations

import time
from typing import Any

import httpx

from fin_toolkit.exceptions import ProviderUnavailableError, TickerNotFoundError
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData, PricePoint

_BASE_URL = "https://kase.kz/api"

# Map KASE share_data fields → KeyMetrics fields.
_SHARE_FIELD_MAP: dict[str, str] = {
    "capit": "market_cap",
    "price": "current_price",
    "pe": "pe_ratio",
    "pb": "pb_ratio",
    "dividend_yield": "dividend_yield",
}

# Yahoo Finance suffixes to try for KASE tickers.
_YAHOO_SUFFIXES = (".ME", ".IL", "")

# Only include actively traded local share categories.
_LOCAL_SHARE_CATEGORIES = frozenset({
    "main_shares_premium",
    "main_shares_standard",
    "alternative_shares",
})


def _is_local_share(security: dict[str, Any]) -> bool:
    """Keep only actively traded local shares (exclude KASE Global, delisted, etc.)."""
    ticker_data = security.get("ticker")
    if isinstance(ticker_data, dict):
        category = ticker_data.get("ticker_category", "")
        return category in _LOCAL_SHARE_CATEGORIES
    return False


def _safe_float(val: Any) -> float | None:
    """Safely convert to float or return None."""
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _unwrap(data: Any) -> dict[str, Any]:
    """Unwrap KASE API response — may be a dict or a single-element list."""
    if isinstance(data, list):
        return dict(data[0]) if data else {}
    return dict(data)


class _KASEClient:
    """Thin async HTTP client for kase.kz/api/* endpoints."""

    def __init__(self, base_url: str = _BASE_URL) -> None:
        self._base_url = base_url

    async def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        """Execute GET request, raise on HTTP errors."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(f"{self._base_url}{path}", params=params)
            if resp.status_code == 404:
                return None
            if resp.status_code != 200:
                raise ProviderUnavailableError("kase", f"HTTP {resp.status_code}")
            return resp.json()

    async def list_securities(self, sec_type: str | None = None) -> list[dict[str, Any]]:
        """List all securities, optionally filtered by type (share/bond/gsec)."""
        params = {"sec_type": sec_type} if sec_type else None
        data = await self._get("/instruments/securities", params=params)
        if not data:
            return []
        return data if isinstance(data, list) else []

    async def get_security(self, code: str) -> dict[str, Any] | None:
        """Get single security metadata by code."""
        data = await self._get("/instruments/securities", params={"code": code})
        if not data:
            return None
        result = _unwrap(data)
        return result or None

    async def get_share_data(self, ticker: str) -> dict[str, Any]:
        """Get realtime share data (price, bid/offer, capit, trand, etc.)."""
        data = await self._get(f"/instruments/shares/{ticker}")
        if not data:
            raise TickerNotFoundError(ticker, provider="kase")
        return _unwrap(data)

    async def get_trade_info(self, ticker: str) -> dict[str, Any]:
        """Get daily trade info (OHLCV for current day)."""
        data = await self._get(f"/instruments/trade-info/{ticker}")
        if not data:
            raise TickerNotFoundError(ticker, provider="kase")
        return _unwrap(data)

    async def get_last_deals(self, ticker: str) -> list[dict[str, Any]]:
        """Get last 10 deals for a ticker."""
        data = await self._get(f"/instruments/last-deals/{ticker}")
        if not data:
            return []
        return data if isinstance(data, list) else []

    async def get_dividends(self, ticker: str) -> list[dict[str, Any]]:
        """Get historical dividends."""
        data = await self._get(f"/instruments/dividends/{ticker}")
        if not data:
            return []
        return data if isinstance(data, list) else []

    async def get_characteristics(self, ticker: str) -> dict[str, Any] | None:
        """Get listing characteristics."""
        data = await self._get(f"/instruments/characteristics/{ticker}")
        return _unwrap(data) if data else None

    async def search(self, query: str) -> dict[str, Any]:
        """Search issuers, securities, and members."""
        data = await self._get("/search", params={"query": query})
        return data if data else {}

    async def get_calendar(self) -> list[dict[str, Any]]:
        """Get trading calendar."""
        data = await self._get("/calendar")
        if not data:
            return []
        return data if isinstance(data, list) else []


class KASEProvider:
    """Data provider for Kazakhstan Stock Exchange via JSON API.

    Uses _KASEClient for realtime data and optional YahooFinanceProvider
    for historical OHLC prices. Tries multiple Yahoo suffixes (.ME, .IL, bare)
    to find the correct listing.
    """

    _CACHE_TTL = 86400  # 24 hours

    def __init__(self, yahoo: Any = None) -> None:
        self._client = _KASEClient()
        self._yahoo = yahoo
        self._tickers_cache: list[str] | None = None
        self._tickers_cache_time: float = 0.0
        self._yahoo_suffix_cache: dict[str, str] = {}

    async def list_tickers(self) -> list[str]:
        """List all KASE share tickers, cached for 24h."""
        if self._tickers_cache is not None and (
            time.monotonic() - self._tickers_cache_time < self._CACHE_TTL
        ):
            return self._tickers_cache
        securities = await self._client.list_securities(sec_type="share")
        self._tickers_cache = [
            s["code"]
            for s in securities
            if s.get("code")
            and _is_local_share(s)
        ]
        self._tickers_cache_time = time.monotonic()
        return self._tickers_cache

    async def _resolve_yahoo_ticker(self, ticker: str) -> str:
        """Find working Yahoo ticker by trying suffixes (.ME, .IL, bare)."""
        if ticker in self._yahoo_suffix_cache:
            suffix = self._yahoo_suffix_cache[ticker]
            return f"{ticker}{suffix}" if suffix else ticker

        if self._yahoo is None:
            raise ProviderUnavailableError(
                "kase", "Yahoo provider required for price resolution",
            )

        from datetime import datetime, timedelta

        probe_end = datetime.now().strftime("%Y-%m-%d")
        probe_start = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

        for suffix in _YAHOO_SUFFIXES:
            candidate = f"{ticker}{suffix}" if suffix else ticker
            try:
                await self._yahoo.get_prices(candidate, probe_start, probe_end)
                self._yahoo_suffix_cache[ticker] = suffix
                return candidate
            except (TickerNotFoundError, ProviderUnavailableError):
                continue

        raise ProviderUnavailableError("kase", f"No Yahoo ticker for {ticker}")

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        """Fetch current-day prices from KASE API in KZT.

        KASE API provides only current-day OHLCV, not deep history.
        For historical GDR prices in USD, use Yahoo provider directly.

        API fields: high, low, price (last/close), average_price,
        date0 (timestamp), volume, deals_count. No open price available.
        """
        data = await self._client.get_trade_info(ticker)

        # Extract date from date0 ("2026-03-17 17:30:38") or period
        raw_date = str(data.get("date0", data.get("period", "")))[:10]

        # KASE API has no open price — use average_price as proxy
        price = _safe_float(data.get("price", 0.0))
        high = _safe_float(data.get("high", 0.0))
        low = _safe_float(data.get("low", 0.0))
        avg = _safe_float(data.get("average_price")) or price

        prices = [
            PricePoint(
                date=raw_date,
                open=avg or 0.0,
                high=high or 0.0,
                low=low or 0.0,
                close=price or 0.0,
                volume=int(data.get("volume", 0)),
            ),
        ]

        return PriceData(
            ticker=ticker,
            period=f"{start}/{end}",
            prices=prices,
            currency="KZT",
        )

    async def get_financials(self, ticker: str) -> FinancialStatements:
        """Fetch financials via Yahoo delegation; returns None fields if unavailable."""
        if self._yahoo is None:
            return FinancialStatements(
                ticker=ticker,
                income_statement=None,
                balance_sheet=None,
                cash_flow=None,
            )
        try:
            yahoo_ticker = await self._resolve_yahoo_ticker(ticker)
            result = await self._yahoo.get_financials(yahoo_ticker)
            return FinancialStatements(
                ticker=ticker,
                income_statement=result.income_statement,
                balance_sheet=result.balance_sheet,
                cash_flow=result.cash_flow,
                income_history=result.income_history,
                cash_flow_history=result.cash_flow_history,
            )
        except (TickerNotFoundError, ProviderUnavailableError):
            return FinancialStatements(
                ticker=ticker,
                income_statement=None,
                balance_sheet=None,
                cash_flow=None,
            )

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        """Fetch key metrics from KASE, enriched with Yahoo data when available."""
        data = await self._client.get_share_data(ticker)

        yahoo_metrics: KeyMetrics | None = None
        if self._yahoo:
            try:
                yahoo_ticker = await self._resolve_yahoo_ticker(ticker)
                yahoo_metrics = await self._yahoo.get_metrics(yahoo_ticker)
            except (TickerNotFoundError, ProviderUnavailableError):
                pass

        return KeyMetrics(
            ticker=ticker,
            # KASE primary
            market_cap=data.get("capit"),
            current_price=data.get("price"),
            pe_ratio=data.get("pe"),
            pb_ratio=data.get("pb"),
            dividend_yield=data.get("dividend_yield"),
            # Yahoo enrichment
            roe=yahoo_metrics.roe if yahoo_metrics else None,
            roa=yahoo_metrics.roa if yahoo_metrics else None,
            debt_to_equity=yahoo_metrics.debt_to_equity if yahoo_metrics else None,
            enterprise_value=yahoo_metrics.enterprise_value if yahoo_metrics else None,
            ev_ebitda=yahoo_metrics.ev_ebitda if yahoo_metrics else None,
            fcf_yield=yahoo_metrics.fcf_yield if yahoo_metrics else None,
            shares_outstanding=yahoo_metrics.shares_outstanding if yahoo_metrics else None,
        )
