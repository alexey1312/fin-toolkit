"""Tests for SerperSearchProvider."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from fin_toolkit.exceptions import ProviderConfigError, ProviderUnavailableError
from fin_toolkit.models.results import SearchResult
from fin_toolkit.providers.search_protocol import SearchProvider
from fin_toolkit.providers.serper import SerperSearchProvider


class TestSerperSearchProvider:
    def test_missing_api_key_raises_config_error(self) -> None:
        with pytest.raises(ProviderConfigError, match="API key"):
            SerperSearchProvider(api_key="")

    def test_satisfies_search_protocol(self) -> None:
        provider = SerperSearchProvider(api_key="test-key")
        assert isinstance(provider, SearchProvider)

    async def test_search_returns_results(self) -> None:
        mock_response_data: dict[str, Any] = {
            "organic": [
                {
                    "title": "AAPL Stock Price",
                    "link": "https://finance.example.com/aapl",
                    "snippet": "Current Apple stock price and analysis",
                    "date": "2026-03-14",
                },
                {
                    "title": "Apple News",
                    "link": "https://news.example.com/apple",
                    "snippet": "Latest Apple news",
                },
            ]
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        provider = SerperSearchProvider(api_key="test-key")

        with patch.object(provider._client, "post", AsyncMock(return_value=mock_response)):
            results = await provider.search("AAPL stock", max_results=5)

        assert len(results) == 2
        assert results[0].title == "AAPL Stock Price"
        assert results[0].url == "https://finance.example.com/aapl"
        assert results[1].published_date is None

    async def test_http_error_raises_unavailable(self) -> None:
        provider = SerperSearchProvider(api_key="test-key")

        with patch.object(
            provider._client,
            "post",
            side_effect=httpx.HTTPStatusError(
                "403",
                request=httpx.Request("POST", "https://google.serper.dev/search"),
                response=httpx.Response(403),
            ),
        ), pytest.raises(ProviderUnavailableError, match="Serper"):
            await provider.search("fail query")
