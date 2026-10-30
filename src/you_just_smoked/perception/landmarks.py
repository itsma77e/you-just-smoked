"""MediaPipe adapter: one RGB frame in, a `Scene` of hands and the main face out."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Self

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

from you_just_smoked.perception.scene import Face, Hand, Point, Scene

if TYPE_CHECKING:
    from pathlib import Path
    from types import TracebackType

    from you_just_smoked.perception.frame import Frame, Image

_MOUTH_KEYPOINT = 3


class SceneReader(Protocol):
    def read(self, frame: Frame) -> Scene: ...

    def close(self) -> None: ...


def to_mediapipe_image(image: Image) -> Any:
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=image)


class MediaPipeSceneReader:
    def __init__(self, hand_model: Path, face_model: Path, *, min_confidence: float = 0.5) -> None:
        self._hands = vision.HandLandmarker.create_from_options(
            vision.HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(hand_model)),
                num_hands=2,
                min_hand_detection_confidence=min_confidence,
                min_hand_presence_confidence=min_confidence,
            )
        )
        self._faces = vision.FaceDetector.create_from_options(
            vision.FaceDetectorOptions(
                base_options=BaseOptions(model_asset_path=str(face_model)),
                min_detection_confidence=min_confidence,
            )
        )

    def read(self, frame: Frame) -> Scene:
        image = to_mediapipe_image(frame.image)
        aspect = frame.height / frame.width
        hands = tuple(
            Hand(tuple(Point(mark.x, mark.y * aspect) for mark in marks))
            for marks in self._hands.detect(image).hand_landmarks
        )
        return Scene(hands=hands, face=_main_face(self._faces.detect(image), frame, aspect))

    def close(self) -> None:
        self._hands.close()
        self._faces.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


def _main_face(result: Any, frame: Frame, aspect: float) -> Face | None:
    detections = [d for d in result.detections if len(d.keypoints) > _MOUTH_KEYPOINT]
    if not detections:
        return None
    biggest = max(detections, key=lambda d: d.bounding_box.width * d.bounding_box.height)
    box = biggest.bounding_box
    mouth = biggest.keypoints[_MOUTH_KEYPOINT]
    width = frame.width
    return Face(
        left=box.origin_x / width,
        top=box.origin_y / width,
        width=box.width / width,
        height=box.height / width,
        mouth=Point(mouth.x, mouth.y * aspect),
    )
