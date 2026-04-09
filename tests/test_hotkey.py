"""Tests for HotkeyListener."""

import enum
import sys
from unittest import mock

import pytest

from noasr.hotkey import HotkeyListener


# ---------------------------------------------------------------------------
# Helpers: fake pynput types used across tests
# ---------------------------------------------------------------------------


class _FakeKeyCode:
    """Minimal stand-in for pynput.keyboard.KeyCode.

    Must be a real class so that isinstance() checks in _get_key_code work.
    """

    def __init__(self, vk=None, char=None):
        self.vk = vk
        self.char = char


# Use a real Enum so isinstance(key, Key) works inside _get_key_code.
class _FakeKey(enum.Enum):
    """Stand-in for pynput.keyboard.Key enum."""

    alt_l = "alt_l"
    alt_r = "alt_r"
    ctrl_l = "ctrl_l"
    ctrl_r = "ctrl_r"
    f1 = "f1"
    f2 = "f2"
    f3 = "f3"
    f4 = "f4"
    f5 = "f5"
    f6 = "f6"
    f7 = "f7"
    f8 = "f8"
    f9 = "f9"
    f10 = "f10"
    f11 = "f11"
    f12 = "f12"
    space = "space"
    tab = "tab"
    enter = "enter"
    shift = "shift"
    caps_lock = "caps_lock"  # extra member for "unknown key" test


# Build a fake ``pynput.keyboard`` module that HotkeyListener imports at
# runtime via ``from pynput import keyboard`` / ``from pynput.keyboard import …``.


def _make_fake_keyboard_module():
    """Return a fake ``pynput.keyboard`` module with Listener, KeyCode, Key."""

    fake_key_module = mock.MagicMock(name="pynput.keyboard")

    # KeyCode class — must be a real class for isinstance()
    fake_key_module.KeyCode = _FakeKeyCode

    # Key enum — must be a real Enum for isinstance()
    fake_key_module.Key = _FakeKey

    # Listener class — MagicMock is fine, we just check call args
    fake_key_module.Listener = mock.MagicMock(name="Listener")
    return fake_key_module


def _install_fake_pynput():
    """Install fake pynput modules into sys.modules and return the keyboard fake."""
    fake_kb = _make_fake_keyboard_module()
    fake_pynput = mock.MagicMock(name="pynput")
    fake_pynput.keyboard = fake_kb
    sys.modules["pynput"] = fake_pynput
    sys.modules["pynput.keyboard"] = fake_kb
    return fake_kb


def _remove_fake_pynput():
    """Remove fake pynput modules from sys.modules."""
    sys.modules.pop("pynput", None)
    sys.modules.pop("pynput.keyboard", None)


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


class TestHotkeyListenerInit:
    """Test HotkeyListener initial state and constructor."""

    def test_initial_state_not_running(self) -> None:
        """Newly created listener is not running."""
        listener = HotkeyListener()
        assert listener.is_running is False

    def test_initial_state_no_listener(self) -> None:
        """Newly created listener has no internal listener object."""
        listener = HotkeyListener()
        assert listener._listener is None

    def test_constructor_accepts_on_key_down(self) -> None:
        """Constructor stores on_key_down callback."""
        cb = mock.MagicMock()
        listener = HotkeyListener(on_key_down=cb)
        assert listener._on_key_down is cb

    def test_constructor_accepts_on_key_up(self) -> None:
        """Constructor stores on_key_up callback."""
        cb = mock.MagicMock()
        listener = HotkeyListener(on_key_up=cb)
        assert listener._on_key_up is cb

    def test_constructor_defaults_callbacks_to_none(self) -> None:
        """Constructor defaults both callbacks to None."""
        listener = HotkeyListener()
        assert listener._on_key_down is None
        assert listener._on_key_up is None


