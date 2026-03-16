"""Provider router with market-based routing and fallback chain."""

from __future__ import annotations

import asyncio

from fin_toolkit.config.models import ToolkitConfig
from fin_toolkit.exceptions import (
    AllProvidersFailedError,
    ProviderUnavailableError,
    TickerNotFoundError,
)
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData
from fin_toolkit.providers.protocol import DataProvider


class ProviderRouter:
    """Routes requests to providers based on market mapping and fallback chain.

    Resolution order:
    1. Explicit `provider` parameter
    2. Market mapping from config (e.g. KZ tickers → KASE)
    3. Primary → fallback chain
    """

    def __init__(
        self,
        config: ToolkitConfig,
        providers: dict[str, DataProvider],
    ) -> None:
        self._config = config
        self._providers = providers
        self._dynamic_tickers: dict[str, set[str]] | None = None
        self._dynamic_lock = asyncio.Lock()

    async def _ensure_dynamic_tickers(self) -> None:
        """Lazily populate dynamic ticker sets from providers with list_tickers()."""
        if self._dynamic_tickers is not None:
            return
        async with self._dynamic_lock:
            if self._dynamic_tickers is not None:
                return  # another coroutine filled it while we waited
            result: dict[str, set[str]] = {}
            for market_cfg in self._config.markets.values():
                prov = self._providers.get(market_cfg.provider)
                if prov and hasattr(prov, "list_tickers") and not market_cfg.tickers:
                    tickers = await prov.list_tickers()
                    result[market_cfg.provider] = set(tickers)
            self._dynamic_tickers = result

    def _resolve_chain(self, ticker: str, provider: str | None = None) -> list[str]:
        """Build ordered list of provider names to try."""
        if provider:
            return [provider]

        chain: list[str] = []

        # Check static market mapping
        mapped = self._config.get_ticker_provider(ticker)

        # Check dynamic tickers if no static mapping found
        if not mapped and self._dynamic_tickers:
            for prov_name, ticker_set in self._dynamic_tickers.items():
                if ticker in ticker_set:
                    mapped = prov_name
                    break

        if mapped and mapped in self._providers:
            chain.append(mapped)

        # Primary provider
        primary = self._config.data.primary_provider
        if primary in self._providers and primary not in chain:
            chain.append(primary)

        # Fallback providers
        for fb in self._config.data.fallback_providers:
            if fb in self._providers and fb not in chain:
                chain.append(fb)

        return chain

    async def get_prices(
        self,
        ticker: str,
        start: str,
        end: str,
        provider: str | None = None,
    ) -> PriceData:
        """Get prices, trying providers in resolution order."""
        await self._ensure_dynamic_tickers()
        chain = self._resolve_chain(ticker, provider)
        errors: dict[str, str] = {}

        for name in chain:
            try:
                return await self._providers[name].get_prices(ticker, start, end)
            except (TickerNotFoundError, ProviderUnavailableError) as exc:
                errors[name] = str(exc)

        raise AllProvidersFailedError(errors)

    async def get_financials(
        self,
        ticker: str,
        provider: str | None = None,
    ) -> FinancialStatements:
        """Get financials, trying providers in resolution order."""
        await self._ensure_dynamic_tickers()
        chain = self._resolve_chain(ticker, provider)
        errors: dict[str, str] = {}

        for name in chain:
            try:
                return await self._providers[name].get_financials(ticker)
            except (TickerNotFoundError, ProviderUnavailableError) as exc:
                errors[name] = str(exc)

        raise AllProvidersFailedError(errors)

    async def get_metrics(
        self,
        ticker: str,
        provider: str | None = None,
    ) -> KeyMetrics:
        """Get metrics, trying providers in resolution order."""
        await self._ensure_dynamic_tickers()
        chain = self._resolve_chain(ticker, provider)
        errors: dict[str, str] = {}

        for name in chain:
            try:
                return await self._providers[name].get_metrics(ticker)
            except (TickerNotFoundError, ProviderUnavailableError) as exc:
                errors[name] = str(exc)

        raise AllProvidersFailedError(errors)
