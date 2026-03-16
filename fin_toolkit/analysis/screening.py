"""Stock screening pure functions."""

from __future__ import annotations

import re

from fin_toolkit.exceptions import InvalidFilterError
from fin_toolkit.models.financial import KeyMetrics


def compute_quick_score(metrics: KeyMetrics) -> float:
    """Quick valuation score from key metrics only (0-100).

    Scoring breakdown:
      P/E ≤10 → 20pts (linear decay to 0 at P/E=30)
      P/B ≤1.0 → 15pts (linear decay to 0 at P/B=5)
      EV/EBITDA ≤8 → 15pts (linear decay to 0 at EV/EBITDA=20)
      FCF yield ≥5% → 15pts (linear from 0% to 10%)
      D/E ≤0.5 → 15pts (linear decay to 0 at D/E=3)
      Dividend yield ≥3% → 10pts (linear from 0% to 6%)
      ROE ≥15% → 10pts (linear from 0% to 30%)
    """
    score = 0.0

    # P/E: 20 pts max
    if metrics.pe_ratio is not None and metrics.pe_ratio > 0:
        score += max(0.0, min(20.0, 20.0 * (1.0 - (metrics.pe_ratio - 10) / 20)))

    # P/B: 15 pts max
    if metrics.pb_ratio is not None and metrics.pb_ratio > 0:
        score += max(0.0, min(15.0, 15.0 * (1.0 - (metrics.pb_ratio - 1.0) / 4.0)))

    # EV/EBITDA: 15 pts max
    ev_ebitda = metrics.ev_ebitda
    if ev_ebitda is not None and ev_ebitda > 0:
        score += max(0.0, min(15.0, 15.0 * (1.0 - (ev_ebitda - 8) / 12)))

    # FCF yield: 15 pts max
    fcf_yield = metrics.fcf_yield
    if fcf_yield is not None:
        score += max(0.0, min(15.0, 15.0 * fcf_yield / 0.10))

    # D/E: 15 pts max (lower is better)
    if metrics.debt_to_equity is not None and metrics.debt_to_equity >= 0:
        score += max(0.0, min(15.0, 15.0 * (1.0 - (metrics.debt_to_equity - 0.5) / 2.5)))

    # Dividend yield: 10 pts max
    if metrics.dividend_yield is not None:
        score += max(0.0, min(10.0, 10.0 * metrics.dividend_yield / 0.06))

    # ROE: 10 pts max
    if metrics.roe is not None:
        score += max(0.0, min(10.0, 10.0 * metrics.roe / 0.30))

    return max(0.0, min(100.0, score))


# ---------------------------------------------------------------------------
# Screening filters
# ---------------------------------------------------------------------------

_FILTER_RE = re.compile(
    r"^(?P<op><=|>=|<|>|=)(?P<val>[0-9.eE+-]+)$"
    r"|^(?P<lo>[0-9.eE+-]+)\.\.(?P<hi>[0-9.eE+-]+)$"
)

_FILTER_KEYS: frozenset[str] = frozenset({
    "pe_ratio", "pb_ratio", "ev_ebitda", "fcf_yield", "debt_to_equity",
    "dividend_yield", "roe", "roa", "market_cap", "current_price",
})


def parse_filter(expr: str) -> tuple[str, float, float | None]:
    """Parse a filter expression like '<8', '>0.2', '5..15', '>=10'.

    Returns (operator, value1, value2_or_none).
    Raises InvalidFilterError on malformed input.
    """
    expr = expr.strip()
    if not expr:
        raise InvalidFilterError(expr, "empty expression")

    m = _FILTER_RE.match(expr)
    if not m:
        raise InvalidFilterError(expr, "unrecognized format")

    if m.group("op"):
        try:
            return m.group("op"), float(m.group("val")), None
        except ValueError:
            raise InvalidFilterError(expr, "invalid number") from None
    else:
        try:
            return "..", float(m.group("lo")), float(m.group("hi"))
        except ValueError:
            raise InvalidFilterError(expr, "invalid range numbers") from None


def _check_op(op: str, value: float, val1: float, val2: float | None) -> bool:
    """Check if value satisfies the operator condition."""
    if op == "<":
        return value < val1
    if op == ">":
        return value > val1
    if op == "<=":
        return value <= val1
    if op == ">=":
        return value >= val1
    if op == "=":
        return abs(value - val1) < 1e-9
    if op == ".." and val2 is not None:
        return val1 <= value <= val2
    return True


def matches_filters(metrics: KeyMetrics, filters: dict[str, str]) -> bool:
    """Return True if metrics satisfy ALL filter conditions.

    None metric values never match any filter.
    """
    for key, expr in filters.items():
        op, val1, val2 = parse_filter(expr)
        raw = getattr(metrics, key, None)
        if raw is None:
            return False
        value = float(raw)
        if not _check_op(op, value, val1, val2):
            return False
    return True
