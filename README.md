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

All MCP tools work out of the box — no API keys required (Yahoo Finance + DuckDuckGo).

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
│  └──────────────┘ └──────────────┘ └──────────────┘ └───────────┘ │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────┐ │
│  │search_news   │ │run_agent     │ │run_all_agents│ │run_recom- │ │
│  │              │ │              │ │              │ │mendation  │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └───────────┘ │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────┐ │
│  │run_portfolio │ │screen_stocks │ │generate_     │ │parse_     │ │
│  │_analysis     │ │              │ │investment_   │ │report     │ │
│  │              │ │              │ │idea          │ │           │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └───────────┘ │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────┐ │
│  │deep_dive     │ │compare_      │ │manage_       │ │check_     │ │
│  │              │ │stocks        │ │watchlist     │ │watchlist  │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └───────────┘ │
│                             │                                       │
│  ┌──────────────────────────┴──────────────────────────────────┐   │
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
│  KASE (JSON API) │ │  SearXNG            │ │  Warren Buffett        │
│  MOEX (aiomoex)  │ │  Google (Gemini)    │ │  Ben Graham            │
│  SmartLab (RU)   │ │  Perplexity         │ │  Charlie Munger        │
│  FinDatasets.ai  │ │  Tavily             │ │  Cathie Wood           │
│  EDGAR (SEC)     │ │  Brave              │ │  Peter Lynch           │
│  PDF Reports     │ │  Serper             │ │                        │
│                  │ │  Exa                │ │                        │
└──────────────────┘ └─────────────────────┘ └────────────────────────┘
```

## CLI Commands

CLI is infrastructure-only — it manages the server lifecycle, not analysis:

| Command | Description |
|---------|-------------|
| `fin-toolkit serve` | Start the MCP server |
| `fin-toolkit setup` | Register in `.mcp.json` (or `--global` for `~/.claude.json`) |
| `fin-toolkit status` | Show available providers, search engines, and agents |

All financial analysis is available exclusively through MCP tools below.

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

### run_all_agents

Run all active agents on a ticker and compute consensus.

```
ticker: "AAPL"
```

Returns: consensus score, signal, confidence, and per-agent results.

### run_recommendation

Generate a buy/hold recommendation with position sizing.

```
ticker: "AAPL"
period: "1y"
```

Returns: consensus, risk, technical signals, position size (0-25% portfolio), stop-loss level.

### run_portfolio_analysis

Analyze a portfolio with correlation-adjusted position sizing.

```
tickers: ["AAPL", "MSFT", "GOOGL"]
period: "1y"
```

Returns: per-ticker recommendations, correlation matrix, adjusted position sizes, total allocation.

### screen_stocks

Screen stocks by valuation score with optional consensus on top candidates.

```
tickers: ["AAPL", "MSFT", "GOOGL"]  # or use market
market: "moex"                        # auto-fetch tickers (moex, kase)
top_n: 10
filters: {"pe_ratio": "<15", "roe": ">0.10"}  # optional metric filters
```

Supported filter operators: `<`, `>`, `<=`, `>=`, `=`, `min..max` (range).

### generate_investment_idea

Generate a comprehensive investment idea with charts.

```
ticker: "AAPL"
period: "2y"
format: "html"        # opens interactive HTML with Plotly charts
```

Returns: consensus, fundamentals, scenarios, FCF waterfall, catalysts, risks, price chart.

### parse_report

Parse a financial report PDF and extract structured data.

```
source: "https://example.com/report.pdf"  # URL or local path
ticker: "AAPL"
```

Works with English and Russian (IFRS/МСФО) reports.

### deep_dive

Batch deep dive on multiple tickers (max 10). Fetches prices, financials, metrics, consensus, and news concurrently per ticker.

```
tickers: ["AAPL", "MSFT", "INTC"]
period: "1y"
```

Returns: per-ticker fundamentals, technical, risk, consensus, news. Partial failures → warnings per ticker.

### compare_stocks

Compare 2-10 stocks side by side on key metrics.

```
tickers: ["AAPL", "MSFT"]
metrics: ["pe_ratio", "roe", "consensus_score"]  # optional, defaults to standard set
```

Returns: comparison matrix `{metric: {ticker: value}}`.

### manage_watchlist

Manage persistent watchlists (YAML-backed at `~/.config/fin-toolkit/watchlists.yaml`).

```
action: "add"       # add, remove, list, show
watchlist: "default"
ticker: "AAPL"
notes: "Core holding"
```

### set_alert

Set an alert on a ticker in a watchlist.

```
watchlist: "default"
ticker: "AAPL"
metric: "pe_ratio"    # pe_ratio, roe, rsi, volatility_30d, etc.
operator: ">"
threshold: 25
label: "High P/E warning"
```

### check_watchlist

Check a watchlist for triggered alerts. Fetches current data and evaluates all configured alerts.

```
watchlist: "default"
```

Returns: list of triggered alerts with current values.

## Analysis Agents

| Agent | Style | Scoring |
|-------|-------|---------|
| `elvis_marlamov` | Fundamentals + sentiment | quality / stability / valuation / sentiment |
| `warren_buffett` | Value investing | margin of safety / durable advantage / management |
| `ben_graham` | Deep value | net-net value / earnings stability / financial strength |
| `charlie_munger` | Wonderful business at fair price | business quality / fair price / financial fortress |
| `cathie_wood` | Innovation & growth | growth signals / innovation premium / market position |
| `peter_lynch` | GARP | PEG value / earnings quality / common sense |

## Data Providers

| Provider | Markets | API Key | Notes |
|----------|---------|---------|-------|
| Yahoo Finance | Global | No | Default, free |
| KASE | Kazakhstan | No | JSON API (`kase.kz/api/*`), realtime data + Yahoo `.ME` fallback for OHLCV |
| MOEX | Russia | No | Prices via `aiomoex` package (ISS REST API) |
| SmartLab | Russia | No | P/E, P/B, EV/EBITDA, ROE + IFRS financials (scraper, `smart-lab.ru`) |
| Financial Datasets | US | Yes (`FINANCIAL_DATASETS_API_KEY`) | SEC EDGAR data, 17k+ tickers |
| EDGAR | US | No | SEC filings via `edgartools` |
| PDF Reports | Any | No | Parse IFRS/МСФО PDFs via `pdfplumber` |

## Search Providers

Fallback chain (first available wins):

| # | Provider | API Key | Env Var | Notes |
|---|----------|---------|---------|-------|
| 1 | DuckDuckGo | No | — | Always available, default |
| 2 | SearXNG | No | — | Self-hosted (`docker run -p 8888:8080 searxng/searxng`) |
| 3 | Google | Yes | `GEMINI_API_KEY` | Gemini + Search Grounding (model configurable via `search.gemini_model`) |
| 4 | Perplexity | Yes | `PERPLEXITY_API_KEY` | AI-powered search with citations |
| 5 | Tavily | Yes | `TAVILY_API_KEY` | Optimized for AI agents |
| 6 | Brave | Yes | `BRAVE_API_KEY` | Web search |
| 7 | Serper | Yes | `SERPER_API_KEY` | Google Search wrapper |
| 8 | Exa | Yes | `EXA_API_KEY` | Semantic / neural search |

## Architecture

```
fin-toolkit/
  providers/          # Data & search sources (protocols + implementations)
    protocol.py       #   DataProvider protocol (get_prices, get_financials, get_metrics)
    search_protocol.py#   SearchProvider protocol (search)
    yahoo.py          #   Yahoo Finance (free, no API key)
    kase.py           #   KASE JSON API + Yahoo .ME fallback
    moex.py           #   MOEX via aiomoex
    smartlab.py       #   SmartLab fundamentals + IFRS (scraper)
    financialdatasets.py#  Financial Datasets REST API
    edgar.py          #   SEC EDGAR filings via edgartools
    pdf_report.py     #   PDF report parser (IFRS/МСФО)
    duckduckgo.py     #   DuckDuckGo (free, no API key)
    searxng.py        #   SearXNG (self-hosted search)
    google.py         #   Google Search via Gemini API grounding
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
    portfolio.py      #   Consensus, position sizing, stop-loss
    screening.py      #   Quick valuation scoring + custom filters
    idea.py           #   Investment idea: scenarios, catalysts, FCF
    comparison.py     #   Stock comparison matrix
    alerts.py         #   Alert evaluation + AlertRule/WatchlistEntry dataclasses
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
    server.py         #   MCP tools (18 tools)
    serialize.py      #   TOON/JSON serialization
  report/             # Report generation
    html_report.py    #   Interactive HTML reports with Plotly charts (13 sections, EN/RU toggle)
    i18n.py           #   Bilingual translations, currency helpers
    narrative.py      #   Template-based thesis/FCF/target narratives
  watchlist.py        # YAML-backed persistent watchlist store
  cli.py              # CLI entry point (serve, setup, status)
```

### Protocol-first design

All major boundaries are `typing.Protocol` classes with `@runtime_checkable`. New providers/agents implement the protocol — no base class inheritance needed.

### Exception hierarchy

All exceptions inherit from `FinToolkitError`. Key subtypes: `TickerNotFoundError`, `ProviderUnavailableError`, `AllProvidersFailedError`, `InsufficientDataError`, `AgentNotFoundError`.

## Configuration

fin-toolkit loads configuration from (in priority order):

1. Environment variables (`GEMINI_API_KEY`, `BRAVE_API_KEY`, `PERPLEXITY_API_KEY`, `TAVILY_API_KEY`, etc.)
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
  providers: [duckduckgo, searxng, google, perplexity, tavily, brave, serper, exa]
  searxng_url: http://localhost:8888
  gemini_model: gemini-3.1-flash-lite  # configurable Gemini model for Google search

agents:
  active: [elvis_marlamov, warren_buffett, ben_graham, charlie_munger, cathie_wood, peter_lynch]

markets:
  kz:
    provider: kase
    tickers: [KCEL, KZTO, KEGC, HSBK, CCBN, KZAP]
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
