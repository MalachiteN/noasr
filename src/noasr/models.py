"""Domain models and data structures for noasr."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class RuntimeState(Enum):
    """Runtime state machine states."""

    IDLE = auto()
    LISTENING = auto()
    LOADING = auto()
    ERROR = auto()
    APPLYING_RESULT = auto()


class OverlayState(Enum):
    """Overlay display states."""

    HIDDEN = auto()
    LISTENING = auto()
    LOADING = auto()
    ERROR = auto()


@dataclass
class AppConfig:
    """Application configuration."""

    baseurl: str = "https://api.mi-fds.com/v1"
    api_key: str = ""
    tavily_api_key: str = ""
    toolsets: dict[str, list[str]] = field(default_factory=dict)
    agents: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        """Create config from dictionary with safe defaults."""
        return cls(
            baseurl=data.get("baseurl", "https://api.mi-fds.com/v1"),
            api_key=data.get("api_key", ""),
            tavily_api_key=data.get("tavily_api_key", ""),
            toolsets=data.get("toolsets", {}),
            agents=data.get("agents", []),
        )


@dataclass
class AgentConfig:
    """Agent configuration."""

    name: str = ""
    trigger: int = 0
    toolsets: list[str] = field(default_factory=list)
    system_prompt_file: str = "input_system_prompt.md"
    user_prompt_file: str = "input_user_prompt.md"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentConfig":
        """Create agent config from dictionary with safe defaults."""
        raw_trigger = data.get("trigger", 0)
        if isinstance(raw_trigger, list):
            raise ValueError(
                f"Agent 'trigger' must be a single integer (virtual key code), "
                f"got list {raw_trigger}. Update your config.json."
            )
        return cls(
            name=data.get("name", ""),
            trigger=int(raw_trigger),
            toolsets=data.get("toolsets", []),
            system_prompt_file=data.get("system_prompt_file", "input_system_prompt.md"),
            user_prompt_file=data.get("user_prompt_file", "input_user_prompt.md"),
        )


@dataclass
class AudioPayload:
    """Audio payload for MiMo API."""

    data_uri: str = ""  # base64 data URI

    @classmethod
    def from_wav_bytes(cls, wav_bytes: bytes) -> "AudioPayload":
        """Create audio payload from WAV bytes."""
        import base64

        encoded = base64.b64encode(wav_bytes).decode("utf-8")
        return cls(data_uri=f"data:audio/wav;base64,{encoded}")

    def to_api_item(self) -> dict[str, Any]:
        """Convert to API message item."""
        return {"type": "input_audio", "input_audio": {"data": self.data_uri}}


@dataclass
class PlatformInfo:
    """Platform information and capabilities."""

    platform: str = ""
    is_windows: bool = False
    is_macos: bool = False
    is_linux: bool = False
    display_server: str | None = None  # x11, wayland, or None

    def get_warnings(self) -> list[str]:
        """Get platform-specific warnings."""
        from noasr.constants import PLATFORM_WARNINGS, PlatformCapability

        warnings = []
        if self.is_macos:
            warnings.append(PLATFORM_WARNINGS[PlatformCapability.MACOS])
        elif self.is_linux:
            if self.display_server == "wayland":
                warnings.append(PLATFORM_WARNINGS[PlatformCapability.LINUX_WAYLAND])
            elif self.display_server == "x11":
                warnings.append(PLATFORM_WARNINGS[PlatformCapability.LINUX_X11])
            else:
                warnings.append(PLATFORM_WARNINGS[PlatformCapability.LINUX])
        return warnings


def get_platform_info() -> PlatformInfo:
    """Detect current platform and capabilities."""
    import sys

    info = PlatformInfo()
    info.platform = sys.platform

    if sys.platform == "win32":
        info.is_windows = True
    elif sys.platform == "darwin":
        info.is_macos = True
    elif sys.platform.startswith("linux"):
        info.is_linux = True
        # Try to detect display server
        import os

        wayland_display = os.environ.get("WAYLAND_DISPLAY")
        display = os.environ.get("DISPLAY")
        if wayland_display:
            info.display_server = "wayland"
        elif display:
            info.display_server = "x11"

    return info
