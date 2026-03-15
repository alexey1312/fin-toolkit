"""Tests for KASEProvider."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from fin_toolkit.exceptions import ProviderUnavailableError, TickerNotFoundError
from fin_toolkit.providers.kase import KASEProvider

FIXTURES = Path(__file__).parent / "fixtures"


def _read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


def _mock_response(html: str, status_code: int = 200) -> httpx.Response:
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.text = html
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=response
        )
    return response


class TestKASEProvider:
    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_prices_success(self, mock_client_cls: MagicMock) -> None:
        html = _read_fixture("kase_prices.html")
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(html)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        provider = KASEProvider()
        result = await provider.get_prices("KCEL", "2024-01-01", "2024-01-05")

        assert result.ticker == "KCEL"
        assert len(result.prices) == 2
        assert result.prices[0].close == 4620.0
        assert result.prices[0].date == "2024-01-02"
        assert result.prices[0].volume == 125_000
        assert result.prices[1].close == 4680.0

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_prices_empty_raises(self, mock_client_cls: MagicMock) -> None:
        html = _read_fixture("kase_empty.html")
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(html)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        provider = KASEProvider()
        with pytest.raises(TickerNotFoundError):
            await provider.get_prices("INVALID", "2024-01-01", "2024-01-05")

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_prices_http_error(self, mock_client_cls: MagicMock) -> None:
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response("", status_code=500)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        provider = KASEProvider()
        with pytest.raises(ProviderUnavailableError):
            await provider.get_prices("KCEL", "2024-01-01", "2024-01-05")

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_financials_returns_none_fields(self, mock_client_cls: MagicMock) -> None:
        """KASE doesn't provide financial statements, so fields should be None."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        provider = KASEProvider()
        result = await provider.get_financials("KCEL")

        assert result.ticker == "KCEL"
        assert result.income_statement is None
        assert result.balance_sheet is None
        assert result.cash_flow is None

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_metrics_returns_none_fields(self, mock_client_cls: MagicMock) -> None:
        """KASE doesn't provide key metrics, so fields should be None."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        provider = KASEProvider()
        result = await provider.get_metrics("KCEL")

        assert result.ticker == "KCEL"
        assert result.pe_ratio is None
        assert result.market_cap is None
