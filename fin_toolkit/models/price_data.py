"""Price data models."""

from __future__ import annotations

from pydantic import BaseModel


class PricePoint(BaseModel):
    """A single price point (OHLCV)."""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class PriceData(BaseModel):
    """Historical price data for a ticker."""

    ticker: str
    period: str
    prices: list[PricePoint]
    currency: str = "USD"
