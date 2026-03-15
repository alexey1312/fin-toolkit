# fin-toolkit

Protocol-first financial analysis toolkit with MCP server for Claude Code.

## Quick Start

```bash
# Install
mise install && uv sync

# Register MCP server for Claude Code
fin-toolkit setup            # local (.mcp.json)
fin-toolkit setup --global   # global (~/.claude.json)

# Check status
fin-toolkit status
```

All 6 MCP tools work out of the box — no API keys required (Yahoo Finance + DuckDuckGo).

## How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Claude Code                                 │
│                                                                     │
│  "Analyze AAPL"  "Compare AAPL vs MSFT risk"  "Search AAPL news"  │
└────────────────────────────┬────────────────────────────────────────┘
                             │ MCP Protocol
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    fin-toolkit MCP Server                            │
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────┐ │
│  │get_stock_data│ │run_technical │ │run_fundamental│ │run_risk   │ │
│  │              │ │_analysis     │ │_analysis      │ │_analysis  │ │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └─────┬─────┘ │
│         │                │                │               │        │
│  ┌──────┴────────────────┴────────────────┴───────────────┘        │
│  │                                                                  │
│  │  ┌───────────┐ ┌───────────────┐                                │
│  │  │search_news│ │  run_agent    │                                │
│  │  └─────┬─────┘ └──────┬───────┘                                │
│  │        │              │                                          │
│  ▼        ▼              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Routing Layer                              │   │
│  │  ProviderRouter          SearchRouter        AgentRegistry   │   │
│  │  (market map → primary   (DuckDuckGo →       (6 agents)      │   │
│  │   → fallbacks)            SearXNG → ...)                     │   │
│  └──────────┬───────────────────┬──────────────────┬────────────┘   │
└─────────────┼───────────────────┼──────────────────┼────────────────┘
              ▼                   ▼                   ▼
