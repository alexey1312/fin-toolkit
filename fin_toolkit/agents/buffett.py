"""Warren Buffett analysis agent."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.models.results import AgentResult, FundamentalResult
from fin_toolkit.providers.protocol import DataProvider


class WarrenBuffettAgent:
    """Agent inspired by Warren Buffett's value investing principles.

    Scoring blocks (max 100):
        - Margin of Safety (40): P/E, P/B, FCF yield
        - Durable Advantage (35): ROE, margins, consistency
        - Management Quality (25): ROA, debt management, capital allocation
    """

    _MAX_MARGIN_OF_SAFETY = 40.0
    _MAX_DURABLE_ADVANTAGE = 35.0
    _MAX_MANAGEMENT_QUALITY = 25.0

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
        """Run Buffett-style value investing analysis."""
        warnings: list[str] = []
        missing_blocks = 0
        total_blocks = 3

        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        await self._data.get_prices(ticker, start, end)
        financials = await self._data.get_financials(ticker)
        metrics = await self._data.get_metrics(ticker)

        fund_result = self._fundamental.analyze(financials, metrics)

        # --- Margin of Safety (max 40) ---
        mos, mos_missing = self._score_margin_of_safety(fund_result, metrics, warnings)
        if mos_missing:
            missing_blocks += 1

        # --- Durable Competitive Advantage (max 35) ---
        dca, dca_missing = self._score_durable_advantage(fund_result, warnings)
        if dca_missing:
            missing_blocks += 1

        # --- Management Quality (max 25) ---
        mq, mq_missing = self._score_management_quality(fund_result, metrics, warnings)
        if mq_missing:
            missing_blocks += 1

        total_score = mos + dca + mq

        confidence = max(0.0, 1.0 - (missing_blocks / total_blocks) * 0.3)

        if total_score >= 75.0:
            signal = "Bullish"
        elif total_score >= 50.0:
            signal = "Neutral"
        else:
            signal = "Bearish"

        rationale = (
            f"Buffett value analysis for {ticker}: "
            f"Margin of Safety={mos:.1f}/{self._MAX_MARGIN_OF_SAFETY}, "
            f"Durable Advantage={dca:.1f}/{self._MAX_DURABLE_ADVANTAGE}, "
            f"Management Quality={mq:.1f}/{self._MAX_MANAGEMENT_QUALITY}"
        )

        return AgentResult(
            signal=signal,
            score=total_score,
            confidence=round(confidence, 2),
            rationale=rationale,
            breakdown={
                "margin_of_safety": mos,
                "durable_advantage": dca,
                "management_quality": mq,
            },
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _score_margin_of_safety(
        self,
        fund: FundamentalResult,
        metrics: Any,
        warnings: list[str],
    ) -> tuple[float, bool]:
        """Margin of safety: low P/E, low P/B, high FCF yield (max 40)."""
        score = 0.0
        available = 0

        pe = fund.valuation.get("pe_ratio")
        pb = fund.valuation.get("pb_ratio")
        fcf_yield = fund.valuation.get("fcf_yield")

        if pe is not None:
            available += 1
            if pe <= 0:
                score += 0.0
            elif pe <= 12:
                score += 15.0
            elif pe <= 20:
                score += 10.0
            elif pe <= 30:
                score += 5.0

        if pb is not None:
            available += 1
            if pb <= 1.0:
                score += 15.0
            elif pb <= 2.0:
                score += 10.0
            elif pb <= 3.0:
                score += 5.0

        if fcf_yield is not None:
            available += 1
            if fcf_yield >= 0.08:
                score += 10.0
            elif fcf_yield >= 0.05:
                score += 7.0
            elif fcf_yield >= 0.03:
                score += 4.0
            elif fcf_yield > 0:
                score += 1.0

        if available == 0:
            warnings.append("No valuation data for margin of safety")
            return 0.0, True

        return min(self._MAX_MARGIN_OF_SAFETY, score), False

    def _score_durable_advantage(
        self, fund: FundamentalResult, warnings: list[str],
    ) -> tuple[float, bool]:
        """Durable competitive advantage: high ROE, strong margins (max 35)."""
        score = 0.0
        available = 0

        roe = fund.profitability.get("roe")
        net_margin = fund.profitability.get("net_margin")
        gross_margin = fund.profitability.get("gross_margin")

        if roe is not None:
            available += 1
            # Buffett likes ROE > 15% consistently
            if roe >= 0.20:
                score += 15.0
            elif roe >= 0.15:
                score += 10.0
            elif roe >= 0.10:
                score += 5.0

        if net_margin is not None:
            available += 1
            if net_margin >= 0.20:
                score += 10.0
            elif net_margin >= 0.10:
                score += 7.0
            elif net_margin >= 0.05:
                score += 3.0

        if gross_margin is not None:
            available += 1
            # > 40% suggests durable advantage
            if gross_margin >= 0.40:
                score += 10.0
            elif gross_margin >= 0.30:
                score += 7.0
            elif gross_margin >= 0.20:
                score += 3.0

        if available == 0:
            warnings.append("No profitability data for durable advantage assessment")
            return 0.0, True

        return min(self._MAX_DURABLE_ADVANTAGE, score), False

    def _score_management_quality(
        self,
        fund: FundamentalResult,
        metrics: Any,
        warnings: list[str],
    ) -> tuple[float, bool]:
        """Management quality: ROA, low debt, capital efficiency (max 25)."""
        score = 0.0
        available = 0

        roa = fund.profitability.get("roa")
        debt_to_equity = fund.stability.get("debt_to_equity")
        current_ratio = fund.stability.get("current_ratio")

        if roa is not None:
            available += 1
            if roa >= 0.15:
                score += 10.0
            elif roa >= 0.10:
                score += 7.0
            elif roa >= 0.05:
                score += 3.0

        if debt_to_equity is not None:
            available += 1
            # Buffett prefers low debt
            if debt_to_equity <= 0.3:
                score += 10.0
            elif debt_to_equity <= 0.5:
                score += 7.0
            elif debt_to_equity <= 1.0:
                score += 4.0

        if current_ratio is not None:
            available += 1
            if current_ratio >= 2.0:
                score += 5.0
            elif current_ratio >= 1.5:
                score += 3.0
            elif current_ratio >= 1.0:
                score += 1.0

        if available == 0:
            warnings.append("No data for management quality assessment")
            return 0.0, True

        return min(self._MAX_MANAGEMENT_QUALITY, score), False
