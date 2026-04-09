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
    asset_name: str,
    target_path: Path,
    create_empty: bool = False,
    default_content: str | None = None,
) -> bool:
    """
    Copy an asset from the package to the target path if it doesn't exist.

    Args:
        asset_name: Name of the asset file in the package
        target_path: Path to copy to
        create_empty: If True and asset not found, create file with default_content
        default_content: Content to write if creating file (defaults to empty string)

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
        target_path.write_text(
            default_content if default_content is not None else "",
            encoding="utf-8",
        )
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


def _sanitize_prompt_filename(filename: str) -> str:
    """Sanitize a prompt filename to prevent path traversal.

    Only bare filenames (no path separators, no parent refs) are allowed.
    """
    if not filename:
        return filename
    # Reject absolute paths and path traversal
    if Path(filename).is_absolute() or ".." in filename:
        print(
            f"Warning: Prompt filename '{filename}' rejected (path traversal), using default",
            file=sys.stderr,
        )
        return (
            "input_system_prompt.md" if "system" in filename else "input_user_prompt.md"
        )
    # Reject any path separator
    if "/" in filename or "\\" in filename:
        print(
            f"Warning: Prompt filename '{filename}' rejected (path separator), using default",
            file=sys.stderr,
        )
        return (
            "input_system_prompt.md" if "system" in filename else "input_user_prompt.md"
        )
    return filename


def load_agent_prompts(
    system_prompt_file: str = "input_system_prompt.md",
    user_prompt_file: str = "input_user_prompt.md",
) -> tuple[str, str]:
    """Load system and user prompts for an agent from ~/.noasr/.

    Only bare filenames are allowed (no path separators, no ..) to prevent
    path traversal from user-controlled config.

    Args:
        system_prompt_file: Filename of the system prompt.
        user_prompt_file: Filename of the user prompt.

    Returns:
        Tuple of (system_prompt, user_prompt). Missing files return empty string.
    """
    system_prompt_file = _sanitize_prompt_filename(system_prompt_file)
    user_prompt_file = _sanitize_prompt_filename(user_prompt_file)

    system_prompt_path = DEFAULT_CONFIG_DIR / system_prompt_file
    user_prompt_path = DEFAULT_CONFIG_DIR / user_prompt_file

    system_prompt = ""
    if system_prompt_path.exists():
        try:
            system_prompt = system_prompt_path.read_text(encoding="utf-8")
        except OSError as e:
            print(
                f"Warning: Failed to read system prompt '{system_prompt_file}': {e}",
                file=sys.stderr,
            )
    else:
        print(
            f"Warning: System prompt file not found: {system_prompt_path}",
            file=sys.stderr,
        )

    user_prompt = ""
    if user_prompt_path.exists():
        try:
            user_prompt = user_prompt_path.read_text(encoding="utf-8")
        except OSError as e:
            print(
                f"Warning: Failed to read user prompt '{user_prompt_file}': {e}",
                file=sys.stderr,
            )
    else:
        print(
            f"Warning: User prompt file not found: {user_prompt_path}",
            file=sys.stderr,
        )

    return system_prompt, user_prompt


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
        "regex.json",
        DEFAULT_CONFIG_DIR / "regex.json",
        create_empty=True,
        default_content="{}",
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
