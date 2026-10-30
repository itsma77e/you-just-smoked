from datetime import timedelta

import pytest

from you_just_smoked.domain.stats import Stats
from you_just_smoked.notify.messages import (
    LANGUAGES,
    format_duration,
    nudge_text,
    phrase,
    resolve_language,
    status_lines,
)

from factories import at

NOW = at(0)


def stats(
    minutes_ago: float | None = 47, today: int = 6, resisted: int = 0, held_off: float = 0
) -> Stats:
    last = NOW - timedelta(minutes=minutes_ago) if minutes_ago is not None else None
    return Stats(
        last_cigarette_at=last,
        today=today,
        this_session=2,
        resisted_today=resisted,
        held_off_today=timedelta(minutes=held_off),
    )


def test_nudge_mentions_time_since_last_count_and_next_goal() -> None:
    text = nudge_text(stats(), NOW, "en")
    assert text.title == "Your last one was 47 min ago"
    assert text.body == "6 today. Can you make it to 1 h?"
    assert (text.wait, text.smoking, text.false_alarm) == (
        "I'll wait",
        "Smoking anyway",
        "Not smoking",
    )


def test_nudge_in_italian() -> None:
    text = nudge_text(stats(), NOW, "it")
    assert text.title == "L'ultima è stata 47 min fa"
    assert text.body == "Oggi sono 6. Arrivi a 1 h?"


def test_nudge_when_nothing_is_logged_yet() -> None:
    text = nudge_text(stats(minutes_ago=None, today=0), NOW, "en")
    assert text.title == "About to smoke?"


def test_status_shows_wins_only_when_there_are_any() -> None:
    assert status_lines(stats(), NOW, "en") == ["Last: 47 min ago", "Today: 6"]
    lines = status_lines(stats(resisted=2, held_off=25), NOW, "en")
    assert lines[2:] == ["Resisted: 2", "Held off: 25 min"]


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_language_has_every_phrase(language: str) -> None:
    for key in ("menu_log", "menu_pause", "menu_resume", "menu_quit", "status_paused"):
        assert phrase(key, language)


def test_explicit_language_wins_over_the_system_locale() -> None:
    assert resolve_language("it") == "it"
    assert resolve_language("auto") in LANGUAGES


@pytest.mark.parametrize(
    ("duration", "text"),
    [
        (timedelta(seconds=59), "0 min"),
        (timedelta(minutes=45), "45 min"),
        (timedelta(hours=1), "1 h"),
        (timedelta(hours=1, minutes=20), "1 h 20 min"),
        (timedelta(days=2), "2 d"),
        (timedelta(days=2, hours=3, minutes=10), "2 d 3 h"),
    ],
)
def test_format_duration(duration: timedelta, text: str) -> None:
    assert format_duration(duration) == text
