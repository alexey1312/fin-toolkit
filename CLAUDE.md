# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## MCP Server

This project IS an MCP server built on FastMCP. Run `fin-toolkit serve` to start.

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

## Architecture

### yfinance data quirks

- `Ticker.financials`/`.balance_sheet`/`.cashflow` DataFrames: columns=dates, index=field names (e.g. "Total Revenue", not "revenue")
- `_df_to_dict()` in `yahoo.py` normalizes to flat `{field: value}` using `_FIELD_MAP`
- `enterprise_value` lives in `.info["enterpriseValue"]`, NOT in balance_sheet DataFrame
- Some fields are NaN for certain tickers (e.g. AAPL has no Interest Expense) — this is a data limitation, not a bug
- 1 calendar year ≈ 250 trading days; period mapping uses 400 days buffer for 252-window volatility

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

`mcp_server/server.py` uses module-level globals initialized by `init_server()`. The CLI (`cli.py`) builds all dependencies (providers, analyzers, registry) and passes them to `init_server()` before calling `server.run()`.

### Analysis agents

- `elvis_marlamov` — fundamentals + sentiment scoring (quality/stability/valuation/sentiment)
- `warren_buffett` — value investing (margin of safety/durable advantage/management quality)
- `ben_graham` — deep value (net-net value/earnings stability/financial strength)
- `charlie_munger` — wonderful business at fair price (business quality/fair price/financial fortress)
- `cathie_wood` — innovation & growth (growth signals/innovation premium/market position)
- `peter_lynch` — GARP (PEG value/earnings quality/common sense)
- New agents: implement `AnalysisAgent` protocol, add to registry `factories` dict + `_AGENT_FACTORIES`, list in config `agents.active`

### Exception hierarchy

All exceptions inherit from `FinToolkitError` (`exceptions.py`). Key subtypes: `TickerNotFoundError`, `ProviderUnavailableError`, `AllProvidersFailedError`, `InsufficientDataError`, `AgentNotFoundError`.

### Config resolution

Priority: env vars → `.env` → `./fin-toolkit.yaml` → `~/.config/fin-toolkit/config.yaml` → defaults.

### Search provider chain

Fallback order: DuckDuckGo → SearXNG → Perplexity → Tavily → Brave → Serper → Exa.
- Key-based: `PERPLEXITY_API_KEY`, `TAVILY_API_KEY`, `BRAVE_API_KEY`, `SERPER_API_KEY`, `EXA_API_KEY`
- DuckDuckGo: always available, no API key (uses `ddgs` package, NOT `duckduckgo-search`)
- SearXNG: self-hosted via Docker, `search.searxng_url` in config (default `http://localhost:8888`)
- New search provider: implement `SearchProvider` protocol (~50 LOC), add to `config/models.py` + `cli.py`

## Testing

- TDD: write tests first
- Mock providers in unit tests; never hit real APIs without `@pytest.mark.live`
- Mock financial data must match real yfinance structure (flat dict with normalized keys from `_FIELD_MAP`, not raw yfinance names)
- Tests mirror source structure: `tests/test_providers/`, `tests/test_analysis/`, etc.
- `asyncio_mode = "auto"` in pytest config — no need for `@pytest.mark.asyncio`
- Coverage target: 80% (enforced by `fail_under` in pyproject.toml)

## Code style

- Python 3.11+, strict mypy, ruff with `E,F,I,N,W,UP,B,SIM` rules
- Line length: 100
- `from __future__ import annotations` in every module
- All provider/agent methods are async
