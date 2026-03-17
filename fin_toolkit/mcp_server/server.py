"""FastMCP server with financial analysis tools."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any

from fastmcp import Context, FastMCP

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
    ComparisonInput,
    ConsensusResult,
    CorrelationResult,
    DeepDiveItem,
    DeepDiveResult,
    InvestmentIdeaResult,
    PortfolioResult,
    RecommendationResult,
    RiskResult,
    ScreeningCandidate,
    ScreeningResult,
    WatchlistCheckResult,
    WatchlistInfo,
)
from fin_toolkit.portfolio_store import PortfolioStore
from fin_toolkit.providers.router import ProviderRouter
from fin_toolkit.providers.search_router import SearchRouter
from fin_toolkit.watchlist import WatchlistStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level shared state (set by init_server or CLI)
# ---------------------------------------------------------------------------

_provider_router: ProviderRouter | None = None
_search_router: SearchRouter | None = None
_technical_analyzer: TechnicalAnalyzer | None = None
_fundamental_analyzer: FundamentalAnalyzer | None = None
_agent_registry: AgentRegistry | None = None
_watchlist_store: WatchlistStore | None = None
_portfolio_store: PortfolioStore | None = None

mcp = FastMCP("fin-toolkit")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _error_response(exc: FinToolkitError | str) -> str:
    """Return a structured JSON error string, with hint if available."""
    if isinstance(exc, str):
        return json.dumps({"error": exc, "is_error": True})
    payload: dict[str, object] = {"error": str(exc), "is_error": True}
    if exc.hint:
        payload["hint"] = exc.hint
    return json.dumps(payload)


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
    watchlist_store: WatchlistStore | None = None,
    portfolio_store: PortfolioStore | None = None,
) -> FastMCP:
    """Initialize shared state and return the MCP server instance."""
    global _provider_router, _search_router  # noqa: PLW0603
    global _technical_analyzer, _fundamental_analyzer, _agent_registry  # noqa: PLW0603
    global _watchlist_store, _portfolio_store  # noqa: PLW0603

    _provider_router = provider_router
    _search_router = search_router
    _technical_analyzer = technical_analyzer
    _fundamental_analyzer = fundamental_analyzer
    _agent_registry = agent_registry
    _watchlist_store = watchlist_store
    _portfolio_store = portfolio_store

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
    """START HERE: fetch price data for any stock, ETF, or crypto ticker.

    Supports US, European, Asian, Russian (MOEX), and Kazakh (KASE) markets.
    For Russian tickers (SBER, GAZP, LKOH), use provider="moex".
    See also: deep_dive for batch analysis, run_technical_analysis for indicators.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, MSFT, SBER).
        period: Time period - 1m, 3m, 6m, 1y, 2y, 5y.
        provider: Force a specific data provider (e.g. "moex" for Russian stocks).
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        assert _provider_router is not None
        start, end = _period_to_dates(period)
        price_data = await _provider_router.get_prices(ticker, start, end, provider)
        return serialize(price_data.model_dump(), format)
    except FinToolkitError as exc:
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in get_stock_data")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def run_technical_analysis(ticker: str, format: str = "toon") -> str:
    """Compute technical indicators and trading signals for a ticker.

    Returns RSI, EMA (20/50/200), Bollinger Bands, MACD, signals, overall bias.
    See also: get_stock_data for raw prices, run_fundamental_analysis for ratios.

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
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in run_technical_analysis")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def run_fundamental_analysis(
    ticker: str,
    sector: str | None = None,
    format: str = "toon",
) -> str:
    """Compute profitability, valuation, and stability ratios for a ticker.

    Returns ROE, ROA, ROIC, margins, P/E, P/B, EV/EBITDA, FCF yield, D/E, etc.
    See also: run_all_agents for AI-driven analysis, deep_dive for batch.

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
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in run_fundamental_analysis")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def get_analyst_estimates(
    ticker: str,
    format: str = "toon",
) -> str:
    """Get Wall Street analyst target prices, ratings, and earnings history.

    Returns analyst consensus (Buy/Hold/Sell), target prices (low/median/high),
    forward P/E, forward EPS, and historical EPS actual vs estimate with surprise %.
    Data sourced from Yahoo Finance. Works best for US and dual-listed stocks.
    See also: run_fundamental_analysis for ratios, run_all_agents for AI analysis.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, KSPI).
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        from fin_toolkit.providers.yahoo import YahooFinanceProvider

        yahoo = YahooFinanceProvider()
        result = await yahoo.get_analyst_estimates(ticker)
        return serialize(result.model_dump(), format)
    except FinToolkitError as exc:
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in get_analyst_estimates")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def run_risk_analysis(
    tickers: list[str],
    period: str = "1y",
    format: str = "toon",
) -> str:
    """Compute volatility, Value at Risk, and correlation for one or more tickers.

    Returns per-ticker volatility (30d/90d/252d), VaR (95%/99%), pairwise correlations.
    See also: run_portfolio_analysis for position sizing, deep_dive for full analysis.

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
        return _error_response(exc)
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
    """Search financial news and articles via DuckDuckGo or configured providers.

    Works out of the box (no API key). See also: deep_dive (includes news per ticker).

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
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in search_news")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def run_agent(
    ticker: str,
    agent: str = "elvis_marlamov",
    format: str = "toon",
) -> str:
    """Run a single AI analysis agent on a ticker.

    Available agents: elvis_marlamov, warren_buffett, ben_graham,
    charlie_munger, cathie_wood, peter_lynch.
    See also: run_all_agents for consensus from all agents at once.

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
        return _error_response(exc)
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


