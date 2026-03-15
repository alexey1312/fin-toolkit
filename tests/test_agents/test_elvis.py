"""Tests for ElvisMarlamovAgent."""

from __future__ import annotations

from fin_toolkit.agents.elvis import ElvisMarlamovAgent
from fin_toolkit.agents.protocol import AnalysisAgent
from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData, PricePoint
from fin_toolkit.models.results import AgentResult, SearchResult

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_prices(ticker: str = "VALUE", count: int = 60, base: float = 150.0) -> PriceData:
    """Create synthetic price data with upward trend."""
    return PriceData(
        ticker=ticker,
        period="1y",
        prices=[
            PricePoint(
                date=f"2024-01-{(i % 28) + 1:02d}",
                open=base + i,
                high=base + i + 5,
                low=base + i - 2,
                close=base + i + 2,
                volume=1_000_000,
            )
            for i in range(count)
        ],
    )


def _make_value_financials(ticker: str = "VALUE") -> FinancialStatements:
    """Deep value company with solid fundamentals — Elvis's ideal pick."""
    return FinancialStatements(
        ticker=ticker,
        income_statement={
            "revenue": 100_000_000_000,
            "net_income": 25_000_000_000,
            "gross_profit": 45_000_000_000,
            "operating_income": 30_000_000_000,
            "interest_expense": 1_000_000_000,
            "ebitda": 35_000_000_000,
        },
        balance_sheet={
            "total_assets": 200_000_000_000,
            "total_equity": 120_000_000_000,
            "total_debt": 40_000_000_000,
            "current_assets": 80_000_000_000,
            "current_liabilities": 35_000_000_000,
            "invested_capital": 160_000_000_000,
        },
        cash_flow={
            "operating_cash_flow": 28_000_000_000,
            "capital_expenditures": 5_000_000_000,
        },
    )


def _make_value_metrics(ticker: str = "VALUE") -> KeyMetrics:
    """Deep value metrics — low multiples, solid dividend."""
    return KeyMetrics(
        ticker=ticker,
        pe_ratio=4.0,
        pb_ratio=0.8,
        market_cap=100_000_000_000,
        dividend_yield=0.07,
        roe=0.21,
        roa=0.125,
        debt_to_equity=0.33,
        enterprise_value=130_000_000_000,
    )


def _make_weak_financials(ticker: str = "BAD") -> FinancialStatements:
    return FinancialStatements(
        ticker=ticker,
        income_statement={
            "revenue": 10_000_000,
            "net_income": -5_000_000,
            "gross_profit": 2_000_000,
            "operating_income": -3_000_000,
            "interest_expense": 2_000_000,
            "ebitda": -1_000_000,
        },
        balance_sheet={
            "total_assets": 20_000_000,
            "total_equity": 5_000_000,
            "total_debt": 30_000_000,
            "current_assets": 3_000_000,
            "current_liabilities": 15_000_000,
            "invested_capital": 35_000_000,
            "enterprise_value": 50_000_000,
        },
        cash_flow={
            "operating_cash_flow": -2_000_000,
            "capital_expenditures": 1_000_000,
        },
    )


def _make_weak_metrics(ticker: str = "BAD") -> KeyMetrics:
    return KeyMetrics(
        ticker=ticker,
        pe_ratio=None,  # no P/E (negative earnings)
        pb_ratio=0.5,
        market_cap=10_000_000,
        dividend_yield=0.0,
        roe=-1.0,
        roa=-0.25,
        debt_to_equity=6.0,  # very high leverage
    )


def _make_sparse_financials(ticker: str = "SPARSE") -> FinancialStatements:
    """Financials with some data for margin computation."""
    return FinancialStatements(
        ticker=ticker,
        income_statement={
            "revenue": 400_000_000_000,
            "net_income": 100_000_000_000,
            "gross_profit": 170_000_000_000,
            "operating_income": 120_000_000_000,
            "interest_expense": 4_000_000_000,
            "ebitda": 135_000_000_000,
        },
        balance_sheet={
            "total_assets": 350_000_000_000,
            "total_equity": 100_000_000_000,
            "total_debt": 50_000_000_000,
            "current_assets": 160_000_000_000,
            "current_liabilities": 80_000_000_000,
            "invested_capital": 180_000_000_000,
        },
        cash_flow={
            "operating_cash_flow": 115_000_000_000,
            "capital_expenditures": 11_000_000_000,
        },
    )


class MockDataProvider:
    """Mock data provider returning configurable data."""

    def __init__(
        self,
        prices: PriceData | None = None,
        financials: FinancialStatements | None = None,
        metrics: KeyMetrics | None = None,
    ) -> None:
        self._prices = prices or _make_prices()
        self._financials = financials or _make_value_financials()
        self._metrics = metrics or _make_value_metrics()

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        return self._prices

    async def get_financials(self, ticker: str) -> FinancialStatements:
        return self._financials

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        return self._metrics


