"""Stock screening pure functions."""

from __future__ import annotations

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
