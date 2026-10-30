"""A floating card that slides and fades in next to an anchor point, and back out."""

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

from you_just_smoked.ui import render, theme
from you_just_smoked.ui.anim import Tween, ease_in_cubic
from you_just_smoked.ui.controls import Surface
from you_just_smoked.ui.shell import make_floating, scale_factor, work_area

if TYPE_CHECKING:
    from collections.abc import Callable

_SLIDE = 40
_IN_MS = 280
_OUT_MS = 200


class SlidingCard:
    def __init__(self, root: tk.Tk, size: tuple[float, float]) -> None:
        self.window = tk.Toplevel(root)
        outside = make_floating(self.window)
        self.window.withdraw()
        self.canvas = tk.Canvas(self.window, highlightthickness=0, bg=outside)
        self.canvas.pack(fill="both", expand=True)
        self.surface = Surface(self.canvas, scale_factor(root))
        self.visible = False
        self._width, self._height = (self.surface.px(v) for v in size)
        radius = self.surface.px(theme.RADIUS)
        card = render.card(
            self._width, self._height, color=theme.CARD, radius=radius, outside=outside
        )
        self.surface.image("card", card, 0, 0)
        self.window.geometry(f"{self._width}x{self._height}")

    def slide_in(self, anchor: Callable[[], tuple[int, int]]) -> None:
        """Appear with the bottom-right corner at `anchor()`, kept inside the screen."""
        self.visible = True
        right, bottom = anchor()
        width, height = self._width, self._height
        x, y = right - width, max(bottom - height, work_area(self.window).top)
        start_x = x + self.surface.px(_SLIDE)
        self.window.wm_attributes("-alpha", 0.0)
        self.window.deiconify()

        def step(t: float) -> None:
            self.window.geometry(f"{width}x{height}+{round(start_x + (x - start_x) * t)}+{y}")
            self.window.wm_attributes("-alpha", t)

        Tween(self.window, _IN_MS, step)

    def slide_out(self) -> None:
        if not self.visible:
            return
        self.visible = False
        x, y = self.window.winfo_x(), self.window.winfo_y()
        shift = self.surface.px(_SLIDE)

        def step(t: float) -> None:
            self.window.geometry(f"+{round(x + shift * t)}+{y}")
            self.window.wm_attributes("-alpha", 1 - t)

        Tween(self.window, _OUT_MS, step, done=self.window.withdraw, ease=ease_in_cubic)
