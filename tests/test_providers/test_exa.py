"""Tests for ExaSearchProvider."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from fin_toolkit.exceptions import ProviderConfigError, ProviderUnavailableError
from fin_toolkit.models.results import SearchResult
from fin_toolkit.providers.exa import ExaSearchProvider
from fin_toolkit.providers.search_protocol import SearchProvider


class TestExaSearchProvider:
    def test_missing_api_key_raises_config_error(self) -> None:
        with pytest.raises(ProviderConfigError, match="API key"):
            ExaSearchProvider(api_key="")

    def test_satisfies_search_protocol(self) -> None:
        provider = ExaSearchProvider(api_key="test-key")
        assert isinstance(provider, SearchProvider)

    async def test_search_returns_results(self) -> None:
        mock_response_data: dict[str, Any] = {
            "results": [
                {
                    "title": "AAPL Deep Analysis",
                    "url": "https://research.example.com/aapl",
                    "text": "Semantic analysis of Apple stock performance",
                    "publishedDate": "2026-03-12",
                },
            ]
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        provider = ExaSearchProvider(api_key="test-key")

        with patch.object(provider._client, "post", AsyncMock(return_value=mock_response)):
            results = await provider.search("AAPL analysis", max_results=5)

        assert len(results) == 1
        assert results[0].title == "AAPL Deep Analysis"
        assert results[0].snippet == "Semantic analysis of Apple stock performance"
        assert results[0].published_date == "2026-03-12"

    async def test_search_handles_empty_results(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()

        provider = ExaSearchProvider(api_key="test-key")

        with patch.object(provider._client, "post", AsyncMock(return_value=mock_response)):
            results = await provider.search("nothing")

        assert results == []

    async def test_http_error_raises_unavailable(self) -> None:
        provider = ExaSearchProvider(api_key="test-key")

        with patch.object(
            provider._client,
            "post",
            side_effect=httpx.HTTPStatusError(
                "401",
                request=httpx.Request("POST", "https://api.exa.ai/search"),
                response=httpx.Response(401),
            ),
        ), pytest.raises(ProviderUnavailableError, match="Exa"):
            await provider.search("fail query")
