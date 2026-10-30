"""Optional object detector for lighters, packs, rolling papers and cigarettes.

No public model covers these objects yet, so this runs only when the user points
the config at a MediaPipe object detector (`.tflite`, e.g. trained with
MediaPipe Model Maker). Its labels are mapped to cues with `labels`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

from mediapipe.tasks.python import BaseOptions, vision

from you_just_smoked.domain.cues import Cue, CueObservation
from you_just_smoked.perception.landmarks import to_mediapipe_image

if TYPE_CHECKING:
    from pathlib import Path

    from you_just_smoked.perception.frame import Frame
    from you_just_smoked.perception.scene import Scene

DEFAULT_LABELS: Mapping[str, Cue] = MappingProxyType(
    {
        "lighter": Cue.LIGHTER,
        "cigarette_pack": Cue.PACK,
        "tobacco_pouch": Cue.ROLLING,
        "rolling_paper": Cue.ROLLING,
        "filter_tip": Cue.ROLLING,
        "cigarette": Cue.CIGARETTE,
    }
)


@dataclass(frozen=True, slots=True)
class ObjectSettings:
    model: Path
    min_score: float = 0.5
    labels: Mapping[str, Cue] = field(default_factory=lambda: DEFAULT_LABELS)


class ObjectDetector:
    def __init__(self, settings: ObjectSettings) -> None:
        self._labels = settings.labels
        self._detector = vision.ObjectDetector.create_from_options(
            vision.ObjectDetectorOptions(
                base_options=BaseOptions(model_asset_path=str(settings.model)),
                score_threshold=settings.min_score,
                category_allowlist=list(settings.labels),
            )
        )

    def detect(self, frame: Frame, scene: Scene) -> list[CueObservation]:
        best: dict[Cue, float] = {}
        for detection in self._detector.detect(to_mediapipe_image(frame.image)).detections:
            for category in detection.categories:
                cue = self._labels.get(category.category_name)
                if cue is not None:
                    best[cue] = max(best.get(cue, 0.0), float(category.score))
        return [CueObservation(cue, min(score, 1.0), frame.at) for cue, score in best.items()]

    def close(self) -> None:
        self._detector.close()
