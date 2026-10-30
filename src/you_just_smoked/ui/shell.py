"""Platform quirks for small floating windows: DPI, transparency and the usable screen area."""

from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from you_just_smoked.ui import theme

if TYPE_CHECKING:
    import tkinter as tk


@dataclass(frozen=True, slots=True)
class Area:
    left: int
    top: int
    right: int
    bottom: int


def enable_dpi_awareness() -> None:
    """Render crisply on scaled Windows displays. Call before creating the Tk root."""
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()


def scale_factor(root: tk.Misc) -> float:
    """Logical-to-physical pixel ratio: 1.0 at 96 DPI, 1.5 at 150% scaling."""
    return max(root.winfo_fpixels("1i") / 96.0, 1.0)


def make_floating(window: tk.Tk | tk.Toplevel) -> str:
    """Frameless, always on top, out of the taskbar. Returns the colour to paint outside
    the card: a transparency key on Windows, the card colour elsewhere (square corners)."""
    window.wm_overrideredirect(True)
    window.wm_attributes("-topmost", True)
    if sys.platform == "win32":
        window.configure(bg=theme.TRANSPARENT_KEY)
        window.wm_attributes("-transparentcolor", theme.TRANSPARENT_KEY)
        return theme.TRANSPARENT_KEY
    window.configure(bg=theme.CARD)
    return theme.CARD


def work_area(root: tk.Misc) -> Area:
    """The screen minus the taskbar or dock."""
    if sys.platform == "win32":
        rect = (ctypes.c_long * 4)()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
            return Area(*rect)
    return Area(0, 0, root.winfo_screenwidth(), root.winfo_screenheight() - 64)
