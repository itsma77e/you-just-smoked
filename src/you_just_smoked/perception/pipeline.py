"""Runs the scene reader once and every cue detector on its result."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from you_just_smoked.domain.cues import CueObservation
    from you_just_smoked.perception.cues.base import CueDetector
    from you_just_smoked.perception.frame import Frame
    from you_just_smoked.perception.landmarks import SceneReader
    from you_just_smoked.perception.scene import Scene


@dataclass(frozen=True, slots=True)
class Perception:
    scene: Scene
    observations: list[CueObservation]


class PerceptionPipeline:
    def __init__(self, reader: SceneReader, detectors: Sequence[CueDetector]) -> None:
        self._reader = reader
        self._detectors = tuple(detectors)

    def perceive(self, frame: Frame) -> Perception:
        scene = self._reader.read(frame)
        if not scene.someone_visible:
            return Perception(scene, [])
        observations = [
            obs for detector in self._detectors for obs in detector.detect(frame, scene)
        ]
        return Perception(scene, observations)

    def close(self) -> None:
        self._reader.close()
        for detector in self._detectors:
            detector.close()
