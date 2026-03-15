"""CLI entry point for fin-toolkit."""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

# Default MCP server entry
_MCP_SERVER_ENTRY: dict[str, Any] = {
    "command": "uv",
    "args": ["run", "--project", str(Path(__file__).resolve().parent.parent), "fin-toolkit", "serve"],
}

# Default config content
_DEFAULT_CONFIG: dict[str, Any] = {
    "data": {
        "primary_provider": "yahoo",
        "fallback_providers": ["fmp"],
    },
    "search": {
        "providers": ["brave", "searxng"],
        "searxng_url": "http://localhost:8888",
    },
    "agents": {
        "active": ["elvis_marlamov", "warren_buffett"],
    },
}


def _parse_setup_args() -> bool:
    """Parse setup-specific args. Returns True if --global flag is set."""
    return "--global" in sys.argv


def main() -> None:
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: fin-toolkit <command>")
        print("Commands: setup, serve, status")
        sys.exit(1)

    command = sys.argv[1]
    if command == "serve":
        _serve()
    elif command == "setup":
        _setup()
    elif command == "status":
        _status()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


def _serve() -> None:
    """Start the MCP server."""
    import os

    from fin_toolkit.agents.registry import AgentRegistry
    from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
    from fin_toolkit.analysis.technical import TechnicalAnalyzer
    from fin_toolkit.config.loader import load_config
    from fin_toolkit.config.models import PROVIDER_KEY_MAP
    from fin_toolkit.mcp_server.server import init_server
    from fin_toolkit.providers.protocol import DataProvider
    from fin_toolkit.providers.router import ProviderRouter
    from fin_toolkit.providers.search_protocol import SearchProvider
    from fin_toolkit.providers.search_router import SearchRouter

    config = load_config()

    # Build data providers
    providers: dict[str, DataProvider] = {}
    available = config.available_providers()
    if "yahoo" in available:
        from fin_toolkit.providers.yahoo import YahooFinanceProvider

        providers["yahoo"] = YahooFinanceProvider()
    if "kase" in available:
        from fin_toolkit.providers.kase import KASEProvider

        providers["kase"] = KASEProvider()

    provider_router = ProviderRouter(config=config, providers=providers)

    # Build search providers
    search_list: list[SearchProvider] = []
    available_search = config.available_search_providers()
    if "perplexity" in available_search:
        from fin_toolkit.providers.perplexity import PerplexitySearchProvider

        api_key = config.api_keys.get("perplexity") or os.environ.get(
            PROVIDER_KEY_MAP.get("perplexity", ""), ""
        )
        if api_key:
            search_list.append(PerplexitySearchProvider(api_key=api_key))
    if "brave" in available_search:
        from fin_toolkit.providers.brave import BraveSearchProvider

        api_key = config.api_keys.get("brave") or os.environ.get(
            PROVIDER_KEY_MAP.get("brave", ""), ""
        )
        if api_key:
            search_list.append(BraveSearchProvider(api_key=api_key))
    if "searxng" in available_search:
        from fin_toolkit.providers.searxng import SearXNGProvider

        search_list.append(SearXNGProvider(base_url=config.search.searxng_url))

    search_router = SearchRouter(search_list) if search_list else None

    # Build analyzers
    technical = TechnicalAnalyzer()
    fundamental = FundamentalAnalyzer()

    # Build agent registry
    agent_registry = AgentRegistry(
        config=config,
        data_provider=provider_router,
        technical=technical,
        fundamental=fundamental,
        search=search_router,
    )

    # Initialize and run
    server = init_server(
        provider_router=provider_router,
        search_router=search_router,
        technical_analyzer=technical,
        fundamental_analyzer=fundamental,
        agent_registry=agent_registry,
    )
    server.run()


def _setup() -> None:
    """Set up MCP configuration and default config file."""
    use_global = _parse_setup_args()

    # 1. Write MCP JSON
    target = Path.home() / ".claude.json" if use_global else Path.cwd() / ".mcp.json"

    _write_mcp_entry(target)

    # 2. Write default config if not exists
    config_file = Path.home() / ".config" / "fin-toolkit" / "config.yaml"
    if not config_file.exists():
        config_file.parent.mkdir(parents=True, exist_ok=True)
        content = yaml.dump(_DEFAULT_CONFIG, default_flow_style=False, sort_keys=False)
        config_file.write_text(content)

    if use_global:
        print(f"Wrote MCP server entry to {target}")
    else:
        print(f"Wrote MCP server entry to {target}")
    print(f"Config: {config_file}")


def _write_mcp_entry(target: Path) -> None:
    """Write the fin-toolkit MCP server entry into a JSON file, preserving existing content."""
    existing: dict[str, Any] = {}
    if target.exists():
        try:
            existing = json.loads(target.read_text())
        except (json.JSONDecodeError, OSError):
            existing = {}

    servers = existing.get("mcpServers", {})
    if "fin-toolkit" not in servers:
        servers["fin-toolkit"] = _MCP_SERVER_ENTRY
        existing["mcpServers"] = servers
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(existing, indent=2) + "\n")


def _status() -> None:
    """Show toolkit status."""
    home = Path.home()
    cwd = Path.cwd()

    # Determine config path
    local_config = cwd / "fin-toolkit.yaml"
    global_config = home / ".config" / "fin-toolkit" / "config.yaml"

    if local_config.exists():
        config_path = local_config
    elif global_config.exists():
        config_path = global_config
    else:
        config_path = None

    print("fin-toolkit status")
    print("=" * 40)

    # Config path
    if config_path:
        print(f"Config: {config_path}")
    else:
        print("Config: (none found)")

    # Load config for provider info
    config_data: dict[str, Any] = {}
    if config_path and config_path.exists():
        with contextlib.suppress(yaml.YAMLError, OSError):
            config_data = yaml.safe_load(config_path.read_text()) or {}

    # .mcp.json
    mcp_json = cwd / ".mcp.json"
    if mcp_json.exists():
        print(f".mcp.json: found ({mcp_json})")
    else:
        print(".mcp.json: not found")

    # Data providers (always show all known ones)
    import os

    print("\nData providers:")
    data_providers = ["yahoo", "kase", "fmp"]
    key_free = {"yahoo", "kase"}
    key_map = {"fmp": "FMP_API_KEY"}
    for p in data_providers:
        mark = "✓" if p in key_free or os.environ.get(key_map.get(p, ""), "") else "✗"
        print(f"  {mark} {p}")

    # Search providers
    print("\nSearch providers:")
    search_providers = ["brave", "searxng"]
    search_key_map = {"brave": "BRAVE_API_KEY"}
    for p in search_providers:
        env_var = search_key_map.get(p, "")
        mark = "✓" if p == "searxng" or os.environ.get(env_var, "") else "✗"
        print(f"  {mark} {p}")

    # Agents
    agents_data = config_data.get("agents", {})
    active = agents_data.get("active", [])
    print("\nActive agents:")
    if active:
        for a in active:
            print(f"  - {a}")
    else:
        print("  (none)")
