---
name: earnings-analysis
description: "Analyze a company's earnings quality, profitability, margin trends, and financial health. Use this skill whenever the user asks about earnings, profitability, margins, revenue growth, cash flow quality, balance sheet health, or financial statements. Trigger on phrases like 'how profitable is AAPL?', 'are Tesla's margins improving?', 'is this company financially healthy?', 'покажи прибыль компании', 'как с маржой у Сбера?', 'качество прибыли', 'финансовое здоровье'. Also trigger when the user asks to compare earnings across periods, check for accounting red flags, or assess whether a company's earnings are sustainable."
---

# Earnings Analysis

Analyze a company's earnings quality, margin trends, and financial health using fin-toolkit MCP tools.

## Tool Reference

See `_shared/mcp-tools-reference.md` for full MCP tool signatures and provider routing.

## Workflow

### 1. Fetch Data

```
run_fundamental_analysis(ticker)
get_stock_data(ticker, period="5y")
```

From fundamentals, extract:
- **Income statement**: revenue, gross profit, operating income, net income (multi-year if available via `income_history`)
- **Margins**: gross, operating, net
- **Cash flow**: operating cash flow, free cash flow (via `cash_flow_history`)
- **Balance sheet**: assets, liabilities, equity, cash, debt
- **Per-share**: EPS, revenue per share

Price data provides context for earnings vs stock performance.

If fundamental data is incomplete (common for Russian tickers via SmartLab or MOEX), note which fields are missing and proceed with what's available.

### 2. Revenue & Growth Analysis

- YoY revenue growth for each available period
- Growth acceleration or deceleration trend
- Revenue consistency — smooth vs lumpy (one-time items)

### 3. Margin Analysis

Track across periods:
- **Gross margin** — pricing power and cost structure
- **Operating margin** — operational efficiency
- **Net margin** — bottom-line profitability after all costs

Identify: expanding (good), stable (neutral), or contracting (concern).

### 4. Earnings Quality Assessment

This is the core insight — not all earnings are equal:

| Metric | How to Compute | Good | Concern |
|--------|---------------|------|---------|
| **Cash conversion** | FCF / Net Income | >1.0 | <0.5 |
| **Accrual ratio** | (Net Income − OCF) / Total Assets | Low (<5%) | High (>10%) |
| **Earnings consistency** | Volatility of YoY earnings | Stable | Wild swings |
| **SBC impact** | Stock-based comp / Net Income | <10% | >25% |

High net income + low cash conversion = aggressive accounting. Flag this clearly.

### 5. Balance Sheet Health

| Metric | Compute | Conservative | Aggressive |
|--------|---------|-------------|-----------|
| **Debt-to-Equity** | Total debt / Equity | <0.5 | >2.0 |
| **Net Debt / EBITDA** | (Debt − Cash) / EBITDA | <2x | >4x |
| **Cash position** | Cash / Total assets | >10% | <3% |

Track debt trajectory: is the company deleveraging or loading up?

### 6. Period Comparison

- Most recent year vs prior year (YoY change)
- Multi-year trend (3-5 years if available)
- Identify inflection points — when did margins start expanding/contracting?

## Output Structure

### 1. Company Overview
Ticker, sector, current price, market cap.

### 2. Revenue & Growth Table

| Period | Revenue | YoY Growth |
|--------|---------|------------|
| FY-4 through FY (latest) | values | percentages |

### 3. Profitability Margins Table

| Period | Gross Margin | Operating Margin | Net Margin |
|--------|-------------|-----------------|------------|
| each year | % | % | % |

With trend commentary.

### 4. Earnings Quality Scorecard

| Metric | Value | Assessment |
|--------|-------|------------|
| FCF / Net Income | X.Xx | Strong / Adequate / Weak |
| Accrual Ratio | X.X% | Low (good) / High (concern) |
| Earnings Consistency | — | Stable / Volatile |
| SBC as % of Net Income | X.X% | Minimal / Moderate / Heavy |

### 5. Balance Sheet Summary

| Metric | Value | Assessment |
|--------|-------|------------|
| Debt-to-Equity | X.Xx | Conservative / Moderate / Aggressive |
| Net Debt / EBITDA | X.Xx | Low / Moderate / High |
| Cash Position | $X.XB | Ample / Adequate / Thin |

### 6. Overall Assessment
One paragraph: financial health verdict, key strengths, key risks, red flags.

## Edge Cases

- **Pre-profit companies**: Focus on revenue growth, gross margin trajectory, cash burn rate. Skip earnings quality metrics.
- **Russian companies** (SmartLab data): Financials in billions of rubles. SmartLab provides IFRS statements with history. MOEX gives only basic metrics (no financials).
- **Banks**: Different financial structure — focus on NIM (net interest margin), loan growth, asset quality instead of standard operating margins.
- **Incomplete data**: If `income_history` / `cash_flow_history` are empty, work with whatever single-period data is available. State the limitation.
