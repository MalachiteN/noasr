"""Tests for platform diagnostics functionality."""

from unittest import mock

import pytest

from noasr.constants import PLATFORM_WARNINGS, PlatformCapability
from noasr.models import PlatformInfo
from noasr.platform import PlatformDiagnostics, run_diagnostics


class TestPlatformDiagnostics:
    """Test PlatformDiagnostics class."""

    def test_init_with_none_uses_default(self) -> None:
        """Test that None platform_info creates default."""
        diagnostics = PlatformDiagnostics()
        assert diagnostics.platform_info is not None

    def test_init_with_custom_platform_info(self) -> None:
        """Test initialization with custom platform info."""
        info = PlatformInfo()
        info.is_windows = True
        diagnostics = PlatformDiagnostics(info)

        assert diagnostics.platform_info is info

    def test_is_recommended_windows(self) -> None:
        """Test that Windows is recommended."""
        info = PlatformInfo()
        info.is_windows = True
        info.platform = "win32"
        diagnostics = PlatformDiagnostics(info)

        assert diagnostics.is_recommended() is True

    def test_is_recommended_macos(self) -> None:
        """Test that macOS is not recommended (but supported)."""
        info = PlatformInfo()
        info.is_macos = True
        info.platform = "darwin"
        diagnostics = PlatformDiagnostics(info)

        assert diagnostics.is_recommended() is False

    def test_is_recommended_linux(self) -> None:
        """Test that Linux is not recommended (but supported)."""
        info = PlatformInfo()
        info.is_linux = True
        info.platform = "linux"
        diagnostics = PlatformDiagnostics(info)

        assert diagnostics.is_recommended() is False

    def test_get_capability_level_windows(self) -> None:
        """Test Windows capability level is full."""
        info = PlatformInfo()
        info.is_windows = True
        diagnostics = PlatformDiagnostics(info)

        assert diagnostics.get_capability_level() == "full"

    def test_get_capability_level_macos(self) -> None:
        """Test macOS capability level is full."""
        info = PlatformInfo()
        info.is_macos = True
        diagnostics = PlatformDiagnostics(info)

        assert diagnostics.get_capability_level() == "full"

    def test_get_capability_level_linux_x11(self) -> None:
        """Test Linux X11 capability level is full."""
        info = PlatformInfo()
        info.is_linux = True
        info.display_server = "x11"
        diagnostics = PlatformDiagnostics(info)

        assert diagnostics.get_capability_level() == "full"

    def test_get_capability_level_linux_wayland(self) -> None:
        """Test Linux Wayland capability level is limited."""
        info = PlatformInfo()
        info.is_linux = True
        info.display_server = "wayland"
        diagnostics = PlatformDiagnostics(info)

        assert diagnostics.get_capability_level() == "limited"

    def test_get_capability_report_structure(self) -> None:
        """Test capability report has expected keys."""
        info = PlatformInfo()
        info.is_windows = True
        diagnostics = PlatformDiagnostics(info)

        report = diagnostics.get_capability_report()

        assert "platform" in report
        assert "hotkeys" in report
        assert "clipboard" in report
        assert "overlay" in report
        assert "audio" in report

    def test_get_capability_report_windows(self) -> None:
        """Test capability report for Windows."""
        info = PlatformInfo()
        info.is_windows = True
        info.platform = "win32"
        diagnostics = PlatformDiagnostics(info)

        report = diagnostics.get_capability_report()

        assert report["platform"]["status"] == "recommended"
        assert report["hotkeys"]["status"] == "supported"
        assert report["clipboard"]["status"] == "supported"

    def test_get_capability_report_macos(self) -> None:
        """Test capability report for macOS."""
        info = PlatformInfo()
        info.is_macos = True
        info.platform = "darwin"
        diagnostics = PlatformDiagnostics(info)

        report = diagnostics.get_capability_report()

        assert report["platform"]["status"] == "experimental"
        assert "Accessibility" in report["hotkeys"]["note"]

    def test_get_capability_report_linux_x11(self) -> None:
        """Test capability report for Linux X11."""
        info = PlatformInfo()
        info.is_linux = True
        info.display_server = "x11"
        diagnostics = PlatformDiagnostics(info)

        report = diagnostics.get_capability_report()

        assert report["platform"]["status"] == "experimental"
        # X11 should have better hotkey support than Wayland
        assert report["hotkeys"]["status"] in ("supported", "full")
        assert "X11" in report["hotkeys"]["note"]

    def test_get_capability_report_linux_wayland(self) -> None:
        """Test capability report for Linux Wayland."""
        info = PlatformInfo()
        info.is_linux = True
        info.display_server = "wayland"
        diagnostics = PlatformDiagnostics(info)

        report = diagnostics.get_capability_report()

        assert report["platform"]["status"] == "experimental"
        assert report["hotkeys"]["status"] == "limited"
        assert "Wayland" in report["hotkeys"]["note"]

    def test_get_startup_message_windows(self) -> None:
        """Test startup message for Windows."""
        info = PlatformInfo()
        info.is_windows = True
        info.platform = "win32"
        diagnostics = PlatformDiagnostics(info)

        message = diagnostics.get_startup_message()

        assert "win32" in message
        assert "recommended" in message.lower() or "full support" in message.lower()

    def test_get_startup_message_macos(self) -> None:
        """Test startup message for macOS."""
        info = PlatformInfo()
        info.is_macos = True
        info.platform = "darwin"
        diagnostics = PlatformDiagnostics(info)

        message = diagnostics.get_startup_message()

        assert "darwin" in message
        assert "Accessibility" in message

    def test_get_startup_message_linux_wayland(self) -> None:
        """Test startup message for Linux Wayland."""
        info = PlatformInfo()
        info.is_linux = True
        info.display_server = "wayland"
        diagnostics = PlatformDiagnostics(info)

        message = diagnostics.get_startup_message()

        assert "wayland" in message.lower()
        assert "limited" in message.lower()

    def test_log_capabilities_calls_logger(self, caplog) -> None:
        """Test that log_capabilities logs at INFO level."""
        info = PlatformInfo()
        info.is_windows = True
        info.platform = "win32"
        diagnostics = PlatformDiagnostics(info)

        # Import logging to ensure the logger is set up
        import logging

        caplog.set_level(logging.INFO)

        diagnostics.log_capabilities()

        assert "noasr Platform Diagnostics" in caplog.text
        assert "Platform:" in caplog.text


