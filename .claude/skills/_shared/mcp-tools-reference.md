# fin-toolkit MCP Tools Reference

Quick reference for all MCP tools available via fin-toolkit. All tools return TOON by default (30-60% token savings). Pass `format="json"` only when parsing programmatically.

## Data Retrieval

### get_stock_data
```
get_stock_data(ticker, period="1y", provider=None, format="toon")
```
Historical OHLCV prices. Periods: `1m`, `3m`, `6m`, `1y`, `2y`, `5y`.

### search_news
```
search_news(query, max_results=10, format="toon")
```
News articles with dates/sources. Broad queries work best (e.g. `"AAPL stock news 2026"`).

### parse_report
```
parse_report(source, ticker, format="toon")
```
Extract financials from PDF (URL or path). Bilingual EN/RU МСФО support.

## Analysis

### run_technical_analysis
```
run_technical_analysis(ticker, format="toon")
```
RSI, EMA (20/50/200), MACD, Bollinger Bands, signals, trend bias.

### run_fundamental_analysis
```
run_fundamental_analysis(ticker, sector=None, format="toon")
```
ROE, ROA, ROIC, margins, P/E, P/B, EV/EBITDA, FCF yield, D/E, dividend yield.

### run_risk_analysis
```
run_risk_analysis(tickers, period="1y", format="toon")
```
Volatility (30d/90d/252d), VaR (95%/99%), correlation matrix. Takes a **list** of tickers.

## Agent Analysis

### run_agent
```
run_agent(ticker, agent="elvis_marlamov", format="toon")
```
Single agent: `elvis_marlamov`, `warren_buffett`, `ben_graham`, `charlie_munger`, `cathie_wood`, `peter_lynch`.

### run_all_agents
```
run_all_agents(ticker, format="toon")
```
Consensus from all 6 agents. Returns aggregate score, signal (Bullish/Neutral/Bearish), per-agent breakdown.

### run_recommendation
```
run_recommendation(ticker, period="1y", format="toon")
```
Buy/Hold/Sell signal + position size (0-25%) + stop-loss level.

## Portfolio & Screening

### screen_stocks
```
screen_stocks(tickers=None, market=None, top_n=10, filters=None, format="toon")
```
Two-stage screening. Either pass `tickers` list or `market` (e.g. `"moex"`). Filters: `{"pe_ratio": "<15", "roe": ">10"}`.

### deep_dive
```
deep_dive(tickers, period="1y", format="toon")
```
Batch analysis for 1-10 tickers. Prices + metrics + consensus + news per ticker.

### compare_stocks
```
compare_stocks(tickers, metrics=None, format="toon")
```
Side-by-side comparison for 2-10 tickers.

### generate_investment_idea
```
generate_investment_idea(ticker, period="2y", format="html")
```
Full HTML report with Plotly charts. Default format is `"html"` (opens browser). Use `"toon"` or `"json"` for data only.

### run_portfolio_analysis
```
run_portfolio_analysis(tickers, period="1y", format="toon")
```
Per-ticker recommendation with correlation-adjusted position sizing.

## Watchlist & Portfolio

### manage_watchlist
```
manage_watchlist(action, watchlist="default", ticker=None, notes=None, format="toon")
```
Actions: `add`, `remove`, `list`, `show`.

### set_alert / check_watchlist
```
set_alert(watchlist, ticker, metric, operator, threshold, label=None, format="toon")
check_watchlist(watchlist="default", format="toon")
```

### manage_portfolio
```
manage_portfolio(action, portfolio=None, ticker=None, shares=None, price=None, fee=0, currency="USD", date=None, notes=None, format="toon")
```
Actions: `create`, `delete`, `list`, `show`, `buy`, `sell`, `history`.

### portfolio_performance
```
portfolio_performance(portfolio, period="1m", format="toon")
```
P&L, returns %, per-ticker breakdown. Periods: `1m`, `3m`, `6m`, `1y`, `ytd`, `all`.

## Provider Routing

| Market | Prices | Fundamentals | Metrics |
|--------|--------|-------------|---------|
| US (AAPL, MSFT) | Yahoo | Yahoo / EDGAR | Yahoo / FinancialDatasets |
| Russia (SBER, GAZP) | MOEX | SmartLab | SmartLab |
| Kazakhstan (KCEL, HSBK) | KASE (via Yahoo .ME) | — | KASE |

Default chain: explicit `provider` → market mapping → Yahoo → SmartLab → MOEX → FinancialDatasets → EDGAR.

## Error Responses

Errors always return JSON (regardless of `format`):
```json
{"error": "...", "is_error": true, "hint": "actionable guidance"}
```