async def _fetch_analyst_estimates(ticker: str) -> Any:
    """Fetch analyst estimates from Yahoo. Returns AnalystEstimates or None on failure."""
    try:
        from fin_toolkit.providers.yahoo import YahooFinanceProvider

        yahoo = YahooFinanceProvider()
        return await yahoo.get_analyst_estimates(ticker)
    except Exception:
        return None


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
async def run_all_agents(
    ticker: str, format: str = "toon", ctx: Context | None = None,
) -> str:
    """START HERE: get consensus from 6 AI investment analyst agents.

    Runs elvis_marlamov, warren_buffett, ben_graham, charlie_munger,
    cathie_wood, peter_lynch concurrently and computes consensus score/signal.
    See also: run_agent for a single agent, run_recommendation for sizing.

    Args:
        ticker: Stock ticker symbol.
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        if ctx:
            await ctx.report_progress(0, 100, f"Running 6 agents for {ticker}...")
        consensus = await _run_consensus(ticker)
        if ctx:
            await ctx.report_progress(100, 100, "Done")
        if not consensus.agent_results:
            return _error_response(
                "All agents failed: "
                + "; ".join(f"{k}: {v}" for k, v in consensus.agent_errors.items())
            )
        return serialize(consensus.model_dump(), format)
    except FinToolkitError as exc:
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in run_all_agents")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def run_recommendation(
    ticker: str, period: str = "1y", format: str = "toon",
    ctx: Context | None = None,
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
        if ctx:
            await ctx.report_progress(0, 100, f"Recommendation for {ticker}...")
        start, end = _period_to_dates(period)
        result, _ = await _run_single_recommendation(ticker, start, end)
        if ctx:
            await ctx.report_progress(100, 100, "Done")
        return serialize(result.model_dump(), format)
    except FinToolkitError as exc:
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in run_recommendation")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def run_portfolio_analysis(
    tickers: list[str], period: str = "1y", format: str = "toon",
    ctx: Context | None = None,
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

        if ctx:
            await ctx.report_progress(0, 100, f"Analyzing {len(tickers)} tickers...")
        start, end = _period_to_dates(period)
        tasks = [_run_single_recommendation(t, start, end) for t in tickers]
        results_raw = await asyncio.gather(*tasks, return_exceptions=True)
        if ctx:
            await ctx.report_progress(80, 100, "Computing correlations...")

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
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in run_portfolio_analysis")
        return _error_response(f"Internal error: {exc}")


# ---------------------------------------------------------------------------
# Investment Idea / Screening / Report tools
# ---------------------------------------------------------------------------


@mcp.tool
async def screen_stocks(
    tickers: list[str] | None = None,
    market: str | None = None,
    top_n: int = 10,
    filters: dict[str, str] | None = None,
    format: str = "toon",
    ctx: Context | None = None,
) -> str:
    """START HERE: find undervalued stocks in a market or custom list.

    Provide either an explicit list of tickers or a market name to auto-fetch.
    Scoring uses P/E, P/B, EV/EBITDA, FCF yield, D/E, dividend yield, ROE.

    Note: MOEX ISS only provides prices and market cap — no P/E, P/B, ROE.
    Russian tickers screened via MOEX will score 0. Use Yahoo with ".ME" suffix
    (e.g. "SBER.ME") for fundamental metrics, or parse_report for IFRS data.

    Args:
        tickers: Explicit list of ticker symbols to screen.
        market: Market to auto-fetch tickers ("moex" or "kase"). MOEX auto-fetches
            all TQBR tickers but metrics will be limited (prices/market cap only).
        top_n: How many top candidates to run full consensus on.
        filters: Optional metric filters, e.g. {"pe_ratio": "<15", "roe": ">0.10"}.
            Supported operators: <, >, <=, >=, =, min..max (range).
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        assert _provider_router is not None

        from fin_toolkit.analysis.screening import (
            compute_quick_score,
            matches_filters,
        )

        # Resolve ticker list
        ticker_list = tickers or []
        if not ticker_list and market:
            if ctx:
                await ctx.report_progress(0, 100, f"Fetching {market} tickers...")
            ticker_list = await _resolve_market_tickers(market)
        if not ticker_list:
            return _error_response("Provide tickers or market name")

        active_filters = filters or {}
        total = len(ticker_list)

        # Stage 1: quick score + filter (concurrent fetch)
        import asyncio

        scored: list[tuple[str, float, dict[str, float | None]]] = []
        warnings: list[str] = []
        sem = asyncio.Semaphore(10)
        scored_count = 0

        async def _score_one(t: str) -> tuple[str, float, dict[str, float | None]] | None:
            nonlocal scored_count
            async with sem:
                try:
                    metrics = await _provider_router.get_metrics(t)
                    if active_filters and not matches_filters(metrics, active_filters):
                        return None
                    qs = compute_quick_score(metrics)
                    key_m: dict[str, float | None] = {
                        "pe_ratio": metrics.pe_ratio,
                        "pb_ratio": metrics.pb_ratio,
                        "ev_ebitda": metrics.ev_ebitda,
                        "dividend_yield": metrics.dividend_yield,
                        "roe": metrics.roe,
                    }
                    return (t, qs, key_m)
                except Exception as exc:
                    warnings.append(f"{t}: {exc}")
                    return None
                finally:
                    scored_count += 1
                    if ctx and scored_count % 10 == 0:
                        pct = int(10 + 60 * scored_count / total)
                        await ctx.report_progress(pct, 100, f"Scoring {scored_count}/{total}...")

        if ctx:
            await ctx.report_progress(10, 100, f"Scoring {total} tickers...")
        results = await asyncio.gather(*[_score_one(t) for t in ticker_list])
        for r in results:
            if r is not None:
                scored.append(r)

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_n]

        # Stage 2: consensus for top-N (concurrent)
        if ctx:
            top_tickers = ", ".join(t for t, _, _ in top)
            await ctx.report_progress(70, 100, f"Consensus for {len(top)}: {top_tickers}")

        async def _consensus_one(
            t: str, qs: float, key_m: dict[str, float | None],
        ) -> ScreeningCandidate:
            cs_score: float | None = None
            cs_signal: str | None = None
            try:
                consensus = await _run_consensus(t)
                cs_score = consensus.consensus_score
                cs_signal = consensus.consensus_signal
            except Exception as exc:
                warnings.append(f"{t} consensus: {exc}")
            return ScreeningCandidate(
                ticker=t,
                quick_score=qs,
                consensus_score=cs_score,
                consensus_signal=cs_signal,
                key_metrics=key_m,
            )

        candidates = list(await asyncio.gather(
            *[_consensus_one(t, qs, km) for t, qs, km in top],
        ))

        if ctx:
            await ctx.report_progress(100, 100, "Done")

        result = ScreeningResult(
            market=market,
            total_scanned=len(ticker_list),
            candidates=candidates,
            filters_applied=active_filters or None,
            warnings=warnings,
        )
        return serialize(result.model_dump(), format)
    except FinToolkitError as exc:
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in screen_stocks")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def generate_investment_idea(
    ticker: str,
    period: str = "2y",
    format: str = "html",
    ctx: Context | None = None,
) -> str:
    """START HERE: full investment report with charts, scenarios, and catalysts.

    Combines consensus from all agents, fundamental/technical/risk analysis,
    FCF waterfall, scenario valuations, catalysts, and risks into a single report.
    Default output is an interactive HTML file with Plotly charts.
    See also: deep_dive for quick multi-ticker analysis, compare_stocks for side-by-side.

    Best results for US tickers (full fundamentals via Yahoo/EDGAR).
    For Russian tickers: use parse_report first to load IFRS data, then
    generate the idea. Without parsed reports, FCF/scenarios will be empty.

    Args:
        ticker: Stock ticker symbol (e.g. AAPL, INTC, SBER.ME).
        period: Time period for price data (1m, 3m, 6m, 1y, 2y, 5y).
        format: Output format - "html" (default, opens in browser), "toon", or "json".
    """
    try:
        assert _provider_router is not None
        assert _technical_analyzer is not None
        assert _fundamental_analyzer is not None

        start, end = _period_to_dates(period)

        # Step 1: parallel data fetch
        if ctx:
            await ctx.report_progress(0, 100, f"Fetching data for {ticker}...")
        consensus_task = _run_consensus(ticker)
        financials_task = _provider_router.get_financials(ticker)
        metrics_task = _provider_router.get_metrics(ticker)
        prices_task = _provider_router.get_prices(ticker, start, end)
        estimates_task = _fetch_analyst_estimates(ticker)

        results = await asyncio.gather(
            consensus_task, financials_task, metrics_task, prices_task,
            estimates_task,
            return_exceptions=True,
        )
        if ctx:
            await ctx.report_progress(50, 100, "Building scenarios & report...")

        consensus = _unwrap(results[0], "consensus")
        financials = _unwrap(results[1], "financials")
        metrics = _unwrap(results[2], "metrics")
        price_data = _unwrap(results[3], "prices")
        analyst_est = _unwrap(results[4], "analyst_estimates")

        idea_warnings: list[str] = []

        if isinstance(consensus, str):
            idea_warnings.append(consensus)
            from fin_toolkit.analysis.portfolio import compute_consensus
            consensus = compute_consensus({}, {"_": consensus})
        if isinstance(financials, str):
            idea_warnings.append(financials)
            from fin_toolkit.models.financial import FinancialStatements
            financials = FinancialStatements(
                ticker=ticker, income_statement=None,
                balance_sheet=None, cash_flow=None,
            )
        if isinstance(metrics, str):
            idea_warnings.append(metrics)
            from fin_toolkit.models.financial import KeyMetrics
            metrics = KeyMetrics(
                ticker=ticker, pe_ratio=None, pb_ratio=None,
                market_cap=None, dividend_yield=None,
                roe=None, roa=None, debt_to_equity=None,
            )
        if isinstance(price_data, str):
            idea_warnings.append(price_data)
            price_data = PriceData(ticker=ticker, period=period, prices=[])

        from fin_toolkit.models.financial import AnalystEstimates

        analyst_estimates: AnalystEstimates | None = None
        if isinstance(analyst_est, str):
            idea_warnings.append(analyst_est)
        elif isinstance(analyst_est, AnalystEstimates):
            analyst_estimates = analyst_est

        # Step 2: search for catalysts/risks
        search_results_catalysts: list[Any] = []
        search_results_risks: list[Any] = []
        year = datetime.now().year
        if _search_router is not None:
            try:
                cat_task = _search_router.search(
                    f"{ticker} stock news {year}",
                    max_results=10,
                )
                risk_task = _search_router.search(
                    f"{ticker} risk lawsuit regulation {year}",
                    max_results=5,
                )
                cat_r, risk_r = await asyncio.gather(cat_task, risk_task, return_exceptions=True)
                if not isinstance(cat_r, BaseException):
                    search_results_catalysts = cat_r
                if not isinstance(risk_r, BaseException):
                    search_results_risks = risk_r
            except Exception:
                pass

        # Step 3: analysis
        from fin_toolkit.analysis.idea import (
            classify_catalysts,
            compute_cagr,
            compute_fcf_waterfall,
            compute_scenarios,
            detect_risks,
        )

        # Technical & risk
        technical = _technical_analyzer.analyze(price_data) if price_data.prices else (
            _empty_technical()
        )
        risk = _compute_risk(price_data) if price_data.prices else _empty_risk()

        # Fundamental
        sector = _detect_sector(ticker)
        fund_result = _fundamental_analyzer.analyze(financials, metrics, sector=sector)

        # CAGR from history
        revenue_cagr: float | None = None
        ebitda_cagr: float | None = None
        if financials.income_history:
            rev_values = [
                float(p.get("revenue", 0)) for p in reversed(financials.income_history)
                if p.get("revenue") is not None
            ]
            ebitda_values = [
                float(p.get("ebitda", 0)) for p in reversed(financials.income_history)
                if p.get("ebitda") is not None
            ]
            if len(rev_values) >= 2:
                revenue_cagr = compute_cagr(rev_values, len(rev_values) - 1)
            if len(ebitda_values) >= 2:
                ebitda_cagr = compute_cagr(ebitda_values, len(ebitda_values) - 1)

        # FCF waterfall
        fcf_waterfall = compute_fcf_waterfall(financials, metrics)

        # Scenarios
        inc = financials.income_statement or {}
        bs = financials.balance_sheet or {}
        ebitda_val = _safe_float(inc.get("ebitda"))
        total_debt = _safe_float(bs.get("total_debt"))
        cash = _safe_float(bs.get("cash_and_equivalents"))
        net_debt: float | None = None
        if total_debt is not None:
            net_debt = total_debt - (cash or 0)
        elif metrics.enterprise_value and metrics.market_cap:
            net_debt = metrics.enterprise_value - metrics.market_cap

        scenarios = compute_scenarios(
            current_price=metrics.current_price or 0,
            ebitda=ebitda_val,
            ebitda_cagr=ebitda_cagr,
            ev_ebitda_multiple=metrics.ev_ebitda,
            ev=metrics.enterprise_value,
            net_debt=net_debt,
            shares=metrics.shares_outstanding,
        )

        # Catalysts & risks
        catalysts = classify_catalysts(search_results_catalysts)
        risks = detect_risks(fund_result.model_dump(), risk, search_results_risks)

        # Price history for chart
        price_history = [
            {"date": p.date, "open": p.open, "high": p.high,
             "low": p.low, "close": p.close, "volume": p.volume}
            for p in price_data.prices
        ]

        idea = InvestmentIdeaResult(
            ticker=ticker,
            current_price=metrics.current_price,
            consensus=consensus,
            fundamentals=fund_result,
            analyst_estimates=analyst_estimates,
            catalysts=catalysts,
            revenue_cagr_3y=revenue_cagr,
            ebitda_cagr_3y=ebitda_cagr,
            fcf_waterfall=fcf_waterfall,
            scenarios=scenarios,
            risks=risks,
            technical=technical,
            risk=risk,
            price_history=price_history,
            warnings=idea_warnings,
        )

        # Step 4: output
        if format == "html":
            return _render_html_idea(idea)
        return serialize(idea.model_dump(), format)
    except FinToolkitError as exc:
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in generate_investment_idea")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def parse_report(
    source: str,
    ticker: str,
    format: str = "toon",
) -> str:
    """Parse a financial report PDF and extract structured data.

    Extracts income statement, balance sheet, and cash flow from PDF.
    Works with English and Russian (IFRS/МСФО) reports.

    Args:
        source: URL or local path to PDF report.
        ticker: Ticker symbol to associate with the extracted data.
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        from fin_toolkit.providers.pdf_report import parse_financial_report

        result = await parse_financial_report(source, ticker)
        return serialize(result.model_dump(), format)
    except FinToolkitError as exc:
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in parse_report")
        return _error_response(f"Internal error: {exc}")


# ---------------------------------------------------------------------------
# Helpers for investment idea / screening
# ---------------------------------------------------------------------------


def _unwrap(result: Any, label: str) -> Any:
    """Unwrap asyncio.gather result: return value or error string."""
    if isinstance(result, BaseException):
        return f"{label}: {result}"
    return result


async def _resolve_market_tickers(market: str) -> list[str]:
    """Resolve market name to a list of tickers."""
    if market == "moex":
        from fin_toolkit.providers.moex import MOEXProvider
        moex = MOEXProvider()
        return await moex.list_tickers()
    if market == "kase":
        kase_prov = _provider_router._providers.get("kase")  # type: ignore[union-attr]
        if kase_prov and hasattr(kase_prov, "list_tickers"):
            result: list[str] = await kase_prov.list_tickers()
            return result
        return []
    return []


def _render_html_idea(idea: InvestmentIdeaResult) -> str:
    """Render idea to HTML, save to /tmp, open in browser, return summary."""
    import webbrowser
    from pathlib import Path

    from fin_toolkit.report.html_report import render_investment_idea_html

    html = render_investment_idea_html(idea)
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(f"/tmp/fin_toolkit_{idea.ticker}_{date_str}.html")
    path.write_text(html)
    webbrowser.open(f"file://{path}")

    # Return summary
    from fin_toolkit.report.i18n import currency_symbol

    sym = currency_symbol(idea.ticker)
    scenarios_summary = ""
    for s in idea.scenarios:
        if s.target_price is not None:
            scenarios_summary += f"  {s.label}: {sym}{s.target_price:,.2f}"
            if s.upside_pct is not None:
                scenarios_summary += f" ({s.upside_pct:+.1f}%)"
            scenarios_summary += "\n"

    price_line = (
        f"Price: {sym}{idea.current_price:,.2f}\n" if idea.current_price else ""
    )
    analyst_line = ""
    if idea.analyst_estimates:
        ae = idea.analyst_estimates
        parts = []
        if ae.recommendation:
            parts.append(f"Rating: {ae.recommendation}")
        if ae.num_analysts:
            parts.append(f"({ae.num_analysts} analysts)")
        if ae.target_mean:
            parts.append(f"Target: {sym}{ae.target_mean:,.2f}")
        if ae.target_low and ae.target_high:
            parts.append(f"[{sym}{ae.target_low:,.2f}–{sym}{ae.target_high:,.2f}]")
        if ae.forward_pe:
            parts.append(f"Fwd P/E: {ae.forward_pe:.1f}")
        if parts:
            analyst_line = "Analysts: " + " ".join(parts) + "\n"

    return (
        f"Investment Idea: {idea.ticker}\n"
        f"Signal: {idea.consensus.consensus_signal} "
        f"({idea.consensus.consensus_score:.0f}/100)\n"
        f"{price_line}"
        f"{analyst_line}"
        f"Scenarios:\n{scenarios_summary}"
        f"Report saved: {path}\n"
        f"Opened in browser."
    )


# ---------------------------------------------------------------------------
# Deep Dive / Compare / Watchlist tools
# ---------------------------------------------------------------------------


@mcp.tool
async def deep_dive(
    tickers: list[str],
    period: str = "1y",
    format: str = "toon",
    ctx: Context | None = None,
) -> str:
    """START HERE: comprehensive analysis for 1-10 tickers at once.

    For each ticker: fetches prices, financials, metrics, runs consensus and
    news search concurrently. Partial failures produce warnings, never kill batch.
    See also: compare_stocks for side-by-side metrics, run_portfolio_analysis for sizing.

    Args:
        tickers: List of 1-10 stock ticker symbols.
        period: Time period for price data.
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        assert _provider_router is not None
        assert _technical_analyzer is not None
        assert _fundamental_analyzer is not None

        if len(tickers) > 10:
            return _error_response("Deep dive supports at most 10 tickers")

        if ctx:
            await ctx.report_progress(
                0, 100, f"Deep dive: {', '.join(tickers)}",
            )

        start, end = _period_to_dates(period)
        items: dict[str, DeepDiveItem] = {}
        batch_warnings: list[str] = []

        async def _dive_one(ticker: str) -> tuple[str, DeepDiveItem | None, str | None]:
            w: list[str] = []
            try:
                item = await _deep_dive_single(ticker, start, end, w)
                return (ticker, item, None)
            except Exception as exc:
                return (ticker, None, f"{ticker}: {exc}")

        dive_results = await asyncio.gather(*[_dive_one(t) for t in tickers])
        for ticker, item, err in dive_results:
            if item is not None:
                items[ticker] = item
            if err:
                batch_warnings.append(err)

        if ctx:
            await ctx.report_progress(100, 100, "Done")

        if not items:
            return _error_response(
                "All tickers failed: " + "; ".join(batch_warnings)
            )

        result = DeepDiveResult(items=items, warnings=batch_warnings)
        return serialize(result.model_dump(), format)
    except FinToolkitError as exc:
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in deep_dive")
        return _error_response(f"Internal error: {exc}")


