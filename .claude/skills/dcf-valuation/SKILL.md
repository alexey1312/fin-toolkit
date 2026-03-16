---
name: dcf-valuation
description: "Run DCF (Discounted Cash Flow) valuation on a stock. Use when the user asks to value a stock, compute intrinsic value, or run DCF analysis."
---

# DCF Valuation Skill

Perform a Discounted Cash Flow valuation using fin-toolkit MCP tools to estimate a stock's intrinsic value.

## Prerequisites

- fin-toolkit MCP server running (`fin-toolkit serve`)
- Valid API keys configured for the data provider

## Workflow

### Step 1: Fetch Historical Price Data

Call the MCP tool to retrieve 5 years of historical prices:

```
get_stock_data(ticker, period="5y")
```

Extract from the result:
- Current share price
- Historical price trajectory (used later for sanity-checking growth assumptions)

**Error handling:** If `get_stock_data` returns an error, check that the ticker symbol is valid and the MCP server is running. Inform the user if the provider does not cover this ticker.

### Step 2: Retrieve Fundamental Data

Call the MCP tool to pull financial ratios and statements:

```
run_fundamental_analysis(ticker)
```

Extract from the result:
- Revenue, operating income, net income (trailing and multi-year)
- Free Cash Flow (FCF) or the components to compute it (operating cash flow minus capex)
- Shares outstanding
- Existing debt and cash balances

**Error handling:** If `run_fundamental_analysis` returns incomplete data, warn the user which fields are missing and whether the valuation can still proceed with reasonable assumptions.

### Step 3: Determine Growth Rate Assumption

Ask the user for their preferred growth rate. Provide guidance:

- **Analyst consensus:** If available in the fundamental data, surface the consensus revenue/earnings growth estimate.
- **Historical CAGR:** Calculate the compound annual growth rate of FCF or revenue over the available history.
- **Default:** If the user has no preference, use the lower of analyst consensus and 5-year historical CAGR as a conservative baseline.

Present the options clearly and let the user decide before proceeding.

### Step 4: Determine Discount Rate (WACC)

Ask the user for a discount rate or WACC. Provide guidance:

- **Cost of equity:** Can be estimated via CAPM — risk-free rate (10Y Treasury ~4-5%) + beta * equity risk premium (~5-6%).
- **Cost of debt:** Interest expense / total debt, tax-adjusted.
- **WACC formula:** (E/V) * Re + (D/V) * Rd * (1 - tax rate), where E = market cap, D = total debt, V = E + D.
- **Typical ranges:** 8-12% for large-cap US equities; higher for small-cap or emerging markets.
- **Default:** If the user has no preference, use 10% as a reasonable starting point for a US large-cap.

### Step 5: Project Free Cash Flows (5-Year Horizon)

Using the most recent FCF as the base, project forward 5 years:

| Year | FCF |
|------|-----|
| 0 (base) | Latest FCF from fundamentals |
| 1 | FCF_0 * (1 + growth_rate) |
| 2 | FCF_1 * (1 + growth_rate) |
| 3 | FCF_2 * (1 + growth_rate) |
| 4 | FCF_3 * (1 + growth_rate) |
| 5 | FCF_4 * (1 + growth_rate) |

If the user prefers a two-stage model (high growth then fade), apply the higher rate for years 1-3 and a lower terminal growth rate for years 4-5.

### Step 6: Calculate Terminal Value

Use one of two approaches (ask user preference, default to Gordon Growth):

**Gordon Growth Model:**
```
Terminal Value = FCF_5 * (1 + terminal_growth_rate) / (WACC - terminal_growth_rate)
```
- Terminal growth rate should be 2-3% (roughly GDP growth). Never exceed WACC.

**Exit Multiple Method:**
```
Terminal Value = FCF_5 * exit_EV_to_FCF_multiple
```
- Use sector-median EV/FCF multiple as default.

### Step 7: Discount to Present Value

Discount each projected FCF and the terminal value back to today:

```
PV = FCF_t / (1 + WACC)^t
Enterprise Value = sum(PV of FCFs) + PV of Terminal Value
Equity Value = Enterprise Value - Net Debt + Cash
Intrinsic Value Per Share = Equity Value / Shares Outstanding
```

Present the full calculation table to the user.

### Step 8: Margin of Safety Assessment

Compare the computed intrinsic value to the current market price:

```
Margin of Safety = (Intrinsic Value - Current Price) / Intrinsic Value * 100%
```

Provide interpretation:
- **> 30% margin of safety:** Potentially undervalued with a good safety buffer
- **10-30%:** Modestly undervalued, reasonable entry depending on conviction
- **< 10%:** Roughly fairly valued
- **Negative:** Stock appears overvalued relative to DCF estimate

Always caveat that DCF is highly sensitive to growth and discount rate assumptions. Recommend the user run a sensitivity analysis (see `references/dcf-guide.md`).

## Output Format

Present results as a structured summary:

1. **Company overview** — name, ticker, sector, current price
2. **Key assumptions** — growth rate, WACC, terminal growth, projection period
3. **FCF projection table** — year-by-year with present values
4. **Valuation result** — enterprise value, equity value, intrinsic value per share
5. **Margin of safety** — percentage and interpretation
6. **Sensitivity table** — show intrinsic value across ±1-2% variations in growth and WACC

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| MCP tool calls fail | fin-toolkit server not running | Run `fin-toolkit serve` in a separate terminal |
| "API key not found" | Missing provider API key | Check fin-toolkit configuration for required API keys |
| Negative FCF | Company is not FCF-positive | Warn user that DCF is unreliable for pre-profit companies; suggest revenue-based or comparable valuation instead |
| Unrealistic intrinsic value | Extreme growth or low WACC assumptions | Re-check inputs; run sensitivity analysis to show range |
| Missing financial data | Provider does not cover this stock | Try a different provider or inform user of data limitations |
