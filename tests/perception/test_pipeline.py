from you_just_smoked.domain.cues import Cue, CueObservation
from you_just_smoked.perception.frame import Frame
from you_just_smoked.perception.pipeline import PerceptionPipeline
from you_just_smoked.perception.scene import Scene

from factories import blank_frame, face


class FixedReader:
    def __init__(self, scene: Scene) -> None:
        self.scene = scene
        self.closed = False

    def read(self, frame: Frame) -> Scene:
        return self.scene

    def close(self) -> None:
        self.closed = True


class AlwaysFlame:
    def __init__(self) -> None:
        self.closed = False

    def detect(self, frame: Frame, scene: Scene) -> list[CueObservation]:
        return [CueObservation(Cue.FLAME, 1.0, frame.at)]

    def close(self) -> None:
        self.closed = True


def test_runs_every_detector_when_someone_is_there() -> None:
    pipeline = PerceptionPipeline(FixedReader(Scene(face=face())), [AlwaysFlame(), AlwaysFlame()])
    assert len(pipeline.perceive(blank_frame()).observations) == 2


def test_skips_detectors_on_an_empty_scene() -> None:
    pipeline = PerceptionPipeline(FixedReader(Scene()), [AlwaysFlame()])
    assert pipeline.perceive(blank_frame()).observations == []


def test_close_releases_reader_and_detectors() -> None:
    reader, detector = FixedReader(Scene()), AlwaysFlame()
    PerceptionPipeline(reader, [detector]).close()
    assert reader.closed
    assert detector.closed
