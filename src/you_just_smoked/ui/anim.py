"""A tiny tween helper on top of Tk's `after`, so animations never block the event loop."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk

_FRAME_MS = 15


def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def ease_in_cubic(t: float) -> float:
    return t**3


class Tween:
    """Calls `step(progress)` with eased progress 0 -> 1 over `duration_ms`, then `done`."""

    def __init__(
        self,
        widget: tk.Misc,
        duration_ms: int,
        step: Callable[[float], None],
        *,
        done: Callable[[], None] | None = None,
        ease: Callable[[float], float] = ease_out_cubic,
    ) -> None:
        self._widget = widget
        self._duration = duration_ms / 1000
        self._step = step
        self._done = done
        self._ease = ease
        self._start = time.perf_counter()
        self._cancelled = False
        self._frame()

    def cancel(self) -> None:
        self._cancelled = True

    def _frame(self) -> None:
        if self._cancelled:
            return
        progress = min((time.perf_counter() - self._start) / self._duration, 1.0)
        self._step(self._ease(progress))
        if progress < 1.0:
            self._widget.after(_FRAME_MS, self._frame)
        elif self._done is not None:
            self._done()
