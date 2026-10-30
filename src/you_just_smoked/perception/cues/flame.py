"""A small, very bright blob with a warm rim, close to the mouth or a fingertip.

Webcams clip a lighter flame to a white core surrounded by orange. Lamps and
windows are too big, screens and LEDs have no warm rim, and skin highlights are
mostly warm with almost no clipped core. Anything far from the face and hands
is ignored, so a candle on the shelf does not count.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import cv2
import numpy as np

from you_just_smoked.domain.cues import Cue, CueObservation
from you_just_smoked.perception.cues.base import closeness
from you_just_smoked.perception.scene import Point

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from you_just_smoked.perception.frame import Frame, Image
    from you_just_smoked.perception.scene import Scene


@dataclass(frozen=True, slots=True)
class FlameSettings:
    working_width: int = 320
    hot_value: int = 245
    hot_max_saturation: int = 60
    """A clipped core is near-white: very bright and almost colourless."""

    warm_max_hue: int = 35
    """OpenCV hue runs 0-179; 0-35 covers red, orange and yellow."""

    warm_min_saturation: int = 90
    warm_min_value: int = 200
    min_area: float = 0.0001
    max_area: float = 0.015
    """Blob size as a fraction of the frame."""

    min_hot_ratio: float = 0.25
    min_warm_ratio: float = 0.1
    max_hot_fraction: float = 0.08
    """If more of the frame than this is clipped, the exposure is useless; skip it."""

    reach: float = 1.2
    """Distance from the mouth or a fingertip, in face widths, at which a blob stops counting."""

    unit_without_face: float = 0.15


class FlameDetector:
    def __init__(self, settings: FlameSettings | None = None) -> None:
        self._settings = settings or FlameSettings()

    def close(self) -> None:
        pass

    def detect(self, frame: Frame, scene: Scene) -> list[CueObservation]:
        anchors = _anchors(scene)
        if not anchors:
            return []
        unit = scene.face.scale if scene.face else self._settings.unit_without_face
        strength = 0.0
        for center in self._blob_centers(frame.image):
            nearest = min(center.distance_to(anchor) for anchor in anchors)
            strength = max(strength, closeness(nearest / unit, self._settings.reach))
        if strength <= 0.0:
            return []
        return [CueObservation(Cue.FLAME, 0.5 + 0.5 * strength, frame.at)]

    def _blob_centers(self, image: Image) -> list[Point]:
        s = self._settings
        small = _resize(image, s.working_width)
        hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
        hue, saturation, value = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        hot = (value >= s.hot_value) & (saturation <= s.hot_max_saturation)
        if hot.mean() > s.max_hot_fraction:
            return []
        warm = (hue <= s.warm_max_hue) & (saturation >= s.warm_min_saturation)
        warm &= (value >= s.warm_min_value) & ~hot
        mask = (hot | warm).astype(np.uint8)

        count, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
        flat = np.asarray(labels, dtype=np.intp).ravel()
        hot_counts = np.bincount(flat, weights=hot.ravel(), minlength=count)
        warm_counts = np.bincount(flat, weights=warm.ravel(), minlength=count)

        height, width = mask.shape
        centers: list[Point] = []
        for label in range(1, count):
            pixels = float(stats[label, cv2.CC_STAT_AREA])
            area = pixels / (width * height)
            if not s.min_area <= area <= s.max_area:
                continue
            if hot_counts[label] / pixels < s.min_hot_ratio:
                continue
            if warm_counts[label] / pixels < s.min_warm_ratio:
                continue
            x, y = centroids[label]
            centers.append(Point(float(x) / width, float(y) / width))
        return centers


def _anchors(scene: Scene) -> list[Point]:
    anchors = [tip for hand in scene.hands for tip in hand.grip_tips()]
    if scene.face is not None:
        anchors.append(scene.face.mouth)
    return anchors


def _resize(image: Image, width: int) -> NDArray[np.uint8]:
    if image.shape[1] <= width:
        return image
    height = round(image.shape[0] * width / image.shape[1])
    resized = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
    return np.asarray(resized, dtype=np.uint8)
