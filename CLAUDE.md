# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## MCP Server

This project IS an MCP server built on FastMCP. Run `fin-toolkit serve` to start.

- CLI is infrastructure-only (`serve`, `setup`, `status`) — all financial analysis is exposed exclusively via MCP tools
- `fin-toolkit setup` registers the server in `.mcp.json` (local) or `~/.claude.json` (with `--global`)
- MCP entry uses `uv run --project <path>` (NOT `uvx` — package is not on PyPI)
- `fin-toolkit status` shows provider/agent availability

## Development

- `mise install && uv sync` to set up
- `uv run pytest` to run all tests
- `uv run pytest tests/test_providers/test_yahoo.py::test_get_prices` to run a single test
- `uv run pytest --cov` to run with coverage (fails under 80%)
- `uv run pytest -m live` for tests hitting real APIs
- `uv run mypy fin_toolkit/` for type checking (strict mode)
- `uv run ruff check` for linting
- `uv run ruff check --fix` to auto-fix lint issues
- hatchling requires `[tool.hatch.metadata] allow-direct-references = true` for git-based dependencies

## Architecture

### yfinance data quirks

- `Ticker.financials`/`.balance_sheet`/`.cashflow` DataFrames: columns=dates, index=field names (e.g. "Total Revenue", not "revenue")
- `_df_to_dict()` in `yahoo.py` normalizes to flat `{field: value}` using `_FIELD_MAP`
- `enterprise_value` lives in `.info["enterpriseValue"]`, NOT in balance_sheet DataFrame
- Some fields are NaN for certain tickers (e.g. AAPL has no Interest Expense) — this is a data limitation, not a bug
- 1 calendar year ≈ 250 trading days; period mapping uses 400 days buffer for 252-window volatility
- `_df_to_history(df)` in `yahoo.py` converts ALL columns to `list[dict]` for historical trends; columns may be datetime or string (in mocks) — check `hasattr(col, "strftime")`
- `KeyMetrics` extended fields: `ev_ebitda` (from `info["enterpriseToEbitda"]`), `fcf_yield` (computed: freeCashflow/marketCap), `shares_outstanding`, `current_price`
- `FinancialStatements` extended: `income_history`, `cash_flow_history` — list of period dicts from all DataFrame columns

### Protocol-first design

All major boundaries are `typing.Protocol` classes with `@runtime_checkable`:

- `DataProvider` (`providers/protocol.py`) — `get_prices`, `get_financials`, `get_metrics`
- `SearchProvider` (`providers/search_protocol.py`) — `search`
- `AnalysisAgent` (`agents/protocol.py`) — `analyze → AgentResult`

New providers/agents implement the protocol; no base class inheritance needed.

### Routing & fallback chains

- `ProviderRouter` resolves data sources in order: explicit provider → market mapping (config) → primary → fallbacks. All methods iterate the chain and raise `AllProvidersFailedError` if exhausted.
- `SearchRouter` does the same for search providers.

### MCP server wiring

`mcp_server/server.py` uses module-level globals initialized by `init_server()`. The CLI (`cli.py`) builds all dependencies (providers, analyzers, registry, watchlist store) and passes them to `init_server()` before calling `server.run()`.
- `init_server()` accepts optional `watchlist_store: WatchlistStore | None` — `cli.py` creates `WatchlistStore()` and passes it

All tools accept `format` param (`"toon"` | `"json"`, default: `"toon"`). TOON saves 30-60% tokens on tabular data. Errors always return JSON. Serialization logic in `mcp_server/serialize.py`.

### Analysis agents

- `elvis_marlamov` — 'Future Blue Chips' deep value + catalysts (valuation/quality/catalysts/financial_health). Uses `SearchProvider` for M&A/corporate event detection with bilingual EN/RU keywords
- `warren_buffett` — value investing with ROIC moat evidence (margin_of_safety/durable_advantage/management_quality)
- `ben_graham` — defensive value with Graham Number P/E×P/B<22.5 (net_net_value/earnings_stability/financial_strength)
- `charlie_munger` — wonderful business at fair price, ROIC-first (business_quality/fair_price/financial_fortress)
- `cathie_wood` — disruptive innovation, tolerates high P/E, rewards zero dividends (growth_signals/innovation_premium/market_position)
- `peter_lynch` — GARP with dividend-adjusted PEG (peg_value/earnings_quality/common_sense)
- New agents: implement `AnalysisAgent` protocol, add to registry `factories` dict + `_AGENT_FACTORIES`, list in config `agents.active`
- Agent scoring: each block has sub-metrics whose max sum may exceed block MAX; `min(MAX, score)` caps the block. This allows adding metrics without redistribution — preserve block names to avoid breaking tests.
- Available FundamentalResult metrics: profitability (roe, roa, roic, net_margin, gross_margin), valuation (pe_ratio, pb_ratio, ev_ebitda, fcf_yield, dividend_yield), stability (debt_to_equity, current_ratio, interest_coverage)

