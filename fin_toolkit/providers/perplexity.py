"""Perplexity Sonar Search API provider."""

from __future__ import annotations

import httpx

from fin_toolkit.exceptions import ProviderConfigError, ProviderUnavailableError
from fin_toolkit.models.results import SearchResult

_PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


class PerplexitySearchProvider:
    """Search provider backed by the Perplexity Sonar API.

    Uses the sonar model to perform web searches and returns results
    with citations as SearchResult objects.
    """

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ProviderConfigError("Perplexity API key is required")
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search via Perplexity Sonar and return results from citations."""
        payload = {
            "model": "sonar",
            "messages": [{"role": "user", "content": query}],
        }
        try:
            response = await self._client.post(_PERPLEXITY_API_URL, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderUnavailableError(
                "Perplexity", f"HTTP {exc.response.status_code}",
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("Perplexity", str(exc)) from exc

        data = response.json()
        citations: list[str] = data.get("citations", [])
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        results: list[SearchResult] = []
        for url in citations[:max_results]:
            results.append(
                SearchResult(
                    title=url.split("/")[-1] or url,
                    url=url,
                    snippet=content[:200] if content else "",
                    published_date=None,
                ),
            )
        return results
