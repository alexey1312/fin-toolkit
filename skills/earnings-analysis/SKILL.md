---
name: earnings-analysis
description: "Analyze earnings quality and financial health. Use when the user asks about earnings, margins, revenue growth, or financial health."
---

# Earnings Analysis Skill

Analyze a company's earnings quality, margin trends, and overall financial health using fin-toolkit MCP tools.

## Prerequisites

- fin-toolkit MCP server running (`fin-toolkit serve`)
- Valid API keys configured for the data provider

## Workflow

### Step 1: Fetch Historical Price Data

```
get_stock_data(ticker, period="5y")
```

Retrieve 5 years of price data to contextualize earnings against stock performance. Extract current price and historical trajectory.

**Error handling:** If `get_stock_data` fails, verify the ticker and MCP server status. Proceed to Step 2 even if price data is unavailable — earnings analysis can still be performed.

### Step 2: Retrieve Fundamental Data

```
run_fundamental_analysis(ticker)
```

Extract from the result:
- **Income statement:** Revenue, gross profit, operating income, net income (multi-year)
- **Margins:** Gross margin, operating margin, net margin
- **Per-share metrics:** EPS (diluted), revenue per share
- **Cash flow:** Operating cash flow, free cash flow
- **Balance sheet:** Total assets, total liabilities, shareholders' equity, cash, debt

**Error handling:** If `run_fundamental_analysis` returns incomplete data, note which fields are missing. If core income statement data is absent, inform the user that a full earnings analysis is not possible with the available data.

### Step 3: Analyze Trends and Quality

#### Revenue Analysis
- Calculate year-over-year revenue growth for each available period
- Identify acceleration or deceleration in growth
- Note any one-time or non-recurring revenue items if visible

#### Margin Analysis
- Track gross margin, operating margin, and net margin over time
- Identify expanding or contracting margins
- Compare margins to sector averages if the user provides them or if available in the data

#### Earnings Quality Assessment
- **Accrual ratio:** Compare net income to operating cash flow. If net income significantly exceeds OCF, earnings quality is lower (aggressive accrual accounting).
- **Cash conversion:** FCF / Net Income ratio. Above 1.0 is strong; below 0.5 is a warning sign.
- **Consistency:** Look for volatile swings in earnings that suggest one-time items or accounting changes.
- **SBC impact:** If stock-based compensation is available, note its magnitude relative to net income.

#### Balance Sheet Health
- **Leverage:** Debt-to-equity ratio, net debt / EBITDA
- **Liquidity:** Current ratio (if available), cash as percentage of total assets
- **Debt trajectory:** Is the company deleveraging or taking on more debt?

### Step 4: Period-over-Period Comparison

Construct a comparison of the most recent period versus prior periods:

- Most recent quarter vs same quarter last year (YoY)
- Most recent annual vs prior annual
- Identify any inflection points or notable changes

### Step 5: Present Assessment

Compile the analysis into a structured report with a clear quality verdict.

## Output Format

### 1. Company Overview
- Name, ticker, sector, current price, market cap

### 2. Revenue and Growth

| Period | Revenue | YoY Growth |
|--------|---------|------------|
| FY-4 | $X.XB | — |
| FY-3 | $X.XB | X.X% |
| FY-2 | $X.XB | X.X% |
| FY-1 | $X.XB | X.X% |
| FY (latest) | $X.XB | X.X% |

### 3. Profitability Margins

| Period | Gross Margin | Operating Margin | Net Margin |
|--------|-------------|-----------------|------------|
| (each year) | X.X% | X.X% | X.X% |

Trend commentary: expanding, stable, or contracting.

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
| Net Debt / EBITDA | X.Xx | Low / Moderate / High leverage |
| Cash Position | $X.XB | Ample / Adequate / Thin |

### 6. Overall Assessment
- One-paragraph summary of financial health and earnings quality
- Key strengths and key risks
- Any red flags (deteriorating margins, rising leverage, poor cash conversion)

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| MCP tool calls fail | fin-toolkit server not running | Run `fin-toolkit serve` in a separate terminal |
| "API key not found" | Missing provider API key | Check fin-toolkit configuration for required API keys |
| Incomplete financial statements | Company is foreign, small-cap, or recently listed | Inform user of data gaps; analysis will be partial |
| Negative earnings | Company is pre-profit | Focus on revenue growth, gross margin trend, and cash burn rate instead |
| Stale data | Provider data not yet updated for latest quarter | Note the most recent period available and warn user |
