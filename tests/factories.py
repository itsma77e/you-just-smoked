"""Small builders shared by the tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np

from you_just_smoked.domain.cues import Cue, CueObservation
from you_just_smoked.perception.frame import Frame, Image
from you_just_smoked.perception.scene import Face, Hand, HandPoint, Point

T0 = datetime(2026, 10, 30, 9, 0, tzinfo=UTC)


def at(seconds: float = 0, *, minutes: float = 0) -> datetime:
    return T0 + timedelta(seconds=seconds, minutes=minutes)


def seen(
    cue: Cue, seconds: float = 0, *, minutes: float = 0, confidence: float = 1.0
) -> CueObservation:
    return CueObservation(cue, confidence, at(seconds, minutes=minutes))


def face(mouth: tuple[float, float] = (0.5, 0.45), width: float = 0.2) -> Face:
    """A face whose box is centred on the mouth horizontally."""
    x, y = mouth
    return Face(
        left=x - width / 2, top=y - width, width=width, height=width * 1.2, mouth=Point(x, y)
    )


def hand(wrist: tuple[float, float], **tips: tuple[float, float]) -> Hand:
    """A hand with every landmark on the wrist, except the named fingertips."""
    points = [Point(*wrist)] * 21
    for name, (x, y) in tips.items():
        points[HandPoint[name.upper()]] = Point(x, y)
    return Hand(tuple(points))


def blank_frame(width: int = 320, height: int = 240) -> Frame:
    return Frame(np.zeros((height, width, 3), dtype=np.uint8), T0)


def frame_of(image: Image) -> Frame:
    return Frame(image, T0)
