"""Perspective while waiting: today against yesterday, and what the current rhythm adds up to."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from you_just_smoked.domain.history import local_day

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime

    from you_just_smoked.domain.episode import Episode

_SHORTEST_GAP = timedelta(minutes=1)


@dataclass(frozen=True, slots=True)
class Pace:
    if_now: int
    """Cigarettes in a computer day if every gap were as long as the current one."""

    if_waiting: int
    """The same, if every gap lasted until the goal of this wait."""


def pace(elapsed: timedelta, goal: timedelta, computer_day: timedelta) -> Pace | None:
    """The day's total at the current rhythm versus waiting until `goal`; None if too early."""
    if elapsed < _SHORTEST_GAP:
        return None
    return Pace(round(computer_day / elapsed), round(computer_day / goal))


def yesterday_by_now(history: Iterable[Episode], now: datetime) -> int:
    """Cigarettes smoked yesterday up to the same time of day as now."""
    yesterday = now.date() - timedelta(days=1)
    clock = now.timetz()
    return sum(
        1
        for e in history
        if e.counts_as_cigarette
        and local_day(e.ended_at, now.tzinfo) == yesterday
        and e.ended_at.astimezone(now.tzinfo).timetz() <= clock
    )
