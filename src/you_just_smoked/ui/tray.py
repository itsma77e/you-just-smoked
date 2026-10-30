"""pystray adapter. Runs on the main thread (macOS requires it) and only talks to the
engine through commands; it renders whatever `Status` the engine last published.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import pystray

from you_just_smoked.notify.messages import phrase, status_lines
from you_just_smoked.runtime.commands import Command, LogCigarette, Pause, Resume, Stop
from you_just_smoked.ui.icon import draw_icon

if TYPE_CHECKING:
    from you_just_smoked.runtime.status import Status

_PAUSE = timedelta(hours=1)


class Tray:
    def __init__(self, name: str, submit: Callable[[Command], None], language: str) -> None:
        self._submit = submit
        self._language = language
        self._lines: list[str] = []
        self._paused = False
        self._icon: Any = pystray.Icon(name, draw_icon(), name, menu=self._menu())

    def run(self, setup: Callable[[], None]) -> None:
        """Block on the tray loop. `setup` runs once the icon is visible."""

        def on_ready(icon: Any) -> None:
            icon.visible = True
            setup()

        self._icon.run(setup=on_ready)

    def stop(self) -> None:
        self._icon.stop()

    def show(self, status: Status) -> None:
        """Called from the engine thread with each new status; redraws only on change."""
        lines = self._render(status)
        if lines != self._lines:
            self._lines = lines
            self._icon.title = " · ".join(lines)
            self._icon.update_menu()
        if status.paused != self._paused:
            self._paused = status.paused
            self._icon.icon = draw_icon(paused=status.paused)

    def _render(self, status: Status) -> list[str]:
        lines = status_lines(status.stats, status.at, self._language)
        if status.paused:
            lines.insert(0, phrase("status_paused", self._language))
        if status.camera_error:
            lines.insert(0, phrase("status_camera", self._language))
        return lines

    def _menu(self) -> Any:
        def line(index: int) -> pystray.MenuItem:
            return pystray.MenuItem(
                lambda _item: self._lines[index] if index < len(self._lines) else "",
                None,
                enabled=False,
                visible=lambda _item: index < len(self._lines),
            )

        def text(key: str) -> str:
            return phrase(key, self._language)

        return pystray.Menu(
            *(line(index) for index in range(5)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(text("menu_log"), lambda: self._submit(LogCigarette())),
            pystray.MenuItem(
                text("menu_pause"),
                lambda: self._submit(Pause(_PAUSE)),
                visible=lambda _item: not self._paused,
            ),
            pystray.MenuItem(
                text("menu_resume"),
                lambda: self._submit(Resume()),
                visible=lambda _item: self._paused,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(text("menu_quit"), self._quit),
        )

    def _quit(self) -> None:
        self._submit(Stop())
        self.stop()
