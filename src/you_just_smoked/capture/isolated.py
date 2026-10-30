"""`FrameSource` backed by the camera helper process, restarted before its leak adds up."""

from __future__ import annotations

import contextlib
import logging
import multiprocessing
from typing import TYPE_CHECKING, Any, Protocol

from you_just_smoked.capture.camera import OpenCVCamera
from you_just_smoked.capture.worker import Failed, Grab, Grabbed, Stop, serve
from you_just_smoked.domain.sampling import CaptureMode
from you_just_smoked.runtime.ports import CameraUnavailableError

if TYPE_CHECKING:
    from multiprocessing.process import BaseProcess

    from you_just_smoked.capture.camera import CameraSettings
    from you_just_smoked.capture.worker import CameraFactory
    from you_just_smoked.perception.frame import Image

log = logging.getLogger(__name__)

RECYCLE_AFTER_OPENS = 20
"""About 140 MB of leaked memory at most, recycled every few minutes when idle."""

_REPLY_TIMEOUT_S = 15.0


class _Channel(Protocol):
    """The parent end of the pipe (a `Connection`, or a `PipeConnection` on Windows)."""

    def send(self, obj: Any) -> None: ...

    def recv(self) -> Any: ...

    def poll(self, timeout: float | None = ...) -> bool: ...

    def close(self) -> None: ...


class IsolatedCamera:
    def __init__(
        self,
        settings: CameraSettings,
        *,
        factory: CameraFactory = OpenCVCamera,
        recycle_after: int = RECYCLE_AFTER_OPENS,
    ) -> None:
        self._settings = settings
        self._factory = factory
        self._recycle_after = recycle_after
        self._context = multiprocessing.get_context("spawn")
        self._process: BaseProcess | None = None
        self._connection: _Channel | None = None
        self._opens = 0
        self.restarts = 0

    def grab(self, mode: CaptureMode) -> Image | None:
        if mode is CaptureMode.OFF and self._process is None:
            return None
        reply = self._request(Grab(mode))
        if isinstance(reply, Failed):
            raise CameraUnavailableError(reply.reason)
        self._opens += reply.opened
        released = mode is CaptureMode.OFF or (
            mode is CaptureMode.SNAPSHOT and not self._settings.keep_open
        )
        if released and self._opens >= self._recycle_after:
            self._stop()
        return reply.image

    def close(self) -> None:
        self._stop()

    def _request(self, request: Grab) -> Grabbed | Failed:
        connection = self._ensure_started()
        connection.send(request)
        if not connection.poll(_REPLY_TIMEOUT_S):
            self._kill()
            raise CameraUnavailableError("the camera helper stopped answering")
        reply: Grabbed | Failed = connection.recv()
        return reply

    def _ensure_started(self) -> _Channel:
        if self._process is not None and self._connection is not None:
            if self._process.is_alive():
                return self._connection
            self._kill()
        parent, child = self._context.Pipe()
        process = self._context.Process(
            target=serve,
            args=(child, self._settings, self._factory),
            name="camera",
            daemon=True,
        )
        process.start()
        child.close()
        self._process, self._connection, self._opens = process, parent, 0
        self.restarts += 1
        return parent

    def _stop(self) -> None:
        if self._process is None or self._connection is None:
            return
        with contextlib.suppress(OSError):
            self._connection.send(Stop())
        self._process.join(timeout=5)
        self._kill()

    def _kill(self) -> None:
        if self._process is not None and self._process.is_alive():
            log.warning("Terminating an unresponsive camera helper")
            self._process.terminate()
            self._process.join(timeout=2)
        if self._connection is not None:
            self._connection.close()
        self._process, self._connection = None, None
