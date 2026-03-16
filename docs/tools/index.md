# MCP Tools

fin-toolkit exposes 20 MCP tools for financial analysis. All tools accept a `format` parameter (`"toon"` or `"json"`, default: `"toon"`).

| Tool | Category | Description |
|------|----------|-------------|
| [`get_stock_data`](market-data.md#get_stock_data) | Market Data | Historical OHLCV prices |
| [`deep_dive`](market-data.md#deep_dive) | Market Data | Batch deep dive (up to 10 tickers) |
| [`compare_stocks`](market-data.md#compare_stocks) | Market Data | Side-by-side comparison |
| [`run_technical_analysis`](analysis.md#run_technical_analysis) | Analysis | RSI, EMA, MACD, Bollinger Bands |
| [`run_fundamental_analysis`](analysis.md#run_fundamental_analysis) | Analysis | ROE, P/E, margins, ratios |
| [`run_risk_analysis`](analysis.md#run_risk_analysis) | Analysis | Volatility, VaR, correlation |
| [`run_portfolio_analysis`](analysis.md#run_portfolio_analysis) | Analysis | Correlation-adjusted sizing |
| [`run_agent`](agents.md#run_agent) | Agents | Single AI agent analysis |
| [`run_all_agents`](agents.md#run_all_agents) | Agents | Consensus from all agents |
| [`run_recommendation`](agents.md#run_recommendation) | Agents | Buy/hold + position sizing |
| [`screen_stocks`](screening.md#screen_stocks) | Screening | Valuation scoring + filters |
| [`generate_investment_idea`](screening.md#generate_investment_idea) | Screening | Full idea with Plotly charts |
| [`parse_report`](screening.md#parse_report) | Screening | PDF report parser (EN/RU) |
| [`search_news`](market-data.md#search_news) | News | Financial news search |
| [`manage_watchlist`](watchlist.md#manage_watchlist) | Watchlist | YAML-backed watchlists |
| [`set_alert`](watchlist.md#set_alert) | Watchlist | Metric-based alerts |
| [`check_watchlist`](watchlist.md#check_watchlist) | Watchlist | Evaluate triggered alerts |
| [`manage_portfolio`](portfolio.md#manage_portfolio) | Portfolio | Buy/sell transactions |
| [`portfolio_performance`](portfolio.md#portfolio_performance) | Portfolio | P&L and returns |
