from datetime import timedelta

from you_just_smoked.domain.achievements import Badge, achievements
from you_just_smoked.domain.cues import Cue
from you_just_smoked.domain.episode import Answer, Episode, Outcome

from factories import at

DAY = 24 * 60


def episode(
    minutes: float,
    outcome: Outcome = Outcome.SMOKED,
    answer: Answer | None = None,
    postponed: float | None = None,
) -> Episode:
    moment = at(minutes=minutes)
    delay = timedelta(minutes=postponed) if postponed is not None else None
    return Episode(moment, moment, outcome, Cue.FLAME, answer=answer, postponed_for=delay)


def badges(episodes: list[Episode], now_minutes: float = 0) -> dict[Badge, object]:
    return {a.badge: a.unlocked_at for a in achievements(episodes, at(minutes=now_minutes))}


def test_nothing_yet() -> None:
    assert badges([]) == {}


def test_first_wait_and_first_resisted() -> None:
    found = badges([episode(-50, answer=Answer.WAIT), episode(-20, Outcome.RESISTED, Answer.WAIT)])
    assert found[Badge.FIRST_WAIT] == at(minutes=-50)
    assert found[Badge.FIRST_RESISTED] == at(minutes=-20)


def test_hour_gap_unlocks_live_while_waiting() -> None:
    assert Badge.HOUR_GAP not in badges([episode(-59)])
    assert badges([episode(-61)])[Badge.HOUR_GAP] == at(minutes=-1)


def test_overnight_gaps_do_not_count() -> None:
    assert Badge.HOUR_GAP not in badges([episode(-DAY + 500), episode(-30)])


def test_two_hour_gap_between_two_cigarettes() -> None:
    found = badges([episode(-300), episode(-170), episode(-10)])
    assert found[Badge.TWO_HOUR_GAP] == at(minutes=-180)
    assert found[Badge.HOUR_GAP] == at(minutes=-240)


def test_half_hour_gained_in_one_day() -> None:
    found = badges([episode(-100, postponed=20), episode(-40, postponed=15)])
    assert found[Badge.GAINED_HALF_HOUR] == at(minutes=-40)


def test_three_resisted_in_one_day() -> None:
    resisted = [episode(m, Outcome.RESISTED) for m in (-90, -60, -30)]
    assert badges(resisted)[Badge.THREE_RESISTED] == at(minutes=-30)


def test_fewer_than_the_day_before_once_the_day_is_over() -> None:
    two_days_ago = [episode(-2 * DAY), episode(-2 * DAY + 10), episode(-2 * DAY + 20)]
    yesterday = [episode(-DAY - 60)]
    found = badges([*two_days_ago, *yesterday])
    assert Badge.FEWER_THAN_YESTERDAY in found
    assert Badge.FEWER_THAN_YESTERDAY not in badges([*two_days_ago, episode(-10)])


def test_badges_are_listed_in_unlock_order() -> None:
    found = achievements(
        [episode(-200, Outcome.RESISTED, Answer.WAIT), episode(-100, answer=Answer.WAIT)],
        at(0),
    )
    assert [a.unlocked_at for a in found] == sorted(a.unlocked_at for a in found)
