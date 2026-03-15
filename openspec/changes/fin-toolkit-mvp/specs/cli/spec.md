## ADDED Requirements

### Requirement: CLI entry point
The system SHALL provide a `fin-toolkit` CLI via `[project.scripts]` entry point in `pyproject.toml`. The CLI SHALL support three subcommands: `setup`, `serve`, `status`.

#### Scenario: CLI is available after install
- **WHEN** `uv tool install fin-toolkit` or `pip install fin-toolkit` completes
- **THEN** `fin-toolkit --help` SHALL be available and list all subcommands

### Requirement: `fin-toolkit setup` command
The `setup` command SHALL configure fin-toolkit for use with Claude Code in one step. It SHALL be idempotent — repeated calls SHALL NOT overwrite existing configuration.

#### Scenario: First-time local setup
- **WHEN** `fin-toolkit setup` is called in a project directory
- **THEN** the system SHALL:
  1. Create `~/.config/fin-toolkit/config.yaml` with default configuration (Yahoo primary, no search, Elvis agent active) if it does not exist. This is the global user config following XDG convention.
  2. Create or update `.mcp.json` in the current directory, adding `fin-toolkit` server entry with `{"command": "uvx", "args": ["fin-toolkit", "serve"]}`
  3. Print summary: created files, config path, available providers, missing optional keys

#### Scenario: Global setup
- **WHEN** `fin-toolkit setup --global` is called
- **THEN** the system SHALL write MCP server entry to `~/.claude.json` (Claude Code global config), making fin-toolkit available in all Claude Code sessions

#### Scenario: Existing config preserved
- **WHEN** `fin-toolkit setup` is called and `fin-toolkit.yaml` already exists
- **THEN** the system SHALL NOT overwrite it, and SHALL print "Config already exists, skipping"

#### Scenario: Existing .mcp.json with other servers
- **WHEN** `.mcp.json` already exists with other MCP servers configured
- **THEN** the system SHALL add `fin-toolkit` entry without removing existing servers

### Requirement: `fin-toolkit serve` command
The `serve` command SHALL start the FastMCP server on stdio transport.

#### Scenario: Start server
- **WHEN** `fin-toolkit serve` is called
- **THEN** the MCP server SHALL start on stdio transport, load config from `fin-toolkit.yaml` (or defaults), and be ready to accept tool calls

#### Scenario: Start server with config search
- **WHEN** `fin-toolkit serve` is called
- **THEN** the server SHALL search for config in order: (1) `./fin-toolkit.yaml` (current dir), (2) `~/.config/fin-toolkit/config.yaml` (XDG), (3) built-in defaults

#### Scenario: Start server without config
- **WHEN** `fin-toolkit serve` is called and no config file is found in any location
- **THEN** the server SHALL start with default configuration (Yahoo Finance, no search, Elvis agent)

### Requirement: `fin-toolkit status` command
The `status` command SHALL display current configuration and provider availability.

#### Scenario: Show status
- **WHEN** `fin-toolkit status` is called
- **THEN** the system SHALL print:
  - Config file location (or "using defaults")
  - Data providers: available and active (e.g., "yahoo ✓ (primary), kase ✓ (fallback), fmp ✗ (no API key)")
  - Search providers: available and active (e.g., "brave ✗ (no API key), searxng ✗ (no base_url)")
  - Agents: active list (e.g., "elvis_marlamov ✓, warren_buffett ✓")
  - MCP: whether `.mcp.json` is configured

### Requirement: Install script (curl bootstrap)
The repository SHALL include an `install.sh` at the root, hosted via GitHub raw URL. The script SHALL bootstrap fin-toolkit from zero prerequisites.

#### Scenario: Bootstrap on clean system without uv
- **WHEN** `curl -fsSL https://raw.githubusercontent.com/alexey1312/fin-toolkit/main/install.sh | sh` is executed on a system without `uv`
- **THEN** the script SHALL:
  1. Install `uv` via `curl -LsSf https://astral.sh/uv/install.sh | sh`
  2. Run `uv tool install fin-toolkit`
  3. Run `fin-toolkit setup`
  4. Print success message with next steps

#### Scenario: Bootstrap on system with uv
- **WHEN** the install script is executed on a system that already has `uv`
- **THEN** the script SHALL skip uv installation and proceed to step 2

#### Scenario: Upgrade existing installation
- **WHEN** the install script is executed and fin-toolkit is already installed
- **THEN** the script SHALL run `uv tool upgrade fin-toolkit` instead of install
