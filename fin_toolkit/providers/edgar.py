"""SEC EDGAR data provider via edgartools."""

from __future__ import annotations

import asyncio
from typing import Any

from fin_toolkit.exceptions import ProviderUnavailableError, TickerNotFoundError
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData


class EdgarProvider:
    """US financial statements from SEC EDGAR via edgartools."""

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        """EDGAR doesn't have price data."""
        raise ProviderUnavailableError("edgar", "No price data in EDGAR")

    async def get_financials(self, ticker: str) -> FinancialStatements:
        """Fetch 10-K XBRL data → income/balance/cashflow."""
        try:
            data = await asyncio.to_thread(self._fetch_financials, ticker)
        except TickerNotFoundError:
            raise
        except Exception as exc:
            raise ProviderUnavailableError("edgar", str(exc)) from exc
        return data

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        """Derive metrics from EDGAR financials."""
        fin = await self.get_financials(ticker)
        inc = fin.income_statement or {}
        bs = fin.balance_sheet or {}

        net_income = _safe_float(inc.get("net_income"))
        total_equity = _safe_float(bs.get("total_equity"))
        total_assets = _safe_float(bs.get("total_assets"))

        roe: float | None = None
        if net_income is not None and total_equity is not None and total_equity > 0:
            roe = net_income / total_equity

        roa: float | None = None
        if net_income is not None and total_assets is not None and total_assets > 0:
            roa = net_income / total_assets

        return KeyMetrics(
            ticker=ticker,
            pe_ratio=None,
            pb_ratio=None,
            market_cap=None,
            dividend_yield=None,
            roe=roe,
            roa=roa,
            debt_to_equity=None,
        )

    @staticmethod
    def _fetch_financials(ticker: str) -> FinancialStatements:
        """Synchronous EDGAR fetch (runs in thread)."""
        try:
            from edgar import Company  # type: ignore[attr-defined]
        except ImportError as exc:
            raise ProviderUnavailableError(
                "edgar", "edgartools not installed"
            ) from exc

        try:
            company = Company(ticker)
        except Exception as exc:
            raise TickerNotFoundError(ticker, provider="edgar") from exc

        filings = company.get_filings(form="10-K")
        if not filings:
            raise TickerNotFoundError(ticker, provider="edgar")

        latest = filings.latest(1)
        if not latest:
            raise TickerNotFoundError(ticker, provider="edgar")

        # latest() may return a single filing or a list
        filing = latest[0] if isinstance(latest, (list, tuple)) else latest

        income: dict[str, object] = {}
        balance: dict[str, object] = {}
        cash_flow: dict[str, object] = {}

        try:
            xbrl = filing.xbrl()
            if xbrl is not None:
                income = _extract_income(xbrl)
                balance = _extract_balance(xbrl)
                cash_flow = _extract_cashflow(xbrl)
        except Exception:
            pass

        return FinancialStatements(
            ticker=ticker,
            income_statement=income or None,
            balance_sheet=balance or None,
            cash_flow=cash_flow or None,
        )


# ---------------------------------------------------------------------------
# XBRL field extraction
# ---------------------------------------------------------------------------

_INCOME_FIELDS: dict[str, str] = {
    "Revenues": "revenue",
    "RevenueFromContractWithCustomerExcludingAssessedTax": "revenue",
    "NetIncomeLoss": "net_income",
    "GrossProfit": "gross_profit",
    "OperatingIncomeLoss": "operating_income",
    "InterestExpense": "interest_expense",
    "EarningsBeforeInterestAndTaxes": "ebit",
}

_BALANCE_FIELDS: dict[str, str] = {
    "Assets": "total_assets",
    "StockholdersEquity": "total_equity",
    "LongTermDebt": "total_debt",
    "AssetsCurrent": "current_assets",
    "LiabilitiesCurrent": "current_liabilities",
}

_CASHFLOW_FIELDS: dict[str, str] = {
    "NetCashProvidedByUsedInOperatingActivities": "operating_cash_flow",
    "PaymentsToAcquirePropertyPlantAndEquipment": "capital_expenditures",
}


def _extract_facts(xbrl: Any, field_map: dict[str, str]) -> dict[str, object]:
    """Extract values from XBRL data using a field mapping."""
    result: dict[str, object] = {}
    for xbrl_name, our_name in field_map.items():
        if our_name in result:
            continue
        try:
            val = getattr(xbrl, xbrl_name, None)
            if val is not None:
                result[our_name] = float(val)
        except (TypeError, ValueError, AttributeError):
            pass
    return result


def _extract_income(xbrl: Any) -> dict[str, object]:
    return _extract_facts(xbrl, _INCOME_FIELDS)


def _extract_balance(xbrl: Any) -> dict[str, object]:
    return _extract_facts(xbrl, _BALANCE_FIELDS)


def _extract_cashflow(xbrl: Any) -> dict[str, object]:
    return _extract_facts(xbrl, _CASHFLOW_FIELDS)


def _safe_float(val: object) -> float | None:
    if val is None:
        return None
    try:
        return float(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
