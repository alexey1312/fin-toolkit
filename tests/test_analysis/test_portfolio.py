"""Tests for portfolio analysis pure functions."""

from __future__ import annotations

import pytest

from fin_toolkit.models.results import (
    AgentResult,
    CorrelationResult,
    RiskResult,
    TechnicalResult,
)


def _agent(signal: str, score: float, confidence: float) -> AgentResult:
    return AgentResult(
        signal=signal,
        score=score,
        confidence=confidence,
        rationale="test",
        breakdown={},
        warnings=[],
    )


def _risk(
    vol_252: float | None = 0.25,
    var_95: float | None = -0.02,
) -> RiskResult:
    return RiskResult(
        volatility_30d=0.20,
        volatility_90d=0.22,
        volatility_252d=vol_252,
        var_95=var_95,
        var_99=-0.03,
        warnings=[],
    )


def _technical(bias: str = "Bullish") -> TechnicalResult:
    return TechnicalResult(
        rsi=55.0,
        ema_20=150.0,
        ema_50=148.0,
        ema_200=140.0,
        bb_upper=160.0,
        bb_middle=150.0,
        bb_lower=140.0,
        macd_line=1.5,
        macd_signal=1.0,
        macd_histogram=0.5,
        signals={},
        overall_bias=bias,
        warnings=[],
    )


# ---------------------------------------------------------------------------
# _signal_from_score
# ---------------------------------------------------------------------------


class TestSignalFromScore:
    def test_bullish_at_70(self) -> None:
        from fin_toolkit.analysis.portfolio import _signal_from_score

        assert _signal_from_score(70) == "Bullish"

    def test_bullish_above_70(self) -> None:
        from fin_toolkit.analysis.portfolio import _signal_from_score

        assert _signal_from_score(85) == "Bullish"

    def test_neutral_at_40(self) -> None:
        from fin_toolkit.analysis.portfolio import _signal_from_score

        assert _signal_from_score(40) == "Neutral"

    def test_neutral_at_69(self) -> None:
        from fin_toolkit.analysis.portfolio import _signal_from_score

        assert _signal_from_score(69) == "Neutral"

    def test_bearish_at_39(self) -> None:
        from fin_toolkit.analysis.portfolio import _signal_from_score

        assert _signal_from_score(39) == "Bearish"

    def test_bearish_at_zero(self) -> None:
        from fin_toolkit.analysis.portfolio import _signal_from_score

        assert _signal_from_score(0) == "Bearish"


# ---------------------------------------------------------------------------
# compute_consensus
# ---------------------------------------------------------------------------


class TestComputeConsensus:
    def test_single_agent(self) -> None:
        from fin_toolkit.analysis.portfolio import compute_consensus

        results = {"buffett": _agent("Bullish", 80, 0.9)}
        c = compute_consensus(results, {})
        assert c.consensus_score == pytest.approx(80.0)
        assert c.consensus_signal == "Bullish"
        assert c.consensus_confidence == pytest.approx(0.9)
        assert c.agreement == pytest.approx(1.0)

    def test_weighted_avg_three_agents(self) -> None:
        from fin_toolkit.analysis.portfolio import compute_consensus

        results = {
            "a": _agent("Bullish", 80, 0.9),  # 80*0.9 = 72
            "b": _agent("Bullish", 70, 0.7),  # 70*0.7 = 49
            "c": _agent("Neutral", 50, 0.5),  # 50*0.5 = 25
        }
        # weighted = (72+49+25) / (0.9+0.7+0.5) = 146/2.1 ≈ 69.52
        c = compute_consensus(results, {})
        assert c.consensus_score == pytest.approx(146 / 2.1, abs=0.01)
        # 69.52 → Neutral (< 70)
        assert c.consensus_signal == "Neutral"

    def test_all_bearish_agreement_is_1(self) -> None:
        from fin_toolkit.analysis.portfolio import compute_consensus

        results = {
            "a": _agent("Bearish", 20, 0.8),
            "b": _agent("Bearish", 30, 0.7),
        }
        c = compute_consensus(results, {})
        assert c.consensus_signal == "Bearish"
        assert c.agreement == pytest.approx(1.0)

    def test_mixed_signals_low_agreement(self) -> None:
        from fin_toolkit.analysis.portfolio import compute_consensus

        results = {
            "a": _agent("Bullish", 75, 0.8),
            "b": _agent("Bearish", 20, 0.6),
            "c": _agent("Bullish", 80, 0.9),
        }
        c = compute_consensus(results, {})
        # Weighted score ≈ 62.6 → Neutral, but no agent said Neutral → agreement=0
        assert c.consensus_signal == "Neutral"
        assert c.agreement == pytest.approx(0.0)

    def test_empty_results(self) -> None:
        from fin_toolkit.analysis.portfolio import compute_consensus

        c = compute_consensus({}, {"a": "failed"})
        assert c.consensus_score == 0.0
        assert c.consensus_signal == "Neutral"
        assert c.consensus_confidence == 0.0

    def test_errors_in_warnings(self) -> None:
        from fin_toolkit.analysis.portfolio import compute_consensus

        c = compute_consensus(
            {"a": _agent("Bullish", 80, 0.9)},
            {"b": "provider timeout"},
        )
        assert any("b" in w for w in c.warnings)


