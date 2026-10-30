"""Day-by-day view of the log, for the weekly chart and same-day gaps."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, tzinfo
from itertools import pairwise

from you_just_smoked.domain.episode import Episode, Outcome


@dataclass(frozen=True, slots=True)
class Day:
    day: date
    smoked: int
    resisted: int


def local_day(moment: datetime, zone: tzinfo | None) -> date:
    return moment.astimezone(zone).date()


def week(episodes: Iterable[Episode], now: datetime, days: int = 7) -> list[Day]:
    """The last `days` calendar days, oldest first, today last."""
    today = now.date()
    first = today - timedelta(days=days - 1)
    smoked: dict[date, int] = {}
    resisted: dict[date, int] = {}
    for episode in episodes:
        day = local_day(episode.ended_at, now.tzinfo)
        if day < first or day > today:
            continue
        if episode.outcome is Outcome.SMOKED:
            smoked[day] = smoked.get(day, 0) + 1
        elif episode.outcome is Outcome.RESISTED:
            resisted[day] = resisted.get(day, 0) + 1
    return [
        Day(day, smoked.get(day, 0), resisted.get(day, 0))
        for day in (first + timedelta(days=offset) for offset in range(days))
    ]


def best_gap_today(episodes: Iterable[Episode], now: datetime) -> timedelta | None:
    """Longest wait between two cigarettes today, counting the one running now.

    None until the first cigarette of the day: sleeping is not an achievement.
    """
    today = [
        e.ended_at
        for e in episodes
        if e.counts_as_cigarette and local_day(e.ended_at, now.tzinfo) == now.date()
    ]
    if not today:
        return None
    times = [*sorted(today), now]
    return max(after - before for before, after in pairwise(times))
