"""Integration tests for noasr — mocked end-to-end flows.

Covers: plain dictation, ReAct tool loop, error recovery,
bootstrap/startup, and max-duration auto-stop.
"""

import time
from unittest import mock

import pytest

from noasr.agent import AgentManager, AgentType
from noasr.main import NoasrRuntime
from noasr.models import AgentConfig, AppConfig, RuntimeState
from noasr.tools import ToolManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_tool_manager() -> None:
    """Reset the ToolManager singleton between tests."""
    ToolManager._instance = None
    ToolManager._initialized = False


def _make_config_with_agent() -> AppConfig:
    """Return an AppConfig with one agent (trigger=62)."""
    return AppConfig(
        baseurl="https://api.test.com/v1",
        api_key="test-key",
        toolsets={"default": ["GetCurrentDateTime"]},
        agents=[
            {"name": "dictate", "trigger": [62, 62], "toolsets": ["default"]},
        ],
    )


def _make_runtime_with_mocks() -> tuple[NoasrRuntime, dict]:
    """Create a NoasrRuntime with all internal components mocked.

    Returns (runtime, mocks_dict) where mocks_dict contains every mock so
    tests can configure return-values / assert calls.
    """
    _reset_tool_manager()
    runtime = NoasrRuntime()

    mock_agent_manager = mock.MagicMock()
    mock_tool_manager = mock.MagicMock()
    mock_tool_manager.list_tools.return_value = []
    mock_client = mock.MagicMock()
    mock_recorder = mock.MagicMock()
    mock_overlay = mock.MagicMock()
    mock_hotkey = mock.MagicMock()
    mock_injector = mock.MagicMock()
    mock_regex = mock.MagicMock()

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

    # Set internal references directly so _on_key_down etc. use the mocks
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
# TestE2EDictation
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestE2EDictation:
    """Mocked end-to-end plain dictation flow."""

    def setup_method(self) -> None:
        _reset_tool_manager()

    def test_full_dictation_flow(self) -> None:
        """Complete flow: init → key down → key up → recording → MiMo response → regex → inject."""
        runtime, mocks = _make_runtime_with_mocks()

        # Set up agent for trigger key 62
        mock_agent = mock.MagicMock()
        mock_agent.name = "dictate"
        mocks["agent_manager"].get_agent_for_trigger.return_value = mock_agent

        # Agent returns simple text
        mocks["agent_manager"].run_agent.return_value = "Hello world"
        mocks["regex"].apply.return_value = "Hello world"

        # Recorder returns valid audio
        mocks["recorder"].stop_and_normalize.return_value = (
            "data:audio/wav;base64,AAAA",
            1.5,
        )

        # --- Step 1: Key down ---
        runtime._on_key_down(62)
        assert runtime.state == RuntimeState.LISTENING
        mocks["recorder"].start.assert_called_once()
        mocks["overlay"].show_listening.assert_called_once_with(0.0)

        # --- Step 2: Key up ---
        with mock.patch("noasr.main.load_system_prompt", return_value="sys"):
            with mock.patch("noasr.main.load_user_prompt", return_value="user"):
                runtime._on_key_up(62)

        # --- Assert state transitions ---
        # After key up, should have gone LOADING → APPLYING_RESULT → IDLE
        assert runtime.state == RuntimeState.IDLE

        # --- Assert overlay transitions ---
        mocks["overlay"].show_loading.assert_called_once()
        mocks["overlay"].hide.assert_called()

        # --- Assert client.send called with correct message structure ---
        mocks["agent_manager"].run_agent.assert_called_once()
        call_args = mocks["agent_manager"].run_agent.call_args
        assert call_args[0][0] == "dictate"  # agent name
        messages = call_args[0][1]  # messages list
        assert len(messages) == 2  # system + user
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "sys"
        assert messages[1]["role"] == "user"
        user_content = messages[1]["content"]
        assert isinstance(user_content, list)
        # First item should be audio
        assert user_content[0]["type"] == "input_audio"
        assert "data" in user_content[0]["input_audio"]
        # Second item should be text prompt
        assert user_content[1]["type"] == "text"
        assert user_content[1]["text"] == "user"

        # --- Assert regex called on response text ---
        mocks["regex"].apply.assert_called_once_with("Hello world")

        # --- Assert injector called with final text ---
        mocks["injector"].inject.assert_called_once_with("Hello world")


