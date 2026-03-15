"""Tests for investment idea pure functions."""

from __future__ import annotations

import pytest

from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.results import RiskResult, SearchResult


# ---------------------------------------------------------------------------
# compute_cagr
# ---------------------------------------------------------------------------


class TestComputeCAGR:
    def test_positive_growth(self) -> None:
        from fin_toolkit.analysis.idea import compute_cagr

        # 100 → 200 in 3 years → CAGR ≈ 26%
        result = compute_cagr([100, 130, 160, 200], 3)
        assert result is not None
        assert result == pytest.approx(0.2599, abs=0.01)

    def test_negative_growth(self) -> None:
        from fin_toolkit.analysis.idea import compute_cagr

        # 200 → 100 in 2 years → CAGR ≈ -29%
        result = compute_cagr([200, 150, 100], 2)
        assert result is not None
        assert result < 0

    def test_single_value_returns_none(self) -> None:
        from fin_toolkit.analysis.idea import compute_cagr

        assert compute_cagr([100], 1) is None

    def test_empty_returns_none(self) -> None:
        from fin_toolkit.analysis.idea import compute_cagr

        assert compute_cagr([], 3) is None

    def test_zero_start_returns_none(self) -> None:
        from fin_toolkit.analysis.idea import compute_cagr

        assert compute_cagr([0, 100, 200], 2) is None

    def test_negative_start_returns_none(self) -> None:
        from fin_toolkit.analysis.idea import compute_cagr

        assert compute_cagr([-50, 100, 200], 2) is None

    def test_zero_years_returns_none(self) -> None:
        from fin_toolkit.analysis.idea import compute_cagr

        assert compute_cagr([100, 200], 0) is None

    def test_flat_returns_zero(self) -> None:
        from fin_toolkit.analysis.idea import compute_cagr

        result = compute_cagr([100, 100, 100], 2)
        assert result == pytest.approx(0.0, abs=0.001)


# ---------------------------------------------------------------------------
# compute_fcf_waterfall
# ---------------------------------------------------------------------------


def _financials() -> FinancialStatements:
    return FinancialStatements(
        ticker="TEST",
        income_statement={
            "ebitda": 1_000_000,
            "interest_expense": 50_000,
            "net_income": 600_000,
            "ebit": 800_000,
        },
        balance_sheet={"total_assets": 5_000_000},
        cash_flow={"capital_expenditures": 200_000},
    )


def _key_metrics() -> KeyMetrics:
    return KeyMetrics(
        ticker="TEST",
        pe_ratio=15.0,
        pb_ratio=2.0,
        market_cap=10_000_000,
        dividend_yield=0.02,
        roe=0.12,
        roa=0.08,
        debt_to_equity=0.5,
        shares_outstanding=1_000_000,
    )


class TestComputeFCFWaterfall:
    def test_basic_waterfall(self) -> None:
        from fin_toolkit.analysis.idea import compute_fcf_waterfall

        result = compute_fcf_waterfall(_financials(), _key_metrics())
        assert result.ebitda == 1_000_000
        assert result.capex == 200_000
        assert result.interest_expense == 50_000
        assert result.fcf is not None
        assert result.shares_outstanding == 1_000_000

    def test_fcf_per_share(self) -> None:
        from fin_toolkit.analysis.idea import compute_fcf_waterfall

        result = compute_fcf_waterfall(_financials(), _key_metrics())
        assert result.fcf_per_share is not None
        assert result.fcf_per_share == pytest.approx(
            result.fcf / result.shares_outstanding, abs=0.01,  # type: ignore[operator]
        )

    def test_none_income_statement(self) -> None:
        from fin_toolkit.analysis.idea import compute_fcf_waterfall

        fin = FinancialStatements(
            ticker="TEST",
            income_statement=None,
            balance_sheet=None,
            cash_flow=None,
        )
        result = compute_fcf_waterfall(fin, _key_metrics())
        assert result.ebitda is None
        assert result.fcf is None


# ---------------------------------------------------------------------------
# compute_scenarios
# ---------------------------------------------------------------------------