class TestHotkeyListenerStart:
    """Test HotkeyListener.start() behaviour."""

    def setup_method(self) -> None:
        self.fake_kb = _install_fake_pynput()

    def teardown_method(self) -> None:
        _remove_fake_pynput()

    def test_start_returns_true(self) -> None:
        """start() returns True on success."""
        listener = HotkeyListener()
        assert listener.start() is True

    def test_start_sets_is_running(self) -> None:
        """start() sets is_running to True."""
        listener = HotkeyListener()
        listener.start()
        assert listener.is_running is True

    def test_start_creates_listener(self) -> None:
        """start() creates a pynput.keyboard.Listener."""
        listener = HotkeyListener()
        listener.start()
        self.fake_kb.Listener.assert_called_once()

    def test_start_sets_listener_daemon(self) -> None:
        """start() sets the listener thread as daemon."""
        listener = HotkeyListener()
        listener.start()
        mock_listener = self.fake_kb.Listener.return_value
        assert mock_listener.daemon is True

    def test_start_calls_listener_start(self) -> None:
        """start() calls listener.start()."""
        listener = HotkeyListener()
        listener.start()
        mock_listener = self.fake_kb.Listener.return_value
        mock_listener.start.assert_called_once()

    def test_start_when_already_running_returns_true(self) -> None:
        """start() when already running returns True without creating a new listener."""
        listener = HotkeyListener()
        listener.start()
        assert listener.start() is True
        # Listener should only have been created once
        assert self.fake_kb.Listener.call_count == 1


class TestHotkeyListenerStop:
    """Test HotkeyListener.stop() behaviour."""

    def setup_method(self) -> None:
        self.fake_kb = _install_fake_pynput()

    def teardown_method(self) -> None:
        _remove_fake_pynput()

    def test_stop_sets_is_running_false(self) -> None:
        """stop() sets is_running to False."""
        listener = HotkeyListener()
        listener.start()
        listener.stop()
        assert listener.is_running is False

    def test_stop_calls_listener_stop(self) -> None:
        """stop() calls the underlying listener's stop()."""
        listener = HotkeyListener()
        listener.start()
        mock_listener = self.fake_kb.Listener.return_value
        listener.stop()
        mock_listener.stop.assert_called_once()

    def test_stop_clears_listener_reference(self) -> None:
        """stop() sets _listener to None."""
        listener = HotkeyListener()
        listener.start()
        listener.stop()
        assert listener._listener is None

    def test_stop_when_not_running_is_safe(self) -> None:
        """stop() when not running does not crash."""
        listener = HotkeyListener()
        listener.stop()  # Should not raise
        assert listener.is_running is False

    def test_stop_handles_listener_stop_exception(self) -> None:
        """stop() swallows exceptions from listener.stop()."""
        listener = HotkeyListener()
        listener.start()
        mock_listener = self.fake_kb.Listener.return_value
        mock_listener.stop.side_effect = RuntimeError("boom")
        listener.stop()  # Should not raise
        assert listener._listener is None


class TestHotkeyListenerGetKeyCode:
    """Test HotkeyListener._get_key_code() behaviour."""

    def setup_method(self) -> None:
        _install_fake_pynput()

    def teardown_method(self) -> None:
        _remove_fake_pynput()

    def test_keycode_with_vk_returns_vk(self) -> None:
        """_get_key_code returns vk when KeyCode has vk attribute."""
        listener = HotkeyListener()
        key = _FakeKeyCode(vk=65)
        assert listener._get_key_code(key) == 65

    def test_keycode_with_char_returns_ord(self) -> None:
        """_get_key_code returns ord(char) when KeyCode has char but no vk."""
        listener = HotkeyListener()
        key = _FakeKeyCode(char="A")
        assert listener._get_key_code(key) == ord("A")

    def test_keycode_with_vk_and_char_prefers_vk(self) -> None:
        """_get_key_code prefers vk over char when both are present."""
        listener = HotkeyListener()
        key = _FakeKeyCode(vk=99, char="A")
        assert listener._get_key_code(key) == 99

    def test_keycode_with_no_vk_no_char_returns_none(self) -> None:
        """_get_key_code returns None when KeyCode has neither vk nor char."""
        listener = HotkeyListener()
        key = _FakeKeyCode()
        assert listener._get_key_code(key) is None

    def test_key_enum_maps_to_virtual_key_code(self) -> None:
        """_get_key_code maps Key enum values to virtual key codes."""
        listener = HotkeyListener()
        # Access the fake Key members from sys.modules
        from pynput.keyboard import Key

        assert listener._get_key_code(Key.alt_l) == 56
        assert listener._get_key_code(Key.alt_r) == 62
        assert listener._get_key_code(Key.ctrl_l) == 29
        assert listener._get_key_code(Key.ctrl_r) == 63
        assert listener._get_key_code(Key.f1) == 59
        assert listener._get_key_code(Key.f12) == 88
        assert listener._get_key_code(Key.space) == 57
        assert listener._get_key_code(Key.tab) == 15
        assert listener._get_key_code(Key.enter) == 28
        assert listener._get_key_code(Key.shift) == 42

    def test_unknown_key_returns_none(self) -> None:
        """_get_key_code returns None for unknown key types."""
        listener = HotkeyListener()
        assert listener._get_key_code("not_a_key") is None

    def test_unknown_key_enum_returns_none(self) -> None:
        """_get_key_code returns None for Key enum values not in the map."""
        listener = HotkeyListener()
        # caps_lock is in our fake enum but not in the key_map inside _get_key_code
        assert listener._get_key_code(_FakeKey.caps_lock) is None


