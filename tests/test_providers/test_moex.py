"""Tests for MOEX ISS provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fin_toolkit.exceptions import TickerNotFoundError
from fin_toolkit.providers.moex import MOEXProvider


class TestMOEXGetPrices:
    async def test_valid_ticker_returns_price_data(self) -> None:
        provider = MOEXProvider()
        mock_candles = [
            {
                "begin": "2024-01-15 00:00:00",
                "open": 100.0,
                "high": 105.0,
                "low": 98.0,
                "close": 103.0,
                "volume": 500000,
            },
            {
                "begin": "2024-01-16 00:00:00",
                "open": 103.0,
                "high": 107.0,
                "low": 101.0,
                "close": 106.0,
                "volume": 600000,
            },
        ]
        with patch("fin_toolkit.providers.moex.aiomoex") as mock_moex:
            mock_moex.get_market_candles = AsyncMock(return_value=mock_candles)
            with patch("fin_toolkit.providers.moex.aiohttp.ClientSession") as mock_session:
                mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await provider.get_prices("SBER", "2024-01-01", "2024-02-01")

        assert result.ticker == "SBER"
        assert result.currency == "RUB"
        assert len(result.prices) == 2
        assert result.prices[0].close == 103.0

    async def test_empty_result_raises_not_found(self) -> None:
        provider = MOEXProvider()
        with patch("fin_toolkit.providers.moex.aiomoex") as mock_moex:
            mock_moex.get_market_candles = AsyncMock(return_value=[])
            with patch("fin_toolkit.providers.moex.aiohttp.ClientSession") as mock_session:
                mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
                with pytest.raises(TickerNotFoundError):
                    await provider.get_prices("INVALID", "2024-01-01", "2024-02-01")


class TestMOEXGetMetrics:
    async def test_valid_ticker(self) -> None:
        provider = MOEXProvider()
        mock_securities = [
            {
                "SECID": "SBER",
                "PREVPRICE": 275.5,
                "ISSUESIZE": 21586948000.0,
                "MARKETPRICEBOARD": "TQBR",
                "LISTLEVEL": 1,
            },
        ]
        with patch("fin_toolkit.providers.moex.aiomoex") as mock_moex:
            mock_moex.get_board_securities = AsyncMock(return_value=mock_securities)
            with patch("fin_toolkit.providers.moex.aiohttp.ClientSession") as mock_session:
                mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
                result = await provider.get_metrics("SBER")

        assert result.ticker == "SBER"
        assert result.current_price == 275.5
        assert result.shares_outstanding == 21586948000.0
        assert result.market_cap is not None

    async def test_ticker_not_found(self) -> None:
        provider = MOEXProvider()
        with patch("fin_toolkit.providers.moex.aiomoex") as mock_moex:
            mock_moex.get_board_securities = AsyncMock(return_value=[])
            with patch("fin_toolkit.providers.moex.aiohttp.ClientSession") as mock_session:
                mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
                with pytest.raises(TickerNotFoundError):
                    await provider.get_metrics("INVALID")


class TestMOEXGetFinancials:
    async def test_returns_empty_financials(self) -> None:
        """MOEX ISS doesn't provide financial statements."""
        provider = MOEXProvider()
        result = await provider.get_financials("SBER")
        assert result.ticker == "SBER"
        assert result.income_statement is None
        assert result.balance_sheet is None
        assert result.cash_flow is None


class TestMOEXListTickers:
    async def test_list_tickers(self) -> None:
        provider = MOEXProvider()
        mock_data = [
            {"SECID": "SBER"},
            {"SECID": "GAZP"},
            {"SECID": "LKOH"},
        ]
        with patch("fin_toolkit.providers.moex.aiomoex") as mock_moex:
            mock_moex.get_board_securities = AsyncMock(return_value=mock_data)
            with patch("fin_toolkit.providers.moex.aiohttp.ClientSession") as mock_session:
                mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.return_value.__aexit__ = AsyncMock(return_value=False)
                tickers = await provider.list_tickers()

        assert tickers == ["SBER", "GAZP", "LKOH"]
