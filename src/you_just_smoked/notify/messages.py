"""The nudge and status text, built from the numbers. Words live in `you_just_smoked.i18n`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from you_just_smoked.domain.stats import wait_goal
from you_just_smoked.i18n import format_duration, text

if TYPE_CHECKING:
    from datetime import datetime

    from you_just_smoked.domain.stats import Stats


@dataclass(frozen=True, slots=True)
class NudgeText:
    title: str
    body: str
    wait: str
    smoking: str
    false_alarm: str
    wait_for: timedelta
    """How long "I'll wait" counts down: exactly until the goal named in `body`."""


def nudge_text(stats: Stats, now: datetime, language: str, *, minimum_wait: timedelta) -> NudgeText:
    elapsed = stats.since_last(now) or timedelta(0)
    goal = wait_goal(elapsed, minimum_wait)
    if stats.last_cigarette_at is None:
        title, body = text("title_first", language), text("body_first", language)
    else:
        title = text("title_last", language, ago=format_duration(elapsed))
        body = text("body_counts", language, today=stats.today, goal=format_duration(goal))
    return NudgeText(
        title,
        body,
        text("wait", language),
        text("smoking", language),
        text("false_alarm", language),
        wait_for=goal - elapsed,
    )


def status_lines(stats: Stats, now: datetime, language: str) -> list[str]:
    elapsed = stats.since_last(now)
    lines = [
        text("status_last", language, ago=format_duration(elapsed))
        if elapsed is not None
        else text("status_none", language),
        text("status_today", language, today=stats.today),
    ]
    if stats.resisted_today:
        lines.append(text("status_resisted", language, resisted=stats.resisted_today))
    if stats.held_off_today:
        held_off = format_duration(stats.held_off_today)
        lines.append(text("status_held_off", language, held_off=held_off))
    return lines
