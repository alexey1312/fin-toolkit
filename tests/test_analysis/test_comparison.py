"""Tests for comparison pure functions."""

from __future__ import annotations

from fin_toolkit.analysis.comparison import DEFAULT_COMPARISON_METRICS, build_comparison_matrix
from fin_toolkit.models.financial import KeyMetrics
from fin_toolkit.models.results import (
    AgentResult,
    ComparisonInput,
    ConsensusResult,
    RiskResult,
)


def _make_input(
    ticker: str = "AAPL",
    pe: float = 20.0,
    vol30: float | None = 0.20,
    score: float = 75.0,
) -> ComparisonInput:
    metrics = KeyMetrics(
        ticker=ticker, pe_ratio=pe, pb_ratio=3.0, market_cap=1e9,
        dividend_yield=0.01, roe=0.15, roa=0.08, debt_to_equity=0.5,
        ev_ebitda=12.0, fcf_yield=0.05, current_price=150.0,
    )
    risk = RiskResult(
        volatility_30d=vol30, volatility_90d=0.22, volatility_252d=0.25,
        var_95=-0.02, var_99=-0.03, warnings=[],
    )
    agent = AgentResult(
        signal="Bullish", score=score, confidence=0.8,
        rationale="test", breakdown={}, warnings=[],
    )
    consensus = ConsensusResult(
        agent_results={"buffett": agent}, agent_errors={},
        consensus_score=score, consensus_signal="Bullish",
        consensus_confidence=0.8, agreement=1.0, warnings=[],
    )
    return ComparisonInput(
        ticker=ticker, key_metrics=metrics, risk=risk, consensus=consensus,
    )


class TestBuildComparisonMatrix:
    def test_two_tickers_default_metrics(self) -> None:
        data = {
            "AAPL": _make_input("AAPL", pe=20.0, score=75.0),
            "MSFT": _make_input("MSFT", pe=30.0, score=65.0),
        }
        result = build_comparison_matrix(data)
        assert "AAPL" in result.tickers
        assert "MSFT" in result.tickers
        assert "pe_ratio" in result.metrics
        assert result.matrix["pe_ratio"]["AAPL"] == 20.0
        assert result.matrix["pe_ratio"]["MSFT"] == 30.0

    def test_custom_metrics(self) -> None:
        data = {
            "AAPL": _make_input("AAPL"),
            "MSFT": _make_input("MSFT"),
        }
        result = build_comparison_matrix(data, metrics=["pe_ratio", "roe"])
        assert result.metrics == ["pe_ratio", "roe"]
        assert "ev_ebitda" not in result.matrix

    def test_consensus_metrics_included(self) -> None:
        data = {"AAPL": _make_input("AAPL", score=75.0)}
        result = build_comparison_matrix(data)
        assert "consensus_score" in result.matrix
        assert result.matrix["consensus_score"]["AAPL"] == 75.0
        assert result.matrix["consensus_signal"]["AAPL"] == "Bullish"

    def test_volatility_from_risk(self) -> None:
        data = {"AAPL": _make_input("AAPL", vol30=0.25)}
        result = build_comparison_matrix(data)
        assert result.matrix["volatility_30d"]["AAPL"] == 0.25

    def test_missing_metrics_none(self) -> None:
        inp = ComparisonInput(ticker="EMPTY", key_metrics=None, risk=None, consensus=None)
        result = build_comparison_matrix({"EMPTY": inp})
        assert result.matrix["pe_ratio"]["EMPTY"] is None

    def test_default_metrics_list(self) -> None:
        assert "pe_ratio" in DEFAULT_COMPARISON_METRICS
        assert "consensus_score" in DEFAULT_COMPARISON_METRICS

    def test_warnings_on_unknown_metric(self) -> None:
        data = {"AAPL": _make_input("AAPL")}
        result = build_comparison_matrix(data, metrics=["nonexistent"])
        assert len(result.warnings) > 0
