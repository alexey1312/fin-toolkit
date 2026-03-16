# Getting Started

## Users (2 commands)

```bash
uv tool install "fin-toolkit @ git+https://github.com/alexey1312/fin-toolkit.git"
fin-toolkit quickstart
```

`quickstart` registers the MCP server globally and shows available providers. No API keys required — Yahoo Finance + DuckDuckGo work out of the box.

## Developers

```bash
git clone https://github.com/alexey1312/fin-toolkit.git && cd fin-toolkit
uv sync
fin-toolkit setup            # local (.mcp.json)
# or: fin-toolkit setup --global   # global (~/.claude.json)
```

Run `fin-toolkit status` to see what's available.

## CLI Commands

CLI is infrastructure-only — it manages the server lifecycle, not analysis:

| Command | Description |
|---------|-------------|
| `fin-toolkit quickstart` | Setup + status in one step (registers globally) |
| `fin-toolkit serve` | Start the MCP server |
| `fin-toolkit setup` | Register in `.mcp.json` (or `--global` for `~/.claude.json`) |
| `fin-toolkit status` | Show available providers, search engines, and agents |

All financial analysis is available exclusively through MCP tools.

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                      Claude Code                         │
│                                                          │
│  "Analyze AAPL"  "Compare risk"  "Search AAPL news"    │
└──────────────────────┬───────────────────────────────────┘
                       │ MCP Protocol
                       ▼
┌─────────────────────────────────────────────────────────┐
│                 fin-toolkit MCP Server                    │
│                                                          │
│  20 tools → Routing Layer → Providers / Agents          │
└──────────────────────┬───────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    Data Providers  Search      Analysis
    (7 sources)    (8 engines)  (6 agents)
```

## Adding API Keys (optional)

Set environment variables or add to `fin-toolkit.yaml`:

```bash
export GEMINI_API_KEY="..."        # Google Search via Gemini
export PERPLEXITY_API_KEY="..."    # Perplexity AI search
export TAVILY_API_KEY="..."        # Tavily search
export BRAVE_API_KEY="..."         # Brave Search
export FINANCIAL_DATASETS_API_KEY="..."  # Financial Datasets (US)
```

See [Configuration](configuration.md) for full details.
