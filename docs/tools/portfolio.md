# Portfolio

## manage_portfolio

Manage portfolios with buy/sell transactions (SQLite-backed at `~/.config/fin-toolkit/fin-toolkit.db`).

```
action: "create"      # create, delete, list, show, buy, sell, history
portfolio: "us_tech"
ticker: "AAPL"        # required for buy/sell/history
shares: 10            # required for buy/sell
price: 150.0          # required for buy/sell
fee: 0                # optional transaction fee
currency: "USD"       # for create (USD, RUB, KZT)
date: null            # ISO 8601, default: now
```

Actions:

- **create** — create a new portfolio with currency
- **delete** — delete portfolio and all transactions
- **list** — list all portfolios
- **show** — show positions enriched with live prices, P&L, and weights
- **buy** / **sell** — record a transaction (sell validates against current position)
- **history** — show transaction history for a ticker

## portfolio_performance

Analyze portfolio performance over a time period.

```
portfolio: "us_tech"
period: "1m"          # 1m, 3m, 6m, 1y, ytd, all
```

Returns: start/end value, P&L, P&L %, transaction count, per-ticker returns.
