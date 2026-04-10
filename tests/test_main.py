"""Tests for NoasrRuntime and main() in noasr.main."""

import sys
import threading
from unittest import mock

import pytest

from noasr.main import NoasrRuntime, main
from noasr.models import AppConfig, RuntimeState
from noasr.tools import ToolManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_tool_manager() -> None:
    """Reset the ToolManager singleton between tests."""
    ToolManager._instance = None
    ToolManager._initialized = False


def _make_runtime_with_mocks() -> tuple[NoasrRuntime, dict]:
    """Create a NoasrRuntime with all internal components mocked.

    Returns (runtime, mocks_dict) where mocks_dict contains every mock so
    tests can configure return-values / assert calls.
    """
    _reset_tool_manager()
    runtime = NoasrRuntime()

    # Mock all external dependencies that initialize() would create
    mock_agent_manager = mock.MagicMock()
    mock_tool_manager = mock.MagicMock()
    mock_tool_manager.list_tools.return_value = []
    mock_client = mock.MagicMock()
    mock_recorder = mock.MagicMock()
    mock_overlay = mock.MagicMock()
    mock_hotkey = mock.MagicMock()
    mock_injector = mock.MagicMock()
    mock_regex = mock.MagicMock()

    # Patch load_config to return a minimal valid config.
    # GetCurrentDateTime is imported locally inside initialize() from
    # noasr.tools.datetime, so we patch it at the source module.
    with mock.patch("noasr.main.load_config", return_value={}):
        with mock.patch("noasr.main.AppConfig.from_dict", return_value=AppConfig()):
            with mock.patch(
                "noasr.main.ToolManager.get_instance", return_value=mock_tool_manager
            ):
                with mock.patch("noasr.tools.datetime.GetCurrentDateTime"):
                    with mock.patch(
                        "noasr.main.AgentManager", return_value=mock_agent_manager
                    ):
                        with mock.patch(
                            "noasr.main.MiMoClient", return_value=mock_client
                        ):
                            with mock.patch(
                                "noasr.main.AudioRecorder", return_value=mock_recorder
                            ):
                                with mock.patch(
                                    "noasr.main.OverlayController",
                                    return_value=mock_overlay,
                                ):
                                    with mock.patch(
                                        "noasr.main.HotkeyListener",
                                        return_value=mock_hotkey,
                                    ):
                                        with mock.patch(
                                            "noasr.main.TextInjector",
                                            return_value=mock_injector,
                                        ):
                                            with mock.patch(
                                                "noasr.main.RegexProcessor",
                                                return_value=mock_regex,
                                            ):
                                                with mock.patch(
                                                    "noasr.main.load_regex_registry",
                                                    return_value={},
                                                ):
                                                    runtime.initialize()

    mocks = {
        "agent_manager": mock_agent_manager,
        "tool_manager": mock_tool_manager,
        "client": mock_client,
        "recorder": mock_recorder,
        "overlay": mock_overlay,
        "hotkey": mock_hotkey,
        "injector": mock_injector,
        "regex": mock_regex,
    }

    # Also set internal references directly so _on_key_down etc. use the mocks
    runtime._agent_manager = mock_agent_manager
    runtime._tool_manager = mock_tool_manager
    runtime._client = mock_client
    runtime._recorder = mock_recorder
    runtime._overlay = mock_overlay
    runtime._hotkey = mock_hotkey
    runtime._injector = mock_injector
    runtime._regex_processor = mock_regex

    return runtime, mocks


# ---------------------------------------------------------------------------
# Test: Initial state
# ---------------------------------------------------------------------------


class TestInitialState:
    """Test NoasrRuntime initial state."""

    def test_initial_state_is_idle(self) -> None:
        """Fresh runtime should be in IDLE state."""
        runtime = NoasrRuntime()
        assert runtime._state == RuntimeState.IDLE

    def test_state_property_returns_idle(self) -> None:
        """The state property should return RuntimeState.IDLE initially."""
        runtime = NoasrRuntime()
        assert runtime.state == RuntimeState.IDLE


