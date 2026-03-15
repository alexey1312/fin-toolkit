"""Tests for configuration system."""

import os
from pathlib import Path
from unittest.mock import patch

from fin_toolkit.config.loader import load_config
from fin_toolkit.config.models import ToolkitConfig


class TestToolkitConfig:
    def test_defaults(self) -> None:
        config = ToolkitConfig()
        assert config.data.primary_provider == "yahoo"
        assert config.agents.active == ["elvis_marlamov", "warren_buffett"]

    def test_rate_limit_defaults(self) -> None:
        config = ToolkitConfig()
        assert config.rate_limits["yahoo"].requests_per_minute == 5
        assert config.rate_limits["yahoo"].max_concurrent == 2
        assert config.rate_limits["kase"].requests_per_minute == 2
        assert config.rate_limits["kase"].max_concurrent == 1

    def test_market_mapping(self) -> None:
        config = ToolkitConfig()
        assert "kz" in config.markets
        assert "KCEL" in config.markets["kz"].tickers
        assert config.markets["kz"].provider == "kase"


class TestLoadConfig:
    def test_load_valid_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "fin-toolkit.yaml"
        config_file.write_text(
            "data:\n"
            "  primary_provider: yahoo\n"
            "  fallback_providers: []\n"
            "agents:\n"
            "  active:\n"
            "    - elvis_marlamov\n"
        )
        config = load_config(config_path=config_file)
        assert config.data.primary_provider == "yahoo"
        assert config.agents.active == ["elvis_marlamov"]

    def test_missing_file_uses_defaults(self) -> None:
        config = load_config(config_path=Path("/nonexistent/fin-toolkit.yaml"))
        assert config.data.primary_provider == "yahoo"

    def test_env_override(self, tmp_path: Path) -> None:
        config_file = tmp_path / "fin-toolkit.yaml"
        config_file.write_text("data:\n  primary_provider: yahoo\n")
        with patch.dict(os.environ, {"FIN_TOOLKIT_DATA_PRIMARY": "fmp", "FMP_API_KEY": "test123"}):
            config = load_config(config_path=config_file)
            assert config.data.primary_provider == "fmp"

    def test_auto_detection_no_keys(self) -> None:
        config = load_config(config_path=Path("/nonexistent"))
        available = config.available_providers()
        assert "yahoo" in available
        assert "kase" in available
        assert "fmp" not in available

    def test_auto_detection_with_brave_key(self) -> None:
        with patch.dict(os.environ, {"BRAVE_API_KEY": "test_key"}):
            config = load_config(config_path=Path("/nonexistent"))
            available = config.available_search_providers()
            assert "brave" in available

    def test_config_priority_env_over_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "fin-toolkit.yaml"
        config_file.write_text("data:\n  primary_provider: yahoo\n")
        with patch.dict(os.environ, {"FIN_TOOLKIT_DATA_PRIMARY": "fmp", "FMP_API_KEY": "key"}):
            config = load_config(config_path=config_file)
            assert config.data.primary_provider == "fmp"

    def test_market_mapping_from_yaml(self, tmp_path: Path) -> None:
        config_file = tmp_path / "fin-toolkit.yaml"
        config_file.write_text(
            "markets:\n"
            "  kz:\n"
            "    provider: kase\n"
            "    tickers:\n"
            "      - KCEL\n"
            "      - KZTO\n"
        )
        config = load_config(config_path=config_file)
        assert config.markets["kz"].provider == "kase"
        assert "KCEL" in config.markets["kz"].tickers
