"""Shared test fixtures for fin-toolkit."""

from datetime import datetime

import pytest


@pytest.fixture
def mock_price_points() -> list[dict[str, object]]:
    """Raw price point data for creating PriceData fixtures."""
    return [
        {
            "date": datetime(2024, 1, 2 + i),
            "open": 150.0 + i,
            "high": 155.0 + i,
            "low": 148.0 + i,
            "close": 152.0 + i,
            "volume": 1_000_000 + i * 10_000,
        }
        for i in range(60)
    ]


@pytest.fixture
def mock_financials_data() -> dict[str, object]:
    """Raw financial statements data."""
    return {
        "ticker": "AAPL",
        "revenue": 383_285_000_000,
        "net_income": 96_995_000_000,
        "total_assets": 352_583_000_000,
        "total_liabilities": 290_437_000_000,
        "total_equity": 62_146_000_000,
        "operating_cash_flow": 110_543_000_000,
        "capital_expenditures": -10_959_000_000,
        "free_cash_flow": 99_584_000_000,
        "ebitda": 125_820_000_000,
    }


@pytest.fixture
def mock_metrics_data() -> dict[str, object]:
    """Raw key metrics data."""
    return {
        "ticker": "AAPL",
        "market_cap": 2_900_000_000_000,
        "pe_ratio": 29.5,
        "pb_ratio": 46.7,
        "ps_ratio": 7.6,
        "ev_to_ebitda": 23.1,
        "dividend_yield": 0.005,
        "roe": 1.56,
        "roa": 0.275,
        "roic": 0.55,
        "debt_to_equity": 4.67,
        "current_ratio": 0.99,
        "fcf_yield": 0.034,
    }
