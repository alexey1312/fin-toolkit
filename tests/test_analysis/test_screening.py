"""Tests for screening pure functions."""

from __future__ import annotations

import pytest

from fin_toolkit.analysis.screening import matches_filters, parse_filter
from fin_toolkit.exceptions import InvalidFilterError
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
        assert compute_quick_score(m10) >= compute_quick_score(m11)

    def test_negative_pe_no_points(self) -> None:
        """Negative P/E (losses) earns 0 points for P/E component."""
        from fin_toolkit.analysis.screening import compute_quick_score

        m_neg = _metrics(pe=-5)
        m_good = _metrics(pe=8)
        assert compute_quick_score(m_good) > compute_quick_score(m_neg)


# ---------------------------------------------------------------------------
# parse_filter / matches_filters
# ---------------------------------------------------------------------------


class TestParseFilter:
    def test_less_than(self) -> None:
        op, val1, val2 = parse_filter("<8")
        assert op == "<" and val1 == 8.0 and val2 is None

    def test_greater_than(self) -> None:
        op, val1, val2 = parse_filter(">0.2")
        assert op == ">" and val1 == 0.2

    def test_less_equal(self) -> None:
        op, val1, val2 = parse_filter("<=10")
        assert op == "<=" and val1 == 10.0

    def test_greater_equal(self) -> None:
        op, val1, val2 = parse_filter(">=0.05")
        assert op == ">=" and val1 == 0.05

    def test_equal(self) -> None:
        op, val1, val2 = parse_filter("=5")
        assert op == "=" and val1 == 5.0

    def test_range(self) -> None:
        op, val1, val2 = parse_filter("5..15")
        assert op == ".." and val1 == 5.0 and val2 == 15.0

    def test_invalid_raises(self) -> None:
        with pytest.raises(InvalidFilterError):
            parse_filter("abc")

    def test_empty_raises(self) -> None:
        with pytest.raises(InvalidFilterError):
            parse_filter("")


class TestMatchesFilters:
    def test_single_filter_matches(self) -> None:
        m = _metrics(pe=8.0)
        assert matches_filters(m, {"pe_ratio": "<10"}) is True

    def test_single_filter_no_match(self) -> None:
        m = _metrics(pe=15.0)
        assert matches_filters(m, {"pe_ratio": "<10"}) is False

    def test_range_filter_matches(self) -> None:
        m = _metrics(pe=8.0)
        assert matches_filters(m, {"pe_ratio": "5..15"}) is True

    def test_range_filter_no_match(self) -> None:
        m = _metrics(pe=20.0)
        assert matches_filters(m, {"pe_ratio": "5..15"}) is False

    def test_multiple_filters_all_match(self) -> None:
        m = _metrics(pe=8.0, pb=0.9)
        assert matches_filters(m, {"pe_ratio": "<15", "pb_ratio": "<2"}) is True

    def test_multiple_filters_one_fails(self) -> None:
        m = _metrics(pe=8.0, pb=5.0)
        assert matches_filters(m, {"pe_ratio": "<15", "pb_ratio": "<2"}) is False

    def test_none_value_never_matches(self) -> None:
        m = _metrics(pe=None)
        assert matches_filters(m, {"pe_ratio": "<10"}) is False

    def test_empty_filters_always_matches(self) -> None:
        m = _metrics()
        assert matches_filters(m, {}) is True

    def test_roe_filter(self) -> None:
        m = _metrics(roe=0.18)
        assert matches_filters(m, {"roe": ">0.15"}) is True

    def test_fcf_yield_filter(self) -> None:
        m = _metrics(fcf_yield=0.07)
        assert matches_filters(m, {"fcf_yield": ">=0.05"}) is True
