"""Tests for WarrenBuffettAgent."""

from __future__ import annotations

from fin_toolkit.agents.buffett import WarrenBuffettAgent
from fin_toolkit.agents.protocol import AnalysisAgent
from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData, PricePoint
from fin_toolkit.models.results import AgentResult

# ---------------------------------------------------------------------------
# Mock helpers (reuse pattern from test_elvis)
# ---------------------------------------------------------------------------

def _make_prices(ticker: str = "BRK-B", count: int = 60, base: float = 400.0) -> PriceData:
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
                volume=500_000,
            )
            for i in range(count)
        ],
    )


def _make_value_financials(ticker: str = "BRK-B") -> FinancialStatements:
    """A Buffett-style value company: high margins, low debt, strong cash flow."""
    return FinancialStatements(
        ticker=ticker,
        income_statement={
            "revenue": 300_000_000_000,
            "net_income": 90_000_000_000,
            "gross_profit": 150_000_000_000,
            "operating_income": 100_000_000_000,
            "interest_expense": 2_000_000_000,
            "ebitda": 110_000_000_000,
        },
        balance_sheet={
            "total_assets": 500_000_000_000,
            "total_equity": 300_000_000_000,
            "total_debt": 50_000_000_000,
            "current_assets": 200_000_000_000,
            "current_liabilities": 80_000_000_000,
            "invested_capital": 350_000_000_000,
            "enterprise_value": 800_000_000_000,
        },
        cash_flow={
            "operating_cash_flow": 95_000_000_000,
            "capital_expenditures": 10_000_000_000,
        },
    )


def _make_value_metrics(ticker: str = "BRK-B") -> KeyMetrics:
    return KeyMetrics(
        ticker=ticker,
        pe_ratio=12.0,
        pb_ratio=1.5,
        market_cap=800_000_000_000,
        dividend_yield=0.015,
        roe=0.30,
        roa=0.18,
        debt_to_equity=0.17,
    )


def _make_overvalued_metrics(ticker: str = "HYPE") -> KeyMetrics:
    return KeyMetrics(
        ticker=ticker,
        pe_ratio=200.0,
        pb_ratio=50.0,
        market_cap=500_000_000_000,
        dividend_yield=0.0,
        roe=0.02,
        roa=0.01,
        debt_to_equity=5.0,
    )


def _make_weak_financials(ticker: str = "HYPE") -> FinancialStatements:
    return FinancialStatements(
        ticker=ticker,
        income_statement={
            "revenue": 5_000_000,
            "net_income": -2_000_000,
            "gross_profit": 1_000_000,
            "operating_income": -1_500_000,
            "interest_expense": 500_000,
            "ebitda": -1_000_000,
        },
        balance_sheet={
            "total_assets": 10_000_000,
            "total_equity": 2_000_000,
            "total_debt": 12_000_000,
            "current_assets": 2_000_000,
            "current_liabilities": 8_000_000,
            "invested_capital": 14_000_000,
            "enterprise_value": 20_000_000,
        },
        cash_flow={
            "operating_cash_flow": -1_000_000,
            "capital_expenditures": 500_000,
        },
    )


class MockDataProvider:
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_buffett_returns_agent_result() -> None:
    """WarrenBuffettAgent.analyze returns a proper AgentResult."""
    agent = WarrenBuffettAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("BRK-B")
    assert isinstance(result, AgentResult)
    assert result.signal in ("Bullish", "Neutral", "Bearish")
    assert 0.0 <= result.score <= 100.0
    assert 0.0 <= result.confidence <= 1.0


async def test_buffett_value_stock_bullish() -> None:
    """A classic value stock should score Bullish."""
    agent = WarrenBuffettAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("BRK-B")
    assert result.signal == "Bullish"
    assert result.score >= 75.0


async def test_buffett_overvalued_bearish() -> None:
    """An overvalued company with poor fundamentals → Bearish."""
    agent = WarrenBuffettAgent(
        data_provider=MockDataProvider(
            prices=_make_prices("HYPE", base=10.0),
            financials=_make_weak_financials(),
            metrics=_make_overvalued_metrics(),
        ),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("HYPE")
    assert result.signal == "Bearish"
    assert result.score < 50.0


async def test_buffett_breakdown_keys() -> None:
    """Result breakdown has margin_of_safety, durable_advantage, management_quality."""
    agent = WarrenBuffettAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("BRK-B")
    assert "margin_of_safety" in result.breakdown
    assert "durable_advantage" in result.breakdown
    assert "management_quality" in result.breakdown


async def test_buffett_missing_data_graceful() -> None:
    """Missing metrics → confidence reduced + warnings, no crash."""
    sparse = KeyMetrics(
        ticker="MISS",
        pe_ratio=None,
        pb_ratio=None,
        market_cap=None,
        dividend_yield=None,
        roe=None,
        roa=None,
        debt_to_equity=None,
    )
    agent = WarrenBuffettAgent(
        data_provider=MockDataProvider(metrics=sparse),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("MISS")
    assert result.confidence < 1.0
    assert len(result.warnings) > 0


def test_buffett_satisfies_protocol() -> None:
    """WarrenBuffettAgent satisfies the AnalysisAgent protocol."""
    agent = WarrenBuffettAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    assert isinstance(agent, AnalysisAgent)
