# DCF Methodology Reference Guide

A comprehensive reference for Discounted Cash Flow analysis, intended as background material for the `dcf-valuation` skill.

## Free Cash Flow (FCF) Projection Methods

### Method 1: Direct FCF from Cash Flow Statement

```
FCF = Operating Cash Flow - Capital Expenditures
```

Most straightforward when reliable cash flow statements are available. Preferred for mature companies with stable capex.

### Method 2: Build-Up from Net Income

```
FCF = Net Income
    + Depreciation & Amortization
    - Changes in Working Capital
    - Capital Expenditures
```

Useful when operating cash flow is not directly available or when you want to decompose the drivers.

### Method 3: EBITDA-Based

```
FCF = EBITDA * (1 - Tax Rate) + D&A * Tax Rate - ΔWorking Capital - CapEx
```

Common in leveraged finance and when comparing across capital structures.

### Choosing a Method

- Use **Method 1** when cash flow statements are complete and trustworthy.
- Use **Method 2** when you want granular control over working capital assumptions.
- Use **Method 3** when working from EBITDA multiples or comparable analysis.

## WACC Calculation

WACC (Weighted Average Cost of Capital) represents the blended required return for all capital providers.

### Formula

```
WACC = (E/V) * Re + (D/V) * Rd * (1 - T)
```

Where:
- **E** = Market value of equity (market cap)
- **D** = Market value of debt (book value as proxy if market value unavailable)
- **V** = E + D (total enterprise value of capital)
- **Re** = Cost of equity
- **Rd** = Cost of debt (pre-tax)
- **T** = Corporate tax rate

### Cost of Equity (CAPM)

```
Re = Rf + β * (Rm - Rf)
```

- **Rf** = Risk-free rate (10-year US Treasury yield, typically 4-5% as of 2025-2026)
- **β** = Beta of the stock relative to the market (from fundamental data or regression)
- **Rm - Rf** = Equity risk premium (historical average ~5-6% for US equities)

**Adjustments:**
- Add a size premium (1-3%) for small-cap stocks
- Add a country risk premium for emerging market stocks
- If beta is unavailable, use sector-average beta

### Cost of Debt

```
Rd = Interest Expense / Total Debt
```

Or use the yield on the company's outstanding bonds if available. Always apply the tax shield: `Rd * (1 - T)`.

### Typical WACC Ranges

| Company Profile | WACC Range |
|----------------|------------|
| Large-cap US blue chip | 7-9% |
| Mid-cap US | 9-11% |
| Small-cap US | 11-14% |
| Emerging market large-cap | 10-14% |
| High-growth tech (pre-profit) | 12-16% |

## Terminal Value Approaches

The terminal value typically accounts for 60-80% of total DCF value, so the method and assumptions matter greatly.

### Approach 1: Gordon Growth Model (Perpetuity Growth)

```
TV = FCF_n * (1 + g) / (WACC - g)
```

Where:
- **FCF_n** = Free cash flow in the last projected year
- **g** = Perpetual growth rate (terminal growth)
- **WACC** = Discount rate

**Guidelines for terminal growth rate (g):**
- Should not exceed long-term nominal GDP growth (2-3% for developed markets)
- Higher than 3% is rarely justifiable for any single company in perpetuity
- Must be strictly less than WACC, or the formula produces nonsensical results
- 2.5% is a common default for US companies

### Approach 2: Exit Multiple Method

```
TV = FCF_n * Multiple
```

or

```
TV = EBITDA_n * EV/EBITDA Multiple
```

**Choosing the multiple:**
- Use the current sector-median EV/EBITDA or EV/FCF multiple
- Can also use the company's own historical average multiple
- Typical EV/EBITDA ranges: 8-12x for mature industrials, 15-25x for tech, 6-8x for utilities

**Pros and cons:**
- Gordon Growth is theoretically pure but very sensitive to the growth rate assumption
- Exit Multiple is more market-grounded but embeds current market sentiment (which may be irrational)
- Best practice: calculate both and compare

## Sensitivity Analysis

Because DCF output is highly sensitive to inputs, always present a sensitivity table varying the two most impactful assumptions: **growth rate** and **WACC**.

### Example Sensitivity Matrix

Create a grid where:
- Rows = WACC values (e.g., 8%, 9%, 10%, 11%, 12%)
- Columns = Growth rate values (e.g., 3%, 5%, 7%, 9%, 11%)
- Cells = Resulting intrinsic value per share

This gives the user a range of fair values rather than a single point estimate, which is far more useful for decision-making.

### Interpreting the Sensitivity Table

- If the stock is undervalued across most of the table, that is a stronger signal than if it's only undervalued under optimistic assumptions.
- Focus on the "realistic" center of the table, not the extremes.
- If terminal value dominates (>80% of enterprise value), the model is fragile — flag this to the user.

## Two-Stage and Three-Stage Models

### Two-Stage DCF

- **Stage 1 (High growth):** 3-5 years at above-average growth (company-specific)
- **Stage 2 (Terminal):** Perpetuity at stable growth (2-3%)

Appropriate for companies currently growing faster than the economy but expected to mature.

### Three-Stage DCF

- **Stage 1 (High growth):** 3-5 years at peak growth
- **Stage 2 (Transition):** 3-5 years with linearly declining growth
- **Stage 3 (Terminal):** Perpetuity at GDP-like growth

More realistic for high-growth companies, as it avoids the abrupt transition from high growth to terminal.

## Common Pitfalls

1. **Garbage in, garbage out:** If base FCF is anomalous (one-time charges, restructuring), normalize it first.
2. **Terminal value dominance:** If terminal value is >80% of total, the near-term projections barely matter — consider whether the terminal assumptions are robust.
3. **Circular references:** WACC depends on equity value, which is what you are trying to calculate. Use iterative solving or assume a target capital structure.
4. **Negative FCF companies:** DCF does not work well for companies burning cash. Use revenue multiples or option-based valuation instead.
5. **Ignoring dilution:** Account for stock-based compensation and outstanding options/warrants that will dilute shares.
6. **Currency mismatch:** Ensure cash flows and discount rate are in the same currency.
