# Configuration

fin-toolkit loads configuration from (in priority order):

1. Environment variables
2. `.env` file in the project root
3. `./fin-toolkit.yaml` (local config)
4. `~/.config/fin-toolkit/config.yaml` (global config)
5. Built-in defaults

!!! warning "Config files are NOT merged"
    First found wins. If `./fin-toolkit.yaml` exists, `~/.config/fin-toolkit/config.yaml` is ignored (including its API keys).

## Environment Variables

| Variable | Provider |
|----------|----------|
| `GEMINI_API_KEY` | Google Search via Gemini |
| `PERPLEXITY_API_KEY` | Perplexity |
| `TAVILY_API_KEY` | Tavily |
| `BRAVE_API_KEY` | Brave Search |
| `SERPER_API_KEY` | Serper |
| `EXA_API_KEY` | Exa |
| `FMP_API_KEY` | Financial Modeling Prep |
| `FINANCIAL_DATASETS_API_KEY` | Financial Datasets |

## Example `fin-toolkit.yaml`

```yaml
# API keys (alternative to env vars)
api_keys:
  google: "your-gemini-api-key"
  brave: "your-brave-api-key"
  perplexity: "your-perplexity-api-key"
  tavily: "your-tavily-api-key"
  serper: "your-serper-api-key"
  exa: "your-exa-api-key"
  fmp: "your-fmp-api-key"
  financialdatasets: "your-financial-datasets-api-key"

data:
  primary_provider: yahoo
  fallback_providers: [smartlab, moex, financialdatasets, edgar]

search:
  providers: [duckduckgo, searxng, google, perplexity, tavily, brave, serper, exa]
  searxng_url: http://localhost:8888
  gemini_model: gemini-3.1-flash-lite

agents:
  active:
    - elvis_marlamov
    - warren_buffett
    - ben_graham
    - charlie_munger
    - cathie_wood
    - peter_lynch

markets:
  ru:
    provider: moex
    tickers: [SBER, GAZP, LKOH, ROSN, GMKN]
  # kz market uses dynamic ticker discovery — no need to list tickers
  # kz:
  #   provider: kase
  #   tickers: []  # auto-fetched via KASE API

# Override default rate limits per provider (optional)
rate_limits:
  yahoo:
    requests_per_minute: 5
    max_concurrent: 2
  smartlab:
    requests_per_minute: 5
    max_concurrent: 2
  moex:
    requests_per_minute: 10
    max_concurrent: 3
  kase:
    requests_per_minute: 2
    max_concurrent: 1
  stockanalysis:
    requests_per_minute: 5
    max_concurrent: 2
```