class TestComputeScenarios:
    def test_three_scenarios(self) -> None:
        from fin_toolkit.analysis.idea import compute_scenarios

        scenarios = compute_scenarios(
            current_price=100.0,
            ebitda=1_000_000,
            ebitda_cagr=0.10,
            ev_ebitda_multiple=8.0,
            ev=8_000_000,
            net_debt=2_000_000,
            shares=1_000_000,
        )
        assert len(scenarios) == 3
        labels = {s.label for s in scenarios}
        assert labels == {"bull", "base", "bear"}

    def test_bull_highest_target(self) -> None:
        from fin_toolkit.analysis.idea import compute_scenarios

        scenarios = compute_scenarios(
            current_price=100.0,
            ebitda=1_000_000,
            ebitda_cagr=0.10,
            ev_ebitda_multiple=8.0,
            ev=8_000_000,
            net_debt=2_000_000,
            shares=1_000_000,
        )
        by_label = {s.label: s for s in scenarios}
        assert by_label["bull"].target_price > by_label["base"].target_price  # type: ignore[operator]
        assert by_label["base"].target_price > by_label["bear"].target_price  # type: ignore[operator]

    def test_upside_relative_to_current(self) -> None:
        from fin_toolkit.analysis.idea import compute_scenarios

        scenarios = compute_scenarios(
            current_price=100.0,
            ebitda=1_000_000,
            ebitda_cagr=0.10,
            ev_ebitda_multiple=8.0,
            ev=8_000_000,
            net_debt=2_000_000,
            shares=1_000_000,
        )
        for s in scenarios:
            if s.target_price is not None and s.upside_pct is not None:
                expected = (s.target_price - 100.0) / 100.0 * 100
                assert s.upside_pct == pytest.approx(expected, abs=0.1)

    def test_none_ebitda_returns_empty(self) -> None:
        from fin_toolkit.analysis.idea import compute_scenarios

        scenarios = compute_scenarios(
            current_price=100.0,
            ebitda=None,
            ebitda_cagr=None,
            ev_ebitda_multiple=None,
            ev=None,
            net_debt=None,
            shares=None,
        )
        assert len(scenarios) == 3
        for s in scenarios:
            assert s.target_price is None


# ---------------------------------------------------------------------------
# classify_catalysts
# ---------------------------------------------------------------------------


class TestClassifyCatalysts:
    def test_merger_keyword(self) -> None:
        from fin_toolkit.analysis.idea import classify_catalysts

        results = [
            SearchResult(
                title="Company announces merger with rival",
                url="https://example.com",
                snippet="Major merger deal announced",
                published_date="2024-01-01",
            ),
        ]
        cats = classify_catalysts(results)
        assert len(cats) >= 1
        assert any(c.category == "m_and_a" for c in cats)

    def test_buyback_keyword(self) -> None:
        from fin_toolkit.analysis.idea import classify_catalysts

        results = [
            SearchResult(
                title="Board approves share buyback program",
                url="https://example.com",
                snippet="$1B buyback announced",
                published_date="2024-01-01",
            ),
        ]
        cats = classify_catalysts(results)
        assert any(c.category == "buyback" for c in cats)

    def test_russian_keywords(self) -> None:
        from fin_toolkit.analysis.idea import classify_catalysts

        results = [
            SearchResult(
                title="Компания объявила о слиянии",
                url="https://example.com",
                snippet="Слияние с конкурентом",
                published_date="2024-01-01",
            ),
        ]
        cats = classify_catalysts(results)
        assert any(c.category == "m_and_a" for c in cats)

    def test_empty_results(self) -> None:
        from fin_toolkit.analysis.idea import classify_catalysts

        assert classify_catalysts([]) == []


# ---------------------------------------------------------------------------
# detect_risks
# ---------------------------------------------------------------------------


class TestDetectRisks:
    def test_high_leverage(self) -> None:
        from fin_toolkit.analysis.idea import detect_risks

        fund = {
            "stability": {"debt_to_equity": 3.0, "current_ratio": 0.5, "interest_coverage": 1.5},
        }
        risk = RiskResult(
            volatility_30d=0.3, volatility_90d=0.3, volatility_252d=0.5,
            var_95=-0.05, var_99=-0.08, warnings=[],
        )
        risks = detect_risks(fund, risk, [])
        assert any(r.category == "leverage" for r in risks)
        assert any(r.severity == "high" for r in risks)

    def test_low_leverage_no_risk(self) -> None:
        from fin_toolkit.analysis.idea import detect_risks

        fund = {
            "stability": {"debt_to_equity": 0.3, "current_ratio": 2.0, "interest_coverage": 10.0},
        }
        risk = RiskResult(
            volatility_30d=0.1, volatility_90d=0.1, volatility_252d=0.15,
            var_95=-0.01, var_99=-0.02, warnings=[],
        )
        risks = detect_risks(fund, risk, [])
        assert not any(r.category == "leverage" for r in risks)

    def test_sanctions_keyword_risk(self) -> None:
        from fin_toolkit.analysis.idea import detect_risks

        results = [
            SearchResult(
                title="New sanctions imposed",
                url="https://example.com",
                snippet="Government sanctions the company",
                published_date="2024-01-01",
            ),
        ]
        fund = {"stability": {}}
        risk = RiskResult(
            volatility_30d=0.2, volatility_90d=0.2, volatility_252d=0.25,
            var_95=-0.02, var_99=-0.03, warnings=[],
        )
        risks = detect_risks(fund, risk, results)
        assert any(r.category == "regulatory" for r in risks)

    def test_high_volatility_risk(self) -> None:
        from fin_toolkit.analysis.idea import detect_risks

        fund = {"stability": {}}
        risk = RiskResult(
            volatility_30d=0.6, volatility_90d=0.6, volatility_252d=0.7,
            var_95=-0.08, var_99=-0.12, warnings=[],
        )
        risks = detect_risks(fund, risk, [])
        assert any(r.category == "macro" for r in risks)
