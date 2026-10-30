from you_just_smoked.domain.cues import Cue
from you_just_smoked.perception.cues.puff import PuffDetector
from you_just_smoked.perception.scene import Scene

from factories import blank_frame, face, hand

MOUTH = (0.5, 0.45)


def holding_at(x: float, y: float) -> Scene:
    fingers = hand(
        (x, y + 0.1), thumb_tip=(x, y + 0.01), index_tip=(x, y), middle_tip=(x + 0.02, y)
    )
    return Scene(hands=(fingers,), face=face(MOUTH))


def test_pinched_fingers_at_the_mouth_is_a_puff() -> None:
    [observation] = PuffDetector().detect(blank_frame(), holding_at(*MOUTH))
    assert observation.cue is Cue.PUFF
    assert observation.confidence > 0.9


def test_far_from_the_mouth_is_not_a_puff() -> None:
    assert PuffDetector().detect(blank_frame(), holding_at(0.9, 0.7)) == []


def test_open_hand_at_the_mouth_is_not_a_puff() -> None:
    x, y = MOUTH
    open_hand = hand(
        (x, y + 0.1), thumb_tip=(x - 0.1, y), index_tip=(x, y), middle_tip=(x + 0.1, y)
    )
    scene = Scene(hands=(open_hand,), face=face(MOUTH))
    assert PuffDetector().detect(blank_frame(), scene) == []


def test_a_hand_resting_at_the_mouth_counts_once() -> None:
    detector = PuffDetector()
    resting = holding_at(*MOUTH)
    assert detector.detect(blank_frame(), resting)
    assert detector.detect(blank_frame(), resting) == []
    assert detector.detect(blank_frame(), resting) == []


def test_each_new_puff_counts_again() -> None:
    detector = PuffDetector()
    away = holding_at(0.9, 0.7)
    for _ in range(3):
        assert detector.detect(blank_frame(), holding_at(*MOUTH))
        assert detector.detect(blank_frame(), away) == []


def test_needs_a_face() -> None:
    scene = Scene(hands=holding_at(*MOUTH).hands)
    assert PuffDetector().detect(blank_frame(), scene) == []