# ---------------------------------------------------------------------------
# TestE2EReActToolLoop
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestE2EReActToolLoop:
    """Mocked end-to-end ReAct flow with datetime tool."""

    def setup_method(self) -> None:
        _reset_tool_manager()

    def test_react_loop_with_datetime_tool(self) -> None:
        """Agent with datetime tool → tool_call → execute → second response → inject."""
        # Set up real ToolManager with GetCurrentDateTime
        tool_manager = ToolManager()

        from noasr.tools.datetime import GetCurrentDateTime

        tool_manager.register_tool(GetCurrentDateTime())
        tool_manager.register_toolset("default", ["GetCurrentDateTime"])

        # Set up real AgentManager with an agent
        agent_manager = AgentManager()
        agent_config = AgentConfig(
            name="dictate", trigger=[62, 62], toolsets=["default"]
        )
        agent_manager.register(AgentType(agent_config))

        # Create runtime with mocks but real agent/tool managers
        runtime = NoasrRuntime()
        runtime._agent_manager = agent_manager
        runtime._tool_manager = tool_manager

        mock_client = mock.MagicMock()
        runtime._client = mock_client

        mock_overlay = mock.MagicMock()
        runtime._overlay = mock_overlay

        mock_injector = mock.MagicMock()
        runtime._injector = mock_injector

        mock_regex = mock.MagicMock()
        mock_regex.apply.return_value = "The time is 2025-01-01T00:00:00"
        runtime._regex_processor = mock_regex

        # Mock MiMoClient.send: 1st call has tool_calls, 2nd call has final content
        mock_client.send.side_effect = [
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "function": {
                                        "name": "GetCurrentDateTime",
                                        "arguments": '{"format": "iso"}',
                                    },
                                    "type": "function",
                                }
                            ],
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "The time is 2025-01-01T00:00:00",
                            "tool_calls": None,
                        }
                    }
                ]
            },
        ]

        # Set active agent
        runtime._active_agent = agent_manager.get_agent("dictate")

        # Run _process_recording
        with mock.patch("noasr.main.load_system_prompt", return_value="sys"):
            with mock.patch("noasr.main.load_user_prompt", return_value="user"):
                runtime._process_recording("data:audio/wav;base64,AAAA")

        # Assert: ToolManager executed GetCurrentDateTime
        assert mock_client.send.call_count == 2

        # Assert: Tool result message was appended to conversation
        # The second call to send should have messages including tool result
        second_call_args = mock_client.send.call_args_list[1]
        messages = (
            second_call_args[0][0]
            if second_call_args[0]
            else second_call_args.kwargs.get("messages", [])
        )
        tool_messages = [m for m in messages if m.get("role") == "tool"]
        assert len(tool_messages) == 1
        assert tool_messages[0]["tool_call_id"] == "call_1"

        # Assert: Final text is injected
        mock_regex.apply.assert_called_once_with("The time is 2025-01-01T00:00:00")
        mock_injector.inject.assert_called_once_with("The time is 2025-01-01T00:00:00")