### Consensus & portfolio layer

- `analysis/portfolio.py` — pure functions (no async/IO): `compute_consensus`, `compute_position_size`, `compute_stop_loss`, `adjust_position_sizes`
- `_signal_from_score(score)` — shared threshold logic: ≥70 Bullish, ≥40 Neutral, <40 Bearish
- `_run_consensus(ticker)` and `_run_single_recommendation(ticker, start, end)` — private async helpers in `server.py`, reused by `run_all_agents`, `run_recommendation`, `run_portfolio_analysis`
- `AgentRegistry.get_active_agents()` returns all loaded agents; used by consensus to run them concurrently via `asyncio.gather(return_exceptions=True)`
- Position sizing: volatility cap (5-25%) × confidence × signal multiplier × technical alignment, capped at base
- Correlation adjustment: max pairwise |corr| → multiplier (0.70–1.10) applied to raw sizes

### Exception hierarchy

All exceptions inherit from `FinToolkitError` (`exceptions.py`). Key subtypes: `TickerNotFoundError`, `ProviderUnavailableError`, `AllProvidersFailedError`, `InsufficientDataError`, `AgentNotFoundError`, `InvalidFilterError`, `WatchlistError`.

### Config resolution

Priority: env vars → `.env` → `./fin-toolkit.yaml` → `~/.config/fin-toolkit/config.yaml` → defaults.
Config files are NOT merged — first found wins. API keys in global config are invisible if local config exists.
`_status()` uses `load_config()` + `available_providers()` — do not duplicate availability logic.

### Search provider chain

Fallback order: DuckDuckGo → SearXNG → Google → Perplexity → Tavily → Brave → Serper → Exa.
- Key-based: `GEMINI_API_KEY`, `PERPLEXITY_API_KEY`, `TAVILY_API_KEY`, `BRAVE_API_KEY`, `SERPER_API_KEY`, `EXA_API_KEY`
- Google: uses Gemini API with Search Grounding; model configurable via `search.gemini_model` (default: `gemini-3.1-flash-lite`)
- DuckDuckGo: always available, no API key (uses `ddgs` package, NOT `duckduckgo-search`)
- Uses `ddgs.news()` (not `ddgs.text()`) for articles with dates; falls back to `text()` if news fails/empty
- `ddgs.news()` may raise `DDGSException` on complex queries — catch inside provider, not at caller level
- SearXNG: self-hosted via Docker, `search.searxng_url` in config (default `http://localhost:8888`)
- New search provider: implement `SearchProvider` protocol (~50 LOC), add to `config/models.py` + `cli.py`
- Google search provider has extra `model` param — wired separately from generic key-based loop in `cli.py`

### Financial Datasets provider

- REST API (`api.financialdatasets.ai`), auth via `X-API-KEY` header, key env var: `FINANCIAL_DATASETS_API_KEY`
- API quirks: 301 redirects (needs `follow_redirects=True`), prices use `time` (ISO 8601) not `date`, metrics endpoint is `/financial-metrics/snapshot` (not `/financial-metrics`)
- Field rename mapping in `_FIELD_RENAME`: `net_cash_flow_from_operations` → `operating_cash_flow`, `price_to_earnings_ratio` → `pe_ratio` (via `get_metrics`)
- US equities only, 17k+ tickers, 30+ years history from SEC EDGAR

### MOEX ISS provider

- Open REST API (`iss.moex.com`), no auth, via `aiomoex` + `aiohttp` (NOT httpx)
- `get_prices`: daily candles via `aiomoex.get_market_candles()`
- `get_metrics`: PREVPRICE, ISSUESIZE from `aiomoex.get_board_securities()` — P/E, financials unavailable
- `get_financials`: returns None (ISS has no financial statements)
- `list_tickers(board="TQBR")`: fetches all traded SECID from board
- Board mapping: TQBR (equities, default), TQCB (bonds)

