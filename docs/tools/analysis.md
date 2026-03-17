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

**Valuation:** P/E, P/B, EV/EBITDA, FCF yield, dividend yield. Fallback: when metrics are unavailable, computes P/E from market_cap/net_income, P/B from market_cap/equity, EV from market_cap + debt - cash.

**Stability:** D/E, current ratio, interest coverage.

Includes sector comparison when sector is detected. For KASE tickers, ratios come from StockAnalysis (KZT-consistent).

## get_analyst_estimates

Get Wall Street analyst target prices, ratings, and earnings history.

```
ticker: "KSPI"
```

**Target prices:** low, median, mean, high — analyst consensus price targets.

**Ratings:** recommendation (buy/hold/sell), recommendation score (1.0–5.0), number of analysts covering.

**Forward estimates:** forward P/E, forward EPS.

**Earnings history:** up to 24 quarters of EPS estimate vs actual with surprise %. Shows whether the company consistently beats or misses expectations.

Data sourced from Yahoo Finance. Works best for US and dual-listed stocks (e.g. KSPI on NASDAQ). KASE-only tickers (HSBK, CCBN) will return an error since Yahoo doesn't cover them.

Automatically included in `generate_investment_idea` and `deep_dive` results.

!!! note "Dual-listed caveats"
    For dual-listed tickers like KSPI, `forward_pe` may be unreliable (Yahoo divides KZT EPS by USD price). Use `forward_eps` and current price to compute manually.

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
