"""FastMCP server with financial analysis tools."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any

from fastmcp import FastMCP

from fin_toolkit.agents.registry import AgentRegistry
from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.portfolio import (
    adjust_position_sizes,
    compute_consensus,
    compute_position_size,
    compute_recommendation_text,
    compute_stop_loss,
)
from fin_toolkit.analysis.risk import (
    calculate_var,
    calculate_volatility,
    correlation_matrix,
)
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.exceptions import FinToolkitError
from fin_toolkit.mcp_server.serialize import serialize
from fin_toolkit.models.price_data import PriceData
from fin_toolkit.models.results import (
    ConsensusResult,
    CorrelationResult,
    PortfolioResult,
    RecommendationResult,
    RiskResult,
)
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
        "1y": timedelta(days=400),
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
    format: str = "toon",
) -> str:
    """Get historical stock price data for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT).
        period: Time period - 1m, 3m, 6m, 1y, 2y, 5y.
        provider: Force a specific data provider (optional).
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        assert _provider_router is not None
        start, end = _period_to_dates(period)
        price_data = await _provider_router.get_prices(ticker, start, end, provider)
        return serialize(price_data.model_dump(), format)
    except FinToolkitError as exc:
        return _error_response(str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in get_stock_data")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def run_technical_analysis(ticker: str, format: str = "toon") -> str:
    """Run technical analysis on a stock ticker.

    Computes RSI, EMA, Bollinger Bands, MACD, and derives trading signals.

    Args:
        ticker: Stock ticker symbol.
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        assert _provider_router is not None
        assert _technical_analyzer is not None
        start, end = _period_to_dates("1y")
        price_data = await _provider_router.get_prices(ticker, start, end)
        result = _technical_analyzer.analyze(price_data)
        return serialize(result.model_dump(), format)
    except FinToolkitError as exc:
        return _error_response(str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in run_technical_analysis")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def run_fundamental_analysis(
    ticker: str,
    sector: str | None = None,
    format: str = "toon",
) -> str:
    """Run fundamental analysis on a stock ticker.

    Computes profitability, valuation, and stability ratios with optional
    sector comparison.

    Args:
        ticker: Stock ticker symbol.
        sector: Sector for comparison (auto-detected if not provided).
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        assert _provider_router is not None
        assert _fundamental_analyzer is not None
        financials = await _provider_router.get_financials(ticker)
        metrics = await _provider_router.get_metrics(ticker)

        if sector is None:
            sector = _detect_sector(ticker)

        result = _fundamental_analyzer.analyze(financials, metrics, sector=sector)
        return serialize(result.model_dump(), format)
    except FinToolkitError as exc:
        return _error_response(str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in run_fundamental_analysis")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def run_risk_analysis(
    tickers: list[str],
    period: str = "1y",
    format: str = "toon",
) -> str:
    """Run risk analysis on one or more tickers.

    Computes volatility, Value at Risk, and correlation matrix.

    Args:
        tickers: List of stock ticker symbols.
        period: Time period for analysis.
        format: Response format - "toon" (default, token-efficient) or "json".
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

        combined: dict[str, Any] = {"risk": risk, "correlation": corr.model_dump()}
        return serialize(combined, format)
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
    format: str = "toon",
) -> str:
    """Search for financial news and articles.

    Args:
        query: Search query (e.g. "AAPL earnings Q4 2024").
        max_results: Maximum number of results to return.
        format: Response format - "toon" (default, token-efficient) or "json".
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
        data: dict[str, Any] = {"results": [r.model_dump() for r in results]}
        if not results:
            data["warning"] = (
                "Search returned no results. "
                "All configured providers may be unavailable."
            )
        return serialize(data, format)
    except FinToolkitError as exc:
        return _error_response(str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in search_news")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def run_agent(
    ticker: str,
    agent: str = "elvis_marlamov",
    format: str = "toon",
) -> str:
    """Run an AI analysis agent on a stock ticker.

    Available agents: elvis_marlamov, warren_buffett, ben_graham,
    charlie_munger, cathie_wood, peter_lynch.

    Args:
        ticker: Stock ticker symbol.
        agent: Agent name to use for analysis.
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        assert _agent_registry is not None
        agent_instance = _agent_registry.get_agent(agent)
        result = await agent_instance.analyze(ticker)
        return serialize(result.model_dump(), format)
    except FinToolkitError as exc:
        return _error_response(str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in run_agent")
        return _error_response(f"Internal error: {exc}")


# ---------------------------------------------------------------------------
# Private helpers for consensus / recommendation / portfolio
# ---------------------------------------------------------------------------


async def _run_consensus(ticker: str) -> ConsensusResult:
    """Run all active agents concurrently and compute consensus."""
    assert _agent_registry is not None
    agents = _agent_registry.get_active_agents()
    if not agents:
        return compute_consensus({}, {"_": "No active agents in registry"})

    tasks = {name: ag.analyze(ticker) for name, ag in agents.items()}
    results_raw = await asyncio.gather(*tasks.values(), return_exceptions=True)

    agent_results = {}
    agent_errors = {}
    for name, result in zip(tasks.keys(), results_raw, strict=True):
        if isinstance(result, BaseException):
            agent_errors[name] = str(result)
        else:
            agent_results[name] = result

    return compute_consensus(agent_results, agent_errors)


def _compute_risk(price_data: PriceData) -> RiskResult:
    """Compute risk metrics from price data."""
    warnings: list[str] = []
    vol_30 = _safe_calculate(calculate_volatility, price_data, 30, warnings)
    vol_90 = _safe_calculate(calculate_volatility, price_data, 90, warnings)
    vol_252 = _safe_calculate(calculate_volatility, price_data, 252, warnings)
    var_95 = _safe_calculate_var(price_data, 0.95, warnings)
    var_99 = _safe_calculate_var(price_data, 0.99, warnings)
    return RiskResult(
        volatility_30d=vol_30,
        volatility_90d=vol_90,
        volatility_252d=vol_252,
        var_95=var_95,
        var_99=var_99,
        warnings=warnings,
    )


async def _run_single_recommendation(
    ticker: str, start: str, end: str,
) -> tuple[RecommendationResult, PriceData]:
    """Full recommendation for one ticker. Returns (result, price_data)."""
    assert _provider_router is not None
    assert _technical_analyzer is not None

    consensus_task = _run_consensus(ticker)
    prices_task = _provider_router.get_prices(ticker, start, end)
    consensus, price_data = await asyncio.gather(consensus_task, prices_task)

    risk = _compute_risk(price_data)
    technical = _technical_analyzer.analyze(price_data)

    position_size = compute_position_size(consensus, risk, technical)
    stop_loss = compute_stop_loss(risk, technical)
    recommendation = compute_recommendation_text(consensus, position_size, risk)

    rec_warnings: list[str] = []
    rec_warnings.extend(consensus.warnings)
    rec_warnings.extend(risk.warnings)
    rec_warnings.extend(technical.warnings)

    result = RecommendationResult(
        ticker=ticker,
        consensus=consensus,
        risk=risk,
        technical=technical,
        position_size_pct=position_size,
        stop_loss_pct=stop_loss,
        recommendation=recommendation,
        warnings=rec_warnings,
    )
    return result, price_data


# ---------------------------------------------------------------------------
# Consensus / Recommendation / Portfolio tools
# ---------------------------------------------------------------------------


@mcp.tool
async def run_all_agents(ticker: str, format: str = "toon") -> str:
    """Run all active analysis agents on a ticker and compute consensus.

    Returns aggregated consensus score, signal, confidence, and per-agent results.

    Args:
        ticker: Stock ticker symbol.
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        consensus = await _run_consensus(ticker)
        if not consensus.agent_results:
            return _error_response(
                "All agents failed: "
                + "; ".join(f"{k}: {v}" for k, v in consensus.agent_errors.items())
            )
        return serialize(consensus.model_dump(), format)
    except FinToolkitError as exc:
        return _error_response(str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in run_all_agents")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def run_recommendation(
    ticker: str, period: str = "1y", format: str = "toon",
) -> str:
    """Generate a buy/hold recommendation with position sizing for a ticker.

    Combines consensus from all agents, risk analysis, and technical signals
    to produce a position size (0-25% portfolio) and stop-loss level.

    Args:
        ticker: Stock ticker symbol.
        period: Time period for price data - 1m, 3m, 6m, 1y, 2y, 5y.
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        start, end = _period_to_dates(period)
        result, _ = await _run_single_recommendation(ticker, start, end)
        return serialize(result.model_dump(), format)
    except FinToolkitError as exc:
        return _error_response(str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in run_recommendation")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def run_portfolio_analysis(
    tickers: list[str], period: str = "1y", format: str = "toon",
) -> str:
    """Analyze a portfolio of tickers with correlation-adjusted position sizing.

    Runs recommendations for each ticker, computes correlation matrix, and
    adjusts position sizes based on pairwise correlations.

    Args:
        tickers: List of 2-10 stock ticker symbols.
        period: Time period for price data.
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        if len(tickers) < 2:
            return _error_response("Portfolio analysis requires at least 2 tickers")
        if len(tickers) > 10:
            return _error_response("Portfolio analysis supports at most 10 tickers")

        start, end = _period_to_dates(period)
        tasks = [_run_single_recommendation(t, start, end) for t in tickers]
        results_raw = await asyncio.gather(*tasks, return_exceptions=True)

        recommendations: dict[str, RecommendationResult] = {}
        prices_map: dict[str, PriceData] = {}
        raw_sizes: dict[str, float] = {}
        portfolio_warnings: list[str] = []

        for ticker, result in zip(tickers, results_raw, strict=True):
            if isinstance(result, BaseException):
                portfolio_warnings.append(f"{ticker}: {result}")
                continue
            rec, price_data = result
            recommendations[ticker] = rec
            prices_map[ticker] = price_data
            raw_sizes[ticker] = rec.position_size_pct

        if not recommendations:
            return _error_response(
                "All tickers failed: " + "; ".join(portfolio_warnings)
            )

        # Correlation matrix from available price data
        if len(prices_map) >= 2:
            corr = correlation_matrix(prices_map)
        else:
            only_ticker = next(iter(prices_map))
            corr = CorrelationResult(
                tickers=[only_ticker],
                matrix={only_ticker: {only_ticker: 1.0}},
                warnings=["Only 1 ticker available; no correlation adjustment"],
            )

        adjusted = adjust_position_sizes(raw_sizes, corr)
        total = sum(adjusted.values())

        portfolio = PortfolioResult(
            recommendations=recommendations,
            adjusted_sizes=adjusted,
            correlation=corr,
            total_allocation_pct=total,
            warnings=portfolio_warnings,
        )
        return serialize(portfolio.model_dump(), format)
    except FinToolkitError as exc:
        return _error_response(str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in run_portfolio_analysis")
        return _error_response(f"Internal error: {exc}")
