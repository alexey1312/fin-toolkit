"""Tests for FinancialDatasetsProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from fin_toolkit.exceptions import ProviderUnavailableError, TickerNotFoundError
from fin_toolkit.providers.financialdatasets import FinancialDatasetsProvider


def _make_prices_response() -> dict:
    return {
        "prices": [
            {
                "date": "2024-01-02",
                "open": 150.0,
                "high": 155.0,
                "low": 148.0,
                "close": 153.0,
                "volume": 1_000_000,
            },
            {
                "date": "2024-01-03",
                "open": 152.0,
                "high": 157.0,
                "low": 150.0,
                "close": 156.0,
                "volume": 1_200_000,
            },
        ],
    }


def _make_income_response() -> dict:
    return {
        "income_statements": [
            {
                "ticker": "AAPL",
                "report_period": "2024-09-30",
                "period": "annual",
                "revenue": 391_035_000_000,
                "net_income": 93_736_000_000,
                "gross_profit": 180_683_000_000,
                "operating_income": 123_216_000_000,
                "interest_expense": 3_002_000_000,
                "ebitda": 134_661_000_000,
            },
        ],
    }


def _make_balance_sheet_response() -> dict:
    return {
        "balance_sheets": [
            {
                "ticker": "AAPL",
                "report_period": "2024-09-30",
                "period": "annual",
                "total_assets": 364_980_000_000,
                "total_equity": 56_950_000_000,
                "total_debt": 96_802_000_000,
                "current_assets": 152_987_000_000,
                "current_liabilities": 176_392_000_000,
            },
        ],
    }


def _make_cashflow_response() -> dict:
    return {
        "cash_flow_statements": [
            {
                "ticker": "AAPL",
                "report_period": "2024-09-30",
                "period": "annual",
                "operating_cash_flow": 118_254_000_000,
                "capital_expenditure": -9_959_000_000,
                "free_cash_flow": 108_807_000_000,
            },
        ],
    }


def _make_metrics_snapshot() -> dict:
    return {
        "snapshot": {
            "ticker": "AAPL",
            "price_to_earnings_ratio": 28.5,
            "price_to_book_ratio": 40.0,
            "market_cap": 3_000_000_000_000,
            "payout_ratio": 0.005,
            "return_on_equity": 1.5,
            "return_on_assets": 0.3,
            "debt_to_equity": 180.0,
            "enterprise_value": 3_500_000_000_000,
        },
    }


def _mock_response(json_data: dict, status_code: int = 200) -> httpx.Response:
    """Create a mock httpx.Response."""
    response = httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "https://api.financialdatasets.ai/test"),
    )
    return response


class TestFinancialDatasetsProvider:
    def _provider(self) -> FinancialDatasetsProvider:
        return FinancialDatasetsProvider(api_key="test-key")

    @patch("fin_toolkit.providers.financialdatasets.httpx.AsyncClient")
    async def test_get_prices_success(self, mock_client_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(_make_prices_response())
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        provider = self._provider()
        result = await provider.get_prices("AAPL", "2024-01-01", "2024-01-05")

        assert result.ticker == "AAPL"
        assert len(result.prices) == 2
        assert result.prices[0].close == 153.0
        assert result.prices[0].date == "2024-01-02"
        assert result.prices[1].volume == 1_200_000

        mock_client.get.assert_called_once()
        call_kwargs = mock_client.get.call_args
        assert "X-API-KEY" in call_kwargs.kwargs.get("headers", {})

    @patch("fin_toolkit.providers.financialdatasets.httpx.AsyncClient")
    async def test_get_prices_empty_raises(self, mock_client_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response({"prices": []})
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        provider = self._provider()
        with pytest.raises(TickerNotFoundError):
            await provider.get_prices("INVALID", "2024-01-01", "2024-01-05")

    @patch("fin_toolkit.providers.financialdatasets.httpx.AsyncClient")
    async def test_get_prices_http_error_raises(self, mock_client_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response({}, status_code=401)
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        provider = self._provider()
        with pytest.raises(ProviderUnavailableError):
            await provider.get_prices("AAPL", "2024-01-01", "2024-01-05")

    @patch("fin_toolkit.providers.financialdatasets.httpx.AsyncClient")
    async def test_get_financials_success(self, mock_client_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_client.get.side_effect = [
            _mock_response(_make_income_response()),
            _mock_response(_make_balance_sheet_response()),
            _mock_response(_make_cashflow_response()),
        ]
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        provider = self._provider()
        result = await provider.get_financials("AAPL")

        assert result.ticker == "AAPL"
        assert result.income_statement is not None
        assert result.income_statement["revenue"] == 391_035_000_000
        assert result.income_statement["net_income"] == 93_736_000_000
        assert result.balance_sheet is not None
        assert result.balance_sheet["total_assets"] == 364_980_000_000
        assert result.balance_sheet["total_equity"] == 56_950_000_000
        assert result.cash_flow is not None
        assert result.cash_flow["operating_cash_flow"] == 118_254_000_000

    @patch("fin_toolkit.providers.financialdatasets.httpx.AsyncClient")
    async def test_get_financials_empty_raises(self, mock_client_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_client.get.side_effect = [
            _mock_response({"income_statements": []}),
            _mock_response({"balance_sheets": []}),
            _mock_response({"cash_flow_statements": []}),
        ]
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        provider = self._provider()
        with pytest.raises(TickerNotFoundError):
            await provider.get_financials("INVALID")

    @patch("fin_toolkit.providers.financialdatasets.httpx.AsyncClient")
    async def test_get_metrics_success(self, mock_client_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(_make_metrics_snapshot())
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        provider = self._provider()
        result = await provider.get_metrics("AAPL")

        assert result.ticker == "AAPL"
        assert result.pe_ratio == 28.5
        assert result.pb_ratio == 40.0
        assert result.market_cap == 3_000_000_000_000
        assert result.dividend_yield == 0.005
        assert result.roe == 1.5
        assert result.roa == 0.3
        assert result.debt_to_equity == 180.0
        assert result.enterprise_value == 3_500_000_000_000

    @patch("fin_toolkit.providers.financialdatasets.httpx.AsyncClient")
    async def test_get_metrics_empty_raises(self, mock_client_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response({"snapshot": {}})
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        provider = self._provider()
        with pytest.raises(TickerNotFoundError):
            await provider.get_metrics("INVALID")

    @patch("fin_toolkit.providers.financialdatasets.httpx.AsyncClient")
    async def test_get_metrics_null_fields_handled(self, mock_client_cls: AsyncMock) -> None:
        """API may return null for some metrics — should map to None."""
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response({
            "snapshot": {
                "ticker": "AAPL",
                "price_to_earnings_ratio": 28.5,
                "price_to_book_ratio": None,
                "market_cap": 3_000_000_000_000,
                "payout_ratio": None,
                "return_on_equity": None,
                "return_on_assets": None,
                "debt_to_equity": None,
                "enterprise_value": None,
            },
        })
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        provider = self._provider()
        result = await provider.get_metrics("AAPL")

        assert result.pe_ratio == 28.5
        assert result.pb_ratio is None
        assert result.dividend_yield is None
