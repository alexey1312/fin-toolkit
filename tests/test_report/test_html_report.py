"""Tests for HTML report generator."""

from __future__ import annotations

from fin_toolkit.models.results import (
    AgentResult,
    CatalystItem,
    ConsensusResult,
    FCFWaterfall,
    FundamentalResult,
    InvestmentIdeaResult,
    RiskItem,
    RiskResult,
    ScenarioValuation,
    TechnicalResult,
)


def _make_idea_result() -> InvestmentIdeaResult:
    agent_result = AgentResult(
        signal="Bullish", score=75.0, confidence=0.8,
        rationale="Strong fundamentals", breakdown={"quality": 80.0}, warnings=[],
    )
    consensus = ConsensusResult(
        agent_results={"buffett": agent_result},
        agent_errors={},
        consensus_score=75.0,
        consensus_signal="Bullish",
        consensus_confidence=0.8,
        agreement=1.0,
        warnings=[],
    )
    fundamentals = FundamentalResult(
        profitability={"roe": 0.15, "roa": 0.08},
        valuation={"pe_ratio": 12.0, "pb_ratio": 1.5},
        stability={"debt_to_equity": 0.5},
        sector_comparison={},
        warnings=[],
    )
    technical = TechnicalResult(
        rsi=55.0, ema_20=150.0, ema_50=148.0, ema_200=140.0,
        bb_upper=160.0, bb_middle=150.0, bb_lower=140.0,
        macd_line=1.5, macd_signal=1.0, macd_histogram=0.5,
        signals={"rsi": "neutral", "macd": "bullish"},
        overall_bias="Bullish", warnings=[],
    )
    risk = RiskResult(
        volatility_30d=0.2, volatility_90d=0.22, volatility_252d=0.25,
        var_95=-0.02, var_99=-0.03, warnings=[],
    )
    fcf = FCFWaterfall(
        ebitda=1_000_000, capex=200_000, interest_expense=50_000,
        taxes=187_500, fcf=562_500, shares_outstanding=100_000, fcf_per_share=5.625,
    )
    scenarios = [
        ScenarioValuation(
            label="bull", forward_ebitda=1_300_000, forward_eps=None,
            target_ev_ebitda=8.0, target_pe=None,
            target_price=150.0, upside_pct=50.0,
        ),
        ScenarioValuation(
            label="base", forward_ebitda=1_100_000, forward_eps=None,
            target_ev_ebitda=8.0, target_pe=None,
            target_price=120.0, upside_pct=20.0,
        ),
        ScenarioValuation(
            label="bear", forward_ebitda=900_000, forward_eps=None,
            target_ev_ebitda=8.0, target_pe=None,
            target_price=90.0, upside_pct=-10.0,
        ),
    ]
    catalysts = [
        CatalystItem(category="m_and_a", description="Potential acquisition",
                     sentiment="positive", source_url="https://example.com"),
    ]
    risks = [
        RiskItem(category="leverage", description="High D/E ratio", severity="medium"),
    ]
    price_history = [
        {"date": f"2024-01-{i + 1:02d}", "close": 100.0 + i, "volume": 1000000}
        for i in range(30)
    ]

    return InvestmentIdeaResult(
        ticker="TEST",
        current_price=100.0,
        consensus=consensus,
        fundamentals=fundamentals,
        catalysts=catalysts,
        revenue_cagr_3y=0.12,
        ebitda_cagr_3y=0.15,
        fcf_waterfall=fcf,
        scenarios=scenarios,
        risks=risks,
        technical=technical,
        risk=risk,
        price_history=price_history,
        warnings=[],
    )


class TestRenderHTML:
    def test_produces_valid_html(self) -> None:
        from fin_toolkit.report.html_report import render_investment_idea_html

        html = render_investment_idea_html(_make_idea_result())
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html

    def test_contains_ticker(self) -> None:
        from fin_toolkit.report.html_report import render_investment_idea_html

        html = render_investment_idea_html(_make_idea_result())
        assert "TEST" in html

    def test_contains_plotly_script(self) -> None:
        from fin_toolkit.report.html_report import render_investment_idea_html

        html = render_investment_idea_html(_make_idea_result())
        assert "plotly" in html.lower()

    def test_contains_all_sections(self) -> None:
        from fin_toolkit.report.html_report import render_investment_idea_html

        html = render_investment_idea_html(_make_idea_result())
        assert "Price Chart" in html
        assert "Agent Consensus" in html
        assert "Fundamental Snapshot" in html
        assert "FCF Waterfall" in html
        assert "Scenario Valuation" in html
        assert "Catalysts" in html
        assert "Risk Catalog" in html
        assert "Technical Signals" in html
        assert "disclaimer" in html.lower()

    def test_consensus_badges(self) -> None:
        from fin_toolkit.report.html_report import render_investment_idea_html

        html = render_investment_idea_html(_make_idea_result())
        assert "badge-bullish" in html
        assert "75" in html  # consensus score

    def test_scenario_values(self) -> None:
        from fin_toolkit.report.html_report import render_investment_idea_html

        html = render_investment_idea_html(_make_idea_result())
        assert "BULL" in html
        assert "BASE" in html
        assert "BEAR" in html
