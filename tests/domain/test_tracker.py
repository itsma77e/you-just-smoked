from datetime import timedelta

from you_just_smoked.domain.cues import Cue
from you_just_smoked.domain.episode import Answer, Outcome
from you_just_smoked.domain.events import (
    EpisodeClosed,
    EpisodeOpened,
    EpisodeResumed,
    TrackerEvent,
)
from you_just_smoked.domain.tracker import EpisodeTracker, Phase, TrackerSettings

from factories import at, seen

SETTINGS = TrackerSettings(
    quiet_period=timedelta(minutes=6), refractory_period=timedelta(minutes=5)
)


def full_cigarette(tracker: EpisodeTracker) -> list[TrackerEvent]:
    """Roll, pick up the lighter, light it, smoke for five minutes."""
    events: list[TrackerEvent] = []
    for second in range(0, 90, 10):
        events += tracker.observe(seen(Cue.ROLLING, second))
    events += tracker.observe(seen(Cue.LIGHTER, 95))
    events += tracker.observe(seen(Cue.FLAME, 97))
    for second in range(120, 420, 30):
        events += tracker.observe(seen(Cue.PUFF, second))
    return events


def closed(events: list[TrackerEvent]) -> list[EpisodeClosed]:
    return [event for event in events if isinstance(event, EpisodeClosed)]


def test_a_whole_cigarette_opens_exactly_one_episode() -> None:
    tracker = EpisodeTracker(SETTINGS)
    events = full_cigarette(tracker)
    opened = [event for event in events if isinstance(event, EpisodeOpened)]
    assert len(opened) == 1
    assert opened[0].trigger is Cue.ROLLING
    assert opened[0].started_at == at(0)
    assert tracker.phase is Phase.ACTIVE


def test_a_single_weak_cue_is_not_enough() -> None:
    tracker = EpisodeTracker(SETTINGS)
    assert tracker.observe(seen(Cue.LIGHTER, 0)) == []
    assert tracker.phase is Phase.IDLE


def test_episode_ends_after_quiet_period_and_counts_once() -> None:
    tracker = EpisodeTracker(SETTINGS)
    full_cigarette(tracker)
    last_puff = at(390)
    assert tracker.tick(last_puff + timedelta(minutes=5)) == []
    events = tracker.tick(last_puff + timedelta(minutes=6))
    [event] = closed(events)
    assert event.episode.outcome is Outcome.SMOKED
    assert event.episode.ended_at == last_puff
    assert tracker.phase is Phase.REFRACTORY


def test_refractory_ignores_cues_then_returns_to_idle() -> None:
    tracker = EpisodeTracker(SETTINGS)
    full_cigarette(tracker)
    end = at(390) + timedelta(minutes=6)
    tracker.tick(end)
    assert tracker.observe(seen(Cue.FLAME, minutes=13)) == []
    tracker.tick(end + timedelta(minutes=5))
    assert tracker.phase is Phase.IDLE


def test_wait_then_quiet_is_resisted() -> None:
    tracker = EpisodeTracker(SETTINGS)
    [opened] = tracker.observe(seen(Cue.FLAME, 0)) + tracker.observe(seen(Cue.LIGHTER, 1))
    assert isinstance(opened, EpisodeOpened)
    tracker.answer(opened.started_at, Answer.WAIT, at(2))
    [event] = closed(tracker.tick(at(2) + timedelta(minutes=6)))
    assert event.episode.outcome is Outcome.RESISTED
    assert event.episode.answer is Answer.WAIT
    assert tracker.phase is Phase.IDLE


def test_preparation_cues_alone_do_not_end_a_postponement() -> None:
    tracker = EpisodeTracker(SETTINGS)
    for second in range(0, 60, 10):
        tracker.observe(seen(Cue.ROLLING, second))
    started = tracker.open_episode_started_at
    assert started is not None
    tracker.answer(started, Answer.WAIT, at(60))
    for second in range(70, 200, 10):
        assert tracker.observe(seen(Cue.ROLLING, second)) == []
    assert tracker.phase is Phase.POSTPONED


def test_smoking_after_waiting_resumes_silently_and_records_the_delay() -> None:
    tracker = EpisodeTracker(SETTINGS)
    tracker.observe(seen(Cue.FLAME, 0))
    tracker.observe(seen(Cue.PUFF, 5))
    started = tracker.open_episode_started_at
    assert started is not None
    tracker.answer(started, Answer.WAIT, at(10))

    events = tracker.observe(seen(Cue.FLAME, minutes=4)) + tracker.observe(
        seen(Cue.PUFF, 5, minutes=4)
    )
    assert not any(isinstance(event, EpisodeOpened) for event in events)
    [resumed] = [event for event in events if isinstance(event, EpisodeResumed)]
    assert resumed.postponed_for == at(minutes=4) - at(10)

    [event] = closed(tracker.tick(at(5, minutes=10)))
    assert event.episode.outcome is Outcome.SMOKED
    assert event.episode.postponed_for == resumed.postponed_for


def test_false_alarm_is_kept_but_not_counted_and_backs_off() -> None:
    tracker = EpisodeTracker(SETTINGS)
    tracker.observe(seen(Cue.FLAME, 0))
    tracker.observe(seen(Cue.PUFF, 1))
    started = tracker.open_episode_started_at
    assert started is not None
    [event] = closed(tracker.answer(started, Answer.FALSE_ALARM, at(3)))
    assert event.episode.outcome is Outcome.FALSE_ALARM
    assert not event.episode.counts_as_cigarette
    assert tracker.phase is Phase.REFRACTORY


def test_stale_and_repeated_answers_are_ignored() -> None:
    tracker = EpisodeTracker(SETTINGS)
    tracker.observe(seen(Cue.FLAME, 0))
    tracker.observe(seen(Cue.PUFF, 1))
    started = tracker.open_episode_started_at
    assert started is not None
    assert tracker.answer(at(-100), Answer.FALSE_ALARM, at(2)) == []
    tracker.answer(started, Answer.SMOKING, at(2))
    assert tracker.answer(started, Answer.FALSE_ALARM, at(3)) == []
    assert tracker.phase is Phase.ACTIVE


def test_logging_by_hand_when_idle_records_a_cigarette() -> None:
    tracker = EpisodeTracker(SETTINGS)
    [event] = closed(tracker.log_cigarette(at(0)))
    assert event.episode.outcome is Outcome.SMOKED
    assert event.episode.trigger is None
    assert tracker.phase is Phase.REFRACTORY


def test_logging_by_hand_closes_the_open_episode_instead_of_adding_one() -> None:
    tracker = EpisodeTracker(SETTINGS)
    full_cigarette(tracker)
    [event] = closed(tracker.log_cigarette(at(400)))
    assert event.episode.started_at == at(0)
    assert tracker.log_cigarette(at(401)) == []


def test_logging_by_hand_while_postponed_keeps_the_delay() -> None:
    tracker = EpisodeTracker(SETTINGS)
    tracker.observe(seen(Cue.FLAME, 0))
    tracker.observe(seen(Cue.PUFF, 1))
    started = tracker.open_episode_started_at
    assert started is not None
    tracker.answer(started, Answer.WAIT, at(2))
    [event] = closed(tracker.log_cigarette(at(2, minutes=15)))
    assert event.episode.postponed_for == timedelta(minutes=15)


def test_suspicion_tracks_progress_towards_the_threshold() -> None:
    tracker = EpisodeTracker(SETTINGS)
    assert tracker.suspicion(at(0)) == 0.0
    tracker.observe(seen(Cue.LIGHTER, 0))
    assert 0.0 < tracker.suspicion(at(0)) < 1.0
