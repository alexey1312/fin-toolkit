"""Tests for narrative thesis generation."""

from __future__ import annotations

from fin_toolkit.models.results import (
    AgentResult,
    CatalystItem,
    ConsensusResult,
    FCFWaterfall,
    FundamentalResult,
    InvestmentIdeaResult,
    RiskResult,
    ScenarioValuation,
    TechnicalResult,
)
from fin_toolkit.report.narrative import (
    generate_fcf_narrative,
    generate_target_summary,
    generate_thesis,
)


def _make_idea(
    signal: str = "Bullish",
    score: float = 75.0,
    current_price: float | None = 150.0,
) -> InvestmentIdeaResult:
    """Create a minimal InvestmentIdeaResult for testing."""
    agent = AgentResult(
        signal=signal, score=score, confidence=0.8,
        rationale="Strong fundamentals and growth potential",
        breakdown={"quality": 40, "value": 35}, warnings=[],
    )
    consensus = ConsensusResult(
        agent_results={"buffett": agent},
        agent_errors={},
        consensus_score=score,
        consensus_signal=signal,
        consensus_confidence=0.8,
        agreement=1.0,
        warnings=[],
    )
    fundamentals = FundamentalResult(
        profitability={"roe": 0.15, "roa": 0.08},
        valuation={"pe_ratio": 20.0, "pb_ratio": 3.0},
        stability={"debt_to_equity": 0.5},
        sector_comparison={},
        warnings=[],
    )
    fcf = FCFWaterfall(
        ebitda=10_000_000_000,
        capex=3_000_000_000,
        interest_expense=500_000_000,
        taxes=1_500_000_000,
        fcf=5_000_000_000,
        shares_outstanding=1_000_000_000,
        fcf_per_share=5.0,
    )
    scenarios = [
        ScenarioValuation(label="bull", forward_ebitda=12e9, forward_eps=None,
                          target_ev_ebitda=15.0, target_pe=None,
                          target_price=200.0, upside_pct=33.3),
        ScenarioValuation(label="base", forward_ebitda=10e9, forward_eps=None,
                          target_ev_ebitda=12.0, target_pe=None,
                          target_price=165.0, upside_pct=10.0),
        ScenarioValuation(label="bear", forward_ebitda=8e9, forward_eps=None,
                          target_ev_ebitda=9.0, target_pe=None,
                          target_price=120.0, upside_pct=-20.0),
    ]
    catalysts = [
        CatalystItem(category="buyback", description="$10B buyback announced",
                     sentiment="positive", source_url=None),
    ]
    technical = TechnicalResult(
        rsi=55.0, ema_20=150.0, ema_50=148.0, ema_200=140.0,
        bb_upper=160.0, bb_middle=150.0, bb_lower=140.0,
        macd_line=1.5, macd_signal=1.0, macd_histogram=0.5,
        signals={}, overall_bias="Bullish", warnings=[],
    )
    risk = RiskResult(
        volatility_30d=0.20, volatility_90d=0.22, volatility_252d=0.25,
        var_95=-0.02, var_99=-0.03, warnings=[],
    )
    return InvestmentIdeaResult(
        ticker="AAPL",
        current_price=current_price,
        consensus=consensus,
        fundamentals=fundamentals,
        catalysts=catalysts,
        revenue_cagr_3y=0.08,
        ebitda_cagr_3y=0.10,
        fcf_waterfall=fcf,
        scenarios=scenarios,
        risks=[],
        technical=technical,
        risk=risk,
        price_history=[],
        warnings=[],
    )


class TestGenerateThesis:
    def test_bullish_thesis_contains_signal(self) -> None:
        idea = _make_idea(signal="Bullish", score=75.0)
        thesis = generate_thesis(idea)
        assert "Bullish" in thesis.en or "bullish" in thesis.en.lower()
        assert "Покупать" in thesis.ru or "бычий" in thesis.ru.lower()

    def test_bearish_thesis(self) -> None:
        idea = _make_idea(signal="Bearish", score=25.0)
        thesis = generate_thesis(idea)
        assert "Bearish" in thesis.en or "bearish" in thesis.en.lower()

    def test_thesis_mentions_score(self) -> None:
        idea = _make_idea(score=75.0)
        thesis = generate_thesis(idea)
        assert "75" in thesis.en

    def test_thesis_mentions_catalyst(self) -> None:
        idea = _make_idea()
        thesis = generate_thesis(idea)
        assert "buyback" in thesis.en.lower()

    def test_thesis_with_cagr(self) -> None:
        idea = _make_idea()
        thesis = generate_thesis(idea)
        # Should mention revenue or EBITDA growth
        assert "CAGR" in thesis.en or "growth" in thesis.en.lower() or "%" in thesis.en

    def test_thesis_no_price_graceful(self) -> None:
        idea = _make_idea(current_price=None)
        thesis = generate_thesis(idea)
        assert thesis.en != ""
        assert thesis.ru != ""


class TestGenerateFcfNarrative:
    def test_full_fcf_narrative(self) -> None:
        idea = _make_idea()
        narrative = generate_fcf_narrative(idea)
        assert "EBITDA" in narrative.en
        assert "CAPEX" in narrative.en or "capex" in narrative.en.lower()
        assert "FCF" in narrative.en

    def test_empty_fcf_graceful(self) -> None:
        idea = _make_idea()
        idea.fcf_waterfall = FCFWaterfall(
            ebitda=None, capex=None, interest_expense=None,
            taxes=None, fcf=None, shares_outstanding=None, fcf_per_share=None,
        )
        narrative = generate_fcf_narrative(idea)
        assert narrative.en != ""


class TestGenerateTargetSummary:
    def test_with_scenarios(self) -> None:
        idea = _make_idea()
        summary = generate_target_summary(idea)
        assert "165" in summary.en  # base target
        assert "10.0%" in summary.en or "+10.0%" in summary.en

    def test_no_scenarios_graceful(self) -> None:
        idea = _make_idea()
        idea.scenarios = []
        summary = generate_target_summary(idea)
        assert summary.en != ""