# ---------------------------------------------------------------------------
# Test: initialize()
# ---------------------------------------------------------------------------


class TestInitialize:
    """Test NoasrRuntime.initialize()."""

    def setup_method(self) -> None:
        _reset_tool_manager()

    def test_initialize_creates_components_and_returns_true(self) -> None:
        """initialize() should create all components and return True."""
        runtime = NoasrRuntime()

        mock_tool_manager = mock.MagicMock()
        mock_tool_manager.list_tools.return_value = []

        with mock.patch(
            "noasr.main.load_config",
            return_value={"baseurl": "http://test", "api_key": "key123"},
        ):
            with mock.patch("noasr.main.AppConfig.from_dict") as mock_from_dict:
                mock_from_dict.return_value = AppConfig(
                    baseurl="http://test", api_key="key123"
                )

                with mock.patch(
                    "noasr.main.ToolManager.get_instance",
                    return_value=mock_tool_manager,
                ):
                    with mock.patch("noasr.tools.datetime.GetCurrentDateTime"):
                        with mock.patch("noasr.main.AgentManager") as MockAgentMgr:
                            with mock.patch("noasr.main.MiMoClient") as MockClient:
                                with mock.patch(
                                    "noasr.main.AudioRecorder"
                                ) as MockRecorder:
                                    with mock.patch(
                                        "noasr.main.OverlayController"
                                    ) as MockOverlay:
                                        with mock.patch(
                                            "noasr.main.HotkeyListener"
                                        ) as MockHotkey:
                                            with mock.patch(
                                                "noasr.main.TextInjector"
                                            ) as MockInjector:
                                                with mock.patch(
                                                    "noasr.main.RegexProcessor"
                                                ) as MockRegex:
                                                    result = runtime.initialize()

        assert result is True
        assert runtime._config is not None
        assert runtime._agent_manager is not None
        assert runtime._tool_manager is not None
        assert runtime._client is not None
        assert runtime._recorder is not None
        assert runtime._overlay is not None
        assert runtime._hotkey is not None
        assert runtime._injector is not None
        assert runtime._regex_processor is not None

    def test_initialize_registers_agents_from_config(self) -> None:
        """initialize() should register agents from config."""
        runtime = NoasrRuntime()

        mock_tool_manager = mock.MagicMock()
        mock_tool_manager.list_tools.return_value = []
        mock_agent_manager = mock.MagicMock()

        agents_data = [{"name": "dictate", "trigger": [62, 62], "toolsets": []}]

        with mock.patch("noasr.main.load_config", return_value={"agents": agents_data}):
            with mock.patch("noasr.main.AppConfig.from_dict") as mock_from_dict:
                mock_from_dict.return_value = AppConfig(agents=agents_data)

                with mock.patch(
                    "noasr.main.ToolManager.get_instance",
                    return_value=mock_tool_manager,
                ):
                    with mock.patch("noasr.tools.datetime.GetCurrentDateTime"):
                        with mock.patch(
                            "noasr.main.AgentManager",
                            return_value=mock_agent_manager,
                        ):
                            with mock.patch(
                                "noasr.main.AgentConfig.from_dict"
                            ) as mock_agent_from_dict:
                                mock_agent_from_dict.return_value = mock.MagicMock()

                                with mock.patch("noasr.main.MiMoClient"):
                                    with mock.patch("noasr.main.AudioRecorder"):
                                        with mock.patch("noasr.main.OverlayController"):
                                            with mock.patch(
                                                "noasr.main.HotkeyListener"
                                            ):
                                                with mock.patch(
                                                    "noasr.main.TextInjector"
                                                ):
                                                    with mock.patch(
                                                        "noasr.main.RegexProcessor"
                                                    ):
                                                        runtime.initialize()

        # AgentManager.register should have been called once per agent
        assert mock_agent_manager.register.call_count == 1

    def test_initialize_registers_toolsets_from_config(self) -> None:
        """initialize() should register toolsets from config."""
        runtime = NoasrRuntime()

        mock_tool_manager = mock.MagicMock()
        mock_tool_manager.list_tools.return_value = []

        toolsets = {"default": ["GetCurrentDateTime"]}

        with mock.patch("noasr.main.load_config", return_value={"toolsets": toolsets}):
            with mock.patch("noasr.main.AppConfig.from_dict") as mock_from_dict:
                mock_from_dict.return_value = AppConfig(toolsets=toolsets)

                with mock.patch(
                    "noasr.main.ToolManager.get_instance",
                    return_value=mock_tool_manager,
                ):
                    with mock.patch("noasr.tools.datetime.GetCurrentDateTime"):
                        with mock.patch("noasr.main.AgentManager"):
                            with mock.patch("noasr.main.MiMoClient"):
                                with mock.patch("noasr.main.AudioRecorder"):
                                    with mock.patch("noasr.main.OverlayController"):
                                        with mock.patch("noasr.main.HotkeyListener"):
                                            with mock.patch("noasr.main.TextInjector"):
                                                with mock.patch(
                                                    "noasr.main.RegexProcessor"
                                                ):
                                                    runtime.initialize()

        mock_tool_manager.register_toolset.assert_called_once_with(
            "default", ["GetCurrentDateTime"]
        )


