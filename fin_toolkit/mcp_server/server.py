"""FastMCP server with financial analysis tools."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from fastmcp import FastMCP

from fin_toolkit.agents.registry import AgentRegistry
from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.risk import (
    calculate_var,
    calculate_volatility,
    correlation_matrix,
)
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.exceptions import FinToolkitError
from fin_toolkit.providers.router import ProviderRouter
from fin_toolkit.providers.search_router import SearchRouter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level shared state (set by init_server or CLI)
# ---------------------------------------------------------------------------

_provider_router: ProviderRouter | None = None
_search_router: SearchRouter | None = None
_technical_analyzer: TechnicalAnalyzer | None = None
_fundamental_analyzer: FundamentalAnalyzer | None = None
_agent_registry: AgentRegistry | None = None

mcp = FastMCP("fin-toolkit")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _error_response(message: str) -> str:
    """Return a structured JSON error string."""
    return json.dumps({"error": message, "is_error": True})


def _period_to_dates(period: str) -> tuple[str, str]:
    """Convert a period string like '1y' to (start, end) date strings."""
    end = datetime.now()
    mapping: dict[str, timedelta] = {
        "1m": timedelta(days=30),
        "3m": timedelta(days=90),
        "6m": timedelta(days=180),
        "1y": timedelta(days=365),
        "2y": timedelta(days=730),
        "5y": timedelta(days=1825),
    }
    delta = mapping.get(period, timedelta(days=365))
    start = end - delta
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _detect_sector(ticker: str) -> str | None:
    """Try to auto-detect sector via yfinance. Returns None on failure."""
    try:
        import yfinance as yf

        info: dict[str, object] = yf.Ticker(ticker).info  # type: ignore[no-untyped-call]
        sector = info.get("sector")
        return str(sector) if sector is not None else None
    except Exception:
        return None


def init_server(
    provider_router: ProviderRouter,
    search_router: SearchRouter | None,
    technical_analyzer: TechnicalAnalyzer,
    fundamental_analyzer: FundamentalAnalyzer,
    agent_registry: AgentRegistry,
) -> FastMCP:
    """Initialize shared state and return the MCP server instance."""
    global _provider_router, _search_router  # noqa: PLW0603
    global _technical_analyzer, _fundamental_analyzer, _agent_registry  # noqa: PLW0603

    _provider_router = provider_router
    _search_router = search_router
    _technical_analyzer = technical_analyzer
    _fundamental_analyzer = fundamental_analyzer
    _agent_registry = agent_registry

    return mcp


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool
async def get_stock_data(
    ticker: str,
    period: str = "1y",
    provider: str | None = None,
) -> str:
    """Get historical stock price data for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT).
        period: Time period - 1m, 3m, 6m, 1y, 2y, 5y.
        provider: Force a specific data provider (optional).
    """
    try:
        assert _provider_router is not None
        start, end = _period_to_dates(period)
        price_data = await _provider_router.get_prices(ticker, start, end, provider)
        return json.dumps(price_data.model_dump())
    except FinToolkitError as exc:
        return _error_response(str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in get_stock_data")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def run_technical_analysis(ticker: str) -> str:
    """Run technical analysis on a stock ticker.

    Computes RSI, EMA, Bollinger Bands, MACD, and derives trading signals.

    Args:
        ticker: Stock ticker symbol.
    """
    try:
        assert _provider_router is not None
        assert _technical_analyzer is not None
        start, end = _period_to_dates("1y")
        price_data = await _provider_router.get_prices(ticker, start, end)
        result = _technical_analyzer.analyze(price_data)
        return json.dumps(result.model_dump())
    except FinToolkitError as exc:
        return _error_response(str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in run_technical_analysis")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def run_fundamental_analysis(
    ticker: str,
    sector: str | None = None,
) -> str:
    """Run fundamental analysis on a stock ticker.

    Computes profitability, valuation, and stability ratios with optional
    sector comparison.

    Args:
        ticker: Stock ticker symbol.
        sector: Sector for comparison (auto-detected if not provided).
    """
    try:
        assert _provider_router is not None
        assert _fundamental_analyzer is not None
        financials = await _provider_router.get_financials(ticker)
        metrics = await _provider_router.get_metrics(ticker)

        if sector is None:
            sector = _detect_sector(ticker)

        result = _fundamental_analyzer.analyze(financials, metrics, sector=sector)
        return json.dumps(result.model_dump())
    except FinToolkitError as exc:
        return _error_response(str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in run_fundamental_analysis")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def run_risk_analysis(
    tickers: list[str],
    period: str = "1y",
) -> str:
    """Run risk analysis on one or more tickers.

    Computes volatility, Value at Risk, and correlation matrix.

    Args:
        tickers: List of stock ticker symbols.
        period: Time period for analysis.
    """
    try:
        assert _provider_router is not None
        start, end = _period_to_dates(period)

        prices_map: dict[str, Any] = {}
        for ticker in tickers:
            prices_map[ticker] = await _provider_router.get_prices(
                ticker, start, end
            )

        risk: dict[str, Any] = {}
        for ticker, price_data in prices_map.items():
            warnings: list[str] = []
            vol_30 = _safe_calculate(calculate_volatility, price_data, 30, warnings)
            vol_90 = _safe_calculate(calculate_volatility, price_data, 90, warnings)
            vol_252 = _safe_calculate(calculate_volatility, price_data, 252, warnings)
            var_95 = _safe_calculate_var(price_data, 0.95, warnings)
            var_99 = _safe_calculate_var(price_data, 0.99, warnings)

            from fin_toolkit.models.results import RiskResult

            risk[ticker] = RiskResult(
                volatility_30d=vol_30,
                volatility_90d=vol_90,
                volatility_252d=vol_252,
                var_95=var_95,
                var_99=var_99,
                warnings=warnings,
            ).model_dump()

        corr = correlation_matrix(prices_map)

        return json.dumps({"risk": risk, "correlation": corr.model_dump()})
    except FinToolkitError as exc:
        return _error_response(str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in run_risk_analysis")
        return _error_response(f"Internal error: {exc}")


def _safe_calculate(
    fn: Any,
    price_data: Any,
    window: int,
    warnings: list[str],
) -> float | None:
    """Calculate volatility, returning None on insufficient data."""
    try:
        return fn(price_data, window)  # type: ignore[no-any-return]
    except Exception as exc:
        warnings.append(str(exc))
        return None


def _safe_calculate_var(
    price_data: Any,
    confidence: float,
    warnings: list[str],
) -> float | None:
    """Calculate VaR, returning None on insufficient data."""
    try:
        return calculate_var(price_data, confidence)
    except Exception as exc:
        warnings.append(str(exc))
        return None


@mcp.tool
async def search_news(
    query: str,
    max_results: int = 10,
) -> str:
    """Search for financial news and articles.

    Args:
        query: Search query (e.g. "AAPL earnings Q4 2024").
        max_results: Maximum number of results to return.
    """
    try:
        if _search_router is None:
            return json.dumps(
                {
                    "results": [],
                    "warning": "No search provider configured. "
                    "Add a Brave API key or SearXNG URL to enable search.",
                }
            )

        results = await _search_router.search(query, max_results=max_results)
        return json.dumps({"results": [r.model_dump() for r in results]})
    except FinToolkitError as exc:
        return _error_response(str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in search_news")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def run_agent(
    ticker: str,
    agent: str = "elvis_marlamov",
) -> str:
    """Run an AI analysis agent on a stock ticker.

    Available agents: elvis_marlamov, warren_buffett.

    Args:
        ticker: Stock ticker symbol.
        agent: Agent name to use for analysis.
    """
    try:
        assert _agent_registry is not None
        agent_instance = _agent_registry.get_agent(agent)
        result = await agent_instance.analyze(ticker)
        return json.dumps(result.model_dump())
    except FinToolkitError as exc:
        return _error_response(str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in run_agent")
        return _error_response(f"Internal error: {exc}")
