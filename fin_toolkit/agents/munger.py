"""Charlie Munger analysis agent."""

from __future__ import annotations

from datetime import datetime, timedelta

from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.models.results import AgentResult, FundamentalResult
from fin_toolkit.providers.protocol import DataProvider


class CharlieMungerAgent:
    """Agent inspired by Charlie Munger's 'wonderful business at fair price'.

    Munger's approach: start with qualitative durability (brand, network
    effects, switching costs, culture), then validate with unit economics,
    ROIC, FCF conversion, and pricing power through cycles.

    "All intelligent investing is value investing — acquiring more than
    you are paying for."

    Scoring blocks (max 100):
        - Business Quality (45): ROIC, ROE, gross margin (moat), net margin, ROA
        - Fair Price (30): P/E, P/B, EV/EBITDA, FCF yield (tolerant of higher
          multiples for truly wonderful businesses)
        - Financial Fortress (25): low debt, interest coverage, current ratio
    """

    _MAX_QUALITY = 45.0
    _MAX_FAIR_PRICE = 30.0
    _MAX_FORTRESS = 25.0

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
        """Run Munger-style quality-at-fair-price analysis."""
        warnings: list[str] = []
        missing_blocks = 0
        total_blocks = 3

        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        await self._data.get_prices(ticker, start, end)
        financials = await self._data.get_financials(ticker)
        metrics = await self._data.get_metrics(ticker)

        fund_result = self._fundamental.analyze(financials, metrics)

        # --- Business Quality (max 45) ---
        quality, q_missing = self._score_business_quality(fund_result, warnings)
        if q_missing:
            missing_blocks += 1

        # --- Fair Price (max 30) ---
        price, p_missing = self._score_fair_price(fund_result, warnings)
        if p_missing:
            missing_blocks += 1

        # --- Financial Fortress (max 25) ---
        fortress, f_missing = self._score_financial_fortress(fund_result, warnings)
        if f_missing:
            missing_blocks += 1

        total_score = quality + price + fortress
        confidence = max(0.0, 1.0 - (missing_blocks / total_blocks) * 0.3)

        if total_score >= 75.0:
            signal = "Bullish"
        elif total_score >= 50.0:
            signal = "Neutral"
        else:
            signal = "Bearish"

        rationale = (
            f"Charlie Munger analysis for {ticker}: "
            f"Business Quality={quality:.1f}/{self._MAX_QUALITY}, "
            f"Fair Price={price:.1f}/{self._MAX_FAIR_PRICE}, "
            f"Financial Fortress={fortress:.1f}/{self._MAX_FORTRESS}"
        )

        return AgentResult(
            signal=signal,
            score=total_score,
            confidence=round(confidence, 2),
            rationale=rationale,
            breakdown={
                "business_quality": quality,
                "fair_price": price,
                "financial_fortress": fortress,
            },
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _score_business_quality(
        self, fund: FundamentalResult, warnings: list[str],
    ) -> tuple[float, bool]:
        """Business quality: ROIC, ROE, margins, moat indicators (max 45).

        Munger starts with qualitative durability then validates with
        ROIC and pricing power.  Gross margin > 60% is a strong moat
        signal (network effects, brand, switching costs).
        """
        score = 0.0
        available = 0

        roic = fund.profitability.get("roic")
        roe = fund.profitability.get("roe")
        net_margin = fund.profitability.get("net_margin")
        gross_margin = fund.profitability.get("gross_margin")
        roa = fund.profitability.get("roa")

        # ROIC — Munger's primary quantitative moat evidence
        if roic is not None:
            available += 1
            if roic >= 0.25:
                score += 10.0
            elif roic >= 0.15:
                score += 8.0
            elif roic >= 0.10:
                score += 5.0
            elif roic >= 0.05:
                score += 2.0

        if roe is not None:
            available += 1
            # Munger loves consistently high ROE (> 20%)
            if roe >= 0.25:
                score += 15.0
            elif roe >= 0.20:
                score += 12.0
            elif roe >= 0.15:
                score += 8.0
            elif roe >= 0.10:
                score += 4.0

        if gross_margin is not None:
            available += 1
            # High gross margin = moat indicator
            if gross_margin >= 0.60:
                score += 12.0
            elif gross_margin >= 0.40:
                score += 9.0
            elif gross_margin >= 0.30:
                score += 5.0
            elif gross_margin >= 0.20:
                score += 2.0

        if net_margin is not None:
            available += 1
            if net_margin >= 0.25:
                score += 10.0
            elif net_margin >= 0.15:
                score += 7.0
            elif net_margin >= 0.10:
                score += 4.0
            elif net_margin >= 0.05:
                score += 2.0

        if roa is not None:
            available += 1
            if roa >= 0.15:
                score += 8.0
            elif roa >= 0.10:
                score += 5.0
            elif roa >= 0.05:
                score += 2.0

        if available == 0:
            warnings.append("No profitability data for business quality assessment")
            return 0.0, True

        return min(self._MAX_QUALITY, score), False

    def _score_fair_price(
        self,
        fund: FundamentalResult,
        warnings: list[str],
    ) -> tuple[float, bool]:
        """Fair price: reasonable valuation — not cheap, but not overpriced (max 30).

        Munger accepts higher multiples for quality businesses, but still
        requires a meaningful discount to intrinsic value.
        """
        score = 0.0
        available = 0

        pe = fund.valuation.get("pe_ratio")
        pb = fund.valuation.get("pb_ratio")
        fcf_yield = fund.valuation.get("fcf_yield")
        ev_ebitda = fund.valuation.get("ev_ebitda")

        if pe is not None:
            available += 1
            # Munger tolerates higher PE for quality (up to ~25)
            if pe <= 0:
                pass  # negative earnings
            elif pe <= 15:
                score += 12.0
            elif pe <= 25:
                score += 9.0
            elif pe <= 35:
                score += 4.0

        if pb is not None:
            available += 1
            if pb <= 2.0:
                score += 10.0
            elif pb <= 4.0:
                score += 7.0
            elif pb <= 6.0:
                score += 3.0

        if fcf_yield is not None:
            available += 1
            if fcf_yield >= 0.06:
                score += 8.0
            elif fcf_yield >= 0.04:
                score += 5.0
            elif fcf_yield >= 0.02:
                score += 2.0

        # EV/EBITDA — Munger validates unit economics
        if ev_ebitda is not None and ev_ebitda > 0:
            available += 1
            if ev_ebitda <= 10:
                score += 7.0
            elif ev_ebitda <= 15:
                score += 4.0
            elif ev_ebitda <= 20:
                score += 2.0

        if available == 0:
            warnings.append("No valuation data for fair price assessment")
            return 0.0, True

        return min(self._MAX_FAIR_PRICE, score), False

    def _score_financial_fortress(
        self,
        fund: FundamentalResult,
        warnings: list[str],
    ) -> tuple[float, bool]:
        """Financial fortress: strong balance sheet (max 25).

        Munger: "The first rule of compounding: never interrupt it
        unnecessarily."  Strong balance sheet prevents forced selling.
        """
        score = 0.0
        available = 0

        debt_to_equity = fund.stability.get("debt_to_equity")
        current_ratio = fund.stability.get("current_ratio")
        interest_coverage = fund.stability.get("interest_coverage")

        if debt_to_equity is not None:
            available += 1
            if debt_to_equity <= 0.3:
                score += 13.0
            elif debt_to_equity <= 0.5:
                score += 10.0
            elif debt_to_equity <= 1.0:
                score += 5.0

        if current_ratio is not None:
            available += 1
            if current_ratio >= 2.0:
                score += 10.0
            elif current_ratio >= 1.5:
                score += 7.0
            elif current_ratio >= 1.0:
                score += 3.0

        # Interest coverage — compounding protection
        if interest_coverage is not None and interest_coverage > 0:
            available += 1
            if interest_coverage >= 10.0:
                score += 5.0
            elif interest_coverage >= 5.0:
                score += 3.0
            elif interest_coverage >= 2.0:
                score += 1.0

        if available == 0:
            warnings.append("No data for financial fortress assessment")
            return 0.0, True

        return min(self._MAX_FORTRESS, score), False
