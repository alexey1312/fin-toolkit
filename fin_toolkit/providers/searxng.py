"""SearXNG search provider."""

from __future__ import annotations

import httpx

from fin_toolkit.exceptions import ProviderUnavailableError
from fin_toolkit.models.results import SearchResult


class SearXNGProvider:
    """Search provider backed by a SearXNG instance."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search via SearXNG JSON API."""
        try:
            response = await self._client.get(
                f"{self._base_url}/search",
                params={"q": query, "format": "json", "pageno": 1},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderUnavailableError(
                "SearXNG", f"HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("SearXNG", str(exc)) from exc

        data = response.json()
        raw_results = data.get("results", [])[:max_results]

        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("content", ""),
                published_date=r.get("publishedDate"),
            )
            for r in raw_results
        ]
