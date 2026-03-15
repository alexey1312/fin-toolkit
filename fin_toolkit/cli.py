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
    print("MCP server not yet implemented")


def _setup() -> None:
    """Set up MCP configuration."""
    print("Setup not yet implemented")


def _status() -> None:
    """Show toolkit status."""
    print("Status not yet implemented")