# ---------------------------------------------------------------------------
# compute_position_size
# ---------------------------------------------------------------------------


class TestComputePositionSize:
    def test_bullish_low_vol(self) -> None:
        from fin_toolkit.analysis.portfolio import compute_consensus, compute_position_size

        c = compute_consensus({"a": _agent("Bullish", 80, 0.9)}, {})
        size = compute_position_size(c, _risk(vol_252=0.15), _technical("Bullish"))
        # low vol → base 25%, confidence 0.9, score>=75 → 1.0x, aligned → 1.1x (cap 25)
        assert 15.0 < size <= 25.0

    def test_bullish_high_vol(self) -> None:
        from fin_toolkit.analysis.portfolio import compute_consensus, compute_position_size

        c = compute_consensus({"a": _agent("Bullish", 80, 0.9)}, {})
        size = compute_position_size(c, _risk(vol_252=0.65), _technical("Bullish"))
        # high vol → base 5%
        assert 0 < size <= 5.0

    def test_neutral_halves(self) -> None:
        from fin_toolkit.analysis.portfolio import compute_consensus, compute_position_size

        c = compute_consensus({"a": _agent("Neutral", 50, 0.8)}, {})
        size = compute_position_size(c, _risk(vol_252=0.25), _technical("Neutral"))
        # Neutral → 0.5x multiplier
        assert size < 10.0

    def test_bearish_is_zero(self) -> None:
        from fin_toolkit.analysis.portfolio import compute_consensus, compute_position_size

        c = compute_consensus({"a": _agent("Bearish", 20, 0.8)}, {})
        size = compute_position_size(c, _risk(), _technical("Bearish"))
        assert size == 0.0

    def test_confidence_scaling(self) -> None:
        from fin_toolkit.analysis.portfolio import compute_consensus, compute_position_size

        c_high = compute_consensus({"a": _agent("Bullish", 80, 1.0)}, {})
        c_low = compute_consensus({"a": _agent("Bullish", 80, 0.5)}, {})
        r = _risk(vol_252=0.15)
        t = _technical("Bullish")
        size_high = compute_position_size(c_high, r, t)
        size_low = compute_position_size(c_low, r, t)
        assert size_high > size_low

    def test_technical_contradiction(self) -> None:
        from fin_toolkit.analysis.portfolio import compute_consensus, compute_position_size

        c = compute_consensus({"a": _agent("Bullish", 80, 0.9)}, {})
        size_aligned = compute_position_size(c, _risk(), _technical("Bullish"))
        size_contra = compute_position_size(c, _risk(), _technical("Bearish"))
        assert size_aligned > size_contra

    def test_none_volatility_conservative(self) -> None:
        from fin_toolkit.analysis.portfolio import compute_consensus, compute_position_size

        c = compute_consensus({"a": _agent("Bullish", 80, 0.9)}, {})
        size = compute_position_size(c, _risk(vol_252=None), _technical("Bullish"))
        # None vol → base 10% (conservative default)
        assert 0 < size <= 10.0


