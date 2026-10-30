"""The Tk application. It owns the main thread; other threads talk to it only through `post`.

Nothing is on screen but the tray icon. The nudge appears when the engine opens an
episode, and the statistics card when the user asks for it from the tray.

Tk is not thread-safe, so messages from the engine and the tray wait in a queue
that the Tk loop drains every 100 ms. User actions go to the engine as commands.
"""

from __future__ import annotations

import logging
import queue
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from you_just_smoked.i18n import text
from you_just_smoked.notify.messages import status_lines
from you_just_smoked.runtime.commands import Command, LogCigarette, Pause, Resume, Stop
from you_just_smoked.ui import sound, theme
from you_just_smoked.ui.nudge import NudgePopup, PopupActions
from you_just_smoked.ui.shell import enable_dpi_awareness, scale_factor, work_area
from you_just_smoked.ui.sound import Chime
from you_just_smoked.ui.tray import Tray, TrayActions
from you_just_smoked.ui.viewmodel import new_badges
from you_just_smoked.ui.widget import Widget, WidgetActions

if TYPE_CHECKING:
    from you_just_smoked.notify.base import AnswerCallback
    from you_just_smoked.notify.messages import NudgeText
    from you_just_smoked.runtime.clock import Clock
    from you_just_smoked.runtime.status import Status
    from you_just_smoked.ui.position import PositionStore

log = logging.getLogger(__name__)

_PUMP_MS = 100
_TICK_MS = 1000
_PAUSE = timedelta(hours=1)


@dataclass(frozen=True, slots=True)
class StatusChanged:
    status: Status


@dataclass(frozen=True, slots=True)
class ShowNudge:
    text: NudgeText
    on_answer: AnswerCallback


@dataclass(frozen=True, slots=True)
class ToggleStats:
    pass


@dataclass(frozen=True, slots=True)
class Shutdown:
    pass


UiMessage = StatusChanged | ShowNudge | ToggleStats | Shutdown


@dataclass(frozen=True, slots=True)
class UiSettings:
    name: str
    language: str
    positions: PositionStore
    sound: bool = True
    computer_day: timedelta = timedelta(hours=8)


class TkNotifier:
    """The `Notifier` port, implemented by asking the UI thread to show the popup."""

    def __init__(self, post: Callable[[UiMessage], None]) -> None:
        self._post = post

    def nudge(self, text: NudgeText, on_answer: AnswerCallback) -> None:
        self._post(ShowNudge(text, on_answer))

    def close(self) -> None:
        pass


