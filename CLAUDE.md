# fin-toolkit

## MCP Server
This project IS an MCP server. Run `fin-toolkit serve` to start.

## Development
- `mise install && uv sync` to set up
- `uv run pytest` to test
- `uv run mypy fin_toolkit/` for type checking
- `uv run ruff check` for linting

## Architecture
- Protocol-first: DataProvider, SearchProvider, AnalysisAgent
- Providers: Yahoo Finance (free), KASE scraper, Brave Search, SearXNG
- Analysis: Technical (ta), Fundamental (sector medians), Risk (VaR, Kelly)
- Agents: Elvis Marlamov (100-point scoring), Warren Buffett (value investing)
- MCP Tools: get_stock_data, run_technical_analysis, run_fundamental_analysis, run_risk_analysis, search_news, run_agent

## Testing
- TDD: write tests first
- Mock providers in unit tests
- `pytest -m live` for real API tests (optional)
- Coverage target: 80%
