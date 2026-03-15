"""Configuration loader for fin-toolkit."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from fin_toolkit.config.models import ToolkitConfig


def load_config(
    config_path: Path | None = None,
) -> ToolkitConfig:
    """Load configuration from YAML file, .env, and environment variables.

    Priority: env vars > .env > yaml > defaults
    """
    # Load .env file if present
    load_dotenv()

    # Determine config file path
    if config_path is None:
        config_path = _find_config_file()

    # Load YAML
    yaml_data: dict[str, Any] = {}
    if config_path and config_path.exists():
        with open(config_path) as f:
            yaml_data = yaml.safe_load(f) or {}

    # Apply env overrides
    _apply_env_overrides(yaml_data)

    # Build config
    return ToolkitConfig(**yaml_data)


def _find_config_file() -> Path | None:
    """Find config file: local > XDG global > None."""
    local = Path("./fin-toolkit.yaml")
    if local.exists():
        return local

    xdg = Path.home() / ".config" / "fin-toolkit" / "config.yaml"
    if xdg.exists():
        return xdg

    return None


def _apply_env_overrides(data: dict[str, Any]) -> None:
    """Apply environment variable overrides to config data."""
    env_mappings: dict[str, tuple[str, str]] = {
        "FIN_TOOLKIT_DATA_PRIMARY": ("data", "primary_provider"),
    }
    for env_var, (section, key) in env_mappings.items():
        value = os.environ.get(env_var)
        if value is not None:
            if section not in data:
                data[section] = {}
            data[section][key] = value
