"""Tests for ProviderRouter."""

from unittest.mock import AsyncMock

import pytest

from fin_toolkit.config.models import (
    DataConfig,
    MarketConfig,
    RateLimitConfig,
    ToolkitConfig,
)
from fin_toolkit.exceptions import AllProvidersFailedError, ProviderUnavailableError
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData, PricePoint
from fin_toolkit.providers.protocol import DataProvider
from fin_toolkit.providers.router import ProviderRouter


def _make_price_data(ticker: str, source: str = "") -> PriceData:
    return PriceData(
        ticker=ticker,
        period=f"from_{source}",
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


def _make_financials(ticker: str) -> FinancialStatements:
    return FinancialStatements(
        ticker=ticker,
        income_statement={"revenue": 1_000_000},
        balance_sheet=None,
        cash_flow=None,
    )


def _make_metrics(ticker: str) -> KeyMetrics:
    return KeyMetrics(
        ticker=ticker,
        pe_ratio=15.0,
        pb_ratio=None,
        market_cap=1e9,
        dividend_yield=None,
        roe=None,
        roa=None,
        debt_to_equity=None,
    )


def _make_provider(name: str, fail: bool = False) -> AsyncMock:
    provider = AsyncMock(spec=DataProvider)
    if fail:
        provider.get_prices.side_effect = ProviderUnavailableError(name, "down")
        provider.get_financials.side_effect = ProviderUnavailableError(name, "down")
        provider.get_metrics.side_effect = ProviderUnavailableError(name, "down")
    else:
        provider.get_prices.return_value = _make_price_data("AAPL", name)
        provider.get_financials.return_value = _make_financials("AAPL")
        provider.get_metrics.return_value = _make_metrics("AAPL")
    return provider


def _make_config() -> ToolkitConfig:
    return ToolkitConfig(
        data=DataConfig(primary_provider="yahoo", fallback_providers=["fmp"]),
        markets={
            "kz": MarketConfig(provider="kase", tickers=["KCEL", "KZTO", "HSBK"]),
        },
        rate_limits={
            "yahoo": RateLimitConfig(requests_per_minute=60, max_concurrent=5),
            "kase": RateLimitConfig(requests_per_minute=60, max_concurrent=5),
            "fmp": RateLimitConfig(requests_per_minute=60, max_concurrent=5),
        },
    )


class TestProviderRouter:
    async def test_primary_succeeds(self) -> None:
        config = _make_config()
        yahoo = _make_provider("yahoo")
        router = ProviderRouter(config=config, providers={"yahoo": yahoo})

        result = await router.get_prices("AAPL", "2024-01-01", "2024-12-31")
        assert result.ticker == "AAPL"
        assert result.period == "from_yahoo"
        yahoo.get_prices.assert_called_once_with("AAPL", "2024-01-01", "2024-12-31")

    async def test_primary_fails_fallback_succeeds(self) -> None:
        config = _make_config()
        yahoo = _make_provider("yahoo", fail=True)
        fmp = _make_provider("fmp")
        router = ProviderRouter(config=config, providers={"yahoo": yahoo, "fmp": fmp})

        result = await router.get_prices("AAPL", "2024-01-01", "2024-12-31")
        assert result.period == "from_fmp"

    async def test_all_providers_fail(self) -> None:
        config = _make_config()
        yahoo = _make_provider("yahoo", fail=True)
        fmp = _make_provider("fmp", fail=True)
        router = ProviderRouter(config=config, providers={"yahoo": yahoo, "fmp": fmp})

        with pytest.raises(AllProvidersFailedError):
            await router.get_prices("AAPL", "2024-01-01", "2024-12-31")

    async def test_market_mapping_kz_ticker(self) -> None:
        config = _make_config()
        yahoo = _make_provider("yahoo")
        kase = _make_provider("kase")
        kase.get_prices.return_value = _make_price_data("KCEL", "kase")
        router = ProviderRouter(
            config=config, providers={"yahoo": yahoo, "kase": kase}
        )

        result = await router.get_prices("KCEL", "2024-01-01", "2024-12-31")
        assert result.period == "from_kase"
        kase.get_prices.assert_called_once()

    async def test_explicit_provider_override(self) -> None:
        config = _make_config()
        yahoo = _make_provider("yahoo")
        fmp = _make_provider("fmp")
        fmp.get_prices.return_value = _make_price_data("AAPL", "fmp")
        router = ProviderRouter(
            config=config, providers={"yahoo": yahoo, "fmp": fmp}
        )

        result = await router.get_prices(
            "AAPL", "2024-01-01", "2024-12-31", provider="fmp"
        )
        assert result.period == "from_fmp"
        yahoo.get_prices.assert_not_called()

    async def test_unknown_ticker_fallback_chain(self) -> None:
        config = _make_config()
        yahoo = _make_provider("yahoo")
        router = ProviderRouter(config=config, providers={"yahoo": yahoo})

        result = await router.get_prices("UNKNOWN", "2024-01-01", "2024-12-31")
        assert result.ticker == "AAPL"  # from mock
        yahoo.get_prices.assert_called_once()

    async def test_get_financials_routes(self) -> None:
        config = _make_config()
        yahoo = _make_provider("yahoo")
        router = ProviderRouter(config=config, providers={"yahoo": yahoo})

        result = await router.get_financials("AAPL")
        assert result.ticker == "AAPL"
        yahoo.get_financials.assert_called_once_with("AAPL")

    async def test_get_metrics_routes(self) -> None:
        config = _make_config()
        yahoo = _make_provider("yahoo")
        router = ProviderRouter(config=config, providers={"yahoo": yahoo})

        result = await router.get_metrics("AAPL")
        assert result.ticker == "AAPL"
        yahoo.get_metrics.assert_called_once_with("AAPL")

    async def test_market_mapping_fallback_on_kase_failure(self) -> None:
        """If KASE fails for a KZ ticker, fall back to primary chain."""
        config = _make_config()
        kase = _make_provider("kase", fail=True)
        yahoo = _make_provider("yahoo")
        yahoo.get_prices.return_value = _make_price_data("KCEL", "yahoo")
        router = ProviderRouter(
            config=config, providers={"kase": kase, "yahoo": yahoo}
        )

        result = await router.get_prices("KCEL", "2024-01-01", "2024-12-31")
        assert result.period == "from_yahoo"


class TestDynamicTickers:
    async def test_router_dynamic_kase_ticker(self) -> None:
        """Unknown ticker found in KASE dynamic list routes to kase provider."""
        config = ToolkitConfig(
            data=DataConfig(primary_provider="yahoo", fallback_providers=[]),
            markets={"kz": MarketConfig(provider="kase", tickers=[])},
        )
        kase = _make_provider("kase")
        kase.get_prices.return_value = _make_price_data("AIRA", "kase")
        # Add list_tickers capability
        kase.list_tickers = AsyncMock(return_value=["KCEL", "AIRA", "HSBK"])

        yahoo = _make_provider("yahoo")
        router = ProviderRouter(
            config=config, providers={"kase": kase, "yahoo": yahoo},
        )

        result = await router.get_prices("AIRA", "2024-01-01", "2024-12-31")
        assert result.period == "from_kase"
        kase.get_prices.assert_called_once()

    async def test_router_dynamic_does_not_override_static(self) -> None:
        """Static market mapping still takes priority over dynamic."""
        config = ToolkitConfig(
            data=DataConfig(primary_provider="yahoo", fallback_providers=[]),
            markets={"kz": MarketConfig(provider="kase", tickers=["KCEL"])},
        )
        kase = _make_provider("kase")
        kase.get_prices.return_value = _make_price_data("KCEL", "kase")
        kase.list_tickers = AsyncMock(return_value=["KCEL", "AIRA"])

        router = ProviderRouter(
            config=config, providers={"kase": kase, "yahoo": _make_provider("yahoo")},
        )

        result = await router.get_prices("KCEL", "2024-01-01", "2024-12-31")
        assert result.period == "from_kase"

    async def test_router_dynamic_unknown_ticker_falls_to_primary(self) -> None:
        """Ticker not in any dynamic list falls to primary chain."""
        config = ToolkitConfig(
            data=DataConfig(primary_provider="yahoo", fallback_providers=[]),
            markets={"kz": MarketConfig(provider="kase", tickers=[])},
        )
        kase = _make_provider("kase")
        kase.list_tickers = AsyncMock(return_value=["KCEL"])

        yahoo = _make_provider("yahoo")
        yahoo.get_prices.return_value = _make_price_data("AAPL", "yahoo")

        router = ProviderRouter(
            config=config, providers={"kase": kase, "yahoo": yahoo},
        )

        result = await router.get_prices("AAPL", "2024-01-01", "2024-12-31")
        assert result.period == "from_yahoo"

    async def test_router_dynamic_caches_tickers(self) -> None:
        """Dynamic tickers are fetched once and cached."""
        config = ToolkitConfig(
            data=DataConfig(primary_provider="yahoo", fallback_providers=[]),
            markets={"kz": MarketConfig(provider="kase", tickers=[])},
        )
        kase = _make_provider("kase")
        kase.get_prices.return_value = _make_price_data("AIRA", "kase")
        kase.list_tickers = AsyncMock(return_value=["AIRA"])

        router = ProviderRouter(
            config=config, providers={"kase": kase, "yahoo": _make_provider("yahoo")},
        )

        await router.get_prices("AIRA", "2024-01-01", "2024-12-31")
        await router.get_prices("AIRA", "2024-01-01", "2024-12-31")

        # list_tickers called only once
        kase.list_tickers.assert_called_once()
