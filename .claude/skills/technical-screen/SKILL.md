---
name: technical-screen
description: "Run technical analysis on a stock. Use when the user asks for technical screening, chart analysis, RSI, MACD, or trend analysis."
---

# Technical Screen Skill

Perform technical analysis on a stock using fin-toolkit MCP tools to identify trends, momentum, and actionable signals.

## Prerequisites

- fin-toolkit MCP server running (`fin-toolkit serve`)
- Valid API keys configured for the data provider

## Workflow

### Step 1: Fetch Historical Price Data

```
get_stock_data(ticker, period="1y")
```

Retrieve at least 1 year of daily OHLCV data. For shorter-term analysis, the user may request `period="3mo"` or `period="6mo"`.

**Error handling:** If `get_stock_data` fails, verify the ticker is valid and the MCP server is running. Some tickers (OTC, foreign) may not be available from all providers.

### Step 2: Run Technical Analysis

```
run_technical_analysis(ticker)
```

This computes standard technical indicators. Extract from the result:

- **Trend indicators:** SMA (50-day, 200-day), EMA (12, 26)
- **Momentum indicators:** RSI (14-day), MACD (12/26/9), Stochastic Oscillator
- **Volatility indicators:** Bollinger Bands (20-day, 2 std), ATR (14-day)
- **Volume indicators:** OBV, Volume SMA

**Error handling:** If `run_technical_analysis` returns partial data (e.g., missing some indicators), note which indicators are unavailable and proceed with what is available.

### Step 3: Interpret Signals

Analyze each indicator category and determine its signal:

#### Trend Assessment
- **Bullish:** Price above 50-day SMA, 50-day SMA above 200-day SMA (golden cross territory)
- **Bearish:** Price below 50-day SMA, 50-day SMA below 200-day SMA (death cross territory)
- **Neutral:** Mixed signals, price oscillating around SMAs

#### Momentum Assessment
- **RSI:** Below 30 = oversold (potential buy), above 70 = overbought (potential sell), 30-70 = neutral
- **MACD:** Signal line crossover bullish/bearish, histogram direction and magnitude
- **Stochastic:** Below 20 = oversold, above 80 = overbought

#### Volatility Assessment
- **Bollinger Bands:** Price near upper band = potential resistance, near lower band = potential support, bandwidth expansion = increasing volatility
- **ATR:** Compare current ATR to historical average — elevated ATR suggests heightened volatility

#### Volume Assessment
- **OBV trend:** Rising OBV confirms price uptrend, falling OBV confirms downtrend
- **Volume vs average:** Above-average volume on up days is bullish; above-average volume on down days is bearish

### Step 4: Present Summary

Compile findings into a structured, actionable report.

## Output Format

### 1. Overview
- Ticker, current price, price change (1D, 1W, 1M, 3M, 6M, 1Y)
- Current trend direction (Bullish / Bearish / Neutral)

### 2. Technical Indicators Table

| Indicator | Value | Signal |
|-----------|-------|--------|
| SMA 50 | $XXX | Above/Below price |
| SMA 200 | $XXX | Above/Below price |
| RSI (14) | XX | Overbought/Oversold/Neutral |
| MACD | X.XX | Bullish/Bearish crossover |
| Bollinger Band Position | Upper/Mid/Lower | Interpretation |
| ATR (14) | $X.XX | High/Normal/Low volatility |
| OBV Trend | Rising/Falling | Confirming/Diverging |

### 3. Key Signals
- List the 2-3 most significant signals and what they suggest
- Note any divergences (e.g., price rising but RSI falling)

### 4. Support and Resistance Levels
- Nearest support level(s)
- Nearest resistance level(s)
- Key SMA levels acting as support/resistance

### 5. Actionable Takeaway
- One-paragraph plain-language summary of what the technicals suggest
- Timeframe context (short-term vs medium-term outlook)
- Clear caveat that technical analysis is probabilistic, not predictive

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| MCP tool calls fail | fin-toolkit server not running | Run `fin-toolkit serve` in a separate terminal |
| "API key not found" | Missing provider API key | Check fin-toolkit configuration for required API keys |
| Insufficient data for indicators | Stock recently IPO'd or data period too short | Use a longer period or note that indicators requiring 200 days of data are unavailable |
| Flat/meaningless indicators | Low-liquidity stock with sparse trading | Warn user that technical analysis is less reliable for illiquid stocks |
| Provider error or timeout | API rate limits or downtime | Retry after a short wait; check provider status |
