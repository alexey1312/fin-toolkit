"""Google Search provider via Gemini API with Search Grounding."""

from __future__ import annotations

import httpx

from fin_toolkit.exceptions import ProviderConfigError, ProviderUnavailableError
from fin_toolkit.models.results import SearchResult

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
_DEFAULT_MODEL = "gemini-3.1-flash-lite"


class GoogleSearchProvider:
    """Search provider backed by Gemini API with Google Search grounding.

    Sends a query to Gemini with the google_search tool enabled.
    Returns grounding chunks (cited URLs) as SearchResult objects.
    """

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        if not api_key:
            raise ProviderConfigError("Google (Gemini) API key is required")
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search via Gemini with Google Search grounding."""
        payload = {
            "contents": [{"parts": [{"text": query}]}],
            "tools": [{"google_search": {}}],
        }
        url = f"{_GEMINI_BASE_URL}/{self._model}:generateContent?key={self._api_key}"
        try:
            response = await self._client.post(url, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderUnavailableError(
                "Google", f"HTTP {exc.response.status_code}",
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("Google", str(exc)) from exc

        data = response.json()
        candidate = data.get("candidates", [{}])[0]
        content = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
        grounding = candidate.get("groundingMetadata", {})
        chunks = grounding.get("groundingChunks", [])

        results: list[SearchResult] = []
        for chunk in chunks[:max_results]:
            web = chunk.get("web", {})
            uri = web.get("uri", "")
            if not uri:
                continue
            results.append(
                SearchResult(
                    title=web.get("title", "") or uri.split("/")[-1] or uri,
                    url=uri,
                    snippet=content[:200] if content else "",
                    published_date=None,
                ),
            )
        return results
