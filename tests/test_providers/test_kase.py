"""Tests for KASE provider (JSON API)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from fin_toolkit.exceptions import ProviderUnavailableError, TickerNotFoundError
from fin_toolkit.providers.kase import KASEProvider, _KASEClient

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


def _mock_response(json_data: Any, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "https://kase.kz/api/test"),
    )


# ── _KASEClient tests ──────────────────────────────────────────────


class TestKASEClient:
    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_share_data_success(self, mock_cls: AsyncMock) -> None:
        fixture = _load_fixture("kase_share_data.json")
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(fixture)
        mock_cls.return_value.__aenter__.return_value = mock_client

        client = _KASEClient()
        result = await client.get_share_data("KCEL")

        assert result["ticker"] == "KCEL"
        assert result["capit"] == 462_000_000_000.0
        assert result["price"] == 4620.0
        assert result["pe"] == 12.5

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_share_data_not_found(self, mock_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(None, status_code=404)
        mock_cls.return_value.__aenter__.return_value = mock_client

        client = _KASEClient()
        with pytest.raises(TickerNotFoundError):
            await client.get_share_data("INVALID")

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_share_data_server_error(self, mock_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response({}, status_code=500)
        mock_cls.return_value.__aenter__.return_value = mock_client

        client = _KASEClient()
        with pytest.raises(ProviderUnavailableError):
            await client.get_share_data("KCEL")

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_trade_info_success(self, mock_cls: AsyncMock) -> None:
        fixture = _load_fixture("kase_trade_info.json")
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(fixture)
        mock_cls.return_value.__aenter__.return_value = mock_client

        client = _KASEClient()
        result = await client.get_trade_info("KCEL")

        assert result["close"] == 4620.0
        assert result["volume"] == 125_000

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_list_securities_success(self, mock_cls: AsyncMock) -> None:
        fixture = _load_fixture("kase_securities.json")
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(fixture)
        mock_cls.return_value.__aenter__.return_value = mock_client

        client = _KASEClient()
        result = await client.list_securities(sec_type="share")

        assert len(result) == 3
        assert result[0]["code"] == "KCEL"

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_list_securities_empty(self, mock_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(None, status_code=404)
        mock_cls.return_value.__aenter__.return_value = mock_client

        client = _KASEClient()
        result = await client.list_securities()
        assert result == []

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_dividends_success(self, mock_cls: AsyncMock) -> None:
        fixture = _load_fixture("kase_dividends.json")
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(fixture)
        mock_cls.return_value.__aenter__.return_value = mock_client

        client = _KASEClient()
        result = await client.get_dividends("KCEL")

        assert len(result) == 2
        assert result[0]["dividend_per_share"] == 250.0

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_dividends_empty(self, mock_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(None, status_code=404)
        mock_cls.return_value.__aenter__.return_value = mock_client

        client = _KASEClient()
        result = await client.get_dividends("UNKNOWN")
        assert result == []

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_search_success(self, mock_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response({"issuers": [{"name": "Kcell"}]})
        mock_cls.return_value.__aenter__.return_value = mock_client

        client = _KASEClient()
        result = await client.search("kcell")
        assert "issuers" in result

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_last_deals_success(self, mock_cls: AsyncMock) -> None:
        deals = [{"price": 4620.0, "volume": 100}]
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(deals)
        mock_cls.return_value.__aenter__.return_value = mock_client

        client = _KASEClient()
        result = await client.get_last_deals("KCEL")
        assert len(result) == 1

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_calendar(self, mock_cls: AsyncMock) -> None:
        cal = [{"date": "2024-01-02", "is_trading": True}]
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(cal)
        mock_cls.return_value.__aenter__.return_value = mock_client

        client = _KASEClient()
        result = await client.get_calendar()
        assert len(result) == 1


# ── KASEProvider tests ──────────────────────────────────────────────


class TestKASEProvider:
    async def test_get_prices_delegates_to_yahoo(self) -> None:
        """get_prices should delegate to Yahoo with .ME suffix."""
        from fin_toolkit.models.price_data import PricePoint

        mock_yahoo = AsyncMock()
        mock_yahoo.get_prices.return_value = AsyncMock(
            period="2024-01-01/2024-01-05",
            prices=[
                PricePoint(
                    date="2024-01-02", open=4500.0, high=4650.0,
                    low=4480.0, close=4620.0, volume=125_000,
                ),
            ],
        )

        provider = KASEProvider(yahoo=mock_yahoo)
        result = await provider.get_prices("KCEL", "2024-01-01", "2024-01-05")

        assert result.ticker == "KCEL"
        assert len(result.prices) == 1
        assert result.prices[0].close == 4620.0
        mock_yahoo.get_prices.assert_called_once_with("KCEL.ME", "2024-01-01", "2024-01-05")

    async def test_get_prices_no_yahoo_raises(self) -> None:
        """get_prices without Yahoo provider should raise."""
        provider = KASEProvider()
        with pytest.raises(ProviderUnavailableError):
            await provider.get_prices("KCEL", "2024-01-01", "2024-01-05")

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_metrics_success(self, mock_cls: AsyncMock) -> None:
        fixture = _load_fixture("kase_share_data.json")
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(fixture)
        mock_cls.return_value.__aenter__.return_value = mock_client

        provider = KASEProvider()
        result = await provider.get_metrics("KCEL")

        assert result.ticker == "KCEL"
        assert result.market_cap == 462_000_000_000.0
        assert result.current_price == 4620.0
        assert result.pe_ratio == 12.5
        assert result.pb_ratio == 3.2
        assert result.dividend_yield == 0.045
        assert result.roe is None
        assert result.roa is None

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_metrics_not_found(self, mock_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(None, status_code=404)
        mock_cls.return_value.__aenter__.return_value = mock_client

        provider = KASEProvider()
        with pytest.raises(TickerNotFoundError):
            await provider.get_metrics("INVALID")

    async def test_get_financials_returns_none_fields(self) -> None:
        """KASE doesn't provide financial statements."""
        provider = KASEProvider()
        result = await provider.get_financials("KCEL")

        assert result.ticker == "KCEL"
        assert result.income_statement is None
        assert result.balance_sheet is None
        assert result.cash_flow is None
