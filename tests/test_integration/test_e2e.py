"""End-to-end integration tests with mock providers.

These tests verify the full pipeline: data provider → analysis → agents → MCP tools.
All external dependencies are mocked.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from fin_toolkit.agents.elvis import ElvisMarlamovAgent
from fin_toolkit.agents.registry import AgentRegistry
from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.risk import (
    calculate_var,
    calculate_volatility,
    correlation_matrix,
)
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.config.models import ToolkitConfig
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData, PricePoint
from fin_toolkit.models.results import (
    AgentResult,
    CorrelationResult,
    FundamentalResult,
    RiskResult,
    SearchResult,
    TechnicalResult,
)
from fin_toolkit.providers.router import ProviderRouter
from fin_toolkit.providers.search_router import SearchRouter

# ---------------------------------------------------------------------------
# Mock data factories
# ---------------------------------------------------------------------------


def _make_price_data(ticker: str = "AAPL", n: int = 260) -> PriceData:
    """Create realistic price data with enough points for all indicators."""
    base = 150.0
    prices: list[PricePoint] = []
    for i in range(n):
        # Simulate a gentle uptrend with some noise
        close = base + i * 0.1 + (i % 7 - 3) * 0.5
        prices.append(
            PricePoint(
                date=f"2023-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",
                open=close - 0.5,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                volume=1_000_000 + i * 1000,
            )
        )
    return PriceData(ticker=ticker, period="1y", prices=prices)


def _make_financials(ticker: str = "AAPL") -> FinancialStatements:
    """Create realistic financial statements."""
    return FinancialStatements(
        ticker=ticker,
        income_statement={
            "revenue": 383_285_000_000,
            "net_income": 96_995_000_000,
            "gross_profit": 169_148_000_000,
            "operating_income": 114_301_000_000,
            "interest_expense": 3_933_000_000,
            "ebitda": 125_820_000_000,
        },
        balance_sheet={
            "current_assets": 143_566_000_000,
            "current_liabilities": 145_308_000_000,
            "invested_capital": 200_000_000_000,
            "enterprise_value": 3_000_000_000_000,
        },
        cash_flow={
            "operating_cash_flow": 110_543_000_000,
            "capital_expenditures": 10_959_000_000,
        },
    )


def _make_metrics(ticker: str = "AAPL") -> KeyMetrics:
    """Create realistic key metrics."""
    return KeyMetrics(
        ticker=ticker,
        pe_ratio=29.5,
        pb_ratio=46.7,
        market_cap=2_900_000_000_000,
        dividend_yield=0.005,
        roe=0.20,
        roa=0.10,
        debt_to_equity=1.5,
    )


class MockDataProvider:
    """Mock DataProvider that returns realistic data for any ticker."""

    def __init__(self) -> None:
        self._prices: dict[str, PriceData] = {}
        self._financials: dict[str, FinancialStatements] = {}
        self._metrics: dict[str, KeyMetrics] = {}

    def add_ticker(
        self,
        ticker: str,
        prices: PriceData | None = None,
        financials: FinancialStatements | None = None,
        metrics: KeyMetrics | None = None,
    ) -> None:
        self._prices[ticker] = prices or _make_price_data(ticker)
        self._financials[ticker] = financials or _make_financials(ticker)
        self._metrics[ticker] = metrics or _make_metrics(ticker)

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        return self._prices[ticker]

    async def get_financials(self, ticker: str) -> FinancialStatements:
        return self._financials[ticker]

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        return self._metrics[ticker]


class MockSearchProvider:
    """Mock SearchProvider returning canned search results."""

    def __init__(self, results: list[SearchResult] | None = None) -> None:
        self._results = results or [
            SearchResult(
                title="AAPL beats earnings expectations",
                url="https://example.com/aapl-earnings",
                snippet="Apple reported strong growth and buy recommendation",
                published_date="2024-01-15",
            ),
            SearchResult(
                title="AAPL stock upgrade from analysts",
                url="https://example.com/aapl-upgrade",
                snippet="Multiple analysts upgrade AAPL to strong buy",
                published_date="2024-01-14",
            ),
        ]

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return self._results[:max_results]


# ---------------------------------------------------------------------------
# 1. ProviderRouter with mock provider
# ---------------------------------------------------------------------------


class TestProviderRouterIntegration:
    """Test ProviderRouter with a mock data provider."""

    async def test_get_prices_through_router(self) -> None:
        mock_provider = MockDataProvider()
        mock_provider.add_ticker("AAPL")
        config = ToolkitConfig()
        router = ProviderRouter(config=config, providers={"yahoo": mock_provider})

        result = await router.get_prices("AAPL", "2023-01-01", "2024-01-01")

        assert isinstance(result, PriceData)
        assert result.ticker == "AAPL"
        assert len(result.prices) == 260

    async def test_get_financials_through_router(self) -> None:
        mock_provider = MockDataProvider()
        mock_provider.add_ticker("MSFT")
        config = ToolkitConfig()
        router = ProviderRouter(config=config, providers={"yahoo": mock_provider})

        result = await router.get_financials("MSFT")

        assert isinstance(result, FinancialStatements)
        assert result.ticker == "MSFT"
        assert result.income_statement is not None

    async def test_get_metrics_through_router(self) -> None:
        mock_provider = MockDataProvider()
        mock_provider.add_ticker("GOOG")
        config = ToolkitConfig()
        router = ProviderRouter(config=config, providers={"yahoo": mock_provider})

        result = await router.get_metrics("GOOG")

        assert isinstance(result, KeyMetrics)
        assert result.ticker == "GOOG"
        assert result.pe_ratio == 29.5


# ---------------------------------------------------------------------------
# 2. TechnicalAnalyzer pipeline
# ---------------------------------------------------------------------------


class TestTechnicalAnalyzerPipeline:
    """Test full technical analysis pipeline with mock data."""

    async def test_analyze_produces_valid_result(self) -> None:
        price_data = _make_price_data("AAPL", n=260)
        analyzer = TechnicalAnalyzer()

        result = analyzer.analyze(price_data)

        assert isinstance(result, TechnicalResult)
        # With 260 data points, all indicators should be computed
        assert result.rsi is not None
        assert result.ema_20 is not None
        assert result.ema_50 is not None
        assert result.ema_200 is not None
        assert result.bb_upper is not None
        assert result.bb_middle is not None
        assert result.bb_lower is not None
        assert result.macd_line is not None
        assert result.macd_signal is not None
        assert result.macd_histogram is not None
        # Signals should have been derived
        assert len(result.signals) > 0
        assert result.overall_bias in ("Bullish", "Bearish", "Neutral")
        # No warnings with enough data
        assert result.warnings == []

    async def test_analyze_with_router_data(self) -> None:
        """Full pipeline: router → prices → TechnicalAnalyzer."""
        mock_provider = MockDataProvider()
        mock_provider.add_ticker("AAPL")
        config = ToolkitConfig()
        router = ProviderRouter(config=config, providers={"yahoo": mock_provider})

        price_data = await router.get_prices("AAPL", "2023-01-01", "2024-01-01")
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(price_data)

        assert isinstance(result, TechnicalResult)
        assert result.rsi is not None
        assert result.overall_bias in ("Bullish", "Bearish", "Neutral")


# ---------------------------------------------------------------------------
# 3. FundamentalAnalyzer pipeline
# ---------------------------------------------------------------------------


class TestFundamentalAnalyzerPipeline:
    """Test full fundamental analysis pipeline with mock data."""

    async def test_analyze_produces_valid_result(self) -> None:
        financials = _make_financials("AAPL")
        metrics = _make_metrics("AAPL")
        analyzer = FundamentalAnalyzer()

        result = analyzer.analyze(financials, metrics)

        assert isinstance(result, FundamentalResult)
        # Profitability should have values
        assert result.profitability["roe"] == 0.20
        assert result.profitability["roa"] == 0.10
        assert result.profitability["net_margin"] is not None
        assert result.profitability["gross_margin"] is not None
        assert result.profitability["roic"] is not None
        # Valuation
        assert result.valuation["pe_ratio"] == 29.5
        assert result.valuation["pb_ratio"] == 46.7
        assert result.valuation["ev_ebitda"] is not None
        assert result.valuation["fcf_yield"] is not None
        # Stability
        assert result.stability["debt_to_equity"] == 1.5
        assert result.stability["current_ratio"] is not None

    async def test_analyze_with_router_data(self) -> None:
        """Full pipeline: router → financials + metrics → FundamentalAnalyzer."""
        mock_provider = MockDataProvider()
        mock_provider.add_ticker("AAPL")
        config = ToolkitConfig()
        router = ProviderRouter(config=config, providers={"yahoo": mock_provider})

        financials = await router.get_financials("AAPL")
        metrics = await router.get_metrics("AAPL")
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(financials, metrics)

        assert isinstance(result, FundamentalResult)
        assert result.profitability["roe"] is not None


# ---------------------------------------------------------------------------
# 4. Risk analysis pipeline
# ---------------------------------------------------------------------------


class TestRiskAnalysisPipeline:
    """Test risk analysis functions with mock data."""

    async def test_calculate_volatility(self) -> None:
        price_data = _make_price_data("AAPL", n=260)

        vol_30 = calculate_volatility(price_data, window=30)
        vol_90 = calculate_volatility(price_data, window=90)
        vol_252 = calculate_volatility(price_data, window=252)

        assert isinstance(vol_30, float)
        assert isinstance(vol_90, float)
        assert isinstance(vol_252, float)
        assert vol_30 > 0
        assert vol_90 > 0
        assert vol_252 > 0

    async def test_calculate_var(self) -> None:
        price_data = _make_price_data("AAPL", n=260)

        var_95 = calculate_var(price_data, confidence=0.95)
        var_99 = calculate_var(price_data, confidence=0.99)

        assert isinstance(var_95, float)
        assert isinstance(var_99, float)
        # VaR at 99% should be more negative (larger loss) than 95%
        assert var_99 <= var_95

    async def test_risk_result_model(self) -> None:
        price_data = _make_price_data("AAPL", n=260)

        result = RiskResult(
            volatility_30d=calculate_volatility(price_data, 30),
            volatility_90d=calculate_volatility(price_data, 90),
            volatility_252d=calculate_volatility(price_data, 252),
            var_95=calculate_var(price_data, 0.95),
            var_99=calculate_var(price_data, 0.99),
            warnings=[],
        )

        assert isinstance(result, RiskResult)
        assert result.volatility_30d is not None
        assert result.var_95 is not None

    async def test_correlation_matrix(self) -> None:
        prices = {
            "AAPL": _make_price_data("AAPL", n=60),
            "MSFT": _make_price_data("MSFT", n=60),
        }

        result = correlation_matrix(prices)

        assert isinstance(result, CorrelationResult)
        assert set(result.tickers) == {"AAPL", "MSFT"}
        # Self-correlation should be 1.0
        assert result.matrix["AAPL"]["AAPL"] == 1.0
        assert result.matrix["MSFT"]["MSFT"] == 1.0
        # Cross-correlations should be between -1 and 1 (with float tolerance)
        assert result.matrix["AAPL"]["MSFT"] == pytest.approx(
            result.matrix["AAPL"]["MSFT"], abs=1e-9
        )
        assert result.matrix["AAPL"]["MSFT"] >= -1.0 - 1e-9
        assert result.matrix["AAPL"]["MSFT"] <= 1.0 + 1e-9

    async def test_risk_with_router_data(self) -> None:
        """Full pipeline: router → prices → risk functions."""
        mock_provider = MockDataProvider()
        mock_provider.add_ticker("AAPL")
        config = ToolkitConfig()
        router = ProviderRouter(config=config, providers={"yahoo": mock_provider})

        price_data = await router.get_prices("AAPL", "2023-01-01", "2024-01-01")
        vol = calculate_volatility(price_data, 30)
        var = calculate_var(price_data, 0.95)

        assert vol > 0
        assert isinstance(var, float)


# ---------------------------------------------------------------------------
# 5. ElvisMarlamovAgent pipeline
# ---------------------------------------------------------------------------


class TestElvisMarlamovAgentPipeline:
    """Test Elvis Marlamov agent with mock DI."""

    async def test_analyze_without_search(self) -> None:
        mock_provider = MockDataProvider()
        mock_provider.add_ticker("AAPL")

        technical = TechnicalAnalyzer()
        fundamental = FundamentalAnalyzer()
        agent = ElvisMarlamovAgent(
            data_provider=mock_provider,
            technical=technical,
            fundamental=fundamental,
            search=None,
        )

        result = await agent.analyze("AAPL")

        assert isinstance(result, AgentResult)
        assert result.signal in ("Bullish", "Neutral", "Bearish")
        assert 0.0 <= result.score <= 100.0
        assert 0.0 <= result.confidence <= 1.0
        assert "Elvis Marlamov" in result.rationale
        assert "quality" in result.breakdown
        assert "stability" in result.breakdown
        assert "valuation" in result.breakdown
        assert "sentiment" in result.breakdown
        # Without search, sentiment should be 0
        assert result.breakdown["sentiment"] == 0.0
        assert any("search" in w.lower() or "sentiment" in w.lower() for w in result.warnings)

    async def test_analyze_with_search(self) -> None:
        mock_provider = MockDataProvider()
        mock_provider.add_ticker("AAPL")
        mock_search = MockSearchProvider()

        technical = TechnicalAnalyzer()
        fundamental = FundamentalAnalyzer()
        agent = ElvisMarlamovAgent(
            data_provider=mock_provider,
            technical=technical,
            fundamental=fundamental,
            search=mock_search,
        )

        result = await agent.analyze("AAPL")

        assert isinstance(result, AgentResult)
        assert result.signal in ("Bullish", "Neutral", "Bearish")
        # With positive search results, sentiment should be > 0
        assert result.breakdown["sentiment"] > 0.0


# ---------------------------------------------------------------------------
# 6. WarrenBuffettAgent pipeline
# ---------------------------------------------------------------------------


class TestWarrenBuffettAgentPipeline:
    """Test Warren Buffett agent with mock DI."""

    async def test_analyze(self) -> None:
        from fin_toolkit.agents.buffett import WarrenBuffettAgent

        mock_provider = MockDataProvider()
        mock_provider.add_ticker("BRK-B")

        technical = TechnicalAnalyzer()
        fundamental = FundamentalAnalyzer()
        agent = WarrenBuffettAgent(
            data_provider=mock_provider,
            technical=technical,
            fundamental=fundamental,
        )

        result = await agent.analyze("BRK-B")

        assert isinstance(result, AgentResult)
        assert result.signal in ("Bullish", "Neutral", "Bearish")
        assert 0.0 <= result.score <= 100.0
        assert 0.0 <= result.confidence <= 1.0
        assert "Buffett" in result.rationale
        assert "margin_of_safety" in result.breakdown
        assert "durable_advantage" in result.breakdown
        assert "management_quality" in result.breakdown


# ---------------------------------------------------------------------------
# 7. AgentRegistry pipeline
# ---------------------------------------------------------------------------


class TestAgentRegistryPipeline:
    """Test AgentRegistry with mock providers."""

    async def test_registry_loads_agents(self) -> None:
        mock_provider = MockDataProvider()
        mock_provider.add_ticker("AAPL")
        config = ToolkitConfig()
        technical = TechnicalAnalyzer()
        fundamental = FundamentalAnalyzer()

        registry = AgentRegistry(
            config=config,
            data_provider=mock_provider,
            technical=technical,
            fundamental=fundamental,
            search=None,
        )

        agents = registry.get_active_agents()
        assert "elvis_marlamov" in agents
        assert "warren_buffett" in agents

    async def test_registry_elvis_produces_result(self) -> None:
        mock_provider = MockDataProvider()
        mock_provider.add_ticker("AAPL")
        config = ToolkitConfig()
        technical = TechnicalAnalyzer()
        fundamental = FundamentalAnalyzer()

        registry = AgentRegistry(
            config=config,
            data_provider=mock_provider,
            technical=technical,
            fundamental=fundamental,
        )

        agent = registry.get_agent("elvis_marlamov")
        result = await agent.analyze("AAPL")

        assert isinstance(result, AgentResult)
        assert result.signal in ("Bullish", "Neutral", "Bearish")


# ---------------------------------------------------------------------------
# 8. MCP tool functions with mocked server state
# ---------------------------------------------------------------------------


class TestMCPToolsIntegration:
    """Test MCP tool functions end-to-end with mocked server state."""

    async def test_get_stock_data_tool(self) -> None:
        """get_stock_data tool returns valid JSON through full pipeline."""
        from fin_toolkit.mcp_server.server import get_stock_data

        mock_provider = MockDataProvider()
        mock_provider.add_ticker("AAPL")
        config = ToolkitConfig()
        router = ProviderRouter(config=config, providers={"yahoo": mock_provider})

        with patch("fin_toolkit.mcp_server.server._provider_router", router):
            result = await get_stock_data("AAPL", "1y", None)

        parsed = json.loads(result)
        assert parsed["ticker"] == "AAPL"
        assert len(parsed["prices"]) == 260

    async def test_run_technical_analysis_tool(self) -> None:
        """run_technical_analysis tool returns valid TechnicalResult JSON."""
        from fin_toolkit.mcp_server.server import run_technical_analysis

        mock_provider = MockDataProvider()
        mock_provider.add_ticker("AAPL")
        config = ToolkitConfig()
        router = ProviderRouter(config=config, providers={"yahoo": mock_provider})
        analyzer = TechnicalAnalyzer()

        with (
            patch("fin_toolkit.mcp_server.server._provider_router", router),
            patch("fin_toolkit.mcp_server.server._technical_analyzer", analyzer),
        ):
            result = await run_technical_analysis("AAPL")

        parsed = json.loads(result)
        assert "rsi" in parsed
        assert "overall_bias" in parsed
        assert parsed["rsi"] is not None
        assert parsed["overall_bias"] in ("Bullish", "Bearish", "Neutral")

    async def test_run_fundamental_analysis_tool(self) -> None:
        """run_fundamental_analysis tool returns valid FundamentalResult JSON."""
        from fin_toolkit.mcp_server.server import run_fundamental_analysis

        mock_provider = MockDataProvider()
        mock_provider.add_ticker("AAPL")
        config = ToolkitConfig()
        router = ProviderRouter(config=config, providers={"yahoo": mock_provider})
        analyzer = FundamentalAnalyzer()

        with (
            patch("fin_toolkit.mcp_server.server._provider_router", router),
            patch("fin_toolkit.mcp_server.server._fundamental_analyzer", analyzer),
            patch(
                "fin_toolkit.mcp_server.server._detect_sector",
                return_value="Technology",
            ),
        ):
            result = await run_fundamental_analysis("AAPL")

        parsed = json.loads(result)
        assert "profitability" in parsed
        assert "valuation" in parsed
        assert "stability" in parsed

    async def test_run_risk_analysis_tool(self) -> None:
        """run_risk_analysis tool returns valid risk + correlation JSON."""
        from fin_toolkit.mcp_server.server import run_risk_analysis

        mock_provider = MockDataProvider()
        mock_provider.add_ticker("AAPL")
        mock_provider.add_ticker("MSFT")
        config = ToolkitConfig()
        router = ProviderRouter(config=config, providers={"yahoo": mock_provider})

        with patch("fin_toolkit.mcp_server.server._provider_router", router):
            result = await run_risk_analysis(["AAPL", "MSFT"], "1y")

        parsed = json.loads(result)
        assert "risk" in parsed
        assert "correlation" in parsed
        assert "AAPL" in parsed["risk"]
        assert "MSFT" in parsed["risk"]
        # Verify risk fields
        aapl_risk = parsed["risk"]["AAPL"]
        assert "volatility_30d" in aapl_risk
        assert "var_95" in aapl_risk

    async def test_search_news_tool(self) -> None:
        """search_news tool returns results through SearchRouter."""
        from fin_toolkit.mcp_server.server import search_news

        mock_search = MockSearchProvider()
        search_router = SearchRouter(providers=[mock_search])

        with patch("fin_toolkit.mcp_server.server._search_router", search_router):
            result = await search_news("AAPL earnings", 5)

        parsed = json.loads(result)
        assert "results" in parsed
        assert len(parsed["results"]) == 2
        assert parsed["results"][0]["title"] == "AAPL beats earnings expectations"

    async def test_run_agent_tool(self) -> None:
        """run_agent tool returns valid AgentResult JSON through full pipeline."""
        from fin_toolkit.mcp_server.server import run_agent

        mock_provider = MockDataProvider()
        mock_provider.add_ticker("AAPL")
        config = ToolkitConfig()
        technical = TechnicalAnalyzer()
        fundamental = FundamentalAnalyzer()
        registry = AgentRegistry(
            config=config,
            data_provider=mock_provider,
            technical=technical,
            fundamental=fundamental,
        )

        with patch("fin_toolkit.mcp_server.server._agent_registry", registry):
            result = await run_agent("AAPL", "elvis_marlamov")

        parsed = json.loads(result)
        assert "signal" in parsed
        assert "score" in parsed
        assert "confidence" in parsed
        assert "rationale" in parsed
        assert "breakdown" in parsed
        assert parsed["signal"] in ("Bullish", "Neutral", "Bearish")
        assert 0 <= parsed["score"] <= 100
        assert 0.0 <= parsed["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# 9. Full pipeline: config → providers → analysis → agent → MCP
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """Test the complete wiring from config to MCP output."""

    async def test_config_to_agent_result(self) -> None:
        """Config → ProviderRouter → Analyzers → AgentRegistry → AgentResult."""
        config = ToolkitConfig()
        mock_provider = MockDataProvider()
        mock_provider.add_ticker("TSLA")

        technical = TechnicalAnalyzer()
        fundamental = FundamentalAnalyzer()
        mock_search = MockSearchProvider()
        search_router = SearchRouter(providers=[mock_search])

        registry = AgentRegistry(
            config=config,
            data_provider=mock_provider,
            technical=technical,
            fundamental=fundamental,
            search=search_router,
        )

        # Run both agents
        elvis = registry.get_agent("elvis_marlamov")
        elvis_result = await elvis.analyze("TSLA")
        assert isinstance(elvis_result, AgentResult)

        buffett = registry.get_agent("warren_buffett")
        buffett_result = await buffett.analyze("TSLA")
        assert isinstance(buffett_result, AgentResult)

        # Both should produce valid results
        for result in (elvis_result, buffett_result):
            assert result.signal in ("Bullish", "Neutral", "Bearish")
            assert 0 <= result.score <= 100
            assert 0.0 <= result.confidence <= 1.0

    async def test_init_server_wiring(self) -> None:
        """init_server wires everything and returns a FastMCP instance."""
        from fastmcp import FastMCP

        from fin_toolkit.mcp_server.server import init_server

        config = ToolkitConfig()
        mock_provider = MockDataProvider()
        mock_provider.add_ticker("AAPL")

        router = ProviderRouter(config=config, providers={"yahoo": mock_provider})
        technical = TechnicalAnalyzer()
        fundamental = FundamentalAnalyzer()

        registry = AgentRegistry(
            config=config,
            data_provider=mock_provider,
            technical=technical,
            fundamental=fundamental,
        )

        server = init_server(
            provider_router=router,
            search_router=None,
            technical_analyzer=technical,
            fundamental_analyzer=fundamental,
            agent_registry=registry,
        )

        assert isinstance(server, FastMCP)