### SEC EDGAR provider

- US financial statements from XBRL via `edgartools` (PyPI, no API key)
- Only `get_financials` and `get_metrics` — no prices (raises `ProviderUnavailableError`)
- `from edgar import Company` is lazy-imported inside `_fetch_financials` (runs in thread via `asyncio.to_thread`)
- `filings.latest()` may return single object or list — use `isinstance(latest, (list, tuple))`

### PDF report parser

- `providers/pdf_report.py`: extracts financial tables from PDF via `pdfplumber`
- Bilingual field mapping (EN + RU МСФО): "Выручка" → "revenue", "Чистая прибыль" → "net_income"
- Classification heuristic: counts overlapping field names to assign tables to income/balance/cashflow
- Exposed as MCP tool `parse_report(source, ticker)`

### SmartLab provider

- Scraper for `smart-lab.ru` — Russian market fundamentals (P/E, P/B, EV/EBITDA, ROE) + IFRS financial statements
- `get_metrics`: parses `/q/shares_fundamental/` table (one page = all MOEX tickers)
- `get_financials`: parses `/q/{TICKER}/f/y/MSFO/` per-ticker page (income/balance/cashflow + history)
- `get_prices`: not supported — use MOEX provider for prices
- Values in tables are in млрд руб — multiply by `1e9` to convert to absolute; shares in млн → `1e6`
- No API, no auth — server-rendered HTML, `httpx` + `beautifulsoup4`
- Rate limit: polite 5 req/min to avoid blocks
- SmartLab field names use `field=` attribute on `<tr>` tags (e.g. `field="revenue"`, `field="p_e"`)
- Banks have different fields (e.g. `bank_assets` instead of `assets`, `capital` instead of `net_assets`)

### Russian market provider strategy

- Prices: MOEX ISS (`provider="moex"`) — always use for SBER, GAZP, LKOH etc.
- Fundamentals (P/E, ROE, financials): SmartLab (`provider="smartlab"`) — scrapes smart-lab.ru
- Yahoo Finance requires `.ME` suffix for Moscow Exchange tickers (e.g. `SBER.ME`)
- `screen_stocks(market="moex")` fetches tickers from MOEX ISS, metrics from SmartLab via fallback chain

### Investment idea & screening layer

- `analysis/idea.py` — pure functions (no async/IO): `compute_cagr`, `compute_fcf_waterfall`, `compute_scenarios`, `classify_catalysts`, `detect_risks`
- `analysis/screening.py` — `compute_quick_score(metrics)`: 0-100 from P/E, P/B, EV/EBITDA, FCF yield, D/E, div yield, ROE; `parse_filter(expr)` + `matches_filters(metrics, filters)` for custom screener filters (operators: `<`, `>`, `<=`, `>=`, `=`, `min..max`)
- `report/html_report.py` — self-contained HTML with Plotly charts (CDN), dark theme, 13 sections with EN/RU toggle (JS-based, zero reload)
- `report/i18n.py` — `LangPair` dataclass, `HEADERS`/`SIGNALS`/`METRIC_LABELS`/`DISCLAIMER` dicts, `i18n_span()` for HTML, `currency_symbol(ticker)` (₽/₸/$), `fmt_price()`
- `report/narrative.py` — template-based (no LLM) thesis/FCF/target narratives: `generate_thesis()`, `generate_fcf_narrative()`, `generate_target_summary()` → `LangPair`
- MCP tools: `generate_investment_idea` (html/json/toon), `screen_stocks` (two-stage + optional `filters` param), `parse_report`
- `generate_investment_idea` default format is `"html"` (not `"toon"`) — opens browser via `webbrowser.open()`
- Catalyst search: use broad query `"{ticker} stock news {year}"` with max_results=10, NOT narrow `"acquisition buyback"` — narrow queries return other tickers' results
- `classify_catalysts()` keyword categories: m_and_a, buyback, restructuring (incl. layoffs), index, strategic (incl. deals/capex/infrastructure), growth, innovation (incl. AI), dividend
- `_fmt_large()` in `html_report.py` hardcodes `$` prefix — should use `currency_symbol(ticker)` for RU/KZ tickers (known tech debt)

