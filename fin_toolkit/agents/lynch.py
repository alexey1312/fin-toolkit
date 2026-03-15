"""Peter Lynch analysis agent."""

from __future__ import annotations

from datetime import datetime, timedelta

from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.models.results import AgentResult, FundamentalResult
from fin_toolkit.providers.protocol import DataProvider


class PeterLynchAgent:
    """Agent inspired by Peter Lynch's GARP (Growth at a Reasonable Price).

    Lynch classified stocks into six categories: slow growers, stalwarts,
    fast growers, cyclicals, asset plays, and turnarounds.  His primary
    tool is the PEG ratio (P/E ÷ earnings growth rate), where PEG < 1 is
    a bargain.  He also used dividend-adjusted PEG:
        PEG_adj = P/E ÷ (growth% + dividend_yield%)

    "Know what you own, and know why you own it."

    Scoring blocks (max 100):
        - PEG Value (35): PEG ratio, dividend-adjusted PEG, P/B, FCF yield
        - Earnings Quality (35): ROE, ROIC, margins, consistent profitability
        - Common Sense (30): reasonable debt, cash flow, interest coverage
    """

    _MAX_PEG = 35.0
    _MAX_EARNINGS = 35.0
    _MAX_COMMON_SENSE = 30.0

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
        """Run Lynch-style GARP analysis."""
        warnings: list[str] = []
        missing_blocks = 0
        total_blocks = 3

        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        await self._data.get_prices(ticker, start, end)
        financials = await self._data.get_financials(ticker)
        metrics = await self._data.get_metrics(ticker)

        fund_result = self._fundamental.analyze(financials, metrics)

        # --- PEG Value (max 35) ---
        peg, peg_missing = self._score_peg_value(fund_result, warnings)
        if peg_missing:
            missing_blocks += 1

        # --- Earnings Quality (max 35) ---
        earnings, e_missing = self._score_earnings_quality(fund_result, warnings)
        if e_missing:
            missing_blocks += 1

        # --- Common Sense (max 30) ---
        common, c_missing = self._score_common_sense(fund_result, warnings)
        if c_missing:
            missing_blocks += 1

        total_score = peg + earnings + common
        confidence = max(0.0, 1.0 - (missing_blocks / total_blocks) * 0.3)

        if total_score >= 75.0:
            signal = "Bullish"
        elif total_score >= 50.0:
            signal = "Neutral"
        else:
            signal = "Bearish"

        rationale = (
            f"Peter Lynch GARP analysis for {ticker}: "
            f"PEG Value={peg:.1f}/{self._MAX_PEG}, "
            f"Earnings Quality={earnings:.1f}/{self._MAX_EARNINGS}, "
            f"Common Sense={common:.1f}/{self._MAX_COMMON_SENSE}"
        )

        return AgentResult(
            signal=signal,
            score=total_score,
            confidence=round(confidence, 2),
            rationale=rationale,
            breakdown={
                "peg_value": peg,
                "earnings_quality": earnings,
                "common_sense": common,
            },
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _score_peg_value(
        self,
        fund: FundamentalResult,
        warnings: list[str],
    ) -> tuple[float, bool]:
        """PEG-style value: P/E relative to growth (max 35).

        Lynch's rule: PEG < 1 is a bargain, PEG > 2 is overpriced.
        Dividend-adjusted PEG = P/E ÷ (growth% + dividend_yield%).
        Growth rate is approximated from ROE (sustainable growth ≈ ROE).
        """
        score = 0.0
        available = 0

        pe = fund.valuation.get("pe_ratio")
        roe = fund.profitability.get("roe")
        div_yield = fund.valuation.get("dividend_yield")

        if pe is not None and roe is not None and roe > 0:
            available += 1
            # Implied growth rate ≈ ROE (assuming high retention)
            growth_pct = roe * 100  # e.g., ROE 0.20 → 20% growth
            # Dividend-adjusted PEG (Lynch's actual formula)
            div_pct = (div_yield or 0.0) * 100
            adjusted_growth = growth_pct + div_pct
            if adjusted_growth > 0 and pe > 0:
                peg_ratio = pe / adjusted_growth
                if peg_ratio <= 0.5:
                    score += 20.0
                elif peg_ratio <= 1.0:
                    score += 15.0
                elif peg_ratio <= 1.5:
                    score += 10.0
                elif peg_ratio <= 2.0:
                    score += 5.0
                # PEG > 2 → 0 points
        elif pe is not None:
            available += 1
            # Fallback: just use PE
            if pe <= 0:
                pass
            elif pe <= 15:
                score += 12.0
            elif pe <= 25:
                score += 7.0

        pb = fund.valuation.get("pb_ratio")
        if pb is not None:
            available += 1
            if pb <= 1.5:
                score += 10.0
            elif pb <= 3.0:
                score += 7.0
            elif pb <= 5.0:
                score += 3.0

        fcf_yield = fund.valuation.get("fcf_yield")
        if fcf_yield is not None:
            available += 1
            if fcf_yield >= 0.06:
                score += 5.0
            elif fcf_yield >= 0.03:
                score += 3.0
            elif fcf_yield > 0:
                score += 1.0

        if available == 0:
            warnings.append("No valuation data for PEG assessment")
            return 0.0, True

        return min(self._MAX_PEG, score), False

    def _score_earnings_quality(
        self, fund: FundamentalResult, warnings: list[str],
    ) -> tuple[float, bool]:
        """Earnings quality: strong, consistent profitability (max 35).

        Lynch: "Know what you own, and know why you own it."
        ROIC indicates capital efficiency beyond simple profitability.
        """
        score = 0.0
        available = 0

        roe = fund.profitability.get("roe")
        net_margin = fund.profitability.get("net_margin")
        gross_margin = fund.profitability.get("gross_margin")
        roa = fund.profitability.get("roa")
        roic = fund.profitability.get("roic")

        if roe is not None:
            available += 1
            if roe >= 0.20:
                score += 12.0
            elif roe >= 0.15:
                score += 9.0
            elif roe >= 0.10:
                score += 5.0
            elif roe >= 0.05:
                score += 2.0

        if net_margin is not None:
            available += 1
            if net_margin >= 0.15:
                score += 10.0
            elif net_margin >= 0.10:
                score += 7.0
            elif net_margin >= 0.05:
                score += 4.0
            elif net_margin > 0:
                score += 1.0

        if gross_margin is not None:
            available += 1
            if gross_margin >= 0.40:
                score += 8.0
            elif gross_margin >= 0.30:
                score += 5.0
            elif gross_margin >= 0.20:
                score += 3.0

        if roa is not None:
            available += 1
            if roa >= 0.12:
                score += 5.0
            elif roa >= 0.08:
                score += 3.0
            elif roa >= 0.04:
                score += 1.0

        # ROIC — capital efficiency (Lynch valued understanding the business)
        if roic is not None:
            available += 1
            if roic >= 0.15:
                score += 5.0
            elif roic >= 0.10:
                score += 3.0
            elif roic >= 0.05:
                score += 1.0

        if available == 0:
            warnings.append("No earnings data for quality assessment")
            return 0.0, True

        return min(self._MAX_EARNINGS, score), False

    def _score_common_sense(
        self,
        fund: FundamentalResult,
        warnings: list[str],
    ) -> tuple[float, bool]:
        """Common sense checks: debt, cash flow, balance sheet health (max 30).

        Lynch: "Go for a business that any idiot can run — because sooner
        or later, any idiot probably is going to run it."
        """
        score = 0.0
        available = 0

        debt_to_equity = fund.stability.get("debt_to_equity")
        current_ratio = fund.stability.get("current_ratio")
        fcf_yield = fund.valuation.get("fcf_yield")
        interest_coverage = fund.stability.get("interest_coverage")

        if debt_to_equity is not None:
            available += 1
            if debt_to_equity <= 0.3:
                score += 12.0
            elif debt_to_equity <= 0.7:
                score += 8.0
            elif debt_to_equity <= 1.5:
                score += 4.0

        if current_ratio is not None:
            available += 1
            if current_ratio >= 2.0:
                score += 8.0
            elif current_ratio >= 1.5:
                score += 5.0
            elif current_ratio >= 1.0:
                score += 2.0

        if fcf_yield is not None:
            available += 1
            # Positive free cash flow = sustainable business
            if fcf_yield >= 0.05:
                score += 8.0
            elif fcf_yield >= 0.02:
                score += 5.0
            elif fcf_yield > 0:
                score += 2.0

        # Interest coverage — can the business handle its debt?
        if interest_coverage is not None and interest_coverage > 0:
            available += 1
            if interest_coverage >= 10.0:
                score += 5.0
            elif interest_coverage >= 5.0:
                score += 3.0
            elif interest_coverage >= 2.0:
                score += 1.0

        if available == 0:
            warnings.append("No data for common sense assessment")
            return 0.0, True

        return min(self._MAX_COMMON_SENSE, score), False
