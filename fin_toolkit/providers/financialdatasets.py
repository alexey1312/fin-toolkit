"""Financial Datasets (financialdatasets.ai) data provider."""

from __future__ import annotations

from typing import Any

import httpx

from fin_toolkit.exceptions import ProviderUnavailableError, TickerNotFoundError
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData, PricePoint

_BASE_URL = "https://api.financialdatasets.ai"

# Fields to skip when building normalized dicts (metadata, not financial data).
_SKIP_FIELDS = {
    "ticker", "report_period", "period", "fiscal_year", "fiscal_quarter", "fiscal_period",
    "cik", "currency", "accession_number", "filing_url",
}

# Rename API fields to match our normalized keys (where they differ).
_FIELD_RENAME: dict[str, str] = {
    "capital_expenditure": "capital_expenditures",
    "net_cash_flow_from_operations": "operating_cash_flow",
    "net_cash_flow_from_investing": "investing_cash_flow",
    "net_cash_flow_from_financing": "financing_cash_flow",
    "shareholders_equity": "total_equity",
    "stockholders_equity": "total_equity",
}


class FinancialDatasetsProvider:
    """Data provider using the Financial Datasets REST API (US equities)."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {"X-API-KEY": self._api_key}

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        """Fetch historical EOD prices."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(
                f"{_BASE_URL}/prices",
                params={"ticker": ticker, "interval": "day", "start_date": start, "end_date": end},
                headers=self._headers(),
            )
            if resp.status_code != 200:
                raise ProviderUnavailableError("financialdatasets", f"HTTP {resp.status_code}")

        rows: list[dict[str, Any]] = resp.json().get("prices", [])
        if not rows:
            raise TickerNotFoundError(ticker, provider="financialdatasets")

        prices = [
            PricePoint(
                date=r.get("date") or r["time"][:10],
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
                volume=int(r["volume"]),
            )
            for r in rows
        ]
        return PriceData(ticker=ticker, period=f"{start}/{end}", prices=prices)

    async def get_financials(self, ticker: str) -> FinancialStatements:
        """Fetch latest annual financial statements (income, balance, cashflow)."""
        params: dict[str, str | int] = {"ticker": ticker, "period": "annual", "limit": 1}

        async with httpx.AsyncClient(follow_redirects=True) as client:
            inc_resp = await client.get(
                f"{_BASE_URL}/financials/income-statements",
                params=params,
                headers=self._headers(),
            )
            bs_resp = await client.get(
                f"{_BASE_URL}/financials/balance-sheets",
                params=params,
                headers=self._headers(),
            )
            cf_resp = await client.get(
                f"{_BASE_URL}/financials/cash-flow-statements",
                params=params,
                headers=self._headers(),
            )

        income = self._extract_statement(inc_resp, "income_statements")
        balance = self._extract_statement(bs_resp, "balance_sheets")
        cashflow = self._extract_statement(cf_resp, "cash_flow_statements")

        if income is None and balance is None and cashflow is None:
            raise TickerNotFoundError(ticker, provider="financialdatasets")

        return FinancialStatements(
            ticker=ticker,
            income_statement=income,
            balance_sheet=balance,
            cash_flow=cashflow,
        )

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        """Fetch current financial metrics snapshot."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(
                f"{_BASE_URL}/financial-metrics/snapshot",
                params={"ticker": ticker},
                headers=self._headers(),
            )
            if resp.status_code != 200:
                raise ProviderUnavailableError("financialdatasets", f"HTTP {resp.status_code}")

        m: dict[str, Any] = resp.json().get("snapshot", {})
        if not m:
            raise TickerNotFoundError(ticker, provider="financialdatasets")

        return KeyMetrics(
            ticker=ticker,
            pe_ratio=m.get("price_to_earnings_ratio"),
            pb_ratio=m.get("price_to_book_ratio"),
            market_cap=m.get("market_cap"),
            dividend_yield=m.get("payout_ratio"),
            roe=m.get("return_on_equity"),
            roa=m.get("return_on_assets"),
            debt_to_equity=m.get("debt_to_equity"),
            enterprise_value=m.get("enterprise_value"),
        )

    @staticmethod
    def _extract_statement(resp: httpx.Response, key: str) -> dict[str, object] | None:
        """Extract and normalize the first statement from an API response."""
        if resp.status_code != 200:
            return None
        rows = resp.json().get(key, [])
        if not rows:
            return None

        raw = rows[0]
        result: dict[str, object] = {}
        for field, value in raw.items():
            if field in _SKIP_FIELDS or value is None:
                continue
            normalized = _FIELD_RENAME.get(field, field)
            result[normalized] = value
        return result
