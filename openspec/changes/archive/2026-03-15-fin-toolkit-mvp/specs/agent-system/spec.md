## ADDED Requirements

### Requirement: Agent Protocol interface
The system SHALL define an `AnalysisAgent` Protocol with method `async analyze(ticker: str) -> AgentResult`. `AgentResult` SHALL contain: `signal` (Bullish/Neutral/Bearish), `score` (0-100), `confidence` (0.0-1.0), `rationale` (str), `breakdown` (dict), `warnings` (list[str]).

Agents are **mini-orchestrators**, NOT pure functions. `analyze()` internally calls `DataProvider.get_prices()`, `get_financials()`, `get_metrics()`, and optionally `SearchProvider.search()` via injected dependencies. This is an async I/O operation. This distinguishes agents from pure-function analyzers (`TechnicalAnalyzer`, `FundamentalAnalyzer`, risk functions) which only compute over pre-fetched data.

**Three levels of orchestration in the system:**
1. **Analyzers** — pure functions: `TechnicalAnalyzer.analyze(price_data)`, `calculate_volatility(price_data)` — no I/O
2. **Agents** — mini-orchestrators: fetch data via DataProvider → call analyzers → apply scoring logic
3. **MCP tools** — top-level orchestrators: coordinate providers, analyzers, or agents for Claude Code

#### Scenario: Agent implements AnalysisAgent Protocol
- **WHEN** a class implements `analyze(ticker: str) -> AgentResult`
- **THEN** it SHALL be accepted as a valid `AnalysisAgent`

### Requirement: Dependency injection for agents
Each agent SHALL receive its dependencies (`DataProvider`, `TechnicalAnalyzer`, `FundamentalAnalyzer`, and optionally `SearchProvider`) through constructor injection. Agents SHALL NOT instantiate providers or analyzers internally. `SearchProvider` is optional — if not provided, sentiment-dependent scoring blocks SHALL score 0 with a warning.

#### Scenario: Agent initialization with dependencies
- **WHEN** `ElvisMarlamovAgent(data_provider=yahoo, technical=ta, fundamental=fa, search=brave)` is created
- **THEN** the agent SHALL use the injected provider, analyzers, and search for data fetching, analysis, and sentiment

#### Scenario: Agent initialization without SearchProvider
- **WHEN** `ElvisMarlamovAgent(data_provider=yahoo, technical=ta, fundamental=fa)` is created without search
- **THEN** the agent SHALL operate with Sentiment block = 0 and include a warning in rationale

#### Scenario: Agent testability
- **WHEN** `ElvisMarlamovAgent(data_provider=mock_provider, technical=mock_ta, fundamental=mock_fa, search=mock_search)` is created with mock dependencies
- **THEN** the agent SHALL operate identically, enabling unit testing without network calls

### Requirement: Elvis Marlamov agent
The system SHALL provide an `ElvisMarlamovAgent` implementing the 100-point scoring system for Russian/KZ market stocks. Scoring blocks: Quality (40), Stability (20), Valuation (30), Sentiment (10). Sentiment block uses `SearchProvider` to fetch recent news and assess sentiment polarity. If `SearchProvider` is not injected, Sentiment block = 0 and the effective maximum score is 90.

#### Scenario: Analyze fundamentally strong stock
- **WHEN** `analyze("SBER")` is called and SBER has ROE > 15%, Debt/Equity < 1.0, P/E below sector average
- **THEN** the agent SHALL return score >= 75 with signal "Bullish" and breakdown per scoring block

#### Scenario: Analyze weak stock
- **WHEN** `analyze(ticker)` is called and the stock has ROE < 5%, Debt/Equity > 2.0, P/E above sector
- **THEN** the agent SHALL return score < 50 with signal "Bearish"

#### Scenario: Scoring thresholds
- **WHEN** agent completes scoring
- **THEN** signal SHALL be: >= 75 → "Bullish", 50-74 → "Neutral", < 50 → "Bearish"

#### Scenario: Missing metrics data (e.g. KASE ticker)
- **WHEN** `analyze(ticker)` is called and `DataProvider.get_metrics()` returns `KeyMetrics` with most fields `None`
- **THEN** the agent SHALL score only available blocks, set unavailable blocks to 0, adjust `confidence` downward proportionally, and include a warning listing which blocks were skipped due to missing data

### Requirement: Warren Buffett agent
The system SHALL provide a `WarrenBuffettAgent` adapted from ai-hedge-fund, implementing value investing principles: margin of safety, durable competitive advantage, management quality.

#### Scenario: Analyze value stock
- **WHEN** `analyze("BRK-B")` is called
- **THEN** the agent SHALL return an `AgentResult` with score, signal, and rationale based on Buffett's criteria

### Requirement: Agent registry with dependency assembly
The system SHALL maintain an `AgentRegistry` that assembles agents with their dependencies from configuration. The registry reads `fin-toolkit.yaml`, instantiates the correct `DataProvider`, analyzers, and optionally `SearchProvider`, and injects them into each agent.

#### Scenario: List active agents
- **WHEN** config has `agents.active: [elvis_marlamov, warren_buffett]`
- **THEN** `get_active_agents()` SHALL return both agent instances, each initialized with the configured DataProvider and analyzers

#### Scenario: Run specific agent
- **WHEN** `run_agent(ticker="KCEL", agent="elvis_marlamov")` is called
- **THEN** the system SHALL invoke only the Elvis Marlamov agent and return its result

#### Scenario: Unknown agent requested
- **WHEN** `run_agent(ticker="AAPL", agent="nonexistent")` is called
- **THEN** the system SHALL raise `AgentNotFoundError`