# ---------------------------------------------------------------------------
# Test: _on_key_down()
# ---------------------------------------------------------------------------


class TestOnKeyDown:
    """Test NoasrRuntime._on_key_down()."""

    def setup_method(self) -> None:
        _reset_tool_manager()

    def test_key_down_idle_matching_trigger_transitions_to_listening(self) -> None:
        """When IDLE and key matches an agent trigger, transition to LISTENING."""
        runtime, mocks = _make_runtime_with_mocks()

        mock_agent = mock.MagicMock()
        mock_agent.name = "dictate"
        mocks["agent_manager"].get_agent_for_trigger.return_value = mock_agent

        runtime._on_key_down(62)

        assert runtime.state == RuntimeState.LISTENING
        assert runtime._active_agent is mock_agent
        mocks["recorder"].start.assert_called_once()
        mocks["overlay"].show_listening.assert_called_once_with(0.0)

    def test_key_down_not_idle_does_nothing(self) -> None:
        """When not IDLE, _on_key_down should do nothing."""
        runtime, mocks = _make_runtime_with_mocks()

        runtime._state = RuntimeState.LISTENING
        runtime._on_key_down(62)

        # State should remain LISTENING, no new recording
        assert runtime.state == RuntimeState.LISTENING
        mocks["recorder"].start.assert_not_called()

    def test_key_down_no_matching_agent_does_nothing(self) -> None:
        """When no agent matches the trigger key, do nothing."""
        runtime, mocks = _make_runtime_with_mocks()

        mocks["agent_manager"].get_agent_for_trigger.return_value = None

        runtime._on_key_down(99)

        assert runtime.state == RuntimeState.IDLE
        mocks["recorder"].start.assert_not_called()
        mocks["overlay"].show_listening.assert_not_called()

    def test_key_down_recorder_start_fails_stays_idle(self) -> None:
        """When recorder.start() raises, runtime should stay IDLE."""
        runtime, mocks = _make_runtime_with_mocks()

        mock_agent = mock.MagicMock()
        mock_agent.name = "dictate"
        mocks["agent_manager"].get_agent_for_trigger.return_value = mock_agent
        mocks["recorder"].start.side_effect = RuntimeError("Device busy")

        runtime._on_key_down(62)

        assert runtime.state == RuntimeState.IDLE
        assert runtime._active_agent is None
        mocks["overlay"].show_listening.assert_not_called()


# ---------------------------------------------------------------------------
# Test: _on_key_up()
# ---------------------------------------------------------------------------