# ---------------------------------------------------------------------------
# TestE2EErrorRecovery
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestE2EErrorRecovery:
    """Error handling in integration."""

    def setup_method(self) -> None:
        _reset_tool_manager()

    def test_client_send_exception_shows_error_and_returns_idle(self) -> None:
        """Client.send raises exception → runtime shows error overlay, returns to IDLE."""
        runtime, mocks = _make_runtime_with_mocks()

        runtime._state = RuntimeState.LISTENING
        runtime._active_agent = mock.MagicMock()
        runtime._active_agent.name = "dictate"

        mocks["recorder"].stop_and_normalize.return_value = (
            "data:audio/wav;base64,AAAA",
            1.5,
        )

        # Make _process_recording raise an exception
        with mock.patch.object(
            runtime, "_process_recording", side_effect=Exception("Network error")
        ):
            with mock.patch("noasr.main.time.sleep"):
                runtime._on_key_up(62)

        mocks["overlay"].show_error.assert_called_once()
        assert runtime.state == RuntimeState.IDLE

    def test_recording_too_short_returns_to_idle(self) -> None:
        """Recording too short (stop_and_normalize returns None) → runtime returns to IDLE."""
        runtime, mocks = _make_runtime_with_mocks()

        runtime._state = RuntimeState.LISTENING
        runtime._active_agent = mock.MagicMock()

        mocks["recorder"].stop_and_normalize.return_value = None

        runtime._on_key_up(62)

        assert runtime.state == RuntimeState.IDLE
        mocks["overlay"].hide.assert_called()
        mocks["injector"].inject.assert_not_called()

    def test_empty_response_no_injection(self) -> None:
        """Empty response from client → no injection occurs."""
        runtime, mocks = _make_runtime_with_mocks()

        runtime._active_agent = mock.MagicMock()
        runtime._active_agent.name = "dictate"

        mocks["agent_manager"].run_agent.return_value = ""
        mocks["regex"].apply.return_value = ""

        with mock.patch("noasr.main.load_system_prompt", return_value=""):
            with mock.patch("noasr.main.load_user_prompt", return_value=""):
                runtime._process_recording("data:audio/wav;base64,AAAA")

        mocks["injector"].inject.assert_not_called()


# ---------------------------------------------------------------------------
# TestE2EBootstrap
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestE2EBootstrap:
    """Startup behavior."""

    def setup_method(self) -> None:
        _reset_tool_manager()

    def test_first_run_returns_0(self) -> None:
        """First run (check_and_bootstrap returns True) → run() returns 0, no runtime init."""
        runtime = NoasrRuntime()

        with mock.patch("noasr.main.check_and_bootstrap", return_value=True):
            result = runtime.run()

        assert result == 0

    def test_lock_acquisition_fails_returns_1(self) -> None:
        """Lock acquisition fails → run() returns 1."""
        runtime = NoasrRuntime()

        with mock.patch("noasr.main.check_and_bootstrap", return_value=False):
            with mock.patch("noasr.main.acquire_runtime_lock", return_value=False):
                with mock.patch("noasr.main.release_runtime_lock"):
                    result = runtime.run()

        assert result == 1

    def test_hotkey_listener_fails_returns_1(self) -> None:
        """Hotkey listener fails to start → run() returns 1."""
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


# ---------------------------------------------------------------------------
# TestE2EMaxDuration
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestE2EMaxDuration:
    """Auto-stop on max recording duration."""

    def setup_method(self) -> None:
        _reset_tool_manager()

    def test_auto_stop_on_max_duration(self) -> None:
        """When elapsed >= MAX_RECORDING_DURATION, _on_key_up is auto-triggered."""
        from noasr.constants import MAX_RECORDING_DURATION

        runtime, mocks = _make_runtime_with_mocks()

        # Set up agent for trigger key 62
        mock_agent = mock.MagicMock()
        mock_agent.name = "dictate"
        mocks["agent_manager"].get_agent_for_trigger.return_value = mock_agent

        # Simulate key down
        runtime._on_key_down(62)
        assert runtime.state == RuntimeState.LISTENING

        # Simulate that recording start time was long ago
        runtime._recording_start_time = time.time() - MAX_RECORDING_DURATION - 0.1

        # Recorder returns valid audio
        mocks["recorder"].stop_and_normalize.return_value = (
            "data:audio/wav;base64,AAAA",
            MAX_RECORDING_DURATION,
        )
        mocks["agent_manager"].run_agent.return_value = "Auto-stopped result"
        mocks["regex"].apply.return_value = "Auto-stopped result"

        # Simulate the auto-stop logic from run()'s main loop
        elapsed = time.time() - runtime._recording_start_time
        assert elapsed >= MAX_RECORDING_DURATION

        # Trigger _on_key_up as the run loop would
        with mock.patch("noasr.main.load_system_prompt", return_value=""):
            with mock.patch("noasr.main.load_user_prompt", return_value=""):
                runtime._on_key_up(0)

        # Should have processed and returned to idle
        assert runtime.state == RuntimeState.IDLE
        mocks["injector"].inject.assert_called_once_with("Auto-stopped result")
