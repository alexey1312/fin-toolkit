"""Tests for search providers and search router."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from fin_toolkit.exceptions import ProviderConfigError, ProviderUnavailableError
from fin_toolkit.models.results import SearchResult
from fin_toolkit.providers.search_protocol import SearchProvider
from fin_toolkit.providers.search_router import SearchRouter

# ---------------------------------------------------------------------------
# SearchProvider protocol compliance
# ---------------------------------------------------------------------------


class MockSearchProvider:
    """A mock class that satisfies the SearchProvider protocol."""

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return [
            SearchResult(
                title="Mock",
                url="https://example.com",
                snippet="mock snippet",
                published_date=None,
            )
        ]


class IncompleteSearchProvider:
    """Missing the search method — should NOT satisfy the protocol."""

    async def lookup(self, query: str) -> list[SearchResult]:  # wrong name
        return []


class TestSearchProviderProtocol:
    def test_protocol_is_runtime_checkable(self) -> None:
        provider = MockSearchProvider()
        assert isinstance(provider, SearchProvider)

    def test_incomplete_provider_fails(self) -> None:
        provider = IncompleteSearchProvider()
        assert not isinstance(provider, SearchProvider)


# ---------------------------------------------------------------------------
# BraveSearchProvider
# ---------------------------------------------------------------------------


class TestBraveSearchProvider:
    def test_missing_api_key_raises_config_error(self) -> None:
        from fin_toolkit.providers.brave import BraveSearchProvider

        with pytest.raises(ProviderConfigError, match="API key"):
            BraveSearchProvider(api_key="")

    async def test_search_returns_results(self) -> None:
        from fin_toolkit.providers.brave import BraveSearchProvider

        mock_response_data: dict[str, Any] = {
            "web": {
                "results": [
                    {
                        "title": "AAPL Stock",
                        "url": "https://finance.example.com/aapl",
                        "description": "Apple Inc stock analysis",
                        "age": "2026-03-10",
                    },
                    {
                        "title": "AAPL News",
                        "url": "https://news.example.com/aapl",
                        "description": "Latest Apple news",
                        "age": None,
                    },
                ]
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        provider = BraveSearchProvider(api_key="test-key-123")

        mock_get = AsyncMock(return_value=mock_response)
        with patch.object(provider._client, "get", mock_get):
            results = await provider.search("AAPL stock", max_results=5)

        mock_get.assert_called_once()
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].title == "AAPL Stock"
        assert results[0].url == "https://finance.example.com/aapl"
        assert results[0].snippet == "Apple Inc stock analysis"
        assert results[1].published_date is None

    async def test_search_handles_empty_response(self) -> None:
        from fin_toolkit.providers.brave import BraveSearchProvider

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        provider = BraveSearchProvider(api_key="test-key")

        with patch.object(provider._client, "get", AsyncMock(return_value=mock_response)):
            results = await provider.search("nothing")

        assert results == []

    async def test_search_http_error_raises_unavailable(self) -> None:
        from fin_toolkit.providers.brave import BraveSearchProvider

        provider = BraveSearchProvider(api_key="test-key")

        with patch.object(
            provider._client,
            "get",
            side_effect=httpx.HTTPStatusError(
                "503",
                request=httpx.Request("GET", "https://api.search.brave.com"),
                response=httpx.Response(503),
            ),
        ), pytest.raises(ProviderUnavailableError, match="Brave"):
            await provider.search("fail query")


# ---------------------------------------------------------------------------
# SearXNGProvider
# ---------------------------------------------------------------------------


class TestSearXNGProvider:
    async def test_search_returns_results(self) -> None:
        from fin_toolkit.providers.searxng import SearXNGProvider

        mock_response_data: dict[str, Any] = {
            "results": [
                {
                    "title": "SearX Result",
                    "url": "https://example.com/searx",
                    "content": "Found via SearXNG",
                    "publishedDate": "2026-03-12",
                },
            ]
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        provider = SearXNGProvider(base_url="http://localhost:8080")

        mock_get = AsyncMock(return_value=mock_response)
        with patch.object(provider._client, "get", mock_get):
            results = await provider.search("test query", max_results=5)

        mock_get.assert_called_once()
        assert len(results) == 1
        assert results[0].title == "SearX Result"
        assert results[0].snippet == "Found via SearXNG"
        assert results[0].published_date == "2026-03-12"

    async def test_unavailable_raises_error(self) -> None:
        from fin_toolkit.providers.searxng import SearXNGProvider

        provider = SearXNGProvider(base_url="http://localhost:8080")

        with patch.object(
            provider._client,
            "get",
            side_effect=httpx.ConnectError("Connection refused"),
        ), pytest.raises(ProviderUnavailableError, match="SearXNG"):
            await provider.search("fail query")

    async def test_search_handles_empty_results(self) -> None:
        from fin_toolkit.providers.searxng import SearXNGProvider

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()

        provider = SearXNGProvider(base_url="http://localhost:8080")

        with patch.object(provider._client, "get", AsyncMock(return_value=mock_response)):
            results = await provider.search("empty")

        assert results == []


# ---------------------------------------------------------------------------
# SearchRouter
# ---------------------------------------------------------------------------


class TestSearchRouter:
    async def test_primary_succeeds(self) -> None:
        primary = AsyncMock(spec=MockSearchProvider)
        primary.search.return_value = [
            SearchResult(
                title="Primary", url="https://p.com", snippet="from primary", published_date=None
            )
        ]

        router = SearchRouter(providers=[primary])
        results = await router.search("test")

        assert len(results) == 1
        assert results[0].title == "Primary"
        primary.search.assert_called_once_with("test", max_results=10)

    async def test_primary_fails_fallback_succeeds(self) -> None:
        primary = AsyncMock(spec=MockSearchProvider)
        primary.search.side_effect = ProviderUnavailableError("primary", "down")

        fallback = AsyncMock(spec=MockSearchProvider)
        fallback.search.return_value = [
            SearchResult(
                title="Fallback",
                url="https://f.com",
                snippet="from fallback",
                published_date=None,
            )
        ]

        router = SearchRouter(providers=[primary, fallback])
        results = await router.search("test")

        assert len(results) == 1
        assert results[0].title == "Fallback"
        primary.search.assert_called_once()
        fallback.search.assert_called_once()

    async def test_no_providers_returns_empty(self) -> None:
        router = SearchRouter(providers=[])
        results = await router.search("anything")

        assert results == []

    async def test_all_providers_fail_returns_empty(self) -> None:
        p1 = AsyncMock(spec=MockSearchProvider)
        p1.search.side_effect = ProviderUnavailableError("p1", "down")

        p2 = AsyncMock(spec=MockSearchProvider)
        p2.search.side_effect = ProviderUnavailableError("p2", "down")

        router = SearchRouter(providers=[p1, p2])
        results = await router.search("test")

        assert results == []
