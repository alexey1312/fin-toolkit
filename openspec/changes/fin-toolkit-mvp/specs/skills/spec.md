## ADDED Requirements

### Requirement: Skill folder structure
Each fin-toolkit skill SHALL follow the Anthropic Skills standard: a folder containing `SKILL.md` with YAML frontmatter, optional `references/` for detailed documentation, and optional `scripts/` for executable helpers. Skill folder names SHALL be kebab-case. No README.md inside skill folders.

#### Scenario: Valid skill structure
- **WHEN** the `skills/dcf-valuation/` folder is examined
- **THEN** it SHALL contain `SKILL.md` with valid YAML frontmatter (`name`, `description`) and markdown body with step-by-step instructions

### Requirement: SKILL.md frontmatter
Each SKILL.md SHALL have YAML frontmatter with:
- `name` (required): kebab-case, matches folder name
- `description` (required): under 1024 chars, includes WHAT the skill does + WHEN to use it (trigger phrases). No XML angle brackets.
- `metadata` (optional): `author`, `version`, `mcp-server: fin-toolkit`

#### Scenario: Frontmatter triggers correctly
- **WHEN** a user says "analyze AAPL earnings" in Claude Code
- **THEN** the `earnings-analysis` skill SHALL be loaded based on its description matching the user's intent

#### Scenario: Frontmatter does not over-trigger
- **WHEN** a user says "write a Python function to sort a list"
- **THEN** no fin-toolkit skill SHALL be loaded

### Requirement: Progressive disclosure
Skills SHALL use three-level progressive disclosure:
1. **YAML frontmatter** — always loaded in system prompt, minimal (~100 tokens)
2. **SKILL.md body** — loaded when Claude determines relevance, contains full instructions
3. **references/ files** — linked from SKILL.md, loaded on demand for deep documentation

### Requirement: MCP-enhanced workflow skills
Skills SHALL coordinate multi-step workflows using fin-toolkit MCP tools. Each skill SHALL reference specific MCP tools by name and define the execution sequence.

#### Scenario: DCF valuation workflow
- **WHEN** the `dcf-valuation` skill is activated
- **THEN** it SHALL instruct Claude to: (1) call `get_stock_data` for price history, (2) call `run_fundamental_analysis` for ratios, (3) guide the user through DCF assumptions, (4) compute intrinsic value

### Requirement: dcf-valuation skill
The system SHALL provide a `dcf-valuation` skill that guides Claude through a Discounted Cash Flow analysis using MCP tools.

#### Scenario: Complete DCF workflow
- **WHEN** user says "run a DCF valuation on AAPL"
- **THEN** the skill SHALL guide Claude to fetch financial data, ask user for growth assumptions, compute WACC, project free cash flows, and present intrinsic value vs current price

### Requirement: technical-screen skill
The system SHALL provide a `technical-screen` skill for technical screening of stocks.

#### Scenario: Single stock screen
- **WHEN** user says "technical analysis of MSFT"
- **THEN** the skill SHALL guide Claude to call `run_technical_analysis`, interpret signals, and present actionable summary

### Requirement: earnings-analysis skill
The system SHALL provide an `earnings-analysis` skill for earnings quality assessment.

#### Scenario: Earnings analysis workflow
- **WHEN** user says "analyze TSLA earnings"
- **THEN** the skill SHALL guide Claude to fetch financials via MCP, compute margins/growth, compare to prior periods, and assess quality

### Requirement: portfolio-review skill
The system SHALL provide a `portfolio-review` skill that orchestrates multi-stock analysis with risk metrics.

#### Scenario: Portfolio review workflow
- **WHEN** user says "review my portfolio: AAPL, MSFT, GOOGL"
- **THEN** the skill SHALL guide Claude to run analysis per ticker, compute correlations and VaR via `run_risk_analysis`, and present portfolio-level summary

### Requirement: kase-analysis skill
The system SHALL provide a `kase-analysis` skill specialized for Kazakhstan market analysis.

#### Scenario: KASE analysis workflow
- **WHEN** user says "analyze KCEL on KASE"
- **THEN** the skill SHALL guide Claude to use `get_stock_data(provider="kase")`, run analysis, and present KZ-market-specific context

### Requirement: Error handling in skills
Each skill SHALL include a "Common Issues" section addressing MCP connection failures, missing API keys, and provider-specific errors with resolution steps.

#### Scenario: MCP server not connected
- **WHEN** a skill is activated but fin-toolkit MCP server is not running
- **THEN** the skill SHALL instruct the user to run `fin-toolkit serve` or activate pitchfork, and verify `.mcp.json` configuration
