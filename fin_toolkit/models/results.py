"""Analysis result models."""

from __future__ import annotations

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


class ConsensusResult(BaseModel):
    """Aggregated result from all active agents."""

    agent_results: dict[str, AgentResult]
    agent_errors: dict[str, str]
    consensus_score: float  # 0-100, confidence-weighted avg
    consensus_signal: str  # "Bullish" | "Neutral" | "Bearish"
    consensus_confidence: float  # 0.0-1.0
    agreement: float  # 0.0-1.0, fraction agreeing with consensus
    warnings: list[str]


class RecommendationResult(BaseModel):
    """Consensus + risk + technical → position sizing."""

    ticker: str
    consensus: ConsensusResult
    risk: RiskResult
    technical: TechnicalResult
    position_size_pct: float  # 0-25% portfolio
    stop_loss_pct: float | None  # % below entry (3-15%)
    recommendation: str  # human-readable summary
    warnings: list[str]


class PortfolioResult(BaseModel):
    """Portfolio-level analysis with correlation adjustment."""

    recommendations: dict[str, RecommendationResult]
    adjusted_sizes: dict[str, float]  # ticker -> adjusted %
    correlation: CorrelationResult
    total_allocation_pct: float  # sum of adjusted_sizes
    warnings: list[str]


class SearchResult(BaseModel):
    """A single search result."""

    title: str
    url: str
    snippet: str
    published_date: str | None


# ---------------------------------------------------------------------------
# Investment idea models
# ---------------------------------------------------------------------------


class ScenarioValuation(BaseModel):
    """Bull/base/bear scenario valuation."""

    label: str  # "bull" | "base" | "bear"
    forward_ebitda: float | None
    forward_eps: float | None
    target_ev_ebitda: float | None
    target_pe: float | None
    target_price: float | None
    upside_pct: float | None


class FCFWaterfall(BaseModel):
    """Free cash flow waterfall decomposition."""

    ebitda: float | None
    capex: float | None
    interest_expense: float | None
    taxes: float | None
    fcf: float | None
    shares_outstanding: float | None
    fcf_per_share: float | None


class CatalystItem(BaseModel):
    """A single catalyst event or driver."""

    category: str  # "m_and_a", "buyback", "restructuring", "index", "strategic"
    description: str
    sentiment: str  # "positive" | "negative" | "neutral"
    source_url: str | None


class RiskItem(BaseModel):
    """A single risk factor."""

    category: str  # "leverage", "liquidity", "regulatory", "esg", "operational", "macro"
    description: str
    severity: str  # "high" | "medium" | "low"


class InvestmentIdeaResult(BaseModel):
    """Complete investment idea with all analysis components."""

    ticker: str
    current_price: float | None
    consensus: ConsensusResult
    fundamentals: FundamentalResult
    catalysts: list[CatalystItem]
    revenue_cagr_3y: float | None
    ebitda_cagr_3y: float | None
    fcf_waterfall: FCFWaterfall
    scenarios: list[ScenarioValuation]
    risks: list[RiskItem]
    technical: TechnicalResult
    risk: RiskResult
    price_history: list[dict[str, object]]
    warnings: list[str]


# ---------------------------------------------------------------------------
# Screening models
# ---------------------------------------------------------------------------


class ScreeningCandidate(BaseModel):
    """A single screening candidate with scores."""

    ticker: str
    quick_score: float  # 0-100
    consensus_score: float | None  # filled for top-N
    consensus_signal: str | None
    key_metrics: dict[str, float | None]


class ScreeningResult(BaseModel):
    """Result of stock screening."""

    market: str | None
    total_scanned: int
    candidates: list[ScreeningCandidate]
    warnings: list[str]