class MockCatalystSearchProvider:
    """Mock search returning M&A and dividend catalyst results."""

    def __init__(self, results: list[SearchResult] | None = None) -> None:
        self._results = results if results is not None else [
            SearchResult(
                title="Company announces major acquisition deal",
                url="https://example.com/1",
                snippet="Strategic acquisition expected to drive growth.",
                published_date="2024-01-15",
            ),
            SearchResult(
                title="Board approves dividend increase and buyback",
                url="https://example.com/2",
                snippet="Shareholders to benefit from repurchase program.",
                published_date="2024-01-14",
            ),
        ]

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return self._results


# ---------------------------------------------------------------------------
# Tests: scoring blocks
# ---------------------------------------------------------------------------


async def test_scoring_blocks_present() -> None:
    """Result breakdown has valuation, quality, catalysts, financial_health keys."""
    agent = ElvisMarlamovAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
        search=MockCatalystSearchProvider(),
    )
    result = await agent.analyze("VALUE")
    assert "valuation" in result.breakdown
    assert "quality" in result.breakdown
    assert "catalysts" in result.breakdown
    assert "financial_health" in result.breakdown


async def test_scoring_block_maximums() -> None:
    """Scoring blocks respect correct maximums."""
    agent = ElvisMarlamovAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
        search=MockCatalystSearchProvider(),
    )
    result = await agent.analyze("VALUE")
    assert result.breakdown["valuation"] <= 35.0
    assert result.breakdown["quality"] <= 25.0
    assert result.breakdown["catalysts"] <= 25.0
    assert result.breakdown["financial_health"] <= 15.0


# ---------------------------------------------------------------------------
# Tests: deep value stock → Bullish
# ---------------------------------------------------------------------------


async def test_value_stock_bullish() -> None:
    """Deep value stock with catalysts → Bullish (>=70)."""
    agent = ElvisMarlamovAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
        search=MockCatalystSearchProvider(),
    )
    result = await agent.analyze("VALUE")
    assert isinstance(result, AgentResult)
    assert result.signal == "Bullish"
    assert result.score >= 70.0


# ---------------------------------------------------------------------------
# Tests: weak stock → Bearish
# ---------------------------------------------------------------------------


async def test_weak_stock_bearish() -> None:
    """Weak fundamentals, high leverage, no catalysts → Bearish (<40)."""
    agent = ElvisMarlamovAgent(
        data_provider=MockDataProvider(
            prices=_make_prices("BAD", base=10.0),
            financials=_make_weak_financials(),
            metrics=_make_weak_metrics(),
        ),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("BAD")
    assert result.signal == "Bearish"
    assert result.score < 40.0


# ---------------------------------------------------------------------------
# Tests: without search → catalysts=0 + warning
# ---------------------------------------------------------------------------


async def test_no_search_provider_catalysts_zero() -> None:
    """Without SearchProvider, catalysts=0 and a warning is emitted."""
    agent = ElvisMarlamovAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
        search=None,
    )
    result = await agent.analyze("VALUE")
    assert result.breakdown["catalysts"] == 0.0
    assert any("catalyst" in w.lower() or "search" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# Tests: missing metrics → confidence reduced + warning
# ---------------------------------------------------------------------------


async def test_missing_metrics_reduces_confidence() -> None:
    """When key metrics are None, confidence is reduced and warnings are emitted."""
    sparse_metrics = KeyMetrics(
        ticker="SPARSE",
        pe_ratio=None,
        pb_ratio=None,
        market_cap=None,
        dividend_yield=None,
        roe=None,
        roa=None,
        debt_to_equity=None,
    )
    agent = ElvisMarlamovAgent(
        data_provider=MockDataProvider(
            financials=_make_sparse_financials(),
            metrics=sparse_metrics,
        ),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("SPARSE")
    assert result.confidence < 1.0
    assert len(result.warnings) > 0


# ---------------------------------------------------------------------------
# Tests: negative catalyst search results lower score
# ---------------------------------------------------------------------------


async def test_negative_catalysts_reduce_score() -> None:
    """Negative corporate events should lower the catalyst score."""
    negative_results = [
        SearchResult(
            title="Company faces bankruptcy proceedings",
            url="https://example.com/1",
            snippet="Investigation reveals potential fraud in financial statements.",
            published_date="2024-01-15",
        ),
        SearchResult(
            title="New sanctions imposed on the company",
            url="https://example.com/2",
            snippet="Stock sell-off continues after downgrade.",
            published_date="2024-01-14",
        ),
    ]
    agent = ElvisMarlamovAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
        search=MockCatalystSearchProvider(results=negative_results),
    )
    result = await agent.analyze("VALUE")
    # Negative catalysts → low catalyst score
    assert result.breakdown["catalysts"] < 12.5  # below neutral


# ---------------------------------------------------------------------------
# Tests: rationale mentions methodology
# ---------------------------------------------------------------------------


async def test_rationale_mentions_future_blue_chips() -> None:
    """Rationale should reference Elvis's 'Future Blue Chips' methodology."""
    agent = ElvisMarlamovAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("VALUE")
    assert "Future Blue Chips" in result.rationale


# ---------------------------------------------------------------------------
# Tests: protocol compliance
# ---------------------------------------------------------------------------


def test_elvis_satisfies_protocol() -> None:
    """ElvisMarlamovAgent satisfies the AnalysisAgent protocol."""
    agent = ElvisMarlamovAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    assert isinstance(agent, AnalysisAgent)
