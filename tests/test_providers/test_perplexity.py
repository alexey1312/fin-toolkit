"""Tests for PerplexitySearchProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from fin_toolkit.exceptions import ProviderConfigError, ProviderUnavailableError
from fin_toolkit.models.results import SearchResult
from fin_toolkit.providers.perplexity import PerplexitySearchProvider
from fin_toolkit.providers.search_protocol import SearchProvider


class TestPerplexitySearchProvider:
    def test_missing_api_key_raises_config_error(self) -> None:
        with pytest.raises(ProviderConfigError, match="API key"):
            PerplexitySearchProvider(api_key="")

    def test_satisfies_search_protocol(self) -> None:
        provider = PerplexitySearchProvider(api_key="test-key")
        assert isinstance(provider, SearchProvider)

    async def test_search_returns_results_from_citations(self) -> None:
        mock_response_data = {
            "citations": [
                "https://finance.example.com/aapl-earnings",
                "https://news.example.com/aapl-q1",
            ],
            "choices": [
                {
                    "message": {
                        "content": "Apple reported strong Q1 earnings with revenue of $130B.",
                    }
                }
            ],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        provider = PerplexitySearchProvider(api_key="test-key-123")

        mock_post = AsyncMock(return_value=mock_response)
        with patch.object(provider._client, "post", mock_post):
            results = await provider.search("AAPL earnings", max_results=5)

        mock_post.assert_called_once()
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].url == "https://finance.example.com/aapl-earnings"
        assert results[1].url == "https://news.example.com/aapl-q1"
        assert "Apple reported" in results[0].snippet

    async def test_search_handles_empty_citations(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "No info."}}]}
        mock_response.raise_for_status = MagicMock()

        provider = PerplexitySearchProvider(api_key="test-key")

        with patch.object(provider._client, "post", AsyncMock(return_value=mock_response)):
            results = await provider.search("nothing")

        assert results == []

    async def test_search_respects_max_results(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "citations": [f"https://example.com/{i}" for i in range(10)],
            "choices": [{"message": {"content": "Many results"}}],
        }
        mock_response.raise_for_status = MagicMock()

        provider = PerplexitySearchProvider(api_key="test-key")

        with patch.object(provider._client, "post", AsyncMock(return_value=mock_response)):
            results = await provider.search("test", max_results=3)

        assert len(results) == 3

    async def test_http_error_raises_unavailable(self) -> None:
        provider = PerplexitySearchProvider(api_key="test-key")

        with patch.object(
            provider._client,
            "post",
            side_effect=httpx.HTTPStatusError(
                "401",
                request=httpx.Request("POST", "https://api.perplexity.ai/chat/completions"),
                response=httpx.Response(401),
            ),
        ), pytest.raises(ProviderUnavailableError, match="Perplexity"):
            await provider.search("fail query")

    async def test_connection_error_raises_unavailable(self) -> None:
        provider = PerplexitySearchProvider(api_key="test-key")

        with patch.object(
            provider._client,
            "post",
            side_effect=httpx.ConnectError("Connection refused"),
        ), pytest.raises(ProviderUnavailableError, match="Perplexity"):
            await provider.search("fail query")
