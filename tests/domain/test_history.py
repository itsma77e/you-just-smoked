from datetime import date, timedelta

from you_just_smoked.domain.cues import Cue
from you_just_smoked.domain.episode import Episode, Outcome
from you_just_smoked.domain.history import Day, best_gap_today, week

from factories import at


def smoked(minutes: float) -> Episode:
    return Episode(at(minutes=minutes), at(minutes=minutes), Outcome.SMOKED, Cue.FLAME)


def resisted(minutes: float) -> Episode:
    return Episode(at(minutes=minutes), at(minutes=minutes), Outcome.RESISTED, Cue.FLAME)


DAY = 24 * 60


def test_week_counts_each_of_the_last_seven_days() -> None:
    episodes = [
        smoked(-8 * DAY),
        smoked(-6 * DAY),
        smoked(-DAY),
        smoked(-DAY),
        resisted(-5),
        smoked(-1),
    ]
    days = week(episodes, at(0))
    assert len(days) == 7
    assert days[0] == Day(date(2026, 10, 24), 1, 0)
    assert days[-2] == Day(date(2026, 10, 29), 2, 0)
    assert days[-1] == Day(date(2026, 10, 30), 1, 1)


def test_best_gap_includes_the_one_running_now() -> None:
    episodes = [smoked(-200), smoked(-170), smoked(-60)]
    assert best_gap_today(episodes, at(0)) == timedelta(minutes=110)
    assert best_gap_today(episodes, at(minutes=60)) == timedelta(minutes=120)


def test_no_best_gap_before_the_first_cigarette_of_the_day() -> None:
    assert best_gap_today([smoked(-DAY)], at(0)) is None
