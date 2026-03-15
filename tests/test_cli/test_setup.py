"""Tests for fin-toolkit CLI setup and status commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import yaml

from fin_toolkit.cli import _setup, _status, main


class TestSetupCommand:
    """Tests for the setup command."""

    def test_setup_creates_mcp_json(self, tmp_path: Path) -> None:
        """setup creates .mcp.json with correct MCP server entry."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        config_dir = tmp_path / "home" / ".config" / "fin-toolkit"

        with (
            patch("fin_toolkit.cli.Path.cwd", return_value=project_dir),
            patch("fin_toolkit.cli.Path.home", return_value=tmp_path / "home"),
        ):
            _setup()

        mcp_json = project_dir / ".mcp.json"
        assert mcp_json.exists()
        data = json.loads(mcp_json.read_text())
        entry = data["mcpServers"]["fin-toolkit"]
        assert entry["command"] == "uv"
        assert entry["args"][0] == "run"
        assert "--project" in entry["args"]
        assert entry["args"][-2:] == ["fin-toolkit", "serve"]

        # Also creates default config
        config_file = config_dir / "config.yaml"
        assert config_file.exists()

    def test_setup_creates_default_config_yaml(self, tmp_path: Path) -> None:
        """setup creates ~/.config/fin-toolkit/config.yaml with defaults."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        home = tmp_path / "home"

        with (
            patch("fin_toolkit.cli.Path.cwd", return_value=project_dir),
            patch("fin_toolkit.cli.Path.home", return_value=home),
        ):
            _setup()

        config_file = home / ".config" / "fin-toolkit" / "config.yaml"
        assert config_file.exists()
        data = yaml.safe_load(config_file.read_text())
        assert data["data"]["primary_provider"] == "yahoo"
        assert "agents" in data
        assert "search" in data

    def test_setup_idempotent_does_not_overwrite_config(self, tmp_path: Path) -> None:
        """Second call does not overwrite existing config."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        home = tmp_path / "home"
        config_dir = home / ".config" / "fin-toolkit"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("data:\n  primary_provider: fmp\n")

        with (
            patch("fin_toolkit.cli.Path.cwd", return_value=project_dir),
            patch("fin_toolkit.cli.Path.home", return_value=home),
        ):
            _setup()

        # Config should NOT be overwritten
        data = yaml.safe_load(config_file.read_text())
        assert data["data"]["primary_provider"] == "fmp"

    def test_setup_idempotent_does_not_overwrite_mcp_json(self, tmp_path: Path) -> None:
        """Second call does not overwrite existing .mcp.json if fin-toolkit entry exists."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        home = tmp_path / "home"

        # Pre-create .mcp.json with fin-toolkit entry
        existing = {
            "mcpServers": {
                "fin-toolkit": {
                    "command": "uvx",
                    "args": ["fin-toolkit", "serve"],
                },
                "other-server": {"command": "other"},
            }
        }
        mcp_json = project_dir / ".mcp.json"
        mcp_json.write_text(json.dumps(existing))

        with (
            patch("fin_toolkit.cli.Path.cwd", return_value=project_dir),
            patch("fin_toolkit.cli.Path.home", return_value=home),
        ):
            _setup()

        data = json.loads(mcp_json.read_text())
        # Should preserve both servers, not overwrite
        assert "other-server" in data["mcpServers"]
        assert "fin-toolkit" in data["mcpServers"]

    def test_setup_preserves_existing_servers(self, tmp_path: Path) -> None:
        """setup merges into existing .mcp.json, preserving other servers."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        home = tmp_path / "home"

        existing = {"mcpServers": {"some-other": {"command": "foo"}}}
        mcp_json = project_dir / ".mcp.json"
        mcp_json.write_text(json.dumps(existing))

        with (
            patch("fin_toolkit.cli.Path.cwd", return_value=project_dir),
            patch("fin_toolkit.cli.Path.home", return_value=home),
        ):
            _setup()

        data = json.loads(mcp_json.read_text())
        assert "some-other" in data["mcpServers"]
        assert data["mcpServers"]["some-other"] == {"command": "foo"}
        assert "fin-toolkit" in data["mcpServers"]

    def test_setup_global_writes_to_claude_json(self, tmp_path: Path) -> None:
        """--global writes to ~/.claude.json instead of local .mcp.json."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        home = tmp_path / "home"

        with (
            patch("fin_toolkit.cli.Path.cwd", return_value=project_dir),
            patch("fin_toolkit.cli.Path.home", return_value=home),
            patch("fin_toolkit.cli._parse_setup_args", return_value=True),
        ):
            _setup()

        # Should NOT create local .mcp.json
        assert not (project_dir / ".mcp.json").exists()

        # Should create ~/.claude.json
        claude_json = home / ".claude.json"
        assert claude_json.exists()
        data = json.loads(claude_json.read_text())
        assert "mcpServers" in data
        assert "fin-toolkit" in data["mcpServers"]

    def test_setup_global_preserves_existing_claude_json(self, tmp_path: Path) -> None:
        """--global merges into existing ~/.claude.json."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        home = tmp_path / "home"
        home.mkdir(parents=True, exist_ok=True)

        existing = {"mcpServers": {"existing-server": {"command": "bar"}}, "other_key": 42}
        claude_json = home / ".claude.json"
        claude_json.write_text(json.dumps(existing))

        with (
            patch("fin_toolkit.cli.Path.cwd", return_value=project_dir),
            patch("fin_toolkit.cli.Path.home", return_value=home),
            patch("fin_toolkit.cli._parse_setup_args", return_value=True),
        ):
            _setup()

        data = json.loads(claude_json.read_text())
        assert data["other_key"] == 42
        assert "existing-server" in data["mcpServers"]
        assert "fin-toolkit" in data["mcpServers"]

    def test_setup_local_config_override(self, tmp_path: Path) -> None:
        """Local ./fin-toolkit.yaml is detected in status after setup."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        home = tmp_path / "home"

        with (
            patch("fin_toolkit.cli.Path.cwd", return_value=project_dir),
            patch("fin_toolkit.cli.Path.home", return_value=home),
        ):
            _setup()

        # Create local override
        local_config = project_dir / "fin-toolkit.yaml"
        local_config.write_text("data:\n  primary_provider: kase\n")

        # Global config should still exist
        assert (home / ".config" / "fin-toolkit" / "config.yaml").exists()
        # Local override should exist
        assert local_config.exists()


class TestMainGlobalFlag:
    """Tests for --global flag parsing in main()."""

    def test_main_setup_global_flag(self, tmp_path: Path) -> None:
        """main() passes --global flag to setup."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        home = tmp_path / "home"

        with (
            patch("sys.argv", ["fin-toolkit", "setup", "--global"]),
            patch("fin_toolkit.cli.Path.cwd", return_value=project_dir),
            patch("fin_toolkit.cli.Path.home", return_value=home),
        ):
            main()

        # Should create ~/.claude.json, NOT local .mcp.json
        assert not (project_dir / ".mcp.json").exists()
        assert (home / ".claude.json").exists()