async def _deep_dive_single(
    ticker: str, start: str, end: str, warnings: list[str],
) -> DeepDiveItem:
    """Deep dive for a single ticker."""
    assert _provider_router is not None
    assert _technical_analyzer is not None
    assert _fundamental_analyzer is not None

    # Concurrent fetch
    tasks: dict[str, Any] = {
        "prices": _provider_router.get_prices(ticker, start, end),
        "financials": _provider_router.get_financials(ticker),
        "metrics": _provider_router.get_metrics(ticker),
        "consensus": _run_consensus(ticker),
        "estimates": _fetch_analyst_estimates(ticker),
    }
    # Add news search if available
    if _search_router is not None:
        tasks["news"] = _search_router.search(
            f"{ticker} stock latest news {datetime.now().year}",
            max_results=5,
        )

    results_raw = await asyncio.gather(*tasks.values(), return_exceptions=True)
    fetched: dict[str, Any] = {}
    for key, result in zip(tasks.keys(), results_raw, strict=True):
        if isinstance(result, BaseException):
            warnings.append(f"{ticker} {key}: {result}")
            fetched[key] = None
        else:
            fetched[key] = result

    # Derive technical/risk from prices
    technical = None
    risk_result = None
    if fetched.get("prices") and fetched["prices"].prices:
        technical = _technical_analyzer.analyze(fetched["prices"])
        risk_result = _compute_risk(fetched["prices"])

    # Fundamental from financials+metrics
    fundamental = None
    if fetched.get("financials") and fetched.get("metrics"):
        fundamental = _fundamental_analyzer.analyze(
            fetched["financials"], fetched["metrics"],
        )

    news_items = fetched.get("news") or []

    return DeepDiveItem(
        ticker=ticker,
        fundamentals=fundamental,
        technical=technical,
        risk=risk_result,
        consensus=fetched.get("consensus"),
        analyst_estimates=fetched.get("estimates"),
        news=news_items,
        warnings=warnings,
    )