# ---------------------------------------------------------------------------
# compute_stop_loss
# ---------------------------------------------------------------------------


class TestComputeStopLoss:
    def test_normal_2x_var(self) -> None:
        from fin_toolkit.analysis.portfolio import compute_stop_loss

        sl = compute_stop_loss(_risk(var_95=-0.02), _technical())
        # abs(-0.02) * 2 = 0.04 → 4%
        assert sl == pytest.approx(4.0, abs=0.01)

    def test_clamp_min_3(self) -> None:
        from fin_toolkit.analysis.portfolio import compute_stop_loss

        sl = compute_stop_loss(_risk(var_95=-0.005), _technical())
        # abs(-0.005) * 2 = 0.01 → 1% → clamped to 3%
        assert sl == pytest.approx(3.0)

    def test_clamp_max_15(self) -> None:
        from fin_toolkit.analysis.portfolio import compute_stop_loss

        sl = compute_stop_loss(_risk(var_95=-0.10), _technical())
        # abs(-0.10) * 2 = 0.20 → 20% → clamped to 15%
        assert sl == pytest.approx(15.0)

    def test_none_on_missing_var(self) -> None:
        from fin_toolkit.analysis.portfolio import compute_stop_loss

        sl = compute_stop_loss(_risk(var_95=None), _technical())
        assert sl is None


# ---------------------------------------------------------------------------
# adjust_position_sizes
# ---------------------------------------------------------------------------


class TestAdjustPositionSizes:
    def test_high_correlation_reduces(self) -> None:
        from fin_toolkit.analysis.portfolio import adjust_position_sizes

        corr = CorrelationResult(
            tickers=["A", "B"],
            matrix={"A": {"A": 1.0, "B": 0.85}, "B": {"A": 0.85, "B": 1.0}},
            warnings=[],
        )
        raw = {"A": 10.0, "B": 10.0}
        adj = adjust_position_sizes(raw, corr)
        # corr >= 0.80 → 0.70x
        assert adj["A"] == pytest.approx(7.0)
        assert adj["B"] == pytest.approx(7.0)

    def test_low_correlation_boosts(self) -> None:
        from fin_toolkit.analysis.portfolio import adjust_position_sizes

        corr = CorrelationResult(
            tickers=["A", "B"],
            matrix={"A": {"A": 1.0, "B": 0.10}, "B": {"A": 0.10, "B": 1.0}},
            warnings=[],
        )
        raw = {"A": 10.0, "B": 10.0}
        adj = adjust_position_sizes(raw, corr)
        # corr < 0.20 → 1.10x
        assert adj["A"] == pytest.approx(11.0)
        assert adj["B"] == pytest.approx(11.0)

    def test_moderate_correlation_unchanged(self) -> None:
        from fin_toolkit.analysis.portfolio import adjust_position_sizes

        corr = CorrelationResult(
            tickers=["A", "B"],
            matrix={"A": {"A": 1.0, "B": 0.50}, "B": {"A": 0.50, "B": 1.0}},
            warnings=[],
        )
        raw = {"A": 10.0, "B": 10.0}
        adj = adjust_position_sizes(raw, corr)
        assert adj["A"] == pytest.approx(10.0)
        assert adj["B"] == pytest.approx(10.0)

    def test_single_ticker_unchanged(self) -> None:
        from fin_toolkit.analysis.portfolio import adjust_position_sizes

        corr = CorrelationResult(
            tickers=["A"],
            matrix={"A": {"A": 1.0}},
            warnings=[],
        )
        raw = {"A": 15.0}
        adj = adjust_position_sizes(raw, corr)
        assert adj["A"] == pytest.approx(15.0)
