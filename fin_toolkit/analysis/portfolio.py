"""Portfolio analysis pure functions — consensus, sizing, correlation adjustment."""

from __future__ import annotations

from fin_toolkit.models.results import (
    AgentResult,
    ConsensusResult,
    CorrelationResult,
    RiskResult,
    TechnicalResult,
)


def _signal_from_score(score: float) -> str:
    """Derive signal from a 0-100 score."""
    if score >= 70:
        return "Bullish"
    if score >= 40:
        return "Neutral"
    return "Bearish"


def compute_consensus(
    agent_results: dict[str, AgentResult],
    agent_errors: dict[str, str],
) -> ConsensusResult:
    """Aggregate agent results into a single consensus."""
    if not agent_results:
        return ConsensusResult(
            agent_results={},
            agent_errors=agent_errors,
            consensus_score=0.0,
            consensus_signal="Neutral",
            consensus_confidence=0.0,
            agreement=0.0,
            warnings=[f"Agent '{k}' failed: {v}" for k, v in agent_errors.items()],
        )

    # Confidence-weighted average score
    total_weight = sum(r.confidence for r in agent_results.values())
    weighted_sum = sum(r.score * r.confidence for r in agent_results.values())
    consensus_score = weighted_sum / total_weight if total_weight > 0 else 0.0

    consensus_signal = _signal_from_score(consensus_score)
    consensus_confidence = sum(r.confidence for r in agent_results.values()) / len(
        agent_results
    )

    # Agreement: fraction whose signal matches consensus
    matching = sum(
        1 for r in agent_results.values() if r.signal == consensus_signal
    )
    agreement = matching / len(agent_results)

    warnings: list[str] = [
        f"Agent '{k}' failed: {v}" for k, v in agent_errors.items()
    ]

    return ConsensusResult(
        agent_results=agent_results,
        agent_errors=agent_errors,
        consensus_score=consensus_score,
        consensus_signal=consensus_signal,
        consensus_confidence=consensus_confidence,
        agreement=agreement,
        warnings=warnings,
    )


def compute_position_size(
    consensus: ConsensusResult,
    risk: RiskResult,
    technical: TechnicalResult,
) -> float:
    """Compute position size as % of portfolio (0-25)."""
    # 1. Volatility cap
    vol = risk.volatility_252d
    if vol is None:
        base = 10.0  # conservative default
    elif vol <= 0.20:
        base = 25.0
    elif vol <= 0.40:
        base = 15.0
    elif vol <= 0.60:
        base = 10.0
    else:
        base = 5.0

    # 2. Confidence multiplier
    size = base * consensus.consensus_confidence

    # 3. Signal multiplier
    if consensus.consensus_signal == "Bearish":
        return 0.0
    elif consensus.consensus_signal == "Neutral":
        size *= 0.5
    elif consensus.consensus_score >= 75:
        size *= 1.0
    else:
        size *= 0.8  # Bullish but score 70-74

    # 4. Technical alignment
    if technical.overall_bias == consensus.consensus_signal:
        size *= 1.1
    elif (
        technical.overall_bias != "Neutral"
        and technical.overall_bias != consensus.consensus_signal
    ):
        size *= 0.8

    # Cap at base
    return min(size, base)


def compute_stop_loss(risk: RiskResult, technical: TechnicalResult) -> float | None:
    """Compute stop loss as percentage below entry (3-15%), or None."""
    if risk.var_95 is None:
        return None
    raw = abs(risk.var_95) * 2 * 100  # 2x daily VaR, convert to %
    return max(3.0, min(15.0, raw))


def compute_recommendation_text(
    consensus: ConsensusResult,
    position_size: float,
    risk: RiskResult,
) -> str:
    """Generate a human-readable recommendation summary."""
    n_agents = len(consensus.agent_results)
    n_agree = int(consensus.agreement * n_agents)

    vol_desc = ""
    if risk.volatility_252d is not None:
        vol_pct = risk.volatility_252d * 100
        if vol_pct > 40:
            vol_desc = f" High volatility ({vol_pct:.0f}%)."
        elif vol_pct > 20:
            vol_desc = f" Moderate volatility ({vol_pct:.0f}%)."
        else:
            vol_desc = f" Low volatility ({vol_pct:.0f}%)."

    return (
        f"{consensus.consensus_signal} "
        f"({consensus.consensus_score:.0f}/100, "
        f"{consensus.consensus_confidence:.0%} confidence). "
        f"Position: {position_size:.1f}% portfolio."
        f"{vol_desc} "
        f"{n_agree}/{n_agents} agents agree."
    )


def adjust_position_sizes(
    raw_sizes: dict[str, float],
    correlation: CorrelationResult,
) -> dict[str, float]:
    """Adjust position sizes based on pairwise correlation."""
    if len(raw_sizes) <= 1:
        return dict(raw_sizes)

    adjusted: dict[str, float] = {}
    for ticker, size in raw_sizes.items():
        # Find max pairwise correlation with other tickers in portfolio
        max_corr = 0.0
        for other in raw_sizes:
            if other == ticker:
                continue
            corr_val = abs(correlation.matrix.get(ticker, {}).get(other, 0.0))
            max_corr = max(max_corr, corr_val)

        # Correlation multiplier
        if max_corr >= 0.80:
            mult = 0.70
        elif max_corr >= 0.60:
            mult = 0.85
        elif max_corr >= 0.40:
            mult = 1.00
        elif max_corr >= 0.20:
            mult = 1.05
        else:
            mult = 1.10

        adjusted[ticker] = size * mult

    return adjusted
