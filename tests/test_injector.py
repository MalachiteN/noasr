"""Tests for text injection functionality."""

from unittest import mock

import pytest

from noasr.injector import (
    ClipboardSnapshot,
    LinuxAdapter,
    MacOSAdapter,
    PlatformAdapter,
    TextInjector,
    WindowsAdapter,
    get_platform_adapter,
)


class FakeClipboard:
    """Fake clipboard backend for testing."""

    def __init__(self, content: str = "") -> None:
        self._content = content

    def paste(self) -> str:
        return self._content

    def copy(self, text: str) -> None:
        self._content = text


class FakeAdapter(PlatformAdapter):
    """Fake platform adapter for testing."""

    def __init__(self, clipboard_content: str = "") -> None:
        self._clipboard = FakeClipboard(clipboard_content)
        self._paste_called = False

    @property
    def name(self) -> str:
        return "fake"

    def simulate_paste(self) -> bool:
        self._paste_called = True
        return True

    def get_clipboard_backend(self):
        return self._clipboard


class TestClipboardSnapshot:
    """Test ClipboardSnapshot dataclass."""

    def test_capture_success(self) -> None:
        """Test capturing clipboard with content."""
        backend = FakeClipboard("hello")
        snapshot = ClipboardSnapshot.capture(backend)

        assert snapshot.content == "hello"
        assert snapshot.has_content is True

    def test_capture_empty(self) -> None:
        """Test capturing empty clipboard."""
        backend = FakeClipboard("")
        snapshot = ClipboardSnapshot.capture(backend)

        assert snapshot.content == ""
        assert snapshot.has_content is False

    def test_capture_failure(self) -> None:
        """Test capturing when clipboard throws exception."""

        class BrokenClipboard:
            def paste(self):
                raise RuntimeError("clipboard broken")

        snapshot = ClipboardSnapshot.capture(BrokenClipboard())

        assert snapshot.content is None
        assert snapshot.has_content is False


class TestPlatformAdapters:
    """Test platform adapter classes."""

    def test_windows_adapter_name(self) -> None:
        adapter = WindowsAdapter()
        assert adapter.name == "windows"

    def test_macos_adapter_name(self) -> None:
        adapter = MacOSAdapter()
        assert adapter.name == "macos"

    def test_linux_adapter_name(self) -> None:
        adapter = LinuxAdapter()
        assert adapter.name == "linux"

    def test_get_platform_adapter_windows(self) -> None:
        with mock.patch("sys.platform", "win32"):
            adapter = get_platform_adapter()
        assert isinstance(adapter, WindowsAdapter)

    def test_get_platform_adapter_macos(self) -> None:
        with mock.patch("sys.platform", "darwin"):
            adapter = get_platform_adapter()
        assert isinstance(adapter, MacOSAdapter)

    def test_get_platform_adapter_linux(self) -> None:
        with mock.patch("sys.platform", "linux"):
            adapter = get_platform_adapter()
        assert isinstance(adapter, LinuxAdapter)


class TestTextInjector:
    """Test TextInjector class."""

    def test_inject_normal_text(self) -> None:
        """Test injecting normal text."""
        adapter = FakeAdapter("original clipboard")
        injector = TextInjector(adapter=adapter)

        result = injector.inject("test text")

        assert result is True
        assert adapter._paste_called is True
        # Clipboard should have been restored
        assert adapter._clipboard.paste() == "original clipboard"

    def test_inject_empty_text_skipped(self) -> None:
        """Test that empty text does not trigger injection."""
        adapter = FakeAdapter()
        injector = TextInjector(adapter=adapter)

        result = injector.inject("")

        assert result is False
        assert adapter._paste_called is False

    def test_inject_whitespace_text_skipped(self) -> None:
        """Test that whitespace-only text does not trigger injection."""
        adapter = FakeAdapter()
        injector = TextInjector(adapter=adapter)

        result = injector.inject("   \n\t  ")

        assert result is False
        assert adapter._paste_called is False

    def test_inject_restores_clipboard(self) -> None:
        """Test that original clipboard content is restored after injection."""
        adapter = FakeAdapter("save this")
        injector = TextInjector(adapter=adapter)

        injector.inject("new text")

        # After injection, clipboard should be restored
        assert adapter._clipboard.paste() == "save this"

    def test_inject_with_empty_clipboard(self) -> None:
        """Test injection when clipboard was originally empty."""
        adapter = FakeAdapter("")
        injector = TextInjector(adapter=adapter)

        result = injector.inject("some text")

        assert result is True
        assert adapter._paste_called is True

    def test_inject_copy_failure_returns_false(self) -> None:
        """Test that copy failure returns False."""

        class BrokenCopyAdapter(FakeAdapter):
            def get_clipboard_backend(self):
                backend = FakeClipboard()

                def broken_copy(text):
                    raise RuntimeError("copy failed")

                backend.copy = broken_copy
                return backend

        adapter = BrokenCopyAdapter()
        injector = TextInjector(adapter=adapter)

        result = injector.inject("text")

        assert result is False

    def test_inject_paste_failure_restores_clipboard(self) -> None:
        """Test that clipboard is restored even if paste fails."""

        class FailingPasteAdapter(FakeAdapter):
            def simulate_paste(self) -> bool:
                return False  # Paste fails

        adapter = FailingPasteAdapter("original")
        injector = TextInjector(adapter=adapter)

        result = injector.inject("test")

        assert result is False
        # Clipboard should still be restored
        assert adapter._clipboard.paste() == "original"
