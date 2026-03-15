"""Financial data models."""

from pydantic import BaseModel


class FinancialStatements(BaseModel):
    """Financial statements from a data provider."""

    ticker: str
    income_statement: dict[str, object] | None
    balance_sheet: dict[str, object] | None
    cash_flow: dict[str, object] | None


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