class UiApp:
    def __init__(
        self, submit: Callable[[Command], None], settings: UiSettings, clock: Clock
    ) -> None:
        self._submit = submit
        self._settings = settings
        self._clock = clock
        self._inbox: queue.Queue[UiMessage] = queue.Queue()
        self._status: Status | None = None

    def post(self, message: UiMessage) -> None:
        """Thread-safe: the message is handled on the UI thread."""
        self._inbox.put(message)

    def run(self) -> None:
        """Block on the Tk loop until the user quits or `Shutdown` arrives."""
        enable_dpi_awareness()
        self._root = tk.Tk()
        self._root.withdraw()
        language = self._settings.language
        positions = self._settings.positions
        widget_actions = WidgetActions(
            log_cigarette=lambda: self._submit(LogCigarette()),
            open_menu=self._open_menu,
            moved=positions.save,
        )
        self._widget = Widget(self._root, widget_actions, language, positions.load())
        popup_actions = PopupActions(
            chime=self._chime,
            show_stats=self._show_stats,
            computer_day=self._settings.computer_day,
        )
        self._popup = NudgePopup(self._root, language, self._popup_anchor, popup_actions)
        self._menu = tk.Menu(self._root, tearoff=0)
        self._tray = Tray(self._settings.name, self._tray_actions(), language)
        self._tray.start()
        self._root.after(_PUMP_MS, self._pump)
        self._root.after(_TICK_MS, self._tick)
        try:
            self._root.mainloop()
        finally:
            self._tray.stop()

    def _tray_actions(self) -> TrayActions:
        """These run on the tray thread: they only queue work, never touch Tk."""
        return TrayActions(
            show_stats=lambda: self.post(ToggleStats()),
            log_cigarette=lambda: self._submit(LogCigarette()),
            pause=lambda: self._submit(Pause(_PAUSE)),
            resume=lambda: self._submit(Resume()),
            quit=self._quit_from_tray,
        )

    def _pump(self) -> None:
        while True:
            try:
                message = self._inbox.get_nowait()
            except queue.Empty:
                break
            if isinstance(message, Shutdown):
                self._root.destroy()
                return
            try:
                self._handle(message)
            except Exception:
                log.exception("Could not handle %s", type(message).__name__)
        self._root.after(_PUMP_MS, self._pump)

    def _handle(self, message: StatusChanged | ShowNudge | ToggleStats) -> None:
        match message:
            case StatusChanged(status=status):
                self._show(status)
            case ShowNudge(text=nudge, on_answer=on_answer):
                self._popup.ask(nudge, on_answer)
            case ToggleStats():
                self._widget.set_visible(not self._widget.visible)

    def _show(self, status: Status) -> None:
        language = self._settings.language
        previous = self._status.summary if self._status else None
        self._status = status
        now = self._clock.now()
        self._widget.show(status, now)
        self._popup.on_status(status)
        lines = status_lines(status.summary.stats, now, language)
        self._tray.update(lines, paused=status.paused)
        if self._widget.visible:
            for badge in new_badges(previous, status.summary):
                name = text(f"badge_{badge.value}", language)
                self._widget.celebrate(text("badge_unlocked", language, name=name), now)

    def _tick(self) -> None:
        try:
            if self._widget.visible:
                self._widget.tick(self._clock.now())
            self._popup.tick(self._clock.now())
        except Exception:
            log.exception("Could not refresh the interface")
        self._root.after(_TICK_MS, self._tick)

    def _popup_anchor(self) -> tuple[int, int]:
        """Where the popup's bottom-right corner goes: above the card, or in the corner."""
        gap = round(theme.GAP * scale_factor(self._root))
        if self._widget.visible:
            window = self._widget.window
            return window.winfo_x() + window.winfo_width(), window.winfo_y() - gap
        area = work_area(self._root)
        margin = round(theme.MARGIN * scale_factor(self._root))
        return area.right - margin, area.bottom - margin

    def _show_stats(self) -> None:
        self._widget.set_visible(True)
        if not self._widget.expanded:
            self._widget.toggle()

    def _chime(self, chime: Chime) -> None:
        if self._settings.sound:
            sound.play(chime, fallback=self._root.bell)

    def _open_menu(self, x: int, y: int) -> None:
        def label(key: str) -> str:
            return text(key, self._settings.language)

        paused = self._status is not None and self._status.paused
        menu = self._menu
        menu.delete(0, "end")
        menu.add_command(label=label("menu_log"), command=lambda: self._submit(LogCigarette()))
        if paused:
            menu.add_command(label=label("menu_resume"), command=lambda: self._submit(Resume()))
        else:
            menu.add_command(label=label("menu_pause"), command=lambda: self._submit(Pause(_PAUSE)))
        toggle = "menu_collapse" if self._widget.expanded else "menu_expand"
        menu.add_command(label=label(toggle), command=self._widget.toggle)
        menu.add_command(label=label("menu_hide"), command=lambda: self._widget.set_visible(False))
        menu.add_separator()
        menu.add_command(label=label("menu_quit"), command=self._quit)
        menu.tk_popup(x, y)

    def _quit_from_tray(self) -> None:
        self._submit(Stop())
        self.post(Shutdown())

    def _quit(self) -> None:
        self._submit(Stop())
        self._root.destroy()
