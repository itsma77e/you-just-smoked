"""A live debug window: what the camera sees, the landmarks, the cues and the tracker state.

Use it to check your camera framing and to tune thresholds. Nothing is saved.
Press r to reset the tracker and try again, q to quit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import cv2
import numpy as np

from you_just_smoked.app.bootstrap import build_perception
from you_just_smoked.capture.camera import OpenCVCamera
from you_just_smoked.domain.tracker import EpisodeTracker, Phase
from you_just_smoked.perception.frame import Frame
from you_just_smoked.runtime.clock import SystemClock

if TYPE_CHECKING:
    from datetime import datetime

    from numpy.typing import NDArray

    from you_just_smoked.app.config import Config
    from you_just_smoked.app.paths import AppPaths
    from you_just_smoked.perception.pipeline import Perception
    from you_just_smoked.perception.scene import Point

_WINDOW = "you-just-smoked preview (r: reset, q: quit)"
_GREEN = (80, 220, 120)
_ORANGE = (40, 140, 255)
_WHITE = (255, 255, 255)


def run_preview(config: Config, paths: AppPaths) -> None:
    clock = SystemClock()
    tracker = EpisodeTracker(config.tracker)
    camera = OpenCVCamera(config.camera)
    perception_pipeline = build_perception(config, paths)
    try:
        camera.open()
        while (key := cv2.waitKey(1) & 0xFF) != ord("q"):
            if key == ord("r"):
                tracker = EpisodeTracker(config.tracker)
            frame = Frame(camera.read(), clock.now())
            perception = perception_pipeline.perceive(frame)
            tracker.tick(frame.at)
            for observation in perception.observations:
                tracker.observe(observation)
            cv2.imshow(_WINDOW, _draw(frame, perception, _describe(tracker, frame.at)))
    finally:
        camera.close()
        perception_pipeline.close()
        cv2.destroyAllWindows()


def _describe(tracker: EpisodeTracker, at: datetime) -> str:
    """The tracker state in plain words, including whether the app would nudge now."""
    match tracker.phase:
        case Phase.IDLE:
            return f"watching | evidence {tracker.suspicion(at):.0%} of a nudge"
        case Phase.ACTIVE:
            return "EPISODE OPEN: the app shows the nudge here | r: reset"
        case Phase.POSTPONED:
            return f"waiting (postponed) | relapse {tracker.suspicion(at):.0%}"
        case Phase.REFRACTORY:
            return "just ended: cues ignored for a few minutes | r: reset"


def _draw(frame: Frame, perception: Perception, status: str) -> NDArray[np.uint8]:
    canvas = np.ascontiguousarray(cv2.cvtColor(frame.image, cv2.COLOR_RGB2BGR), dtype=np.uint8)
    width = frame.width

    def pixel(point: Point) -> tuple[int, int]:
        return round(point.x * width), round(point.y * width)

    scene = perception.scene
    for hand in scene.hands:
        for point in hand.landmarks:
            cv2.circle(canvas, pixel(point), 3, _GREEN, -1)
    if scene.face is not None:
        f = scene.face
        top_left = (round(f.left * width), round(f.top * width))
        bottom_right = (round((f.left + f.width) * width), round((f.top + f.height) * width))
        cv2.rectangle(canvas, top_left, bottom_right, _GREEN, 2)
        cv2.circle(canvas, pixel(f.mouth), 5, _ORANGE, -1)

    cues = ", ".join(f"{o.cue} {o.confidence:.2f}" for o in perception.observations) or "-"
    for row, text in enumerate((status, f"cues: {cues}")):
        cv2.putText(canvas, text, (10, 24 + 24 * row), cv2.FONT_HERSHEY_SIMPLEX, 0.6, _WHITE, 2)
    return canvas
