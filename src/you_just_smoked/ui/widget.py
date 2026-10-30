"""The statistics card: a live timer since the last cigarette, expandable into the week.

Hidden until opened from the tray. Left click toggles the details, dragging moves
it, right click opens the menu.
Drawing is split by what changes it: `_build` once, `show` per engine status,
`tick` every second.
"""

from __future__ import annotations

import time
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from you_just_smoked.domain.achievements import Badge
from you_just_smoked.i18n import format_duration, text
from you_just_smoked.ui import render, theme
from you_just_smoked.ui.anim import Tween
from you_just_smoked.ui.controls import (
    BODY,
    BUTTON_TAG,
    LABEL,
    MUTED,
    PRIMARY,
    SECTION,
    TIMER,
    Box,
    PillButton,
    Surface,
    TextStyle,
)
from you_just_smoked.ui.shell import make_floating, scale_factor, work_area
from you_just_smoked.ui.viewmodel import Indicator, badge_views, week_view, widget_view

if TYPE_CHECKING:
    from datetime import datetime

    from you_just_smoked.runtime.status import Status

_INDICATOR_COLOURS = {
    Indicator.WATCHING: theme.GOOD,
    Indicator.PAUSED: theme.MUTED,
    Indicator.CAMERA: theme.DANGER,
    Indicator.ACTIVE: theme.EMBER,
    Indicator.POSTPONED: theme.GOLD,
}
_W = theme.WIDGET_WIDTH
_TEXT_X = 104
_BADGE_Y = 258
_BADGE_SIZE = 28
_BADGE_STEP = 38
_GLYPH = TextStyle(9, theme.CARD, "bold", "center")
_DRAG_THRESHOLD = 4
_BANNER = TextStyle(10, theme.GOLD, "bold")


def _badge_group(index: int) -> str:
    """Shared by a badge's dot and glyph, so hovering either shows its name."""
    return f"badge-hover-{index}"


@dataclass(frozen=True, slots=True)
class WidgetActions:
    log_cigarette: Callable[[], None]
    open_menu: Callable[[int, int], None]
    moved: Callable[[int, int], None]


