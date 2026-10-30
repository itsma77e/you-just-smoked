from datetime import timedelta

import pytest

from you_just_smoked.domain.achievements import Badge
from you_just_smoked.domain.cues import Cue
from you_just_smoked.domain.episode import Answer, Episode, Outcome
from you_just_smoked.domain.summary import summarize
from you_just_smoked.domain.tracker import Phase
from you_just_smoked.runtime.status import Status
from you_just_smoked.ui.viewmodel import (
    Indicator,
    badge_views,
    format_timer,
    new_badges,
    week_view,
    widget_view,
)

from factories import at

NOW = at(0)


def smoked(minutes: float, answer: Answer | None = None) -> Episode:
    moment = at(minutes=minutes)
    return Episode(moment, moment, Outcome.SMOKED, Cue.FLAME, answer=answer)


def status(*episodes: Episode, phase: Phase = Phase.IDLE, **extra: object) -> Status:
    summary = summarize(list(episodes), now=NOW, session_start=at(minutes=-600))
    return Status(at=NOW, phase=phase, summary=summary, **extra)  # type: ignore[arg-type]


def test_shows_time_since_last_and_progress_to_the_next_goal() -> None:
    view = widget_view(status(smoked(-54)), NOW, "en")
    assert view.timer == "54:00"
    assert view.caption == "since your last one"
    assert view.goal == "goal 1 h"
    assert view.progress == pytest.approx(0.9)
    assert view.today == "today 1 · skipped 0 · +0 min"
    assert view.indicator is Indicator.WATCHING


def test_nothing_logged_yet() -> None:
    view = widget_view(status(), NOW, "it")
    assert view.timer == "--:--"
    assert view.caption == "ancora nessuna registrata"


@pytest.mark.parametrize(
    ("phase", "extra", "indicator"),
    [
        (Phase.ACTIVE, {}, Indicator.ACTIVE),
        (Phase.POSTPONED, {}, Indicator.POSTPONED),
        (Phase.IDLE, {"camera_error": "unplugged"}, Indicator.CAMERA),
        (Phase.ACTIVE, {"paused_until": at(minutes=30)}, Indicator.PAUSED),
    ],
)
def test_indicator(phase: Phase, extra: dict[str, object], indicator: Indicator) -> None:
    assert widget_view(status(phase=phase, **extra), NOW, "en").indicator is indicator


@pytest.mark.parametrize(
    ("elapsed", "shown"),
    [
        (timedelta(seconds=7), "0:07"),
        (timedelta(minutes=47, seconds=12), "47:12"),
        (timedelta(hours=1, minutes=5, seconds=12), "1:05:12"),
        (timedelta(days=2, hours=3), "2 d 3 h"),
    ],
)
def test_format_timer(elapsed: timedelta, shown: str) -> None:
    assert format_timer(elapsed) == shown


def test_week_ends_today_with_weekday_labels() -> None:
    bars = week_view(status(smoked(-10), smoked(-20)).summary, "it")
    assert [bar.label for bar in bars] == ["Sa", "Do", "Lu", "Ma", "Me", "Gi", "Ve"]
    assert bars[-1].value == 2
    assert bars[-1].is_today


def test_badges_list_every_badge_and_mark_unlocked_ones() -> None:
    views = badge_views(status(smoked(-30, Answer.WAIT)).summary, "en")
    assert len(views) == len(Badge)
    assert all(view.glyph for view in views)
    assert [v.badge for v in views if v.unlocked] == [Badge.FIRST_WAIT]


def test_new_badges_only_reports_fresh_unlocks() -> None:
    before = status(smoked(-30)).summary
    after = status(smoked(-30), smoked(-5, Answer.WAIT)).summary
    assert new_badges(None, after) == []
    assert new_badges(before, after) == [Badge.FIRST_WAIT]
