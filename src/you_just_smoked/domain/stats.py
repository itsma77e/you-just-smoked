"""Numbers shown in the nudge and the tray: honest, local, and computed from the log."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from you_just_smoked.domain.episode import Episode, Outcome

_MILESTONES = tuple(
    timedelta(minutes=m) for m in (15, 30, 45, 60, 90, 120, 180, 240, 360, 480, 720, 1440)
)


@dataclass(frozen=True, slots=True)
class Stats:
    last_cigarette_at: datetime | None
    today: int
    this_session: int
    resisted_today: int
    held_off_today: timedelta
    """Total time gained today by choosing to wait before smoking."""

    def since_last(self, now: datetime) -> timedelta | None:
        if self.last_cigarette_at is None:
            return None
        return max(now - self.last_cigarette_at, timedelta(0))


def compute_stats(episodes: Iterable[Episode], *, now: datetime, session_start: datetime) -> Stats:
    """Summarise the history. `now` must be timezone-aware; "today" is its calendar day."""
    today = now.date()
    last: datetime | None = None
    smoked_today = smoked_in_session = resisted_today = 0
    held_off = timedelta(0)

    for episode in episodes:
        is_today = episode.ended_at.astimezone(now.tzinfo).date() == today
        if episode.outcome is Outcome.RESISTED and is_today:
            resisted_today += 1
        if not episode.counts_as_cigarette:
            continue
        if last is None or episode.ended_at > last:
            last = episode.ended_at
        if episode.ended_at >= session_start:
            smoked_in_session += 1
        if is_today:
            smoked_today += 1
            held_off += episode.postponed_for or timedelta(0)

    return Stats(last, smoked_today, smoked_in_session, resisted_today, held_off)


def next_milestone(elapsed: timedelta) -> timedelta:
    """The next round goal worth waiting for, e.g. 47 minutes -> 1 hour."""
    for milestone in _MILESTONES:
        if milestone > elapsed:
            return milestone
    return _MILESTONES[-1] * (elapsed // _MILESTONES[-1] + 1)


def wait_goal(elapsed: timedelta, minimum: timedelta) -> timedelta:
    """The first round goal at least `minimum` away: 16 min with a 5 min minimum -> 30 min.

    The nudge offers this goal and the wait challenge counts down to it, so the two
    always agree.
    """
    for milestone in _MILESTONES:
        if milestone - elapsed >= minimum:
            return milestone
    step = _MILESTONES[-1]
    goal = step * (elapsed // step + 1)
    while goal - elapsed < minimum:
        goal += step
    return goal


def milestone_progress(elapsed: timedelta) -> tuple[timedelta, float]:
    """The next goal and how much of it is done, in [0, 1): 45 min of 1 h is 0.75."""
    goal = next_milestone(elapsed)
    return goal, elapsed / goal
