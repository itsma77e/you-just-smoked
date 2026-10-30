import cv2
import numpy as np

from you_just_smoked.domain.cues import Cue
from you_just_smoked.perception.cues.flame import FlameDetector
from you_just_smoked.perception.frame import Image
from you_just_smoked.perception.scene import Scene

from factories import face, frame_of

WIDTH, HEIGHT = 320, 240
ORANGE = (255, 140, 20)
WHITE = (255, 255, 255)
SCENE = Scene(face=face(mouth=(0.5, 0.45)))


def dark() -> Image:
    return np.full((HEIGHT, WIDTH, 3), 40, dtype=np.uint8)


def with_flame(x: float, y: float, core: int = 3, rim: int = 6) -> Image:
    """Draw a flame centred at (x, y), given in image widths."""
    image = dark()
    center = (round(x * WIDTH), round(y * WIDTH))
    cv2.circle(image, center, rim, ORANGE, -1)
    cv2.circle(image, center, core, WHITE, -1)
    return image


def test_small_hot_blob_with_warm_rim_near_the_mouth_is_a_flame() -> None:
    [observation] = FlameDetector().detect(frame_of(with_flame(0.5, 0.5)), SCENE)
    assert observation.cue is Cue.FLAME


def test_flame_far_from_face_and_hands_is_ignored() -> None:
    assert FlameDetector().detect(frame_of(with_flame(0.05, 0.05)), SCENE) == []


def test_white_light_without_warm_rim_is_not_a_flame() -> None:
    image = dark()
    cv2.circle(image, (160, 160), 5, WHITE, -1)
    assert FlameDetector().detect(frame_of(image), SCENE) == []


def test_large_bright_area_is_not_a_flame() -> None:
    assert FlameDetector().detect(frame_of(with_flame(0.5, 0.5, core=30, rim=40)), SCENE) == []


def test_overexposed_frame_is_skipped() -> None:
    image = with_flame(0.5, 0.5)
    image[: HEIGHT // 3] = 255
    assert FlameDetector().detect(frame_of(image), SCENE) == []


def test_needs_a_face_or_a_hand_to_anchor_to() -> None:
    assert FlameDetector().detect(frame_of(with_flame(0.5, 0.5)), Scene()) == []


def test_large_frames_are_downscaled_consistently() -> None:
    small = with_flame(0.5, 0.5)
    big = np.repeat(np.repeat(small, 4, axis=0), 4, axis=1)
    assert FlameDetector().detect(frame_of(big), SCENE)
