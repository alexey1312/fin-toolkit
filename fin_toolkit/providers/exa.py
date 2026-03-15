"""Exa AI semantic search provider."""

from __future__ import annotations

import httpx

from fin_toolkit.exceptions import ProviderConfigError, ProviderUnavailableError
from fin_toolkit.models.results import SearchResult

_EXA_API_URL = "https://api.exa.ai/search"


class ExaSearchProvider:
    """Search provider backed by the Exa AI semantic search API."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ProviderConfigError("Exa API key is required")
        self._client = httpx.AsyncClient(
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search via Exa and return results."""
        payload = {
            "query": query,
            "numResults": max_results,
            "type": "neural",
        }
        try:
            response = await self._client.post(_EXA_API_URL, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderUnavailableError(
                "Exa", f"HTTP {exc.response.status_code}",
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("Exa", str(exc)) from exc

        data = response.json()
        raw_results = data.get("results", [])

        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("text", r.get("summary", "")),
                published_date=r.get("publishedDate"),
            )
            for r in raw_results
        ]
