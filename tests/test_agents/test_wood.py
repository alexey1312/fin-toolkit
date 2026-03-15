"""Tests for CathieWoodAgent."""

from __future__ import annotations

from fin_toolkit.agents.protocol import AnalysisAgent
from fin_toolkit.agents.wood import CathieWoodAgent
from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData, PricePoint
from fin_toolkit.models.results import AgentResult


def _make_prices(ticker: str = "TSLA", count: int = 60, base: float = 250.0) -> PriceData:
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


def _make_growth_financials(ticker: str = "TSLA") -> FinancialStatements:
    """A Cathie Wood favourite: high-growth, strong margins, moderate debt."""
    return FinancialStatements(
        ticker=ticker,
        income_statement={
            "revenue": 80_000_000_000,
            "net_income": 16_000_000_000,
            "gross_profit": 48_000_000_000,
            "operating_income": 20_000_000_000,
            "interest_expense": 1_000_000_000,
            "ebitda": 25_000_000_000,
        },
        balance_sheet={
            "total_assets": 120_000_000_000,
            "total_equity": 80_000_000_000,
            "total_debt": 15_000_000_000,
            "current_assets": 50_000_000_000,
            "current_liabilities": 20_000_000_000,
            "invested_capital": 95_000_000_000,
            "enterprise_value": 800_000_000_000,
        },
        cash_flow={
            "operating_cash_flow": 22_000_000_000,
            "capital_expenditures": 8_000_000_000,
        },
    )


def _make_growth_metrics(ticker: str = "TSLA") -> KeyMetrics:
    return KeyMetrics(
        ticker=ticker,
        pe_ratio=40.0, pb_ratio=8.0, market_cap=800_000_000_000,
        dividend_yield=0.0, roe=0.25, roa=0.13, debt_to_equity=0.19,
    )


def _make_stagnant_metrics(ticker: str = "OLD") -> KeyMetrics:
    return KeyMetrics(
        ticker=ticker,
        pe_ratio=8.0, pb_ratio=0.8, market_cap=10_000_000_000,
        dividend_yield=0.06, roe=0.04, roa=0.02, debt_to_equity=3.0,
    )


def _make_stagnant_financials(ticker: str = "OLD") -> FinancialStatements:
    return FinancialStatements(
        ticker=ticker,
        income_statement={
            "revenue": 10_000_000_000, "net_income": 300_000_000,
            "gross_profit": 2_000_000_000, "operating_income": 500_000_000,
            "interest_expense": 400_000_000, "ebitda": 700_000_000,
        },
        balance_sheet={
            "total_assets": 30_000_000_000, "total_equity": 8_000_000_000,
            "total_debt": 20_000_000_000, "current_assets": 5_000_000_000,
            "current_liabilities": 7_000_000_000, "invested_capital": 28_000_000_000,
            "enterprise_value": 30_000_000_000,
        },
        cash_flow={"operating_cash_flow": 600_000_000, "capital_expenditures": 500_000_000},
    )


class MockDataProvider:
    def __init__(
        self,
        prices: PriceData | None = None,
        financials: FinancialStatements | None = None,
        metrics: KeyMetrics | None = None,
    ) -> None:
        self._prices = prices or _make_prices()
        self._financials = financials or _make_growth_financials()
        self._metrics = metrics or _make_growth_metrics()

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        return self._prices

    async def get_financials(self, ticker: str) -> FinancialStatements:
        return self._financials

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        return self._metrics


async def test_wood_returns_agent_result() -> None:
    agent = CathieWoodAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("TSLA")
    assert isinstance(result, AgentResult)
    assert result.signal in ("Bullish", "Neutral", "Bearish")
    assert 0.0 <= result.score <= 100.0
    assert 0.0 <= result.confidence <= 1.0


async def test_wood_growth_stock_bullish() -> None:
    agent = CathieWoodAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("TSLA")
    assert result.signal == "Bullish"
    assert result.score >= 75.0


async def test_wood_stagnant_stock_bearish() -> None:
    agent = CathieWoodAgent(
        data_provider=MockDataProvider(
            prices=_make_prices("OLD", base=20.0),
            financials=_make_stagnant_financials(),
            metrics=_make_stagnant_metrics(),
        ),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("OLD")
    assert result.signal == "Bearish"
    assert result.score < 50.0


async def test_wood_breakdown_keys() -> None:
    agent = CathieWoodAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("TSLA")
    assert "growth_signals" in result.breakdown
    assert "innovation_premium" in result.breakdown
    assert "market_position" in result.breakdown


async def test_wood_missing_data_graceful() -> None:
    sparse = KeyMetrics(
        ticker="MISS", pe_ratio=None, pb_ratio=None, market_cap=None,
        dividend_yield=None, roe=None, roa=None, debt_to_equity=None,
    )
    agent = CathieWoodAgent(
        data_provider=MockDataProvider(metrics=sparse),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("MISS")
    assert result.confidence < 1.0
    assert len(result.warnings) > 0


def test_wood_satisfies_protocol() -> None:
    agent = CathieWoodAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    assert isinstance(agent, AnalysisAgent)