class TestOnKeyUp:
    """Test NoasrRuntime._on_key_up()."""

    def setup_method(self) -> None:
        _reset_tool_manager()

    def test_key_up_listening_transitions_to_loading(self) -> None:
        """When LISTENING, _on_key_up should transition to LOADING and stop recording."""
        runtime, mocks = _make_runtime_with_mocks()

        # Set up state as LISTENING
        runtime._state = RuntimeState.LISTENING
        runtime._active_agent = mock.MagicMock()
        runtime._active_agent.name = "dictate"

        # Mock recorder to return valid WAV bytes
        mocks[
            "recorder"
        ].stop_and_normalize.return_value = b"RIFF\x00\x00\x00\x00WAVEfmt "

        # Mock _process_recording to avoid actual LLM call
        with mock.patch.object(runtime, "_process_recording"):
            runtime._on_key_up(62)

        assert runtime.state == RuntimeState.LOADING
        mocks["overlay"].show_loading.assert_called_once()
        mocks["recorder"].stop_and_normalize.assert_called_once()

    def test_key_up_not_listening_does_nothing(self) -> None:
        """When not LISTENING, _on_key_up should do nothing."""
        runtime, mocks = _make_runtime_with_mocks()

        runtime._state = RuntimeState.IDLE
        runtime._on_key_up(62)

        mocks["recorder"].stop_and_normalize.assert_not_called()

    def test_key_up_recording_too_short_resets_to_idle(self) -> None:
        """When recorder raises RecordingTooShortError, runtime should reset to IDLE."""
        from noasr.audio import RecordingTooShortError

        runtime, mocks = _make_runtime_with_mocks()

        runtime._state = RuntimeState.LISTENING
        runtime._active_agent = mock.MagicMock()

        mocks["recorder"].stop_and_normalize.side_effect = RecordingTooShortError(
            "Recording too short: 0.1s < 0.3s"
        )

        runtime._on_key_up(62)

        assert runtime.state == RuntimeState.IDLE
        mocks["overlay"].hide.assert_called()

    def test_key_up_recorder_exception_resets_to_idle(self) -> None:
        """When recorder.stop_and_normalize() raises, runtime should reset to IDLE."""
        runtime, mocks = _make_runtime_with_mocks()

        runtime._state = RuntimeState.LISTENING
        runtime._active_agent = mock.MagicMock()

        mocks["recorder"].stop_and_normalize.side_effect = RuntimeError("Device error")

        runtime._on_key_up(62)

        assert runtime.state == RuntimeState.IDLE
        mocks["overlay"].hide.assert_called()

    def test_key_up_process_recording_exception_shows_error(self) -> None:
        """When _process_recording raises, overlay should show error then reset."""
        runtime, mocks = _make_runtime_with_mocks()

        runtime._state = RuntimeState.LISTENING
        runtime._active_agent = mock.MagicMock()
        runtime._active_agent.name = "dictate"

        mocks[
            "recorder"
        ].stop_and_normalize.return_value = b"RIFF\x00\x00\x00\x00WAVEfmt "

        with mock.patch.object(
            runtime, "_process_recording", side_effect=Exception("LLM error")
        ):
            with mock.patch("noasr.main.time.sleep"):
                runtime._on_key_up(62)

        mocks["overlay"].show_error.assert_called_once()
        assert runtime.state == RuntimeState.IDLE


# ---------------------------------------------------------------------------
# Test: _process_recording()
# ---------------------------------------------------------------------------


