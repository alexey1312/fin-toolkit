"""Portfolio data models."""

from __future__ import annotations

from pydantic import BaseModel


class Transaction(BaseModel):
    """A single buy/sell transaction."""

    id: int
    ticker: str
    action: str  # "buy" | "sell"
    shares: float
    price: float
    fee: float
    executed_at: str
    notes: str | None


class Position(BaseModel):
    """Computed position from aggregated transactions."""

    ticker: str
    shares: float
    avg_cost: float
    total_invested: float
    current_price: float | None = None
    market_value: float | None = None
    pnl: float | None = None
    pnl_pct: float | None = None
    weight: float | None = None


class PortfolioSummary(BaseModel):
    """Portfolio with positions and P&L summary."""

    name: str
    currency: str
    positions: list[Position]
    total_invested: float
    total_value: float | None = None
    total_pnl: float | None = None
    total_pnl_pct: float | None = None


class PortfolioPerformance(BaseModel):
    """Performance over a time period."""

    name: str
    period: str
    start_value: float
    end_value: float
    pnl: float
    pnl_pct: float
    transactions_count: int
    ticker_returns: dict[str, float]
