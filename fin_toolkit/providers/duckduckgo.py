"""DuckDuckGo search provider (no API key required)."""

from __future__ import annotations

import asyncio
import logging

from fin_toolkit.exceptions import ProviderUnavailableError
from fin_toolkit.models.results import SearchResult

logger = logging.getLogger(__name__)


class DuckDuckGoSearchProvider:
    """Search provider using the duckduckgo-search library. No API key needed."""

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search DuckDuckGo News for recent articles with dates.

        Uses ddgs.news() for actual news articles with publication dates.
        Falls back to ddgs.text() if news search fails or returns empty.
        """
        try:
            from ddgs import DDGS

            ddgs = DDGS()

            # Try news first (has dates)
            raw: list[dict[str, str]] = []
            try:
                raw = await asyncio.to_thread(
                    ddgs.news, query, max_results=max_results,
                )
            except Exception:
                logger.debug("ddgs.news() failed for %r, falling back to text", query)

            if raw:
                return [
                    SearchResult(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        snippet=r.get("body", ""),
                        published_date=r.get("date"),
                    )
                    for r in raw
                ]

            # Fallback to text search
            raw = await asyncio.to_thread(
                ddgs.text, query, max_results=max_results,
            )
            return [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                    published_date=None,
                )
                for r in raw
            ]

        except Exception as exc:
            raise ProviderUnavailableError("DuckDuckGo", str(exc)) from exc
