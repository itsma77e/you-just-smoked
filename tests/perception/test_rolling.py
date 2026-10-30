from you_just_smoked.domain.cues import Cue
from you_just_smoked.perception.cues.rolling import RollingDetector
from you_just_smoked.perception.scene import Hand, Scene

from factories import blank_frame, face, hand

MOUTH = (0.5, 0.4)


def pair(gap: float, y: float = 0.6) -> tuple[Hand, Hand]:
    left = hand((0.4, y + 0.05), thumb_tip=(0.5 - gap / 2, y), index_tip=(0.5 - gap / 2, y))
    right = hand((0.6, y + 0.05), thumb_tip=(0.5 + gap / 2, y), index_tip=(0.5 + gap / 2, y))
    return left, right


def test_fingertips_together_below_the_face_is_rolling() -> None:
    [observation] = RollingDetector().detect(blank_frame(), Scene(pair(0.01), face(MOUTH)))
    assert observation.cue is Cue.ROLLING
    assert observation.confidence > 0.9


def test_hands_apart_like_typing_is_not_rolling() -> None:
    assert RollingDetector().detect(blank_frame(), Scene(pair(0.4), face(MOUTH))) == []


def test_hands_above_the_mouth_is_not_rolling() -> None:
    scene = Scene(pair(0.01, y=0.2), face(MOUTH))
    assert RollingDetector().detect(blank_frame(), scene) == []


def test_one_hand_is_not_rolling() -> None:
    scene = Scene(pair(0.01)[:1], face(MOUTH))
    assert RollingDetector().detect(blank_frame(), scene) == []


def test_works_without_a_face() -> None:
    assert RollingDetector().detect(blank_frame(), Scene(pair(0.01)))
