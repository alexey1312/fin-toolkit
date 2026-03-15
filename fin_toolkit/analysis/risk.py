"""Risk analysis functions."""

from __future__ import annotations

import math
import statistics

from fin_toolkit.exceptions import InsufficientDataError
from fin_toolkit.models.price_data import PriceData
from fin_toolkit.models.results import CorrelationResult

# Hardcoded z-scores (no scipy dependency)
_Z_SCORES: dict[float, float] = {
    0.90: 1.2816,
    0.95: 1.6449,
    0.99: 2.3263,
}


def _log_returns(prices: list[float]) -> list[float]:
    """Compute log returns from a price series."""
    return [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]


def calculate_volatility(price_data: PriceData, window: int = 30) -> float:
    """Calculate annualized volatility from closing prices.

    Args:
        price_data: Historical price data.
        window: Number of trading days for the rolling window.

    Returns:
        Annualized volatility (std of log returns * sqrt(252)).

    Raises:
        InsufficientDataError: If fewer than ``window + 1`` prices.
    """
    closes = [p.close for p in price_data.prices]
    required = window + 1
    if len(closes) < required:
        raise InsufficientDataError(
            required=required,
            available=len(closes),
            context=f"volatility calculation (window={window})",
        )

    returns = _log_returns(closes)
    # Use the last `window` returns
    window_returns = returns[-window:]

    if all(r == 0.0 for r in window_returns):
        return 0.0

    std = statistics.stdev(window_returns)
    return std * math.sqrt(252)


def calculate_var(
    price_data: PriceData,
    confidence: float = 0.95,
    horizon_days: int = 1,
) -> float:
    """Calculate parametric Value at Risk.

    Args:
        price_data: Historical price data.
        confidence: Confidence level (0.90, 0.95, or 0.99).
        horizon_days: Investment horizon in trading days.

    Returns:
        VaR as a return value (negative means loss).
    """
    closes = [p.close for p in price_data.prices]
    returns = _log_returns(closes)

    mean_r = statistics.mean(returns)
    std_r = statistics.stdev(returns) if len(returns) > 1 else 0.0

    z = _Z_SCORES.get(confidence, 1.6449)

    var = mean_r * horizon_days - z * std_r * math.sqrt(horizon_days)
    return var


def correlation_matrix(prices: dict[str, PriceData]) -> CorrelationResult:
    """Compute pairwise Pearson correlation of log returns.

    Args:
        prices: Mapping of ticker → PriceData.

    Returns:
        CorrelationResult with tickers and correlation matrix.
    """
    tickers = sorted(prices.keys())

    # Build date-aligned return series
    # First, build date→return maps per ticker
    return_maps: dict[str, dict[str, float]] = {}
    for ticker in tickers:
        closes = prices[ticker].prices
        rmap: dict[str, float] = {}
        for i in range(1, len(closes)):
            date = closes[i].date
            rmap[date] = math.log(closes[i].close / closes[i - 1].close)
        return_maps[ticker] = rmap

    # Find common dates
    common_dates = set.intersection(*(set(rm.keys()) for rm in return_maps.values()))
    sorted_dates = sorted(common_dates)

    # Build aligned return vectors
    aligned: dict[str, list[float]] = {
        ticker: [return_maps[ticker][d] for d in sorted_dates] for ticker in tickers
    }

    # Pearson correlation helper
    def _pearson(x: list[float], y: list[float]) -> float:
        n = len(x)
        if n < 2:
            return 0.0
        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)
        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y, strict=True)) / (n - 1)
        std_x = statistics.stdev(x)
        std_y = statistics.stdev(y)
        if std_x == 0 or std_y == 0:
            return 0.0
        return cov / (std_x * std_y)

    matrix: dict[str, dict[str, float]] = {}
    for t1 in tickers:
        matrix[t1] = {}
        for t2 in tickers:
            if t1 == t2:
                matrix[t1][t2] = 1.0
            else:
                matrix[t1][t2] = _pearson(aligned[t1], aligned[t2])

    warnings: list[str] = []
    if len(sorted_dates) < 20:
        warnings.append(
            f"Only {len(sorted_dates)} common dates; correlation may be unreliable"
        )

    return CorrelationResult(tickers=tickers, matrix=matrix, warnings=warnings)


def kelly_criterion(win_rate: float, win_loss_ratio: float) -> float:
    """Calculate the Kelly Criterion optimal bet fraction.

    Args:
        win_rate: Probability of winning (0-1).
        win_loss_ratio: Average win / average loss.

    Returns:
        Optimal fraction of capital to risk (0 if negative EV).
    """
    k = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
    return max(k, 0.0)
