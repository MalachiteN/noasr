"""Platform capability diagnostics and runtime environment detection."""

import logging
from typing import Optional

from noasr.models import PlatformInfo, get_platform_info

logger = logging.getLogger(__name__)


class PlatformDiagnostics:
    """
    Runtime platform capability diagnostics.

    Provides detailed platform information and reports capability limitations
    without aborting startup on supported platforms (Windows).
    """

    def __init__(self, platform_info: Optional[PlatformInfo] = None) -> None:
        """Initialize diagnostics with platform info."""
        self._platform_info = platform_info or get_platform_info()

    @property
    def platform_info(self) -> PlatformInfo:
        """Get the platform info object."""
        return self._platform_info

    def get_capability_level(self) -> str:
        """
        Get the capability level as a string.

        Returns:
            'full' for Windows, 'full' for macOS/Linux with correct setup,
            'limited' for degraded environments.
        """
        if self._platform_info.is_windows:
            return "full"

        if self._platform_info.is_macos:
            return "full"  # Full functionality with accessibility permissions

        if self._platform_info.is_linux:
            if self._platform_info.display_server == "x11":
                return "full"
            elif self._platform_info.display_server == "wayland":
                return "limited"
            else:
                return "limited"

        return "unknown"

    def is_recommended(self) -> bool:
        """Check if current platform is recommended for noasr."""
        return self._platform_info.is_windows

    def get_capability_report(self) -> dict[str, dict[str, str]]:
        """
        Get a detailed capability report for the current platform.

        Returns:
            Dictionary with platform capabilities and their status.
        """
        info = self._platform_info
        report: dict[str, dict[str, str]] = {}

        # Overall recommendation
        report["platform"] = {
            "status": "recommended" if self.is_recommended() else "experimental",
            "platform": info.platform,
            "display_server": info.display_server or "unknown",
        }

        # Hotkey support
        hotkey_status = "supported"
        if info.is_linux:
            if info.display_server == "wayland":
                hotkey_status = "limited"
            elif info.display_server == "x11":
                hotkey_status = "supported"
            else:
                hotkey_status = "limited"
        report["hotkeys"] = {
            "status": hotkey_status,
            "note": self._get_hotkey_note(),
        }

        # Clipboard injection
        report["clipboard"] = {
            "status": "supported" if info.is_windows else "limited",
            "note": "Ctrl+V paste supported on Windows; may require permissions on other platforms",
        }

        # Overlay/UI
        report["overlay"] = {
            "status": "supported",
            "note": self._get_overlay_note(),
        }

        # Audio input
        report["audio"] = {
            "status": "supported",
            "note": "Microphone access required on all platforms",
        }

        return report

    def _get_hotkey_note(self) -> str:
        """Get platform-specific hotkey note."""
        if self._platform_info.is_windows:
            return "Full global hotkey support via pynput on Windows"
        elif self._platform_info.is_macos:
            return "Requires Accessibility permissions for global hotkeys"
        elif self._platform_info.is_linux:
            if self._platform_info.display_server == "x11":
                return "X11 full support with appropriate permissions"
            elif self._platform_info.display_server == "wayland":
                return "Wayland limited - global hotkeys may not work reliably"
            else:
                return "Limited hotkey support"
        return "Hotkey support unknown"

    def _get_overlay_note(self) -> str:
        """Get platform-specific overlay note."""
        if self._platform_info.is_windows:
            return "Flet overlay with best-effort focus handling on Windows"
        elif self._platform_info.is_macos:
            return "Overlay support with macOS limitations"
        elif self._platform_info.is_linux:
            if self._platform_info.display_server == "wayland":
                return "Wayland may restrict overlay behavior"
            return "Overlay support on X11"
        return "Overlay support unknown"

    def log_capabilities(self) -> None:
        """Log platform capabilities at INFO level."""
        report = self.get_capability_report()

        logger.info("=" * 50)
        logger.info("noasr Platform Diagnostics")
        logger.info("=" * 50)

        # Log platform
        platform_data = report.get("platform", {})
        logger.info(
            "Platform: %s (%s, display: %s)",
            platform_data.get("platform", "unknown"),
            platform_data.get("status", "unknown"),
            platform_data.get("display_server", "unknown"),
        )

        # Log warnings
        warnings = self._platform_info.get_warnings()
        if warnings:
            logger.warning("Platform limitations detected:")
            for warning in warnings:
                logger.warning("  - %s", warning)

        # Log capability details
        for capability, details in report.items():
            if capability != "platform":
                status = details.get("status", "unknown")
                note = details.get("note", "")
                logger.info("%s: %s - %s", capability, status, note)

        logger.info("=" * 50)

    def get_startup_message(self) -> str:
        """
        Get a formatted startup message with platform info.

        Returns:
            Multi-line string with platform diagnostic information.
        """
        lines = []

        # Platform header
        lines.append("Platform Information:")
        lines.append(f"  OS: {self._platform_info.platform}")

        if self._platform_info.display_server:
            lines.append(f"  Display Server: {self._platform_info.display_server}")

        # Capability level
        level = self.get_capability_level()
        lines.append(f"  Capability Level: {level}")

        if self._platform_info.is_windows:
            lines.append("  Status: Full support - Windows is the recommended platform")
        elif self._platform_info.is_macos:
            lines.append("  Status: Supported - Requires Accessibility permissions")
        elif self._platform_info.is_linux:
            if self._platform_info.display_server == "x11":
                lines.append("  Status: Supported - Full functionality on X11")
            elif self._platform_info.display_server == "wayland":
                lines.append("  Status: Limited - Wayland has security restrictions")
            else:
                lines.append("  Status: Experimental")

        # Add warnings
        warnings = self._platform_info.get_warnings()
        if warnings:
            lines.append("")
            lines.append("Platform Warnings:")
            for warning in warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)


def run_diagnostics() -> PlatformDiagnostics:
    """
    Run platform diagnostics and log results.

    Returns:
        PlatformDiagnostics instance with current platform info.
    """
    diagnostics = PlatformDiagnostics()
    diagnostics.log_capabilities()
    return diagnostics
