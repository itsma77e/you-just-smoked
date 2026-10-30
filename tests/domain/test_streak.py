from datetime import timedelta

from you_just_smoked.domain.cues import Cue
from you_just_smoked.domain.episode import Answer, Episode, Outcome
from you_just_smoked.domain.streak import Streak, streak

from factories import at

TARGET = timedelta(minutes=14)


def wait(minutes: float, *, held_for: float | None) -> Episode:
    """A wait accepted at `minutes`; `held_for` None means it ended resisted."""
    moment = at(minutes=minutes)
    if held_for is None:
        return Episode(moment, moment, Outcome.RESISTED, Cue.FLAME, Answer.WAIT, None, TARGET)
    held = timedelta(minutes=held_for)
    return Episode(moment, moment, Outcome.SMOKED, Cue.FLAME, Answer.WAIT, held, TARGET)


def kept(minutes: float) -> Episode:
    return wait(minutes, held_for=20)


def broken(minutes: float) -> Episode:
    return wait(minutes, held_for=3)


def test_a_wait_succeeds_when_resisted_or_held_to_the_target() -> None:
    assert wait(0, held_for=None).wait_succeeded is True
    assert kept(0).wait_succeeded is True
    assert broken(0).wait_succeeded is False
    plain = Episode(at(0), at(0), Outcome.SMOKED, Cue.FLAME, Answer.SMOKING)
    assert plain.wait_succeeded is None


def test_successes_build_the_streak_and_every_third_earns_a_jolly() -> None:
    result = streak([kept(m) for m in range(0, 70, 10)])
    assert result == Streak(current=7, best=7, jollies=2, successes=7)
    assert result.to_next_jolly == 2


def test_a_jolly_absorbs_a_slip() -> None:
    result = streak([kept(0), kept(10), kept(20), broken(30), kept(40)])
    assert result.current == 4
    assert result.jollies == 0


def test_a_slip_without_jolly_restarts_the_streak_but_keeps_the_best() -> None:
    result = streak([kept(0), kept(10), broken(20), kept(30)])
    assert result.current == 1
    assert result.best == 2


def test_jollies_have_no_limit() -> None:
    assert streak([kept(m) for m in range(0, 120, 10)]).jollies == 4


def test_episodes_without_a_wait_do_not_count() -> None:
    plain = Episode(at(0), at(0), Outcome.SMOKED, Cue.FLAME)
    assert streak([plain, kept(10)]).current == 1
