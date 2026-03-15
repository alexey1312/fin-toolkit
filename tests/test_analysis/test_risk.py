"""Tests for risk analysis module."""

import math

import pytest

from fin_toolkit.analysis.risk import (
    calculate_var,
    calculate_volatility,
    correlation_matrix,
    kelly_criterion,
)
from fin_toolkit.exceptions import InsufficientDataError
from fin_toolkit.models.price_data import PriceData, PricePoint


def _make_price_data(ticker: str, closes: list[float]) -> PriceData:
    """Build PriceData from a list of closing prices."""
    prices = [
        PricePoint(
            date=f"2024-01-{i + 1:02d}",
            open=c,
            high=c,
            low=c,
            close=c,
            volume=1000,
        )
        for i, c in enumerate(closes)
    ]
    return PriceData(ticker=ticker, period="custom", prices=prices)


# ---------- calculate_volatility ----------


class TestCalculateVolatility:
    def test_constant_prices_zero_volatility(self) -> None:
        """Constant prices → all log returns are 0 → volatility is 0."""
        pd = _make_price_data("FLAT", [100.0] * 35)
        vol = calculate_volatility(pd, window=30)
        assert vol == 0.0

    def test_known_volatility(self) -> None:
        """Alternating returns with known std dev."""
        # Build prices so that log returns alternate +r, -r
        # std dev of [r, -r, r, -r, ...] = r  (mean ≈ 0)
        r = 0.01  # daily log return magnitude
        prices = [100.0]
        for i in range(32):
            sign = 1 if i % 2 == 0 else -1
            prices.append(prices[-1] * math.exp(sign * r))

        pd = _make_price_data("ALT", prices)
        vol = calculate_volatility(pd, window=30)
        expected_annual = r * math.sqrt(252)
        assert vol == pytest.approx(expected_annual, rel=0.05)

    def test_insufficient_data_raises(self) -> None:
        pd = _make_price_data("SHORT", [100.0] * 10)
        with pytest.raises(InsufficientDataError):
            calculate_volatility(pd, window=30)


# ---------- calculate_var ----------


class TestCalculateVaR:
    def _uniform_growth_data(self) -> PriceData:
        """50 days of steady 1% daily growth → std ≈ 0, VaR ≈ mean."""
        prices = [100.0]
        for _ in range(50):
            prices.append(prices[-1] * 1.01)
        return _make_price_data("GROW", prices)

    def test_var_95(self) -> None:
        pd = self._uniform_growth_data()
        var = calculate_var(pd, confidence=0.95)
        # Constant returns → std ≈ 0, VaR ≈ daily return ≈ 0.01
        assert var == pytest.approx(0.01, abs=0.002)

    def test_var_99_more_conservative(self) -> None:
        """99% VaR must be ≤ 95% VaR (further into the left tail)."""
        # Use data with some variance
        r = 0.005
        prices = [100.0]
        for i in range(60):
            sign = 1 if i % 2 == 0 else -1
            prices.append(prices[-1] * math.exp(sign * r))
        pd = _make_price_data("VAR", prices)
        var_95 = calculate_var(pd, confidence=0.95)
        var_99 = calculate_var(pd, confidence=0.99)
        assert var_99 < var_95

    def test_var_multi_day_horizon(self) -> None:
        """Multi-day VaR scales by sqrt(horizon)."""
        r = 0.005
        prices = [100.0]
        for i in range(60):
            sign = 1 if i % 2 == 0 else -1
            prices.append(prices[-1] * math.exp(sign * r))
        pd = _make_price_data("HOR", prices)
        var_1d = calculate_var(pd, confidence=0.95, horizon_days=1)
        var_4d = calculate_var(pd, confidence=0.95, horizon_days=4)
        # VaR should scale roughly by sqrt(4)=2
        # The mean part also scales, so use approximate check
        ratio = abs(var_4d) / abs(var_1d) if var_1d != 0 else 0
        assert 1.5 < ratio < 2.5


# ---------- correlation_matrix ----------


class TestCorrelationMatrix:
    def test_identical_series_correlation_one(self) -> None:
        """Identical price series → correlation = 1.0."""
        closes = [100.0 + i for i in range(40)]
        prices = {
            "A": _make_price_data("A", closes),
            "B": _make_price_data("B", closes),
        }
        result = correlation_matrix(prices)
        assert result.matrix["A"]["B"] == pytest.approx(1.0, abs=1e-10)
        assert result.matrix["B"]["A"] == pytest.approx(1.0, abs=1e-10)

    def test_inverse_series_negative_correlation(self) -> None:
        """Inversely moving prices → correlation ≈ -1."""
        # Build series where log returns are exactly negated
        r_values = [0.01 * (1 + (i % 5) * 0.3) * (1 if i % 3 else -1) for i in range(39)]
        up = [100.0]
        down = [100.0]
        for rv in r_values:
            up.append(up[-1] * math.exp(rv))
            down.append(down[-1] * math.exp(-rv))
        prices = {
            "UP": _make_price_data("UP", up),
            "DOWN": _make_price_data("DOWN", down),
        }
        result = correlation_matrix(prices)
        assert result.matrix["UP"]["DOWN"] == pytest.approx(-1.0, abs=0.05)

    def test_three_tickers_matrix_shape(self) -> None:
        """Three tickers produce a 3×3 matrix with diagonal = 1."""
        closes_a = [100.0 + i for i in range(40)]
        closes_b = [50.0 + i * 0.5 for i in range(40)]
        closes_c = [200.0 - i for i in range(40)]
        prices = {
            "A": _make_price_data("A", closes_a),
            "B": _make_price_data("B", closes_b),
            "C": _make_price_data("C", closes_c),
        }
        result = correlation_matrix(prices)
        assert set(result.tickers) == {"A", "B", "C"}
        for t in result.tickers:
            assert result.matrix[t][t] == pytest.approx(1.0, abs=1e-10)


# ---------- kelly_criterion ----------


class TestKellyCriterion:
    def test_positive_ev(self) -> None:
        """win_rate=0.6, win_loss_ratio=2 → positive Kelly fraction."""
        k = kelly_criterion(win_rate=0.6, win_loss_ratio=2.0)
        # Kelly = (0.6*2 - 0.4) / 2 = 0.8/2 = 0.4
        assert k == pytest.approx(0.4)

    def test_negative_ev_returns_zero(self) -> None:
        """Low win rate → negative Kelly → clamped to 0."""
        k = kelly_criterion(win_rate=0.2, win_loss_ratio=1.0)
        assert k == 0.0

    def test_breakeven_returns_zero(self) -> None:
        """Exactly breakeven → Kelly = 0."""
        # Kelly = (0.5*1 - 0.5)/1 = 0
        k = kelly_criterion(win_rate=0.5, win_loss_ratio=1.0)
        assert k == 0.0

    def test_high_win_rate(self) -> None:
        """Very high win rate → large fraction."""
        k = kelly_criterion(win_rate=0.9, win_loss_ratio=3.0)
        # (0.9*3 - 0.1) / 3 = 2.6/3 ≈ 0.8667
        assert k == pytest.approx(2.6 / 3.0)
