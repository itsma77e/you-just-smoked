"""The camera helper process. It owns the webcam and answers one request at a time.

Opening a webcam leaks a few megabytes inside the Windows capture stack every
time, whatever the backend. Doing it in this short-lived process, which the app
restarts regularly, gives the memory back to the system.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from you_just_smoked.capture.camera import Camera, CameraController, CameraSettings
from you_just_smoked.domain.sampling import CaptureMode
from you_just_smoked.runtime.ports import CameraUnavailableError

if TYPE_CHECKING:
    from multiprocessing.connection import Connection

    from you_just_smoked.perception.frame import Image

CameraFactory = Callable[[CameraSettings], Camera]


@dataclass(frozen=True, slots=True)
class Grab:
    mode: CaptureMode


@dataclass(frozen=True, slots=True)
class Stop:
    pass


@dataclass(frozen=True, slots=True)
class Grabbed:
    image: Image | None
    opened: bool
    """True when this request had to open the device, which is what leaks."""


@dataclass(frozen=True, slots=True)
class Failed:
    reason: str


def serve(connection: Connection, settings: CameraSettings, factory: CameraFactory) -> None:
    """Entry point of the helper process. Returns on `Stop` or when the app goes away."""
    camera = factory(settings)
    controller = CameraController(camera, keep_open=settings.keep_open)
    try:
        while True:
            try:
                request = connection.recv()
            except (EOFError, KeyboardInterrupt):
                return  # the app went away, or Ctrl+C reached this console too
            if isinstance(request, Stop):
                return
            opened = request.mode is not CaptureMode.OFF and not camera.is_open
            try:
                connection.send(Grabbed(controller.grab(request.mode), opened))
            except CameraUnavailableError as error:
                connection.send(Failed(str(error)))
    finally:
        controller.close()
