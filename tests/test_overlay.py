"""Tests for overlay UI controller."""

import queue
from unittest import mock

import pytest

from noasr.models import OverlayState
from noasr.overlay import OverlayController, OverlayError


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

    def test_initial_update_queue_is_empty(self) -> None:
        """Test that initial update queue is empty."""
        ctrl = OverlayController()
        assert ctrl._update_queue.empty()


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

    def test_enqueues_state_and_elapsed(self) -> None:
        """Test that show_listening enqueues (LISTENING, elapsed) on the queue."""
        ctrl = OverlayController()
        ctrl.show_listening(elapsed=5.0)
        assert ctrl._update_queue.qsize() == 1
        assert ctrl._update_queue.get_nowait() == (OverlayState.LISTENING, 5.0)

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

    def test_enqueues_loading_state(self) -> None:
        """Test that show_loading enqueues (LOADING, 0.0) on the queue."""
        ctrl = OverlayController()
        ctrl.show_loading()
        assert ctrl._update_queue.qsize() == 1
        assert ctrl._update_queue.get_nowait() == (OverlayState.LOADING, 0.0)


class TestOverlayControllerShowError:
    """Test OverlayController.show_error()."""

    def test_sets_state_to_error(self) -> None:
        """Test that show_error sets state to ERROR."""
        ctrl = OverlayController()
        ctrl.show_error()
        assert ctrl.state == OverlayState.ERROR

    def test_enqueues_error_state(self) -> None:
        """Test that show_error enqueues (ERROR, 0.0) on the queue."""
        ctrl = OverlayController()
        ctrl.show_error()
        assert ctrl._update_queue.qsize() == 1
        assert ctrl._update_queue.get_nowait() == (OverlayState.ERROR, 0.0)


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

    def test_enqueues_hidden_state(self) -> None:
        """Test that hide enqueues (HIDDEN, 0.0) on the queue."""
        ctrl = OverlayController()
        ctrl.show_listening()
        # Clear the queue from show_listening
        ctrl._update_queue.get_nowait()
        ctrl.hide()
        assert ctrl._update_queue.qsize() == 1
        assert ctrl._update_queue.get_nowait() == (OverlayState.HIDDEN, 0.0)


class TestOverlayControllerUpdateElapsed:
    """Test OverlayController.update_elapsed()."""

    def test_updates_elapsed_when_listening(self) -> None:
        """Test that update_elapsed updates time when state is LISTENING."""
        ctrl = OverlayController()
        ctrl.show_listening(elapsed=0.0)
        ctrl.update_elapsed(elapsed=10.0)
        assert ctrl._elapsed_seconds == 10.0

    def test_enqueues_when_listening(self) -> None:
        """Test that update_elapsed enqueues when state is LISTENING."""
        ctrl = OverlayController()
        ctrl.show_listening(elapsed=0.0)
        # Clear the queue from show_listening
        ctrl._update_queue.get_nowait()
        ctrl.update_elapsed(elapsed=10.0)
        assert ctrl._update_queue.qsize() == 1
        assert ctrl._update_queue.get_nowait() == (OverlayState.LISTENING, 10.0)

    def test_does_not_enqueue_when_not_listening(self) -> None:
        """Test that update_elapsed does not enqueue when state is not LISTENING."""
        ctrl = OverlayController()
        ctrl.show_loading()
        # Clear the queue from show_loading
        ctrl._update_queue.get_nowait()
        ctrl.update_elapsed(elapsed=5.0)
        assert ctrl._update_queue.qsize() == 0

    def test_does_not_update_elapsed_when_not_listening(self) -> None:
        """Test that update_elapsed does not change _elapsed_seconds when not LISTENING."""
        ctrl = OverlayController()
        ctrl.show_loading()
        ctrl.update_elapsed(elapsed=7.5)
        assert ctrl._elapsed_seconds == 0.0


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
    """Test OverlayController._get_display_text(state, elapsed)."""

    def test_listening_state_text(self) -> None:
        """Test display text for LISTENING state with emoji prefix."""
        ctrl = OverlayController()
        result = ctrl._get_display_text(OverlayState.LISTENING, 65.0)
        assert result == "● Listening 01:05"

    def test_listening_zero_elapsed(self) -> None:
        """Test display text for LISTENING with zero elapsed."""
        ctrl = OverlayController()
        result = ctrl._get_display_text(OverlayState.LISTENING, 0.0)
        assert result == "● Listening 00:00"

    def test_loading_state_text(self) -> None:
        """Test display text for LOADING state shows processing emoji."""
        ctrl = OverlayController()
        result = ctrl._get_display_text(OverlayState.LOADING, 0.0)
        assert result == "⏳ Processing"

    def test_error_state_text(self) -> None:
        """Test display text for ERROR state shows error emoji."""
        ctrl = OverlayController()
        result = ctrl._get_display_text(OverlayState.ERROR, 0.0)
        assert result == "❌ Error"

    def test_hidden_state_text(self) -> None:
        """Test display text for HIDDEN state returns empty string."""
        ctrl = OverlayController()
        result = ctrl._get_display_text(OverlayState.HIDDEN, 0.0)
        assert result == ""


