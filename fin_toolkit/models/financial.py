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
