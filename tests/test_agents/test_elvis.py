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

def _make_prices(ticker: str = "AAPL", count: int = 60, base: float = 150.0) -> PriceData:
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


def _make_strong_financials(ticker: str = "AAPL") -> FinancialStatements:
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
            "enterprise_value": 3_000_000_000_000,
        },
        cash_flow={
            "operating_cash_flow": 115_000_000_000,
            "capital_expenditures": 11_000_000_000,
        },
    )


def _make_strong_metrics(ticker: str = "AAPL") -> KeyMetrics:
    return KeyMetrics(
        ticker=ticker,
        pe_ratio=15.0,  # low P/E = good value
        pb_ratio=3.0,
        market_cap=3_000_000_000_000,
        dividend_yield=0.02,
        roe=1.0,  # 100% ROE = excellent
        roa=0.28,
        debt_to_equity=0.5,  # low D/E = stable
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


class MockDataProvider:
    """Mock data provider returning configurable data."""

    def __init__(
        self,
        prices: PriceData | None = None,
        financials: FinancialStatements | None = None,
        metrics: KeyMetrics | None = None,
    ) -> None:
        self._prices = prices or _make_prices()
        self._financials = financials or _make_strong_financials()
        self._metrics = metrics or _make_strong_metrics()

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        return self._prices

    async def get_financials(self, ticker: str) -> FinancialStatements:
        return self._financials

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        return self._metrics


class MockSearchProvider:
    """Mock search provider returning positive sentiment results."""

    def __init__(self, results: list[SearchResult] | None = None) -> None:
        self._results = results if results is not None else [
            SearchResult(
                title="Stock surges on strong earnings",
                url="https://example.com/1",
                snippet="The company reported record earnings, exceeding expectations.",
                published_date="2024-01-15",
            ),
            SearchResult(
                title="Analysts upgrade stock to buy",
                url="https://example.com/2",
                snippet="Multiple analysts have upgraded their rating to buy.",
                published_date="2024-01-14",
            ),
        ]

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return self._results


# ---------------------------------------------------------------------------
# Tests: scoring blocks
# ---------------------------------------------------------------------------

async def test_scoring_blocks_present() -> None:
    """Result breakdown has quality, stability, valuation, sentiment keys."""
    agent = ElvisMarlamovAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
        search=MockSearchProvider(),
    )
    result = await agent.analyze("AAPL")
    assert "quality" in result.breakdown
    assert "stability" in result.breakdown
    assert "valuation" in result.breakdown
    assert "sentiment" in result.breakdown


async def test_scoring_block_maximums() -> None:
    """Scoring blocks respect correct maximums."""
    agent = ElvisMarlamovAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
        search=MockSearchProvider(),
    )
    result = await agent.analyze("AAPL")
    assert result.breakdown["quality"] <= 40.0
    assert result.breakdown["stability"] <= 20.0
    assert result.breakdown["valuation"] <= 30.0
    assert result.breakdown["sentiment"] <= 10.0


# ---------------------------------------------------------------------------
# Tests: strong stock → Bullish
# ---------------------------------------------------------------------------

async def test_strong_stock_bullish() -> None:
    """Strong fundamentals, good valuation, positive sentiment → Bullish (>=75)."""
    agent = ElvisMarlamovAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
        search=MockSearchProvider(),
    )
    result = await agent.analyze("AAPL")
    assert isinstance(result, AgentResult)
    assert result.signal == "Bullish"
    assert result.score >= 75.0


# ---------------------------------------------------------------------------
# Tests: weak stock → Bearish
# ---------------------------------------------------------------------------

async def test_weak_stock_bearish() -> None:
    """Weak fundamentals, bad valuation, no sentiment → Bearish (<50)."""
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
    assert result.score < 50.0


# ---------------------------------------------------------------------------
# Tests: without search → sentiment=0 + warning
# ---------------------------------------------------------------------------

async def test_no_search_provider_sentiment_zero() -> None:
    """Without SearchProvider, sentiment=0 and a warning is emitted."""
    agent = ElvisMarlamovAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
        search=None,
    )
    result = await agent.analyze("AAPL")
    assert result.breakdown["sentiment"] == 0.0
    assert any("sentiment" in w.lower() or "search" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# Tests: missing metrics → confidence reduced + warning
# ---------------------------------------------------------------------------

async def test_missing_metrics_reduces_confidence() -> None:
    """When key metrics are None, confidence is reduced and warnings are emitted."""
    sparse_metrics = KeyMetrics(
        ticker="AAPL",
        pe_ratio=None,
        pb_ratio=None,
        market_cap=None,
        dividend_yield=None,
        roe=None,
        roa=None,
        debt_to_equity=None,
    )
    agent = ElvisMarlamovAgent(
        data_provider=MockDataProvider(metrics=sparse_metrics),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("AAPL")
    assert result.confidence < 1.0
    assert len(result.warnings) > 0


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
