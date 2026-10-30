from datetime import timedelta

from you_just_smoked.domain.stats import Stats
from you_just_smoked.notify.messages import nudge_text, status_lines

from factories import at

NOW = at(0)
FIVE = timedelta(minutes=5)


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
    text = nudge_text(stats(), NOW, "en", minimum_wait=FIVE)
    assert text.title == "Your last one was 47 min ago"
    assert text.body == "6 today. Can you make it to 1 h?"
    assert text.wait_for == timedelta(minutes=13)
    assert (text.wait, text.smoking, text.false_alarm) == (
        "I'll wait",
        "Smoking anyway",
        "Not smoking",
    )


def test_nudge_in_italian() -> None:
    text = nudge_text(stats(), NOW, "it", minimum_wait=FIVE)
    assert text.title == "L'ultima è stata 47 min fa"
    assert text.body == "Oggi sono 6. Arrivi a 1 h?"


def test_nudge_when_nothing_is_logged_yet() -> None:
    text = nudge_text(stats(minutes_ago=None, today=0), NOW, "en", minimum_wait=FIVE)
    assert text.title == "About to smoke?"
    assert text.wait_for == timedelta(minutes=15)


def test_goal_and_countdown_agree_when_the_next_goal_is_too_close() -> None:
    text = nudge_text(stats(minutes_ago=57), NOW, "en", minimum_wait=FIVE)
    assert text.body == "6 today. Can you make it to 1 h 30 min?"
    assert text.wait_for == timedelta(minutes=33)


def test_status_shows_wins_only_when_there_are_any() -> None:
    assert status_lines(stats(), NOW, "en") == ["Last: 47 min ago", "Today: 6"]
    lines = status_lines(stats(resisted=2, held_off=25), NOW, "en")
    assert lines[2:] == ["Skipped: 2", "Time gained: 25 min"]
