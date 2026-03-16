"""Tests for DuckDuckGoSearchProvider."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from fin_toolkit.exceptions import ProviderUnavailableError
from fin_toolkit.models.results import SearchResult
from fin_toolkit.providers.duckduckgo import DuckDuckGoSearchProvider
from fin_toolkit.providers.search_protocol import SearchProvider


class TestDuckDuckGoSearchProvider:
    def test_satisfies_search_protocol(self) -> None:
        provider = DuckDuckGoSearchProvider()
        assert isinstance(provider, SearchProvider)

    async def test_search_returns_news_results(self) -> None:
        mock_news = [
            {
                "title": "AAPL Earnings Beat",
                "url": "https://finance.example.com/aapl",
                "body": "Apple stock analysis",
                "date": "2026-03-15T10:00:00+00:00",
            },
            {
                "title": "AAPL News",
                "url": "https://news.example.com/aapl",
                "body": "Latest Apple news",
                "date": "2026-03-14T08:00:00+00:00",
            },
        ]

        provider = DuckDuckGoSearchProvider()

        with patch(
            "fin_toolkit.providers.duckduckgo.asyncio.to_thread",
            return_value=mock_news,
        ):
            results = await provider.search("AAPL stock", max_results=5)

        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].title == "AAPL Earnings Beat"
        assert results[0].url == "https://finance.example.com/aapl"
        assert results[0].snippet == "Apple stock analysis"
        assert results[0].published_date is not None

    async def test_news_empty_falls_back_to_text(self) -> None:
        """When news returns empty, falls back to text search."""
        mock_text = [
            {
                "title": "AAPL Page",
                "href": "https://example.com/aapl",
                "body": "Apple info",
            },
        ]
        provider = DuckDuckGoSearchProvider()
        call_count = 0

        async def mock_to_thread(fn: object, *args: object, **kwargs: object) -> list[object]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return []  # news returns empty
            return mock_text  # text fallback

        with patch(
            "fin_toolkit.providers.duckduckgo.asyncio.to_thread",
            side_effect=mock_to_thread,
        ):
            results = await provider.search("nothing trending")

        assert len(results) == 1
        assert results[0].published_date is None

    async def test_search_handles_empty_results(self) -> None:
        """Both news and text return empty."""
        provider = DuckDuckGoSearchProvider()

        with patch(
            "fin_toolkit.providers.duckduckgo.asyncio.to_thread",
            return_value=[],
        ):
            results = await provider.search("nothing")

        assert results == []

    async def test_search_error_raises_unavailable(self) -> None:
        provider = DuckDuckGoSearchProvider()

        with patch(
            "fin_toolkit.providers.duckduckgo.asyncio.to_thread",
            side_effect=Exception("Rate limited"),
        ), pytest.raises(ProviderUnavailableError, match="DuckDuckGo"):
            await provider.search("fail query")
