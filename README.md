# fin-toolkit

Protocol-first financial analysis toolkit with MCP server for Claude Code.

## Quick Start

```bash
# Install
mise install && uv sync

# Run MCP server
fin-toolkit serve

# Or use with Claude Code
cp .mcp.json.example .mcp.json
```

## Architecture

```
fin-toolkit/
  providers/          # Data sources (protocols + implementations)
    protocol.py       #   DataProvider protocol (get_prices, get_financials, get_metrics)
    search_protocol.py#   SearchProvider protocol (search)
    yahoo.py          #   Yahoo Finance (free, no API key)
    kase.py           #   KASE scraper (Kazakhstan stock exchange)
    brave.py          #   Brave Search (requires API key)
    searxng.py        #   SearXNG (self-hosted search)
    router.py         #   ProviderRouter: market mapping + fallback chain
    search_router.py  #   SearchRouter: fallback chain for search
  analysis/           # Analysis engines
    technical.py      #   RSI, EMA, Bollinger Bands, MACD
    fundamental.py    #   Profitability, valuation, stability ratios
    risk.py           #   Volatility, VaR, correlation, Kelly criterion
  agents/             # Analysis agents (protocol + implementations)
    protocol.py       #   AnalysisAgent protocol (analyze → AgentResult)
    elvis.py          #   Elvis Marlamov: 100-point scoring (quality/stability/valuation/sentiment)
    buffett.py        #   Warren Buffett: value investing (margin of safety/moat/management)
    graham.py         #   Ben Graham: deep value (net-net/earnings stability/financial strength)
    munger.py         #   Charlie Munger: wonderful business at fair price (quality/price/fortress)
    wood.py           #   Cathie Wood: innovation & growth (growth signals/innovation premium/position)
    lynch.py          #   Peter Lynch: GARP (PEG value/earnings quality/common sense)
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

Search financial news and articles (requires Brave API key or SearXNG instance).

```
query: "AAPL earnings Q4 2024"
max_results: 10
```

### run_agent

Run an AI analysis agent on a ticker.

```
ticker: "AAPL"
agent: "elvis_marlamov"   # or warren_buffett, ben_graham, charlie_munger, cathie_wood, peter_lynch
```

Returns: signal (Bullish/Neutral/Bearish), score (0-100), confidence (0.0-1.0), rationale, breakdown.

## Configuration

fin-toolkit loads configuration from (in priority order):

1. Environment variables (`FIN_TOOLKIT_DATA_PRIMARY`, `BRAVE_API_KEY`, `FMP_API_KEY`)
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
  providers: [brave, searxng]
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
# Run all tests (mock only)
uv run pytest

# Run with coverage
uv run pytest --cov

# Run live tests (hits real APIs)
uv run pytest -m live

# Type checking
uv run mypy fin_toolkit/

# Linting
uv run ruff check
```

## License

MIT