class Widget:
    def __init__(
        self, root: tk.Tk, actions: WidgetActions, language: str, position: tuple[int, int] | None
    ) -> None:
        self.window = tk.Toplevel(root)
        self._outside = make_floating(self.window)
        self._canvas = tk.Canvas(self.window, highlightthickness=0, bg=self._outside)
        self._canvas.pack(fill="both", expand=True)
        self._surface = Surface(self._canvas, scale_factor(root))
        self._actions = actions
        self._language = language
        self._status: Status | None = None
        self.expanded = False
        self._height = float(theme.WIDGET_HEIGHT)
        self._ring_drawn = (-1.0, "")
        self._highlight_until = 0.0
        self._press: tuple[int, int, int, int] | None = None
        self._dragged = False
        self._build()
        self._place(position)
        self.window.withdraw()
        self.visible = False

    def set_visible(self, visible: bool) -> None:
        if visible == self.visible:
            return
        self.visible = visible
        if visible:
            self.window.deiconify()
            self._ring_drawn = (-1.0, "")
        else:
            self.window.withdraw()

    def show(self, status: Status, now: datetime) -> None:
        self._status = status
        view = widget_view(status, now, self._language)
        self._surface.text("today", _TEXT_X, 78, view.today, MUTED)
        dot = render.dot(
            self._px(9), color=_INDICATOR_COLOURS[view.indicator], background=theme.CARD
        )
        self._surface.image("indicator", dot, _W - 22, 14)
        state = replace(MUTED, anchor="ne")
        self._surface.text("state", _W - 16, 114, view.indicator_label, state)
        self._draw_week()
        self._draw_badges()
        self.tick(now)

    def tick(self, now: datetime) -> None:
        if self._status is None:
            return
        view = widget_view(self._status, now, self._language)
        highlighting = time.monotonic() < self._highlight_until
        colour = theme.GOLD if highlighting else theme.EMBER
        if abs(view.progress - self._ring_drawn[0]) > 0.002 or colour != self._ring_drawn[1]:
            self._ring_drawn = (view.progress, colour)
            ring = render.ring(
                self._px(72), view.progress, render.RingStyle(colour, theme.TRACK, 7, theme.CARD)
            )
            self._surface.image("ring", ring, 16, 16)
        self._surface.text("timer", _TEXT_X, 18, view.timer, TIMER)
        if not highlighting:
            caption = f"{view.caption} · {view.goal}" if view.goal else view.caption
            self._surface.text("caption", _TEXT_X, 58, caption, MUTED)

    def celebrate(self, message: str, now: datetime, seconds: float = 6) -> None:
        """Gold ring, the message in place of the caption, and a little hop."""
        self._highlight_until = time.monotonic() + seconds
        self.tick(now)
        self._surface.text("caption", _TEXT_X, 58, message, _BANNER)
        x, top = self.window.winfo_x(), self.window.winfo_y()
        hop = self._px(10)
        Tween(
            self.window,
            420,
            lambda t: self.window.geometry(f"+{x}+{top - round(hop * (1 - abs(2 * t - 1)))}"),
        )

    def toggle(self) -> None:
        self.expanded = not self.expanded
        start = self._height
        end = float(theme.WIDGET_EXPANDED_HEIGHT if self.expanded else theme.WIDGET_HEIGHT)
        bottom = self.window.winfo_y() + self.window.winfo_height()
        upwards = self.window.winfo_y() + self._px(end) > work_area(self.window).bottom

        def step(t: float) -> None:
            self._height = start + (end - start) * t
            self._resize(keep_bottom=bottom if upwards else None)

        Tween(self.window, 260, step)

    # Drawing ----------------------------------------------------------------------------

    def _build(self) -> None:
        """Items that never change: section titles, badge slots and the log button."""
        for tag, y, key in (
            ("week-title", 114, "week_title"),
            ("badges-title", 238, "badges_title"),
        ):
            title = text(key, self._language)
            self._surface.text(tag, 16, y, title, SECTION)
        for index, badge in enumerate(Badge):
            tag = _badge_group(index)
            name = text(f"badge_{badge.value}", self._language)
            self._canvas.tag_bind(tag, "<Enter>", self._caption_handler(name))
            self._canvas.tag_bind(tag, "<Leave>", self._caption_handler(None))
        log_box = Box(16, theme.WIDGET_EXPANDED_HEIGHT - 48, _W - 32, 34)
        PillButton(self._surface, "log", log_box, PRIMARY, self._actions.log_cigarette).draw(
            text("menu_log", self._language)
        )
        for event, handler in (
            ("<ButtonPress-1>", self._on_press),
            ("<B1-Motion>", self._on_drag),
            ("<ButtonRelease-1>", self._on_release),
        ):
            self._canvas.bind(event, handler)
        self._canvas.bind(
            "<ButtonRelease-3>", lambda e: self._actions.open_menu(e.x_root, e.y_root)
        )

    def _draw_week(self) -> None:
        assert self._status is not None
        summary = self._status.summary
        days = week_view(summary, self._language)
        style = render.BarStyle(theme.TRACK, theme.EMBER, theme.CARD)
        chart = render.bars([d.value for d in days], (self._px(_W - 32), self._px(52)), style)
        self._surface.image("bars", chart, 16, 136)
        slot = (_W - 32) / len(days)
        for index, day in enumerate(days):
            colour = theme.TEXT if day.is_today else theme.MUTED
            x = 16 + slot * (index + 0.5)
            self._surface.text(f"day-{index}", x, 192, day.label, replace(LABEL, color=colour))
        best = summary.best_gap_today
        gap = format_duration(best) if best is not None else "-"
        self._surface.text("best", 16, 214, text("best_gap", self._language, gap=gap), BODY)

    def _draw_badges(self) -> None:
        assert self._status is not None
        for index, badge in enumerate(badge_views(self._status.summary, self._language)):
            colour = theme.GOLD if badge.unlocked else theme.TRACK
            picture = render.dot(self._px(_BADGE_SIZE), color=colour, background=theme.CARD)
            x = 16 + _BADGE_STEP * index
            group = (_badge_group(index),)
            self._surface.image(f"badge-{index}", picture, x, _BADGE_Y, groups=group)
            glyph = _GLYPH if badge.unlocked else replace(_GLYPH, color=theme.MUTED)
            centre_x, centre_y = x + _BADGE_SIZE / 2, _BADGE_Y + _BADGE_SIZE / 2
            self._surface.text(
                f"glyph-{index}", centre_x, centre_y, badge.glyph, glyph, groups=group
            )
        self._badge_caption(None)
        streak = self._status.summary.streak
        line = text(
            "companion_streak", self._language, count=streak.current, jollies=streak.jollies
        )
        self._surface.text("streak", _W - 16, 292, line, replace(MUTED, anchor="ne"))

    def _caption_handler(self, name: str | None) -> Callable[[tk.Event[tk.Canvas]], None]:
        return lambda _event: self._badge_caption(name)

    def _badge_caption(self, name: str | None) -> None:
        """Show the hovered badge's name, or how many are unlocked."""
        if name is not None:
            self._surface.text("badge-name", 16, 292, name, BODY)
        elif self._status is not None:
            unlocked = len(self._status.summary.achievements)
            self._surface.text("badge-name", 16, 292, f"{unlocked} / {len(Badge)}", MUTED)

    def _resize(self, *, keep_bottom: int | None) -> None:
        width, height = self._px(_W), self._px(self._height)
        radius = self._px(theme.RADIUS)
        card = render.card(width, height, color=theme.CARD, radius=radius, outside=self._outside)
        self._surface.image("card", card, 0, 0)
        self._canvas.tag_lower("card")
        y = keep_bottom - height if keep_bottom is not None else self.window.winfo_y()
        self.window.geometry(f"{width}x{height}+{self.window.winfo_x()}+{y}")

    def _px(self, value: float) -> int:
        return self._surface.px(value)

    # Placement and input ----------------------------------------------------------------

    def _place(self, position: tuple[int, int] | None) -> None:
        area = work_area(self.window)
        width, height, margin = self._px(_W), self._px(self._height), self._px(theme.MARGIN)
        x, y = position or (area.right - width - margin, area.bottom - height - margin)
        x = min(max(x, area.left), area.right - width)
        y = min(max(y, area.top), area.bottom - height)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.window.update_idletasks()
        self._resize(keep_bottom=None)

    def _on_press(self, event: tk.Event[tk.Canvas]) -> None:
        self._press = (event.x_root, event.y_root, self.window.winfo_x(), self.window.winfo_y())
        self._dragged = False

    def _on_drag(self, event: tk.Event[tk.Canvas]) -> None:
        if self._press is None:
            return
        start_x, start_y, window_x, window_y = self._press
        dx, dy = event.x_root - start_x, event.y_root - start_y
        if self._dragged or abs(dx) + abs(dy) > _DRAG_THRESHOLD:
            self._dragged = True
            self.window.geometry(f"+{window_x + dx}+{window_y + dy}")

    def _on_release(self, _event: tk.Event[tk.Canvas]) -> None:
        if self._dragged:
            self._actions.moved(self.window.winfo_x(), self.window.winfo_y())
        elif BUTTON_TAG not in self._canvas.gettags("current"):
            self.toggle()
        self._press = None
