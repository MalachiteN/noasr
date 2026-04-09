"""Clipboard-preserving text injection service for noasr."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import logging
import time

logger = logging.getLogger(__name__)


@dataclass
class ClipboardSnapshot:
    """Snapshot of clipboard state."""

    content: Optional[str] = None
    has_content: bool = False

    @classmethod
    def capture(cls, clipboard_backend) -> "ClipboardSnapshot":
        """Capture current clipboard state."""
        try:
            content = clipboard_backend.paste()
            return cls(
                content=content,
                has_content=content is not None and len(content) > 0,
            )
        except Exception as e:
            logger.warning("Failed to capture clipboard: %s", e)
            return cls(content=None, has_content=False)


class PlatformAdapter(ABC):
    """Abstract base class for platform-specific injection adapters."""

    @abstractmethod
    def simulate_paste(self) -> bool:
        """Simulate paste keyboard shortcut.

        Returns:
            True if paste simulation succeeded, False otherwise.
        """
        pass

    @abstractmethod
    def get_clipboard_backend(self):
        """Get platform-appropriate clipboard backend.

        Returns:
            Clipboard backend object with paste() and copy() methods.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform adapter name."""
        pass


class WindowsAdapter(PlatformAdapter):
    """Windows platform adapter using pynput for key simulation."""

    def __init__(self) -> None:
        self._clipboard_backend = None
        self._keyboard_controller = None

    @property
    def name(self) -> str:
        return "windows"

    def _get_keyboard(self):
        """Lazy-load keyboard controller."""
        if self._keyboard_controller is None:
            from pynput.keyboard import Controller

            self._keyboard_controller = Controller()
        return self._keyboard_controller

    def get_clipboard_backend(self):
        """Get pyperclip clipboard backend."""
        if self._clipboard_backend is None:
            import pyperclip

            self._clipboard_backend = pyperclip
        return self._clipboard_backend

    def simulate_paste(self) -> bool:
        """Simulate Ctrl+V paste on Windows."""
        try:
            from pynput.keyboard import Key, Controller

            keyboard = self._get_keyboard()
            keyboard.press(Key.ctrl)
            keyboard.press("v")
            time.sleep(0.05)
            keyboard.release("v")
            keyboard.release(Key.ctrl)
            return True
        except Exception as e:
            logger.error("Failed to simulate paste on Windows: %s", e)
            return False


class MacOSAdapter(PlatformAdapter):
    """macOS platform adapter (placeholder for future implementation)."""

    @property
    def name(self) -> str:
        return "macos"

    def get_clipboard_backend(self):
        """Get pyperclip clipboard backend."""
        import pyperclip

        return pyperclip

    def simulate_paste(self) -> bool:
        """Simulate Cmd+V paste on macOS."""
        try:
            from pynput.keyboard import Key, Controller

            keyboard = Controller()
            keyboard.press(Key.cmd)
            keyboard.press("v")
            time.sleep(0.05)
            keyboard.release("v")
            keyboard.release(Key.cmd)
            return True
        except Exception as e:
            logger.error("Failed to simulate paste on macOS: %s", e)
            return False


class LinuxAdapter(PlatformAdapter):
    """Linux platform adapter (placeholder for future implementation)."""

    @property
    def name(self) -> str:
        return "linux"

    def get_clipboard_backend(self):
        """Get pyperclip clipboard backend."""
        import pyperclip

        return pyperclip

    def simulate_paste(self) -> bool:
        """Simulate Ctrl+V paste on Linux."""
        try:
            from pynput.keyboard import Key, Controller

            keyboard = Controller()
            keyboard.press(Key.ctrl)
            keyboard.press("v")
            time.sleep(0.05)
            keyboard.release("v")
            keyboard.release(Key.ctrl)
            return True
        except Exception as e:
            logger.error("Failed to simulate paste on Linux: %s", e)
            return False


def get_platform_adapter() -> PlatformAdapter:
    """Get the appropriate platform adapter for the current OS."""
    import sys

    if sys.platform == "win32":
        return WindowsAdapter()
    elif sys.platform == "darwin":
        return MacOSAdapter()
    else:
        return LinuxAdapter()


class TextInjector:
    """Text injection service that preserves clipboard content."""

    def __init__(self, adapter: Optional[PlatformAdapter] = None) -> None:
        self._adapter = adapter or get_platform_adapter()
        self._clipboard_backend = self._adapter.get_clipboard_backend()

    def inject(self, text: str) -> bool:
        """Inject text into the currently focused application.

        1. Save current clipboard contents.
        2. Copy the text to clipboard.
        3. Simulate paste.
        4. Attempt to restore original clipboard contents.

        Args:
            text: The text to inject.

        Returns:
            True if injection succeeded, False otherwise.
        """
        if not text or not text.strip():
            logger.debug("Skipping injection: empty text")
            return False

        # Step 1: Save clipboard
        snapshot = ClipboardSnapshot.capture(self._clipboard_backend)

        # Step 2: Copy text to clipboard
        try:
            self._clipboard_backend.copy(text)
        except Exception as e:
            logger.error("Failed to copy text to clipboard: %s", e)
            return False

        # Step 3: Simulate paste
        time.sleep(0.05)  # Small delay to ensure clipboard is set
        paste_ok = self._adapter.simulate_paste()

        if not paste_ok:
            logger.error("Paste simulation failed")
            self._restore_clipboard(snapshot)
            return False

        # Step 4: Restore original clipboard
        time.sleep(0.1)  # Wait for paste to complete before restoring
        self._restore_clipboard(snapshot)

        return True

    def _restore_clipboard(self, snapshot: ClipboardSnapshot) -> None:
        """Attempt to restore clipboard from snapshot."""
        if not snapshot.has_content or snapshot.content is None:
            return

        try:
            self._clipboard_backend.copy(snapshot.content)
        except Exception as e:
            logger.warning("Failed to restore clipboard: %s", e)