class TestProcessRecording:
    """Test NoasrRuntime._process_recording()."""

    def setup_method(self) -> None:
        _reset_tool_manager()

    def test_process_recording_sends_audio_and_injects_text(self) -> None:
        """_process_recording should call run_agent, apply regex, inject text."""
        runtime, mocks = _make_runtime_with_mocks()

        runtime._active_agent = mock.MagicMock()
        runtime._active_agent.name = "dictate"

        mocks["agent_manager"].run_agent.return_value = "Hello world"
        mocks["regex"].apply.return_value = "Hello world"

        runtime._process_recording("data:audio/wav;base64,AAAA")

        mocks["agent_manager"].run_agent.assert_called_once_with(
            "dictate",
            "data:audio/wav;base64,AAAA",
            mocks["client"],
            thinking_type="disabled",
        )
        mocks["regex"].apply.assert_called_once_with("Hello world")
        mocks["injector"].inject.assert_called_once_with("Hello world")
        assert runtime.state == RuntimeState.IDLE

    def test_process_recording_empty_result_does_not_inject(self) -> None:
        """_process_recording with empty result should not inject."""
        runtime, mocks = _make_runtime_with_mocks()

        runtime._active_agent = mock.MagicMock()
        runtime._active_agent.name = "dictate"

        mocks["agent_manager"].run_agent.return_value = ""
        mocks["regex"].apply.return_value = ""

        runtime._process_recording("data:audio/wav;base64,AAAA")

        mocks["injector"].inject.assert_not_called()

    def test_process_recording_whitespace_only_does_not_inject(self) -> None:
        """_process_recording with whitespace-only result should not inject."""
        runtime, mocks = _make_runtime_with_mocks()

        runtime._active_agent = mock.MagicMock()
        runtime._active_agent.name = "dictate"

        mocks["agent_manager"].run_agent.return_value = "   "
        mocks["regex"].apply.return_value = "   "

        runtime._process_recording("data:audio/wav;base64,AAAA")

        mocks["injector"].inject.assert_not_called()

    def test_process_recording_applies_regex(self) -> None:
        """_process_recording should apply regex transformations to the result."""
        runtime, mocks = _make_runtime_with_mocks()

        runtime._active_agent = mock.MagicMock()
        runtime._active_agent.name = "dictate"

        mocks["agent_manager"].run_agent.return_value = "Hello world"
        mocks["regex"].apply.return_value = "Hello transformed"

        runtime._process_recording("data:audio/wav;base64,AAAA")

        # Injector should receive the regex-processed text
        mocks["injector"].inject.assert_called_once_with("Hello transformed")

    def test_process_recording_no_regex_processor(self) -> None:
        """_process_recording with no regex processor should still inject text."""
        runtime, mocks = _make_runtime_with_mocks()

        runtime._active_agent = mock.MagicMock()
        runtime._active_agent.name = "dictate"
        runtime._regex_processor = None

        mocks["agent_manager"].run_agent.return_value = "Hello world"

        runtime._process_recording("data:audio/wav;base64,AAAA")

        mocks["injector"].inject.assert_called_once_with("Hello world")

    def test_process_recording_transitions_to_applying_result(self) -> None:
        """_process_recording should set state to APPLYING_RESULT before injection."""
        runtime, mocks = _make_runtime_with_mocks()

        runtime._active_agent = mock.MagicMock()
        runtime._active_agent.name = "dictate"

        mocks["agent_manager"].run_agent.return_value = "Hello"

        states_seen = []

        def capture_state(text: str) -> bool:
            states_seen.append(runtime.state)
            return True

        mocks["injector"].inject.side_effect = capture_state

        runtime._process_recording("data:audio/wav;base64,AAAA")

        assert RuntimeState.APPLYING_RESULT in states_seen


# ---------------------------------------------------------------------------
# Test: _reset_to_idle()
# ---------------------------------------------------------------------------


class TestResetToIdle:
    """Test NoasrRuntime._reset_to_idle()."""

    def setup_method(self) -> None:
        _reset_tool_manager()

    def test_reset_to_idle_resets_state_and_hides_overlay(self) -> None:
        """_reset_to_idle should set state to IDLE and hide overlay."""
        runtime, mocks = _make_runtime_with_mocks()

        runtime._state = RuntimeState.LOADING
        runtime._active_agent = mock.MagicMock()

        runtime._reset_to_idle()

        assert runtime.state == RuntimeState.IDLE
        assert runtime._active_agent is None
        mocks["overlay"].hide.assert_called_once()


# ---------------------------------------------------------------------------
# Test: _request_shutdown()
# ---------------------------------------------------------------------------


class TestRequestShutdown:
    """Test NoasrRuntime._request_shutdown()."""

    def setup_method(self) -> None:
        _reset_tool_manager()

    def test_sets_shutdown_event(self) -> None:
        """_request_shutdown should set the shutdown event."""
        runtime, mocks = _make_runtime_with_mocks()
        assert not runtime._shutdown_event.is_set()
        runtime._request_shutdown()
        assert runtime._shutdown_event.is_set()

    def test_idempotent(self) -> None:
        """_request_shutdown should be safe to call multiple times."""
        runtime, mocks = _make_runtime_with_mocks()
        runtime._request_shutdown()
        runtime._request_shutdown()
        assert runtime._shutdown_event.is_set()


