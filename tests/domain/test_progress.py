from datetime import timedelta

from you_just_smoked.domain.achievements import Badge
from you_just_smoked.domain.cues import Cue
from you_just_smoked.domain.episode import Episode, Outcome
from you_just_smoked.domain.pace import Pace, pace, yesterday_by_now
from you_just_smoked.domain.progress import BadgeProgress, Unit, next_badges

from factories import at

DAY = 24 * 60


def smoked(minutes: float, postponed: float | None = None) -> Episode:
    moment = at(minutes=minutes)
    delay = timedelta(minutes=postponed) if postponed is not None else None
    return Episode(moment, moment, Outcome.SMOKED, Cue.FLAME, postponed_for=delay)


def resisted(minutes: float) -> Episode:
    moment = at(minutes=minutes)
    return Episode(moment, moment, Outcome.RESISTED, Cue.FLAME)


def test_the_closest_badge_comes_first() -> None:
    history = [smoked(-54), resisted(-100), resisted(-80)]
    [closest, *_] = next_badges(history, set(), at(0))
    assert closest == BadgeProgress(Badge.HOUR_GAP, 6, Unit.MINUTES, 0.9)


def test_counts_and_minutes_are_reported() -> None:
    progress = {p.badge: p for p in next_badges([smoked(-30, postponed=12)], set(), at(0))}
    assert progress[Badge.TWO_HOUR_GAP].remaining == 90
    assert progress[Badge.GAINED_HALF_HOUR].remaining == 18
    assert progress[Badge.THREE_RESISTED].remaining == 3
    assert progress[Badge.FIRST_RESISTED].unit is Unit.TIMES


def test_unlocked_and_already_reached_badges_are_left_out() -> None:
    progress = next_badges([smoked(-70)], {Badge.FIRST_RESISTED}, at(0))
    badges = {p.badge for p in progress}
    assert Badge.HOUR_GAP not in badges
    assert Badge.FIRST_RESISTED not in badges
    assert Badge.TWO_HOUR_GAP in badges


def test_gap_badges_need_a_cigarette_today() -> None:
    badges = {p.badge for p in next_badges([smoked(-DAY)], set(), at(0))}
    assert Badge.HOUR_GAP not in badges


def test_pace_compares_now_with_waiting() -> None:
    eight_hours = timedelta(hours=8)
    assert pace(timedelta(minutes=16), timedelta(minutes=30), eight_hours) == Pace(30, 16)
    assert pace(timedelta(seconds=20), timedelta(minutes=15), eight_hours) is None


def test_yesterday_by_now_counts_only_up_to_the_same_time() -> None:
    history = [smoked(-DAY - 60), smoked(-DAY - 10), smoked(-DAY + 30), smoked(-5)]
    assert yesterday_by_now(history, at(0)) == 2
