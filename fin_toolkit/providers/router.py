"""Provider router with market-based routing and fallback chain."""

from __future__ import annotations

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

    def _resolve_chain(self, ticker: str, provider: str | None = None) -> list[str]:
        """Build ordered list of provider names to try."""
        if provider:
            return [provider]

        chain: list[str] = []

        # Check market mapping
        mapped = self._config.get_ticker_provider(ticker)
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
        chain = self._resolve_chain(ticker, provider)
        errors: dict[str, str] = {}

        for name in chain:
            try:
                return await self._providers[name].get_metrics(ticker)
            except (TickerNotFoundError, ProviderUnavailableError) as exc:
                errors[name] = str(exc)

        raise AllProvidersFailedError(errors)
