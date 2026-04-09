"""Tests for overlay UI controller."""

import sys
import threading
from unittest import mock

import pytest

from noasr.models import OverlayState
from noasr.overlay import OverlayController


class TestOverlayControllerInitialState:
    """Test OverlayController initial state."""

    def test_initial_state_is_hidden(self) -> None:
        """Test that a new OverlayController starts in HIDDEN state."""
        ctrl = OverlayController()
        assert ctrl.state == OverlayState.HIDDEN

    def test_initial_elapsed_is_zero(self) -> None:
        """Test that initial elapsed seconds is 0.0."""
        ctrl = OverlayController()
        assert ctrl._elapsed_seconds == 0.0

    def test_initial_page_is_none(self) -> None:
        """Test that initial page is None."""
        ctrl = OverlayController()
        assert ctrl._page is None

    def test_initial_text_control_is_none(self) -> None:
        """Test that initial text control is None."""
        ctrl = OverlayController()
        assert ctrl._text_control is None

    def test_initial_running_is_false(self) -> None:
        """Test that initial running flag is False."""
        ctrl = OverlayController()
        assert ctrl._running is False

    def test_initial_thread_is_none(self) -> None:
        """Test that initial app thread is None."""
        ctrl = OverlayController()
        assert ctrl._app_thread is None


class TestOverlayControllerShowListening:
    """Test OverlayController.show_listening()."""

    def test_sets_state_to_listening(self) -> None:
        """Test that show_listening sets state to LISTENING."""
        ctrl = OverlayController()
        ctrl.show_listening(elapsed=5.0)
        assert ctrl.state == OverlayState.LISTENING

    def test_stores_elapsed_time(self) -> None:
        """Test that show_listening stores the elapsed time."""
        ctrl = OverlayController()
        ctrl.show_listening(elapsed=42.5)
        assert ctrl._elapsed_seconds == 42.5

    def test_default_elapsed_is_zero(self) -> None:
        """Test that show_listening defaults elapsed to 0.0."""
        ctrl = OverlayController()
        ctrl.show_listening()
        assert ctrl._elapsed_seconds == 0.0

    def test_overrides_previous_state(self) -> None:
        """Test that show_listening overrides a previous non-LISTENING state."""
        ctrl = OverlayController()
        ctrl.show_loading()
        assert ctrl.state == OverlayState.LOADING
        ctrl.show_listening(elapsed=1.0)
        assert ctrl.state == OverlayState.LISTENING


class TestOverlayControllerShowLoading:
    """Test OverlayController.show_loading()."""

    def test_sets_state_to_loading(self) -> None:
        """Test that show_loading sets state to LOADING."""
        ctrl = OverlayController()
        ctrl.show_loading()
        assert ctrl.state == OverlayState.LOADING


class TestOverlayControllerShowError:
    """Test OverlayController.show_error()."""

    def test_sets_state_to_error(self) -> None:
        """Test that show_error sets state to ERROR."""
        ctrl = OverlayController()
        ctrl.show_error()
        assert ctrl.state == OverlayState.ERROR


class TestOverlayControllerHide:
    """Test OverlayController.hide()."""

    def test_sets_state_to_hidden(self) -> None:
        """Test that hide sets state to HIDDEN."""
        ctrl = OverlayController()
        ctrl.show_listening()
        ctrl.hide()
        assert ctrl.state == OverlayState.HIDDEN

    def test_hide_from_loading(self) -> None:
        """Test that hide transitions from LOADING to HIDDEN."""
        ctrl = OverlayController()
        ctrl.show_loading()
        ctrl.hide()
        assert ctrl.state == OverlayState.HIDDEN

    def test_hide_from_error(self) -> None:
        """Test that hide transitions from ERROR to HIDDEN."""
        ctrl = OverlayController()
        ctrl.show_error()
        ctrl.hide()
        assert ctrl.state == OverlayState.HIDDEN


class TestOverlayControllerUpdateElapsed:
    """Test OverlayController.update_elapsed()."""

    def test_updates_elapsed_when_listening(self) -> None:
        """Test that update_elapsed updates time when state is LISTENING."""
        ctrl = OverlayController()
        ctrl.show_listening(elapsed=0.0)
        ctrl.update_elapsed(elapsed=10.0)
        assert ctrl._elapsed_seconds == 10.0

    def test_does_not_update_display_when_not_listening(self) -> None:
        """Test that update_elapsed does not call _update_display when not LISTENING."""
        ctrl = OverlayController()
        ctrl.show_loading()
        ctrl._update_display = mock.MagicMock()
        ctrl.update_elapsed(elapsed=5.0)
        ctrl._update_display.assert_not_called()

    def test_stores_elapsed_even_when_not_listening(self) -> None:
        """Test that update_elapsed stores the value even if state is not LISTENING."""
        ctrl = OverlayController()
        ctrl.show_loading()
        ctrl.update_elapsed(elapsed=7.5)
        assert ctrl._elapsed_seconds == 7.5

    def test_calls_update_display_when_listening(self) -> None:
        """Test that update_elapsed calls _update_display when state is LISTENING."""
        ctrl = OverlayController()
        ctrl.show_listening(elapsed=0.0)
        ctrl._update_display = mock.MagicMock()
        ctrl.update_elapsed(elapsed=3.0)
        ctrl._update_display.assert_called_once()


