"""Low-level technical indicator computations wrapping the `ta` library."""

from __future__ import annotations

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands


def compute_rsi(df: pd.DataFrame, period: int = 14) -> float | None:
    """Compute RSI for the *close* column. Returns ``None`` when data is insufficient."""
    if len(df) < period + 1:
        return None
    rsi_series = RSIIndicator(close=df["close"], window=period).rsi()
    last = rsi_series.iloc[-1]
    if pd.isna(last):
        return None
    return float(last)


def compute_ema(df: pd.DataFrame, period: int) -> float | None:
    """Compute EMA for the *close* column. Returns ``None`` when data is insufficient."""
    if len(df) < period:
        return None
    ema_series = EMAIndicator(close=df["close"], window=period).ema_indicator()
    last = ema_series.iloc[-1]
    if pd.isna(last):
        return None
    return float(last)


def compute_bollinger(
    df: pd.DataFrame, period: int = 20
) -> tuple[float | None, float | None, float | None]:
    """Compute Bollinger Bands (upper, middle, lower). Returns a triple of ``None`` on failure."""
    if len(df) < period:
        return None, None, None
    bb = BollingerBands(close=df["close"], window=period)
    upper = bb.bollinger_hband().iloc[-1]
    middle = bb.bollinger_mavg().iloc[-1]
    lower = bb.bollinger_lband().iloc[-1]
    if pd.isna(upper) or pd.isna(middle) or pd.isna(lower):
        return None, None, None
    return float(upper), float(middle), float(lower)


def compute_macd(
    df: pd.DataFrame,
) -> tuple[float | None, float | None, float | None]:
    """Compute MACD (line, signal, histogram). Returns a triple of ``None`` on failure."""
    # MACD needs at least slow (26) + signal (9) periods
    if len(df) < 35:
        return None, None, None
    macd = MACD(close=df["close"])
    line = macd.macd().iloc[-1]
    signal = macd.macd_signal().iloc[-1]
    histogram = macd.macd_diff().iloc[-1]
    if pd.isna(line) or pd.isna(signal) or pd.isna(histogram):
        return None, None, None
    return float(line), float(signal), float(histogram)
