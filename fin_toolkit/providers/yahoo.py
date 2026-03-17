"""Yahoo Finance data provider."""

from __future__ import annotations

import asyncio
import math
from typing import Any

import yfinance as yf

from fin_toolkit.exceptions import TickerNotFoundError
from fin_toolkit.models.financial import (
    AnalystEstimates,
    EarningsEntry,
    FinancialStatements,
    KeyMetrics,
)
from fin_toolkit.models.price_data import PriceData, PricePoint

# Mapping from yfinance field names to normalized keys expected by the analyzer.
_FIELD_MAP: dict[str, str] = {
    "Total Revenue": "revenue",
    "Net Income": "net_income",
    "Gross Profit": "gross_profit",
    "Operating Income": "operating_income",
    "Interest Expense": "interest_expense",
    "EBITDA": "ebitda",
    "Total Assets": "total_assets",
    "Stockholders Equity": "total_equity",
    "Total Debt": "total_debt",
    "Current Assets": "current_assets",
    "Current Liabilities": "current_liabilities",
    "Invested Capital": "invested_capital",
    "Enterprise Value": "enterprise_value",
    "Operating Cash Flow": "operating_cash_flow",
    "Capital Expenditure": "capital_expenditures",
    "Free Cash Flow": "free_cash_flow",
    "Cash And Cash Equivalents": "cash_and_equivalents",
}


class YahooFinanceProvider:
    """Data provider using yfinance (async via asyncio.to_thread)."""

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        """Fetch historical OHLCV data from Yahoo Finance."""
        df = await asyncio.to_thread(self._fetch_history, ticker, start, end)
        if df.empty:
            raise TickerNotFoundError(ticker, provider="yahoo")

        prices = [
            PricePoint(
                date=idx.strftime("%Y-%m-%d"),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=int(row["Volume"]),
            )
            for idx, row in df.iterrows()
        ]
        return PriceData(ticker=ticker, period=f"{start}/{end}", prices=prices)

    async def get_financials(self, ticker: str) -> FinancialStatements:
        """Fetch financial statements from Yahoo Finance."""
        data = await asyncio.to_thread(self._fetch_financials, ticker)
        income, balance, cashflow = data

        if income.empty and balance.empty and cashflow.empty:
            raise TickerNotFoundError(ticker, provider="yahoo")

        return FinancialStatements(
            ticker=ticker,
            income_statement=self._df_to_dict(income) if not income.empty else None,
            balance_sheet=self._df_to_dict(balance) if not balance.empty else None,
            cash_flow=self._df_to_dict(cashflow) if not cashflow.empty else None,
            income_history=self._df_to_history(income) if not income.empty else None,
            cash_flow_history=self._df_to_history(cashflow) if not cashflow.empty else None,
        )

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        """Fetch key metrics from Yahoo Finance."""
        info = await asyncio.to_thread(self._fetch_info, ticker)
        if not info or info.get("marketCap") is None:
            raise TickerNotFoundError(ticker, provider="yahoo")

        return KeyMetrics(
            ticker=ticker,
            pe_ratio=info.get("trailingPE"),
            pb_ratio=info.get("priceToBook"),
            market_cap=info.get("marketCap"),
            dividend_yield=info.get("dividendYield"),
            roe=info.get("returnOnEquity"),
            roa=info.get("returnOnAssets"),
            debt_to_equity=info.get("debtToEquity"),
            enterprise_value=info.get("enterpriseValue"),
            ev_ebitda=info.get("enterpriseToEbitda"),
            fcf_yield=_compute_fcf_yield(info),
            shares_outstanding=info.get("sharesOutstanding"),
            current_price=info.get("currentPrice"),
        )

    async def get_analyst_estimates(self, ticker: str) -> AnalystEstimates:
        """Fetch Wall Street analyst estimates and earnings history."""
        info, earnings_dates = await asyncio.to_thread(
            self._fetch_info_and_earnings, ticker,
        )
        if not info or info.get("marketCap") is None:
            raise TickerNotFoundError(ticker, provider="yahoo")

        earnings_history = _parse_earnings_dates(earnings_dates)

        return AnalystEstimates(
            ticker=ticker,
            target_low=info.get("targetLowPrice"),
            target_median=info.get("targetMedianPrice"),
            target_high=info.get("targetHighPrice"),
            target_mean=info.get("targetMeanPrice"),
            recommendation=info.get("recommendationKey"),
            recommendation_score=info.get("recommendationMean"),
            num_analysts=info.get("numberOfAnalystOpinions"),
            forward_pe=info.get("forwardPE"),
            forward_eps=info.get("forwardEps"),
            earnings_history=earnings_history,
        )

    @staticmethod
    def _fetch_info_and_earnings(ticker: str) -> tuple[dict[str, Any], Any]:
        t = yf.Ticker(ticker)  # type: ignore[no-untyped-call]
        info = dict(t.info)
        try:
            earnings_dates = t.earnings_dates
        except Exception:  # noqa: BLE001 — yfinance may raise various exceptions
            earnings_dates = None
        return info, earnings_dates

    @staticmethod
    def _fetch_history(ticker: str, start: str, end: str) -> Any:
        t = yf.Ticker(ticker)  # type: ignore[no-untyped-call]
        return t.history(start=start, end=end)

    @staticmethod
    def _fetch_financials(ticker: str) -> tuple[Any, Any, Any]:
        t = yf.Ticker(ticker)  # type: ignore[no-untyped-call]
        return t.financials, t.balance_sheet, t.cashflow

    @staticmethod
    def _fetch_info(ticker: str) -> dict[str, Any]:
        t = yf.Ticker(ticker)  # type: ignore[no-untyped-call]
        return dict(t.info)

    @staticmethod
    def _df_to_dict(df: Any) -> dict[str, object]:
        """Convert yfinance DataFrame to flat dict with normalized field names.

        Takes the most recent period (first column) and maps yfinance field
        names to the normalized keys expected by the analyzer.
        """
        if df.columns.empty:
            return {}
        latest = df.iloc[:, 0]
        result: dict[str, object] = {}
        for field_name, value in latest.items():
            key = _FIELD_MAP.get(
                str(field_name), str(field_name).lower().replace(" ", "_"),
            )
            try:
                fval = float(value)
                if not math.isnan(fval):
                    result[key] = fval
            except (TypeError, ValueError):
                result[key] = value
        return result

    @staticmethod
    def _df_to_history(df: Any) -> list[dict[str, object]]:
        """Convert ALL columns of a yfinance DataFrame to a list of period dicts.

        Each dict has a 'period' key (date string) plus normalized field values.
        Columns are dates (most recent first); index is field names.
        """
        history: list[dict[str, object]] = []
        for col in df.columns:
            period_str = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)
            period_data: dict[str, object] = {"period": period_str}
            for field_name, value in df[col].items():
                key = _FIELD_MAP.get(
                    str(field_name), str(field_name).lower().replace(" ", "_"),
                )
                try:
                    fval = float(value)
                    if not math.isnan(fval):
                        period_data[key] = fval
                except (TypeError, ValueError):
                    period_data[key] = value
            history.append(period_data)
        return history


