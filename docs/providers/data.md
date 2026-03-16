# Data Providers

fin-toolkit uses a **routing layer** to resolve data sources automatically. The `ProviderRouter` checks: explicit provider → market mapping (from config) → primary → fallback chain.

## Provider Matrix

| Provider | Markets | API Key | Prices | Financials | Metrics |
|----------|---------|---------|--------|------------|---------|
| Yahoo Finance | Global | No | Yes | Yes | Yes |
| MOEX | Russia | No | Yes | No | Partial |
| KASE | Kazakhstan | No | Via Yahoo `.ME` | No | Yes |
| SmartLab | Russia | No | No | Yes | Yes |
| Financial Datasets | US | Yes | Yes | Yes | Yes |
| SEC EDGAR | US | No | No | Yes | Yes |
| PDF Reports | Any | No | No | Yes | No |

## Yahoo Finance

Default provider. Free, no API key. Covers global markets.

- Historical OHLCV via `yfinance`
- Financial statements: income, balance sheet, cash flow (+ history)
- Key metrics: P/E, P/B, EV/EBITDA, FCF yield, ROE, ROA, ROIC, margins

## MOEX (Moscow Exchange)

Open REST API via `aiomoex` + `aiohttp`. No auth required.

- **Prices**: daily candles via `aiomoex.get_market_candles()`
- **Metrics**: PREVPRICE, ISSUESIZE from board securities (P/E, financials unavailable)
- **Financials**: not available (use SmartLab)
- `list_tickers(board="TQBR")` fetches all traded tickers

## KASE (Kazakhstan Stock Exchange)

JSON API (`kase.kz/api/*`), no auth.

- **Metrics**: market cap, P/E, dividend yield from KASE API
- **Prices**: delegated to Yahoo Finance via `{ticker}.ME` suffix
- **Financials**: not available
- Works for dual-listed KASE+MOEX tickers (KCEL, HSBK); tickers like KZAP (LSE only) will fail for prices

## SmartLab

Scraper for `smart-lab.ru` — Russian market fundamentals.

- **Metrics**: P/E, P/B, EV/EBITDA, ROE from `/q/shares_fundamental/`
- **Financials**: IFRS statements from `/q/{TICKER}/f/y/MSFO/` (income/balance/cashflow + history)
- **Prices**: not supported (use MOEX)
- Values in tables: billions (×1e9), shares in millions (×1e6)

## Financial Datasets

REST API (`api.financialdatasets.ai`). US equities only, 17k+ tickers, 30+ years.

- Requires `FINANCIAL_DATASETS_API_KEY` env var
- Full prices, financials, and metrics from SEC EDGAR data

## SEC EDGAR

US financial statements from XBRL filings via `edgartools`. No API key.

- Only `get_financials` and `get_metrics` — no prices
- Data from official SEC XBRL filings

## PDF Reports

Parse financial report PDFs via `pdfplumber`.

- Works with English and Russian (IFRS/MSFO) reports
- Bilingual field mapping: "Выручка" → "revenue", "Чистая прибыль" → "net_income"
- Exposed as `parse_report` MCP tool

## Russian Market Strategy

| Need | Provider | Why |
|------|----------|-----|
| Prices (SBER, GAZP, etc.) | MOEX | Official exchange data |
| Fundamentals (P/E, ROE) | SmartLab | Scrapes comprehensive data |
| Financial statements | SmartLab | IFRS/MSFO from smart-lab.ru |
| Screening | MOEX + SmartLab | Tickers from MOEX, metrics from SmartLab |
