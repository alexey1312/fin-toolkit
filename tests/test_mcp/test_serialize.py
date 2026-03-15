"""Tests for MCP response serialization (JSON / TOON)."""

from __future__ import annotations

import json

import pytest

from fin_toolkit.mcp_server.serialize import serialize


class TestSerializeJson:
    def test_roundtrip(self) -> None:
        """json.loads(serialize(data, 'json')) == data."""
        data = {"ticker": "AAPL", "prices": [{"date": "2024-01-01", "close": 150.0}]}
        result = serialize(data, "json")
        assert json.loads(result) == data

    def test_none_values(self) -> None:
        """None values survive JSON round-trip."""
        data = {"volatility_30d": None, "var_95": 0.02}
        result = serialize(data, "json")
        parsed = json.loads(result)
        assert parsed["volatility_30d"] is None
        assert parsed["var_95"] == 0.02


class TestSerializeToon:
    def test_not_json(self) -> None:
        """TOON output is NOT valid JSON."""
        data = {"ticker": "AAPL", "prices": [{"date": "2024-01-01", "close": 150.0}]}
        result = serialize(data, "toon")
        with pytest.raises(json.JSONDecodeError):
            json.loads(result)

    def test_roundtrip(self) -> None:
        """toon.decode(serialize(data, 'toon')) == data."""
        from toon_format import decode

        data = {"ticker": "AAPL", "price": 150.0, "volume": 1_000_000}
        result = serialize(data, "toon")
        assert decode(result) == data

    def test_tabular_array(self) -> None:
        """List of PricePoint-like dicts encodes correctly."""
        from toon_format import decode

        data = {
            "ticker": "AAPL",
            "prices": [
                {"date": "2024-01-01", "open": 100.0, "close": 102.0, "volume": 1000},
                {"date": "2024-01-02", "open": 102.0, "close": 105.0, "volume": 2000},
                {"date": "2024-01-03", "open": 105.0, "close": 103.0, "volume": 1500},
            ],
        }
        result = serialize(data, "toon")
        assert decode(result) == data

    def test_none_values(self) -> None:
        """None values survive TOON round-trip."""
        from toon_format import decode

        data = {"volatility_30d": None, "var_95": 0.02, "warnings": []}
        result = serialize(data, "toon")
        assert decode(result) == data


class TestSerializeUnsupported:
    def test_unknown_format_raises(self) -> None:
        """Unknown format raises ValueError."""
        with pytest.raises(ValueError, match="xml"):
            serialize({"a": 1}, "xml")
