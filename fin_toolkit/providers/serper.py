"""Serper (Google Search) API provider."""

from __future__ import annotations

import httpx

from fin_toolkit.exceptions import ProviderConfigError, ProviderUnavailableError
from fin_toolkit.models.results import SearchResult

_SERPER_API_URL = "https://google.serper.dev/search"


class SerperSearchProvider:
    """Search provider backed by the Serper Google Search API."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ProviderConfigError("Serper API key is required")
        self._client = httpx.AsyncClient(
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search via Serper and return results."""
        payload = {"q": query, "num": max_results}
        try:
            response = await self._client.post(_SERPER_API_URL, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderUnavailableError(
                "Serper", f"HTTP {exc.response.status_code}",
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("Serper", str(exc)) from exc

        data = response.json()
        raw_results = data.get("organic", [])

        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("link", ""),
                snippet=r.get("snippet", ""),
                published_date=r.get("date"),
            )
            for r in raw_results[:max_results]
        ]
