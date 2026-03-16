"""Stock comparison pure functions."""

from __future__ import annotations

from fin_toolkit.models.results import ComparisonInput, ComparisonResult

DEFAULT_COMPARISON_METRICS: list[str] = [
    "pe_ratio", "pb_ratio", "ev_ebitda", "fcf_yield", "roe", "roa",
    "debt_to_equity", "dividend_yield", "market_cap", "current_price",
    "volatility_30d", "consensus_score", "consensus_signal",
]

# Metrics sourced from RiskResult
_RISK_METRICS: frozenset[str] = frozenset({"volatility_30d"})

# Metrics sourced from ConsensusResult
_CONSENSUS_METRICS: frozenset[str] = frozenset({"consensus_score", "consensus_signal"})


def _extract_value(
    inp: ComparisonInput, metric: str,
) -> float | str | None:
    """Extract a single metric value from ComparisonInput."""
    if metric in _RISK_METRICS:
        if inp.risk is None:
            return None
        return getattr(inp.risk, metric, None)

    if metric in _CONSENSUS_METRICS:
        if inp.consensus is None:
            return None
        return getattr(inp.consensus, metric, None)

    # Default: from key_metrics
    if inp.key_metrics is None:
        return None
    return getattr(inp.key_metrics, metric, None)


def build_comparison_matrix(
    ticker_data: dict[str, ComparisonInput],
    metrics: list[str] | None = None,
) -> ComparisonResult:
    """Build a comparison matrix for multiple tickers.

    Args:
        ticker_data: Dict of ticker -> ComparisonInput.
        metrics: List of metric names to compare (default: DEFAULT_COMPARISON_METRICS).

    Returns:
        ComparisonResult with matrix oriented as {metric: {ticker: value}}.
    """
    metric_list = metrics if metrics is not None else list(DEFAULT_COMPARISON_METRICS)
    tickers = list(ticker_data.keys())
    warnings: list[str] = []

    matrix: dict[str, dict[str, float | str | None]] = {}
    for metric in metric_list:
        row: dict[str, float | str | None] = {}
        all_none = True
        for ticker in tickers:
            inp = ticker_data[ticker]
            val = _extract_value(inp, metric)
            row[ticker] = val
            if val is not None:
                all_none = False
        matrix[metric] = row
        if all_none:
            warnings.append(f"Metric '{metric}' is unavailable for all tickers")

    return ComparisonResult(
        tickers=tickers,
        metrics=metric_list,
        matrix=matrix,
        warnings=warnings,
    )
