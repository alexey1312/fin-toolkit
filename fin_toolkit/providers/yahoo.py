"""Yahoo Finance data provider."""

from __future__ import annotations

import asyncio
from typing import Any

import yfinance as yf

from fin_toolkit.exceptions import TickerNotFoundError
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData, PricePoint


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
        )

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        """Fetch key metrics from Yahoo Finance."""
        info = await asyncio.to_thread(self._fetch_info, ticker)
        if not info:
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
        )

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
        """Convert DataFrame to a nested dict {column: {index: value}}."""
        result: dict[str, object] = {}
        for col in df.columns:
            result[str(col)] = {str(idx): val for idx, val in df[col].items()}
        return result
