"""A hand at the mouth with two fingertips pinched together, as when holding a cigarette.

A puff is a movement: the hand comes to the mouth and leaves. So only the frame
where the hand *arrives* counts. A hand resting there (chin on hand, thinking)
counts once, not on every frame. Drinking and nail biting still look similar,
which is fine: a puff alone never opens an episode, it takes several of them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from you_just_smoked.domain.cues import Cue, CueObservation
from you_just_smoked.perception.cues.base import closeness
from you_just_smoked.perception.scene import Face, Hand, HandPoint

if TYPE_CHECKING:
    from you_just_smoked.perception.frame import Frame
    from you_just_smoked.perception.scene import Scene


@dataclass(frozen=True, slots=True)
class PuffSettings:
    reach: float = 0.5
    """Fingertip-to-mouth distance, in face widths, at which a hand stops counting."""

    pinch: float = 0.3
    """Maximum distance between two fingertips, in face widths, to count as holding."""


class PuffDetector:
    def __init__(self, settings: PuffSettings | None = None) -> None:
        self._settings = settings or PuffSettings()
        self._was_at_mouth = False

    def close(self) -> None:
        pass

    def detect(self, frame: Frame, scene: Scene) -> list[CueObservation]:
        face = scene.face
        if face is None:
            self._was_at_mouth = False
            return []
        strength = max((self._strength(hand, face) for hand in scene.hands), default=0.0)
        arrived = strength > 0.0 and not self._was_at_mouth
        self._was_at_mouth = strength > 0.0
        if not arrived:
            return []
        return [CueObservation(Cue.PUFF, 0.5 + 0.5 * strength, frame.at)]

    def _strength(self, hand: Hand, face: Face) -> float:
        unit = face.scale
        tips = (hand[HandPoint.THUMB_TIP], hand[HandPoint.INDEX_TIP], hand[HandPoint.MIDDLE_TIP])
        thumb, index, middle = tips
        pinch = min(index.distance_to(middle), thumb.distance_to(index)) / unit
        if pinch > self._settings.pinch:
            return 0.0
        nearest = min(tip.distance_to(face.mouth) for tip in tips) / unit
        return closeness(nearest, self._settings.reach)
