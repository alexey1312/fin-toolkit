"""Tests for DuckDuckGoSearchProvider."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from fin_toolkit.exceptions import ProviderUnavailableError
from fin_toolkit.models.results import SearchResult
from fin_toolkit.providers.duckduckgo import DuckDuckGoSearchProvider
from fin_toolkit.providers.search_protocol import SearchProvider


class TestDuckDuckGoSearchProvider:
    def test_satisfies_search_protocol(self) -> None:
        provider = DuckDuckGoSearchProvider()
        assert isinstance(provider, SearchProvider)

    async def test_search_returns_results(self) -> None:
        mock_results = [
            {
                "title": "AAPL Stock",
                "href": "https://finance.example.com/aapl",
                "body": "Apple stock analysis",
            },
            {
                "title": "AAPL News",
                "href": "https://news.example.com/aapl",
                "body": "Latest Apple news",
            },
        ]

        provider = DuckDuckGoSearchProvider()

        with patch("fin_toolkit.providers.duckduckgo.asyncio.to_thread", return_value=mock_results):
            results = await provider.search("AAPL stock", max_results=5)

        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].title == "AAPL Stock"
        assert results[0].url == "https://finance.example.com/aapl"
        assert results[0].snippet == "Apple stock analysis"

    async def test_search_handles_empty_results(self) -> None:
        provider = DuckDuckGoSearchProvider()

        with patch("fin_toolkit.providers.duckduckgo.asyncio.to_thread", return_value=[]):
            results = await provider.search("nothing")

        assert results == []

    async def test_search_error_raises_unavailable(self) -> None:
        provider = DuckDuckGoSearchProvider()

        with patch(
            "fin_toolkit.providers.duckduckgo.asyncio.to_thread",
            side_effect=Exception("Rate limited"),
        ), pytest.raises(ProviderUnavailableError, match="DuckDuckGo"):
            await provider.search("fail query")
