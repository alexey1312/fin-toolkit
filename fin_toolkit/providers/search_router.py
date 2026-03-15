"""Search router with fallback chain."""

from __future__ import annotations

import logging

from fin_toolkit.models.results import SearchResult
from fin_toolkit.providers.search_protocol import SearchProvider

logger = logging.getLogger(__name__)


class SearchRouter:
    """Tries search providers in order, falling back on failure."""

    def __init__(self, providers: list[SearchProvider]) -> None:
        self._providers = providers

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search using the first available provider; return [] if all fail."""
        for provider in self._providers:
            try:
                return await provider.search(query, max_results=max_results)
            except Exception:
                logger.debug(
                    "Search provider %s failed, trying next",
                    type(provider).__name__,
                    exc_info=True,
                )
                continue
        return []
