"""Constants and default values for noasr."""

# Audio format constants
AUDIO_SAMPLE_RATE = 16000  # 16kHz
AUDIO_BIT_DEPTH = 16  # 16-bit
AUDIO_CHANNELS = 1  # Mono

# Recording constraints (in seconds)
MIN_RECORDING_DURATION = 0.3  # 300ms
MAX_RECORDING_DURATION = 30.0  # 30s


# Platform capability flags
class PlatformCapability:
    """Platform capability flags."""

    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    LINUX_X11 = "linux_x11"
    LINUX_WAYLAND = "linux_wayland"


# Platform limitation messages
PLATFORM_WARNINGS = {
    PlatformCapability.MACOS: "macOS requires Accessibility permissions for global hotkeys and clipboard injection.",
    PlatformCapability.LINUX: "Linux support is experimental. X11 recommended, Wayland has significant limitations.",
    PlatformCapability.LINUX_X11: "X11 detected - full functionality available with appropriate permissions.",
    PlatformCapability.LINUX_WAYLAND: "Wayland detected - hotkeys and focus behavior may be limited due to Wayland security model.",
}

# Default config values
DEFAULT_BASEURL = "https://api.xiaomimimo.com/v1"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_MODEL = "xiaomi/mimo-v2-omni"

# File paths (relative to config dir)
CONFIG_FILENAME = "config.json"
USER_PROMPT_FILENAME = "input_user_prompt.md"
SYSTEM_PROMPT_FILENAME = "input_system_prompt.md"
REGEX_FILENAME = "regex.json"

# Single instance lock
LOCK_FILENAME = ".noasr.lock"