class TestOverlayControllerStart:
    """Test OverlayController.start()."""

    def test_sets_running_to_true(self) -> None:
        """Test that start sets running flag to True."""
        ctrl = OverlayController()
        ctrl.start()
        assert ctrl._running is True

    def test_does_not_create_thread(self) -> None:
        """Test that start does not create any thread."""
        ctrl = OverlayController()
        ctrl.start()
        assert not hasattr(ctrl, "_app_thread")

    def test_does_not_start_if_already_running(self) -> None:
        """Test that calling start when already running is idempotent."""
        ctrl = OverlayController()
        ctrl.start()
        assert ctrl._running is True
        ctrl.start()
        assert ctrl._running is True


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


class TestOverlayControllerEnqueue:
    """Test OverlayController._enqueue()."""

    def test_puts_item_on_queue(self) -> None:
        """Test that _enqueue puts (state, elapsed) on the queue."""
        ctrl = OverlayController()
        ctrl._enqueue(OverlayState.LISTENING, 5.0)
        assert ctrl._update_queue.qsize() == 1
        assert ctrl._update_queue.get_nowait() == (OverlayState.LISTENING, 5.0)

    def test_updates_internal_state(self) -> None:
        """Test that _enqueue updates _state and _elapsed_seconds."""
        ctrl = OverlayController()
        ctrl._enqueue(OverlayState.LOADING, 3.0)
        assert ctrl._state == OverlayState.LOADING
        assert ctrl._elapsed_seconds == 3.0

    def test_default_elapsed_is_zero(self) -> None:
        """Test that _enqueue defaults elapsed to 0.0."""
        ctrl = OverlayController()
        ctrl._enqueue(OverlayState.ERROR)
        assert ctrl._update_queue.get_nowait() == (OverlayState.ERROR, 0.0)

    def test_multiple_enqueues(self) -> None:
        """Test that multiple _enqueue calls accumulate on the queue."""
        ctrl = OverlayController()
        ctrl._enqueue(OverlayState.LISTENING, 1.0)
        ctrl._enqueue(OverlayState.LOADING, 2.0)
        ctrl._enqueue(OverlayState.ERROR, 3.0)
        assert ctrl._update_queue.qsize() == 3


class TestOverlayControllerDrainAndApply:
    """Test OverlayController._drain_and_apply()."""

    def test_noop_when_queue_empty(self) -> None:
        """Test that _drain_and_apply does nothing when queue is empty."""
        ctrl = OverlayController()
        ctrl._page = mock.MagicMock()
        ctrl._text_control = mock.MagicMock()
        ctrl._drain_and_apply()
        ctrl._page.update.assert_not_called()

    def test_noop_when_page_is_none(self) -> None:
        """Test that _drain_and_apply does nothing when page is None."""
        ctrl = OverlayController()
        ctrl._enqueue(OverlayState.LISTENING, 5.0)
        ctrl._drain_and_apply()
        # Should not raise

    def test_noop_when_text_control_is_none(self) -> None:
        """Test that _drain_and_apply does nothing when text_control is None."""
        ctrl = OverlayController()
        ctrl._page = mock.MagicMock()
        ctrl._enqueue(OverlayState.LISTENING, 5.0)
        ctrl._drain_and_apply()
        ctrl._page.update.assert_not_called()

    def test_applies_latest_state_to_text_control(self) -> None:
        """Test that _drain_and_apply sets text control value from latest queue item."""
        ctrl = OverlayController()
        ctrl._page = mock.MagicMock()
        ctrl._text_control = mock.MagicMock()
        ctrl._enqueue(OverlayState.LISTENING, 30.0)
        ctrl._drain_and_apply()
        assert ctrl._text_control.value == "● Listening 00:30"

    def test_drains_all_and_applies_only_latest(self) -> None:
        """Test that _drain_and_apply drains all items but applies only the latest."""
        ctrl = OverlayController()
        ctrl._page = mock.MagicMock()
        ctrl._text_control = mock.MagicMock()
        ctrl._enqueue(OverlayState.LISTENING, 10.0)
        ctrl._enqueue(OverlayState.LOADING, 0.0)
        ctrl._drain_and_apply()
        assert ctrl._text_control.value == "⏳ Processing"
        assert ctrl._update_queue.qsize() == 0

    def test_sets_window_opacity_1_when_not_hidden(self) -> None:
        """Test that _drain_and_apply sets window opacity to 1.0 when not HIDDEN."""
        ctrl = OverlayController()
        ctrl._page = mock.MagicMock()
        ctrl._text_control = mock.MagicMock()
        ctrl._enqueue(OverlayState.LOADING, 0.0)
        ctrl._drain_and_apply()
        assert ctrl._page.window.opacity == 1.0

    def test_sets_window_opacity_0_when_hidden(self) -> None:
        """Test that _drain_and_apply sets window opacity to 0.0 when HIDDEN."""
        ctrl = OverlayController()
        ctrl._page = mock.MagicMock()
        ctrl._text_control = mock.MagicMock()
        ctrl._enqueue(OverlayState.HIDDEN, 0.0)
        ctrl._drain_and_apply()
        assert ctrl._page.window.opacity == 0.0

    def test_calls_page_update(self) -> None:
        """Test that _drain_and_apply calls page.update()."""
        ctrl = OverlayController()
        ctrl._page = mock.MagicMock()
        ctrl._text_control = mock.MagicMock()
        ctrl._enqueue(OverlayState.LOADING, 0.0)
        ctrl._drain_and_apply()
        ctrl._page.update.assert_called_once()

    def test_handles_page_update_exception(self) -> None:
        """Test that _drain_and_apply swallows exceptions from page.update()."""
        ctrl = OverlayController()
        ctrl._page = mock.MagicMock()
        ctrl._text_control = mock.MagicMock()
        ctrl._page.update.side_effect = RuntimeError("page gone")
        ctrl._enqueue(OverlayState.LOADING, 0.0)
        # Should not raise
        ctrl._drain_and_apply()


