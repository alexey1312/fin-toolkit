"""Tests for GoogleSearchProvider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from fin_toolkit.exceptions import ProviderConfigError, ProviderUnavailableError
from fin_toolkit.models.results import SearchResult
from fin_toolkit.providers.google import GoogleSearchProvider
from fin_toolkit.providers.search_protocol import SearchProvider


def _make_gemini_response(
    text: str = "Summary text",
    chunks: list[dict[str, str]] | None = None,
) -> dict:
    """Build a mock Gemini API response with grounding metadata."""
    if chunks is None:
        chunks = []
    return {
        "candidates": [
            {
                "content": {"parts": [{"text": text}]},
                "groundingMetadata": {
                    "groundingChunks": [
                        {"web": {"uri": c["uri"], "title": c.get("title", "")}}
                        for c in chunks
                    ],
                },
            }
        ],
    }


class TestGoogleSearchProvider:
    def test_missing_api_key_raises_config_error(self) -> None:
        with pytest.raises(ProviderConfigError, match="API key"):
            GoogleSearchProvider(api_key="")

    def test_satisfies_search_protocol(self) -> None:
        provider = GoogleSearchProvider(api_key="test-key")
        assert isinstance(provider, SearchProvider)

    async def test_search_returns_results_from_grounding_chunks(self) -> None:
        response_data = _make_gemini_response(
            text="Apple reported strong Q1 earnings.",
            chunks=[
                {"uri": "https://finance.example.com/aapl", "title": "AAPL Earnings"},
                {"uri": "https://news.example.com/aapl-q1", "title": "Apple Q1"},
            ],
        )

        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        provider = GoogleSearchProvider(api_key="test-key-123")
        with patch.object(provider._client, "post", AsyncMock(return_value=mock_response)):
            results = await provider.search("AAPL earnings", max_results=5)

        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].url == "https://finance.example.com/aapl"
        assert results[0].title == "AAPL Earnings"
        assert results[1].url == "https://news.example.com/aapl-q1"
        assert "Apple reported" in results[0].snippet

    async def test_search_handles_no_grounding_metadata(self) -> None:
        response_data = {
            "candidates": [
                {
                    "content": {"parts": [{"text": "Some answer without grounding."}]},
                }
            ],
        }

        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        provider = GoogleSearchProvider(api_key="test-key")
        with patch.object(provider._client, "post", AsyncMock(return_value=mock_response)):
            results = await provider.search("nothing")

        assert results == []

    async def test_search_respects_max_results(self) -> None:
        response_data = _make_gemini_response(
            text="Many results",
            chunks=[{"uri": f"https://example.com/{i}", "title": f"Result {i}"} for i in range(10)],
        )

        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        provider = GoogleSearchProvider(api_key="test-key")
        with patch.object(provider._client, "post", AsyncMock(return_value=mock_response)):
            results = await provider.search("test", max_results=3)

        assert len(results) == 3

    async def test_http_error_raises_unavailable(self) -> None:
        provider = GoogleSearchProvider(api_key="test-key")

        with patch.object(
            provider._client,
            "post",
            side_effect=httpx.HTTPStatusError(
                "403",
                request=httpx.Request("POST", "https://generativelanguage.googleapis.com/"),
                response=httpx.Response(403),
            ),
        ), pytest.raises(ProviderUnavailableError, match="Google"):
            await provider.search("fail query")

    async def test_connection_error_raises_unavailable(self) -> None:
        provider = GoogleSearchProvider(api_key="test-key")

        with patch.object(
            provider._client,
            "post",
            side_effect=httpx.ConnectError("Connection refused"),
        ), pytest.raises(ProviderUnavailableError, match="Google"):
            await provider.search("fail query")

    async def test_sends_correct_payload(self) -> None:
        response_data = _make_gemini_response(chunks=[])

        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        provider = GoogleSearchProvider(api_key="test-key")
        mock_post = AsyncMock(return_value=mock_response)
        with patch.object(provider._client, "post", mock_post):
            await provider.search("AAPL news")

        call_args = mock_post.call_args
        url = call_args[0][0]
        payload = call_args[1]["json"]

        assert "key=test-key" in url
        assert "gemini-" in url
        assert payload["contents"] == [{"parts": [{"text": "AAPL news"}]}]
        assert {"google_search": {}} in payload["tools"]

    async def test_custom_model(self) -> None:
        response_data = _make_gemini_response(chunks=[])

        mock_response = MagicMock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = MagicMock()

        provider = GoogleSearchProvider(api_key="test-key", model="gemini-3.1-flash-lite")
        mock_post = AsyncMock(return_value=mock_response)
        with patch.object(provider._client, "post", mock_post):
            await provider.search("test")

        url = mock_post.call_args[0][0]
        assert "gemini-3.1-flash-lite" in url