@mcp.tool
async def compare_stocks(
    tickers: list[str],
    metrics: list[str] | None = None,
    format: str = "toon",
    ctx: Context | None = None,
) -> str:
    """Compare 2-10 stocks side by side on key metrics.

    Builds a comparison matrix {metric: {ticker: value}} with metrics, risk, consensus.
    See also: deep_dive for full per-ticker analysis, run_portfolio_analysis for sizing.

    Args:
        tickers: List of 2-10 stock ticker symbols.
        metrics: Optional list of metrics to compare (default: standard set).
            Available: pe_ratio, pb_ratio, ev_ebitda, fcf_yield, roe, roa,
            debt_to_equity, dividend_yield, market_cap, current_price,
            volatility_30d, consensus_score, consensus_signal.
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        assert _provider_router is not None

        if len(tickers) < 2:
            return _error_response("Comparison requires at least 2 tickers")
        if len(tickers) > 10:
            return _error_response("Comparison supports at most 10 tickers")

        from fin_toolkit.analysis.comparison import build_comparison_matrix

        if ctx:
            await ctx.report_progress(
                0, 100, f"Comparing {', '.join(tickers)}...",
            )

        start, end = _period_to_dates("1y")
        ticker_data: dict[str, ComparisonInput] = {}
        warnings: list[str] = []

        async def _compare_one(ticker: str) -> ComparisonInput:
            km = None
            risk_r = None
            cons = None
            try:
                km = await _provider_router.get_metrics(ticker)
            except Exception as exc:
                warnings.append(f"{ticker} metrics: {exc}")
            try:
                pd = await _provider_router.get_prices(ticker, start, end)
                risk_r = _compute_risk(pd)
            except Exception as exc:
                warnings.append(f"{ticker} risk: {exc}")
            try:
                cons = await _run_consensus(ticker)
            except Exception as exc:
                warnings.append(f"{ticker} consensus: {exc}")
            return ComparisonInput(
                ticker=ticker, key_metrics=km, risk=risk_r, consensus=cons,
            )

        compare_results = await asyncio.gather(
            *[_compare_one(t) for t in tickers],
        )
        for ci in compare_results:
            ticker_data[ci.ticker] = ci

        if ctx:
            await ctx.report_progress(90, 100, "Building matrix...")

        result = build_comparison_matrix(ticker_data, metrics)
        out = result.model_dump()
        out["warnings"] = result.warnings + warnings
        return serialize(out, format)
    except FinToolkitError as exc:
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in compare_stocks")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def manage_watchlist(
    action: str,
    watchlist: str = "default",
    ticker: str | None = None,
    notes: str | None = None,
    format: str = "toon",
) -> str:
    """Manage watchlists: add/remove tickers, list or show watchlists.

    Args:
        action: "add", "remove", "list" (all watchlists), or "show" (one watchlist).
        watchlist: Watchlist name (default: "default").
        ticker: Ticker symbol (required for "add" and "remove").
        notes: Optional notes when adding a ticker.
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        if _watchlist_store is None:
            return _error_response("Watchlist store not initialized")

        from fin_toolkit.analysis.alerts import WatchlistEntry

        if action == "add":
            if not ticker:
                return _error_response("Ticker required for 'add' action")
            entry = WatchlistEntry(
                ticker=ticker,
                added_at=datetime.now().strftime("%Y-%m-%d"),
                notes=notes,
            )
            _watchlist_store.add_ticker(watchlist, entry)
            return serialize(
                {"status": "ok", "action": "added", "ticker": ticker,
                 "watchlist": watchlist}, format,
            )

        if action == "remove":
            if not ticker:
                return _error_response("Ticker required for 'remove' action")
            _watchlist_store.remove_ticker(watchlist, ticker)
            return serialize(
                {"status": "ok", "action": "removed", "ticker": ticker,
                 "watchlist": watchlist}, format,
            )

        if action == "list":
            names = _watchlist_store.list_watchlists()
            infos: list[dict[str, Any]] = []
            for name in names:
                entries = _watchlist_store.get_watchlist(name)
                alert_count = sum(len(e.alerts) for e in entries)
                infos.append(WatchlistInfo(
                    name=name,
                    tickers=[e.ticker for e in entries],
                    alert_count=alert_count,
                ).model_dump())
            return serialize({"watchlists": infos}, format)

        if action == "show":
            entries = _watchlist_store.get_watchlist(watchlist)
            data: list[dict[str, Any]] = []
            for e in entries:
                data.append({
                    "ticker": e.ticker,
                    "added_at": e.added_at,
                    "notes": e.notes,
                    "alert_count": len(e.alerts),
                })
            return serialize(
                {"watchlist": watchlist, "entries": data}, format,
            )

        return _error_response(f"Unknown action: {action}")
    except FinToolkitError as exc:
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in manage_watchlist")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def set_alert(
    watchlist: str,
    ticker: str,
    metric: str,
    operator: str,
    threshold: float,
    label: str | None = None,
    format: str = "toon",
) -> str:
    """Set an alert on a ticker in a watchlist.

    When check_watchlist is called, the alert fires if the condition is met.

    Args:
        watchlist: Watchlist name.
        ticker: Ticker symbol (must already be in the watchlist).
        metric: Metric to monitor (e.g. "pe_ratio", "rsi", "volatility_30d").
        operator: Comparison operator: "<", ">", "<=", ">=", "=".
        threshold: Threshold value for the alert.
        label: Optional human-readable label for the alert.
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        if _watchlist_store is None:
            return _error_response("Watchlist store not initialized")

        from fin_toolkit.analysis.alerts import AlertRule

        rule = AlertRule(
            metric=metric, operator=operator,
            threshold=threshold, label=label,
        )
        _watchlist_store.set_alert(watchlist, ticker, rule)
        return serialize(
            {"status": "ok", "ticker": ticker, "metric": metric,
             "operator": operator, "threshold": threshold}, format,
        )
    except FinToolkitError as exc:
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in set_alert")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def check_watchlist(
    watchlist: str = "default",
    format: str = "toon",
    ctx: Context | None = None,
) -> str:
    """Check a watchlist for triggered alerts.

    Fetches current metrics, risk, and technical data for each ticker
    and evaluates all configured alerts.

    Args:
        watchlist: Watchlist name to check (default: "default").
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        if _watchlist_store is None:
            return _error_response("Watchlist store not initialized")
        assert _provider_router is not None

        from fin_toolkit.analysis.alerts import evaluate_alerts

        entries = _watchlist_store.get_watchlist(watchlist)
        if ctx:
            await ctx.report_progress(
                0, 100,
                f"Checking {len(entries)} tickers in '{watchlist}'...",
            )
        all_triggered: list[Any] = []
        warnings: list[str] = []
        start, end = _period_to_dates("6m")

        async def _check_entry(
            entry: Any,
        ) -> list[dict[str, Any]]:
            km = None
            risk_r = None
            tech = None
            try:
                km = await _provider_router.get_metrics(entry.ticker)
            except Exception as exc:
                warnings.append(f"{entry.ticker} metrics: {exc}")
            try:
                pd = await _provider_router.get_prices(entry.ticker, start, end)
                risk_r = _compute_risk(pd)
                if _technical_analyzer:
                    tech = _technical_analyzer.analyze(pd)
            except Exception as exc:
                warnings.append(f"{entry.ticker} prices: {exc}")
            triggered = evaluate_alerts(entry, km, risk_r, tech)
            return [t.model_dump() for t in triggered]

        entry_results = await asyncio.gather(
            *[_check_entry(e) for e in entries],
        )
        for triggered_list in entry_results:
            all_triggered.extend(triggered_list)

        if ctx:
            await ctx.report_progress(100, 100, "Done")

        result = WatchlistCheckResult(
            watchlist_name=watchlist,
            tickers=[e.ticker for e in entries],
            alerts_triggered=[],  # filled from dicts below
            warnings=warnings,
        )
        # Re-serialize via model_dump then add triggered
        out = result.model_dump()
        out["alerts_triggered"] = all_triggered
        return serialize(out, format)
    except FinToolkitError as exc:
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in check_watchlist")
        return _error_response(f"Internal error: {exc}")


