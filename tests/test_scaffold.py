"""Test package scaffolding."""

import subprocess
import sys
import noasr
from importlib import resources


def test_import_package() -> None:
    """Verify noasr package can be imported."""
    assert hasattr(noasr, "__version__")
    assert noasr.__version__ == "0.1.0"


def test_cli_help() -> None:
    """Verify CLI entrypoint exists and responds to --help."""
    result = subprocess.run(
        [sys.executable, "-m", "noasr", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "noasr" in result.stderr.lower() or "noasr" in result.stdout.lower()


def test_assets_accessible() -> None:
    """Verify assets are discoverable via importlib.resources."""
    assets_dir = resources.files("noasr") / "assets"
    assert assets_dir.exists()

    config_file = assets_dir / "config.json"
    assert config_file.exists()

    user_prompt = assets_dir / "input_user_prompt.md"
    assert user_prompt.exists()

    system_prompt = assets_dir / "input_system_prompt.md"
    assert system_prompt.exists()

    regex_file = assets_dir / "regex.json"
    assert regex_file.exists()
