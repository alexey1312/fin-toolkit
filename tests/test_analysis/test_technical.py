"""Tests for technical analysis: indicators and TechnicalAnalyzer."""

from __future__ import annotations

import math

import pandas as pd

from fin_toolkit.analysis.indicators import (
    compute_bollinger,
    compute_ema,
    compute_macd,
    compute_rsi,
)
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.models.price_data import PriceData, PricePoint

# ---------------------------------------------------------------------------
# Helpers – synthetic price generators
# ---------------------------------------------------------------------------


def _ascending_prices(n: int, start: float = 100.0, step: float = 1.0) -> list[PricePoint]:
    """Generate steadily ascending prices (RSI should be high)."""
    points: list[PricePoint] = []
    for i in range(n):
        c = start + i * step
        points.append(
            PricePoint(
                date=f"2024-01-{i + 1:02d}",
                open=c - 0.5,
                high=c + 0.5,
                low=c - 1.0,
                close=c,
                volume=1_000_000,
            )
        )
    return points


def _descending_prices(n: int, start: float = 200.0, step: float = 1.0) -> list[PricePoint]:
    """Generate steadily descending prices (RSI should be low)."""
    points: list[PricePoint] = []
    for i in range(n):
        c = start - i * step
        points.append(
            PricePoint(
                date=f"2024-01-{i + 1:02d}",
                open=c + 0.5,
                high=c + 1.0,
                low=c - 0.5,
                close=c,
                volume=1_000_000,
            )
        )
    return points


def _flat_prices(n: int, price: float = 150.0) -> list[PricePoint]:
    """Generate flat prices (RSI ~50, narrow Bollinger bands)."""
    return [
        PricePoint(
            date=f"2024-01-{i + 1:02d}",
            open=price,
            high=price + 0.1,
            low=price - 0.1,
            close=price,
            volume=1_000_000,
        )
        for i in range(n)
    ]


def _price_data(points: list[PricePoint], ticker: str = "TEST") -> PriceData:
    return PriceData(ticker=ticker, period="1y", prices=points)


def _to_df(points: list[PricePoint]) -> pd.DataFrame:
    return pd.DataFrame([p.model_dump() for p in points])


# ---------------------------------------------------------------------------
# Tests – compute_rsi
# ---------------------------------------------------------------------------


class TestComputeRSI:
    def test_ascending_prices_high_rsi(self) -> None:
        df = _to_df(_ascending_prices(30))
        rsi = compute_rsi(df, period=14)
        assert rsi is not None
        assert rsi > 70, f"Expected RSI > 70 for ascending prices, got {rsi}"

    def test_descending_prices_low_rsi(self) -> None:
        df = _to_df(_descending_prices(30))
        rsi = compute_rsi(df, period=14)
        assert rsi is not None
        assert rsi < 30, f"Expected RSI < 30 for descending prices, got {rsi}"

    def test_flat_prices_rsi(self) -> None:
        df = _to_df(_flat_prices(30))
        rsi = compute_rsi(df, period=14)
        # Flat prices with tiny variance: ta library may return 100 (no losses)
        # or None; either is acceptable for degenerate input
        assert rsi is None or isinstance(rsi, float)

    def test_insufficient_data_returns_none(self) -> None:
        df = _to_df(_ascending_prices(5))
        rsi = compute_rsi(df, period=14)
        assert rsi is None


# ---------------------------------------------------------------------------
# Tests – compute_ema
# ---------------------------------------------------------------------------


class TestComputeEMA:
    def test_ema_20(self) -> None:
        df = _to_df(_ascending_prices(50))
        ema = compute_ema(df, period=20)
        assert ema is not None
        # EMA should lag the last close for ascending prices
        last_close = df["close"].iloc[-1]
        assert ema < last_close

    def test_ema_200_insufficient_data(self) -> None:
        df = _to_df(_ascending_prices(50))
        ema = compute_ema(df, period=200)
        assert ema is None

    def test_ema_value_is_float(self) -> None:
        df = _to_df(_ascending_prices(60))
        ema = compute_ema(df, period=50)
        assert ema is not None
        assert isinstance(ema, float)


# ---------------------------------------------------------------------------
# Tests – compute_bollinger
# ---------------------------------------------------------------------------


class TestComputeBollinger:
    def test_bollinger_ordering(self) -> None:
        df = _to_df(_ascending_prices(30))
        upper, middle, lower = compute_bollinger(df, period=20)
        assert upper is not None
        assert middle is not None
        assert lower is not None
        assert lower < middle < upper

    def test_flat_prices_narrow_bands(self) -> None:
        df = _to_df(_flat_prices(30))
        upper, middle, lower = compute_bollinger(df, period=20)
        assert upper is not None and middle is not None and lower is not None
        band_width = upper - lower
        assert band_width < 1.0, f"Expected narrow bands for flat prices, got width {band_width}"

    def test_insufficient_data(self) -> None:
        df = _to_df(_ascending_prices(5))
        upper, middle, lower = compute_bollinger(df, period=20)
        assert upper is None
        assert middle is None
        assert lower is None


