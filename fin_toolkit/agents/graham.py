"""Ben Graham analysis agent."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.models.results import AgentResult, FundamentalResult
from fin_toolkit.providers.protocol import DataProvider


class BenGrahamAgent:
    """Agent inspired by Ben Graham's deep value investing principles.

    Scoring blocks (max 100):
        - Net-Net Value (35): P/E, P/B below book, FCF yield
        - Earnings Stability (30): consistent earnings, reasonable PE, dividends
        - Financial Strength (35): current ratio ≥ 2, low debt, working capital
    """

    _MAX_NET_NET = 35.0
    _MAX_EARNINGS = 30.0
    _MAX_STRENGTH = 35.0

    def __init__(
        self,
        data_provider: DataProvider,
        technical: TechnicalAnalyzer,
        fundamental: FundamentalAnalyzer,
    ) -> None:
        self._data = data_provider
        self._technical = technical
        self._fundamental = fundamental

    async def analyze(self, ticker: str) -> AgentResult:
        """Run Graham-style deep value analysis."""
        warnings: list[str] = []
        missing_blocks = 0
        total_blocks = 3

        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        await self._data.get_prices(ticker, start, end)
        financials = await self._data.get_financials(ticker)
        metrics = await self._data.get_metrics(ticker)

        fund_result = self._fundamental.analyze(financials, metrics)

        # --- Net-Net Value (max 35) ---
        net_net, nn_missing = self._score_net_net(fund_result, metrics, warnings)
        if nn_missing:
            missing_blocks += 1

        # --- Earnings Stability (max 30) ---
        earnings, e_missing = self._score_earnings_stability(fund_result, metrics, warnings)
        if e_missing:
            missing_blocks += 1

        # --- Financial Strength (max 35) ---
        strength, s_missing = self._score_financial_strength(fund_result, metrics, warnings)
        if s_missing:
            missing_blocks += 1

        total_score = net_net + earnings + strength
        confidence = max(0.0, 1.0 - (missing_blocks / total_blocks) * 0.3)

        if total_score >= 75.0:
            signal = "Bullish"
        elif total_score >= 50.0:
            signal = "Neutral"
        else:
            signal = "Bearish"

        rationale = (
            f"Ben Graham value analysis for {ticker}: "
            f"Net-Net={net_net:.1f}/{self._MAX_NET_NET}, "
            f"Earnings Stability={earnings:.1f}/{self._MAX_EARNINGS}, "
            f"Financial Strength={strength:.1f}/{self._MAX_STRENGTH}"
        )

        return AgentResult(
            signal=signal,
            score=total_score,
            confidence=round(confidence, 2),
            rationale=rationale,
            breakdown={
                "net_net_value": net_net,
                "earnings_stability": earnings,
                "financial_strength": strength,
            },
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _score_net_net(
        self,
        fund: FundamentalResult,
        metrics: Any,
        warnings: list[str],
    ) -> tuple[float, bool]:
        """Net-net value: P/B below book, low P/E, FCF yield (max 35).

        Graham insisted on buying below net current asset value.
        """
        score = 0.0
        available = 0

        pb = fund.valuation.get("pb_ratio")
        pe = fund.valuation.get("pe_ratio")
        fcf_yield = fund.valuation.get("fcf_yield")

        if pb is not None:
            available += 1
            # Graham wants P/B < 1.5 (ideally < 1.0)
            if pb <= 0.7:
                score += 15.0
            elif pb <= 1.0:
                score += 12.0
            elif pb <= 1.5:
                score += 8.0
            elif pb <= 2.0:
                score += 3.0

        if pe is not None:
            available += 1
            # Graham: P/E should not exceed 15
            if pe <= 0:
                score += 0.0
            elif pe <= 10:
                score += 12.0
            elif pe <= 15:
                score += 8.0
            elif pe <= 20:
                score += 3.0

        if fcf_yield is not None:
            available += 1
            if fcf_yield >= 0.10:
                score += 8.0
            elif fcf_yield >= 0.07:
                score += 6.0
            elif fcf_yield >= 0.04:
                score += 3.0
            elif fcf_yield > 0:
                score += 1.0

        if available == 0:
            warnings.append("No valuation data for net-net assessment")
            return 0.0, True

        return min(self._MAX_NET_NET, score), False

    def _score_earnings_stability(
        self,
        fund: FundamentalResult,
        metrics: Any,
        warnings: list[str],
    ) -> tuple[float, bool]:
        """Earnings stability: positive earnings, reasonable margins (max 30).

        Graham required 10 years of positive earnings; we proxy with margin health.
        """
        score = 0.0
        available = 0

        net_margin = fund.profitability.get("net_margin")
        roe = fund.profitability.get("roe")
        gross_margin = fund.profitability.get("gross_margin")

        if net_margin is not None:
            available += 1
            # Positive and stable earnings
            if net_margin >= 0.10:
                score += 12.0
            elif net_margin >= 0.05:
                score += 8.0
            elif net_margin > 0:
                score += 4.0
            # Negative = 0

        if roe is not None:
            available += 1
            # Moderate ROE preferred (not excessively high = risky)
            if 0.10 <= roe <= 0.25:
                score += 10.0
            elif roe > 0.25:
                score += 6.0  # too high may indicate leverage
            elif roe >= 0.05:
                score += 4.0

        if gross_margin is not None:
            available += 1
            if gross_margin >= 0.30:
                score += 8.0
            elif gross_margin >= 0.20:
                score += 5.0
            elif gross_margin >= 0.10:
                score += 2.0

        if available == 0:
            warnings.append("No earnings data for stability assessment")
            return 0.0, True

        return min(self._MAX_EARNINGS, score), False

    def _score_financial_strength(
        self,
        fund: FundamentalResult,
        metrics: Any,
        warnings: list[str],
    ) -> tuple[float, bool]:
        """Financial strength: current ratio ≥ 2, low debt (max 35).

        Graham's rule: current assets should be at least 2× current liabilities.
        """
        score = 0.0
        available = 0

        current_ratio = fund.stability.get("current_ratio")
        debt_to_equity = fund.stability.get("debt_to_equity")
        roa = fund.profitability.get("roa")

        if current_ratio is not None:
            available += 1
            # Graham's classic threshold: CR ≥ 2.0
            if current_ratio >= 2.5:
                score += 15.0
            elif current_ratio >= 2.0:
                score += 12.0
            elif current_ratio >= 1.5:
                score += 6.0
            elif current_ratio >= 1.0:
                score += 2.0

        if debt_to_equity is not None:
            available += 1
            # Graham: minimal debt
            if debt_to_equity <= 0.3:
                score += 12.0
            elif debt_to_equity <= 0.5:
                score += 8.0
            elif debt_to_equity <= 1.0:
                score += 4.0

        if roa is not None:
            available += 1
            if roa >= 0.10:
                score += 8.0
            elif roa >= 0.05:
                score += 5.0
            elif roa >= 0.02:
                score += 2.0

        if available == 0:
            warnings.append("No data for financial strength assessment")
            return 0.0, True

        return min(self._MAX_STRENGTH, score), False
