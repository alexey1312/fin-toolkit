"""Financial data models."""

from __future__ import annotations

from pydantic import BaseModel


class FinancialStatements(BaseModel):
    """Financial statements from a data provider."""

    ticker: str
    income_statement: dict[str, object] | None
    balance_sheet: dict[str, object] | None
    cash_flow: dict[str, object] | None
    income_history: list[dict[str, object]] | None = None
    cash_flow_history: list[dict[str, object]] | None = None


class KeyMetrics(BaseModel):
    """Raw summary metrics from a data provider (not computed analysis)."""

    ticker: str
    pe_ratio: float | None
    pb_ratio: float | None
    market_cap: float | None
    dividend_yield: float | None
    roe: float | None
    roa: float | None
    debt_to_equity: float | None
    enterprise_value: float | None = None
    ev_ebitda: float | None = None
    fcf_yield: float | None = None
    shares_outstanding: float | None = None
    current_price: float | None = None


class EarningsEntry(BaseModel):
    """A single earnings period (quarterly)."""

    period: str  # e.g. "2025-Q4", "2025-12-31"
    eps_estimate: float | None
    eps_actual: float | None
    surprise_pct: float | None
    revenue_estimate: float | None = None
    revenue_actual: float | None = None


class AnalystEstimates(BaseModel):
    """Wall Street analyst consensus estimates and ratings."""

    ticker: str
    # Target prices
    target_low: float | None
    target_median: float | None
    target_high: float | None
    target_mean: float | None
    # Ratings
    recommendation: str | None  # "buy", "hold", "sell", "strong_buy", etc.
    recommendation_score: float | None  # 1.0 (strong buy) to 5.0 (sell)
    num_analysts: int | None
    # Forward estimates
    forward_pe: float | None = None
    forward_eps: float | None = None
    # Earnings history
    earnings_history: list[EarningsEntry] | None = None
