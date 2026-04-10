"""Hotkey listener for noasr using pynput."""

import sys
import threading
from typing import Callable, Optional


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
        """Extract virtual key code from pynput key.

        Returns Windows Virtual Key codes so config values are portable.
        """
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
                # Windows Virtual Key codes
                key_map = {
                    Key.alt_l: 0xA4,  # VK_LMENU = 164
                    Key.alt_r: 0xA5,  # VK_RMENU = 165
                    Key.alt_gr: 0xA5,  # VK_RMENU = 165
                    Key.ctrl_l: 0xA2,  # VK_LCONTROL = 162
                    Key.ctrl_r: 0xA3,  # VK_RCONTROL = 163
                    Key.f1: 0x70,  # VK_F1 = 112
                    Key.f2: 0x71,  # VK_F2 = 113
                    Key.f3: 0x72,  # VK_F3 = 114
                    Key.f4: 0x73,  # VK_F4 = 115
                    Key.f5: 0x74,  # VK_F5 = 116
                    Key.f6: 0x75,  # VK_F6 = 117
                    Key.f7: 0x76,  # VK_F7 = 118
                    Key.f8: 0x77,  # VK_F8 = 119
                    Key.f9: 0x78,  # VK_F9 = 120
                    Key.f10: 0x79,  # VK_F10 = 121
                    Key.f11: 0x7A,  # VK_F11 = 122
                    Key.f12: 0x7B,  # VK_F12 = 123
                    Key.space: 0x20,  # VK_SPACE = 32
                    Key.tab: 0x09,  # VK_TAB = 9
                    Key.enter: 0x0D,  # VK_RETURN = 13
                    Key.shift: 0x10,  # VK_SHIFT = 16
                    Key.shift_l: 0xA0,  # VK_LSHIFT = 160
                    Key.shift_r: 0xA1,  # VK_RSHIFT = 161
                    Key.caps_lock: 0x14,  # VK_CAPITAL = 20
                    Key.cmd: 0x5B,  # VK_LWIN = 91
                    Key.cmd_l: 0x5B,  # VK_LWIN = 91
                    Key.cmd_r: 0x5C,  # VK_RWIN = 92
                }
                return key_map.get(key)
        except Exception:
            pass
        return None

    @property
    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._running
