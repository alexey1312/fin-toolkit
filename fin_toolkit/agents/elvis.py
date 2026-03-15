"""Elvis Marlamov 'Future Blue Chips' analysis agent."""

from __future__ import annotations

from datetime import datetime, timedelta

from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.models.results import AgentResult, FundamentalResult
from fin_toolkit.providers.protocol import DataProvider
from fin_toolkit.providers.search_protocol import SearchProvider

# ---------------------------------------------------------------------------
# Catalyst keywords for corporate event detection (EN + RU)
# ---------------------------------------------------------------------------

_POSITIVE_CATALYSTS: frozenset[str] = frozenset({
    # M&A
    "acquisition", "acquire", "merger", "takeover", "buyout",
    "поглощение", "слияние", "приобретение", "скупка",
    # Shareholder returns
    "buyback", "repurchase", "обратный выкуп",
    "dividend increase", "повышение дивидендов", "рост дивидендов",
    # Corporate events
    "reorganization", "restructuring", "реорганизация", "реструктуризация",
    "spin-off", "выделение",
    # Index / listing
    "index inclusion", "включение в индекс",
    # Strategic
    "strategic investor", "стратегический инвестор",
    "upgrade", "повышение рейтинга",
})

_NEGATIVE_CATALYSTS: frozenset[str] = frozenset({
    "dilution", "размытие",
    "bankruptcy", "банкротство",
    "default", "дефолт",
    "sanctions", "санкции",
    "investigation", "расследование",
    "downgrade", "понижение рейтинга",
    "sell-off", "распродажа",
    "fraud", "мошенничество",
})


