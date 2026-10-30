"""How close the next badges are, so the wait has something concrete to aim for."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

from you_just_smoked.domain.achievements import Badge
from you_just_smoked.domain.episode import Outcome
from you_just_smoked.domain.history import local_day

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from datetime import datetime

    from you_just_smoked.domain.episode import Episode


class Unit(StrEnum):
    MINUTES = "minutes"
    TIMES = "times"


@dataclass(frozen=True, slots=True)
class BadgeProgress:
    badge: Badge
    remaining: int
    unit: Unit
    done: float
    """Fraction already achieved, in [0, 1): what makes one badge closer than another."""


def next_badges(
    history: Sequence[Episode], unlocked: Collection[Badge], now: datetime
) -> list[BadgeProgress]:
    """Locked badges that can be earned today, closest first."""
    today = [e for e in history if local_day(e.ended_at, now.tzinfo) == now.date()]
    candidates = [
        *_gap_progress(today, now),
        _count_progress(Badge.THREE_RESISTED, _resisted(today), 3),
        _count_progress(Badge.FIRST_RESISTED, _resisted(history), 1),
        _gained_progress(today),
    ]
    found = [p for p in candidates if p is not None and p.badge not in unlocked]
    return sorted(found, key=lambda p: p.done, reverse=True)


def _gap_progress(today: Sequence[Episode], now: datetime) -> list[BadgeProgress | None]:
    smoked = [e.ended_at for e in today if e.counts_as_cigarette]
    if not smoked:
        return []
    gap = now - max(smoked)
    return [
        _minutes_progress(Badge.HOUR_GAP, gap, timedelta(hours=1)),
        _minutes_progress(Badge.TWO_HOUR_GAP, gap, timedelta(hours=2)),
    ]


def _gained_progress(today: Sequence[Episode]) -> BadgeProgress | None:
    gained = sum((e.postponed_for or timedelta(0) for e in today), timedelta(0))
    return _minutes_progress(Badge.GAINED_HALF_HOUR, gained, timedelta(minutes=30))


def _minutes_progress(badge: Badge, have: timedelta, need: timedelta) -> BadgeProgress | None:
    if have >= need:
        return None
    remaining = -((have - need) // timedelta(minutes=1))
    return BadgeProgress(badge, remaining, Unit.MINUTES, have / need)


def _count_progress(badge: Badge, have: int, need: int) -> BadgeProgress | None:
    if have >= need:
        return None
    return BadgeProgress(badge, need - have, Unit.TIMES, have / need)


def _resisted(episodes: Sequence[Episode]) -> int:
    return sum(1 for e in episodes if e.outcome is Outcome.RESISTED)
