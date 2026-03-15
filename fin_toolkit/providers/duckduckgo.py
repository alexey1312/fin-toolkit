"""DuckDuckGo search provider (no API key required)."""

from __future__ import annotations

import asyncio

from fin_toolkit.exceptions import ProviderUnavailableError
from fin_toolkit.models.results import SearchResult


class DuckDuckGoSearchProvider:
    """Search provider using the duckduckgo-search library. No API key needed."""

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search DuckDuckGo and return results."""
        try:
            from ddgs import DDGS

            ddgs = DDGS()
            raw = await asyncio.to_thread(
                ddgs.text, query, max_results=max_results,
            )
        except Exception as exc:
            raise ProviderUnavailableError("DuckDuckGo", str(exc)) from exc

        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("href", ""),
                snippet=r.get("body", ""),
                published_date=None,
            )
            for r in raw
        ]