class TestOverlayControllerRunMain:
    """Test OverlayController.run_main()."""

    def test_calls_flet_app(self) -> None:
        """Test that run_main calls ft.app()."""
        ctrl = OverlayController()
        mock_ft = mock.MagicMock()
        mock_ft.AppView.FLET_APP = "FLET_APP"
        with mock.patch.dict("sys.modules", {"flet": mock_ft}):
            ctrl.run_main()
        mock_ft.app.assert_called_once()

    def test_passes_target_to_app(self) -> None:
        """Test that run_main passes a target function to ft.app()."""
        ctrl = OverlayController()
        mock_ft = mock.MagicMock()
        mock_ft.AppView.FLET_APP = "FLET_APP"
        with mock.patch.dict("sys.modules", {"flet": mock_ft}):
            ctrl.run_main()
        call_kwargs = mock_ft.app.call_args
        assert "target" in call_kwargs.kwargs or len(call_kwargs.args) > 0

    def test_raises_overlay_error_when_flet_not_installed(self) -> None:
        """Test that run_main raises OverlayError when Flet is not installed."""
        ctrl = OverlayController()
        with mock.patch.dict("sys.modules", {"flet": None}):
            with pytest.raises(OverlayError, match="Flet is not installed"):
                ctrl.run_main()

    def test_raises_overlay_error_on_flet_failure(self) -> None:
        """Test that run_main raises OverlayError when ft.app() fails."""
        ctrl = OverlayController()
        mock_ft = mock.MagicMock()
        mock_ft.AppView.FLET_APP = "FLET_APP"
        mock_ft.app.side_effect = RuntimeError("Display not available")
        with mock.patch.dict("sys.modules", {"flet": mock_ft}):
            with pytest.raises(OverlayError, match="Flet failed"):
                ctrl.run_main()

    def test_wires_window_close_event(self) -> None:
        """Test that run_main wires the window on_event handler."""
        ctrl = OverlayController()
        mock_ft = mock.MagicMock()
        mock_ft.AppView.FLET_APP = "FLET_APP"
        captured_main = None

        def capture_main(**kwargs):
            nonlocal captured_main
            captured_main = kwargs.get("target")

        mock_ft.app.side_effect = capture_main

        with mock.patch.dict("sys.modules", {"flet": mock_ft}):
            ctrl.run_main()

        # Call the captured async main function with a mock page
        assert captured_main is not None
        mock_page = mock.MagicMock()
        import asyncio

        asyncio.get_event_loop().run_until_complete(captured_main(mock_page))
        assert mock_page.window.on_event is not None

    def test_window_close_calls_on_close_callback(self) -> None:
        """Test that closing the Flet window invokes the on_close callback."""
        on_close = mock.MagicMock()
        ctrl = OverlayController(on_close=on_close)
        mock_ft = mock.MagicMock()
        mock_ft.AppView.FLET_APP = "FLET_APP"
        mock_ft.WindowEventType.CLOSE = "close"
        captured_main = None

        def capture_main(**kwargs):
            nonlocal captured_main
            captured_main = kwargs.get("target")

        mock_ft.app.side_effect = capture_main

        with mock.patch.dict("sys.modules", {"flet": mock_ft}):
            ctrl.run_main()

        assert captured_main is not None
        mock_page = mock.MagicMock()
        import asyncio

        asyncio.get_event_loop().run_until_complete(captured_main(mock_page))

        # Simulate window close event
        close_event = mock.MagicMock()
        close_event.type = "close"
        mock_page.window.on_event(close_event)

        on_close.assert_called_once()
        assert ctrl._running is False


class TestOverlayControllerOnClose:
    """Test OverlayController on_close callback."""

    def test_default_on_close_is_none(self) -> None:
        """Test that on_close defaults to None."""
        ctrl = OverlayController()
        assert ctrl._on_close is None

    def test_on_close_callback_stored(self) -> None:
        """Test that on_close callback is stored."""
        callback = mock.MagicMock()
        ctrl = OverlayController(on_close=callback)
        assert ctrl._on_close is callback