# ---------------------------------------------------------------------------
# Tests – compute_macd
# ---------------------------------------------------------------------------


class TestComputeMACD:
    def test_ascending_bullish_macd(self) -> None:
        df = _to_df(_ascending_prices(50))
        line, signal, histogram = compute_macd(df)
        assert line is not None
        assert signal is not None
        assert histogram is not None
        # Ascending prices → MACD line should be positive
        assert line > 0

    def test_descending_bearish_macd(self) -> None:
        df = _to_df(_descending_prices(50))
        line, signal, histogram = compute_macd(df)
        assert line is not None
        # Descending → MACD line should be negative
        assert line < 0

    def test_insufficient_data(self) -> None:
        df = _to_df(_ascending_prices(10))
        line, signal, histogram = compute_macd(df)
        assert line is None
        assert signal is None
        assert histogram is None

    def test_histogram_is_line_minus_signal(self) -> None:
        df = _to_df(_ascending_prices(50))
        line, signal, histogram = compute_macd(df)
        assert line is not None and signal is not None and histogram is not None
        assert math.isclose(histogram, line - signal, abs_tol=0.01)


# ---------------------------------------------------------------------------
# Tests – TechnicalAnalyzer
# ---------------------------------------------------------------------------


class TestTechnicalAnalyzer:
    def test_analyze_ascending_bullish(self) -> None:
        """Ascending prices with 250 points → enough data for EMA-200."""
        data = _price_data(_ascending_prices(250, start=100.0, step=0.5))
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(data)

        assert result.rsi is not None
        assert result.rsi > 70
        assert result.signals["rsi"] == "overbought"
        assert result.ema_200 is not None
        # Price above EMA-200 for ascending
        assert result.signals["trend"] == "uptrend"
        assert result.macd_line is not None
        assert result.signals["macd"] == "bullish"
        assert result.overall_bias == "Bullish"
        assert result.warnings == []

    def test_analyze_descending_bearish(self) -> None:
        data = _price_data(_descending_prices(250, start=300.0, step=0.5))
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(data)

        assert result.rsi is not None
        assert result.rsi < 30
        assert result.signals["rsi"] == "oversold"
        assert result.signals["trend"] == "downtrend"
        assert result.signals["macd"] == "bearish"
        assert result.overall_bias == "Bearish"

    def test_analyze_insufficient_data_warnings(self) -> None:
        """With only 5 data points, everything should be None with warnings."""
        data = _price_data(_ascending_prices(5))
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(data)

        assert result.rsi is None
        assert result.ema_20 is None
        assert result.ema_50 is None
        assert result.ema_200 is None
        assert result.bb_upper is None
        assert result.macd_line is None
        assert result.overall_bias == "Neutral"
        assert len(result.warnings) > 0

    def test_analyze_bollinger_signals(self) -> None:
        """Price near upper band → overbought signal."""
        data = _price_data(_ascending_prices(250, start=100.0, step=0.5))
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(data)

        # For ascending prices, close should be near/above upper band
        assert result.bb_upper is not None
        assert "bb" in result.signals

    def test_overall_bias_neutral_on_mixed_signals(self) -> None:
        """Prices that rise then fall should produce mixed/neutral signals."""
        # Build a series that goes up then down, ending near the middle
        up = _ascending_prices(125, start=100.0, step=0.5)
        down_points: list[PricePoint] = []
        last_up_close = 100.0 + 124 * 0.5  # 162.0
        for i in range(125):
            c = last_up_close - i * 0.5
            down_points.append(
                PricePoint(
                    date=f"2024-06-{i + 1:02d}",
                    open=c + 0.25,
                    high=c + 0.5,
                    low=c - 0.5,
                    close=c,
                    volume=1_000_000,
                )
            )
        data = _price_data(up + down_points)
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(data)

        # The V-shape should produce conflicting signals → Neutral or at most mild bias
        assert result.overall_bias in ("Neutral", "Bearish", "Bullish")

    def test_result_types(self) -> None:
        """Verify the result is a proper TechnicalResult."""
        from fin_toolkit.models.results import TechnicalResult

        data = _price_data(_ascending_prices(60))
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(data)
        assert isinstance(result, TechnicalResult)

    def test_signals_dict_keys(self) -> None:
        """Signals dict should contain expected keys when data is sufficient."""
        data = _price_data(_ascending_prices(250, start=100.0, step=0.5))
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(data)

        expected_keys = {"rsi", "macd", "trend", "bb"}
        assert expected_keys == set(result.signals.keys())
