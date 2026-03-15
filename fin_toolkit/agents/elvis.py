"""Elvis Marlamov analysis agent."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.models.results import AgentResult, FundamentalResult
from fin_toolkit.providers.protocol import DataProvider
from fin_toolkit.providers.search_protocol import SearchProvider


class ElvisMarlamovAgent:
    """Agent inspired by Elvis Marlamov's analysis methodology.

    Scoring blocks (max 100):
        - Quality (40): fundamentals — ROE, ROA, margins
        - Stability (20): debt/equity, current ratio
        - Valuation (30): P/E vs reasonable threshold
        - Sentiment (10): search-derived sentiment (0 if no search provider)
    """

    # Scoring block maximums
    _MAX_QUALITY = 40.0
    _MAX_STABILITY = 20.0
    _MAX_VALUATION = 30.0
    _MAX_SENTIMENT = 10.0

    def __init__(
        self,
        data_provider: DataProvider,
        technical: TechnicalAnalyzer,
        fundamental: FundamentalAnalyzer,
        search: SearchProvider | None = None,
    ) -> None:
        self._data = data_provider
        self._technical = technical
        self._fundamental = fundamental
        self._search = search

    async def analyze(self, ticker: str) -> AgentResult:
        """Run Elvis Marlamov-style analysis on a ticker."""
        warnings: list[str] = []
        missing_blocks = 0
        total_blocks = 4

        # Fetch data
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        await self._data.get_prices(ticker, start, end)
        financials = await self._data.get_financials(ticker)
        metrics = await self._data.get_metrics(ticker)

        # Run fundamental analysis
        fund_result = self._fundamental.analyze(financials, metrics)

        # --- Quality score (max 40) ---
        quality, q_missing = self._score_quality(fund_result, warnings)
        if q_missing:
            missing_blocks += 1

        # --- Stability score (max 20) ---
        stability, s_missing = self._score_stability(fund_result, metrics, warnings)
        if s_missing:
            missing_blocks += 1

        # --- Valuation score (max 30) ---
        valuation, v_missing = self._score_valuation(fund_result, metrics, warnings)
        if v_missing:
            missing_blocks += 1

        # --- Sentiment score (max 10) ---
        sentiment = 0.0
        if self._search is None:
            warnings.append("No search provider — sentiment score is 0")
            missing_blocks += 1
        else:
            sentiment = await self._score_sentiment(ticker)

        total_score = quality + stability + valuation + sentiment

        # Confidence: 1.0 base, reduced proportionally per missing block
        confidence = max(0.0, 1.0 - (missing_blocks / total_blocks) * 0.25)

        # Signal classification
        if total_score >= 75.0:
            signal = "Bullish"
        elif total_score >= 50.0:
            signal = "Neutral"
        else:
            signal = "Bearish"

        rationale = (
            f"Elvis Marlamov analysis for {ticker}: "
            f"Quality={quality:.1f}/{self._MAX_QUALITY}, "
            f"Stability={stability:.1f}/{self._MAX_STABILITY}, "
            f"Valuation={valuation:.1f}/{self._MAX_VALUATION}, "
            f"Sentiment={sentiment:.1f}/{self._MAX_SENTIMENT}"
        )

        return AgentResult(
            signal=signal,
            score=total_score,
            confidence=round(confidence, 2),
            rationale=rationale,
            breakdown={
                "quality": quality,
                "stability": stability,
                "valuation": valuation,
                "sentiment": sentiment,
            },
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _score_quality(
        self, fund: FundamentalResult, warnings: list[str],
    ) -> tuple[float, bool]:
        """Score quality from fundamentals (max 40). Returns (score, is_missing)."""
        score = 0.0
        available = 0
        total_sub = 4  # ROE, ROA, net_margin, gross_margin

        roe = fund.profitability.get("roe")
        roa = fund.profitability.get("roa")
        net_margin = fund.profitability.get("net_margin")
        gross_margin = fund.profitability.get("gross_margin")

        if roe is not None:
            available += 1
            # ROE > 15% is good, scale to 10 points
            score += min(10.0, max(0.0, roe / 0.15) * 10.0)
        if roa is not None:
            available += 1
            score += min(10.0, max(0.0, roa / 0.10) * 10.0)
        if net_margin is not None:
            available += 1
            score += min(10.0, max(0.0, net_margin / 0.20) * 10.0)
        if gross_margin is not None:
            available += 1
            score += min(10.0, max(0.0, gross_margin / 0.40) * 10.0)

        if available == 0:
            warnings.append("No quality metrics available")
            return 0.0, True

        if available < total_sub:
            warnings.append(f"Missing {total_sub - available} quality sub-metrics")

        return min(self._MAX_QUALITY, score), False

    def _score_stability(
        self,
        fund: FundamentalResult,
        metrics: Any,
        warnings: list[str],
    ) -> tuple[float, bool]:
        """Score stability (max 20). Returns (score, is_missing)."""
        score = 0.0
        available = 0

        debt_to_equity = fund.stability.get("debt_to_equity")
        current_ratio = fund.stability.get("current_ratio")

        if debt_to_equity is not None:
            available += 1
            # D/E < 0.5 is excellent (10 pts), > 2.0 is bad (0 pts)
            if debt_to_equity <= 0.5:
                score += 10.0
            elif debt_to_equity <= 1.0:
                score += 7.0
            elif debt_to_equity <= 2.0:
                score += 3.0
            # else 0

        if current_ratio is not None:
            available += 1
            # CR > 2.0 is excellent (10 pts), < 1.0 is bad (0 pts)
            if current_ratio >= 2.0:
                score += 10.0
            elif current_ratio >= 1.5:
                score += 7.0
            elif current_ratio >= 1.0:
                score += 4.0
            # else 0

        if available == 0:
            warnings.append("No stability metrics available")
            return 0.0, True

        return min(self._MAX_STABILITY, score), False

    def _score_valuation(
        self,
        fund: FundamentalResult,
        metrics: Any,
        warnings: list[str],
    ) -> tuple[float, bool]:
        """Score valuation (max 30). Returns (score, is_missing)."""
        score = 0.0
        available = 0

        pe = fund.valuation.get("pe_ratio")
        pb = fund.valuation.get("pb_ratio")
        fcf_yield = fund.valuation.get("fcf_yield")

        if pe is not None:
            available += 1
            # P/E < 15 is great (15 pts), 15-25 is ok, > 40 is bad
            if pe <= 0:
                score += 0.0  # negative earnings
            elif pe <= 15:
                score += 15.0
            elif pe <= 25:
                score += 10.0
            elif pe <= 40:
                score += 5.0
            # else 0

        if pb is not None:
            available += 1
            if pb <= 1.5:
                score += 10.0
            elif pb <= 3.0:
                score += 7.0
            elif pb <= 5.0:
                score += 3.0
            # else 0

        if fcf_yield is not None:
            available += 1
            # FCF yield > 5% is great
            if fcf_yield >= 0.05:
                score += 5.0
            elif fcf_yield >= 0.03:
                score += 3.0
            elif fcf_yield > 0:
                score += 1.0

        if available == 0:
            warnings.append("No valuation metrics available")
            return 0.0, True

        return min(self._MAX_VALUATION, score), False

    async def _score_sentiment(self, ticker: str) -> float:
        """Score sentiment from search results (max 10)."""
        if self._search is None:
            return 0.0

        results = await self._search.search(f"{ticker} stock analysis", max_results=5)
        if not results:
            return 5.0  # neutral when no results

        positive_keywords = {"upgrade", "buy", "strong", "surge", "beat", "record", "growth"}
        negative_keywords = {"downgrade", "sell", "weak", "crash", "miss", "decline", "loss"}

        positive_count = 0
        negative_count = 0

        for r in results:
            text = (r.title + " " + r.snippet).lower()
            for kw in positive_keywords:
                if kw in text:
                    positive_count += 1
            for kw in negative_keywords:
                if kw in text:
                    negative_count += 1

        total = positive_count + negative_count
        if total == 0:
            return 5.0  # neutral

        sentiment_ratio = positive_count / total
        return min(self._MAX_SENTIMENT, sentiment_ratio * self._MAX_SENTIMENT)
