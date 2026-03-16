"""CLI entry point for fin-toolkit."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

# Default MCP server entry
_PROJECT_DIR = str(Path(__file__).resolve().parent.parent)
_MCP_SERVER_ENTRY: dict[str, Any] = {
    "command": "uv",
    "args": ["run", "--project", _PROJECT_DIR, "fin-toolkit", "serve"],
}


def _parse_setup_args() -> bool:
    """Parse setup-specific args. Returns True if --global flag is set."""
    return "--global" in sys.argv


def main() -> None:
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: fin-toolkit <command>")
        print("Commands: setup, serve, status, quickstart")
        sys.exit(1)

    command = sys.argv[1]
    if command == "serve":
        _serve()
    elif command == "setup":
        _setup()
    elif command == "status":
        _status()
    elif command == "quickstart":
        _quickstart()
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

        providers["kase"] = KASEProvider(yahoo=providers.get("yahoo"))

    if "moex" in available:
        from fin_toolkit.providers.moex import MOEXProvider

        providers["moex"] = MOEXProvider()

    if "smartlab" in available:
        from fin_toolkit.providers.smartlab import SmartLabProvider

        providers["smartlab"] = SmartLabProvider()

    if "financialdatasets" in available:
        from fin_toolkit.providers.financialdatasets import FinancialDatasetsProvider

        fd_key = config.api_keys.get("financialdatasets") or os.environ.get(
            "FINANCIAL_DATASETS_API_KEY", "",
        )
        if fd_key:
            providers["financialdatasets"] = FinancialDatasetsProvider(api_key=fd_key)

    # EDGAR: always available (no API key), but only for financials
    from fin_toolkit.providers.edgar import EdgarProvider
    providers["edgar"] = EdgarProvider()

    provider_router = ProviderRouter(config=config, providers=providers)

    # Build search providers (order = fallback priority)
    search_list: list[SearchProvider] = []
    available_search = config.available_search_providers()

    # DuckDuckGo first: always available, no key needed
    if "duckduckgo" in available_search:
        from fin_toolkit.providers.duckduckgo import DuckDuckGoSearchProvider
        search_list.append(DuckDuckGoSearchProvider())

    # SearXNG second: self-hosted, no key needed
    if "searxng" in available_search:
        from fin_toolkit.providers.searxng import SearXNGProvider
        search_list.append(SearXNGProvider(base_url=config.search.searxng_url))

    # Key-based providers: added after free defaults
    # Google: has extra model param
    if "google" in available_search:
        gkey = config.api_keys.get("google") or os.environ.get("GEMINI_API_KEY", "")
        if gkey:
            from fin_toolkit.providers.google import GoogleSearchProvider
            search_list.append(
                GoogleSearchProvider(api_key=gkey, model=config.search.gemini_model),
            )

    # Other key-based providers
    _key_providers: list[tuple[str, str, type]] = []
    if "perplexity" in available_search:
        from fin_toolkit.providers.perplexity import PerplexitySearchProvider
        _key_providers.append(("perplexity", "perplexity", PerplexitySearchProvider))
    if "tavily" in available_search:
        from fin_toolkit.providers.tavily import TavilySearchProvider
        _key_providers.append(("tavily", "tavily", TavilySearchProvider))
    if "brave" in available_search:
        from fin_toolkit.providers.brave import BraveSearchProvider
        _key_providers.append(("brave", "brave", BraveSearchProvider))
    if "serper" in available_search:
        from fin_toolkit.providers.serper import SerperSearchProvider
        _key_providers.append(("serper", "serper", SerperSearchProvider))
    if "exa" in available_search:
        from fin_toolkit.providers.exa import ExaSearchProvider
        _key_providers.append(("exa", "exa", ExaSearchProvider))

    for name, config_key, cls in _key_providers:
        api_key = config.api_keys.get(config_key) or os.environ.get(
            PROVIDER_KEY_MAP.get(name, ""), ""
        )
        if api_key:
            search_list.append(cls(api_key=api_key))

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

    # Build watchlist store
    from fin_toolkit.watchlist import WatchlistStore

    watchlist_store = WatchlistStore()

    # Initialize and run
    server = init_server(
        provider_router=provider_router,
        search_router=search_router,
        technical_analyzer=technical,
        fundamental_analyzer=fundamental,
        agent_registry=agent_registry,
        watchlist_store=watchlist_store,
    )
    server.run()


def _setup() -> None:
    """Set up MCP configuration and default config file."""
    use_global = _parse_setup_args()

    # 1. Write MCP JSON
    target = Path.home() / ".claude.json" if use_global else Path.cwd() / ".mcp.json"

    _write_mcp_entry(target)

    # 2. Write default config if not exists (use Pydantic defaults)
    config_file = Path.home() / ".config" / "fin-toolkit" / "config.yaml"
    if not config_file.exists():
        from fin_toolkit.config.models import ToolkitConfig

        config_file.parent.mkdir(parents=True, exist_ok=True)
        defaults = ToolkitConfig()
        content = yaml.dump(
            defaults.model_dump(exclude_defaults=False, exclude={"rate_limits", "markets"}),
            default_flow_style=False,
            sort_keys=False,
        )
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


_DATA_PROVIDER_DESCRIPTIONS: dict[str, str] = {
    "yahoo": "US/EU/Asia stocks, ETFs, crypto (free)",
    "kase": "Kazakhstan equities via kase.kz (free)",
    "moex": "Russian equities — prices (free)",
    "smartlab": "Russian fundamentals — P/E, ROE, IFRS (free)",
    "edgar": "US SEC filings (free)",
    "fmp": "Financial Modeling Prep (needs FMP_API_KEY)",
    "financialdatasets": "US SEC data, 17k+ tickers (needs FINANCIAL_DATASETS_API_KEY)",
}

_SEARCH_PROVIDER_DESCRIPTIONS: dict[str, str] = {
    "duckduckgo": "news & articles (free)",
    "searxng": "self-hosted search (free)",
    "google": "Gemini + Search Grounding (needs GEMINI_API_KEY)",
    "perplexity": "AI-powered search (needs PERPLEXITY_API_KEY)",
    "tavily": "AI agent search (needs TAVILY_API_KEY)",
    "brave": "web search (needs BRAVE_API_KEY)",
    "serper": "Google Search wrapper (needs SERPER_API_KEY)",
    "exa": "semantic search (needs EXA_API_KEY)",
}


def _status() -> None:
    """Show toolkit status with descriptions and usage examples."""
    from fin_toolkit.config.loader import load_config

    config = load_config()
    cwd = Path.cwd()

    print("fin-toolkit status")
    print("=" * 40)

    # Config path
    local_config = cwd / "fin-toolkit.yaml"
    global_config = Path.home() / ".config" / "fin-toolkit" / "config.yaml"
    config_path = local_config if local_config.exists() else (
        global_config if global_config.exists() else None
    )
    print(f"Config: {config_path or '(none found)'}")

    # .mcp.json
    mcp_json = cwd / ".mcp.json"
    print(f".mcp.json: {'found (' + str(mcp_json) + ')' if mcp_json.exists() else 'not found'}")

    # Data providers
    available_data = set(config.available_providers())
    all_data = ["yahoo", "kase", "moex", "smartlab", "edgar", "fmp", "financialdatasets"]
    data_count = 0
    print("\nData providers:")
    for p in all_data:
        is_available = p in available_data
        mark = "✓" if is_available else "✗"
        desc = _DATA_PROVIDER_DESCRIPTIONS.get(p, "")
        print(f"  {mark} {p:<20s} {desc}")
        if is_available:
            data_count += 1

    # Search providers
    available_search = set(config.available_search_providers())
    all_search = [
        "duckduckgo", "searxng", "google", "perplexity",
        "tavily", "brave", "serper", "exa",
    ]
    search_count = 0
    print("\nSearch providers:")
    for p in all_search:
        is_available = p in available_search
        mark = "✓" if is_available else "✗"
        desc = _SEARCH_PROVIDER_DESCRIPTIONS.get(p, "")
        print(f"  {mark} {p:<20s} {desc}")
        if is_available:
            search_count += 1

    # Agents
    agent_count = len(config.agents.active)
    agent_names = ", ".join(config.agents.active) if config.agents.active else "(none)"
    print(f"\nActive agents: {agent_count} ({agent_names})")

    # Summary
    print(f"\n── Ready {'─' * 31}")
    print(f"{data_count} data + {search_count} search providers active.")
    print("All 18 tools available.")

    # Examples based on available providers
    print("\nTry asking Claude:")
    print('  "Analyze AAPL"')
    if "moex" in available_data or "smartlab" in available_data:
        print('  "Compare SBER vs GAZP"')
        print('  "Screen moex market for value stocks"')
    else:
        print('  "Compare AAPL vs MSFT"')
        print('  "Screen stocks AAPL, MSFT, GOOGL, AMZN, META"')


def _quickstart() -> None:
    """One command to set up and show status."""
    # Force --global for quickstart
    sys.argv.append("--global")
    _setup()
    print()
    _status()
