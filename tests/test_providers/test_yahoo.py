"""Tests for YahooFinanceProvider."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from fin_toolkit.exceptions import TickerNotFoundError
from fin_toolkit.providers.yahoo import YahooFinanceProvider


def _make_history_df() -> pd.DataFrame:
    """Create a mock yfinance history DataFrame."""
    return pd.DataFrame(
        {
            "Open": [150.0, 152.0],
            "High": [155.0, 157.0],
            "Low": [148.0, 150.0],
            "Close": [153.0, 156.0],
            "Volume": [1_000_000, 1_200_000],
        },
        index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
    )


def _make_info() -> dict[str, object]:
    return {
        "trailingPE": 28.5,
        "priceToBook": 40.0,
        "marketCap": 3_000_000_000_000,
        "dividendYield": 0.005,
        "returnOnEquity": 1.5,
        "returnOnAssets": 0.3,
        "debtToEquity": 180.0,
    }


def _make_financials_df() -> pd.DataFrame:
    return pd.DataFrame(
        {"2024": [100_000, 50_000]},
        index=["Total Revenue", "Net Income"],
    )


def _make_balance_sheet_df() -> pd.DataFrame:
    return pd.DataFrame(
        {"2024": [500_000, 200_000]},
        index=["Total Assets", "Total Liabilities"],
    )


def _make_cashflow_df() -> pd.DataFrame:
    return pd.DataFrame(
        {"2024": [80_000]},
        index=["Operating Cash Flow"],
    )


class TestYahooFinanceProvider:
    @patch("fin_toolkit.providers.yahoo.yf")
    async def test_get_prices_success(self, mock_yf: MagicMock) -> None:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_history_df()
        mock_yf.Ticker.return_value = mock_ticker

        provider = YahooFinanceProvider()
        result = await provider.get_prices("AAPL", "2024-01-01", "2024-01-05")

        assert result.ticker == "AAPL"
        assert len(result.prices) == 2
        assert result.prices[0].close == 153.0
        assert result.prices[0].date == "2024-01-02"
        assert result.prices[1].volume == 1_200_000

    @patch("fin_toolkit.providers.yahoo.yf")
    async def test_get_prices_empty_raises_ticker_not_found(self, mock_yf: MagicMock) -> None:
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_ticker

        provider = YahooFinanceProvider()
        with pytest.raises(TickerNotFoundError):
            await provider.get_prices("INVALID", "2024-01-01", "2024-01-05")

    @patch("fin_toolkit.providers.yahoo.yf")
    async def test_get_financials_success(self, mock_yf: MagicMock) -> None:
        mock_ticker = MagicMock()
        mock_ticker.financials = _make_financials_df()
        mock_ticker.balance_sheet = _make_balance_sheet_df()
        mock_ticker.cashflow = _make_cashflow_df()
        mock_yf.Ticker.return_value = mock_ticker

        provider = YahooFinanceProvider()
        result = await provider.get_financials("AAPL")

        assert result.ticker == "AAPL"
        assert result.income_statement is not None
        assert result.income_statement["revenue"] == 100_000
        assert result.income_statement["net_income"] == 50_000
        assert result.balance_sheet is not None
        assert result.balance_sheet["total_assets"] == 500_000
        assert result.cash_flow is not None
        assert result.cash_flow["operating_cash_flow"] == 80_000

    @patch("fin_toolkit.providers.yahoo.yf")
    async def test_get_financials_empty_raises(self, mock_yf: MagicMock) -> None:
        mock_ticker = MagicMock()
        mock_ticker.financials = pd.DataFrame()
        mock_ticker.balance_sheet = pd.DataFrame()
        mock_ticker.cashflow = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_ticker

        provider = YahooFinanceProvider()
        with pytest.raises(TickerNotFoundError):
            await provider.get_financials("INVALID")

    @patch("fin_toolkit.providers.yahoo.yf")
    async def test_get_metrics_success(self, mock_yf: MagicMock) -> None:
        mock_ticker = MagicMock()
        mock_ticker.info = _make_info()
        mock_yf.Ticker.return_value = mock_ticker

        provider = YahooFinanceProvider()
        result = await provider.get_metrics("AAPL")

        assert result.ticker == "AAPL"
        assert result.pe_ratio == 28.5
        assert result.pb_ratio == 40.0
        assert result.market_cap == 3_000_000_000_000
        assert result.dividend_yield == 0.005
        assert result.roe == 1.5
        assert result.debt_to_equity == 180.0

    @patch("fin_toolkit.providers.yahoo.yf")
    async def test_get_metrics_empty_info_raises(self, mock_yf: MagicMock) -> None:
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        mock_yf.Ticker.return_value = mock_ticker

        provider = YahooFinanceProvider()
        with pytest.raises(TickerNotFoundError):
            await provider.get_metrics("INVALID")
