from datetime import timedelta

import pytest

from you_just_smoked.domain.cues import Cue
from you_just_smoked.domain.episode import Answer, Outcome
from you_just_smoked.domain.sampling import CaptureMode, SamplingSettings
from you_just_smoked.domain.tracker import EpisodeTracker, Phase
from you_just_smoked.perception.scene import Scene
from you_just_smoked.runtime.commands import LogCigarette, Pause, Resume, Stop
from you_just_smoked.runtime.engine import Engine, EngineDeps
from you_just_smoked.runtime.status import Status

from factories import face, hand
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

    def step(self, *cues: Cue, seconds: float = 6, scene: Scene | None = None) -> timedelta:
        self.perceiver.show(*cues, scene=scene)
        interval = self.engine.step()
        self.clock.advance(seconds)
        return interval

    @property
    def engine_settings(self) -> SamplingSettings:
        return SamplingSettings()

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
    assert harness.status.summary.stats.today == 1


def test_a_suspicious_snapshot_makes_the_next_frame_come_fast(harness: Harness) -> None:
    assert harness.step() == harness.engine_settings.idle_interval
    assert harness.step(Cue.LIGHTER) == harness.engine_settings.stream_interval


def test_streams_while_suspicious_and_snapshots_otherwise(harness: Harness) -> None:
    harness.step()
    harness.step(Cue.LIGHTER)
    harness.step()
    assert harness.camera.modes == [CaptureMode.SNAPSHOT, CaptureMode.SNAPSHOT, CaptureMode.STREAM]


def test_a_hand_near_the_face_keeps_the_camera_streaming_for_a_while(harness: Harness) -> None:
    mouth = (0.5, 0.45)
    near = Scene(hands=(hand((0.5, 0.6), index_tip=mouth),), face=face(mouth))
    harness.step(scene=near, seconds=10)
    harness.step(seconds=11)
    assert harness.last_mode() is CaptureMode.STREAM
    harness.step()
    assert harness.last_mode() is CaptureMode.SNAPSHOT


def test_a_single_flame_opens_the_episode(harness: Harness) -> None:
    harness.step(Cue.FLAME)
    assert len(harness.notifier.nudges) == 1


def test_the_accepted_wait_is_stored_with_the_episode(harness: Harness) -> None:
    harness.step(Cue.FLAME)
    harness.notifier.answer_last(Answer.WAIT)
    harness.engine.process_pending()
    offered = harness.notifier.nudges[-1][0].wait_for
    harness.clock.advance(7 * 60)
    harness.step()
    [episode] = harness.episodes.episodes
    assert episode.wait_target == offered
    assert episode.wait_succeeded


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
    assert harness.status.summary.stats.today == 1
    assert harness.status.summary.stats.last_cigarette_at == harness.clock.now()


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