┌──────────────────┐ ┌─────────────────────┐ ┌────────────────────────┐
│  Data Providers  │ │  Search Providers   │ │   Analysis Agents      │
│                  │ │                     │ │                        │
│  Yahoo Finance   │ │  DuckDuckGo (free)  │ │  Elvis Marlamov        │
│  KASE (scraper)  │ │  SearXNG            │ │  Warren Buffett        │
│                  │ │  Perplexity         │ │  Ben Graham            │
│                  │ │  Tavily             │ │  Charlie Munger        │
│                  │ │  Brave              │ │  Cathie Wood           │
│                  │ │  Serper             │ │  Peter Lynch           │
│                  │ │  Exa                │ │                        │
└──────────────────┘ └─────────────────────┘ └────────────────────────┘
```

## MCP Tools

### get_stock_data

Fetch historical OHLCV price data.

```
ticker: "AAPL"
period: "1y"          # 1m, 3m, 6m, 1y, 2y, 5y
provider: null        # optional: force a specific provider
```

### run_technical_analysis

Compute technical indicators and derive trading signals.

```
ticker: "AAPL"
```

Returns: RSI, EMA (20/50/200), Bollinger Bands, MACD, signals, overall bias.

### run_fundamental_analysis

Compute profitability, valuation, and stability ratios.

```
ticker: "AAPL"
sector: null          # optional: auto-detected if omitted
```

Returns: ROE, ROA, ROIC, margins, P/E, P/B, EV/EBITDA, FCF yield, D/E, current ratio, sector comparison.

### run_risk_analysis

Compute volatility, Value at Risk, and correlation matrix for one or more tickers.

```
tickers: ["AAPL", "MSFT"]
period: "1y"
```

Returns: per-ticker volatility (30d/90d/252d), VaR (95%/99%), pairwise correlation matrix.

### search_news

Search financial news and articles. Works out of the box via DuckDuckGo (no API key).

```
query: "AAPL earnings Q1 2026"
max_results: 10
```

### run_agent

Run an AI analysis agent on a ticker.

```
ticker: "AAPL"
agent: "elvis_marlamov"   # or warren_buffett, ben_graham, charlie_munger, cathie_wood, peter_lynch
```

Returns: signal (Bullish/Neutral/Bearish), score (0-100), confidence (0.0-1.0), rationale, breakdown.

## Analysis Agents

| Agent | Style | Scoring |
|-------|-------|---------|
| `elvis_marlamov` | Fundamentals + sentiment | quality / stability / valuation / sentiment |
| `warren_buffett` | Value investing | margin of safety / durable advantage / management |
| `ben_graham` | Deep value | net-net value / earnings stability / financial strength |
| `charlie_munger` | Wonderful business at fair price | business quality / fair price / financial fortress |
| `cathie_wood` | Innovation & growth | growth signals / innovation premium / market position |
| `peter_lynch` | GARP | PEG value / earnings quality / common sense |

## Search Providers

Fallback chain (first available wins):

| # | Provider | API Key | Env Var | Notes |
|---|----------|---------|---------|-------|
| 1 | DuckDuckGo | No | — | Always available, default |
| 2 | SearXNG | No | — | Self-hosted (`docker run -p 8888:8080 searxng/searxng`) |
| 3 | Perplexity | Yes | `PERPLEXITY_API_KEY` | AI-powered search with citations |
| 4 | Tavily | Yes | `TAVILY_API_KEY` | Optimized for AI agents |
| 5 | Brave | Yes | `BRAVE_API_KEY` | Web search |
| 6 | Serper | Yes | `SERPER_API_KEY` | Google Search wrapper |
| 7 | Exa | Yes | `EXA_API_KEY` | Semantic / neural search |

## Architecture

```
fin-toolkit/
  providers/          # Data & search sources (protocols + implementations)
    protocol.py       #   DataProvider protocol (get_prices, get_financials, get_metrics)
    search_protocol.py#   SearchProvider protocol (search)
    yahoo.py          #   Yahoo Finance (free, no API key)
    kase.py           #   KASE scraper (Kazakhstan stock exchange)
    duckduckgo.py     #   DuckDuckGo (free, no API key)
    searxng.py        #   SearXNG (self-hosted search)
    perplexity.py     #   Perplexity Sonar API
    tavily.py         #   Tavily Search API
    brave.py          #   Brave Search API
    serper.py         #   Serper (Google Search) API
    exa.py            #   Exa AI semantic search
    router.py         #   ProviderRouter: market mapping + fallback chain
    search_router.py  #   SearchRouter: fallback chain for search
  analysis/           # Analysis engines
    technical.py      #   RSI, EMA, Bollinger Bands, MACD
    fundamental.py    #   Profitability, valuation, stability ratios
    risk.py           #   Volatility, VaR, correlation
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
    results.py        #   TechnicalResult, FundamentalResult, RiskResult, AgentResult, etc.
  config/             # Configuration
    models.py         #   ToolkitConfig, DataConfig, SearchConfig, etc.
    loader.py         #   YAML + env + defaults loader
  mcp_server/         # FastMCP server
    server.py         #   MCP tools (get_stock_data, run_technical_analysis, ...)
  cli.py              # CLI entry point (serve, setup, status)
```

### Protocol-first design

All major boundaries are `typing.Protocol` classes with `@runtime_checkable`. New providers/agents implement the protocol — no base class inheritance needed.

### Exception hierarchy

All exceptions inherit from `FinToolkitError`. Key subtypes: `TickerNotFoundError`, `ProviderUnavailableError`, `AllProvidersFailedError`, `InsufficientDataError`, `AgentNotFoundError`.

## Configuration

fin-toolkit loads configuration from (in priority order):

1. Environment variables (`BRAVE_API_KEY`, `PERPLEXITY_API_KEY`, `TAVILY_API_KEY`, etc.)
2. `.env` file in the project root
3. `./fin-toolkit.yaml` (local config)
4. `~/.config/fin-toolkit/config.yaml` (global config)
5. Built-in defaults

### Example `fin-toolkit.yaml`

```yaml
data:
  primary_provider: yahoo
  fallback_providers: [fmp]

search:
  providers: [duckduckgo, searxng, perplexity, tavily, brave, serper, exa]
  searxng_url: http://localhost:8888

agents:
  active: [elvis_marlamov, warren_buffett, ben_graham, charlie_munger, cathie_wood, peter_lynch]

markets:
  kz:
    provider: kase
    tickers: [KCEL, KZTO, KEGC, HSBK, CCBN]
```

## Testing

```bash
uv run pytest              # all tests (mock only)
uv run pytest --cov        # with coverage (fails under 80%)
uv run pytest -m live      # live tests (hits real APIs)
uv run mypy fin_toolkit/   # type checking (strict)
uv run ruff check          # linting
```

## License

MIT
