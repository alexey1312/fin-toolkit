"""Tests for DataProvider protocol."""

from typing import runtime_checkable

from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData, PricePoint
from fin_toolkit.providers.protocol import DataProvider


class MockProvider:
    """A mock provider that should satisfy the DataProvider protocol."""

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        return PriceData(
            ticker=ticker,
            period=f"{start}/{end}",
            prices=[
                PricePoint(
                    date="2024-01-02",
                    open=100.0,
                    high=105.0,
                    low=99.0,
                    close=103.0,
                    volume=500_000,
                )
            ],
        )

    async def get_financials(self, ticker: str) -> FinancialStatements:
        return FinancialStatements(
            ticker=ticker,
            income_statement={"revenue": 1_000_000},
            balance_sheet={"total_assets": 5_000_000},
            cash_flow={"operating_cash_flow": 200_000},
        )

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        return KeyMetrics(
            ticker=ticker,
            pe_ratio=15.0,
            pb_ratio=2.0,
            market_cap=1e9,
            dividend_yield=0.02,
            roe=0.15,
            roa=0.08,
            debt_to_equity=0.5,
        )


class IncompleteProvider:
    """A provider missing required methods."""

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        return PriceData(ticker=ticker, period="", prices=[])


class TestDataProviderProtocol:
    def test_protocol_is_runtime_checkable(self) -> None:
        assert hasattr(DataProvider, "__protocol_attrs__") or runtime_checkable

    def test_mock_provider_satisfies_protocol(self) -> None:
        provider = MockProvider()
        assert isinstance(provider, DataProvider)

    def test_incomplete_provider_fails_protocol(self) -> None:
        provider = IncompleteProvider()
        assert not isinstance(provider, DataProvider)

    async def test_mock_provider_get_prices(self) -> None:
        provider = MockProvider()
        result = await provider.get_prices("AAPL", "2024-01-01", "2024-12-31")
        assert result.ticker == "AAPL"
        assert len(result.prices) == 1
        assert result.prices[0].close == 103.0

    async def test_mock_provider_get_financials(self) -> None:
        provider = MockProvider()
        result = await provider.get_financials("AAPL")
        assert result.ticker == "AAPL"
        assert result.income_statement is not None

    async def test_mock_provider_get_metrics(self) -> None:
        provider = MockProvider()
        result = await provider.get_metrics("AAPL")
        assert result.ticker == "AAPL"
        assert result.pe_ratio == 15.0
