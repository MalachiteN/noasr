"""Overlay UI controller for noasr using Flet.

Flet requires the main thread (it calls signal.signal internally).
Therefore run_main() must be called from the main thread — it blocks.
All state changes from background threads go through a queue,
and an asyncio task on Flet's event loop drains the queue and applies updates.

The window is always present but hidden via opacity=0.0.
When active, opacity is set to 1.0 to reveal the overlay.
Position: horizontally centered, vertically at 5% from the bottom of the screen.

Flet 0.84+ requires async main + page.run_task() for reliable UI updates.
Using page.run_thread() + page.update() does NOT reliably trigger rendering.
"""

import asyncio
import queue
import sys
from typing import Callable, Optional

from noasr.models import OverlayState


class OverlayError(Exception):
    """Raised when the overlay fails to start or encounters a fatal error."""


def _get_screen_size() -> tuple[int, int]:
    """Get the primary screen size in pixels. Returns (width, height)."""
    if sys.platform == "win32":
        import ctypes

        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    # Fallback for non-Windows: reasonable defaults
    return 1920, 1080


# Overlay window dimensions
_WINDOW_WIDTH = 320
_WINDOW_HEIGHT = 56


class OverlayController:
    """Controls the overlay UI that shows listening/loading state.

    Uses Flet to render a bottom-of-screen black capsule with centered white text.
    Best-effort topmost/non-activating; on Windows prioritized, macOS/Linux degraded.

    Threading model:
    - run_main() MUST be called from the main thread (blocks until stop).
    - show_listening(), show_loading(), show_error(), hide(), update_elapsed()
      are safe to call from any thread — they enqueue state updates.
    - An asyncio task on Flet's event loop (via page.run_task) drains the queue
      and calls page.update(), which reliably triggers rendering.

    Lifecycle:
    - The window starts with opacity=0 (invisible but present).
    - Show/hide toggles opacity between 1.0 and 0.0.
    - When the Flet window is closed by the user, the on_close callback
      is invoked so the runtime can coordinate a clean shutdown.
    - run_main() raises OverlayError if Flet fails to start; returns normally
      on clean exit (window closed or stop() called).
    """

    def __init__(self, on_close: Optional[Callable[[], None]] = None) -> None:
        self._state = OverlayState.HIDDEN
        self._elapsed_seconds: float = 0.0
        self._page = None
        self._text_control = None
        self._container = None
        self._running = False
        self._update_queue: queue.Queue = queue.Queue()
        self._on_close = on_close

    @property
    def state(self) -> OverlayState:
        """Current overlay state."""
        return self._state

    def start(self) -> None:
        """Mark overlay as running (does not start Flet — run_main does that)."""
        self._running = True

    def stop(self) -> None:
        """Signal the overlay to stop."""
        self._running = False
        self._state = OverlayState.HIDDEN

    def show_listening(self, elapsed: float = 0.0) -> None:
        """Show listening state with elapsed time. Thread-safe."""
        self._enqueue(OverlayState.LISTENING, elapsed)

    def show_loading(self) -> None:
        """Show loading state. Thread-safe."""
        self._enqueue(OverlayState.LOADING)

    def show_error(self) -> None:
        """Show error state. Thread-safe."""
        self._enqueue(OverlayState.ERROR)

    def hide(self) -> None:
        """Hide the overlay. Thread-safe."""
        self._enqueue(OverlayState.HIDDEN)

    def update_elapsed(self, elapsed: float) -> None:
        """Update the elapsed time display. Thread-safe."""
        if self._state == OverlayState.LISTENING:
            self._enqueue(OverlayState.LISTENING, elapsed)

    def _enqueue(self, state: OverlayState, elapsed: float = 0.0) -> None:
        """Enqueue a state change for the UI task to process."""
        self._state = state
        self._elapsed_seconds = elapsed
        self._update_queue.put((state, elapsed))

    def _drain_and_apply(self) -> None:
        """Drain all pending state updates and apply the latest one.

        Called on Flet's event loop via an asyncio task, so page.update()
        reliably triggers rendering.
        """
        latest_state: Optional[OverlayState] = None
        latest_elapsed: float = 0.0
        # Drain all pending updates, keep only the latest
        while not self._update_queue.empty():
            try:
                latest_state, latest_elapsed = self._update_queue.get_nowait()
            except queue.Empty:
                break

        if latest_state is None:
            return

        if self._page is None or self._text_control is None:
            return

        try:
            text = self._get_display_text(latest_state, latest_elapsed)
            self._text_control.value = text
            # Toggle opacity: 1.0 when active, 0.0 when hidden
            self._page.window.opacity = (
                1.0 if latest_state != OverlayState.HIDDEN else 0.0
            )
            self._page.update()
        except Exception:
            pass

    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS."""
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{mins:02d}:{secs:02d}"

    def _get_display_text(self, state: OverlayState, elapsed: float) -> str:
        """Get the text to display based on state."""
        if state == OverlayState.LISTENING:
            return f"● Listening {self._format_time(elapsed)}"
        elif state == OverlayState.LOADING:
            return "⏳ Processing"
        elif state == OverlayState.ERROR:
            return "❌ Error"
        return ""

    async def _poll_task(self) -> None:
        """Periodically drain the update queue. Runs as an asyncio task on Flet's event loop.

        Using asyncio.sleep + page.update() from Flet's event loop ensures
        reliable UI rendering (unlike page.run_thread + page.update).
        """
        while self._running:
            await asyncio.sleep(0.1)
            if not self._running:
                break
            self._drain_and_apply()

    def run_main(self) -> None:
        """Run the Flet app on the main thread. Blocks until stop() or window close.

        MUST be called from the main thread. This is the only method
        that interacts with Flet's event loop directly.

        Raises:
            OverlayError: If Flet fails to start or encounters a fatal error.
        """
        try:
            import flet as ft
        except ImportError as e:
            raise OverlayError(
                "Flet is not installed. Install with: pip install flet"
            ) from e

        # Calculate window position: horizontal center, 5% from bottom
        screen_w, screen_h = _get_screen_size()
        win_left = (screen_w - _WINDOW_WIDTH) // 2
        win_top = int(screen_h * 0.95) - _WINDOW_HEIGHT

        async def main(page: ft.Page) -> None:
            self._page = page
            page.title = "noasr"

            # Frameless, always-on-top overlay capsule
            page.window.width = _WINDOW_WIDTH
            page.window.height = _WINDOW_HEIGHT
            page.window.left = win_left
            page.window.top = win_top
            page.window.resizable = False
            page.window.frameless = True
            page.window.skip_task_bar = True
            page.window.always_on_top = True
            page.window.focused = False
            page.window.shadow = False

            # Start invisible (opacity 0)
            page.window.opacity = 0.0

            # Transparent backgrounds so only the capsule is visible
            page.bgcolor = ft.Colors.TRANSPARENT
            page.window.bgcolor = ft.Colors.TRANSPARENT

            # Wire window close event to trigger coordinated shutdown
            def _on_window_event(e: ft.WindowEvent) -> None:
                if e.type == ft.WindowEventType.CLOSE:
                    self._running = False
                    if self._on_close is not None:
                        self._on_close()

            page.window.on_event = _on_window_event

            # Text control
            self._text_control = ft.Text(
                value="",
                color=ft.Colors.WHITE,
                size=14,
                text_align=ft.TextAlign.CENTER,
                font_family="sans-serif",
            )

            # Container with black background, capsule shape
            self._container = ft.Container(
                content=self._text_control,
                bgcolor=ft.Colors.BLACK_87,
                border_radius=25,
                padding=ft.Padding.symmetric(horizontal=20, vertical=8),
                alignment=ft.Alignment.CENTER,
            )

            page.add(
                ft.Row(
                    [self._container],
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            )

            page.update()

            # Start the poll task on Flet's event loop (async, not thread)
            # This ensures page.update() reliably triggers rendering
            page.run_task(self._poll_task)

        try:
            ft.app(target=main, view=ft.AppView.FLET_APP)
        except Exception as e:
            raise OverlayError(f"Flet failed: {e}") from e