class ElvisMarlamovAgent:
    """Agent inspired by Elvis Marlamov's 'Future Blue Chips' methodology.

    Elvis Marlamov is a Russian investor and founder of Alenka Capital, known
    for finding deeply undervalued second-tier stocks with corporate catalysts
    (M&A, reorganizations, index inclusions).  He groups emitters by sector,
    compares multiples within each sector, and hunts for events that unlock
    hidden value.  "A stock is a share in a business, not a trading instrument."

    Scoring blocks (max 100):
        - Valuation (35): P/E, P/BV, EV/EBITDA, dividend yield, FCF yield
        - Quality (25): ROE, net margin, gross margin
        - Catalysts (25): M&A, corporate events, strategic moves via search
        - Financial Health (15): D/E, current ratio, interest coverage
    """

    # Scoring block maximums
    _MAX_VALUATION = 35.0
    _MAX_QUALITY = 25.0
    _MAX_CATALYSTS = 25.0
    _MAX_FINANCIAL_HEALTH = 15.0

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
        """Run Elvis Marlamov-style 'Future Blue Chips' analysis on a ticker."""
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

        # --- Valuation score (max 35) — deep value focus ---
        valuation, v_missing = self._score_valuation(fund_result, warnings)
        if v_missing:
            missing_blocks += 1

        # --- Quality score (max 25) ---
        quality, q_missing = self._score_quality(fund_result, warnings)
        if q_missing:
            missing_blocks += 1

        # --- Catalysts score (max 25) — corporate events ---
        if self._search is None:
            warnings.append("No search provider — catalyst score is 0")
            catalysts = 0.0
            missing_blocks += 1
        else:
            catalysts = await self._score_catalysts(ticker)

        # --- Financial Health score (max 15) — deleveraging focus ---
        fin_health, fh_missing = self._score_financial_health(fund_result, warnings)
        if fh_missing:
            missing_blocks += 1

        total_score = valuation + quality + catalysts + fin_health

        # Confidence: 1.0 base, reduced proportionally per missing block
        confidence = max(0.0, 1.0 - (missing_blocks / total_blocks) * 0.25)

        # Signal classification
        if total_score >= 70.0:
            signal = "Bullish"
        elif total_score >= 40.0:
            signal = "Neutral"
        else:
            signal = "Bearish"

        rationale = (
            f"Elvis Marlamov 'Future Blue Chips' analysis for {ticker}: "
            f"Valuation={valuation:.1f}/{self._MAX_VALUATION}, "
            f"Quality={quality:.1f}/{self._MAX_QUALITY}, "
            f"Catalysts={catalysts:.1f}/{self._MAX_CATALYSTS}, "
            f"Financial Health={fin_health:.1f}/{self._MAX_FINANCIAL_HEALTH}"
        )

        return AgentResult(
            signal=signal,
            score=total_score,
            confidence=round(confidence, 2),
            rationale=rationale,
            breakdown={
                "valuation": valuation,
                "quality": quality,
                "catalysts": catalysts,
                "financial_health": fin_health,
            },
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Valuation (max 35) — deep value focus
    # ------------------------------------------------------------------

    def _score_valuation(
        self, fund: FundamentalResult, warnings: list[str],
    ) -> tuple[float, bool]:
        """Score valuation from fundamentals (max 35).

        Elvis prizes very low multiples: P/E under 5, P/BV below book,
        low EV/EBITDA, and generous dividend yield.
        """
        score = 0.0
        available = 0

        pe = fund.valuation.get("pe_ratio")
        pb = fund.valuation.get("pb_ratio")
        ev_ebitda = fund.valuation.get("ev_ebitda")
        div_yield = fund.valuation.get("dividend_yield")
        fcf_yield = fund.valuation.get("fcf_yield")

        # P/E — deeply undervalued preferred (max 10 pts)
        if pe is not None:
            available += 1
            if pe > 0:
                if pe <= 5:
                    score += 10.0
                elif pe <= 10:
                    score += 7.0
                elif pe <= 20:
                    score += 4.0
                elif pe <= 30:
                    score += 2.0

        # P/BV — below book value is ideal (max 8 pts)
        if pb is not None:
            available += 1
            if pb <= 0.7:
                score += 8.0
            elif pb <= 1.0:
                score += 6.0
            elif pb <= 1.5:
                score += 4.0
            elif pb <= 3.0:
                score += 2.0

        # EV/EBITDA (max 7 pts)
        if ev_ebitda is not None and ev_ebitda > 0:
            available += 1
            if ev_ebitda <= 5:
                score += 7.0
            elif ev_ebitda <= 8:
                score += 5.0
            elif ev_ebitda <= 12:
                score += 3.0
            elif ev_ebitda <= 20:
                score += 1.0

        # Dividend yield (max 6 pts)
        if div_yield is not None:
            available += 1
            if div_yield >= 0.08:
                score += 6.0
            elif div_yield >= 0.05:
                score += 4.0
            elif div_yield >= 0.03:
                score += 3.0
            elif div_yield >= 0.01:
                score += 1.0

        # FCF yield (max 4 pts)
        if fcf_yield is not None:
            available += 1
            if fcf_yield >= 0.10:
                score += 4.0
            elif fcf_yield >= 0.05:
                score += 3.0
            elif fcf_yield >= 0.03:
                score += 2.0
            elif fcf_yield > 0:
                score += 1.0

        if available == 0:
            warnings.append("No valuation metrics available")
            return 0.0, True

        return min(self._MAX_VALUATION, score), False

    # ------------------------------------------------------------------
    # Quality (max 25)
    # ------------------------------------------------------------------

    def _score_quality(
        self, fund: FundamentalResult, warnings: list[str],
    ) -> tuple[float, bool]:
        """Score business quality (max 25)."""
        score = 0.0
        available = 0

        roe = fund.profitability.get("roe")
        net_margin = fund.profitability.get("net_margin")
        gross_margin = fund.profitability.get("gross_margin")

        # ROE (max 10 pts)
        if roe is not None and roe > 0:
            available += 1
            if roe >= 0.20:
                score += 10.0
            elif roe >= 0.15:
                score += 7.0
            elif roe >= 0.10:
                score += 4.0
            elif roe >= 0.05:
                score += 2.0

        # Net margin (max 8 pts)
        if net_margin is not None and net_margin > 0:
            available += 1
            if net_margin >= 0.20:
                score += 8.0
            elif net_margin >= 0.10:
                score += 5.0
            elif net_margin >= 0.05:
                score += 3.0
            elif net_margin > 0:
                score += 1.0

        # Gross margin (max 7 pts)
        if gross_margin is not None and gross_margin > 0:
            available += 1
            if gross_margin >= 0.40:
                score += 7.0
            elif gross_margin >= 0.25:
                score += 4.0
            elif gross_margin >= 0.15:
                score += 2.0

        if available == 0:
            warnings.append("No quality metrics available")
            return 0.0, True

        return min(self._MAX_QUALITY, score), False

    # ------------------------------------------------------------------
    # Catalysts (max 25) — corporate event detection
    # ------------------------------------------------------------------

    async def _score_catalysts(self, ticker: str) -> float:
        """Score catalyst potential via search for corporate events (max 25).

        Elvis's main edge: detecting M&A, reorganizations, index inclusions,
        strategic investor moves, and buybacks before the crowd.
        """
        if self._search is None:
            return 0.0

        results = await self._search.search(
            f"{ticker} acquisition merger buyback dividend restructuring",
            max_results=5,
        )
        if not results:
            return 12.5  # neutral when no results

        positive_count = 0
        negative_count = 0

        for r in results:
            text = (r.title + " " + r.snippet).lower()
            for kw in _POSITIVE_CATALYSTS:
                if kw in text:
                    positive_count += 1
            for kw in _NEGATIVE_CATALYSTS:
                if kw in text:
                    negative_count += 1

        total = positive_count + negative_count
        if total == 0:
            return 12.5  # neutral

        ratio = positive_count / total
        return min(self._MAX_CATALYSTS, ratio * self._MAX_CATALYSTS)

    # ------------------------------------------------------------------
    # Financial Health (max 15) — deleveraging focus
    # ------------------------------------------------------------------

    def _score_financial_health(
        self, fund: FundamentalResult, warnings: list[str],
    ) -> tuple[float, bool]:
        """Score financial health (max 15).

        Elvis watches for deleveraging: companies actively reducing debt
        are more attractive.
        """
        score = 0.0
        available = 0

        de = fund.stability.get("debt_to_equity")
        cr = fund.stability.get("current_ratio")
        ic = fund.stability.get("interest_coverage")

        # D/E — lower is better (max 8 pts)
        if de is not None:
            available += 1
            if de <= 0.3:
                score += 8.0
            elif de <= 0.5:
                score += 6.0
            elif de <= 1.0:
                score += 4.0
            elif de <= 2.0:
                score += 2.0

        # Current ratio (max 4 pts)
        if cr is not None:
            available += 1
            if cr >= 2.0:
                score += 4.0
            elif cr >= 1.5:
                score += 3.0
            elif cr >= 1.0:
                score += 2.0

        # Interest coverage (max 3 pts)
        if ic is not None and ic > 0:
            available += 1
            if ic >= 10.0:
                score += 3.0
            elif ic >= 5.0:
                score += 2.0
            elif ic >= 2.0:
                score += 1.0

        if available == 0:
            warnings.append("No financial health metrics available")
            return 0.0, True

        return min(self._MAX_FINANCIAL_HEALTH, score), False
