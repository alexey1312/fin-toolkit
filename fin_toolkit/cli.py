"""CLI entry point for fin-toolkit."""

import sys


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
    """Set up MCP configuration."""
    print("Setup not yet implemented")


def _status() -> None:
    """Show toolkit status."""
    print("Status not yet implemented")
