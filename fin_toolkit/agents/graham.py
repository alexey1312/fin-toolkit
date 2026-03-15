"""Ben Graham analysis agent."""

from __future__ import annotations

from datetime import datetime, timedelta

from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.models.results import AgentResult, FundamentalResult
from fin_toolkit.providers.protocol import DataProvider


class BenGrahamAgent:
    """Agent inspired by Ben Graham's defensive value investing.

    Based on Graham's 7 criteria from "The Intelligent Investor" Ch. 14:
    1. Adequate size (not micro-cap)
    2. Current ratio ≥ 2.0
    3. Long-term debt ≤ net current assets
    4. Positive earnings for 10 consecutive years
    5. Uninterrupted dividends for 20+ years
    6. P/E ≤ 15 (3-year avg earnings)
    7. P/E × P/B ≤ 22.5 (the "Graham Number" rule)

    Scoring blocks (max 100):
        - Net-Net Value (35): P/E, P/B, Graham Number, FCF yield
        - Earnings Stability (30): margins, dividend yield, moderate ROE
        - Financial Strength (35): current ratio ≥ 2, low debt, interest coverage
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
        net_net, nn_missing = self._score_net_net(fund_result, warnings)
        if nn_missing:
            missing_blocks += 1

        # --- Earnings Stability (max 30) ---
        earnings, e_missing = self._score_earnings_stability(fund_result, warnings)
        if e_missing:
            missing_blocks += 1

        # --- Financial Strength (max 35) ---
        strength, s_missing = self._score_financial_strength(fund_result, warnings)
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
            f"Ben Graham defensive value analysis for {ticker}: "
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
        warnings: list[str],
    ) -> tuple[float, bool]:
        """Net-net value: P/B below book, low P/E, Graham Number (max 35).

        Graham's rule: P/E × P/B should not exceed 22.5.
        Buying below net current asset value is ideal.
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
                pass  # negative earnings
            elif pe <= 10:
                score += 12.0
            elif pe <= 15:
                score += 8.0
            elif pe <= 20:
                score += 3.0

        # Graham Number: P/E × P/B should not exceed 22.5
        if pe is not None and pb is not None and pe > 0:
            graham_product = pe * pb
            if graham_product <= 15.0:
                score += 5.0
            elif graham_product <= 22.5:
                score += 3.0
            # > 22.5 → fails Graham's criterion, no bonus

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
        warnings: list[str],
    ) -> tuple[float, bool]:
        """Earnings stability: positive earnings, dividends, margins (max 30).

        Graham required 10 years of positive earnings and 20 years of
        uninterrupted dividends.  We proxy with margin health and
        dividend yield as stability signals.
        """
        score = 0.0
        available = 0

        net_margin = fund.profitability.get("net_margin")
        roe = fund.profitability.get("roe")
        gross_margin = fund.profitability.get("gross_margin")
        div_yield = fund.valuation.get("dividend_yield")

        if net_margin is not None:
            available += 1
            # Positive and stable earnings
            if net_margin >= 0.10:
                score += 10.0
            elif net_margin >= 0.05:
                score += 7.0
            elif net_margin > 0:
                score += 3.0

        if roe is not None:
            available += 1
            # Moderate ROE preferred (not excessively high = risky leverage)
            if 0.10 <= roe <= 0.25:
                score += 8.0
            elif roe > 0.25:
                score += 5.0  # too high may indicate leverage
            elif roe >= 0.05:
                score += 3.0

        if gross_margin is not None:
            available += 1
            if gross_margin >= 0.30:
                score += 6.0
            elif gross_margin >= 0.20:
                score += 4.0
            elif gross_margin >= 0.10:
                score += 2.0

        # Dividend yield — Graham valued uninterrupted dividends
        if div_yield is not None:
            available += 1
            if div_yield >= 0.04:
                score += 6.0
            elif div_yield >= 0.02:
                score += 4.0
            elif div_yield > 0:
                score += 2.0

        if available == 0:
            warnings.append("No earnings data for stability assessment")
            return 0.0, True

        return min(self._MAX_EARNINGS, score), False

    def _score_financial_strength(
        self,
        fund: FundamentalResult,
        warnings: list[str],
    ) -> tuple[float, bool]:
        """Financial strength: current ratio ≥ 2, low debt (max 35).

        Graham's classic rules: current assets ≥ 2× current liabilities,
        long-term debt ≤ net current assets, adequate interest coverage.
        """
        score = 0.0
        available = 0

        current_ratio = fund.stability.get("current_ratio")
        debt_to_equity = fund.stability.get("debt_to_equity")
        roa = fund.profitability.get("roa")
        interest_coverage = fund.stability.get("interest_coverage")

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

        # Interest coverage — Graham's defensive criterion
        if interest_coverage is not None and interest_coverage > 0:
            available += 1
            if interest_coverage >= 10.0:
                score += 5.0
            elif interest_coverage >= 5.0:
                score += 3.0
            elif interest_coverage >= 2.0:
                score += 1.0

        if available == 0:
            warnings.append("No data for financial strength assessment")
            return 0.0, True

        return min(self._MAX_STRENGTH, score), False
