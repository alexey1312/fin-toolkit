"""Tests for TavilySearchProvider."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from fin_toolkit.exceptions import ProviderConfigError, ProviderUnavailableError
from fin_toolkit.providers.search_protocol import SearchProvider
from fin_toolkit.providers.tavily import TavilySearchProvider


class TestTavilySearchProvider:
    def test_missing_api_key_raises_config_error(self) -> None:
        with pytest.raises(ProviderConfigError, match="API key"):
            TavilySearchProvider(api_key="")

    def test_satisfies_search_protocol(self) -> None:
        provider = TavilySearchProvider(api_key="test-key")
        assert isinstance(provider, SearchProvider)

    async def test_search_returns_results(self) -> None:
        mock_response_data: dict[str, Any] = {
            "results": [
                {
                    "title": "AAPL Earnings",
                    "url": "https://finance.example.com/aapl",
                    "content": "Apple beat earnings expectations",
                    "published_date": "2026-03-10",
                },
            ]
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        provider = TavilySearchProvider(api_key="test-key")

        with patch.object(provider._client, "post", AsyncMock(return_value=mock_response)):
            results = await provider.search("AAPL earnings", max_results=5)

        assert len(results) == 1
        assert results[0].title == "AAPL Earnings"
        assert results[0].snippet == "Apple beat earnings expectations"
        assert results[0].published_date == "2026-03-10"

    async def test_search_handles_empty_results(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()

        provider = TavilySearchProvider(api_key="test-key")

        with patch.object(provider._client, "post", AsyncMock(return_value=mock_response)):
            results = await provider.search("nothing")

        assert results == []

    async def test_http_error_raises_unavailable(self) -> None:
        provider = TavilySearchProvider(api_key="test-key")

        with patch.object(
            provider._client,
            "post",
            side_effect=httpx.HTTPStatusError(
                "401",
                request=httpx.Request("POST", "https://api.tavily.com/search"),
                response=httpx.Response(401),
            ),
        ), pytest.raises(ProviderUnavailableError, match="Tavily"):
            await provider.search("fail query")
