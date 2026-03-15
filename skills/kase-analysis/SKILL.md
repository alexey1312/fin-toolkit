---
name: kase-analysis
description: "Analyze Kazakhstan stock exchange (KASE) stocks. Use when the user asks about KCEL, KZTO, HSBK, or Kazakhstan market stocks."
---

# KASE Analysis Skill

Analyze stocks listed on the Kazakhstan Stock Exchange (KASE) using fin-toolkit MCP tools, with awareness of KASE-specific data limitations and market context.

## Prerequisites

- fin-toolkit MCP server running (`fin-toolkit serve`)
- Valid API keys configured for the data provider
- Note: KASE data availability varies significantly by provider. The `kase` provider is recommended.

## Common KASE Tickers

| Ticker | Company | Sector |
|--------|---------|--------|
| HSBK | Halyk Bank | Banking |
| KCEL | Kcell | Telecom |
| KZTO | KazTransOil | Oil & Gas |
| KEGC | KEGOC | Energy/Utilities |
| CCBN | ForteBank | Banking |

## Workflow

### Step 1: Fetch Stock Data with KASE Provider

```
get_stock_data(ticker, provider="kase")
```

Retrieve available historical price data. KASE stocks may have:
- Shorter history than US equities
- Lower trading frequency (some days with no trades)
- Prices in KZT (Kazakhstani tenge)

**Error handling:** If the `kase` provider is not available or returns an error, try without the provider parameter (default provider). If the ticker is not found, check that the user is using the correct KASE ticker symbol. Some KASE stocks may also trade as GDRs on the London Stock Exchange (e.g., HSBK as HSBK.L).

### Step 2: Run Available Analysis

Attempt both analysis types:

```
run_technical_analysis(ticker)
run_fundamental_analysis(ticker)
```

**Important KASE data caveats:**
- Technical indicators may be less reliable due to lower liquidity and wider bid-ask spreads
- Fundamental data may be less standardized than US GAAP/IFRS reporting from major providers
- Some financial ratios may be missing or computed differently

**Error handling:** If either analysis tool returns limited or no data, inform the user clearly. Do not fabricate or assume missing data points. Proceed with whatever is available.

### Step 3: Apply Kazakhstan Market Context

When interpreting results, factor in KASE-specific considerations:

#### Macroeconomic Context
- **Currency risk:** KZT can be volatile against USD; significant tenge depreciation affects real returns for foreign investors
- **Oil dependency:** Kazakhstan's economy is heavily oil-dependent; oil price swings affect the entire market, not just energy stocks
- **Interest rates:** National Bank of Kazakhstan base rate influences banking stocks and overall market valuations
- **Geopolitical factors:** Regional dynamics (Russia, China, Central Asia) affect investor sentiment

#### Market Structure
- **Liquidity:** KASE is a frontier/small emerging market; daily volumes are low compared to developed markets
- **Concentration:** The market is dominated by a few large-cap names (HSBK, KCEL, KZTO)
- **Information asymmetry:** Less analyst coverage and fewer publicly available research reports
- **Dividend culture:** Many KASE blue chips pay relatively high dividends

#### Sector-Specific Notes
- **Banking (HSBK, CCBN):** Sensitive to KZT interest rates, loan growth, and asset quality
- **Telecom (KCEL):** Subscriber growth, ARPU trends, regulatory environment
- **Oil & Gas (KZTO):** Pipeline volumes, oil price, government tariff regulation
- **Utilities (KEGC):** Regulated tariffs, transmission volumes, government policy

### Step 4: Present Analysis

Compile findings with appropriate caveats about data completeness.

## Output Format

### 1. Company Overview
- Company name, KASE ticker, sector
- Current price (KZT), approximate USD equivalent
- Market cap, daily average volume
- Data availability note (what was and was not available)

### 2. Price Performance
- Available return periods (1M, 3M, 6M, 1Y) in KZT terms
- USD-adjusted returns if exchange rate data is available
- Comparison to KASE index if available

### 3. Technical Summary (if available)
- Key indicators and signals
- Caveat about low-liquidity impact on technical reliability

### 4. Fundamental Summary (if available)
- Key ratios: P/E, P/B, dividend yield, ROE
- Revenue and earnings trends
- Balance sheet highlights

### 5. Kazakhstan Market Context
- Relevant macro factors affecting this stock
- Sector-specific considerations
- Known risks (currency, liquidity, regulatory)

### 6. Assessment
- Overall view with confidence level (high/medium/low based on data availability)
- Key factors to watch
- Clear statement of data limitations

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| MCP tool calls fail | fin-toolkit server not running | Run `fin-toolkit serve` in a separate terminal |
| "API key not found" | Missing provider API key | Check fin-toolkit configuration for required API keys |
| Ticker not found | Wrong ticker format or provider does not cover KASE | Verify KASE ticker symbol; try alternative providers or GDR tickers |
| Very limited data | KASE coverage is sparse in many data providers | Inform user of limitations; provide what is available rather than nothing |
| No fundamental data | Provider does not have KASE financials | Suggest user manually provide key financials if they have access to KASE disclosure portal (kase.kz) |
| Currency confusion | Prices in KZT vs USD | Always state the currency; provide approximate USD conversion if possible |
| Stale prices | Low liquidity means last trade may be days old | Check the date of the most recent price data point and warn if stale |
