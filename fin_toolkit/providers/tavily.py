"""Tavily Search API provider."""

from __future__ import annotations

import httpx

from fin_toolkit.exceptions import ProviderConfigError, ProviderUnavailableError
from fin_toolkit.models.results import SearchResult

_TAVILY_API_URL = "https://api.tavily.com/search"


class TavilySearchProvider:
    """Search provider backed by the Tavily Search API."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ProviderConfigError("Tavily API key is required")
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search via Tavily and return results."""
        payload = {
            "api_key": self._api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
        }
        try:
            response = await self._client.post(_TAVILY_API_URL, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderUnavailableError(
                "Tavily", f"HTTP {exc.response.status_code}",
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("Tavily", str(exc)) from exc

        data = response.json()
        raw_results = data.get("results", [])

        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("content", ""),
                published_date=r.get("published_date"),
            )
            for r in raw_results
        ]