### Watchlist & alerts

- `watchlist.py` — `WatchlistStore` class: YAML-backed persistent storage at `~/.config/fin-toolkit/watchlists.yaml`
- `analysis/alerts.py` — `AlertRule` and `WatchlistEntry` dataclasses + `evaluate_alerts()` pure function
- Alert metrics routed to source: KeyMetrics (pe_ratio, roe, etc.), RiskResult (volatility_30d, var_95), TechnicalResult (rsi, ema_20)
- MCP tools: `manage_watchlist` (add/remove/list/show), `set_alert`, `check_watchlist`

### Deep dive & comparison

- `deep_dive` MCP tool: batch analysis for 1-10 tickers, concurrent fetch per ticker via `_deep_dive_single()`, partial failures → item-level warnings
- `analysis/comparison.py` — `build_comparison_matrix(ticker_data, metrics)`: builds `{metric: {ticker: value}}` matrix from `ComparisonInput`
- `compare_stocks` MCP tool: 2-10 tickers, fetches metrics/risk/consensus concurrently, delegates to `build_comparison_matrix()`
- New models in `results.py`: `DeepDiveItem/Result`, `ComparisonInput/Result`, `AlertTriggered`, `WatchlistCheckResult`, `WatchlistInfo`, `ScreeningResult.filters_applied`

### KASE provider

- JSON API (`kase.kz/api/*`), no auth, no API key needed
- Two-layer design: `_KASEClient` (HTTP client) + `KASEProvider` (protocol adapter)
- Historical OHLCV: delegated to Yahoo Finance via `{ticker}.ME` suffix (KASE API has no history endpoint)
- `get_metrics()` maps KASE fields (`capit` → `market_cap`, `pe` → `pe_ratio`, etc.); `get_financials()` returns None (no reporting data)
- `KASEProvider(yahoo=providers.get("yahoo"))` — Yahoo instance passed from `cli.py`
- Yahoo `.ME` fallback works only for dual-listed KASE+MOEX tickers (KCEL, HSBK); tickers like KZAP (LSE only as KAP.IL) have no MOEX listing — `get_prices` will fail for them
- `DEFAULT_MARKETS["kz"].tickers` in `config/models.py` controls which tickers route to KASE provider — keep this list updated

## Testing

- TDD: write tests first
- Mock providers in unit tests; never hit real APIs without `@pytest.mark.live`
- Mock financial data must match real yfinance structure (flat dict with normalized keys from `_FIELD_MAP`, not raw yfinance names)
- Tests mirror source structure: `tests/test_providers/`, `tests/test_analysis/`, etc.
- `asyncio_mode = "auto"` in pytest config — no need for `@pytest.mark.asyncio`
- Coverage target: 80% (enforced by `fail_under` in pyproject.toml)
- MCP tool tests that parse responses with `json.loads()` must pass `format="json"` (default is TOON)
- `_mock_registry_with_agents(dict)` in `test_tools.py` — helper to build mock registry with agents returning given results/exceptions
- Portfolio pure functions in `test_portfolio.py` are tested without mocks (no I/O); MCP tool tests mock `_agent_registry`, `_provider_router`, `_technical_analyzer`
- MOEX tests: patch `aiomoex` module AND `aiohttp.ClientSession` context manager
- EDGAR tests: use `SimpleNamespace` (not MagicMock) for XBRL objects — `float(MagicMock())` silently returns 1.0
- EDGAR tests: patch `"edgar.Company"` with `create=True` (lazy import inside static method)
- Watchlist tests use `tmp_path` fixture for isolated YAML storage — `WatchlistStore(path=tmp_path / "w.yaml")`
- `deep_dive` partial failures: price/financials/metrics fail independently → warnings in `DeepDiveItem.warnings`, NOT batch-level `DeepDiveResult.warnings`
- Comparison/alerts are pure functions — tested without mocks, same as portfolio functions

## Code style

- Python 3.11+, strict mypy, ruff with `E,F,I,N,W,UP,B,SIM` rules
- Line length: 100
- `from __future__ import annotations` in every module
- All provider/agent methods are async
- For strict mypy with JSON API wrappers: use `dict(data)` (not `cast`) to convert `Any` returns to `dict[str, Any]`
