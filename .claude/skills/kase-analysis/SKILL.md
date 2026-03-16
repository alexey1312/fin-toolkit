---
name: kase-analysis
description: "Analyze stocks listed on the Kazakhstan Stock Exchange (KASE). Use this skill whenever the user mentions KASE, Kazakhstan market, Kazakhstani stocks, or any of these tickers: KCEL, KZTO, HSBK, CCBN, KEGC, KZAP. Also trigger on phrases like 'analyze Halyk Bank', 'Kcell stock', 'KazTransOil', 'ForteBank', 'KEGOC', 'казахстанские акции', 'акции KASE', 'биржа Казахстана', or when the user asks about tenge-denominated investments, Central Asian equities, or frontier market analysis in the CIS region."
---

# KASE Analysis

Analyze stocks listed on the Kazakhstan Stock Exchange using fin-toolkit MCP tools, accounting for KASE-specific data constraints and market context.

## Tool Reference

See `_shared/mcp-tools-reference.md` for full MCP tool signatures and provider routing.

## KASE Tickers

| Ticker | Company | Sector | Notes |
|--------|---------|--------|-------|
| HSBK | Halyk Bank | Banking | Largest bank, most liquid KASE stock |
| KCEL | Kcell | Telecom | Mobile operator (Kazakhtelecom subsidiary) |
| KZTO | KazTransOil | Oil & Gas | Oil pipeline monopoly |
| KEGC | KEGOC | Utilities | Power grid operator |
| CCBN | ForteBank | Banking | Second-tier bank |
| KZAP | KAP (Kazatomprom) | Mining/Nuclear | LSE-listed as KAP.IL — no MOEX listing, prices may fail |

## Provider Routing for KASE

KASE tickers auto-route via market mapping (`kz` → `kase` provider):

| Data Type | Provider | What You Get | Limitations |
|-----------|----------|-------------|-------------|
| **Prices** | KASE → Yahoo (`.ME` suffix) | Historical OHLCV | Only works for dual-listed KASE+MOEX tickers (KCEL, HSBK). KZAP will fail. |
| **Metrics** | KASE API | Market cap, P/E, P/B, dividend yield | Real-time snapshot, no history |
| **Financials** | Not available | — | KASE API has no financial statements |

When `get_stock_data(ticker)` is called for a KASE ticker, the router automatically uses the KASE provider. No need to pass `provider="kase"` explicitly.

## Workflow

### 1. Fetch Data

```
get_stock_data(ticker, period="1y")
run_fundamental_analysis(ticker)
run_technical_analysis(ticker)
```

Expect partial data — KASE coverage is sparser than US markets. Proceed with whatever comes back.

**Likely outcomes:**
- `get_stock_data` — works for HSBK, KCEL, KZTO (via Yahoo `.ME`). May fail for KZAP.
- `run_fundamental_analysis` — returns KASE metrics (P/E, P/B, market cap). No full financial statements.
- `run_technical_analysis` — works if price data was fetched. Low-liquidity caveats apply.

### 2. Interpret with KASE Context

KASE is a frontier market — standard analysis frameworks need adjustment:

#### Macro Factors
- **KZT currency risk**: tenge volatility directly impacts real returns for foreign investors. NBK interventions can be sudden.
- **Oil dependency**: Kazakhstan GDP is ~25% oil/gas. Oil price moves affect the entire market, not just energy stocks.
- **Interest rates**: NBK base rate affects banking margins (HSBK, CCBN) and all valuations.
- **Geopolitics**: Russia/China/Central Asia dynamics. Sanctions spillover risk from Russia.

#### Market Structure
- **Low liquidity**: daily volumes are thin. Technical indicators are less reliable.
- **Concentration**: top 3 stocks (HSBK, KCEL, KZTO) dominate turnover.
- **High dividends**: KASE blue chips often yield 5-10%+. This is a feature, not a distortion.
- **Limited coverage**: minimal sell-side research. Information asymmetry is real.

#### Sector Notes
- **Banking (HSBK, CCBN)**: interest rate sensitivity, loan book quality, KZT rate moves
- **Telecom (KCEL)**: subscriber growth, ARPU, regulatory environment, Kazakhtelecom ownership
- **Oil & Gas (KZTO)**: pipeline volumes, tariff regulation, oil price linkage
- **Utilities (KEGC)**: regulated tariffs, transmission volumes, government policy
- **Mining (KZAP)**: uranium prices, global nuclear energy demand, Samruk-Kazyna state ownership

### 3. Supplement with News

```
search_news("{ticker} Kazakhstan stock {year}")
```

Use broad queries — narrow KASE-specific queries often return empty results.

### 4. Optional: Agent Analysis

For deeper qualitative assessment:
```
run_all_agents(ticker)
```

Agent scores will reflect data limitations — interpret with lower confidence than US stocks.

## Output Structure

### 1. Company Overview
- Company name, KASE ticker, sector
- Current price (KZT) + approximate USD equivalent
- Market cap, dividend yield
- **Data availability note**: explicitly state what data was and wasn't available

### 2. Price Performance
- Returns in KZT terms (1M, 3M, 6M, 1Y)
- Note if price data is stale (last trade may be days old for illiquid names)

### 3. Technical Summary (if available)
- Key indicators and signals
- Caveat: "Technical indicators are less reliable due to low liquidity and wide spreads"

### 4. Fundamental Summary (if available)
- P/E, P/B, dividend yield, market cap
- Comparison to sector norms (KASE valuations tend to be lower than developed markets)

### 5. Kazakhstan Market Context
- Relevant macro factors for this specific stock
- Sector dynamics
- Currency/liquidity/regulatory risks

### 6. Assessment
- Overall view with **confidence level** (high/medium/low based on data completeness)
- Key catalysts and risks to watch
- Clear statement of data limitations

## Edge Cases

- **KZAP (Kazatomprom)**: LSE-listed as KAP.IL, not on MOEX. `get_stock_data` will likely fail. Inform user and suggest looking up LSE data manually.
- **Missing fundamentals**: KASE API provides basic metrics but no financial statements. If user needs deeper analysis, suggest finding PDF annual reports and using `parse_report(source, ticker)`.
- **Currency display**: Prices are in KZT. Always state the currency. Use ~480 KZT/USD as approximate conversion (but check current rate context).
