from datetime import timedelta, timezone

import pytest

from you_just_smoked.domain.cues import Cue
from you_just_smoked.domain.episode import Episode, Outcome
from you_just_smoked.domain.stats import (
    compute_stats,
    milestone_progress,
    next_milestone,
    wait_goal,
)

from factories import at


def episode(
    minutes: float,
    outcome: Outcome = Outcome.SMOKED,
    postponed_for: timedelta | None = None,
) -> Episode:
    moment = at(minutes=minutes)
    return Episode(moment, moment, outcome, Cue.FLAME, postponed_for=postponed_for)


def test_counts_today_session_and_last() -> None:
    episodes = [
        episode(-60 * 24),
        episode(-120),
        episode(-30, postponed_for=timedelta(minutes=12)),
        episode(-10, Outcome.RESISTED),
        episode(-5, Outcome.FALSE_ALARM),
    ]
    stats = compute_stats(episodes, now=at(0), session_start=at(minutes=-60))
    assert stats.today == 2
    assert stats.this_session == 1
    assert stats.resisted_today == 1
    assert stats.held_off_today == timedelta(minutes=12)
    assert stats.last_cigarette_at == at(minutes=-30)
    assert stats.since_last(at(0)) == timedelta(minutes=30)


def test_today_follows_the_local_calendar_day() -> None:
    rome = timezone(timedelta(hours=1))
    half_past_midnight_in_rome = episode(-9 * 60 - 30)
    assert compute_stats([half_past_midnight_in_rome], now=at(0), session_start=at(0)).today == 0
    now = at(0).astimezone(rome)
    assert compute_stats([half_past_midnight_in_rome], now=now, session_start=now).today == 1


def test_nothing_logged_yet() -> None:
    stats = compute_stats([], now=at(0), session_start=at(0))
    assert stats.last_cigarette_at is None
    assert stats.since_last(at(0)) is None


@pytest.mark.parametrize(
    ("elapsed", "goal"),
    [
        (timedelta(minutes=0), timedelta(minutes=15)),
        (timedelta(minutes=47), timedelta(hours=1)),
        (timedelta(hours=1), timedelta(minutes=90)),
        (timedelta(hours=30), timedelta(hours=48)),
    ],
)
def test_next_milestone(elapsed: timedelta, goal: timedelta) -> None:
    assert next_milestone(elapsed) == goal


@pytest.mark.parametrize(
    ("elapsed", "goal", "fraction"),
    [
        (timedelta(minutes=0), timedelta(minutes=15), 0.0),
        (timedelta(minutes=45), timedelta(hours=1), 0.75),
        (timedelta(minutes=54), timedelta(hours=1), 0.9),
        (timedelta(hours=36), timedelta(hours=48), 0.75),
    ],
)
def test_milestone_progress(elapsed: timedelta, goal: timedelta, fraction: float) -> None:
    actual_goal, actual_fraction = milestone_progress(elapsed)
    assert actual_goal == goal
    assert actual_fraction == pytest.approx(fraction)


@pytest.mark.parametrize(
    ("elapsed", "goal"),
    [
        (timedelta(0), timedelta(minutes=15)),
        (timedelta(minutes=16), timedelta(minutes=30)),
        (timedelta(minutes=27), timedelta(minutes=45)),
        (timedelta(minutes=55), timedelta(hours=1)),
        (timedelta(minutes=57), timedelta(minutes=90)),
        (timedelta(hours=23, minutes=58), timedelta(hours=48)),
    ],
)
def test_wait_goal_is_at_least_the_minimum_away(elapsed: timedelta, goal: timedelta) -> None:
    assert wait_goal(elapsed, timedelta(minutes=5)) == goal
