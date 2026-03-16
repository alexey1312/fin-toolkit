"""Tests for MCP server tools."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fin_toolkit.exceptions import (
    AgentNotFoundError,
    AllProvidersFailedError,
    TickerNotFoundError,
)
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData, PricePoint
from fin_toolkit.models.results import (
    AgentResult,
    FundamentalResult,
    SearchResult,
    TechnicalResult,
)
from fin_toolkit.watchlist import WatchlistStore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_price_data(ticker: str = "AAPL", n: int = 60) -> PriceData:
    """Create a PriceData with n price points."""
    prices = [
        PricePoint(
            date=f"2024-01-{i + 1:02d}",
            open=100.0 + i,
            high=105.0 + i,
            low=98.0 + i,
            close=102.0 + i,
            volume=1_000_000,
        )
        for i in range(n)
    ]
    return PriceData(ticker=ticker, period="1y", prices=prices)


def _make_financials(ticker: str = "AAPL") -> FinancialStatements:
    return FinancialStatements(
        ticker=ticker,
        income_statement={"revenue": 100_000, "net_income": 20_000},
        balance_sheet={"current_assets": 50_000, "current_liabilities": 25_000},
        cash_flow={"operating_cash_flow": 30_000, "capital_expenditures": 10_000},
    )


def _make_metrics(ticker: str = "AAPL") -> KeyMetrics:
    return KeyMetrics(
        ticker=ticker,
        pe_ratio=20.0,
        pb_ratio=3.0,
        market_cap=1_000_000_000,
        dividend_yield=0.01,
        roe=0.15,
        roa=0.08,
        debt_to_equity=1.0,
    )


def _make_technical_result() -> TechnicalResult:
    return TechnicalResult(
        rsi=55.0,
        ema_20=150.0,
        ema_50=148.0,
        ema_200=140.0,
        bb_upper=160.0,
        bb_middle=150.0,
        bb_lower=140.0,
        macd_line=1.5,
        macd_signal=1.0,
        macd_histogram=0.5,
        signals={"rsi": "neutral", "macd": "bullish"},
        overall_bias="Bullish",
        warnings=[],
    )


def _make_fundamental_result() -> FundamentalResult:
    return FundamentalResult(
        profitability={"roe": 0.15, "roa": 0.08},
        valuation={"pe_ratio": 20.0},
        stability={"debt_to_equity": 1.0},
        sector_comparison={},
        warnings=[],
    )


def _make_agent_result() -> AgentResult:
    return AgentResult(
        signal="Bullish",
        score=75.0,
        confidence=0.8,
        rationale="Strong technicals and fundamentals",
        breakdown={"technical": 80.0, "fundamental": 70.0},
        warnings=[],
    )


# ---------------------------------------------------------------------------
# get_stock_data
# ---------------------------------------------------------------------------


class TestGetStockData:
    async def test_valid_ticker_returns_json(self) -> None:
        """Valid ticker returns JSON PriceData."""
        from fin_toolkit.mcp_server.server import get_stock_data

        price_data = _make_price_data("AAPL")
        mock_router = AsyncMock()
        mock_router.get_prices.return_value = price_data

        with patch("fin_toolkit.mcp_server.server._provider_router", mock_router):
            result = await get_stock_data("AAPL", "1y", None, format="json")

        parsed = json.loads(result)
        assert parsed["ticker"] == "AAPL"
        assert len(parsed["prices"]) == 60

    async def test_json_format(self) -> None:
        """Explicit format='json' returns valid JSON."""
        from fin_toolkit.mcp_server.server import get_stock_data

        price_data = _make_price_data("AAPL")
        mock_router = AsyncMock()
        mock_router.get_prices.return_value = price_data

        with patch("fin_toolkit.mcp_server.server._provider_router", mock_router):
            result = await get_stock_data("AAPL", "1y", None, format="json")

        parsed = json.loads(result)
        assert parsed["ticker"] == "AAPL"

    async def test_default_toon_format(self) -> None:
        """Default format is TOON (not JSON)."""
        from fin_toolkit.mcp_server.server import get_stock_data

        price_data = _make_price_data("AAPL")
        mock_router = AsyncMock()
        mock_router.get_prices.return_value = price_data

        with patch("fin_toolkit.mcp_server.server._provider_router", mock_router):
            result = await get_stock_data("AAPL", "1y", None)

        # TOON is not valid JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(result)

    async def test_invalid_ticker_returns_error(self) -> None:
        """Invalid ticker returns structured error."""
        from fin_toolkit.mcp_server.server import get_stock_data

        mock_router = AsyncMock()
        mock_router.get_prices.side_effect = TickerNotFoundError("INVALID", "yahoo")

        with patch("fin_toolkit.mcp_server.server._provider_router", mock_router):
            result = await get_stock_data("INVALID")

        parsed = json.loads(result)
        assert parsed["is_error"] is True
        assert "INVALID" in parsed["error"]


# ---------------------------------------------------------------------------
# run_technical_analysis
# ---------------------------------------------------------------------------


class TestRunTechnicalAnalysis:
    async def test_valid_returns_json(self) -> None:
        """Valid ticker returns JSON TechnicalResult."""
        from fin_toolkit.mcp_server.server import run_technical_analysis

        price_data = _make_price_data("AAPL")
        tech_result = _make_technical_result()

        mock_router = AsyncMock()
        mock_router.get_prices.return_value = price_data
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = tech_result

        with (
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch("fin_toolkit.mcp_server.server._technical_analyzer", mock_analyzer),
        ):
            result = await run_technical_analysis("AAPL", format="json")

        parsed = json.loads(result)
        assert parsed["rsi"] == 55.0
        assert parsed["overall_bias"] == "Bullish"

    async def test_provider_error_returns_structured_error(self) -> None:
        """Provider failure returns structured error."""
        from fin_toolkit.mcp_server.server import run_technical_analysis

        mock_router = AsyncMock()
        mock_router.get_prices.side_effect = AllProvidersFailedError(
            {"yahoo": "timeout"}
        )

        with patch("fin_toolkit.mcp_server.server._provider_router", mock_router):
            result = await run_technical_analysis("AAPL")

        parsed = json.loads(result)
        assert parsed["is_error"] is True


# ---------------------------------------------------------------------------
# run_fundamental_analysis
# ---------------------------------------------------------------------------


class TestRunFundamentalAnalysis:
    async def test_valid_returns_json(self) -> None:
        """Valid ticker returns JSON FundamentalResult."""
        from fin_toolkit.mcp_server.server import run_fundamental_analysis

        fund_result = _make_fundamental_result()
        mock_router = AsyncMock()
        mock_router.get_financials.return_value = _make_financials()
        mock_router.get_metrics.return_value = _make_metrics()
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = fund_result

        with (
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch(
                "fin_toolkit.mcp_server.server._fundamental_analyzer", mock_analyzer
            ),
        ):
            result = await run_fundamental_analysis("AAPL", format="json")

        parsed = json.loads(result)
        assert "profitability" in parsed
        assert "valuation" in parsed

    async def test_with_sector_passes_sector(self) -> None:
        """Sector is passed to analyzer when provided."""
        from fin_toolkit.mcp_server.server import run_fundamental_analysis

        fund_result = _make_fundamental_result()
        mock_router = AsyncMock()
        mock_router.get_financials.return_value = _make_financials()
        mock_router.get_metrics.return_value = _make_metrics()
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = fund_result

        with (
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch(
                "fin_toolkit.mcp_server.server._fundamental_analyzer", mock_analyzer
            ),
        ):
            result = await run_fundamental_analysis(
                "AAPL", sector="Technology", format="json"
            )

        mock_analyzer.analyze.assert_called_once()
        call_kwargs = mock_analyzer.analyze.call_args
        assert call_kwargs[1].get("sector") == "Technology" or (
            len(call_kwargs[0]) >= 3 and call_kwargs[0][2] == "Technology"
        )
        parsed = json.loads(result)
        assert parsed["is_error"] is not True if "is_error" in parsed else True

    async def test_without_sector_auto_detects(self) -> None:
        """Without sector, tool attempts auto-detection."""
        from fin_toolkit.mcp_server.server import run_fundamental_analysis

        fund_result = _make_fundamental_result()
        mock_router = AsyncMock()
        mock_router.get_financials.return_value = _make_financials()
        mock_router.get_metrics.return_value = _make_metrics()
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = fund_result

        with (
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch(
                "fin_toolkit.mcp_server.server._fundamental_analyzer", mock_analyzer
            ),
            patch(
                "fin_toolkit.mcp_server.server._detect_sector", return_value="Technology"
            ),
        ):
            result = await run_fundamental_analysis("AAPL", format="json")

        parsed = json.loads(result)
        assert "profitability" in parsed

    async def test_error_returns_structured(self) -> None:
        """Provider error returns structured error."""
        from fin_toolkit.mcp_server.server import run_fundamental_analysis

        mock_router = AsyncMock()
        mock_router.get_financials.side_effect = TickerNotFoundError("BAD", "yahoo")

        with patch("fin_toolkit.mcp_server.server._provider_router", mock_router):
            result = await run_fundamental_analysis("BAD")

        parsed = json.loads(result)
        assert parsed["is_error"] is True


# ---------------------------------------------------------------------------
# run_risk_analysis
# ---------------------------------------------------------------------------


class TestRunRiskAnalysis:
    async def test_multiple_tickers_returns_json(self) -> None:
        """Multiple tickers return combined JSON with risk and correlation."""
        from fin_toolkit.mcp_server.server import run_risk_analysis

        mock_router = AsyncMock()
        mock_router.get_prices.side_effect = [
            _make_price_data("AAPL", 60),
            _make_price_data("MSFT", 60),
        ]

        with patch("fin_toolkit.mcp_server.server._provider_router", mock_router):
            result = await run_risk_analysis(["AAPL", "MSFT"], "1y", format="json")

        parsed = json.loads(result)
        assert "risk" in parsed
        assert "correlation" in parsed
        assert "AAPL" in parsed["risk"]
        assert "MSFT" in parsed["risk"]

    async def test_provider_error_returns_structured(self) -> None:
        """Provider failure returns structured error."""
        from fin_toolkit.mcp_server.server import run_risk_analysis

        mock_router = AsyncMock()
        mock_router.get_prices.side_effect = AllProvidersFailedError(
            {"yahoo": "timeout"}
        )

        with patch("fin_toolkit.mcp_server.server._provider_router", mock_router):
            result = await run_risk_analysis(["AAPL"])

        parsed = json.loads(result)
        assert parsed["is_error"] is True

    async def test_insufficient_data_returns_warnings(self) -> None:
        """Insufficient data returns results with None values and warnings."""
        from fin_toolkit.mcp_server.server import run_risk_analysis

        mock_router = AsyncMock()
        mock_router.get_prices.return_value = _make_price_data("AAPL", 5)

        with patch("fin_toolkit.mcp_server.server._provider_router", mock_router):
            result = await run_risk_analysis(["AAPL"], format="json")

        parsed = json.loads(result)
        assert "risk" in parsed
        aapl_risk = parsed["risk"]["AAPL"]
        # With only 5 data points, volatility_30d should be None
        assert aapl_risk["volatility_30d"] is None
        assert len(aapl_risk["warnings"]) > 0


# ---------------------------------------------------------------------------
# search_news
# ---------------------------------------------------------------------------


class TestSearchNews:
    async def test_with_provider_returns_results(self) -> None:
        """Search with provider returns results."""
        from fin_toolkit.mcp_server.server import search_news

        mock_search_router = AsyncMock()
        mock_search_router.search.return_value = [
            SearchResult(
                title="AAPL News",
                url="https://example.com",
                snippet="Apple earnings beat",
                published_date="2024-01-01",
            )
        ]

        with patch(
            "fin_toolkit.mcp_server.server._search_router", mock_search_router
        ):
            result = await search_news("AAPL earnings", 10, format="json")

        parsed = json.loads(result)
        assert "results" in parsed
        assert len(parsed["results"]) == 1
        assert parsed["results"][0]["title"] == "AAPL News"

    async def test_no_provider_returns_warning(self) -> None:
        """No search provider returns empty results with warning."""
        from fin_toolkit.mcp_server.server import search_news

        with patch("fin_toolkit.mcp_server.server._search_router", None):
            result = await search_news("AAPL earnings", format="json")

        parsed = json.loads(result)
        assert parsed["results"] == []
        assert "warning" in parsed

    async def test_all_providers_fail_returns_warning(self) -> None:
        """Router configured but all providers fail returns warning."""
        from fin_toolkit.mcp_server.server import search_news

        mock_search_router = AsyncMock()
        mock_search_router.search.return_value = []

        with patch(
            "fin_toolkit.mcp_server.server._search_router", mock_search_router
        ):
            result = await search_news("AAPL earnings", format="json")

        parsed = json.loads(result)
        assert parsed["results"] == []
        assert "warning" in parsed


# ---------------------------------------------------------------------------
# run_agent
# ---------------------------------------------------------------------------


class TestRunAgent:
    async def test_valid_agent_returns_json(self) -> None:
        """Valid agent returns JSON AgentResult."""
        from fin_toolkit.mcp_server.server import run_agent

        agent_result = _make_agent_result()
        mock_agent = AsyncMock()
        mock_agent.analyze.return_value = agent_result

        mock_registry = MagicMock()
        mock_registry.get_agent.return_value = mock_agent

        with patch("fin_toolkit.mcp_server.server._agent_registry", mock_registry):
            result = await run_agent("AAPL", "elvis_marlamov", format="json")

        parsed = json.loads(result)
        assert parsed["signal"] == "Bullish"
        assert parsed["score"] == 75.0

    async def test_json_format(self) -> None:
        """Explicit format='json' returns valid JSON for agent."""
        from fin_toolkit.mcp_server.server import run_agent

        agent_result = _make_agent_result()
        mock_agent = AsyncMock()
        mock_agent.analyze.return_value = agent_result

        mock_registry = MagicMock()
        mock_registry.get_agent.return_value = mock_agent

        with patch("fin_toolkit.mcp_server.server._agent_registry", mock_registry):
            result = await run_agent("AAPL", "elvis_marlamov", format="json")

        parsed = json.loads(result)
        assert parsed["signal"] == "Bullish"

    async def test_unknown_agent_returns_error(self) -> None:
        """Unknown agent returns structured error."""
        from fin_toolkit.mcp_server.server import run_agent

        mock_registry = MagicMock()
        mock_registry.get_agent.side_effect = AgentNotFoundError("unknown_agent")

        with patch("fin_toolkit.mcp_server.server._agent_registry", mock_registry):
            result = await run_agent("AAPL", "unknown_agent")

        parsed = json.loads(result)
        assert parsed["is_error"] is True
        assert "unknown_agent" in parsed["error"]

    async def test_agent_internal_error_returns_structured(self) -> None:
        """Agent internal error returns structured error."""
        from fin_toolkit.mcp_server.server import run_agent

        mock_agent = AsyncMock()
        mock_agent.analyze.side_effect = AllProvidersFailedError(
            {"yahoo": "connection error"}
        )

        mock_registry = MagicMock()
        mock_registry.get_agent.return_value = mock_agent

        with patch("fin_toolkit.mcp_server.server._agent_registry", mock_registry):
            result = await run_agent("AAPL", "elvis_marlamov")

        parsed = json.loads(result)
        assert parsed["is_error"] is True


# ---------------------------------------------------------------------------
# run_all_agents
# ---------------------------------------------------------------------------


def _mock_registry_with_agents(
    agents: dict[str, AgentResult | Exception],
) -> MagicMock:
    """Build a mock AgentRegistry with agents returning given results."""
    mock_reg = MagicMock()
    active: dict[str, AsyncMock] = {}
    for name, result in agents.items():
        mock_agent = AsyncMock()
        if isinstance(result, Exception):
            mock_agent.analyze.side_effect = result
        else:
            mock_agent.analyze.return_value = result
        active[name] = mock_agent
    mock_reg.get_active_agents.return_value = active
    return mock_reg


class TestRunAllAgents:
    async def test_all_succeed(self) -> None:
        from fin_toolkit.mcp_server.server import run_all_agents

        agents = {
            "buffett": _make_agent_result(),
            "graham": AgentResult(
                signal="Neutral", score=55.0, confidence=0.7,
                rationale="OK", breakdown={}, warnings=[],
            ),
        }
        mock_reg = _mock_registry_with_agents(agents)

        with patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg):
            result = await run_all_agents("AAPL", format="json")

        parsed = json.loads(result)
        assert "consensus_score" in parsed
        assert "consensus_signal" in parsed
        assert len(parsed["agent_results"]) == 2

    async def test_partial_failure(self) -> None:
        from fin_toolkit.mcp_server.server import run_all_agents

        agents: dict[str, AgentResult | Exception] = {
            "buffett": _make_agent_result(),
            "graham": RuntimeError("provider timeout"),
        }
        mock_reg = _mock_registry_with_agents(agents)

        with patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg):
            result = await run_all_agents("AAPL", format="json")

        parsed = json.loads(result)
        assert len(parsed["agent_results"]) == 1
        assert "graham" in parsed["agent_errors"]
        assert parsed["consensus_score"] > 0

    async def test_all_fail_returns_error(self) -> None:
        from fin_toolkit.mcp_server.server import run_all_agents

        agents: dict[str, AgentResult | Exception] = {
            "buffett": RuntimeError("fail1"),
            "graham": RuntimeError("fail2"),
        }
        mock_reg = _mock_registry_with_agents(agents)

        with patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg):
            result = await run_all_agents("AAPL", format="json")

        parsed = json.loads(result)
        assert parsed["is_error"] is True

    async def test_empty_registry(self) -> None:
        from fin_toolkit.mcp_server.server import run_all_agents

        mock_reg = _mock_registry_with_agents({})

        with patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg):
            result = await run_all_agents("AAPL", format="json")

        parsed = json.loads(result)
        assert parsed["is_error"] is True


# ---------------------------------------------------------------------------
# run_recommendation
# ---------------------------------------------------------------------------


class TestRunRecommendation:
    async def test_bullish_positive_size(self) -> None:
        from fin_toolkit.mcp_server.server import run_recommendation

        agents = {"buffett": _make_agent_result()}  # Bullish, 75, 0.8
        mock_reg = _mock_registry_with_agents(agents)
        mock_router = AsyncMock()
        mock_router.get_prices.return_value = _make_price_data("AAPL", 300)
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_technical_result()

        with (
            patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg),
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch("fin_toolkit.mcp_server.server._technical_analyzer", mock_analyzer),
        ):
            result = await run_recommendation("AAPL", format="json")

        parsed = json.loads(result)
        assert parsed["ticker"] == "AAPL"
        assert parsed["position_size_pct"] > 0
        assert "consensus" in parsed
        assert "risk" in parsed

    async def test_bearish_zero_size(self) -> None:
        from fin_toolkit.mcp_server.server import run_recommendation

        bearish = AgentResult(
            signal="Bearish", score=20.0, confidence=0.9,
            rationale="weak", breakdown={}, warnings=[],
        )
        agents = {"buffett": bearish}
        mock_reg = _mock_registry_with_agents(agents)
        mock_router = AsyncMock()
        mock_router.get_prices.return_value = _make_price_data("AAPL", 300)
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_technical_result()

        with (
            patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg),
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch("fin_toolkit.mcp_server.server._technical_analyzer", mock_analyzer),
        ):
            result = await run_recommendation("AAPL", format="json")

        parsed = json.loads(result)
        assert parsed["position_size_pct"] == 0.0

    async def test_provider_error(self) -> None:
        from fin_toolkit.mcp_server.server import run_recommendation

        mock_reg = _mock_registry_with_agents({"a": _make_agent_result()})
        mock_router = AsyncMock()
        mock_router.get_prices.side_effect = AllProvidersFailedError(
            {"yahoo": "timeout"}
        )

        with (
            patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg),
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
        ):
            result = await run_recommendation("AAPL")

        parsed = json.loads(result)
        assert parsed["is_error"] is True


# ---------------------------------------------------------------------------
# run_portfolio_analysis
# ---------------------------------------------------------------------------


class TestRunPortfolioAnalysis:
    async def test_two_tickers_happy_path(self) -> None:
        from fin_toolkit.mcp_server.server import run_portfolio_analysis

        agents = {"buffett": _make_agent_result()}
        mock_reg = _mock_registry_with_agents(agents)
        mock_router = AsyncMock()
        mock_router.get_prices.side_effect = [
            _make_price_data("AAPL", 300),
            _make_price_data("MSFT", 300),
        ]
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_technical_result()

        with (
            patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg),
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch("fin_toolkit.mcp_server.server._technical_analyzer", mock_analyzer),
        ):
            result = await run_portfolio_analysis(
                ["AAPL", "MSFT"], format="json",
            )

        parsed = json.loads(result)
        assert "recommendations" in parsed
        assert "adjusted_sizes" in parsed
        assert "correlation" in parsed
        assert parsed["total_allocation_pct"] >= 0

    async def test_too_few_tickers_error(self) -> None:
        from fin_toolkit.mcp_server.server import run_portfolio_analysis

        result = await run_portfolio_analysis(["AAPL"], format="json")
        parsed = json.loads(result)
        assert parsed["is_error"] is True
        assert "at least 2" in parsed["error"]

    async def test_too_many_tickers_error(self) -> None:
        from fin_toolkit.mcp_server.server import run_portfolio_analysis

        tickers = [f"T{i}" for i in range(11)]
        result = await run_portfolio_analysis(tickers, format="json")
        parsed = json.loads(result)
        assert parsed["is_error"] is True
        assert "at most 10" in parsed["error"]

    async def test_partial_failure(self) -> None:
        from fin_toolkit.mcp_server.server import run_portfolio_analysis

        agents = {"buffett": _make_agent_result()}
        mock_reg = _mock_registry_with_agents(agents)
        mock_router = AsyncMock()
        # First succeeds, second fails
        mock_router.get_prices.side_effect = [
            _make_price_data("AAPL", 300),
            AllProvidersFailedError({"yahoo": "timeout"}),
        ]
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_technical_result()

        with (
            patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg),
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch("fin_toolkit.mcp_server.server._technical_analyzer", mock_analyzer),
        ):
            result = await run_portfolio_analysis(
                ["AAPL", "MSFT"], format="json",
            )

        parsed = json.loads(result)
        # Should still return results for AAPL
        assert "AAPL" in parsed["recommendations"]
        assert "MSFT" not in parsed["recommendations"]
        assert len(parsed["warnings"]) > 0


# ---------------------------------------------------------------------------
# screen_stocks
# ---------------------------------------------------------------------------


class TestScreenStocks:
    async def test_screen_with_tickers(self) -> None:
        from fin_toolkit.mcp_server.server import screen_stocks

        agents = {"buffett": _make_agent_result()}
        mock_reg = _mock_registry_with_agents(agents)
        mock_router = AsyncMock()
        mock_router.get_metrics.return_value = _make_metrics()

        with (
            patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg),
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
        ):
            result = await screen_stocks(
                tickers=["AAPL", "MSFT"], top_n=2, format="json",
            )

        parsed = json.loads(result)
        assert parsed["total_scanned"] == 2
        assert len(parsed["candidates"]) == 2
        for c in parsed["candidates"]:
            assert "quick_score" in c
            assert "consensus_score" in c

    async def test_screen_no_tickers_no_market_error(self) -> None:
        from fin_toolkit.mcp_server.server import screen_stocks

        mock_router = AsyncMock()
        with patch("fin_toolkit.mcp_server.server._provider_router", mock_router):
            result = await screen_stocks(format="json")

        parsed = json.loads(result)
        assert parsed["is_error"] is True

    async def test_screen_metrics_failure_warning(self) -> None:
        from fin_toolkit.mcp_server.server import screen_stocks

        mock_router = AsyncMock()
        mock_router.get_metrics.side_effect = TickerNotFoundError("BAD", "yahoo")
        mock_reg = _mock_registry_with_agents({})

        with (
            patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg),
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
        ):
            result = await screen_stocks(tickers=["BAD"], format="json")

        parsed = json.loads(result)
        assert parsed["total_scanned"] == 1
        assert len(parsed["candidates"]) == 0
        assert len(parsed["warnings"]) > 0


# ---------------------------------------------------------------------------
# generate_investment_idea
# ---------------------------------------------------------------------------


class TestGenerateInvestmentIdea:
    async def test_json_format(self) -> None:
        from fin_toolkit.mcp_server.server import generate_investment_idea

        agents = {"buffett": _make_agent_result()}
        mock_reg = _mock_registry_with_agents(agents)
        mock_router = AsyncMock()
        mock_router.get_prices.return_value = _make_price_data("AAPL", 300)
        mock_router.get_financials.return_value = _make_financials()
        mock_router.get_metrics.return_value = _make_metrics()
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_technical_result()
        mock_fund = MagicMock()
        mock_fund.analyze.return_value = _make_fundamental_result()

        with (
            patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg),
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch("fin_toolkit.mcp_server.server._technical_analyzer", mock_analyzer),
            patch("fin_toolkit.mcp_server.server._fundamental_analyzer", mock_fund),
            patch("fin_toolkit.mcp_server.server._search_router", None),
        ):
            result = await generate_investment_idea("AAPL", format="json")

        parsed = json.loads(result)
        assert parsed["ticker"] == "AAPL"
        assert "consensus" in parsed
        assert "fundamentals" in parsed
        assert "fcf_waterfall" in parsed
        assert "scenarios" in parsed
        assert len(parsed["scenarios"]) == 3

    async def test_html_format(self) -> None:
        from fin_toolkit.mcp_server.server import generate_investment_idea

        agents = {"buffett": _make_agent_result()}
        mock_reg = _mock_registry_with_agents(agents)
        mock_router = AsyncMock()
        mock_router.get_prices.return_value = _make_price_data("AAPL", 300)
        mock_router.get_financials.return_value = _make_financials()
        mock_router.get_metrics.return_value = _make_metrics()
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_technical_result()
        mock_fund = MagicMock()
        mock_fund.analyze.return_value = _make_fundamental_result()

        with (
            patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg),
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch("fin_toolkit.mcp_server.server._technical_analyzer", mock_analyzer),
            patch("fin_toolkit.mcp_server.server._fundamental_analyzer", mock_fund),
            patch("fin_toolkit.mcp_server.server._search_router", None),
            patch("webbrowser.open"),
        ):
            result = await generate_investment_idea("AAPL", format="html")

        # HTML output returns summary text (not JSON)
        assert "AAPL" in result
        assert "Report saved" in result

    async def test_provider_error_graceful(self) -> None:
        from fin_toolkit.mcp_server.server import generate_investment_idea

        mock_router = AsyncMock()
        mock_router.get_prices.side_effect = AllProvidersFailedError({"yahoo": "fail"})
        mock_router.get_financials.side_effect = AllProvidersFailedError({"yahoo": "fail"})
        mock_router.get_metrics.side_effect = AllProvidersFailedError({"yahoo": "fail"})
        mock_reg = _mock_registry_with_agents({})
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_technical_result()
        mock_fund = MagicMock()
        mock_fund.analyze.return_value = _make_fundamental_result()

        with (
            patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg),
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch("fin_toolkit.mcp_server.server._technical_analyzer", mock_analyzer),
            patch("fin_toolkit.mcp_server.server._fundamental_analyzer", mock_fund),
            patch("fin_toolkit.mcp_server.server._search_router", None),
        ):
            result = await generate_investment_idea("AAPL", format="json")

        # Should still return a result (with warnings), not an error
        parsed = json.loads(result)
        assert parsed["ticker"] == "AAPL"
        assert len(parsed["warnings"]) > 0


# ---------------------------------------------------------------------------
# parse_report
# ---------------------------------------------------------------------------


class TestParseReport:
    async def test_parse_report_returns_financials(self) -> None:
        from fin_toolkit.mcp_server.server import parse_report

        mock_fin = MagicMock()
        mock_fin.model_dump.return_value = {
            "ticker": "TEST",
            "income_statement": {"revenue": 100000},
            "balance_sheet": None,
            "cash_flow": None,
            "income_history": None,
            "cash_flow_history": None,
        }

        with patch(
            "fin_toolkit.mcp_server.server.parse_financial_report",
            return_value=mock_fin,
            create=True,
        ):
            # Need to patch at the import location
            with patch(
                "fin_toolkit.providers.pdf_report.parse_financial_report",
                return_value=mock_fin,
            ):
                result = await parse_report("/fake.pdf", "TEST", format="json")

        parsed = json.loads(result)
        assert parsed["ticker"] == "TEST"


# ---------------------------------------------------------------------------
# screen_stocks with filters
# ---------------------------------------------------------------------------


class TestScreenStocksWithFilters:
    async def test_filter_excludes_tickers(self) -> None:
        """Tickers not matching filters are excluded."""
        from fin_toolkit.mcp_server.server import screen_stocks

        # AAPL has pe=20 (fails <15), MSFT has pe=10 (passes)
        metrics_aapl = KeyMetrics(
            ticker="AAPL", pe_ratio=20.0, pb_ratio=3.0, market_cap=1e9,
            dividend_yield=0.01, roe=0.15, roa=0.08, debt_to_equity=0.5,
        )
        metrics_msft = KeyMetrics(
            ticker="MSFT", pe_ratio=10.0, pb_ratio=2.0, market_cap=2e9,
            dividend_yield=0.02, roe=0.20, roa=0.10, debt_to_equity=0.3,
        )
        mock_router = AsyncMock()
        mock_router.get_metrics.side_effect = [metrics_aapl, metrics_msft]
        mock_reg = _mock_registry_with_agents({"b": _make_agent_result()})

        with (
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg),
        ):
            result = await screen_stocks(
                tickers=["AAPL", "MSFT"],
                filters={"pe_ratio": "<15"},
                format="json",
            )

        parsed = json.loads(result)
        assert parsed["total_scanned"] == 2
        assert len(parsed["candidates"]) == 1
        assert parsed["candidates"][0]["ticker"] == "MSFT"
        assert parsed["filters_applied"] == {"pe_ratio": "<15"}

    async def test_no_filters_returns_all(self) -> None:
        """Without filters, all tickers pass."""
        from fin_toolkit.mcp_server.server import screen_stocks

        mock_router = AsyncMock()
        mock_router.get_metrics.return_value = _make_metrics()
        mock_reg = _mock_registry_with_agents({"b": _make_agent_result()})

        with (
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg),
        ):
            result = await screen_stocks(
                tickers=["AAPL"], format="json",
            )

        parsed = json.loads(result)
        assert len(parsed["candidates"]) == 1
        assert parsed["filters_applied"] is None


# ---------------------------------------------------------------------------
# deep_dive
# ---------------------------------------------------------------------------


class TestDeepDive:
    async def test_single_ticker_happy_path(self) -> None:
        from fin_toolkit.mcp_server.server import deep_dive

        agents = {"buffett": _make_agent_result()}
        mock_reg = _mock_registry_with_agents(agents)
        mock_router = AsyncMock()
        mock_router.get_prices.return_value = _make_price_data("AAPL", 300)
        mock_router.get_financials.return_value = _make_financials()
        mock_router.get_metrics.return_value = _make_metrics()
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_technical_result()
        mock_fund = MagicMock()
        mock_fund.analyze.return_value = _make_fundamental_result()

        with (
            patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg),
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch("fin_toolkit.mcp_server.server._technical_analyzer", mock_analyzer),
            patch("fin_toolkit.mcp_server.server._fundamental_analyzer", mock_fund),
            patch("fin_toolkit.mcp_server.server._search_router", None),
        ):
            result = await deep_dive(["AAPL"], format="json")

        parsed = json.loads(result)
        assert "AAPL" in parsed["items"]
        item = parsed["items"]["AAPL"]
        assert item["ticker"] == "AAPL"
        assert item["fundamentals"] is not None
        assert item["technical"] is not None
        assert item["consensus"] is not None

    async def test_too_many_tickers_error(self) -> None:
        from fin_toolkit.mcp_server.server import deep_dive

        mock_router = AsyncMock()
        mock_analyzer = MagicMock()
        mock_fund = MagicMock()

        with (
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch("fin_toolkit.mcp_server.server._technical_analyzer", mock_analyzer),
            patch("fin_toolkit.mcp_server.server._fundamental_analyzer", mock_fund),
        ):
            result = await deep_dive([f"T{i}" for i in range(11)], format="json")

        parsed = json.loads(result)
        assert parsed["is_error"] is True
        assert "10" in parsed["error"]

    async def test_partial_failure(self) -> None:
        from fin_toolkit.mcp_server.server import deep_dive

        agents = {"buffett": _make_agent_result()}
        mock_reg = _mock_registry_with_agents(agents)
        mock_router = AsyncMock()
        # First ticker succeeds, second fails on prices
        mock_router.get_prices.side_effect = [
            _make_price_data("AAPL", 300),
            AllProvidersFailedError({"yahoo": "timeout"}),
        ]
        mock_router.get_financials.return_value = _make_financials()
        mock_router.get_metrics.return_value = _make_metrics()
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_technical_result()
        mock_fund = MagicMock()
        mock_fund.analyze.return_value = _make_fundamental_result()

        with (
            patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg),
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch("fin_toolkit.mcp_server.server._technical_analyzer", mock_analyzer),
            patch("fin_toolkit.mcp_server.server._fundamental_analyzer", mock_fund),
            patch("fin_toolkit.mcp_server.server._search_router", None),
        ):
            result = await deep_dive(["AAPL", "BAD"], format="json")

        parsed = json.loads(result)
        assert "AAPL" in parsed["items"]
        # BAD partially succeeds (financials/metrics OK) but prices fail
        # → warnings are at item level, not batch level
        assert "BAD" in parsed["items"]
        assert len(parsed["items"]["BAD"]["warnings"]) > 0


# ---------------------------------------------------------------------------
# compare_stocks
# ---------------------------------------------------------------------------


class TestCompareStocks:
    async def test_two_tickers_happy_path(self) -> None:
        from fin_toolkit.mcp_server.server import compare_stocks

        agents = {"buffett": _make_agent_result()}
        mock_reg = _mock_registry_with_agents(agents)
        mock_router = AsyncMock()
        mock_router.get_metrics.return_value = _make_metrics()
        mock_router.get_prices.return_value = _make_price_data("AAPL", 300)
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_technical_result()

        with (
            patch("fin_toolkit.mcp_server.server._agent_registry", mock_reg),
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch("fin_toolkit.mcp_server.server._technical_analyzer", mock_analyzer),
        ):
            result = await compare_stocks(["AAPL", "MSFT"], format="json")

        parsed = json.loads(result)
        assert "AAPL" in parsed["tickers"]
        assert "MSFT" in parsed["tickers"]
        assert "pe_ratio" in parsed["matrix"]

    async def test_too_few_error(self) -> None:
        from fin_toolkit.mcp_server.server import compare_stocks

        mock_router = AsyncMock()
        with patch("fin_toolkit.mcp_server.server._provider_router", mock_router):
            result = await compare_stocks(["AAPL"], format="json")

        parsed = json.loads(result)
        assert parsed["is_error"] is True

    async def test_too_many_error(self) -> None:
        from fin_toolkit.mcp_server.server import compare_stocks

        mock_router = AsyncMock()
        with patch("fin_toolkit.mcp_server.server._provider_router", mock_router):
            result = await compare_stocks([f"T{i}" for i in range(11)], format="json")

        parsed = json.loads(result)
        assert parsed["is_error"] is True


# ---------------------------------------------------------------------------
# manage_watchlist / set_alert / check_watchlist
# ---------------------------------------------------------------------------


class TestManageWatchlist:
    async def test_add_ticker(self, tmp_path: Path) -> None:
        from fin_toolkit.mcp_server.server import manage_watchlist

        store = WatchlistStore(path=tmp_path / "w.yaml")
        with patch("fin_toolkit.mcp_server.server._watchlist_store", store):
            result = await manage_watchlist(
                action="add", ticker="AAPL", format="json",
            )

        parsed = json.loads(result)
        assert parsed["status"] == "ok"
        assert parsed["ticker"] == "AAPL"

    async def test_list_watchlists(self, tmp_path: Path) -> None:
        from fin_toolkit.mcp_server.server import manage_watchlist

        store = WatchlistStore(path=tmp_path / "w.yaml")
        # Add a ticker first
        from fin_toolkit.analysis.alerts import WatchlistEntry
        store.add_ticker("default", WatchlistEntry(ticker="AAPL", added_at="2024-01-01"))

        with patch("fin_toolkit.mcp_server.server._watchlist_store", store):
            result = await manage_watchlist(action="list", format="json")

        parsed = json.loads(result)
        assert len(parsed["watchlists"]) == 1
        assert parsed["watchlists"][0]["name"] == "default"

    async def test_show_watchlist(self, tmp_path: Path) -> None:
        from fin_toolkit.mcp_server.server import manage_watchlist

        store = WatchlistStore(path=tmp_path / "w.yaml")
        from fin_toolkit.analysis.alerts import WatchlistEntry
        store.add_ticker("default", WatchlistEntry(ticker="AAPL", added_at="2024-01-01"))

        with patch("fin_toolkit.mcp_server.server._watchlist_store", store):
            result = await manage_watchlist(action="show", format="json")

        parsed = json.loads(result)
        assert parsed["watchlist"] == "default"
        assert len(parsed["entries"]) == 1

    async def test_remove_ticker(self, tmp_path: Path) -> None:
        from fin_toolkit.mcp_server.server import manage_watchlist

        store = WatchlistStore(path=tmp_path / "w.yaml")
        from fin_toolkit.analysis.alerts import WatchlistEntry
        store.add_ticker("default", WatchlistEntry(ticker="AAPL", added_at="2024-01-01"))

        with patch("fin_toolkit.mcp_server.server._watchlist_store", store):
            result = await manage_watchlist(
                action="remove", ticker="AAPL", format="json",
            )

        parsed = json.loads(result)
        assert parsed["status"] == "ok"

    async def test_no_store_error(self) -> None:
        from fin_toolkit.mcp_server.server import manage_watchlist

        with patch("fin_toolkit.mcp_server.server._watchlist_store", None):
            result = await manage_watchlist(action="list", format="json")

        parsed = json.loads(result)
        assert parsed["is_error"] is True

    async def test_add_no_ticker_error(self, tmp_path: Path) -> None:
        from fin_toolkit.mcp_server.server import manage_watchlist

        store = WatchlistStore(path=tmp_path / "w.yaml")
        with patch("fin_toolkit.mcp_server.server._watchlist_store", store):
            result = await manage_watchlist(action="add", format="json")

        parsed = json.loads(result)
        assert parsed["is_error"] is True


class TestSetAlert:
    async def test_set_alert_ok(self, tmp_path: Path) -> None:
        from fin_toolkit.mcp_server.server import set_alert

        store = WatchlistStore(path=tmp_path / "w.yaml")
        from fin_toolkit.analysis.alerts import WatchlistEntry
        store.add_ticker("default", WatchlistEntry(ticker="AAPL", added_at="2024-01-01"))

        with patch("fin_toolkit.mcp_server.server._watchlist_store", store):
            result = await set_alert(
                watchlist="default", ticker="AAPL",
                metric="pe_ratio", operator=">", threshold=25.0,
                format="json",
            )

        parsed = json.loads(result)
        assert parsed["status"] == "ok"
        assert parsed["metric"] == "pe_ratio"


class TestCheckWatchlist:
    async def test_check_with_triggered_alert(self, tmp_path: Path) -> None:
        from fin_toolkit.mcp_server.server import check_watchlist

        store = WatchlistStore(path=tmp_path / "w.yaml")
        from fin_toolkit.analysis.alerts import AlertRule, WatchlistEntry
        entry = WatchlistEntry(
            ticker="AAPL", added_at="2024-01-01",
            alerts=[AlertRule(metric="pe_ratio", operator=">", threshold=15.0, label="High P/E")],
        )
        store.add_ticker("default", entry)

        mock_router = AsyncMock()
        mock_router.get_metrics.return_value = _make_metrics()  # pe=20
        mock_router.get_prices.return_value = _make_price_data("AAPL", 300)
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_technical_result()

        with (
            patch("fin_toolkit.mcp_server.server._watchlist_store", store),
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch("fin_toolkit.mcp_server.server._technical_analyzer", mock_analyzer),
        ):
            result = await check_watchlist(format="json")

        parsed = json.loads(result)
        assert parsed["watchlist_name"] == "default"
        assert len(parsed["alerts_triggered"]) == 1
        assert parsed["alerts_triggered"][0]["metric"] == "pe_ratio"

    async def test_check_no_alerts_empty(self, tmp_path: Path) -> None:
        from fin_toolkit.mcp_server.server import check_watchlist

        store = WatchlistStore(path=tmp_path / "w.yaml")
        from fin_toolkit.analysis.alerts import WatchlistEntry
        store.add_ticker("default", WatchlistEntry(ticker="AAPL", added_at="2024-01-01"))

        mock_router = AsyncMock()
        mock_router.get_metrics.return_value = _make_metrics()
        mock_router.get_prices.return_value = _make_price_data("AAPL", 300)
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = _make_technical_result()

        with (
            patch("fin_toolkit.mcp_server.server._watchlist_store", store),
            patch("fin_toolkit.mcp_server.server._provider_router", mock_router),
            patch("fin_toolkit.mcp_server.server._technical_analyzer", mock_analyzer),
        ):
            result = await check_watchlist(format="json")

        parsed = json.loads(result)
        assert parsed["alerts_triggered"] == []
