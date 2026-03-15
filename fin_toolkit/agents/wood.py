"""Cathie Wood analysis agent."""

from __future__ import annotations

from datetime import datetime, timedelta

from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.models.results import AgentResult, FundamentalResult
from fin_toolkit.providers.protocol import DataProvider


class CathieWoodAgent:
    """Agent inspired by Cathie Wood's disruptive innovation investing.

    ARK Invest's methodology: identify companies benefiting from
    technological convergence across five innovation platforms (AI, energy
    storage, robotics, genomics, blockchain).  5-year revenue models,
    forward-looking growth potential over backward-looking metrics.

    "We are looking for companies that are on the right side of change."

    Scoring blocks (max 100):
        - Growth Signals (40): ROE, ROA, margin trajectory, reinvestment rate
        - Innovation Premium (30): accepts high P/E for disruptors, rewards
          cash burn for growth, FCF positive is bonus not requirement
        - Market Position (30): gross margin (platform/network effects),
          capital efficiency, manageable debt
    """

    _MAX_GROWTH = 40.0
    _MAX_INNOVATION = 30.0
    _MAX_POSITION = 30.0

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
        """Run Cathie Wood-style innovation/growth analysis."""
        warnings: list[str] = []
        missing_blocks = 0
        total_blocks = 3

        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        await self._data.get_prices(ticker, start, end)
        financials = await self._data.get_financials(ticker)
        metrics = await self._data.get_metrics(ticker)

        fund_result = self._fundamental.analyze(financials, metrics)

        # --- Growth Signals (max 40) ---
        growth, g_missing = self._score_growth_signals(fund_result, warnings)
        if g_missing:
            missing_blocks += 1

        # --- Innovation Premium (max 30) ---
        innovation, i_missing = self._score_innovation_premium(fund_result, warnings)
        if i_missing:
            missing_blocks += 1

        # --- Market Position (max 30) ---
        position, p_missing = self._score_market_position(fund_result, warnings)
        if p_missing:
            missing_blocks += 1

        total_score = growth + innovation + position
        confidence = max(0.0, 1.0 - (missing_blocks / total_blocks) * 0.3)

        if total_score >= 75.0:
            signal = "Bullish"
        elif total_score >= 50.0:
            signal = "Neutral"
        else:
            signal = "Bearish"

        rationale = (
            f"Cathie Wood disruptive growth analysis for {ticker}: "
            f"Growth Signals={growth:.1f}/{self._MAX_GROWTH}, "
            f"Innovation Premium={innovation:.1f}/{self._MAX_INNOVATION}, "
            f"Market Position={position:.1f}/{self._MAX_POSITION}"
        )

        return AgentResult(
            signal=signal,
            score=total_score,
            confidence=round(confidence, 2),
            rationale=rationale,
            breakdown={
                "growth_signals": growth,
                "innovation_premium": innovation,
                "market_position": position,
            },
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _score_growth_signals(
        self,
        fund: FundamentalResult,
        warnings: list[str],
    ) -> tuple[float, bool]:
        """Growth signals: high ROE, reinvestment, margin expansion (max 40).

        Wood focuses on companies reinvesting heavily in innovation.
        Low/zero dividend yield = reinvesting in growth (positive signal).
        High ROE + low dividends = efficient capital deployment.
        """
        score = 0.0
        available = 0

        roe = fund.profitability.get("roe")
        roa = fund.profitability.get("roa")
        net_margin = fund.profitability.get("net_margin")
        div_yield = fund.valuation.get("dividend_yield")

        if roe is not None:
            available += 1
            # High ROE = efficient capital deployment for growth
            if roe >= 0.30:
                score += 15.0
            elif roe >= 0.20:
                score += 12.0
            elif roe >= 0.15:
                score += 8.0
            elif roe >= 0.10:
                score += 4.0
            # Wood tolerates negative ROE for early-stage disruptors
            elif roe < 0:
                score += 2.0  # early-stage, not penalized heavily

        if roa is not None:
            available += 1
            if roa >= 0.15:
                score += 13.0
            elif roa >= 0.10:
                score += 9.0
            elif roa >= 0.05:
                score += 5.0
            elif roa > 0:
                score += 2.0

        if net_margin is not None:
            available += 1
            # Improving margins signal scaling
            if net_margin >= 0.20:
                score += 10.0
            elif net_margin >= 0.10:
                score += 7.0
            elif net_margin >= 0.0:
                score += 4.0  # breakeven is progress
            else:
                score += 2.0  # not-yet-profitable innovators

        # Low dividend yield = reinvesting in growth (Wood's preference)
        if div_yield is not None:
            available += 1
            if div_yield == 0.0:
                score += 5.0  # full reinvestment — ideal for growth
            elif div_yield <= 0.01:
                score += 3.0
            elif div_yield <= 0.02:
                score += 1.0
            # High dividend yield = mature company, less innovation

        if available == 0:
            warnings.append("No data for growth signals assessment")
            return 0.0, True

        return min(self._MAX_GROWTH, score), False

    def _score_innovation_premium(
        self,
        fund: FundamentalResult,
        warnings: list[str],
    ) -> tuple[float, bool]:
        """Innovation premium: growth justifies high multiples (max 30).

        Wood inverts traditional value logic: high PE can be bullish
        if the company is disrupting a large market.  Pre-profit
        innovators are not penalized.
        """
        score = 0.0
        available = 0

        pe = fund.valuation.get("pe_ratio")
        pb = fund.valuation.get("pb_ratio")
        fcf_yield = fund.valuation.get("fcf_yield")

        if pe is not None:
            available += 1
            # Wood's lens: moderate PE is ideal for growth,
            # very low PE may mean stagnation, very high may mean hype
            if pe <= 0:
                score += 5.0  # pre-profit innovator, not penalized
            elif 15 <= pe <= 50:
                score += 12.0  # growth-priced
            elif pe <= 15:
                score += 5.0  # cheap = maybe stagnant
            elif pe <= 80:
                score += 8.0  # expensive but possible
            else:
                score += 2.0  # frothy

        if pb is not None:
            available += 1
            # Asset-light innovators often have high P/B
            if 2.0 <= pb <= 10.0:
                score += 10.0  # typical growth range
            elif pb <= 2.0:
                score += 4.0  # asset-heavy, less innovative
            elif pb <= 20.0:
                score += 6.0
            else:
                score += 2.0

        if fcf_yield is not None:
            available += 1
            # Positive FCF is a bonus, but not required
            if fcf_yield >= 0.03:
                score += 8.0
            elif fcf_yield > 0:
                score += 5.0
            else:
                score += 3.0  # burning cash for growth is ok

        if available == 0:
            warnings.append("No valuation data for innovation premium assessment")
            return 0.0, True

        return min(self._MAX_INNOVATION, score), False

    def _score_market_position(
        self, fund: FundamentalResult, warnings: list[str],
    ) -> tuple[float, bool]:
        """Market position: gross margin as platform/network effect proxy (max 30).

        High gross margins suggest a differentiated product, platform
        economics, or network effects — key to disruptive scaling.
        """
        score = 0.0
        available = 0

        gross_margin = fund.profitability.get("gross_margin")
        roe = fund.profitability.get("roe")
        debt_to_equity = fund.stability.get("debt_to_equity")

        if gross_margin is not None:
            available += 1
            # High gross margin = strong market position / pricing power
            if gross_margin >= 0.70:
                score += 15.0
            elif gross_margin >= 0.50:
                score += 12.0
            elif gross_margin >= 0.40:
                score += 8.0
            elif gross_margin >= 0.25:
                score += 4.0

        if roe is not None:
            available += 1
            # Capital efficiency supports market dominance
            if roe >= 0.20:
                score += 10.0
            elif roe >= 0.10:
                score += 6.0
            elif roe > 0:
                score += 3.0
            else:
                score += 1.0

        if debt_to_equity is not None:
            available += 1
            # Moderate debt ok for growth; low debt = stronger
            if debt_to_equity <= 0.5:
                score += 5.0
            elif debt_to_equity <= 1.5:
                score += 3.0
            elif debt_to_equity <= 3.0:
                score += 1.0

        if available == 0:
            warnings.append("No data for market position assessment")
            return 0.0, True

        return min(self._MAX_POSITION, score), False
