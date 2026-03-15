"""DataProvider protocol definition."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData


@runtime_checkable
class DataProvider(Protocol):
    """Async protocol for financial data providers."""

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        """Fetch historical price data for a ticker."""
        ...

    async def get_financials(self, ticker: str) -> FinancialStatements:
        """Fetch financial statements for a ticker."""
        ...

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        """Fetch key metrics for a ticker."""
        ...