class TestOverlayControllerFormatTime:
    """Test OverlayController._format_time()."""

    def test_zero_seconds(self) -> None:
        """Test formatting zero seconds."""
        ctrl = OverlayController()
        assert ctrl._format_time(0) == "00:00"

    def test_less_than_sixty_seconds(self) -> None:
        """Test formatting seconds less than 60."""
        ctrl = OverlayController()
        assert ctrl._format_time(45) == "00:45"

    def test_exactly_sixty_seconds(self) -> None:
        """Test formatting exactly 60 seconds."""
        ctrl = OverlayController()
        assert ctrl._format_time(60) == "01:00"

    def test_over_sixty_seconds(self) -> None:
        """Test formatting seconds over 60."""
        ctrl = OverlayController()
        assert ctrl._format_time(125) == "02:05"

    def test_large_value(self) -> None:
        """Test formatting a large number of seconds."""
        ctrl = OverlayController()
        assert ctrl._format_time(3661) == "61:01"

    def test_float_truncation(self) -> None:
        """Test that float values are truncated to int."""
        ctrl = OverlayController()
        assert ctrl._format_time(59.9) == "00:59"

    def test_single_digit_minutes(self) -> None:
        """Test that single-digit minutes are zero-padded."""
        ctrl = OverlayController()
        assert ctrl._format_time(90) == "01:30"


class TestOverlayControllerGetDisplayText:
    """Test OverlayController._get_display_text()."""

    def test_listening_state_text(self) -> None:
        """Test display text for LISTENING state."""
        ctrl = OverlayController()
        ctrl._state = OverlayState.LISTENING
        ctrl._elapsed_seconds = 65.0
        assert ctrl._get_display_text() == "Listening 01:05"

    def test_listening_zero_elapsed(self) -> None:
        """Test display text for LISTENING with zero elapsed."""
        ctrl = OverlayController()
        ctrl._state = OverlayState.LISTENING
        ctrl._elapsed_seconds = 0.0
        assert ctrl._get_display_text() == "Listening 00:00"

    def test_loading_state_text(self) -> None:
        """Test display text for LOADING state."""
        ctrl = OverlayController()
        ctrl._state = OverlayState.LOADING
        assert ctrl._get_display_text() == "Loading"

    def test_error_state_text(self) -> None:
        """Test display text for ERROR state."""
        ctrl = OverlayController()
        ctrl._state = OverlayState.ERROR
        assert ctrl._get_display_text() == "Error"

    def test_hidden_state_text(self) -> None:
        """Test display text for HIDDEN state returns empty string."""
        ctrl = OverlayController()
        ctrl._state = OverlayState.HIDDEN
        assert ctrl._get_display_text() == ""


class TestOverlayControllerStart:
    """Test OverlayController.start()."""

    def test_sets_running_to_true(self) -> None:
        """Test that start sets running flag to True."""
        ctrl = OverlayController()
        with mock.patch.object(ctrl, "_run_app"):
            ctrl.start()
        assert ctrl._running is True

    def test_creates_daemon_thread(self) -> None:
        """Test that start creates a daemon thread."""
        ctrl = OverlayController()
        with mock.patch.object(ctrl, "_run_app"):
            ctrl.start()
        assert ctrl._app_thread is not None
        assert ctrl._app_thread.daemon is True

    def test_starts_the_thread(self) -> None:
        """Test that start actually starts the thread."""
        ctrl = OverlayController()
        with mock.patch.object(ctrl, "_run_app"):
            ctrl.start()
        assert ctrl._app_thread is not None
        assert ctrl._app_thread.is_alive() or ctrl._app_thread.ident is not None

    def test_does_not_start_if_already_running(self) -> None:
        """Test that start is a no-op when already running."""
        ctrl = OverlayController()
        ctrl._running = True
        old_thread = ctrl._app_thread
        ctrl.start()
        assert ctrl._app_thread is old_thread


