"""Tests for config bootstrap functionality."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from noasr import config


class TestBootstrapConfig:
    """Test configuration bootstrap functionality."""

    def test_ensure_config_dir_creates_directory(self, tmp_path: Path) -> None:
        """Test that ensure_config_dir creates the config directory."""
        test_dir = tmp_path / ".noasr"

        with mock.patch.object(config, "DEFAULT_CONFIG_DIR", test_dir):
            result = config.ensure_config_dir()

        assert test_dir.exists()
        assert result == test_dir

    def test_copy_asset_if_missing_creates_file(self, tmp_path: Path) -> None:
        """Test that copy_asset_if_missing creates file from asset."""
        target = tmp_path / "test_config.json"

        result = config.copy_asset_if_missing("config.json", target)

        assert result is True
        assert target.exists()
        # Verify it was copied from the actual asset
        content = target.read_text(encoding="utf-8")
        assert "baseurl" in content or "api_key" in content or "toolsets" in content

    def test_copy_asset_if_missing_skips_existing(self, tmp_path: Path) -> None:
        """Test that copy_asset_if_missing skips existing files."""
        target = tmp_path / "existing.json"
        target.write_text('{"existing": true}', encoding="utf-8")

        result = config.copy_asset_if_missing("config.json", target)

        assert result is False
        content = target.read_text(encoding="utf-8")
        assert content == '{"existing": true}'

    def test_copy_asset_if_missing_creates_empty(self, tmp_path: Path) -> None:
        """Test that copy_asset_if_missing can create empty files."""
        target = tmp_path / "empty.md"

        result = config.copy_asset_if_missing(
            "nonexistent.md", target, create_empty=True
        )

        assert result is True
        assert target.exists()
        assert target.read_text(encoding="utf-8") == ""

    def test_copy_asset_if_missing_raises_for_missing_asset(
        self, tmp_path: Path
    ) -> None:
        """Test that copy_asset_if_missing raises for missing assets when create_empty=False."""
        target = tmp_path / "missing.json"

        with pytest.raises(FileNotFoundError):
            config.copy_asset_if_missing(
                "nonexistent_file.json", target, create_empty=False
            )


class TestConfigLoading:
    """Test configuration loading functions."""

    def test_load_config_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        """Test that load_config returns empty dict when file doesn't exist."""
        test_dir = tmp_path / ".noasr"

        with mock.patch.object(config, "DEFAULT_CONFIG_DIR", test_dir):
            result = config.load_config()

        assert result == {}

    def test_load_config_parses_json(self, tmp_path: Path) -> None:
        """Test that load_config correctly parses JSON config."""
        test_dir = tmp_path / ".noasr"
        test_dir.mkdir()
        config_file = test_dir / "config.json"
        config_file.write_text(
            '{"baseurl": "https://test.com", "api_key": "test123"}', encoding="utf-8"
        )

        with mock.patch.object(config, "DEFAULT_CONFIG_DIR", test_dir):
            result = config.load_config()

        assert result == {"baseurl": "https://test.com", "api_key": "test123"}

    def test_load_config_handles_invalid_json(self, tmp_path: Path) -> None:
        """Test that load_config handles invalid JSON gracefully."""
        test_dir = tmp_path / ".noasr"
        test_dir.mkdir()
        config_file = test_dir / "config.json"
        config_file.write_text("not valid json", encoding="utf-8")

        with mock.patch.object(config, "DEFAULT_CONFIG_DIR", test_dir):
            result = config.load_config()

        assert result == {}

    def test_get_config_value_with_default(self, tmp_path: Path) -> None:
        """Test that get_config_value returns default for missing keys."""
        test_dir = tmp_path / ".noasr"
        test_dir.mkdir()
        config_file = test_dir / "config.json"
        config_file.write_text('{"existing": "value"}', encoding="utf-8")

        with mock.patch.object(config, "DEFAULT_CONFIG_DIR", test_dir):
            assert config.get_config_value("existing") == "value"
            assert config.get_config_value("missing") is None
            assert config.get_config_value("missing", "default") == "default"


