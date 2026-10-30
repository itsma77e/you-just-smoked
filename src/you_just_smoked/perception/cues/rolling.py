"""Two hands working together below the face, fingertips almost touching.

Typing keeps the hands apart and resting your chin puts them above the mouth,
so both are excluded. Clasped hands still pass a single frame, which is why
rolling has a low weight and needs to be seen repeatedly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from you_just_smoked.domain.cues import Cue, CueObservation
from you_just_smoked.perception.cues.base import closeness
from you_just_smoked.perception.scene import HandPoint

if TYPE_CHECKING:
    from you_just_smoked.perception.frame import Frame
    from you_just_smoked.perception.scene import Hand, Scene


@dataclass(frozen=True, slots=True)
class RollingSettings:
    reach: float = 0.6
    """Gap between the two hands' fingertips, in face widths, at which it stops counting."""

    unit_without_face: float = 0.15
    """Stand-in for a face width, in image widths, when no face is visible."""


class RollingDetector:
    def __init__(self, settings: RollingSettings | None = None) -> None:
        self._settings = settings or RollingSettings()

    def close(self) -> None:
        pass

    def detect(self, frame: Frame, scene: Scene) -> list[CueObservation]:
        if len(scene.hands) < 2:
            return []
        first, second = scene.hands[:2]
        if scene.face is not None:
            mouth_y = scene.face.mouth.y
            if not _below(first, mouth_y) or not _below(second, mouth_y):
                return []
            unit = scene.face.scale
        else:
            unit = self._settings.unit_without_face

        gap = min(p.distance_to(q) for p in first.grip_tips() for q in second.grip_tips())
        strength = closeness(gap / unit, self._settings.reach)
        if strength <= 0.0:
            return []
        return [CueObservation(Cue.ROLLING, 0.4 + 0.6 * strength, frame.at)]


def _below(hand: Hand, y: float) -> bool:
    return hand[HandPoint.WRIST].y > y
