# Architecture

## Project Structure

```
fin-toolkit/
  providers/          # Data & search sources (protocols + implementations)
    protocol.py       #   DataProvider protocol (get_prices, get_financials, get_metrics)
    search_protocol.py#   SearchProvider protocol (search)
    router.py         #   ProviderRouter: market mapping + fallback chain
    search_router.py  #   SearchRouter: fallback chain for search
    yahoo.py          #   Yahoo Finance (free, no API key)
    kase.py           #   KASE JSON API + Yahoo multi-suffix + dynamic tickers
    moex.py           #   MOEX via aiomoex
    smartlab.py       #   SmartLab fundamentals + IFRS (scraper)
    stockanalysis.py  #   StockAnalysis.com KASE ratios (scraper, KZT-consistent)
    financialdatasets.py  # Financial Datasets REST API
    edgar.py          #   SEC EDGAR filings via edgartools
    pdf_report.py     #   PDF report parser (IFRS/MSFO)
    duckduckgo.py     #   DuckDuckGo (free, no API key)
    searxng.py        #   SearXNG (self-hosted search)
    google.py         #   Google Search via Gemini API grounding
    perplexity.py     #   Perplexity Sonar API
    tavily.py         #   Tavily Search API
    brave.py          #   Brave Search API
    serper.py         #   Serper (Google Search) API
    exa.py            #   Exa AI semantic search
  analysis/           # Analysis engines
    technical.py      #   RSI, EMA, Bollinger Bands, MACD
    fundamental.py    #   Profitability, valuation, stability ratios
    risk.py           #   Volatility, VaR, correlation
    portfolio.py      #   Consensus, position sizing, stop-loss
    screening.py      #   Quick valuation scoring + custom filters
    idea.py           #   Investment idea: scenarios, catalysts, FCF
    comparison.py     #   Stock comparison matrix
    alerts.py         #   Alert evaluation + AlertRule/WatchlistEntry
  agents/             # Analysis agents (protocol + implementations)
    protocol.py       #   AnalysisAgent protocol (analyze -> AgentResult)
    elvis.py          #   Elvis Marlamov
    buffett.py        #   Warren Buffett
    graham.py         #   Ben Graham
    munger.py         #   Charlie Munger
    wood.py           #   Cathie Wood
    lynch.py          #   Peter Lynch
    registry.py       #   AgentRegistry: loads agents from config
  models/             # Pydantic models
    price_data.py     #   PricePoint, PriceData
    financial.py      #   FinancialStatements, KeyMetrics
    portfolio.py      #   Transaction, Position, PortfolioSummary
    results.py        #   TechnicalResult, FundamentalResult, RiskResult, AgentResult
  config/             # Configuration
    models.py         #   ToolkitConfig, DataConfig, SearchConfig
    loader.py         #   YAML + env + defaults loader
  mcp_server/         # FastMCP server
    server.py         #   MCP tools (20 tools)
    serialize.py      #   TOON/JSON serialization
  report/             # Report generation
    html_report.py    #   Interactive HTML reports with Plotly charts
    i18n.py           #   Bilingual translations, currency helpers
    narrative.py      #   Template-based thesis/FCF/target narratives
  watchlist.py        # YAML-backed persistent watchlist store
  portfolio_store.py  # SQLite-backed portfolio store
  cli.py              # CLI entry point (serve, setup, status)
```

## Protocol-First Design

All major boundaries are `typing.Protocol` classes with `@runtime_checkable`. New providers and agents implement the protocol — no base class inheritance needed.

```python
@runtime_checkable
class DataProvider(Protocol):
    async def get_prices(self, ticker: str, start: date, end: date) -> PriceData: ...
    async def get_financials(self, ticker: str) -> FinancialStatements | None: ...
    async def get_metrics(self, ticker: str) -> KeyMetrics | None: ...
```

```python
@runtime_checkable
class AnalysisAgent(Protocol):
    name: str
    async def analyze(
        self, ticker: str, fundamentals: FundamentalResult,
        risk: RiskResult, prices: PriceData
    ) -> AgentResult: ...
```

## Routing & Fallback

```
Request → ProviderRouter
           │
           ├── Explicit provider? → use it
           ├── Static market mapping? → use configured provider
           ├── Dynamic tickers? → check providers with list_tickers()
           ├── Primary provider → try first
           └── Fallback chain → iterate until success
                                └── AllProvidersFailedError
```

Dynamic tickers are fetched lazily on first request (e.g., KASE's 87 actively traded shares) and cached. This allows new listings to be discovered automatically without config changes.

Same pattern for `SearchRouter` with the search fallback chain.

## MCP Server Wiring

`mcp_server/server.py` uses module-level globals initialized by `init_server()`. The CLI builds all dependencies and passes them before calling `server.run()`.

```
cli.py
  └── builds providers, analyzers, registry, stores
       └── init_server(router, search, technical, fundamental, risk, registry, watchlist, portfolio)
            └── server.run()
```

## Exception Hierarchy

All exceptions inherit from `FinToolkitError`:

```
FinToolkitError
  ├── TickerNotFoundError
  ├── ProviderUnavailableError
  ├── AllProvidersFailedError
  ├── InsufficientDataError
  ├── AgentNotFoundError
  ├── InvalidFilterError
  ├── WatchlistError
  └── PortfolioError
```

Each exception has a `.hint` property with actionable guidance, used in MCP error responses.
