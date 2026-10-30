"""OpenCV webcam adapter and the policy for when it stays open."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

import cv2
import numpy as np

from you_just_smoked.domain.sampling import CaptureMode
from you_just_smoked.runtime.ports import CameraUnavailableError

if TYPE_CHECKING:
    from you_just_smoked.perception.frame import Image

_BLACK_FRAME_RETRIES = 5
"""Some drivers deliver fully black frames right after opening."""


class Camera(Protocol):
    @property
    def is_open(self) -> bool: ...

    def open(self) -> None: ...

    def read(self) -> Image: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class CameraSettings:
    index: int = 0
    width: int | None = None
    height: int | None = None
    """Requested resolution. None keeps the camera default; changing it slows down opening."""

    warmup_frames: int = 5
    """Frames discarded after opening, while auto-exposure settles."""

    keep_open: bool = False
    """Keep the camera on between snapshots: faster, but the camera light stays on."""


class OpenCVCamera:
    def __init__(self, settings: CameraSettings) -> None:
        self._settings = settings
        self._capture: Any = None

    @property
    def is_open(self) -> bool:
        return self._capture is not None

    def open(self) -> None:
        if self._capture is not None:
            return
        s = self._settings
        capture = cv2.VideoCapture(s.index, _backend())
        if not capture.isOpened():
            capture.release()
            raise CameraUnavailableError(f"camera {s.index} could not be opened")
        if s.width and s.height:
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, s.width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, s.height)
        for _ in range(s.warmup_frames):
            capture.grab()
        self._capture = capture

    def read(self) -> Image:
        if self._capture is None:
            raise CameraUnavailableError("camera is not open")
        for _ in range(_BLACK_FRAME_RETRIES):
            ok, bgr = self._capture.read()
            if not ok or bgr is None:
                self.close()
                raise CameraUnavailableError("camera returned no frame")
            if bgr.max() > 0:
                break
        return np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), dtype=np.uint8)

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None


class CameraController:
    """Grabs one frame in the way the sampling plan asks for, releasing the camera when idle."""

    def __init__(self, camera: Camera, *, keep_open: bool) -> None:
        self._camera = camera
        self._keep_open = keep_open

    def grab(self, mode: CaptureMode) -> Image | None:
        if mode is CaptureMode.OFF:
            self._camera.close()
            return None
        self._camera.open()
        try:
            return self._camera.read()
        finally:
            if mode is CaptureMode.SNAPSHOT and not self._keep_open:
                self._camera.close()

    def close(self) -> None:
        self._camera.close()


def _backend() -> int:
    # Media Foundation can take seconds to open on Windows; DirectShow opens fast.
    return int(cv2.CAP_DSHOW) if sys.platform == "win32" else int(cv2.CAP_ANY)