class TestOverlayControllerStop:
    """Test OverlayController.stop()."""

    def test_sets_running_to_false(self) -> None:
        """Test that stop sets running flag to False."""
        ctrl = OverlayController()
        ctrl._running = True
        ctrl.stop()
        assert ctrl._running is False

    def test_sets_state_to_hidden(self) -> None:
        """Test that stop sets state to HIDDEN."""
        ctrl = OverlayController()
        ctrl._state = OverlayState.LISTENING
        ctrl.stop()
        assert ctrl.state == OverlayState.HIDDEN

    def test_stop_from_listening(self) -> None:
        """Test stopping from LISTENING state."""
        ctrl = OverlayController()
        ctrl.show_listening(elapsed=5.0)
        ctrl.stop()
        assert ctrl._running is False
        assert ctrl.state == OverlayState.HIDDEN

    def test_stop_from_loading(self) -> None:
        """Test stopping from LOADING state."""
        ctrl = OverlayController()
        ctrl.show_loading()
        ctrl.stop()
        assert ctrl._running is False
        assert ctrl.state == OverlayState.HIDDEN


class TestOverlayControllerUpdateDisplay:
    """Test OverlayController._update_display()."""

    def test_handles_page_none_gracefully(self) -> None:
        """Test that _update_display does not raise when page is None."""
        ctrl = OverlayController()
        ctrl._page = None
        ctrl._text_control = None
        # Should not raise
        ctrl._update_display()

    def test_handles_text_control_none_gracefully(self) -> None:
        """Test that _update_display does not raise when text_control is None."""
        ctrl = OverlayController()
        ctrl._page = mock.MagicMock()
        ctrl._text_control = None
        # Should not raise
        ctrl._update_display()

    def test_updates_text_control_value(self) -> None:
        """Test that _update_display sets text control value."""
        ctrl = OverlayController()
        ctrl._state = OverlayState.LISTENING
        ctrl._elapsed_seconds = 30.0
        ctrl._page = mock.MagicMock()
        ctrl._text_control = mock.MagicMock()
        ctrl._update_display()
        assert ctrl._text_control.value == "Listening 00:30"

    def test_sets_window_visible_true_when_not_hidden(self) -> None:
        """Test that _update_display sets window visible to True when not HIDDEN."""
        ctrl = OverlayController()
        ctrl._state = OverlayState.LOADING
        ctrl._page = mock.MagicMock()
        ctrl._text_control = mock.MagicMock()
        ctrl._update_display()
        assert ctrl._page.window.visible is True

    def test_sets_window_visible_false_when_hidden(self) -> None:
        """Test that _update_display sets window visible to False when HIDDEN."""
        ctrl = OverlayController()
        ctrl._state = OverlayState.HIDDEN
        ctrl._page = mock.MagicMock()
        ctrl._text_control = mock.MagicMock()
        ctrl._update_display()
        assert ctrl._page.window.visible is False

    def test_calls_page_update(self) -> None:
        """Test that _update_display calls page.update()."""
        ctrl = OverlayController()
        ctrl._state = OverlayState.LOADING
        ctrl._page = mock.MagicMock()
        ctrl._text_control = mock.MagicMock()
        ctrl._update_display()
        ctrl._page.update.assert_called_once()

    def test_handles_page_update_exception(self) -> None:
        """Test that _update_display swallows exceptions from page.update()."""
        ctrl = OverlayController()
        ctrl._state = OverlayState.LOADING
        ctrl._page = mock.MagicMock()
        ctrl._text_control = mock.MagicMock()
        ctrl._page.update.side_effect = RuntimeError("page gone")
        # Should not raise
        ctrl._update_display()


class TestOverlayControllerStateTransitions:
    """Test full state transition sequences."""

    def test_full_lifecycle(self) -> None:
        """Test a typical lifecycle: hidden -> listening -> loading -> hidden."""
        ctrl = OverlayController()
        assert ctrl.state == OverlayState.HIDDEN

        ctrl.show_listening(elapsed=0.0)
        assert ctrl.state == OverlayState.LISTENING

        ctrl.show_loading()
        assert ctrl.state == OverlayState.LOADING

        ctrl.hide()
        assert ctrl.state == OverlayState.HIDDEN

    def test_error_then_hide(self) -> None:
        """Test error then hide transition."""
        ctrl = OverlayController()
        ctrl.show_error()
        assert ctrl.state == OverlayState.ERROR
        ctrl.hide()
        assert ctrl.state == OverlayState.HIDDEN

    def test_listening_with_elapsed_updates(self) -> None:
        """Test listening state with multiple elapsed updates."""
        ctrl = OverlayController()
        ctrl.show_listening(elapsed=0.0)
        assert ctrl._elapsed_seconds == 0.0

        ctrl.update_elapsed(elapsed=5.0)
        assert ctrl._elapsed_seconds == 5.0
        assert ctrl.state == OverlayState.LISTENING

        ctrl.update_elapsed(elapsed=10.0)
        assert ctrl._elapsed_seconds == 10.0
