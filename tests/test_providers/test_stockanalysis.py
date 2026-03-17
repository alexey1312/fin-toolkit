"""Tests for StockAnalysis provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fin_toolkit.exceptions import ProviderUnavailableError, TickerNotFoundError
from fin_toolkit.providers.stockanalysis import (
    StockAnalysisProvider,
    _parse_ratios_payload,
)

# ---------------------------------------------------------------------------
# Sample Svelte payload (minimal, matches real structure)
# ---------------------------------------------------------------------------

_SAMPLE_HTML = """
<html><head></head><body>
<script>
__sveltekit_abc123 = {
    data: [{}, {
        financialData:{datekey:["TTM","2024-12-31","2023-12-31"],fiscalYear:[null,2024,2023],pe:[3.798,3.012,2.702],ps:[2.2,1.6,1.1],pb:[1.269,.904,.756],roe:[.35534,.33219,.30894],roa:[.05741,.04832,.03912],roic:[null,.25,.20],debtequity:[.65,.55,.45],evebitda:[null,null,null],currentratio:[null,null,null],fcfyield:[-.432,.12,.15],dividendyield:[.031,.025,.02],marketcap:[4147799937173.55,2774274900663.87,1873457432978.97],ev:[null,null,null],evrevenue:[null,null,null]}
    }]
};
</script>
</body></html>
"""

_SAMPLE_HTML_NONBANK = """
<html><head></head><body>
<script>
__sveltekit_abc123 = {
    data: [{}, {
        financialData:{datekey:["TTM","2024-12-31"],fiscalYear:[null,2024],pe:[38.45,10.331],ps:[0.36,0.28],pb:[1.391,1.382],roe:[.08222,.17364],roa:[.02488,.03737],roic:[.08188,.10337],debtequity:[2.506,2.254],evebitda:[4.015,9.457],currentratio:[1.382,1.55],fcfyield:[.371,.495],dividendyield:[.024,.022],marketcap:[260386000000,200000000000],ev:[350000000000,300000000000],evrevenue:[.5,.4]}
    }]
};
</script>
</body></html>
"""

_EMPTY_HTML = "<html><body>No data here</body></html>"


# ---------------------------------------------------------------------------
# _parse_ratios_payload
# ---------------------------------------------------------------------------


class TestParseRatiosPayload:
    def test_parses_bank_ticker(self) -> None:
        result = _parse_ratios_payload(_SAMPLE_HTML)
        assert result is not None
        assert result["pe"] == pytest.approx(3.798)
        assert result["pb"] == pytest.approx(1.269)
        assert result["roe"] == pytest.approx(0.35534)
        assert result["roa"] == pytest.approx(0.05741)
        assert result["debtequity"] == pytest.approx(0.65)
        assert result["dividendyield"] == pytest.approx(0.031)
        assert result["marketcap"] == pytest.approx(4147799937173.55)

    def test_parses_nonbank_with_evebitda(self) -> None:
        result = _parse_ratios_payload(_SAMPLE_HTML_NONBANK)
        assert result is not None
        assert result["pe"] == pytest.approx(38.45)
        assert result["evebitda"] == pytest.approx(4.015)
        assert result["roic"] == pytest.approx(0.08188)
        assert result["currentratio"] == pytest.approx(1.382)

    def test_null_ttm_returns_none(self) -> None:
        """When TTM value is null, field should be None."""
        result = _parse_ratios_payload(_SAMPLE_HTML)
        assert result is not None
        # evebitda is null for bank ticker
        assert result.get("evebitda") is None

    def test_empty_html_returns_none(self) -> None:
        result = _parse_ratios_payload(_EMPTY_HTML)
        assert result is None

    def test_all_expected_fields_present(self) -> None:
        result = _parse_ratios_payload(_SAMPLE_HTML_NONBANK)
        assert result is not None
        expected = {
            "pe", "pb", "roe", "roa", "roic", "debtequity",
            "evebitda", "currentratio", "fcfyield", "dividendyield",
            "marketcap", "ev",
        }
        for field in expected:
            assert field in result, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# StockAnalysisProvider.get_metrics
# ---------------------------------------------------------------------------


class TestGetMetrics:
    @patch("fin_toolkit.providers.stockanalysis.httpx.AsyncClient")
    async def test_returns_key_metrics(self, mock_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = _SAMPLE_HTML_NONBANK
        mock_resp.raise_for_status = lambda: None
        mock_client.get.return_value = mock_resp
        mock_cls.return_value.__aenter__.return_value = mock_client

        provider = StockAnalysisProvider()
        result = await provider.get_metrics("AIRA")

        assert result.ticker == "AIRA"
        assert result.pe_ratio == pytest.approx(38.45)
        assert result.pb_ratio == pytest.approx(1.391)
        assert result.roe == pytest.approx(0.08222)
        assert result.roa == pytest.approx(0.02488)
        assert result.debt_to_equity == pytest.approx(2.506)
        assert result.ev_ebitda == pytest.approx(4.015)
        assert result.dividend_yield == pytest.approx(0.024)
        assert result.market_cap == pytest.approx(260386000000)
        assert result.enterprise_value == pytest.approx(350000000000)
        assert result.fcf_yield == pytest.approx(0.371)

    @patch("fin_toolkit.providers.stockanalysis.httpx.AsyncClient")
    async def test_null_fields_become_none(self, mock_cls: AsyncMock) -> None:
        """Bank ticker: evebitda=null in TTM → None in KeyMetrics."""
        mock_client = AsyncMock()
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = _SAMPLE_HTML
        mock_resp.raise_for_status = lambda: None
        mock_client.get.return_value = mock_resp
        mock_cls.return_value.__aenter__.return_value = mock_client

        provider = StockAnalysisProvider()
        result = await provider.get_metrics("HSBK")

        assert result.pe_ratio == pytest.approx(3.798)
        assert result.ev_ebitda is None  # null for banks

    @patch("fin_toolkit.providers.stockanalysis.httpx.AsyncClient")
    async def test_no_data_raises_ticker_not_found(self, mock_cls: AsyncMock) -> None:
        mock_client = AsyncMock()
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = _EMPTY_HTML
        mock_resp.raise_for_status = lambda: None
        mock_client.get.return_value = mock_resp
        mock_cls.return_value.__aenter__.return_value = mock_client

        provider = StockAnalysisProvider()
        with pytest.raises(TickerNotFoundError):
            await provider.get_metrics("FAKE")

    @patch("fin_toolkit.providers.stockanalysis.httpx.AsyncClient")
    async def test_http_error_raises_unavailable(self, mock_cls: AsyncMock) -> None:
        import httpx

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("connection refused")
        mock_cls.return_value.__aenter__.return_value = mock_client

        provider = StockAnalysisProvider()
        with pytest.raises(ProviderUnavailableError):
            await provider.get_metrics("HSBK")


# ---------------------------------------------------------------------------
# get_prices / get_financials — not supported
# ---------------------------------------------------------------------------


class TestUnsupportedMethods:
    async def test_get_prices_raises(self) -> None:
        provider = StockAnalysisProvider()
        with pytest.raises(ProviderUnavailableError):
            await provider.get_prices("HSBK", "2024-01-01", "2024-12-31")

    async def test_get_financials_raises(self) -> None:
        provider = StockAnalysisProvider()
        with pytest.raises(ProviderUnavailableError):
            await provider.get_financials("HSBK")
