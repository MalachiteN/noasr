"""Overlay UI controller for noasr using Flet.

Flet requires the main thread (it calls signal.signal internally).
Therefore run_main() must be called from the main thread — it blocks.
All state changes from background threads go through a queue,
and a Flet-managed background thread polls the queue to apply updates.
"""

import queue
import sys
import threading
from typing import Optional

from noasr.models import OverlayState


class OverlayController:
    """Controls the overlay UI that shows listening/loading state.

    Uses Flet to render a bottom-of-screen black capsule with centered white text.
    Best-effort topmost/non-activating; on Windows prioritized, macOS/Linux degraded.

    Threading model:
    - run_main() MUST be called from the main thread (blocks until stop).
    - show_listening(), show_loading(), show_error(), hide(), update_elapsed()
      are safe to call from any thread — they enqueue state updates.
    - A Flet-managed background thread (via page.run_thread) drains the queue
      and calls page.update() on the Flet event loop, which is thread-safe.
    """

    def __init__(self) -> None:
        self._state = OverlayState.HIDDEN
        self._elapsed_seconds: float = 0.0
        self._page = None
        self._text_control = None
        self._container = None
        self._running = False
        self._update_queue: queue.Queue = queue.Queue()

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
        """Enqueue a state change for the UI thread to process."""
        self._state = state
        self._elapsed_seconds = elapsed
        self._update_queue.put((state, elapsed))

    def _drain_and_apply(self) -> None:
        """Drain all pending state updates and apply the latest one.

        Called on a Flet-managed thread, so page.update() is safe.
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
            self._page.window.visible = latest_state != OverlayState.HIDDEN
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

    def _poll_loop(self) -> None:
        """Periodically drain the update queue. Runs on a Flet-managed thread."""
        import time as _time

        while self._running:
            _time.sleep(0.1)
            if not self._running:
                break
            self._drain_and_apply()

        # On exit, try to destroy the window
        if self._page is not None:
            try:
                self._page.window.destroy()
                self._page.update()
            except Exception:
                pass

    def run_main(self) -> None:
        """Run the Flet app on the main thread. Blocks until stop() is called.

        MUST be called from the main thread. This is the only method
        that interacts with Flet's event loop directly.
        """
        try:
            import flet as ft

            def main(page: ft.Page) -> None:
                self._page = page
                page.title = "noasr"
                page.window.width = 300
                page.window.height = 50
                page.window.resizable = False
                page.bgcolor = ft.Colors.TRANSPARENT
                page.window.bgcolor = ft.Colors.TRANSPARENT
                page.window.maximized = False
                page.window.full_screen = False

                # Position at bottom center
                page.window.alignment = ft.WindowAlignment.CENTER

                # Try to make always on top and non-activating
                try:
                    page.window.always_on_top = True
                    page.window.focused = False
                except Exception:
                    pass

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
                    bgcolor=ft.Colors.BLACK87,
                    border_radius=25,
                    padding=ft.padding.symmetric(horizontal=20, vertical=8),
                    alignment=ft.alignment.center,
                )

                page.add(
                    ft.Row(
                        [self._container],
                        alignment=ft.MainAxisAlignment.CENTER,
                    )
                )

                # Initially hidden
                page.window.visible = False
                page.update()

                # Start the queue-polling thread via Flet's run_thread
                # This ensures page.update() is called from a Flet-aware context
                page.run_thread(self._poll_loop)

            ft.app(target=main, view=ft.AppView.FLET_APP)
        except Exception as e:
            print(f"Overlay error: {e}", file=sys.stderr)