class TestHotkeyListenerCallbacks:
    """Test that key press/release callbacks are invoked correctly."""

    def setup_method(self) -> None:
        self.fake_kb = _install_fake_pynput()

    def teardown_method(self) -> None:
        _remove_fake_pynput()

    def _capture_callbacks(self) -> dict:
        """Start a listener and return the on_press/on_release callbacks passed to Listener."""
        on_down = mock.MagicMock()
        on_up = mock.MagicMock()
        listener = HotkeyListener(on_key_down=on_down, on_key_up=on_up)
        listener.start()

        call_kwargs = self.fake_kb.Listener.call_args
        return {
            "on_press": call_kwargs.kwargs.get("on_press")
            or call_kwargs[1].get("on_press"),
            "on_release": call_kwargs.kwargs.get("on_release")
            or call_kwargs[1].get("on_release"),
            "on_down": on_down,
            "on_up": on_up,
        }

    def test_key_press_invokes_on_key_down(self) -> None:
        """Key press callback invokes on_key_down with the key code."""
        cbs = self._capture_callbacks()
        key = _FakeKeyCode(vk=65)
        cbs["on_press"](key)
        cbs["on_down"].assert_called_once_with(65)

    def test_key_release_invokes_on_key_up(self) -> None:
        """Key release callback invokes on_key_up with the key code."""
        cbs = self._capture_callbacks()
        key = _FakeKeyCode(vk=65)
        cbs["on_release"](key)
        cbs["on_up"].assert_called_once_with(65)

    def test_key_press_with_unknown_key_does_not_invoke_callback(self) -> None:
        """Key press with unknown key does not invoke on_key_down."""
        cbs = self._capture_callbacks()
        cbs["on_press"]("unknown")
        cbs["on_down"].assert_not_called()

    def test_key_release_with_unknown_key_does_not_invoke_callback(self) -> None:
        """Key release with unknown key does not invoke on_key_up."""
        cbs = self._capture_callbacks()
        cbs["on_release"]("unknown")
        cbs["on_up"].assert_not_called()

    def test_key_press_callback_handles_exception(self) -> None:
        """Key press callback does not crash when on_key_down raises."""
        cbs = self._capture_callbacks()
        cbs["on_down"].side_effect = RuntimeError("boom")
        key = _FakeKeyCode(vk=65)
        cbs["on_press"](key)  # Should not raise

    def test_key_release_callback_handles_exception(self) -> None:
        """Key release callback does not crash when on_key_up raises."""
        cbs = self._capture_callbacks()
        cbs["on_up"].side_effect = RuntimeError("boom")
        key = _FakeKeyCode(vk=65)
        cbs["on_release"](key)  # Should not raise

    def test_no_callback_does_not_crash_on_press(self) -> None:
        """Key press with no on_key_down callback does not crash."""
        listener = HotkeyListener()
        listener.start()
        call_kwargs = self.fake_kb.Listener.call_args
        on_press = call_kwargs.kwargs.get("on_press") or call_kwargs[1].get("on_press")
        key = _FakeKeyCode(vk=65)
        on_press(key)  # Should not raise

    def test_no_callback_does_not_crash_on_release(self) -> None:
        """Key release with no on_key_up callback does not crash."""
        listener = HotkeyListener()
        listener.start()
        call_kwargs = self.fake_kb.Listener.call_args
        on_release = call_kwargs.kwargs.get("on_release") or call_kwargs[1].get(
            "on_release"
        )
        key = _FakeKeyCode(vk=65)
        on_release(key)  # Should not raise
