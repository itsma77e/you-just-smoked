"""What the widget shows, as plain strings and numbers. Pure, so it is tested without Tk."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

from you_just_smoked.domain.achievements import Badge
from you_just_smoked.domain.pace import pace
from you_just_smoked.domain.progress import BadgeProgress, Unit
from you_just_smoked.domain.stats import milestone_progress
from you_just_smoked.domain.tracker import Phase
from you_just_smoked.i18n import TIP_COUNT, format_duration, text

if TYPE_CHECKING:
    from datetime import datetime

    from you_just_smoked.domain.summary import Summary
    from you_just_smoked.runtime.status import Status


class Indicator(StrEnum):
    WATCHING = "watching"
    PAUSED = "paused"
    CAMERA = "camera"
    ACTIVE = "active"
    POSTPONED = "postponed"


@dataclass(frozen=True, slots=True)
class WidgetView:
    timer: str
    caption: str
    goal: str
    progress: float
    today: str
    indicator: Indicator
    indicator_label: str


@dataclass(frozen=True, slots=True)
class BarView:
    label: str
    value: int
    is_today: bool


_GLYPHS = {
    Badge.FIRST_WAIT: "1",
    Badge.FIRST_RESISTED: "✓",
    Badge.HOUR_GAP: "1h",
    Badge.TWO_HOUR_GAP: "2h",
    Badge.GAINED_HALF_HOUR: "30'",
    Badge.THREE_RESISTED: "3x",
    Badge.FEWER_THAN_YESTERDAY: "↓",
}


@dataclass(frozen=True, slots=True)
class BadgeView:
    badge: Badge
    name: str
    unlocked: bool

    @property
    def glyph(self) -> str:
        """A short, language-neutral mark drawn inside the badge."""
        return _GLYPHS[self.badge]


def widget_view(status: Status, now: datetime, language: str) -> WidgetView:
    stats = status.summary.stats
    elapsed = stats.since_last(now)
    if elapsed is None:
        timer, caption, goal, progress = "--:--", text("no_last", language), "", 0.0
    else:
        target, progress = milestone_progress(elapsed)
        timer = format_timer(elapsed)
        caption = text("since_last", language)
        goal = text("goal", language, goal=format_duration(target))
    today = text(
        "today_line",
        language,
        today=stats.today,
        resisted=stats.resisted_today,
        gained=format_duration(stats.held_off_today),
    )
    indicator = _indicator(status)
    label = text(f"state_{indicator.value}", language)
    return WidgetView(timer, caption, goal, progress, today, indicator, label)


def format_timer(elapsed: timedelta) -> str:
    """A ticking clock: "4:07", "47:12", "1:05:12"; days fall back to "2 d 3 h"."""
    if elapsed >= timedelta(days=1):
        return format_duration(elapsed)
    seconds = int(elapsed.total_seconds())
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"


def companion_lines(
    summary: Summary,
    now: datetime,
    language: str,
    goal: timedelta | None,
    computer_day: timedelta,
) -> list[str]:
    """What the countdown cycles through: streak, the next badge, today, the pace, tips."""
    lines = [_streak_line(summary, language)]
    if summary.next_badges:
        lines.append(_badge_line(summary.next_badges[0], language))
    stats = summary.stats
    lines.append(
        text("companion_today", language, today=stats.today, yesterday=summary.yesterday_by_now)
    )
    elapsed = stats.since_last(now)
    if elapsed is not None and goal is not None:
        rhythm = pace(elapsed, goal, computer_day)
        if rhythm is not None:
            hours = round(computer_day / timedelta(hours=1))
            lines.append(
                text(
                    "companion_pace",
                    language,
                    now=rhythm.if_now,
                    hours=hours,
                    goal=format_duration(goal),
                    later=rhythm.if_waiting,
                )
            )
    return lines + [text(f"tip_{index}", language) for index in range(TIP_COUNT)]


def celebration_line(summary: Summary, language: str) -> str:
    """The streak this success leads to, and a jolly if it earns one."""
    before = summary.streak
    after = before.after(succeeded=True)
    line = text("celebrate_streak", language, count=after.current)
    if after.jollies > before.jollies:
        line += " · " + text("celebrate_jolly", language)
    return line


def _streak_line(summary: Summary, language: str) -> str:
    streak = summary.streak
    if not streak.current and not streak.jollies:
        return text("companion_streak_start", language)
    line = text("companion_streak", language, count=streak.current, jollies=streak.jollies)
    return line + "\n" + text("companion_jolly", language, count=streak.to_next_jolly)


def _badge_line(progress: BadgeProgress, language: str) -> str:
    name = text(f"badge_{progress.badge.value}", language)
    key = "companion_badge_minutes" if progress.unit is Unit.MINUTES else "companion_badge_times"
    return text(key, language, name=name, count=progress.remaining)


def week_view(summary: Summary, language: str) -> list[BarView]:
    last = len(summary.week) - 1
    return [
        BarView(text(f"day_{day.day.weekday()}", language), day.smoked, index == last)
        for index, day in enumerate(summary.week)
    ]


def badge_views(summary: Summary, language: str) -> list[BadgeView]:
    unlocked = {achievement.badge for achievement in summary.achievements}
    return [BadgeView(b, text(f"badge_{b.value}", language), b in unlocked) for b in Badge]


def new_badges(before: Summary | None, after: Summary) -> list[Badge]:
    """Badges that appeared between two summaries. Nothing on the very first one."""
    if before is None:
        return []
    known = {achievement.badge for achievement in before.achievements}
    return [a.badge for a in after.achievements if a.badge not in known]


def _indicator(status: Status) -> Indicator:
    if status.paused:
        return Indicator.PAUSED
    if status.camera_error:
        return Indicator.CAMERA
    if status.phase is Phase.ACTIVE:
        return Indicator.ACTIVE
    if status.phase is Phase.POSTPONED:
        return Indicator.POSTPONED
    return Indicator.WATCHING
