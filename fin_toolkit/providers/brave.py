"""Brave Search API provider."""

from __future__ import annotations

import httpx

from fin_toolkit.exceptions import ProviderConfigError, ProviderUnavailableError
from fin_toolkit.models.results import SearchResult

_BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"


class BraveSearchProvider:
    """Search provider backed by the Brave Search API."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ProviderConfigError("Brave Search API key is required")
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": api_key,
            },
            timeout=30.0,
        )

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search Brave and return a list of SearchResult."""
        try:
            response = await self._client.get(
                _BRAVE_API_URL,
                params={"q": query, "count": max_results},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderUnavailableError(
                "Brave", f"HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("Brave", str(exc)) from exc

        data = response.json()
        raw_results = data.get("web", {}).get("results", [])

        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("description", ""),
                published_date=r.get("age"),
            )
            for r in raw_results
        ]
