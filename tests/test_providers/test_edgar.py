"""Tests for SEC EDGAR provider."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from fin_toolkit.exceptions import ProviderUnavailableError, TickerNotFoundError
from fin_toolkit.providers.edgar import EdgarProvider


def _mock_edgar_setup(
    xbrl_attrs: dict[str, object] | None = None,
    filings_empty: bool = False,
) -> MagicMock:
    """Build a mock Company that returns given XBRL attrs."""
    if filings_empty:
        mock_filings = MagicMock()
        mock_filings.__bool__ = lambda _: False
        mock_company = MagicMock()
        mock_company.get_filings.return_value = mock_filings
        return mock_company

    # Use SimpleNamespace so getattr returns DEFAULT (raises AttributeError)
    # for non-set attributes instead of returning another MagicMock
    mock_xbrl = SimpleNamespace(**(xbrl_attrs or {}))

    mock_filing = MagicMock()
    mock_filing.xbrl.return_value = mock_xbrl

    mock_filings = MagicMock()
    mock_filings.__bool__ = lambda _: True
    mock_filings.latest.return_value = mock_filing

    mock_company = MagicMock()
    mock_company.get_filings.return_value = mock_filings
    return mock_company


class TestEdgarGetPrices:
    async def test_raises_unavailable(self) -> None:
        """EDGAR doesn't provide prices."""
        provider = EdgarProvider()
        with pytest.raises(ProviderUnavailableError):
            await provider.get_prices("AAPL", "2024-01-01", "2024-12-31")


class TestEdgarGetFinancials:
    async def test_valid_ticker(self) -> None:
        provider = EdgarProvider()
        mock_company = _mock_edgar_setup(xbrl_attrs={
            "Revenues": 394328000000,
            "NetIncomeLoss": 96995000000,
            "Assets": 352583000000,
            "StockholdersEquity": 62146000000,
            "NetCashProvidedByUsedInOperatingActivities": 110543000000,
        })

        with patch("edgar.Company", return_value=mock_company, create=True):
            result = await provider.get_financials("AAPL")

        assert result.ticker == "AAPL"
        assert result.income_statement is not None
        assert result.income_statement.get("revenue") == 394328000000

    async def test_no_filings_raises(self) -> None:
        provider = EdgarProvider()
        mock_company = _mock_edgar_setup(filings_empty=True)

        with patch("edgar.Company", return_value=mock_company, create=True):
            with pytest.raises(TickerNotFoundError):
                await provider.get_financials("INVALID")


class TestEdgarGetMetrics:
    async def test_derives_metrics(self) -> None:
        provider = EdgarProvider()
        mock_company = _mock_edgar_setup(xbrl_attrs={
            "Revenues": 100_000_000,
            "NetIncomeLoss": 10_000_000,
            "Assets": 200_000_000,
            "StockholdersEquity": 50_000_000,
            "NetCashProvidedByUsedInOperatingActivities": 20_000_000,
        })

        with patch("edgar.Company", return_value=mock_company, create=True):
            result = await provider.get_metrics("AAPL")

        assert result.roe is not None
        assert result.roe == pytest.approx(0.2, abs=0.01)
        assert result.roa is not None
