## ADDED Requirements

### Requirement: MCP server with FastMCP
The system SHALL provide an MCP server built with FastMCP that exposes financial analysis capabilities as MCP tools. The server SHALL be launchable via `fin-toolkit serve` and manageable as a pitchfork daemon.

#### Scenario: Start MCP server via CLI
- **WHEN** `fin-toolkit serve` is executed
- **THEN** the server SHALL start on stdio transport and be connectable from Claude Code via `.mcp.json`

#### Scenario: Start MCP server via pitchfork
- **WHEN** user enters project directory with pitchfork activated
- **THEN** pitchfork SHALL auto-start the MCP server daemon as configured in `pitchfork.toml`

### Requirement: get_stock_data tool
The MCP server SHALL expose a `get_stock_data` tool that fetches price data for a ticker. An optional `provider` parameter allows specifying a data provider explicitly (e.g., "yahoo", "kase"); if omitted, the configured primary provider with fallback chain is used.

#### Scenario: Fetch stock data via MCP
- **WHEN** Claude Code calls `get_stock_data(ticker="AAPL", period="1y")`
- **THEN** the tool SHALL return JSON with OHLCV data from the active data provider

#### Scenario: Fetch stock data from specific provider
- **WHEN** Claude Code calls `get_stock_data(ticker="KCEL", period="1y", provider="kase")`
- **THEN** the tool SHALL route the request to KASEProvider specifically

### Requirement: run_fundamental_analysis tool
The MCP server SHALL expose a `run_fundamental_analysis` tool with an optional `sector` parameter. If `sector` is not provided, the tool SHALL attempt auto-detection via `yfinance.Ticker.info["sector"]`. If auto-detection fails (e.g. KASE tickers), sector comparison fields SHALL be `None`.

#### Scenario: Run fundamental analysis via MCP
- **WHEN** Claude Code calls `run_fundamental_analysis(ticker="SBER")`
- **THEN** the tool SHALL return JSON with all computed fundamental ratios, with sector auto-detected if possible

#### Scenario: Run fundamental analysis with explicit sector
- **WHEN** Claude Code calls `run_fundamental_analysis(ticker="KCEL", sector="Technology")`
- **THEN** the tool SHALL use the provided sector for median comparison

### Requirement: run_technical_analysis tool
The MCP server SHALL expose a `run_technical_analysis` tool.

#### Scenario: Run technical analysis via MCP
- **WHEN** Claude Code calls `run_technical_analysis(ticker="AAPL")`
- **THEN** the tool SHALL return JSON with technical indicators and signals

### Requirement: search_news tool
The MCP server SHALL expose a `search_news` tool for financial news search. If no SearchProvider is configured (no Brave key, no SearXNG instance), the tool SHALL return an empty list with a warning message, not an error.

#### Scenario: Search news via MCP
- **WHEN** Claude Code calls `search_news(query="KCEL earnings", max_results=5)`
- **THEN** the tool SHALL return JSON array of search results from the active search provider

#### Scenario: No search provider configured
- **WHEN** Claude Code calls `search_news(...)` and no SearchProvider is available
- **THEN** the tool SHALL return `{"results": [], "warning": "No search provider configured. Set BRAVE_API_KEY or configure SearXNG instance."}`

### Requirement: run_agent tool
The MCP server SHALL expose a `run_agent` tool for invoking analysis agents.

#### Scenario: Run agent via MCP
- **WHEN** Claude Code calls `run_agent(ticker="SBER", agent="elvis_marlamov")`
- **THEN** the tool SHALL return JSON with `signal`, `score`, `confidence`, `rationale`, `breakdown`

### Requirement: run_risk_analysis tool
The MCP server SHALL expose a `run_risk_analysis` tool for portfolio risk metrics. The tool acts as orchestration layer: it fetches `PriceData` per ticker via `DataProvider`, then passes typed data to risk analysis pure functions (`calculate_volatility`, `calculate_var`, `correlation_matrix`). The risk module itself does NOT call DataProvider.

#### Scenario: Run risk analysis via MCP
- **WHEN** Claude Code calls `run_risk_analysis(tickers=["AAPL", "MSFT"], period="1y")`
- **THEN** the tool SHALL fetch PriceData for each ticker via DataProvider, compute volatility/VaR/correlations via risk module, and return JSON RiskResult

### Requirement: MCP error handling
All MCP tools SHALL return structured errors for invalid inputs or provider failures.

#### Scenario: Tool receives invalid ticker
- **WHEN** any MCP tool is called with an invalid ticker
- **THEN** the tool SHALL return an error response with `is_error=True` and descriptive message

#### Scenario: Provider rate limited
- **WHEN** a tool call triggers a rate limit on the underlying provider
- **THEN** the tool SHALL wait and retry transparently, returning data once available
