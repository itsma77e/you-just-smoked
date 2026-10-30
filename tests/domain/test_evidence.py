from datetime import timedelta

import pytest

from you_just_smoked.domain.cues import Cue, CueObservation
from you_just_smoked.domain.evidence import Evidence, EvidenceSettings

from factories import at, seen

SETTINGS = EvidenceSettings(
    weights={Cue.LIGHTER: 0.5, Cue.FLAME: 1.0}, half_life=timedelta(seconds=10)
)


def test_starts_empty() -> None:
    evidence = Evidence(SETTINGS)
    assert evidence.value(at(0)) == 0.0
    assert evidence.since is None
    assert evidence.strongest_cue() is None


def test_adds_weight_times_confidence() -> None:
    evidence = Evidence(SETTINGS)
    evidence.add(seen(Cue.LIGHTER, 0, confidence=0.8))
    assert evidence.value(at(0)) == pytest.approx(0.4)


def test_halves_every_half_life() -> None:
    evidence = Evidence(SETTINGS)
    evidence.add(seen(Cue.FLAME, 0))
    assert evidence.value(at(10)) == pytest.approx(0.5)
    assert evidence.value(at(20)) == pytest.approx(0.25)


def test_cues_close_together_add_up() -> None:
    evidence = Evidence(SETTINGS)
    evidence.add(seen(Cue.LIGHTER, 0))
    evidence.add(seen(Cue.FLAME, 2))
    assert evidence.value(at(2)) > 1.3


def test_new_run_restarts_since_after_fading() -> None:
    evidence = Evidence(SETTINGS)
    evidence.add(seen(Cue.LIGHTER, 0))
    evidence.add(seen(Cue.LIGHTER, 5))
    assert evidence.since == at(0)
    evidence.add(seen(Cue.LIGHTER, 300))
    assert evidence.since == at(300)


def test_strongest_cue_is_the_biggest_contributor() -> None:
    evidence = Evidence(SETTINGS)
    evidence.add(seen(Cue.LIGHTER, 0))
    evidence.add(seen(Cue.FLAME, 1, confidence=0.6))
    evidence.add(seen(Cue.LIGHTER, 6))
    assert evidence.strongest_cue() is Cue.LIGHTER


def test_the_same_cue_counts_once_per_spacing() -> None:
    evidence = Evidence(SETTINGS)
    for tenth in range(10):
        evidence.add(seen(Cue.LIGHTER, tenth / 10))
    assert evidence.value(at(1)) == pytest.approx(0.5 * 0.5 ** (1 / 10))


def test_ignores_cues_outside_the_accepted_set() -> None:
    evidence = Evidence(SETTINGS, cues=frozenset({Cue.FLAME}))
    evidence.add(seen(Cue.LIGHTER, 0))
    assert evidence.value(at(0)) == 0.0


def test_out_of_order_observation_does_not_rewind_time() -> None:
    evidence = Evidence(SETTINGS)
    evidence.add(seen(Cue.FLAME, 10))
    evidence.add(seen(Cue.LIGHTER, 4))
    assert evidence.value(at(20)) == pytest.approx(0.75)


def test_rejects_confidence_out_of_range() -> None:
    with pytest.raises(ValueError, match="confidence"):
        CueObservation(Cue.FLAME, 1.5, at(0))
