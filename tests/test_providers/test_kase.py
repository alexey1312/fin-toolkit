"""Tests for KASE provider (JSON API)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from fin_toolkit.exceptions import ProviderUnavailableError, TickerNotFoundError
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
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
        """get_prices should delegate to Yahoo via multi-suffix resolution."""
        from fin_toolkit.models.price_data import PricePoint

        mock_yahoo = AsyncMock()
        price_data = AsyncMock(
            period="2024-01-01/2024-01-05",
            prices=[
                PricePoint(
                    date="2024-01-02", open=4500.0, high=4650.0,
                    low=4480.0, close=4620.0, volume=125_000,
                ),
            ],
        )
        mock_yahoo.get_prices.return_value = price_data

        provider = KASEProvider(yahoo=mock_yahoo)
        result = await provider.get_prices("KCEL", "2024-01-01", "2024-01-05")

        assert result.ticker == "KCEL"
        assert len(result.prices) == 1
        assert result.prices[0].close == 4620.0
        # First call is probe (.ME), second is actual fetch
        assert mock_yahoo.get_prices.call_count == 2
        # Both use .ME suffix (probe succeeded)
        calls = mock_yahoo.get_prices.call_args_list
        assert calls[0].args[0] == "KCEL.ME"
        assert calls[1].args[0] == "KCEL.ME"

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
        """KASE without Yahoo returns None fields."""
        provider = KASEProvider()
        result = await provider.get_financials("KCEL")

        assert result.ticker == "KCEL"
        assert result.income_statement is None
        assert result.balance_sheet is None
        assert result.cash_flow is None


# ── list_tickers tests ────────────────────────────────────────────


def _sec(code: str, category: str = "main_shares_premium") -> dict[str, Any]:
    """Helper to build a minimal KASE security dict with ticker_category."""
    return {"code": code, "ticker": {"ticker_category": category}}


class TestListTickers:
    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_list_tickers_fetches_dynamically(self, mock_cls: AsyncMock) -> None:
        """list_tickers extracts codes from list_securities response."""
        securities = [
            _sec("KCEL"),
            _sec("AIRA"),
            _sec("HSBK"),
        ]
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(securities)
        mock_cls.return_value.__aenter__.return_value = mock_client

        provider = KASEProvider()
        result = await provider.list_tickers()

        assert result == ["KCEL", "AIRA", "HSBK"]

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_list_tickers_caches_24h(self, mock_cls: AsyncMock) -> None:
        """Second call within 24h should not hit API."""
        securities = [_sec("KCEL"), _sec("AIRA")]
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(securities)
        mock_cls.return_value.__aenter__.return_value = mock_client

        provider = KASEProvider()
        result1 = await provider.list_tickers()
        result2 = await provider.list_tickers()

        assert result1 == result2
        # Only one HTTP call — second was cached
        assert mock_client.get.call_count == 1

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_list_tickers_skips_entries_without_code(self, mock_cls: AsyncMock) -> None:
        """Entries without 'code' field are filtered out."""
        securities = [_sec("KCEL"), {"name": "no_code"}, {"code": "", "ticker": {}}]
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(securities)
        mock_cls.return_value.__aenter__.return_value = mock_client

        provider = KASEProvider()
        result = await provider.list_tickers()

        assert result == ["KCEL"]

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_list_tickers_excludes_kase_global(self, mock_cls: AsyncMock) -> None:
        """Cross-listed foreign shares (KASE Global) are filtered out."""
        securities = [
            _sec("KCEL", "main_shares_premium"),
            _sec("AAPL_KZ", "kase_global"),
            _sec("TSLA_KZ", "kase_global"),
            _sec("AIRA", "main_shares_standard"),
        ]
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(securities)
        mock_cls.return_value.__aenter__.return_value = mock_client

        provider = KASEProvider()
        result = await provider.list_tickers()

        assert result == ["KCEL", "AIRA"]
        assert "AAPL_KZ" not in result
        assert "TSLA_KZ" not in result

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_list_tickers_excludes_unknown_category(self, mock_cls: AsyncMock) -> None:
        """Entries without ticker_category (delisted/legacy) are excluded."""
        securities = [
            _sec("KCEL", "main_shares_premium"),
            {"code": "OLD_TICKER", "ticker": {}},  # no category
            {"code": "LEGACY"},  # no ticker field at all
            _sec("CCBN", "alternative_shares"),
        ]
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(securities)
        mock_cls.return_value.__aenter__.return_value = mock_client

        provider = KASEProvider()
        result = await provider.list_tickers()

        assert result == ["KCEL", "CCBN"]


# ── Multi-suffix Yahoo resolution tests ───────────────────────────


class TestYahooSuffixResolution:
    async def test_get_prices_tries_me_then_il(self) -> None:
        """When .ME fails, should try .IL suffix (AIRA case)."""
        from fin_toolkit.models.price_data import PricePoint

        mock_yahoo = AsyncMock()
        price_data = AsyncMock(
            period="2024-01-01/2024-01-05",
            prices=[PricePoint(
                date="2024-01-02", open=10.0, high=11.0,
                low=9.0, close=10.5, volume=1000,
            )],
        )
        # Probe .ME fails, probe .IL succeeds, then fetch .IL succeeds
        mock_yahoo.get_prices.side_effect = [
            TickerNotFoundError("AIRA.ME"),
            price_data,
            price_data,
        ]

        provider = KASEProvider(yahoo=mock_yahoo)
        result = await provider.get_prices("AIRA", "2024-01-01", "2024-01-05")

        assert result.ticker == "AIRA"
        assert mock_yahoo.get_prices.call_count == 3
        calls = mock_yahoo.get_prices.call_args_list
        assert calls[0].args[0] == "AIRA.ME"  # probe
        assert calls[1].args[0] == "AIRA.IL"  # probe (success)
        assert calls[2].args[0] == "AIRA.IL"  # actual fetch

    async def test_get_prices_caches_suffix(self) -> None:
        """Once suffix is found, subsequent calls use cache."""
        from fin_toolkit.models.price_data import PricePoint

        mock_yahoo = AsyncMock()
        price_data = AsyncMock(
            period="2024-01-01/2024-01-05",
            prices=[PricePoint(
                date="2024-01-02", open=10.0, high=11.0,
                low=9.0, close=10.5, volume=1000,
            )],
        )
        # First: probe .ME (fail) + probe .IL (ok) + fetch .IL
        # Second: fetch .IL (cached suffix, no probe)
        mock_yahoo.get_prices.side_effect = [
            TickerNotFoundError("AIRA.ME"),
            price_data,
            price_data,
            price_data,
        ]

        provider = KASEProvider(yahoo=mock_yahoo)
        await provider.get_prices("AIRA", "2024-01-01", "2024-01-05")
        await provider.get_prices("AIRA", "2024-01-01", "2024-01-05")

        # 3 for first (probe .ME + probe .IL + fetch .IL), 1 for second (cached)
        assert mock_yahoo.get_prices.call_count == 4
        last_call = mock_yahoo.get_prices.call_args_list[3]
        assert last_call.args[0] == "AIRA.IL"

    async def test_get_prices_all_suffixes_fail(self) -> None:
        """When all suffixes fail, raise ProviderUnavailableError."""
        mock_yahoo = AsyncMock()
        mock_yahoo.get_prices.side_effect = TickerNotFoundError("fail")

        provider = KASEProvider(yahoo=mock_yahoo)
        with pytest.raises(ProviderUnavailableError, match="No Yahoo ticker"):
            await provider.get_prices("XXXX", "2024-01-01", "2024-01-05")

    async def test_get_prices_me_succeeds_first(self) -> None:
        """When .ME works (e.g. KCEL), probe + fetch = 2 calls."""
        from fin_toolkit.models.price_data import PricePoint

        mock_yahoo = AsyncMock()
        mock_yahoo.get_prices.return_value = AsyncMock(
            period="2024-01-01/2024-01-05",
            prices=[PricePoint(
                date="2024-01-02", open=4500.0, high=4650.0,
                low=4480.0, close=4620.0, volume=125_000,
            )],
        )

        provider = KASEProvider(yahoo=mock_yahoo)
        result = await provider.get_prices("KCEL", "2024-01-01", "2024-01-05")

        assert result.ticker == "KCEL"
        assert mock_yahoo.get_prices.call_count == 2  # probe + fetch
        calls = mock_yahoo.get_prices.call_args_list
        assert calls[0].args[0] == "KCEL.ME"
        assert calls[1].args[0] == "KCEL.ME"


# ── Financials delegation tests ───────────────────────────────────


class TestFinancialsDelegation:
    async def test_get_financials_delegates_to_yahoo(self) -> None:
        """When Yahoo is available, financials are fetched via Yahoo."""
        mock_yahoo = AsyncMock()
        # Probe succeeds on .ME
        mock_yahoo.get_prices.return_value = AsyncMock(
            period="p", prices=[AsyncMock(date="2024-01-02")],
        )
        mock_yahoo.get_financials.return_value = FinancialStatements(
            ticker="KCEL.ME",
            income_statement={"revenue": 500_000},
            balance_sheet={"total_assets": 1_000_000},
            cash_flow={"operating_cash_flow": 200_000},
            income_history=[{"revenue": 400_000}],
            cash_flow_history=[{"operating_cash_flow": 150_000}],
        )

        provider = KASEProvider(yahoo=mock_yahoo)
        result = await provider.get_financials("KCEL")

        assert result.ticker == "KCEL"  # re-tagged with original ticker
        assert result.income_statement == {"revenue": 500_000}
        assert result.balance_sheet == {"total_assets": 1_000_000}
        assert result.cash_flow == {"operating_cash_flow": 200_000}
        assert result.income_history == [{"revenue": 400_000}]
        assert result.cash_flow_history == [{"operating_cash_flow": 150_000}]
        mock_yahoo.get_financials.assert_called_once_with("KCEL.ME")

    async def test_get_financials_no_yahoo_returns_none(self) -> None:
        """Without Yahoo, financials return None fields (backward compat)."""
        provider = KASEProvider()
        result = await provider.get_financials("KCEL")

        assert result.ticker == "KCEL"
        assert result.income_statement is None

    async def test_get_financials_yahoo_fails_returns_none(self) -> None:
        """If Yahoo fails for financials, return None fields gracefully."""
        mock_yahoo = AsyncMock()
        mock_yahoo.get_prices.side_effect = TickerNotFoundError("fail")

        provider = KASEProvider(yahoo=mock_yahoo)
        result = await provider.get_financials("KCEL")

        assert result.ticker == "KCEL"
        assert result.income_statement is None


# ── Enriched metrics tests ────────────────────────────────────────


class TestEnrichedMetrics:
    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_metrics_merges_kase_and_yahoo(self, mock_cls: AsyncMock) -> None:
        """Metrics merge KASE primary fields with Yahoo enrichment."""
        fixture = _load_fixture("kase_share_data.json")
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(fixture)
        mock_cls.return_value.__aenter__.return_value = mock_client

        mock_yahoo = AsyncMock()
        # Yahoo suffix resolves on first call
        mock_yahoo.get_prices.return_value = AsyncMock(
            period="p", prices=[AsyncMock(date="2024-01-02")],
        )
        mock_yahoo.get_metrics.return_value = KeyMetrics(
            ticker="KCEL.ME",
            pe_ratio=13.0,  # Should be overridden by KASE value
            pb_ratio=3.5,   # Should be overridden by KASE value
            market_cap=500e9,  # Should be overridden by KASE value
            dividend_yield=0.03,
            roe=0.25,
            roa=0.12,
            debt_to_equity=0.5,
            enterprise_value=550e9,
            ev_ebitda=8.5,
            fcf_yield=0.06,
            shares_outstanding=1e8,
            current_price=5000.0,
        )

        provider = KASEProvider(yahoo=mock_yahoo)
        result = await provider.get_metrics("KCEL")

        # KASE primary fields
        assert result.ticker == "KCEL"
        assert result.market_cap == 462_000_000_000.0
        assert result.current_price == 4620.0
        assert result.pe_ratio == 12.5
        assert result.pb_ratio == 3.2
        assert result.dividend_yield == 0.045
        # Yahoo enrichment
        assert result.roe == 0.25
        assert result.roa == 0.12
        assert result.debt_to_equity == 0.5
        assert result.enterprise_value == 550e9
        assert result.ev_ebitda == 8.5
        assert result.fcf_yield == 0.06
        assert result.shares_outstanding == 1e8

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_metrics_kase_only_when_yahoo_fails(
        self, mock_cls: AsyncMock,
    ) -> None:
        """When Yahoo is down, still return KASE's 5 fields."""
        fixture = _load_fixture("kase_share_data.json")
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(fixture)
        mock_cls.return_value.__aenter__.return_value = mock_client

        mock_yahoo = AsyncMock()
        mock_yahoo.get_prices.side_effect = ProviderUnavailableError("yahoo", "down")

        provider = KASEProvider(yahoo=mock_yahoo)
        result = await provider.get_metrics("KCEL")

        assert result.ticker == "KCEL"
        assert result.pe_ratio == 12.5
        assert result.market_cap == 462_000_000_000.0
        # Yahoo fields remain None
        assert result.roe is None
        assert result.enterprise_value is None

    @patch("fin_toolkit.providers.kase.httpx.AsyncClient")
    async def test_get_metrics_no_yahoo_provider(self, mock_cls: AsyncMock) -> None:
        """Without Yahoo provider, only KASE fields."""
        fixture = _load_fixture("kase_share_data.json")
        mock_client = AsyncMock()
        mock_client.get.return_value = _mock_response(fixture)
        mock_cls.return_value.__aenter__.return_value = mock_client

        provider = KASEProvider()  # no yahoo
        result = await provider.get_metrics("KCEL")

        assert result.pe_ratio == 12.5
        assert result.roe is None
