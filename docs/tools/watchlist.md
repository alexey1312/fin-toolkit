# Watchlist & Alerts

## manage_watchlist

Manage persistent watchlists (YAML-backed at `~/.config/fin-toolkit/watchlists.yaml`).

```
action: "add"       # add, remove, list, show
watchlist: "default"
ticker: "AAPL"
notes: "Core holding"
```

Actions:

- **add** — add ticker to watchlist with optional notes
- **remove** — remove ticker from watchlist
- **list** — list all watchlists
- **show** — show tickers in a specific watchlist

## set_alert

Set a metric-based alert on a ticker in a watchlist.

```
watchlist: "default"
ticker: "AAPL"
metric: "pe_ratio"    # pe_ratio, roe, rsi, volatility_30d, etc.
operator: ">"
threshold: 25
label: "High P/E warning"
```

Alert metrics are routed to the appropriate data source:

- **KeyMetrics**: `pe_ratio`, `roe`, `pb_ratio`, `ev_ebitda`, `fcf_yield`, `dividend_yield`, `debt_to_equity`, `current_ratio`
- **RiskResult**: `volatility_30d`, `volatility_90d`, `var_95`, `var_99`
- **TechnicalResult**: `rsi`, `ema_20`, `ema_50`, `ema_200`

## check_watchlist

Check a watchlist for triggered alerts. Fetches current data and evaluates all configured alerts.

```
watchlist: "default"
```

Returns a list of triggered alerts with current values and configured thresholds.
