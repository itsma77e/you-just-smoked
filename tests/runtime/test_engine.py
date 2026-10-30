from datetime import timedelta

import pytest

from you_just_smoked.domain.cues import Cue
from you_just_smoked.domain.episode import Answer, Outcome
from you_just_smoked.domain.sampling import CaptureMode
from you_just_smoked.domain.tracker import EpisodeTracker, Phase
from you_just_smoked.runtime.commands import LogCigarette, Pause, Resume, Stop
from you_just_smoked.runtime.engine import Engine, EngineDeps
from you_just_smoked.runtime.status import Status

from fakes import FakeCamera, FakeClock, InMemoryEpisodes, RecordingNotifier, ScriptedPerceiver


class Harness:
    def __init__(self) -> None:
        self.clock = FakeClock()
        self.camera = FakeCamera()
        self.perceiver = ScriptedPerceiver()
        self.episodes = InMemoryEpisodes()
        self.notifier = RecordingNotifier()
        self.statuses: list[Status] = []
        self.engine = Engine(
            EngineDeps(
                tracker=EpisodeTracker(),
                camera=self.camera,
                perception=self.perceiver,
                episodes=self.episodes,
                notifier=self.notifier,
                clock=self.clock,
                on_status=self.statuses.append,
            )
        )

    def step(self, *cues: Cue, seconds: float = 6) -> timedelta:
        self.perceiver.show(*cues)
        interval = self.engine.step()
        self.clock.advance(seconds)
        return interval

    def last_mode(self) -> CaptureMode:
        return self.camera.modes[-1]

    @property
    def status(self) -> Status:
        return self.statuses[-1]


@pytest.fixture
def harness() -> Harness:
    return Harness()


def test_a_cigarette_gives_one_nudge_and_one_logged_episode(harness: Harness) -> None:
    harness.step(Cue.LIGHTER)
    harness.step(Cue.FLAME)
    for _ in range(10):
        harness.step(Cue.PUFF)
    assert len(harness.notifier.nudges) == 1
    assert harness.status.phase is Phase.ACTIVE

    harness.clock.advance(7 * 60)
    harness.step()
    [episode] = harness.episodes.episodes
    assert episode.outcome is Outcome.SMOKED
    assert harness.status.stats.today == 1


def test_streams_while_suspicious_and_snapshots_otherwise(harness: Harness) -> None:
    harness.step()
    harness.step(Cue.FLAME)
    harness.step()
    assert harness.camera.modes == [CaptureMode.SNAPSHOT, CaptureMode.SNAPSHOT, CaptureMode.STREAM]


def test_answering_wait_postpones_the_episode(harness: Harness) -> None:
    harness.step(Cue.FLAME)
    harness.step(Cue.LIGHTER)
    harness.notifier.answer_last(Answer.WAIT)
    assert harness.engine.process_pending()
    assert harness.status.phase is Phase.POSTPONED


def test_pause_turns_the_camera_off_until_resumed(harness: Harness) -> None:
    harness.engine.apply(Pause(timedelta(hours=1)))
    harness.step()
    assert harness.last_mode() is CaptureMode.OFF
    assert harness.status.paused

    harness.engine.apply(Resume())
    harness.step()
    assert harness.last_mode() is CaptureMode.SNAPSHOT


def test_pause_expires_on_its_own(harness: Harness) -> None:
    harness.engine.apply(Pause(timedelta(minutes=1)))
    harness.clock.advance(61)
    harness.step()
    assert harness.last_mode() is CaptureMode.SNAPSHOT


def test_logging_by_hand_is_saved(harness: Harness) -> None:
    harness.engine.apply(LogCigarette())
    assert len(harness.episodes.episodes) == 1
    assert harness.status.stats.today == 1
    assert harness.status.stats.last_cigarette_at == harness.clock.now()


def test_a_broken_camera_is_reported_and_recovers(harness: Harness) -> None:
    harness.camera.broken = True
    harness.step()
    assert harness.status.camera_error == "unplugged"
    harness.camera.broken = False
    harness.step()
    assert harness.status.camera_error is None


def test_run_returns_on_stop_and_releases_the_camera(harness: Harness) -> None:
    harness.engine.submit(Stop())
    harness.engine.run()
    assert harness.camera.closed
