"""Overlay UI controller for noasr using Flet."""

import sys
import threading
from typing import Optional

from noasr.models import OverlayState


class OverlayController:
    """Controls the overlay UI that shows listening/loading state.

    Uses Flet to render a bottom-of-screen black capsule with centered white text.
    Best-effort topmost/non-activating; on Windows prioritized, macOS/Linux degraded.
    """

    def __init__(self) -> None:
        self._state = OverlayState.HIDDEN
        self._elapsed_seconds: float = 0.0
        self._page = None
        self._text_control = None
        self._app_thread: Optional[threading.Thread] = None
        self._running = False

    @property
    def state(self) -> OverlayState:
        """Current overlay state."""
        return self._state

    def start(self) -> None:
        """Start the overlay in a background thread."""
        if self._running:
            return
        self._running = True
        self._app_thread = threading.Thread(target=self._run_app, daemon=True)
        self._app_thread.start()

    def stop(self) -> None:
        """Stop the overlay."""
        self._running = False
        self._state = OverlayState.HIDDEN

    def show_listening(self, elapsed: float = 0.0) -> None:
        """Show listening state with elapsed time."""
        self._state = OverlayState.LISTENING
        self._elapsed_seconds = elapsed
        self._update_display()

    def show_loading(self) -> None:
        """Show loading state."""
        self._state = OverlayState.LOADING
        self._update_display()

    def show_error(self) -> None:
        """Show error state."""
        self._state = OverlayState.ERROR
        self._update_display()

    def hide(self) -> None:
        """Hide the overlay."""
        self._state = OverlayState.HIDDEN
        self._update_display()

    def update_elapsed(self, elapsed: float) -> None:
        """Update the elapsed time display."""
        self._elapsed_seconds = elapsed
        if self._state == OverlayState.LISTENING:
            self._update_display()

    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS."""
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{mins:02d}:{secs:02d}"

    def _get_display_text(self) -> str:
        """Get the text to display based on current state."""
        if self._state == OverlayState.LISTENING:
            return f"Listening {self._format_time(self._elapsed_seconds)}"
        elif self._state == OverlayState.LOADING:
            return "Loading"
        elif self._state == OverlayState.ERROR:
            return "Error"
        return ""

    def _update_display(self) -> None:
        """Update the overlay display."""
        if self._page is None or self._text_control is None:
            return
        try:
            text = self._get_display_text()
            self._text_control.value = text
            self._page.window.visible = self._state != OverlayState.HIDDEN
            self._page.update()
        except Exception:
            pass

    def _run_app(self) -> None:
        """Run the Flet app in a background thread."""
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
                container = ft.Container(
                    content=self._text_control,
                    bgcolor=ft.Colors.BLACK87,
                    border_radius=25,
                    padding=ft.padding.symmetric(horizontal=20, vertical=8),
                    alignment=ft.alignment.center,
                )

                page.add(
                    ft.Row(
                        [container],
                        alignment=ft.MainAxisAlignment.CENTER,
                    )
                )

                # Initially hidden
                page.window.visible = False
                page.update()

            ft.app(target=main, view=ft.AppView.FLET_APP)
        except Exception as e:
            print(f"Overlay error: {e}", file=sys.stderr)
