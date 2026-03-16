# Market Data Tools

## get_stock_data

Fetch historical OHLCV price data.

```
ticker: "AAPL"
period: "1y"          # 1m, 3m, 6m, 1y, 2y, 5y
provider: null        # optional: force a specific provider
```

Provider is auto-resolved via [routing](../providers/data.md): explicit → market mapping → primary → fallbacks.

## search_news

Search financial news and articles. Works out of the box via DuckDuckGo (no API key).

```
query: "AAPL earnings Q1 2026"
max_results: 10
```

Uses the [search fallback chain](../providers/search.md) — first available provider wins.

## deep_dive

Batch deep dive on multiple tickers (max 10). Fetches prices, financials, metrics, consensus, and news concurrently per ticker.

```
tickers: ["AAPL", "MSFT", "INTC"]
period: "1y"
```

Returns per-ticker fundamentals, technical, risk, consensus, news. Partial failures produce per-ticker warnings (not batch-level errors).

## compare_stocks

Compare 2–10 stocks side by side on key metrics.

```
tickers: ["AAPL", "MSFT"]
metrics: ["pe_ratio", "roe", "consensus_score"]  # optional, defaults to standard set
```

Returns comparison matrix `{metric: {ticker: value}}`.
