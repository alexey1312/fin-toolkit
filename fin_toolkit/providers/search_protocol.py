"""SearchProvider protocol definition."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fin_toolkit.models.results import SearchResult


@runtime_checkable
class SearchProvider(Protocol):
    """Async protocol for web search providers."""

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search for a query and return results."""
        ...
