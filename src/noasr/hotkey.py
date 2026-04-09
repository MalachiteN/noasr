"""Hotkey listener for noasr using pynput."""

import sys
import threading
from typing import Callable, Optional

from noasr.models import OverlayState


class HotkeyListener:
    """Listens for global hotkey press/release using pynput.

    Event-driven (not polling). On key press, calls on_key_down callback.
    On key release, calls on_key_up callback.
    """

    def __init__(
        self,
        on_key_down: Optional[Callable[[int], None]] = None,
        on_key_up: Optional[Callable[[int], None]] = None,
    ) -> None:
        self._on_key_down = on_key_down
        self._on_key_up = on_key_up
        self._listener = None
        self._running = False
        self._pressed_key: Optional[int] = None

    def start(self) -> bool:
        """Start listening for hotkeys.

        Returns:
            True if listener started successfully, False otherwise.
        """
        if self._running:
            return True

        try:
            from pynput import keyboard

            def on_press(key) -> None:
                try:
                    vk = self._get_key_code(key)
                    if vk is not None and self._on_key_down:
                        self._on_key_down(vk)
                except Exception:
                    pass

            def on_release(key) -> None:
                try:
                    vk = self._get_key_code(key)
                    if vk is not None and self._on_key_up:
                        self._on_key_up(vk)
                except Exception:
                    pass

            self._listener = keyboard.Listener(
                on_press=on_press,
                on_release=on_release,
            )
            self._listener.daemon = True
            self._listener.start()
            self._running = True
            return True
        except Exception as e:
            print(f"Failed to start hotkey listener: {e}", file=sys.stderr)
            return False

    def stop(self) -> None:
        """Stop listening for hotkeys."""
        self._running = False
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def _get_key_code(self, key) -> Optional[int]:
        """Extract virtual key code from pynput key."""
        try:
            from pynput.keyboard import KeyCode, Key

            if isinstance(key, KeyCode):
                return (
                    key.vk
                    if hasattr(key, "vk") and key.vk
                    else ord(key.char)
                    if hasattr(key, "char") and key.char
                    else None
                )
            elif isinstance(key, Key):
                # Map common keys to virtual key codes
                key_map = {
                    Key.alt_l: 56,
                    Key.alt_r: 62,
                    Key.ctrl_l: 29,
                    Key.ctrl_r: 63,
                    Key.f1: 59,
                    Key.f2: 60,
                    Key.f3: 61,
                    Key.f4: 62,
                    Key.f5: 63,
                    Key.f6: 64,
                    Key.f7: 65,
                    Key.f8: 66,
                    Key.f9: 67,
                    Key.f10: 68,
                    Key.f11: 87,
                    Key.f12: 88,
                    Key.space: 57,
                    Key.tab: 15,
                    Key.enter: 28,
                    Key.shift: 42,
                }
                return key_map.get(key)
        except Exception:
            pass
        return None

    @property
    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._running
