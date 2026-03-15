"""Tests for PeterLynchAgent."""

from __future__ import annotations

from fin_toolkit.agents.lynch import PeterLynchAgent
from fin_toolkit.agents.protocol import AnalysisAgent
from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData, PricePoint
from fin_toolkit.models.results import AgentResult


def _make_prices(ticker: str = "WMT", count: int = 60, base: float = 160.0) -> PriceData:
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


def _make_garp_financials(ticker: str = "WMT") -> FinancialStatements:
    """A Lynch-style GARP pick: solid growth, reasonable price."""
    return FinancialStatements(
        ticker=ticker,
        income_statement={
            "revenue": 600_000_000_000,
            "net_income": 60_000_000_000,
            "gross_profit": 180_000_000_000,
            "operating_income": 80_000_000_000,
            "interest_expense": 3_000_000_000,
            "ebitda": 90_000_000_000,
        },
        balance_sheet={
            "total_assets": 400_000_000_000,
            "total_equity": 250_000_000_000,
            "total_debt": 40_000_000_000,
            "current_assets": 120_000_000_000,
            "current_liabilities": 50_000_000_000,
            "invested_capital": 290_000_000_000,
            "enterprise_value": 500_000_000_000,
        },
        cash_flow={
            "operating_cash_flow": 70_000_000_000,
            "capital_expenditures": 15_000_000_000,
        },
    )


def _make_garp_metrics(ticker: str = "WMT") -> KeyMetrics:
    return KeyMetrics(
        ticker=ticker,
        pe_ratio=14.0, pb_ratio=2.5, market_cap=500_000_000_000,
        dividend_yield=0.015, roe=0.24, roa=0.15, debt_to_equity=0.16,
    )


def _make_overpriced_metrics(ticker: str = "HYPE") -> KeyMetrics:
    return KeyMetrics(
        ticker=ticker,
        pe_ratio=300.0, pb_ratio=60.0, market_cap=1_000_000_000_000,
        dividend_yield=0.0, roe=0.01, roa=0.005, debt_to_equity=8.0,
    )


def _make_overpriced_financials(ticker: str = "HYPE") -> FinancialStatements:
    return FinancialStatements(
        ticker=ticker,
        income_statement={
            "revenue": 2_000_000, "net_income": -5_000_000,
            "gross_profit": 400_000, "operating_income": -4_000_000,
            "interest_expense": 1_000_000, "ebitda": -3_000_000,
        },
        balance_sheet={
            "total_assets": 8_000_000, "total_equity": 1_000_000,
            "total_debt": 10_000_000, "current_assets": 1_500_000,
            "current_liabilities": 6_000_000, "invested_capital": 11_000_000,
            "enterprise_value": 15_000_000,
        },
        cash_flow={"operating_cash_flow": -3_000_000, "capital_expenditures": 500_000},
    )


class MockDataProvider:
    def __init__(
        self,
        prices: PriceData | None = None,
        financials: FinancialStatements | None = None,
        metrics: KeyMetrics | None = None,
    ) -> None:
        self._prices = prices or _make_prices()
        self._financials = financials or _make_garp_financials()
        self._metrics = metrics or _make_garp_metrics()

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        return self._prices

    async def get_financials(self, ticker: str) -> FinancialStatements:
        return self._financials

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        return self._metrics


async def test_lynch_returns_agent_result() -> None:
    agent = PeterLynchAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("WMT")
    assert isinstance(result, AgentResult)
    assert result.signal in ("Bullish", "Neutral", "Bearish")
    assert 0.0 <= result.score <= 100.0
    assert 0.0 <= result.confidence <= 1.0


async def test_lynch_garp_stock_bullish() -> None:
    agent = PeterLynchAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("WMT")
    assert result.signal == "Bullish"
    assert result.score >= 75.0


async def test_lynch_overpriced_bearish() -> None:
    agent = PeterLynchAgent(
        data_provider=MockDataProvider(
            prices=_make_prices("HYPE", base=5.0),
            financials=_make_overpriced_financials(),
            metrics=_make_overpriced_metrics(),
        ),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("HYPE")
    assert result.signal == "Bearish"
    assert result.score < 50.0


async def test_lynch_breakdown_keys() -> None:
    agent = PeterLynchAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("WMT")
    assert "peg_value" in result.breakdown
    assert "earnings_quality" in result.breakdown
    assert "common_sense" in result.breakdown


async def test_lynch_missing_data_graceful() -> None:
    sparse = KeyMetrics(
        ticker="MISS", pe_ratio=None, pb_ratio=None, market_cap=None,
        dividend_yield=None, roe=None, roa=None, debt_to_equity=None,
    )
    agent = PeterLynchAgent(
        data_provider=MockDataProvider(metrics=sparse),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    result = await agent.analyze("MISS")
    assert result.confidence < 1.0
    assert len(result.warnings) > 0


def test_lynch_satisfies_protocol() -> None:
    agent = PeterLynchAgent(
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    assert isinstance(agent, AnalysisAgent)
