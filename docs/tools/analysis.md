# Analysis Tools

## run_technical_analysis

Compute technical indicators and derive trading signals.

```
ticker: "AAPL"
```

Returns: RSI, EMA (20/50/200), Bollinger Bands, MACD, signals, overall bias.

## run_fundamental_analysis

Compute profitability, valuation, and stability ratios.

```
ticker: "AAPL"
sector: null          # optional: auto-detected if omitted
```

**Profitability:** ROE, ROA, ROIC, net margin, gross margin.

**Valuation:** P/E, P/B, EV/EBITDA, FCF yield, dividend yield.

**Stability:** D/E, current ratio, interest coverage.

Includes sector comparison when sector is detected.

## run_risk_analysis

Compute volatility, Value at Risk, and correlation matrix for one or more tickers.

```
tickers: ["AAPL", "MSFT"]
period: "1y"
```

Returns: per-ticker volatility (30d/90d/252d), VaR (95%/99%), pairwise correlation matrix.

## run_portfolio_analysis

Analyze a portfolio with correlation-adjusted position sizing.

```
tickers: ["AAPL", "MSFT", "GOOGL"]
period: "1y"
```

Returns per-ticker recommendations, correlation matrix, adjusted position sizes, total allocation.

Position sizing: volatility cap (5–25%) x confidence x signal multiplier x technical alignment. Correlation adjustment: max pairwise |corr| → multiplier (0.70–1.10).
