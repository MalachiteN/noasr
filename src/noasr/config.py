"""Configuration bootstrap and asset installation for noasr."""

import json
import sys
from pathlib import Path
from typing import Any

from importlib import resources


DEFAULT_CONFIG_DIR = Path.home() / ".noasr"
ASSETS_DIR = resources.files("noasr") / "assets"


def ensure_config_dir() -> Path:
    """Ensure the config directory exists."""
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_CONFIG_DIR


def copy_asset_if_missing(
    asset_name: str, target_path: Path, create_empty: bool = False
) -> bool:
    """
    Copy an asset from the package to the target path if it doesn't exist.

    Args:
        asset_name: Name of the asset file in the package
        target_path: Path to copy to
        create_empty: If True and asset not found, create empty file instead

    Returns:
        True if file was created/copied, False if it already existed
    """
    if target_path.exists():
        return False

    asset_path = ASSETS_DIR / asset_name
    if asset_path.exists():
        content = asset_path.read_text(encoding="utf-8")
        target_path.write_text(content, encoding="utf-8")
    elif create_empty:
        target_path.write_text("", encoding="utf-8")
    else:
        raise FileNotFoundError(
            f"Asset {asset_name} not found in package and create_empty=False"
        )

    return True


def load_config() -> dict[str, Any]:
    """Load configuration from ~/.noasr/config.json."""
    config_path = DEFAULT_CONFIG_DIR / "config.json"

    if not config_path.exists():
        return {}

    try:
        with config_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a configuration value with a safe default."""
    config = load_config()
    return config.get(key, default)


def load_user_prompt() -> str:
    """Load user prompt from ~/.noasr/input_user_prompt.md."""
    prompt_path = DEFAULT_CONFIG_DIR / "input_user_prompt.md"
    if not prompt_path.exists():
        return ""
    return prompt_path.read_text(encoding="utf-8")


def load_system_prompt() -> str:
    """Load system prompt from ~/.noasr/input_system_prompt.md."""
    prompt_path = DEFAULT_CONFIG_DIR / "input_system_prompt.md"
    if not prompt_path.exists():
        return ""
    return prompt_path.read_text(encoding="utf-8")


def load_regex_registry() -> dict[str, str]:
    """Load regex registry from ~/.noasr/regex.json."""
    regex_path = DEFAULT_CONFIG_DIR / "regex.json"
    if not regex_path.exists():
        return {}

    try:
        with regex_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def bootstrap_config() -> bool:
    """
    Bootstrap configuration files from package assets.

    Creates ~/.noasr directory and copies template files if they don't exist.
    Creates empty files for system prompt and regex registry.

    Returns:
        True if any files were created (first run), False otherwise
    """
    ensure_config_dir()

    created_any = False

    # Copy config.json template
    config_created = copy_asset_if_missing(
        "config.json", DEFAULT_CONFIG_DIR / "config.json"
    )
    if config_created:
        created_any = True
        print(
            f"Created template config: {DEFAULT_CONFIG_DIR / 'config.json'}",
            file=sys.stderr,
        )

    # Copy user prompt template
    user_prompt_created = copy_asset_if_missing(
        "input_user_prompt.md", DEFAULT_CONFIG_DIR / "input_user_prompt.md"
    )
    if user_prompt_created:
        created_any = True
        print(
            f"Created template user prompt: {DEFAULT_CONFIG_DIR / 'input_user_prompt.md'}",
            file=sys.stderr,
        )

    # Create empty system prompt
    system_prompt_created = copy_asset_if_missing(
        "input_system_prompt.md",
        DEFAULT_CONFIG_DIR / "input_system_prompt.md",
        create_empty=True,
    )
    if system_prompt_created:
        created_any = True
        print(
            f"Created empty system prompt: {DEFAULT_CONFIG_DIR / 'input_system_prompt.md'}",
            file=sys.stderr,
        )

    # Create empty regex registry
    regex_created = copy_asset_if_missing(
        "regex.json", DEFAULT_CONFIG_DIR / "regex.json", create_empty=True
    )
    if regex_created:
        created_any = True
        print(
            f"Created empty regex registry: {DEFAULT_CONFIG_DIR / 'regex.json'}",
            file=sys.stderr,
        )

    return created_any


def check_and_bootstrap() -> bool:
    """
    Check if bootstrap is needed and perform it.

    Returns:
        True if bootstrap was performed (first run), False otherwise
    """
    is_first_run = bootstrap_config()

    if is_first_run:
        print(
            "\n⚠️  First run detected! Configuration templates have been created.",
            file=sys.stderr,
        )
        print(f"   Please review and edit: {DEFAULT_CONFIG_DIR}", file=sys.stderr)
        print("   Then run noasr again.\n", file=sys.stderr)
        return True

    return False