class TestPromptLoading:
    """Test prompt loading functions."""

    def test_load_user_prompt_returns_empty_for_missing(self, tmp_path: Path) -> None:
        """Test that load_user_prompt returns empty string when file doesn't exist."""
        test_dir = tmp_path / ".noasr"

        with mock.patch.object(config, "DEFAULT_CONFIG_DIR", test_dir):
            result = config.load_user_prompt()

        assert result == ""

    def test_load_user_prompt_reads_file(self, tmp_path: Path) -> None:
        """Test that load_user_prompt reads the prompt file."""
        test_dir = tmp_path / ".noasr"
        test_dir.mkdir()
        prompt_file = test_dir / "input_user_prompt.md"
        prompt_file.write_text("Test user prompt", encoding="utf-8")

        with mock.patch.object(config, "DEFAULT_CONFIG_DIR", test_dir):
            result = config.load_user_prompt()

        assert result == "Test user prompt"

    def test_load_system_prompt_returns_empty_for_missing(self, tmp_path: Path) -> None:
        """Test that load_system_prompt returns empty string when file doesn't exist."""
        test_dir = tmp_path / ".noasr"

        with mock.patch.object(config, "DEFAULT_CONFIG_DIR", test_dir):
            result = config.load_system_prompt()

        assert result == ""

    def test_load_system_prompt_reads_file(self, tmp_path: Path) -> None:
        """Test that load_system_prompt reads the prompt file."""
        test_dir = tmp_path / ".noasr"
        test_dir.mkdir()
        prompt_file = test_dir / "input_system_prompt.md"
        prompt_file.write_text("Test system prompt", encoding="utf-8")

        with mock.patch.object(config, "DEFAULT_CONFIG_DIR", test_dir):
            result = config.load_system_prompt()

        assert result == "Test system prompt"


class TestRegexRegistry:
    """Test regex registry loading."""

    def test_load_regex_registry_returns_empty_for_missing(
        self, tmp_path: Path
    ) -> None:
        """Test that load_regex_registry returns empty dict when file doesn't exist."""
        test_dir = tmp_path / ".noasr"

        with mock.patch.object(config, "DEFAULT_CONFIG_DIR", test_dir):
            result = config.load_regex_registry()

        assert result == {}

    def test_load_regex_registry_parses_json(self, tmp_path: Path) -> None:
        """Test that load_regex_registry correctly parses JSON."""
        test_dir = tmp_path / ".noasr"
        test_dir.mkdir()
        regex_file = test_dir / "regex.json"
        regex_file.write_text('{"pattern": "replacement"}', encoding="utf-8")

        with mock.patch.object(config, "DEFAULT_CONFIG_DIR", test_dir):
            result = config.load_regex_registry()

        assert result == {"pattern": "replacement"}

    def test_load_regex_registry_handles_invalid_json(self, tmp_path: Path) -> None:
        """Test that load_regex_registry handles invalid JSON gracefully."""
        test_dir = tmp_path / ".noasr"
        test_dir.mkdir()
        regex_file = test_dir / "regex.json"
        regex_file.write_text("invalid json", encoding="utf-8")

        with mock.patch.object(config, "DEFAULT_CONFIG_DIR", test_dir):
            result = config.load_regex_registry()

        assert result == {}


class TestBootstrapIntegration:
    """Integration tests for bootstrap functionality."""

    def test_bootstrap_creates_all_files_on_first_run(self, tmp_path: Path) -> None:
        """Test that bootstrap creates all required files on first run."""
        test_dir = tmp_path / ".noasr"

        with mock.patch.object(config, "DEFAULT_CONFIG_DIR", test_dir):
            result = config.bootstrap_config()

        assert result is True
        assert (test_dir / "config.json").exists()
        assert (test_dir / "input_user_prompt.md").exists()
        assert (test_dir / "input_system_prompt.md").exists()
        assert (test_dir / "regex.json").exists()

    def test_bootstrap_returns_false_on_second_run(self, tmp_path: Path) -> None:
        """Test that bootstrap returns False when files already exist."""
        test_dir = tmp_path / ".noasr"

        with mock.patch.object(config, "DEFAULT_CONFIG_DIR", test_dir):
            # First run
            assert config.bootstrap_config() is True
            # Second run
            assert config.bootstrap_config() is False

    def test_check_and_bootstrap_exits_on_first_run(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that check_and_bootstrap returns True on first run (indicating exit needed)."""
        test_dir = tmp_path / ".noasr"

        with mock.patch.object(config, "DEFAULT_CONFIG_DIR", test_dir):
            result = config.check_and_bootstrap()

        assert result is True
        captured = capsys.readouterr()
        assert (
            "First run detected" in captured.err or "First run detected" in captured.out
        )
