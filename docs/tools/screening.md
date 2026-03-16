# Screening & Ideas

## screen_stocks

Screen stocks by valuation score with optional consensus on top candidates.

```
tickers: ["AAPL", "MSFT", "GOOGL"]  # or use market
market: "moex"                        # auto-fetch tickers (moex, kase)
top_n: 10
filters: {"pe_ratio": "<15", "roe": ">0.10"}  # optional metric filters
```

Supported filter operators: `<`, `>`, `<=`, `>=`, `=`, `min..max` (range).

Two-stage process:

1. **Quick scoring** — concurrent metric fetch (`asyncio.gather` + `Semaphore(10)`) for all tickers
2. **Consensus** — concurrent agent analysis for top N candidates

For `market="kase"`, tickers are discovered dynamically (~87 actively traded shares). Progress is reported via MCP notifications during both stages.

## generate_investment_idea

Generate a comprehensive investment idea with charts.

```
ticker: "AAPL"
period: "2y"
format: "html"        # opens interactive HTML with Plotly charts
```

Returns: consensus, fundamentals, scenarios (bull/base/bear), FCF waterfall, catalysts, risks, price chart.

Default format is `"html"` — opens a self-contained HTML file in the browser with interactive Plotly charts, dark theme, and EN/RU toggle.

## parse_report

Parse a financial report PDF and extract structured data.

```
source: "https://example.com/report.pdf"  # URL or local path
ticker: "AAPL"
```

Works with English and Russian (IFRS/MSFO) reports. Extracts income statement, balance sheet, and cash flow data via `pdfplumber`.
