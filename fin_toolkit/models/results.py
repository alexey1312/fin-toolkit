"""Analysis result models."""

from pydantic import BaseModel


class TechnicalResult(BaseModel):
    """Result of technical analysis."""

    rsi: float | None
    ema_20: float | None
    ema_50: float | None
    ema_200: float | None
    bb_upper: float | None
    bb_middle: float | None
    bb_lower: float | None
    macd_line: float | None
    macd_signal: float | None
    macd_histogram: float | None
    signals: dict[str, str]
    overall_bias: str
    warnings: list[str]


class FundamentalResult(BaseModel):
    """Result of fundamental analysis."""

    profitability: dict[str, float | None]
    valuation: dict[str, float | None]
    stability: dict[str, float | None]
    sector_comparison: dict[str, str | None]
    warnings: list[str]


class RiskResult(BaseModel):
    """Result of risk analysis for a single ticker."""

    volatility_30d: float | None
    volatility_90d: float | None
    volatility_252d: float | None
    var_95: float | None
    var_99: float | None
    warnings: list[str]


class CorrelationResult(BaseModel):
    """Correlation matrix for multiple tickers."""

    tickers: list[str]
    matrix: dict[str, dict[str, float]]
    warnings: list[str]


class AgentResult(BaseModel):
    """Result from an analysis agent."""

    signal: str  # "Bullish" | "Neutral" | "Bearish"
    score: float  # 0-100
    confidence: float  # 0.0-1.0
    rationale: str
    breakdown: dict[str, float]
    warnings: list[str]


class SearchResult(BaseModel):
    """A single search result."""

    title: str
    url: str
    snippet: str
    published_date: str | None
