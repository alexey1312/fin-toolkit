---
name: dcf-valuation
description: "Run DCF (Discounted Cash Flow) valuation on a stock to estimate intrinsic value per share. Use this skill whenever the user mentions valuation, intrinsic value, fair value, DCF, discounted cash flow, target price calculation, or asks questions like 'is AAPL undervalued?', 'what is the fair value of Tesla?', 'сколько стоит акция?', 'оценка компании', 'целевая цена'. Also trigger when the user discusses WACC, terminal value, margin of safety, or free cash flow projections in the context of stock valuation."
---

# DCF Valuation

Estimate a stock's intrinsic value using Discounted Cash Flow analysis via fin-toolkit MCP tools.

## Tool Reference

See `_shared/mcp-tools-reference.md` for full MCP tool signatures and provider routing.

## Workflow

### 1. Gather Data

Fetch prices and fundamentals concurrently:

```
get_stock_data(ticker, period="5y")
run_fundamental_analysis(ticker)
```

From the results, extract:
- **Current price** and historical trajectory
- **Free Cash Flow** (or operating cash flow − capex to compute it)
- **Revenue, net income** (trailing + multi-year for growth estimation)
- **Shares outstanding, debt, cash** (for equity bridge)

If data is incomplete — tell the user which fields are missing and whether DCF can proceed with assumptions.

### 2. Determine Growth Rate

Present the user with options and let them choose:

- **Historical CAGR**: compute from available FCF or revenue history
- **Analyst consensus**: surface if present in fundamental data
- **Conservative default**: lower of historical CAGR and consensus

Frame this as a meaningful decision — growth rate is the most impactful assumption in DCF. Different rates lead to vastly different valuations, so the user's view on the company's future matters here.

### 3. Determine Discount Rate (WACC)

Offer guidance, let user decide:

- **CAPM cost of equity**: risk-free rate (10Y Treasury ~4-5%) + beta × equity risk premium (~5-6%)
- **Cost of debt**: interest expense / total debt, tax-adjusted
- **WACC**: (E/V) × Re + (D/V) × Rd × (1 − tax rate)
- **Typical ranges**: 7-9% large-cap US, 9-12% mid/small-cap, 10-14% emerging markets
- **Default**: 10% if user has no preference

See `references/dcf-guide.md` for WACC calculation details and size/country premium adjustments.

### 4. Project Free Cash Flows (5-Year)

Use most recent FCF as base, project forward:

| Year | FCF | PV Factor | Present Value |
|------|-----|-----------|---------------|
| 0 (base) | from fundamentals | — | — |
| 1–5 | FCF × (1 + growth)^n | 1/(1+WACC)^n | FCF_n × PV Factor |

For two-stage models: higher rate years 1-3, lower rate years 4-5 transitioning to terminal.

### 5. Terminal Value

Default to Gordon Growth Model (ask user if they prefer exit multiple):

```
TV = FCF_5 × (1 + g_terminal) / (WACC − g_terminal)
```

- Terminal growth: 2-3% (must be < WACC)
- If TV is >80% of enterprise value, flag the model's sensitivity to terminal assumptions

See `references/dcf-guide.md` for exit multiple approach and three-stage model.

### 6. Compute Intrinsic Value

```
Enterprise Value = Σ PV(FCFs) + PV(Terminal Value)
Equity Value = Enterprise Value − Net Debt + Cash
Intrinsic Value Per Share = Equity Value / Shares Outstanding
```

### 7. Margin of Safety

```
Margin of Safety = (Intrinsic Value − Current Price) / Intrinsic Value × 100%
```

- **>30%**: potentially undervalued with good buffer
- **10-30%**: modestly undervalued
- **<10%**: roughly fair value
- **Negative**: appears overvalued vs DCF estimate

### 8. Sensitivity Analysis

Always include a sensitivity table — DCF is highly assumption-dependent:

| WACC \ Growth | 3% | 5% | 7% | 9% |
|---------------|-----|-----|-----|-----|
| 8% | $XX | $XX | $XX | $XX |
| 10% | $XX | $XX | $XX | $XX |
| 12% | $XX | $XX | $XX | $XX |

## Output Structure

1. **Company overview** — ticker, sector, current price
2. **Key assumptions** — growth rate, WACC, terminal growth, rationale for each
3. **FCF projection table** — year-by-year with present values
4. **Valuation** — enterprise value → equity value → intrinsic value per share
5. **Margin of safety** — percentage + interpretation
6. **Sensitivity table** — ±2% variations in growth and WACC

## Edge Cases

- **Negative FCF**: DCF doesn't work for cash-burning companies. Suggest revenue multiples or `generate_investment_idea(ticker)` for alternative approaches.
- **Cyclical companies**: Normalize FCF over a full cycle instead of using trailing period.
- **Financial companies (banks)**: Standard FCF is meaningless — use dividend discount model or excess return model instead.
- **Russian/KZ tickers**: Prices in local currency. Add country risk premium to WACC (3-5% for Russia, 2-4% for Kazakhstan).
