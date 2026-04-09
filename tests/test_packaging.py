"""Packaging and resource access verification for noasr.

Covers: package metadata, asset discovery, asset contents, and CLI entrypoint.
"""

import importlib
import importlib.resources
import json
import subprocess
import sys

import pytest

import noasr


# ---------------------------------------------------------------------------
# TestPackageMetadata
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestPackageMetadata:
    """Verify package-level metadata."""

    def test_version_is_0_1_0(self) -> None:
        """noasr.__version__ should equal '0.1.0'."""
        assert noasr.__version__ == "0.1.0"

    def test_all_contains_main(self) -> None:
        """noasr.__all__ should contain 'main'."""
        assert "main" in noasr.__all__


# ---------------------------------------------------------------------------
# TestAssetDiscovery
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestAssetDiscovery:
    """Verify that package assets are discoverable via importlib.resources."""

    def test_assets_directory_exists(self) -> None:
        """importlib.resources.files('noasr') / 'assets' should exist."""
        assets = importlib.resources.files("noasr") / "assets"
        assert assets.is_dir()

    def test_config_json_exists_and_readable(self) -> None:
        """config.json asset should exist and be readable."""
        config_path = importlib.resources.files("noasr") / "assets" / "config.json"
        assert config_path.is_file()
        content = config_path.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_user_prompt_exists(self) -> None:
        """input_user_prompt.md asset should exist."""
        prompt_path = (
            importlib.resources.files("noasr") / "assets" / "input_user_prompt.md"
        )
        assert prompt_path.is_file()

    def test_system_prompt_exists(self) -> None:
        """input_system_prompt.md asset should exist."""
        prompt_path = (
            importlib.resources.files("noasr") / "assets" / "input_system_prompt.md"
        )
        assert prompt_path.is_file()

    def test_regex_json_exists(self) -> None:
        """regex.json asset should exist."""
        regex_path = importlib.resources.files("noasr") / "assets" / "regex.json"
        assert regex_path.is_file()


# ---------------------------------------------------------------------------
# TestAssetContents
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestAssetContents:
    """Verify asset file contents are valid."""

    def test_config_json_is_valid_json(self) -> None:
        """config.json should be valid JSON."""
        config_path = importlib.resources.files("noasr") / "assets" / "config.json"
        content = config_path.read_text(encoding="utf-8")
        data = json.loads(content)
        assert isinstance(data, dict)

    def test_regex_json_is_valid_json(self) -> None:
        """regex.json should be valid JSON (empty dict or with entries)."""
        regex_path = importlib.resources.files("noasr") / "assets" / "regex.json"
        content = regex_path.read_text(encoding="utf-8")
        data = json.loads(content)
        assert isinstance(data, dict)

    def test_config_json_contains_expected_keys(self) -> None:
        """config.json should contain baseurl, api_key, toolsets, agents."""
        config_path = importlib.resources.files("noasr") / "assets" / "config.json"
        content = config_path.read_text(encoding="utf-8")
        data = json.loads(content)

        assert "baseurl" in data
        assert "api_key" in data
        assert "toolsets" in data
        assert "agents" in data


# ---------------------------------------------------------------------------
# TestCLIEntrypoint
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCLIEntrypoint:
    """Verify CLI entry points work."""

    def test_python_m_noasr_version_exits_0(self) -> None:
        """python -m noasr --version should exit with code 0."""
        result = subprocess.run(
            [sys.executable, "-m", "noasr", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_noasr_version_exits_0_if_installed(self) -> None:
        """noasr --version should exit 0 if the package is installed on PATH."""
        result = subprocess.run(
            ["noasr", "--version"],
            capture_output=True,
            text=True,
        )
        # Allow skip if noasr is not on PATH or not importable in that env
        if result.returncode != 0:
            stderr_lower = result.stderr.lower()
            if "not found" in stderr_lower or "modulenotfounderror" in stderr_lower:
                pytest.skip("noasr not on PATH or not importable")
        assert result.returncode == 0
