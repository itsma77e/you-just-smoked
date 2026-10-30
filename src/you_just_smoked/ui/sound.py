"""Short system sounds, so the nudge is noticed without looking at the screen.

Uses each platform's own notification sounds (so it follows the user's sound
scheme and volume) and never blocks the interface.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from enum import StrEnum

_MAC_SOUNDS = {"nudge": "Glass", "done": "Hero"}


class Chime(StrEnum):
    NUDGE = "nudge"
    """The popup appears."""

    DONE = "done"
    """The wait challenge is over."""


def play(chime: Chime, *, fallback: Callable[[], None]) -> None:
    """Play `chime` asynchronously; `fallback` (e.g. Tk's bell) where no sound is available."""
    if sys.platform == "win32":
        import winsound  # noqa: PLC0415 - Windows only

        beep = winsound.MB_ICONEXCLAMATION if chime is Chime.NUDGE else winsound.MB_ICONASTERISK
        winsound.MessageBeep(beep)
    elif sys.platform == "darwin":
        sound = f"/System/Library/Sounds/{_MAC_SOUNDS[chime.value]}.aiff"
        subprocess.Popen(["/usr/bin/afplay", sound])
    else:
        fallback()
