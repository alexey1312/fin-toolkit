"""KASE (Kazakhstan Stock Exchange) data provider via kase.kz JSON API."""

from __future__ import annotations

from typing import Any

import httpx

from fin_toolkit.exceptions import ProviderUnavailableError, TickerNotFoundError
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData

_BASE_URL = "https://kase.kz/api"

# Map KASE share_data fields → KeyMetrics fields.
_SHARE_FIELD_MAP: dict[str, str] = {
    "capit": "market_cap",
    "price": "current_price",
    "pe": "pe_ratio",
    "pb": "pb_ratio",
    "dividend_yield": "dividend_yield",
}


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
        if isinstance(data, list):
            result: dict[str, Any] = data[0] if data else {}
            return result or None
        return dict(data)

    async def get_share_data(self, ticker: str) -> dict[str, Any]:
        """Get realtime share data (price, bid/offer, capit, trand, etc.)."""
        data = await self._get(f"/instruments/shares/{ticker}")
        if not data:
            raise TickerNotFoundError(ticker, provider="kase")
        return dict(data)

    async def get_trade_info(self, ticker: str) -> dict[str, Any]:
        """Get daily trade info (OHLCV for current day)."""
        data = await self._get(f"/instruments/trade-info/{ticker}")
        if not data:
            raise TickerNotFoundError(ticker, provider="kase")
        return dict(data)

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
        return dict(data) if data else None

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
    for historical OHLC prices (Kazakh tickers trade on MOEX as {ticker}.ME).
    """

    def __init__(self, yahoo: Any = None) -> None:
        self._client = _KASEClient()
        self._yahoo = yahoo

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        """Fetch historical prices via Yahoo Finance (.ME suffix)."""
        if self._yahoo is None:
            raise ProviderUnavailableError(
                "kase", "Historical prices require Yahoo provider (yahoo= parameter)",
            )
        moex_ticker = f"{ticker}.ME"
        result = await self._yahoo.get_prices(moex_ticker, start, end)
        return PriceData(ticker=ticker, period=result.period, prices=result.prices)

    async def get_financials(self, ticker: str) -> FinancialStatements:
        """KASE does not provide financial statements — returns None fields."""
        return FinancialStatements(
            ticker=ticker,
            income_statement=None,
            balance_sheet=None,
            cash_flow=None,
        )

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        """Fetch key metrics from KASE realtime share data."""
        data = await self._client.get_share_data(ticker)
        return KeyMetrics(
            ticker=ticker,
            market_cap=data.get("capit"),
            current_price=data.get("price"),
            pe_ratio=data.get("pe"),
            pb_ratio=data.get("pb"),
            dividend_yield=data.get("dividend_yield"),
            roe=None,
            roa=None,
            debt_to_equity=None,
        )
