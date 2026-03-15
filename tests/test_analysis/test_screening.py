"""Tests for screening pure functions."""

from __future__ import annotations

import pytest

from fin_toolkit.models.financial import KeyMetrics


def _metrics(
    pe: float | None = 8.0,
    pb: float | None = 0.9,
    ev_ebitda: float | None = 6.0,
    fcf_yield: float | None = 0.07,
    de: float | None = 0.3,
    div_yield: float | None = 0.04,
    roe: float | None = 0.18,
    **kwargs: object,
) -> KeyMetrics:
    return KeyMetrics(
        ticker=str(kwargs.get("ticker", "TEST")),
        pe_ratio=pe,
        pb_ratio=pb,
        market_cap=1_000_000_000,
        dividend_yield=div_yield,
        roe=roe,
        roa=0.10,
        debt_to_equity=de,
        enterprise_value=10_000_000_000,
        ev_ebitda=ev_ebitda,
        fcf_yield=fcf_yield,
    )


# ---------------------------------------------------------------------------
# compute_quick_score
# ---------------------------------------------------------------------------


class TestComputeQuickScore:
    def test_perfect_value_stock(self) -> None:
        """A stock meeting all value criteria scores high (>80)."""
        from fin_toolkit.analysis.screening import compute_quick_score

        m = _metrics(pe=8, pb=0.8, ev_ebitda=6, fcf_yield=0.07, de=0.3, div_yield=0.04, roe=0.18)
        score = compute_quick_score(m)
        assert score > 80.0

    def test_extreme_value_stock_hits_100(self) -> None:
        """Extremely cheap stock hits maximum 100."""
        from fin_toolkit.analysis.screening import compute_quick_score

        m = _metrics(pe=3, pb=0.3, ev_ebitda=3, fcf_yield=0.15, de=0.1, div_yield=0.08, roe=0.35)
        score = compute_quick_score(m)
        assert score == 100.0

    def test_expensive_growth_stock(self) -> None:
        """An expensive growth stock scores low."""
        from fin_toolkit.analysis.screening import compute_quick_score

        m = _metrics(pe=50, pb=10.0, ev_ebitda=25, fcf_yield=0.01, de=2.0, div_yield=0.0, roe=0.05)
        score = compute_quick_score(m)
        assert score < 20.0

    def test_all_none_scores_zero(self) -> None:
        """All None metrics score 0."""
        from fin_toolkit.analysis.screening import compute_quick_score

        m = KeyMetrics(
            ticker="NONE",
            pe_ratio=None,
            pb_ratio=None,
            market_cap=None,
            dividend_yield=None,
            roe=None,
            roa=None,
            debt_to_equity=None,
        )
        score = compute_quick_score(m)
        assert score == 0.0

    def test_score_between_0_and_100(self) -> None:
        """Score is always in [0, 100]."""
        from fin_toolkit.analysis.screening import compute_quick_score

        m = _metrics(pe=15, pb=1.5, ev_ebitda=10, fcf_yield=0.03, de=0.8, div_yield=0.02, roe=0.12)
        score = compute_quick_score(m)
        assert 0 <= score <= 100

    def test_pe_threshold_boundary(self) -> None:
        """P/E exactly 10 earns points, P/E of 11 earns partial."""
        from fin_toolkit.analysis.screening import compute_quick_score

        m10 = _metrics(pe=10)
        m11 = _metrics(pe=11)
        from fin_toolkit.analysis.screening import compute_quick_score
        assert compute_quick_score(m10) >= compute_quick_score(m11)

    def test_negative_pe_no_points(self) -> None:
        """Negative P/E (losses) earns 0 points for P/E component."""
        from fin_toolkit.analysis.screening import compute_quick_score

        m_neg = _metrics(pe=-5)
        m_good = _metrics(pe=8)
        assert compute_quick_score(m_good) > compute_quick_score(m_neg)
