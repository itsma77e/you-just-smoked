"""Small wins worth celebrating. Each badge is unlocked once, at the moment it was earned.

Everything is derived from the episode log, so nothing extra is stored and the
rules can change without a migration.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from itertools import pairwise

from you_just_smoked.domain.episode import Answer, Episode, Outcome
from you_just_smoked.domain.history import local_day


class Badge(StrEnum):
    FIRST_WAIT = "first_wait"
    FIRST_RESISTED = "first_resisted"
    HOUR_GAP = "hour_gap"
    TWO_HOUR_GAP = "two_hour_gap"
    GAINED_HALF_HOUR = "gained_half_hour"
    THREE_RESISTED = "three_resisted"
    FEWER_THAN_YESTERDAY = "fewer_than_yesterday"


@dataclass(frozen=True, slots=True)
class Achievement:
    badge: Badge
    unlocked_at: datetime


def achievements(episodes: Sequence[Episode], now: datetime) -> list[Achievement]:
    """Every badge earned so far, oldest first. `now` is timezone-aware local time."""
    ordered = sorted(episodes, key=lambda e: e.ended_at)
    found: dict[Badge, datetime] = {}

    def unlock(badge: Badge, at: datetime | None) -> None:
        if at is not None and at <= now:
            found[badge] = at

    unlock(Badge.FIRST_WAIT, _first(ordered, lambda e: e.answer is Answer.WAIT))
    unlock(Badge.FIRST_RESISTED, _first(ordered, lambda e: e.outcome is Outcome.RESISTED))
    for badge, length in ((Badge.HOUR_GAP, 1), (Badge.TWO_HOUR_GAP, 2)):
        unlock(badge, _gap_reached(ordered, now, timedelta(hours=length)))
    unlock(Badge.GAINED_HALF_HOUR, _daily_total_reached(ordered, now))
    unlock(Badge.THREE_RESISTED, _nth_resisted_in_a_day(ordered, now, 3))
    unlock(Badge.FEWER_THAN_YESTERDAY, _fewer_than_day_before(ordered, now))
    return [Achievement(badge, at) for badge, at in sorted(found.items(), key=lambda kv: kv[1])]


def _first(ordered: Sequence[Episode], matches: Callable[[Episode], bool]) -> datetime | None:
    return next((e.ended_at for e in ordered if matches(e)), None)


def _gap_reached(ordered: Sequence[Episode], now: datetime, length: timedelta) -> datetime | None:
    """When a gap between two cigarettes of the same day first reached `length`.

    The gap running right now counts too, so the badge pops while you are waiting.
    """
    smoked = [e.ended_at for e in ordered if e.counts_as_cigarette]
    for before, after in pairwise([*smoked, now]):
        same_day = local_day(before, now.tzinfo) == local_day(after, now.tzinfo)
        if same_day and after - before >= length:
            return before + length
    return None


def _daily_total_reached(ordered: Sequence[Episode], now: datetime) -> datetime | None:
    totals: dict[date, timedelta] = {}
    for episode in ordered:
        if episode.postponed_for is None:
            continue
        day = local_day(episode.ended_at, now.tzinfo)
        totals[day] = totals.get(day, timedelta(0)) + episode.postponed_for
        if totals[day] >= timedelta(minutes=30):
            return episode.ended_at
    return None


def _nth_resisted_in_a_day(ordered: Sequence[Episode], now: datetime, n: int) -> datetime | None:
    counts: dict[date, int] = {}
    for episode in ordered:
        if episode.outcome is not Outcome.RESISTED:
            continue
        day = local_day(episode.ended_at, now.tzinfo)
        counts[day] = counts.get(day, 0) + 1
        if counts[day] == n:
            return episode.ended_at
    return None


def _fewer_than_day_before(ordered: Sequence[Episode], now: datetime) -> datetime | None:
    per_day: dict[date, int] = {}
    for episode in ordered:
        if episode.counts_as_cigarette:
            day = local_day(episode.ended_at, now.tzinfo)
            per_day[day] = per_day.get(day, 0) + 1
    for day in sorted(per_day):
        previous = per_day.get(day - timedelta(days=1), 0)
        if day < now.date() and 0 < per_day[day] < previous:
            return datetime.combine(day + timedelta(days=1), time(), tzinfo=now.tzinfo)
    return None
