---
name: portfolio-review
description: "Review a multi-stock portfolio with risk analysis, correlations, and position sizing. Use this skill whenever the user asks to review their portfolio, assess portfolio risk, check diversification, analyze correlations between holdings, get rebalancing suggestions, or evaluate portfolio allocation. Trigger on phrases like 'review my portfolio', 'how risky is my portfolio?', 'check my holdings', 'are my stocks too correlated?', 'portfolio diversification', 'проверь мой портфель', 'оценка рисков портфеля', 'корреляция акций', 'ребалансировка'. Also trigger when the user provides a list of stocks and wants aggregate analysis or when they discuss position sizing."
---

# Portfolio Review

Review a multi-stock portfolio: individual holdings, risk metrics, correlations, diversification, and actionable insights.

## Tool Reference

See `_shared/mcp-tools-reference.md` for full MCP tool signatures and provider routing.

## Workflow

### 1. Gather Holdings

Ask for or extract from conversation:
- List of tickers
- Weights (% or dollar amounts). If not provided — assume equal weighting and note the assumption.

If the user has a portfolio in fin-toolkit, use:
```
manage_portfolio(action="show", portfolio="name")
```
This returns current positions with live prices.

### 2. Analyze Individual Holdings

For each ticker:
```
run_fundamental_analysis(ticker)
run_technical_analysis(ticker)
```

Extract per holding:
- Current price and YTD/1Y return
- Technical signal (bullish/bearish/neutral)
- Key fundamentals: P/E, revenue growth, margins, D/E
- Red flags (if any)

If a tool call fails for a specific ticker — log it and continue. Report failures at the end.

### 3. Portfolio Risk Analysis

```
run_risk_analysis(tickers, period="1y")
```

This returns:
- **Volatility**: 30d, 90d, 252d annualized
- **VaR**: 95% and 99% daily/monthly
- **Correlation matrix**: pairwise correlations between all holdings
- **Max drawdown**: largest peak-to-trough decline

If risk analysis fails, compute basic stats manually from price data.

### 4. Portfolio-Level Recommendation

```
run_portfolio_analysis(tickers, period="1y")
```

Returns per-ticker recommendations with **correlation-adjusted position sizing** — positions in highly correlated stocks get reduced, negatively correlated pairs get boosted.

### 5. Assess Diversification

From the correlation matrix:
- **Highly correlated pairs (>0.8)**: move together, limited diversification. Flag them.
- **Low correlation pairs (<0.3)**: good diversification benefit. Highlight them.
- **Sector concentration**: multiple holdings in same sector = concentration risk.
- **Geographic concentration**: all US, all Russia, etc.

## Output Structure

### 1. Portfolio Overview

| # | Ticker | Weight | Price | 1Y Return | Sector |
|---|--------|--------|-------|-----------|--------|
| 1 | AAPL | 25% | $XXX | +XX% | Tech |

Total holdings count, sector breakdown.

### 2. Individual Holdings

Brief card per holding:
- Price, return, technical signal
- P/E, margin trend, D/E
- One-line verdict (strength or concern)

### 3. Risk Metrics

| Metric | Value |
|--------|-------|
| Portfolio Volatility (ann.) | X.X% |
| VaR 95% (1-day) | -X.X% |
| VaR 99% (1-day) | -X.X% |
| Max Drawdown (1Y) | -X.X% |

### 4. Correlation Matrix

Table with pairwise correlations. Mark >0.8 as high, <0.3 as low.

### 5. Diversification Assessment
- Sector/geographic concentration
- Correlated pairs reducing diversification
- Suggestions for improvement (only if user asks, or if concentration is extreme)

### 6. Position Sizing (from portfolio analysis)

| Ticker | Signal | Raw Size | Adjusted Size | Reason |
|--------|--------|----------|---------------|--------|
| AAPL | Bullish | 20% | 18% | High corr with MSFT |

### 7. Action Summary
- Top strengths
- Top risks
- Red flag holdings
- Rebalancing ideas (if requested)

## Edge Cases

- **Mixed markets** (US + RU + KZ tickers): each ticker routes to appropriate provider automatically. Risk analysis may have incomplete correlations if price histories don't overlap.
- **Large portfolios (>10 tickers)**: `run_risk_analysis` and `run_portfolio_analysis` accept lists. `deep_dive` is capped at 10 — split into batches if needed.
- **Single stock**: still works, but correlation analysis is meaningless. Focus on individual analysis + risk metrics.
- **Portfolio store integration**: if user has portfolios in fin-toolkit, `manage_portfolio(action="show")` gives current positions. `portfolio_performance(portfolio, period)` gives P&L breakdown.
