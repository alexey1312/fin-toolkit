"""Tests for MCP server tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

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
            result = await get_stock_data("AAPL", "1y", None)

        parsed = json.loads(result)
        assert parsed["ticker"] == "AAPL"
        assert len(parsed["prices"]) == 60

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
            result = await run_technical_analysis("AAPL")

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
            result = await run_fundamental_analysis("AAPL")

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
            result = await run_fundamental_analysis("AAPL", sector="Technology")

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
            result = await run_fundamental_analysis("AAPL")

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
            result = await run_risk_analysis(["AAPL", "MSFT"], "1y")

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
            result = await run_risk_analysis(["AAPL"])

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
            result = await search_news("AAPL earnings", 10)

        parsed = json.loads(result)
        assert "results" in parsed
        assert len(parsed["results"]) == 1
        assert parsed["results"][0]["title"] == "AAPL News"

    async def test_no_provider_returns_warning(self) -> None:
        """No search provider returns empty results with warning."""
        from fin_toolkit.mcp_server.server import search_news

        with patch("fin_toolkit.mcp_server.server._search_router", None):
            result = await search_news("AAPL earnings")

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
            result = await search_news("AAPL earnings")

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
            result = await run_agent("AAPL", "elvis_marlamov")

        parsed = json.loads(result)
        assert parsed["signal"] == "Bullish"
        assert parsed["score"] == 75.0

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
