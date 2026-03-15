"""Tests for CharlieMungerAgent."""

from __future__ import annotations

from fin_toolkit.agents.munger import CharlieMungerAgent
from fin_toolkit.agents.protocol import AnalysisAgent
from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData, PricePoint
from fin_toolkit.models.results import AgentResult


def _make_prices(ticker: str = "KO", count: int = 60, base: float = 60.0) -> PriceData:
    return PriceData(
        ticker=ticker,
        period="1y",
        prices=[
            PricePoint(
                date=f"2024-01-{(i % 28) + 1:02d}",
                open=base + i, high=base + i + 5,
                low=base + i - 2, close=base + i + 2, volume=500_000,
            )
            for i in range(count)
        ],
    )


def _make_quality_financials(ticker: str = "KO") -> FinancialStatements:
    """A Munger-style wonderful business: very high margins and ROE."""
    return FinancialStatements(
        ticker=ticker,
        income_statement={
            "revenue": 50_000_000_000,
            "net_income": 15_000_000_000,
            "gross_profit": 32_000_000_000,
            "operating_income": 18_000_000_000,
            "interest_expense": 500_000_000,
            "ebitda": 20_000_000_000,
        },
        balance_sheet={
            "total_assets": 100_000_000_000,
            "total_equity": 70_000_000_000,
            "total_debt": 10_000_000_000,
            "current_assets": 40_000_000_000,
            "current_liabilities": 15_000_000_000,
            "invested_capital": 80_000_000_000,
            "enterprise_value": 200_000_000_000,
        },
        cash_flow={
            "operating_cash_flow": 18_000_000_000,
            "capital_expenditures": 2_000_000_000,
        },
    )


def _make_quality_metrics(ticker: str = "KO") -> KeyMetrics:
    return KeyMetrics(
        ticker=ticker,
        pe_ratio=18.0, pb_ratio=3.0, market_cap=200_000_000_000,
        dividend_yield=0.03, roe=0.25, roa=0.15, debt_to_equity=0.14,
    )


def _make_poor_metrics(ticker: str = "JUNK") -> KeyMetrics:
    return KeyMetrics(
        ticker=ticker,
        pe_ratio=200.0, pb_ratio=50.0, market_cap=500_000_000_000,
        dividend_yield=0.0, roe=0.02, roa=0.01, debt_to_equity=5.0,
    )


def _make_poor_financials(ticker: str = "JUNK") -> FinancialStatements:
    return FinancialStatements(
        ticker=ticker,
        income_statement={
            "revenue": 5_000_000, "net_income": -2_000_000,
            "gross_profit": 500_000, "operating_income": -1_500_000,
            "interest_expense": 500_000, "ebitda": -1_000_000,
        },
        balance_sheet={
            "total_assets": 10_000_000, "total_equity": 2_000_000,
            "total_debt": 12_000_000, "current_assets": 2_000_000,
            "current_liabilities": 8_000_000, "invested_capital": 14_000_000,
            "enterprise_value": 20_000_000,
        },
        cash_flow={"operating_cash_flow": -1_000_000, "capital_expenditures": 500_000},
    )


class MockDataProvider:
    def __init__(
        self,
        prices: PriceData | None = None,
        financials: FinancialStatements | None = None,
        metrics: KeyMetrics | None = None,
    ) -> None:
        self._prices = prices or _make_prices()
        self._financials = financials or _make_quality_financials()
        self._metrics = metrics or _make_quality_metrics()

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        return self._prices

    async def get_financials(self, ticker: str) -> FinancialStatements:
        return self._financials

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        return self._metrics


async def test_munger_returns_agent_result() -> None:
    agent = CharlieMungerAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("KO")
    assert isinstance(result, AgentResult)
    assert result.signal in ("Bullish", "Neutral", "Bearish")
    assert 0.0 <= result.score <= 100.0
    assert 0.0 <= result.confidence <= 1.0


async def test_munger_quality_business_bullish() -> None:
    agent = CharlieMungerAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("KO")
    assert result.signal == "Bullish"
    assert result.score >= 75.0


async def test_munger_poor_business_bearish() -> None:
    agent = CharlieMungerAgent(
        data_provider=MockDataProvider(
            prices=_make_prices("JUNK", base=5.0),
            financials=_make_poor_financials(),
            metrics=_make_poor_metrics(),
        ),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("JUNK")
    assert result.signal == "Bearish"
    assert result.score < 50.0


async def test_munger_breakdown_keys() -> None:
    agent = CharlieMungerAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("KO")
    assert "business_quality" in result.breakdown
    assert "fair_price" in result.breakdown
    assert "financial_fortress" in result.breakdown


async def test_munger_missing_data_graceful() -> None:
    sparse = KeyMetrics(
        ticker="MISS", pe_ratio=None, pb_ratio=None, market_cap=None,
        dividend_yield=None, roe=None, roa=None, debt_to_equity=None,
    )
    agent = CharlieMungerAgent(
        data_provider=MockDataProvider(metrics=sparse),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("MISS")
    assert result.confidence < 1.0
    assert len(result.warnings) > 0


def test_munger_satisfies_protocol() -> None:
    agent = CharlieMungerAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    assert isinstance(agent, AnalysisAgent)
