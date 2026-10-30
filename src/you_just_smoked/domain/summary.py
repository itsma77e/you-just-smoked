"""Everything the interface shows, derived from the episode history in one place."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from you_just_smoked.domain.achievements import Achievement, achievements
from you_just_smoked.domain.history import Day, best_gap_today, week
from you_just_smoked.domain.pace import yesterday_by_now
from you_just_smoked.domain.progress import BadgeProgress, next_badges
from you_just_smoked.domain.stats import Stats, compute_stats
from you_just_smoked.domain.streak import Streak, streak

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime, timedelta

    from you_just_smoked.domain.episode import Episode


@dataclass(frozen=True, slots=True)
class Summary:
    stats: Stats
    week: tuple[Day, ...]
    achievements: tuple[Achievement, ...]
    best_gap_today: timedelta | None
    streak: Streak
    next_badges: tuple[BadgeProgress, ...]
    yesterday_by_now: int


def summarize(history: Sequence[Episode], *, now: datetime, session_start: datetime) -> Summary:
    """`now` must be timezone-aware local time; "today" and the week follow its calendar."""
    earned = tuple(achievements(history, now))
    return Summary(
        stats=compute_stats(history, now=now, session_start=session_start),
        week=tuple(week(history, now)),
        achievements=earned,
        best_gap_today=best_gap_today(history, now),
        streak=streak(history),
        next_badges=tuple(next_badges(history, {a.badge for a in earned}, now)),
        yesterday_by_now=yesterday_by_now(history, now),
    )