class TestRunDiagnostics:
    """Test run_diagnostics function."""

    def test_run_diagnostics_returns_diagnostics(self) -> None:
        """Test that run_diagnostics returns a diagnostics object."""
        result = run_diagnostics()
        assert isinstance(result, PlatformDiagnostics)

    def test_run_diagnostics_logs_info(self, caplog) -> None:
        """Test that run_diagnostics logs information."""
        import logging

        caplog.set_level(logging.INFO)

        run_diagnostics()

        assert "Platform Diagnostics" in caplog.text or "Platform:" in caplog.text


class TestPlatformWarnings:
    """Test platform warning constants are properly defined."""

    def test_macos_warning_exists(self) -> None:
        """Test macOS warning is defined."""
        assert PlatformCapability.MACOS in PLATFORM_WARNINGS
        assert "Accessibility" in PLATFORM_WARNINGS[PlatformCapability.MACOS]

    def test_linux_warning_exists(self) -> None:
        """Test Linux warning is defined."""
        assert PlatformCapability.LINUX in PLATFORM_WARNINGS

    def test_linux_x11_warning_exists(self) -> None:
        """Test Linux X11 warning is defined."""
        assert PlatformCapability.LINUX_X11 in PLATFORM_WARNINGS
        assert "X11" in PLATFORM_WARNINGS[PlatformCapability.LINUX_X11]

    def test_linux_wayland_warning_exists(self) -> None:
        """Test Linux Wayland warning is defined."""
        assert PlatformCapability.LINUX_WAYLAND in PLATFORM_WARNINGS
        assert "Wayland" in PLATFORM_WARNINGS[PlatformCapability.LINUX_WAYLAND]
