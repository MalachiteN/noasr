"""Main entry point and runtime orchestration for noasr."""

import argparse
import base64
import json
import sys
import threading
import time
from typing import Optional

from noasr.agent import AgentManager, AgentType
from noasr.audio import AudioRecorder
from noasr.client import MiMoClient
from noasr.config import (
    check_and_bootstrap,
    load_config,
    load_regex_registry,
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

        if not self._agent_manager.list_agents():
            print(
                "Error: No agents configured. Edit ~/.noasr/config.json",
                file=sys.stderr,
            )
            return False

        # Initialize MiMo client
        self._client = MiMoClient(
            api_key=self._config.api_key,
            base_url=self._config.baseurl,
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
        registry = load_regex_registry()
        self._regex_processor.load_rules(registry)

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

        # Show overlay (non-fatal if it fails)
        try:
            self._overlay.show_listening(0.0)
        except Exception as e:
            print(f"Warning: overlay show_listening failed: {e}", file=sys.stderr)

    def _on_key_up(self, key_code: int) -> None:
        """Handle key release event."""
        if self._state != RuntimeState.LISTENING:
            return

        self._state = RuntimeState.LOADING
        self._overlay.show_loading()

        # Stop recording and get audio
        try:
            wav_bytes = self._recorder.stop_and_normalize()
        except Exception as e:
            print(f"Recording error: {e}", file=sys.stderr)
            self._reset_to_idle()
            return

        # Convert WAV bytes to base64 data URI
        audio_data_uri = (
            f"data:audio/wav;base64,{base64.b64encode(wav_bytes).decode('utf-8')}"
        )

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
        # All LLM interaction goes through AgentManager
        if self._active_agent is None:
            print("Error: No active agent for recording", file=sys.stderr)
            self._reset_to_idle()
            return

        final_text = self._agent_manager.run_agent(
            self._active_agent.name, audio_data_uri, self._client
        )

        # Apply regex transformations
        if self._regex_processor and final_text:
            final_text = self._regex_processor.apply(final_text)

        # Inject text
        self._state = RuntimeState.APPLYING_RESULT
        if final_text and final_text.strip():
            try:
                self._injector.inject(final_text)
            except Exception as e:
                print(f"Error: Text injection failed: {e}", file=sys.stderr)
                try:
                    self._overlay.show_error()
                    time.sleep(1.0)
                except Exception:
                    pass

        # Reset to idle
        self._reset_to_idle()

    def _reset_to_idle(self) -> None:
        """Reset runtime to idle state.

        State is always reset even if overlay operations fail,
        to prevent the runtime from getting wedged in a non-IDLE state.
        """
        self._state = RuntimeState.IDLE
        self._active_agent = None
        try:
            self._overlay.hide()
        except Exception as e:
            print(f"Warning: overlay hide failed: {e}", file=sys.stderr)

    def run(self) -> int:
        """Run the main event loop.

        The overlay (Flet) requires the main thread, so run_main() blocks here.
        The polling loop (elapsed timer, auto-stop) runs in a background thread.

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

            # Start overlay (sets _running flag)
            self._overlay.start()

            # Start hotkey listener
            if not self._hotkey.start():
                print("Failed to start hotkey listener", file=sys.stderr)
                return 1

            print("noasr v0.1.0 - Voice input using MiMo Omni", file=sys.stderr)
            print("Press configured trigger key to start recording.", file=sys.stderr)

            # Run polling loop in background thread
            def _poll_loop() -> None:
                try:
                    while self._overlay.state is not None:  # runs until overlay stops
                        time.sleep(0.1)
                        # Update overlay timer if listening
                        if self._state == RuntimeState.LISTENING:
                            elapsed = time.time() - self._recording_start_time
                            self._overlay.update_elapsed(elapsed)
                            # Auto-stop if max duration reached
                            if elapsed >= MAX_RECORDING_DURATION:
                                self._on_key_up(0)
                except Exception:
                    pass

            poll_thread = threading.Thread(target=_poll_loop, daemon=True)
            poll_thread.start()

            # Run overlay on main thread (blocks until stop())
            self._overlay.run_main()

        except KeyboardInterrupt:
            print("\nShutting down noasr...", file=sys.stderr)
        finally:
            # Cleanup (guard against partial initialization)
            if self._hotkey is not None:
                self._hotkey.stop()
            if self._overlay is not None:
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
