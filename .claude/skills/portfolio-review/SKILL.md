---
name: portfolio-review
description: "Review a portfolio of stocks with risk analysis. Use when the user asks to review their portfolio, check correlations, or assess portfolio risk."
---

# Portfolio Review Skill

Review a multi-stock portfolio using fin-toolkit MCP tools to assess individual holdings, correlations, and aggregate risk.

## Prerequisites

- fin-toolkit MCP server running (`fin-toolkit serve`)
- Valid API keys configured for the data provider
- User provides a list of tickers (and optionally weights/allocation percentages)

## Workflow

### Step 1: Gather Portfolio Holdings

Ask the user for:
- List of ticker symbols
- Allocation weights (percentage or dollar amounts)
- If no weights provided, assume equal weighting

### Step 2: Analyze Each Holding

For each ticker in the portfolio, call all three analysis tools:

```
get_stock_data(ticker, period="1y")
run_technical_analysis(ticker)
run_fundamental_analysis(ticker)
```

Extract per-holding:
- Current price and 1Y return
- Key technical signal (bullish/bearish/neutral)
- Key fundamentals (P/E, revenue growth, margins, debt-to-equity)

**Error handling:** If any tool call fails for a specific ticker, log the error and continue with remaining tickers. Report which holdings could not be analyzed at the end.

### Step 3: Run Portfolio Risk Analysis

Call the risk analysis tool with all tickers:

```
run_risk_analysis(tickers)
```

Where `tickers` is the list of all portfolio ticker symbols.

Extract from the result:
- **Correlation matrix:** Pairwise correlations between holdings
- **Portfolio volatility:** Annualized standard deviation of the weighted portfolio
- **Value at Risk (VaR):** 95% and 99% confidence levels (daily and/or monthly)
- **Maximum drawdown:** Largest peak-to-trough decline in the historical period
- **Sharpe ratio:** Risk-adjusted return (if risk-free rate is available)
- **Beta:** Portfolio beta relative to the benchmark (S&P 500)

**Error handling:** If `run_risk_analysis` fails, compute basic statistics manually from the individual `get_stock_data` results (returns, simple correlation). Warn the user that advanced risk metrics are unavailable.

### Step 4: Assess Diversification

Analyze the correlation matrix:
- **Highly correlated pairs (>0.8):** These holdings move together and provide limited diversification benefit. Flag them.
- **Negative or low correlations (<0.3):** These provide good diversification. Highlight them.
- **Sector concentration:** If multiple holdings are in the same sector, note the concentration risk.

### Step 5: Compile Portfolio Summary

Bring all analysis together into a comprehensive review.

## Output Format

### 1. Portfolio Overview

| # | Ticker | Weight | Current Price | 1Y Return | Sector |
|---|--------|--------|--------------|-----------|--------|
| 1 | AAPL | 25% | $XXX | +XX% | Tech |
| 2 | ... | ... | ... | ... | ... |

Total portfolio value (if dollar amounts provided), number of holdings, sector breakdown.

### 2. Individual Holdings Summary

For each holding, a brief card:
- **Ticker:** Price, 1Y return
- **Technical:** Bullish/Bearish/Neutral (key signal)
- **Fundamental:** P/E, revenue growth, margin trend
- **Verdict:** Strength/concern for this position

### 3. Risk Metrics

| Metric | Value |
|--------|-------|
| Portfolio Annualized Volatility | X.X% |
| Portfolio Beta (vs S&P 500) | X.XX |
| Sharpe Ratio | X.XX |
| VaR (95%, 1-day) | -X.X% |
| VaR (99%, 1-day) | -X.X% |
| Maximum Drawdown (1Y) | -X.X% |

### 4. Correlation Matrix

Present the pairwise correlation matrix as a table. Highlight pairs with correlation > 0.8 and pairs with correlation < 0.3.

### 5. Diversification Assessment
- Sector concentration analysis
- Geographic concentration (if applicable)
- Highly correlated pairs that reduce diversification
- Suggestions for improving diversification (if appropriate)

### 6. Portfolio Actionable Summary
- Top strengths of the portfolio
- Top risks and concentration concerns
- Any individual holdings with red flags (technical or fundamental)
- Optional rebalancing suggestions (only if user asks)

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| MCP tool calls fail | fin-toolkit server not running | Run `fin-toolkit serve` in a separate terminal |
| "API key not found" | Missing provider API key | Check fin-toolkit configuration for required API keys |
| One or more tickers not found | Invalid ticker or not covered by provider | Report which tickers failed and proceed with the rest |
| `run_risk_analysis` fails | Too few tickers or insufficient overlapping data | Fall back to manual correlation computation from price data |
| Slow response for large portfolio | Many tickers means many API calls | Process in batches; warn user that large portfolios take longer |
| Missing weights | User did not specify allocation | Assume equal weighting and note this assumption |