def _compute_fcf_yield(info: dict[str, Any]) -> float | None:
    """Compute FCF yield = freeCashflow / marketCap."""
    fcf = info.get("freeCashflow")
    mcap = info.get("marketCap")
    if fcf is not None and mcap is not None and mcap > 0:
        return float(fcf) / float(mcap)
    return None


def _parse_earnings_dates(df: Any) -> list[EarningsEntry]:
    """Convert yfinance earnings_dates DataFrame to list of EarningsEntry.

    DataFrame is indexed by earnings date with columns:
    'EPS Estimate', 'Reported EPS', 'Surprise(%)'.
    Rows with no Reported EPS are future (upcoming) — skip them.
    """
    if df is None or not hasattr(df, "iterrows") or df.empty:
        return []

    entries: list[EarningsEntry] = []
    for idx, row in df.iterrows():
        reported = row.get("Reported EPS")
        if reported is None or (isinstance(reported, float) and math.isnan(reported)):
            continue  # future earnings date — not yet reported
        period = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
        estimate = row.get("EPS Estimate")
        surprise = row.get("Surprise(%)")
        entries.append(
            EarningsEntry(
                period=period,
                eps_estimate=_safe_float(estimate),
                eps_actual=_safe_float(reported),
                surprise_pct=_safe_float(surprise),
            ),
        )
    return entries


def _safe_float(val: Any) -> float | None:
    """Convert to float, returning None for NaN or non-numeric values."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None