# ---------------------------------------------------------------------------
# Test: run()
# ---------------------------------------------------------------------------


class TestRun:
    """Test NoasrRuntime.run()."""

    def setup_method(self) -> None:
        _reset_tool_manager()

    def test_run_first_run_bootstrap_returns_0(self) -> None:
        """run() should return 0 when first-run bootstrap is detected."""
        runtime = NoasrRuntime()

        with mock.patch("noasr.main.check_and_bootstrap", return_value=True):
            result = runtime.run()

        assert result == 0

    def test_run_lock_fails_returns_1(self) -> None:
        """run() should return 1 when single-instance lock cannot be acquired."""
        runtime = NoasrRuntime()

        with mock.patch("noasr.main.check_and_bootstrap", return_value=False):
            with mock.patch("noasr.main.acquire_runtime_lock", return_value=False):
                with mock.patch("noasr.main.release_runtime_lock"):
                    result = runtime.run()

        assert result == 1

    def test_run_normal_exit_returns_0(self) -> None:
        """run() should return 0 on normal exit (KeyboardInterrupt)."""
        runtime = NoasrRuntime()
        mock_overlay = mock.MagicMock()
        mock_hotkey = mock.MagicMock()
        mock_hotkey.start.return_value = True

        with mock.patch("noasr.main.check_and_bootstrap", return_value=False):
            with mock.patch("noasr.main.acquire_runtime_lock", return_value=True):
                with mock.patch("noasr.main.release_runtime_lock"):
                    with mock.patch.object(runtime, "initialize", return_value=True):
                        runtime._overlay = mock_overlay
                        runtime._hotkey = mock_hotkey

                        # Simulate KeyboardInterrupt on first sleep
                        with mock.patch(
                            "noasr.main.time.sleep", side_effect=KeyboardInterrupt
                        ):
                            result = runtime.run()

        assert result == 0
        mock_hotkey.stop.assert_called_once()
        mock_overlay.stop.assert_called_once()

    def test_run_hotkey_start_fails_returns_1(self) -> None:
        """run() should return 1 when hotkey listener fails to start."""
        runtime = NoasrRuntime()
        mock_overlay = mock.MagicMock()
        mock_hotkey = mock.MagicMock()
        mock_hotkey.start.return_value = False

        with mock.patch("noasr.main.check_and_bootstrap", return_value=False):
            with mock.patch("noasr.main.acquire_runtime_lock", return_value=True):
                with mock.patch("noasr.main.release_runtime_lock"):
                    with mock.patch.object(runtime, "initialize", return_value=True):
                        runtime._overlay = mock_overlay
                        runtime._hotkey = mock_hotkey

                        result = runtime.run()

        assert result == 1

    def test_run_initialize_fails_returns_1(self) -> None:
        """run() should return 1 when initialize() returns False."""
        runtime = NoasrRuntime()
        mock_overlay = mock.MagicMock()
        mock_hotkey = mock.MagicMock()

        with mock.patch("noasr.main.check_and_bootstrap", return_value=False):
            with mock.patch("noasr.main.acquire_runtime_lock", return_value=True):
                with mock.patch("noasr.main.release_runtime_lock"):
                    with mock.patch.object(runtime, "initialize", return_value=False):
                        runtime._overlay = mock_overlay
                        runtime._hotkey = mock_hotkey

                        result = runtime.run()

        assert result == 1

    def test_run_releases_lock_on_exit(self) -> None:
        """run() should always release the runtime lock on exit."""
        runtime = NoasrRuntime()
        mock_overlay = mock.MagicMock()
        mock_hotkey = mock.MagicMock()
        mock_hotkey.start.return_value = True

        with mock.patch("noasr.main.check_and_bootstrap", return_value=False):
            with mock.patch(
                "noasr.main.acquire_runtime_lock", return_value=True
            ) as mock_acquire:
                with mock.patch("noasr.main.release_runtime_lock") as mock_release:
                    with mock.patch.object(runtime, "initialize", return_value=True):
                        runtime._overlay = mock_overlay
                        runtime._hotkey = mock_hotkey

                        with mock.patch(
                            "noasr.main.time.sleep", side_effect=KeyboardInterrupt
                        ):
                            runtime.run()

        mock_release.assert_called_once()

    def test_run_overlay_error_triggers_shutdown_and_cleanup(self) -> None:
        """run() should trigger shutdown and cleanup when overlay raises OverlayError."""
        from noasr.overlay import OverlayError

        runtime = NoasrRuntime()
        mock_overlay = mock.MagicMock()
        mock_overlay.start = mock.MagicMock()
        mock_overlay.run_main.side_effect = OverlayError("Flet failed")
        mock_hotkey = mock.MagicMock()
        mock_hotkey.start.return_value = True

        with mock.patch("noasr.main.check_and_bootstrap", return_value=False):
            with mock.patch("noasr.main.acquire_runtime_lock", return_value=True):
                with mock.patch("noasr.main.release_runtime_lock"):
                    with mock.patch.object(runtime, "initialize", return_value=True):
                        runtime._overlay = mock_overlay
                        runtime._hotkey = mock_hotkey

                        result = runtime.run()

        assert result == 0
        assert runtime._shutdown_event.is_set()
        mock_hotkey.stop.assert_called_once()
        mock_overlay.stop.assert_called_once()

    def test_run_on_close_triggers_shutdown_event(self) -> None:
        """run() should set shutdown_event when on_close callback is invoked."""
        runtime = NoasrRuntime()
        mock_overlay = mock.MagicMock()
        mock_hotkey = mock.MagicMock()
        mock_hotkey.start.return_value = True

        with mock.patch("noasr.main.check_and_bootstrap", return_value=False):
            with mock.patch("noasr.main.acquire_runtime_lock", return_value=True):
                with mock.patch("noasr.main.release_runtime_lock"):
                    with mock.patch.object(runtime, "initialize", return_value=True):
                        runtime._overlay = mock_overlay
                        runtime._hotkey = mock_hotkey

                        # Simulate: overlay.run_main() returns normally (window closed)
                        # This triggers _request_shutdown()
                        result = runtime.run()

        assert result == 0
        assert runtime._shutdown_event.is_set()