class TestStatusCommand:
    """Tests for the status command."""

    def test_status_shows_config_path(self, tmp_path: Path, capsys: object) -> None:
        """status shows which config path is being used."""
        home = tmp_path / "home"
        config_dir = home / ".config" / "fin-toolkit"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("data:\n  primary_provider: yahoo\n")
        cwd = tmp_path / "project"
        cwd.mkdir()

        with (
            patch("fin_toolkit.cli.Path.cwd", return_value=cwd),
            patch("fin_toolkit.cli.Path.home", return_value=home),
        ):
            _status()

        captured = capsys.readouterr()  # type: ignore[union-attr]
        assert str(config_file) in captured.out

    def test_status_shows_mcp_json_exists(self, tmp_path: Path, capsys: object) -> None:
        """status shows whether .mcp.json exists."""
        home = tmp_path / "home"
        cwd = tmp_path / "project"
        cwd.mkdir()
        (cwd / ".mcp.json").write_text("{}")

        with (
            patch("fin_toolkit.cli.Path.cwd", return_value=cwd),
            patch("fin_toolkit.cli.Path.home", return_value=home),
        ):
            _status()

        captured = capsys.readouterr()  # type: ignore[union-attr]
        assert ".mcp.json" in captured.out

    def test_status_shows_providers(self, tmp_path: Path, capsys: object) -> None:
        """status shows available data and search providers."""
        home = tmp_path / "home"
        cwd = tmp_path / "project"
        cwd.mkdir()

        with (
            patch("fin_toolkit.cli.Path.cwd", return_value=cwd),
            patch("fin_toolkit.cli.Path.home", return_value=home),
        ):
            _status()

        captured = capsys.readouterr()  # type: ignore[union-attr]
        assert "yahoo" in captured.out
        assert "kase" in captured.out
        assert "brave" in captured.out
        assert "searxng" in captured.out

    def test_status_shows_agents(self, tmp_path: Path, capsys: object) -> None:
        """status shows active agents."""

        home = tmp_path / "home"
        config_dir = home / ".config" / "fin-toolkit"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text(
            "data:\n  primary_provider: yahoo\nagents:\n  active:\n    - elvis_marlamov\n"
        )
        cwd = tmp_path / "project"
        cwd.mkdir()

        with (
            patch("fin_toolkit.cli.Path.cwd", return_value=cwd),
            patch("fin_toolkit.cli.Path.home", return_value=home),
        ):
            _status()

        captured = capsys.readouterr()  # type: ignore[union-attr]
        assert "elvis_marlamov" in captured.out
