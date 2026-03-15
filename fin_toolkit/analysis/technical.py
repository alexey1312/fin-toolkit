"""High-level technical analysis orchestrator."""

from __future__ import annotations

import pandas as pd

from fin_toolkit.analysis.indicators import (
    compute_bollinger,
    compute_ema,
    compute_macd,
    compute_rsi,
)
from fin_toolkit.models.price_data import PriceData
from fin_toolkit.models.results import TechnicalResult


class TechnicalAnalyzer:
    """Convert :class:`PriceData` into a :class:`TechnicalResult`."""

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def analyze(self, price_data: PriceData) -> TechnicalResult:
        """Run all technical indicators and derive trading signals."""
        df = self._to_dataframe(price_data)
        warnings: list[str] = []

        # --- indicators ---
        rsi = compute_rsi(df)
        if rsi is None and len(df) > 0:
            warnings.append("Insufficient data for RSI")

        ema_20 = compute_ema(df, 20)
        ema_50 = compute_ema(df, 50)
        ema_200 = compute_ema(df, 200)

        if ema_20 is None and len(df) > 0:
            warnings.append("Insufficient data for EMA-20")
        if ema_50 is None and len(df) > 0:
            warnings.append("Insufficient data for EMA-50")
        if ema_200 is None and len(df) > 0:
            warnings.append("Insufficient data for EMA-200")

        bb_upper, bb_middle, bb_lower = compute_bollinger(df)
        if bb_upper is None and len(df) > 0:
            warnings.append("Insufficient data for Bollinger Bands")

        macd_line, macd_signal, macd_histogram = compute_macd(df)
        if macd_line is None and len(df) > 0:
            warnings.append("Insufficient data for MACD")

        # --- signals ---
        signals: dict[str, str] = {}
        last_close = float(df["close"].iloc[-1]) if len(df) > 0 else None

        if rsi is not None:
            signals["rsi"] = self._rsi_signal(rsi)

        if macd_line is not None and macd_signal is not None:
            signals["macd"] = "bullish" if macd_line > macd_signal else "bearish"

        if ema_200 is not None and last_close is not None:
            signals["trend"] = "uptrend" if last_close > ema_200 else "downtrend"

        if bb_upper is not None and bb_lower is not None and last_close is not None:
            signals["bb"] = self._bollinger_signal(last_close, bb_upper, bb_lower)

        overall_bias = self._overall_bias(signals)

        return TechnicalResult(
            rsi=rsi,
            ema_20=ema_20,
            ema_50=ema_50,
            ema_200=ema_200,
            bb_upper=bb_upper,
            bb_middle=bb_middle,
            bb_lower=bb_lower,
            macd_line=macd_line,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            signals=signals,
            overall_bias=overall_bias,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dataframe(price_data: PriceData) -> pd.DataFrame:
        return pd.DataFrame([p.model_dump() for p in price_data.prices])

    @staticmethod
    def _rsi_signal(rsi: float) -> str:
        if rsi > 70:
            return "overbought"
        if rsi < 30:
            return "oversold"
        return "neutral"

    @staticmethod
    def _bollinger_signal(close: float, upper: float, lower: float) -> str:
        band_width = upper - lower
        if band_width == 0:
            return "neutral"
        # "near" = within 10% of band width from the edge
        threshold = band_width * 0.1
        if close >= upper - threshold:
            return "overbought"
        if close <= lower + threshold:
            return "oversold"
        return "neutral"

    @staticmethod
    def _overall_bias(signals: dict[str, str]) -> str:
        if not signals:
            return "Neutral"

        bullish = 0
        bearish = 0
        for value in signals.values():
            if value in ("overbought", "bullish", "uptrend"):
                bullish += 1
            elif value in ("oversold", "bearish", "downtrend"):
                bearish += 1

        if bullish > bearish:
            return "Bullish"
        if bearish > bullish:
            return "Bearish"
        return "Neutral"