# ---------------------------------------------------------------------------
# Test: main()
# ---------------------------------------------------------------------------


class TestMain:
    """Test the main() entry point."""

    def test_main_returns_int_exit_code(self) -> None:
        """main() should return an integer exit code."""
        with mock.patch("sys.argv", ["noasr"]):
            with mock.patch("noasr.main.NoasrRuntime") as MockRuntime:
                mock_instance = mock.MagicMock()
                mock_instance.run.return_value = 0
                MockRuntime.return_value = mock_instance

                result = main()

        assert isinstance(result, int)
        assert result == 0

    def test_main_creates_runtime_and_calls_run(self) -> None:
        """main() should create a NoasrRuntime and call its run() method."""
        with mock.patch("sys.argv", ["noasr"]):
            with mock.patch("noasr.main.NoasrRuntime") as MockRuntime:
                mock_instance = mock.MagicMock()
                mock_instance.run.return_value = 42
                MockRuntime.return_value = mock_instance

                result = main()

        MockRuntime.assert_called_once()
        mock_instance.run.assert_called_once()
        assert result == 42


# ---------------------------------------------------------------------------
# Test: argparse --version
# ---------------------------------------------------------------------------


class TestArgparseVersion:
    """Test --version flag handling."""

    def test_version_flag_exits_with_version_string(self) -> None:
        """--version should print version and exit with code 0."""
        with pytest.raises(SystemExit) as exc_info:
            with mock.patch("sys.argv", ["noasr", "--version"]):
                main()

        assert exc_info.value.code == 0
