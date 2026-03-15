# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## MCP Server

This project IS an MCP server built on FastMCP. Run `fin-toolkit serve` to start.

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

### Exception hierarchy

All exceptions inherit from `FinToolkitError` (`exceptions.py`). Key subtypes: `TickerNotFoundError`, `ProviderUnavailableError`, `AllProvidersFailedError`, `InsufficientDataError`, `AgentNotFoundError`.

### Config resolution

Priority: env vars → `.env` → `./fin-toolkit.yaml` → `~/.config/fin-toolkit/config.yaml` → defaults.

## Testing

- TDD: write tests first
- Mock providers in unit tests; never hit real APIs without `@pytest.mark.live`
- Tests mirror source structure: `tests/test_providers/`, `tests/test_analysis/`, etc.
- `asyncio_mode = "auto"` in pytest config — no need for `@pytest.mark.asyncio`
- Coverage target: 80% (enforced by `fail_under` in pyproject.toml)

## Code style

- Python 3.11+, strict mypy, ruff with `E,F,I,N,W,UP,B,SIM` rules
- Line length: 100
- `from __future__ import annotations` in every module
- All provider/agent methods are async
