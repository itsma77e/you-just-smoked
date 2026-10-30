"""A short confetti burst on a canvas. Plain rectangles and gravity; cleans up after itself."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from you_just_smoked.ui import theme
from you_just_smoked.ui.anim import Tween

if TYPE_CHECKING:
    import tkinter as tk

_COLOURS = (theme.EMBER, theme.GOLD, theme.GOOD, theme.TEXT, theme.EMBER_SOFT)
_TAG = "confetti"


@dataclass(slots=True)
class _Piece:
    item: int
    x: float
    y: float
    vx: float
    vy: float


def burst(canvas: tk.Canvas, origin: tuple[float, float], *, scale: float, count: int = 40) -> None:
    """Throw `count` pieces up from `origin` (physical pixels) and let them fall for ~1.4 s."""
    canvas.delete(_TAG)
    size = 4 * scale
    pieces = []
    for _ in range(count):
        x, y = origin
        item = canvas.create_rectangle(x, y, x + size, y + size * 1.6, width=0, tags=_TAG)
        canvas.itemconfigure(item, fill=random.choice(_COLOURS))
        speed = scale * random.uniform(2.5, 6.5)
        angle = random.uniform(-1.0, 1.0)
        pieces.append(_Piece(item, x, y, speed * angle, -speed * random.uniform(0.9, 1.6)))

    def step(_progress: float) -> None:
        for piece in pieces:
            piece.vy += 0.28 * scale
            piece.x += piece.vx
            piece.y += piece.vy
            canvas.coords(piece.item, piece.x, piece.y, piece.x + size, piece.y + size * 1.6)

    Tween(canvas, 1400, step, done=lambda: canvas.delete(_TAG), ease=lambda t: t)
