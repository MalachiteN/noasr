"""Main entry point and runtime orchestration for noasr."""

import argparse
import json
import sys
import time
from typing import Optional

from noasr.agent import AgentManager, AgentType
from noasr.audio import AudioRecorder
from noasr.client import MiMoClient
from noasr.config import (
    check_and_bootstrap,
    get_config_value,
    load_config,
    load_regex_registry,
    load_system_prompt,
    load_user_prompt,
)
from noasr.constants import MAX_RECORDING_DURATION, MIN_RECORDING_DURATION
from noasr.hotkey import HotkeyListener
from noasr.injector import TextInjector
from noasr.lock import SingleInstanceError, acquire_runtime_lock, release_runtime_lock
from noasr.models import AgentConfig, AppConfig, RuntimeState
from noasr.overlay import OverlayController
from noasr.regex import RegexProcessor
from noasr.tools import ToolManager


class NoasrRuntime:
    """Main runtime coordinator for noasr.

    Wires together: config, single-instance lock, hotkey listener,
    overlay state transitions, audio recording, MiMo request dispatch,
    tool-loop execution, regex postprocessing, and text injection.
    """

    def __init__(self) -> None:
        self._state = RuntimeState.IDLE
        self._config: Optional[AppConfig] = None
        self._agent_manager: Optional[AgentManager] = None
        self._tool_manager: Optional[ToolManager] = None
        self._client: Optional[MiMoClient] = None
        self._recorder: Optional[AudioRecorder] = None
        self._overlay: Optional[OverlayController] = None
        self._hotkey: Optional[HotkeyListener] = None
        self._injector: Optional[TextInjector] = None
        self._regex_processor: Optional[RegexProcessor] = None
        self._recording_start_time: float = 0.0
        self._active_agent: Optional[AgentType] = None

    @property
    def state(self) -> RuntimeState:
        """Current runtime state."""
        return self._state

    def initialize(self) -> bool:
        """Initialize all runtime components.

        Returns:
            True if initialization succeeded, False otherwise.
        """
        # Load config
        raw_config = load_config()
        self._config = AppConfig.from_dict(raw_config)

        # Initialize tool manager and register built-in tools
        from noasr.tools.datetime import GetCurrentDateTime

        self._tool_manager = ToolManager.get_instance()
        if "GetCurrentDateTime" not in self._tool_manager.list_tools():
            self._tool_manager.register_tool(GetCurrentDateTime())

        # Register toolsets from config
        toolsets = self._config.toolsets
        for name, tools in toolsets.items():
            self._tool_manager.register_toolset(name, tools)

        # Initialize agent manager and register agents from config
        self._agent_manager = AgentManager()
        for agent_data in self._config.agents:
            agent_config = AgentConfig.from_dict(agent_data)
            self._agent_manager.register(AgentType(agent_config))

        # Initialize MiMo client
        self._client = MiMoClient(
            baseurl=self._config.baseurl,
            api_key=self._config.api_key,
        )

        # Initialize audio recorder
        self._recorder = AudioRecorder()

        # Initialize overlay
        self._overlay = OverlayController()

        # Initialize hotkey listener
        self._hotkey = HotkeyListener(
            on_key_down=self._on_key_down,
            on_key_up=self._on_key_up,
        )

        # Initialize text injector
        self._injector = TextInjector()

        # Initialize regex processor
        self._regex_processor = RegexProcessor()

        return True

    def _on_key_down(self, key_code: int) -> None:
        """Handle key press event."""
        if self._state != RuntimeState.IDLE:
            return

        # Find agent for this trigger key
        agent = self._agent_manager.get_agent_for_trigger(key_code)
        if agent is None:
            return

        self._active_agent = agent
        self._state = RuntimeState.LISTENING
        self._recording_start_time = time.time()

        # Start recording
        try:
            self._recorder.start()
        except Exception as e:
            print(f"Failed to start recording: {e}", file=sys.stderr)
            self._state = RuntimeState.IDLE
            self._active_agent = None
            return

        # Show overlay
        self._overlay.show_listening(0.0)

    def _on_key_up(self, key_code: int) -> None:
        """Handle key release event."""
        if self._state != RuntimeState.LISTENING:
            return

        self._state = RuntimeState.LOADING
        self._overlay.show_loading()

        # Stop recording and get audio
        try:
            result = self._recorder.stop_and_normalize()
            if result is None:
                print("Recording too short, discarding", file=sys.stderr)
                self._reset_to_idle()
                return
        except Exception as e:
            print(f"Recording error: {e}", file=sys.stderr)
            self._reset_to_idle()
            return

        audio_data_uri, duration = result

        # Process with LLM
        try:
            self._process_recording(audio_data_uri)
        except Exception as e:
            print(f"Processing error: {e}", file=sys.stderr)
            self._overlay.show_error()
            time.sleep(1.0)
            self._reset_to_idle()

    def _process_recording(self, audio_data_uri: str) -> None:
        """Process recorded audio through LLM and inject result."""
        # Load prompts
        system_prompt = load_system_prompt()
        user_prompt = load_user_prompt()

        # Build initial messages
        messages = []

        # System message
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # User message with audio and text
        user_content = []
        user_content.append(
            {
                "type": "input_audio",
                "input_audio": {"data": audio_data_uri},
            }
        )
        if user_prompt:
            user_content.append({"type": "text", "text": user_prompt})

        messages.append({"role": "user", "content": user_content})

        # Run through agent manager (handles ReAct loop)
        if self._active_agent:
            final_text = self._agent_manager.run_agent(
                self._active_agent.name,
                messages,
                self._client,
            )
        else:
            # Fallback: direct client call without agent
            response = self._client.send(messages=messages, tools=None)
            choices = response.get("choices", [])
            if choices:
                final_text = choices[0].get("message", {}).get("content", "")
            else:
                final_text = ""

        # Apply regex transformations
        if self._regex_processor and final_text:
            final_text = self._regex_processor.process_text(final_text)

        # Inject text
        self._state = RuntimeState.APPLYING_RESULT
        if final_text and final_text.strip():
            self._injector.inject(final_text)

        # Reset to idle
        self._reset_to_idle()

    def _reset_to_idle(self) -> None:
        """Reset runtime to idle state."""
        self._state = RuntimeState.IDLE
        self._active_agent = None
        self._overlay.hide()

    def run(self) -> int:
        """Run the main event loop.

        Returns:
            Exit code (0 for normal exit).
        """
        # Bootstrap check
        is_first_run = check_and_bootstrap()
        if is_first_run:
            return 0

        # Acquire single-instance lock
        if not acquire_runtime_lock():
            print("Another instance of noasr is already running.", file=sys.stderr)
            return 1

        try:
            # Initialize components
            if not self.initialize():
                print("Failed to initialize noasr", file=sys.stderr)
                return 1

            # Start overlay
            self._overlay.start()

            # Start hotkey listener
            if not self._hotkey.start():
                print("Failed to start hotkey listener", file=sys.stderr)
                return 1

            print("noasr v0.1.0 - Voice input using MiMo Omni", file=sys.stderr)
            print("Press configured trigger key to start recording.", file=sys.stderr)

            # Keep main thread alive
            try:
                while True:
                    time.sleep(0.1)
                    # Update overlay timer if listening
                    if self._state == RuntimeState.LISTENING:
                        elapsed = time.time() - self._recording_start_time
                        self._overlay.update_elapsed(elapsed)
                        # Auto-stop if max duration reached
                        if elapsed >= MAX_RECORDING_DURATION:
                            self._on_key_up(0)
            except KeyboardInterrupt:
                print("\nShutting down noasr...", file=sys.stderr)

        finally:
            # Cleanup
            self._hotkey.stop()
            self._overlay.stop()
            release_runtime_lock()

        return 0


def main() -> int:
    """Run noasr voice input method."""
    parser = argparse.ArgumentParser(
        prog="noasr",
        description="Voice input method using Xiaomi MiMo Omni multimodal model",
        epilog="Example: noasr",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    args = parser.parse_args()

    runtime = NoasrRuntime()
    return runtime.run()


if __name__ == "__main__":
    sys.exit(main())
