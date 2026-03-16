"""Alert evaluation pure functions."""

from __future__ import annotations

from dataclasses import dataclass, field

from fin_toolkit.models.financial import KeyMetrics
from fin_toolkit.models.results import AlertTriggered, RiskResult, TechnicalResult


@dataclass
class AlertRule:
    """A single alert rule definition."""

    metric: str
    operator: str  # "<", ">", "<=", ">=", "="
    threshold: float
    label: str | None = None


@dataclass
class WatchlistEntry:
    """A single watchlist entry with optional alerts."""

    ticker: str
    added_at: str
    notes: str | None = None
    alerts: list[AlertRule] = field(default_factory=list)


# Metrics sourced from RiskResult
_RISK_METRICS: frozenset[str] = frozenset({
    "volatility_30d", "volatility_90d", "volatility_252d", "var_95", "var_99",
})

# Metrics sourced from TechnicalResult
_TECHNICAL_METRICS: frozenset[str] = frozenset({
    "rsi", "ema_20", "ema_50", "ema_200", "macd_line", "macd_signal",
})


def _get_metric_value(
    metric: str,
    metrics: KeyMetrics | None,
    risk: RiskResult | None,
    technical: TechnicalResult | None,
) -> float | None:
    """Extract a metric value from the appropriate source."""
    if metric in _RISK_METRICS and risk is not None:
        val = getattr(risk, metric, None)
        return float(val) if val is not None else None
    if metric in _TECHNICAL_METRICS and technical is not None:
        val = getattr(technical, metric, None)
        return float(val) if val is not None else None
    if metrics is not None:
        val = getattr(metrics, metric, None)
        return float(val) if val is not None else None
    return None


def _check_condition(value: float, operator: str, threshold: float) -> bool:
    """Evaluate a single condition."""
    if operator == "<":
        return value < threshold
    if operator == ">":
        return value > threshold
    if operator == "<=":
        return value <= threshold
    if operator == ">=":
        return value >= threshold
    if operator == "=":
        return abs(value - threshold) < 1e-9
    return False


def evaluate_alerts(
    entry: WatchlistEntry,
    metrics: KeyMetrics | None,
    risk: RiskResult | None,
    technical: TechnicalResult | None,
) -> list[AlertTriggered]:
    """Evaluate all alerts for a watchlist entry.

    Returns a list of triggered alerts. None metric values are skipped.
    """
    triggered: list[AlertTriggered] = []
    for alert in entry.alerts:
        value = _get_metric_value(alert.metric, metrics, risk, technical)
        if value is None:
            continue
        if _check_condition(value, alert.operator, alert.threshold):
            triggered.append(AlertTriggered(
                ticker=entry.ticker,
                metric=alert.metric,
                operator=alert.operator,
                threshold=alert.threshold,
                current_value=value,
                label=alert.label,
            ))
    return triggered
