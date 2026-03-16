---
name: technical-screen
description: "Run technical analysis on a stock to identify trends, momentum, and actionable signals. Use this skill whenever the user asks for technical screening, chart analysis, trend analysis, or mentions specific indicators like RSI, MACD, EMA, SMA, Bollinger Bands, moving averages, support/resistance, overbought/oversold, golden cross, death cross. Trigger on phrases like 'is AAPL overbought?', 'what's the trend on Tesla?', 'show me the technicals for MSFT', 'RSI of SBER', 'технический анализ', 'тренд акции', 'уровни поддержки', 'перекупленность'. Also trigger when the user wants to time an entry/exit, asks about short-term signals, or wants chart-based analysis."
---

# Technical Screen

Perform technical analysis on a stock using fin-toolkit MCP tools to identify trends, momentum, support/resistance, and actionable signals.

## Tool Reference

See `_shared/mcp-tools-reference.md` for full MCP tool signatures and provider routing.

## Workflow

### 1. Fetch Data

```
get_stock_data(ticker, period="1y")
run_technical_analysis(ticker)
```

`run_technical_analysis` computes: RSI (14), EMA (20/50/200), MACD (12/26/9), Bollinger Bands (20, 2σ), trend signals, and overall bias.

For shorter-term analysis, user may request `period="3m"` or `period="6m"` for prices — but technical indicators are always computed on available history by the tool.

### 2. Interpret Signals

#### Trend
- **Bullish**: price > EMA 50 > EMA 200 (golden cross territory)
- **Bearish**: price < EMA 50 < EMA 200 (death cross territory)
- **Neutral**: mixed — price oscillating around moving averages

#### Momentum
- **RSI**: <30 oversold (potential bounce), >70 overbought (potential pullback), 30-70 neutral
- **MACD**: signal line crossover direction, histogram magnitude and acceleration
- Look for **divergences** — price making new highs while RSI makes lower highs = bearish divergence

#### Volatility
- **Bollinger Bands**: price near upper = potential resistance, near lower = potential support. Band squeeze (narrowing) often precedes a breakout.
- Compare current volatility to historical average from `run_risk_analysis(tickers=[ticker])` if additional context is needed.

#### Volume (if available in price data)
- Rising volume confirming price direction = strong signal
- Price move on declining volume = weak/suspect signal

### 3. Identify Key Levels

- **Support**: recent lows, EMA 50/200 acting as floor, lower Bollinger Band
- **Resistance**: recent highs, EMA levels acting as ceiling, upper Bollinger Band

### 4. Optional: Combine with Agent View

For a more complete picture, add fundamental context:
```
run_recommendation(ticker)
```

This gives a combined technical + fundamental signal with position size and stop-loss.

## Output Structure

### 1. Overview
Ticker, current price, 1D/1W/1M/3M/1Y price change. Overall trend direction.

### 2. Technical Indicators Table

| Indicator | Value | Signal |
|-----------|-------|--------|
| EMA 20 | $XXX | Above/Below price |
| EMA 50 | $XXX | Above/Below price |
| EMA 200 | $XXX | Above/Below price |
| RSI (14) | XX | Overbought/Oversold/Neutral |
| MACD | X.XX | Bullish/Bearish crossover |
| Bollinger Position | Upper/Mid/Lower | Interpretation |

### 3. Key Signals
2-3 most significant signals. Note any divergences.

### 4. Support & Resistance
- Nearest support levels
- Nearest resistance levels
- Which EMAs are acting as dynamic S/R

### 5. Actionable Takeaway
One paragraph: what the technicals suggest, timeframe context (short vs medium term), and caveat that technical analysis is probabilistic.

## Edge Cases

- **Low-liquidity stocks** (KASE, small Russian tickers): technical indicators are less reliable. Wider spreads and thin volume distort signals. State this caveat.
- **Recently IPO'd stocks**: not enough history for 200-day EMA. Note which indicators are unavailable.
- **Crypto/ETFs**: `run_technical_analysis` works on any ticker Yahoo Finance supports.
- **Russian tickers**: prices come from MOEX provider. Technicals should work but with MOEX trading hours context.
