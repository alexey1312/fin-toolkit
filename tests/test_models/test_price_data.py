"""Tests for PricePoint and PriceData models."""

import pytest
from pydantic import ValidationError

from fin_toolkit.models.price_data import PriceData, PricePoint


class TestPricePoint:
    def test_create_valid(self) -> None:
        pp = PricePoint(
            date="2024-01-02",
            open=150.0,
            high=155.0,
            low=148.0,
            close=152.0,
            volume=1_000_000,
        )
        assert pp.date == "2024-01-02"
        assert pp.close == 152.0
        assert pp.volume == 1_000_000

    def test_model_dump(self) -> None:
        pp = PricePoint(
            date="2024-01-02",
            open=150.0,
            high=155.0,
            low=148.0,
            close=152.0,
            volume=1_000_000,
        )
        d = pp.model_dump()
        assert isinstance(d, dict)
        assert d["close"] == 152.0

    def test_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            PricePoint(  # type: ignore[call-arg]
                date="2024-01-02",
                open=150.0,
                high=155.0,
                low=148.0,
                # missing close
                volume=1_000_000,
            )


class TestPriceData:
    def test_create_with_prices(self) -> None:
        pp = PricePoint(
            date="2024-01-02",
            open=150.0,
            high=155.0,
            low=148.0,
            close=152.0,
            volume=1_000_000,
        )
        pd = PriceData(ticker="AAPL", period="1y", prices=[pp])
        assert pd.ticker == "AAPL"
        assert len(pd.prices) == 1

    def test_empty_prices(self) -> None:
        pd = PriceData(ticker="AAPL", period="1y", prices=[])
        assert pd.prices == []

    def test_model_dump_json_compatible(self) -> None:
        pp = PricePoint(
            date="2024-01-02",
            open=150.0,
            high=155.0,
            low=148.0,
            close=152.0,
            volume=1_000_000,
        )
        pd = PriceData(ticker="AAPL", period="1y", prices=[pp])
        d = pd.model_dump()
        assert isinstance(d, dict)
        assert d["ticker"] == "AAPL"
        assert isinstance(d["prices"], list)
        assert d["prices"][0]["close"] == 152.0

    def test_currency_defaults_to_usd(self) -> None:
        pd = PriceData(ticker="AAPL", period="1y", prices=[])
        assert pd.currency == "USD"

    def test_currency_kzt_preserved(self) -> None:
        pd = PriceData(ticker="KCEL", period="1d", prices=[], currency="KZT")
        assert pd.currency == "KZT"

    def test_currency_in_model_dump(self) -> None:
        pd = PriceData(ticker="SBER", period="1y", prices=[], currency="RUB")
        d = pd.model_dump()
        assert d["currency"] == "RUB"
