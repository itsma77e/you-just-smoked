"""Plain geometry describing who is in the frame.

Both axes are measured in image widths, so x is in [0, 1], y is in
[0, height / width] and distances are not distorted by the aspect ratio.

Keeping this free of MediaPipe types lets every cue detector be tested with
hand-written points instead of real images.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float

    def distance_to(self, other: Point) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


class HandPoint(IntEnum):
    """Indices of the 21 MediaPipe hand landmarks we care about."""

    WRIST = 0
    THUMB_TIP = 4
    INDEX_TIP = 8
    MIDDLE_TIP = 12
    RING_TIP = 16
    PINKY_TIP = 20


GRIP_TIPS = (HandPoint.THUMB_TIP, HandPoint.INDEX_TIP, HandPoint.MIDDLE_TIP)


@dataclass(frozen=True, slots=True)
class Hand:
    landmarks: tuple[Point, ...]

    def __post_init__(self) -> None:
        if len(self.landmarks) != 21:
            raise ValueError(f"a hand has 21 landmarks, got {len(self.landmarks)}")

    def __getitem__(self, point: HandPoint) -> Point:
        return self.landmarks[point]

    def grip_tips(self) -> tuple[Point, ...]:
        return tuple(self[tip] for tip in GRIP_TIPS)


@dataclass(frozen=True, slots=True)
class Face:
    left: float
    top: float
    width: float
    height: float
    mouth: Point

    @property
    def scale(self) -> float:
        """Face width, used as the unit of distance so cues work at any camera distance."""
        return max(self.width, 1e-6)


@dataclass(frozen=True, slots=True)
class Scene:
    hands: tuple[Hand, ...] = ()
    face: Face | None = None

    @property
    def someone_visible(self) -> bool:
        return self.face is not None or bool(self.hands)

    def hand_near_face(self, reach: float = 1.5) -> bool:
        """A fingertip within `reach` face widths of the mouth: something may be about to happen."""
        face = self.face
        if face is None:
            return False
        return any(
            tip.distance_to(face.mouth) <= reach * face.scale
            for hand in self.hands
            for tip in hand.grip_tips()
        )
