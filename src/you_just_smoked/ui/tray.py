"""The tray icon: the app's only permanent presence on screen.

pystray runs its own loop on a background thread. Its callbacks never touch Tk;
they only call the actions given here, which post messages or engine commands.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pystray

from you_just_smoked.i18n import text
from you_just_smoked.ui.icon import draw_icon

_STATUS_LINES = 4


@dataclass(frozen=True, slots=True)
class TrayActions:
    show_stats: Callable[[], None]
    log_cigarette: Callable[[], None]
    pause: Callable[[], None]
    resume: Callable[[], None]
    quit: Callable[[], None]


class Tray:
    def __init__(self, name: str, actions: TrayActions, language: str) -> None:
        self._actions = actions
        self._language = language
        self._lines: list[str] = []
        self._paused = False
        self._icon: Any = pystray.Icon(name, draw_icon(), name, menu=self._menu())

    def start(self) -> None:
        self._icon.run_detached()

    def stop(self) -> None:
        self._icon.stop()

    def update(self, lines: list[str], *, paused: bool) -> None:
        """Refresh the tooltip, the status lines and the pause entry; cheap when unchanged."""
        if lines != self._lines:
            self._lines = lines
            self._icon.title = " · ".join(lines)
            self._icon.update_menu()
        if paused != self._paused:
            self._paused = paused
            self._icon.icon = draw_icon(paused=paused)
            self._icon.update_menu()

    def _menu(self) -> Any:
        def label(key: str) -> str:
            return text(key, self._language)

        def status_line(index: int) -> pystray.MenuItem:
            return pystray.MenuItem(
                lambda _item: self._lines[index] if index < len(self._lines) else "",
                None,
                enabled=False,
                visible=lambda _item: index < len(self._lines),
            )

        actions = self._actions
        return pystray.Menu(
            *(status_line(index) for index in range(_STATUS_LINES)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(label("menu_stats"), actions.show_stats, default=True),
            pystray.MenuItem(label("menu_log"), actions.log_cigarette),
            pystray.MenuItem(
                label("menu_pause"),
                actions.pause,
                visible=lambda _item: not self._paused,
            ),
            pystray.MenuItem(
                label("menu_resume"),
                actions.resume,
                visible=lambda _item: self._paused,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(label("menu_quit"), actions.quit),
        )