# ---------------------------------------------------------------------------
# Portfolio tools
# ---------------------------------------------------------------------------


@mcp.tool
async def manage_portfolio(
    action: str,
    portfolio: str | None = None,
    ticker: str | None = None,
    shares: float | None = None,
    price: float | None = None,
    fee: float = 0,
    currency: str = "USD",
    date: str | None = None,
    notes: str | None = None,
    format: str = "toon",
) -> str:
    """Manage portfolios: create, delete, buy/sell, list, show positions, history.

    Args:
        action: "create", "delete", "list", "show", "buy", "sell", or "history".
        portfolio: Portfolio name (required for all except "list").
        ticker: Ticker symbol (required for "buy", "sell", "history" with filter).
        shares: Number of shares (required for "buy" and "sell").
        price: Price per share (required for "buy" and "sell").
        fee: Transaction fee (default: 0).
        currency: Base currency for new portfolio (default: "USD").
        date: Transaction date ISO 8601 (default: now).
        notes: Optional notes.
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        if _portfolio_store is None:
            return _error_response("Portfolio store not initialized")

        if action == "create":
            if not portfolio:
                return _error_response("Portfolio name required for 'create'")
            pid = _portfolio_store.create_portfolio(portfolio, currency=currency, notes=notes)
            return serialize(
                {"status": "ok", "action": "created", "portfolio": portfolio, "id": pid},
                format,
            )

        if action == "delete":
            if not portfolio:
                return _error_response("Portfolio name required for 'delete'")
            _portfolio_store.delete_portfolio(portfolio)
            return serialize(
                {"status": "ok", "action": "deleted", "portfolio": portfolio}, format,
            )

        if action == "list":
            portfolios = _portfolio_store.list_portfolios()
            return serialize({"portfolios": portfolios}, format)

        if action in ("buy", "sell"):
            if not portfolio:
                return _error_response("Portfolio name required")
            if not ticker:
                return _error_response("Ticker required for buy/sell")
            if shares is None or shares <= 0:
                return _error_response("Positive shares required for buy/sell")
            if price is None or price <= 0:
                return _error_response("Positive price required for buy/sell")
            tid = _portfolio_store.add_transaction(
                portfolio, ticker, action, shares, price,
                fee=fee, executed_at=date, notes=notes,
            )
            return serialize(
                {"status": "ok", "action": action, "ticker": ticker,
                 "shares": shares, "price": price, "transaction_id": tid},
                format,
            )

        if action == "show":
            if not portfolio:
                return _error_response("Portfolio name required for 'show'")
            assert _provider_router is not None
            positions = _portfolio_store.get_positions(portfolio)

            enriched: list[dict[str, Any]] = []
            total_value = 0.0
            total_invested = 0.0
            warnings: list[str] = []
            start, end = _period_to_dates("1m")

            for pos in positions:
                d = pos.model_dump()
                total_invested += pos.total_invested
                try:
                    pd = await _provider_router.get_prices(pos.ticker, start, end)
                    if pd.prices:
                        cp = pd.prices[-1].close
                        mv = cp * pos.shares
                        pnl = mv - pos.avg_cost * pos.shares
                        d["current_price"] = cp
                        d["market_value"] = round(mv, 2)
                        d["pnl"] = round(pnl, 2)
                        d["pnl_pct"] = round(
                            pnl / (pos.avg_cost * pos.shares) * 100, 2,
                        )
                        total_value += mv
                except Exception as exc:
                    warnings.append(f"{pos.ticker}: {exc}")
                enriched.append(d)

            if total_value > 0:
                for d in enriched:
                    if d.get("market_value") is not None:
                        d["weight"] = round(d["market_value"] / total_value * 100, 2)

            total_pnl = total_value - total_invested if total_value > 0 else None
            total_pnl_pct = (
                round(total_pnl / total_invested * 100, 2)
                if total_pnl is not None and total_invested > 0 else None
            )

            result = {
                "portfolio": portfolio,
                "positions": enriched,
                "total_invested": round(total_invested, 2),
                "total_value": round(total_value, 2) if total_value > 0 else None,
                "total_pnl": round(total_pnl, 2) if total_pnl is not None else None,
                "total_pnl_pct": total_pnl_pct,
                "warnings": warnings,
            }
            return serialize(result, format)

        if action == "history":
            if not portfolio:
                return _error_response("Portfolio name required for 'history'")
            txns = _portfolio_store.get_transactions(portfolio, ticker=ticker)
            return serialize(
                {"portfolio": portfolio, "ticker": ticker,
                 "transactions": [t.model_dump() for t in txns]},
                format,
            )

        return _error_response(f"Unknown action: {action}")
    except FinToolkitError as exc:
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in manage_portfolio")
        return _error_response(f"Internal error: {exc}")


@mcp.tool
async def portfolio_performance(
    portfolio: str,
    period: str = "1m",
    format: str = "toon",
) -> str:
    """Analyze portfolio performance over a time period.

    Computes P&L, returns, and per-ticker breakdown for a given period.

    Args:
        portfolio: Portfolio name.
        period: Time period - "1m", "3m", "6m", "1y", "ytd", "all" (default: "1m").
        format: Response format - "toon" (default, token-efficient) or "json".
    """
    try:
        if _portfolio_store is None:
            return _error_response("Portfolio store not initialized")
        assert _provider_router is not None

        from fin_toolkit.models.portfolio import PortfolioPerformance

        if period == "ytd":
            start_date = f"{datetime.now().year}-01-01"
            end_date = datetime.now().strftime("%Y-%m-%d")
        elif period == "all":
            start_date = "2000-01-01"
            end_date = datetime.now().strftime("%Y-%m-%d")
        else:
            start_date, end_date = _period_to_dates(period)

        all_txns = _portfolio_store.get_transactions(portfolio)
        period_txns = [
            t for t in all_txns if start_date <= t.executed_at[:10] <= end_date
        ]

        positions = _portfolio_store.get_positions(portfolio)
        warnings: list[str] = []

        current_prices: dict[str, float] = {}
        start_p, end_p = _period_to_dates(period)
        for pos in positions:
            try:
                pd = await _provider_router.get_prices(pos.ticker, start_p, end_p)
                if pd.prices:
                    current_prices[pos.ticker] = pd.prices[-1].close
            except Exception as exc:
                warnings.append(f"{pos.ticker}: {exc}")

        end_value = sum(
            current_prices.get(p.ticker, 0) * p.shares for p in positions
        )

        # Start positions = end positions reversed by period transactions
        start_positions: dict[str, float] = {p.ticker: p.shares for p in positions}
        for t in period_txns:
            if t.action == "buy":
                start_positions[t.ticker] = start_positions.get(t.ticker, 0) - t.shares
            else:
                start_positions[t.ticker] = start_positions.get(t.ticker, 0) + t.shares

        start_value = 0.0
        start_prices: dict[str, float] = {}
        for tkr, sh in start_positions.items():
            if sh <= 1e-9:
                continue
            try:
                pd = await _provider_router.get_prices(tkr, start_p, end_p)
                if pd.prices:
                    start_prices[tkr] = pd.prices[0].close
                    start_value += pd.prices[0].close * sh
            except Exception as exc:
                warnings.append(f"{tkr} start price: {exc}")

        net_invested = 0.0
        for t in period_txns:
            if t.action == "buy":
                net_invested += t.shares * t.price + t.fee
            else:
                net_invested -= t.shares * t.price - t.fee

        pnl = end_value - start_value - net_invested
        base = start_value + net_invested if (start_value + net_invested) > 0 else 1
        pnl_pct = round(pnl / base * 100, 2)

        ticker_returns: dict[str, float] = {}
        for pos in positions:
            cp = current_prices.get(pos.ticker)
            sp = start_prices.get(pos.ticker)
            if cp and sp and sp > 0:
                ticker_returns[pos.ticker] = round((cp - sp) / sp * 100, 2)

        perf = PortfolioPerformance(
            name=portfolio,
            period=period,
            start_value=round(start_value, 2),
            end_value=round(end_value, 2),
            pnl=round(pnl, 2),
            pnl_pct=pnl_pct,
            transactions_count=len(period_txns),
            ticker_returns=ticker_returns,
        )

        out = perf.model_dump()
        out["warnings"] = warnings
        return serialize(out, format)
    except FinToolkitError as exc:
        return _error_response(exc)
    except Exception as exc:
        logger.exception("Unexpected error in portfolio_performance")
        return _error_response(f"Internal error: {exc}")


# ---------------------------------------------------------------------------
# Helpers for investment idea / screening
# ---------------------------------------------------------------------------


def _empty_technical() -> Any:
    """Return an empty TechnicalResult for when no price data is available."""
    from fin_toolkit.models.results import TechnicalResult
    return TechnicalResult(
        rsi=None, ema_20=None, ema_50=None, ema_200=None,
        bb_upper=None, bb_middle=None, bb_lower=None,
        macd_line=None, macd_signal=None, macd_histogram=None,
        signals={}, overall_bias="Neutral", warnings=["No price data"],
    )


def _empty_risk() -> RiskResult:
    """Return an empty RiskResult for when no price data is available."""
    return RiskResult(
        volatility_30d=None, volatility_90d=None, volatility_252d=None,
        var_95=None, var_99=None, warnings=["No price data"],
    )


def _safe_float(val: object) -> float | None:
    """Safely convert to float or return None."""
    if val is None:
        return None
    try:
        return float(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
