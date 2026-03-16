"""Tests for alert evaluation pure functions."""

from __future__ import annotations

from fin_toolkit.analysis.alerts import AlertRule, WatchlistEntry, evaluate_alerts
from fin_toolkit.models.financial import KeyMetrics
from fin_toolkit.models.results import RiskResult, TechnicalResult


def _make_entry(
    ticker: str = "AAPL",
    alerts: list[AlertRule] | None = None,
) -> WatchlistEntry:
    return WatchlistEntry(
        ticker=ticker,
        added_at="2024-01-01",
        notes="test",
        alerts=alerts or [],
    )


def _make_metrics(pe: float = 20.0, roe: float = 0.15) -> KeyMetrics:
    return KeyMetrics(
        ticker="AAPL", pe_ratio=pe, pb_ratio=3.0, market_cap=1e9,
        dividend_yield=0.01, roe=roe, roa=0.08, debt_to_equity=0.5,
    )


def _make_risk(vol30: float = 0.20) -> RiskResult:
    return RiskResult(
        volatility_30d=vol30, volatility_90d=0.22, volatility_252d=0.25,
        var_95=-0.02, var_99=-0.03, warnings=[],
    )


def _make_technical(rsi: float = 55.0) -> TechnicalResult:
    return TechnicalResult(
        rsi=rsi, ema_20=150.0, ema_50=148.0, ema_200=140.0,
        bb_upper=160.0, bb_middle=150.0, bb_lower=140.0,
        macd_line=1.5, macd_signal=1.0, macd_histogram=0.5,
        signals={}, overall_bias="Bullish", warnings=[],
    )


class TestEvaluateAlerts:
    def test_no_alerts_returns_empty(self) -> None:
        entry = _make_entry(alerts=[])
        result = evaluate_alerts(entry, _make_metrics(), None, None)
        assert result == []

    def test_pe_above_threshold_triggers(self) -> None:
        alert = AlertRule(metric="pe_ratio", operator=">", threshold=15.0, label="High P/E")
        entry = _make_entry(alerts=[alert])
        result = evaluate_alerts(entry, _make_metrics(pe=20.0), None, None)
        assert len(result) == 1
        assert result[0].metric == "pe_ratio"
        assert result[0].current_value == 20.0
        assert result[0].label == "High P/E"

    def test_pe_below_threshold_no_trigger(self) -> None:
        alert = AlertRule(metric="pe_ratio", operator=">", threshold=25.0)
        entry = _make_entry(alerts=[alert])
        result = evaluate_alerts(entry, _make_metrics(pe=20.0), None, None)
        assert result == []

    def test_volatility_alert_from_risk(self) -> None:
        alert = AlertRule(metric="volatility_30d", operator=">", threshold=0.15)
        entry = _make_entry(alerts=[alert])
        result = evaluate_alerts(entry, None, _make_risk(vol30=0.25), None)
        assert len(result) == 1
        assert result[0].current_value == 0.25

    def test_rsi_alert_from_technical(self) -> None:
        alert = AlertRule(metric="rsi", operator="<", threshold=30.0)
        entry = _make_entry(alerts=[alert])
        result = evaluate_alerts(entry, None, None, _make_technical(rsi=25.0))
        assert len(result) == 1

    def test_none_metric_skipped(self) -> None:
        alert = AlertRule(metric="pe_ratio", operator=">", threshold=10.0)
        entry = _make_entry(alerts=[alert])
        result = evaluate_alerts(entry, None, None, None)
        assert result == []

    def test_multiple_alerts_mixed(self) -> None:
        alerts = [
            AlertRule(metric="pe_ratio", operator=">", threshold=15.0),
            AlertRule(metric="roe", operator="<", threshold=0.20),
        ]
        entry = _make_entry(alerts=alerts)
        result = evaluate_alerts(entry, _make_metrics(pe=20.0, roe=0.15), None, None)
        # P/E > 15 triggers, ROE < 0.20 triggers (0.15 < 0.20)
        assert len(result) == 2

    def test_le_operator(self) -> None:
        alert = AlertRule(metric="pe_ratio", operator="<=", threshold=20.0)
        entry = _make_entry(alerts=[alert])
        result = evaluate_alerts(entry, _make_metrics(pe=20.0), None, None)
        assert len(result) == 1

    def test_ge_operator(self) -> None:
        alert = AlertRule(metric="roe", operator=">=", threshold=0.15)
        entry = _make_entry(alerts=[alert])
        result = evaluate_alerts(entry, _make_metrics(roe=0.15), None, None)
        assert len(result) == 1
