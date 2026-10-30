"""A small tab on the screen edge that keeps a hidden wait challenge in sight.

Shows a mini ring and the time left; clicking it brings the challenge back.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from you_just_smoked.ui import render, theme
from you_just_smoked.ui.controls import Surface, TextStyle
from you_just_smoked.ui.shell import make_floating, scale_factor, work_area

_W, _H = 104, 44
_RING = 28
_CLOCK = TextStyle(12, theme.TEXT, "bold")


class EdgeTab:
    def __init__(self, root: tk.Tk, on_open: Callable[[], None]) -> None:
        self._window = tk.Toplevel(root)
        outside = make_floating(self._window)
        self._window.withdraw()
        self._canvas = tk.Canvas(self._window, highlightthickness=0, bg=outside, cursor="hand2")
        self._canvas.pack(fill="both", expand=True)
        self._surface = Surface(self._canvas, scale_factor(root))
        width, height = self._surface.px(_W), self._surface.px(_H)
        radius = self._surface.px(_H / 2)
        card = render.card(width, height, color=theme.CARD, radius=radius, outside=outside)
        self._surface.image("card", card, 0, 0)
        self._canvas.bind("<ButtonRelease-1>", lambda _event: on_open())
        self.visible = False

    def show(self) -> None:
        if self.visible:
            return
        self.visible = True
        area = work_area(self._window)
        width, height = self._surface.px(_W), self._surface.px(_H)
        margin = self._surface.px(theme.MARGIN)
        x, y = area.right - width - margin // 2, area.bottom - height - margin
        self._window.geometry(f"{width}x{height}+{x}+{y}")
        self._window.deiconify()

    def hide(self) -> None:
        if self.visible:
            self.visible = False
            self._window.withdraw()

    def update(self, remaining_s: float, fraction: float) -> None:
        if not self.visible:
            return
        style = render.RingStyle(theme.GOLD, theme.TRACK, 4, theme.CARD)
        ring = render.ring(self._surface.px(_RING), fraction, style)
        self._surface.image("ring", ring, 10, (_H - _RING) / 2)
        minutes, seconds = divmod(int(remaining_s + 0.999), 60)
        self._surface.text("clock", 46, 13, f"{minutes}:{seconds:02}", _CLOCK)
