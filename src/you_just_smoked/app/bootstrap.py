"""Wires the real adapters together. The only module that knows about all of them.

Threads: the tray owns the main thread (macOS requires it). The engine thread
creates and owns everything stateful (database, models, camera), so none of it
is ever touched from two threads. They meet only at the command queue and the
published `Status`.
"""

from __future__ import annotations

import logging
import queue
import threading
from contextlib import ExitStack
from dataclasses import dataclass
from typing import TYPE_CHECKING

from you_just_smoked.app.paths import APP_NAME
from you_just_smoked.capture.camera import CameraController, OpenCVCamera
from you_just_smoked.domain.tracker import EpisodeTracker
from you_just_smoked.notify.desktop import DesktopNotifierAdapter
from you_just_smoked.notify.messages import resolve_language
from you_just_smoked.perception.cues.flame import FlameDetector
from you_just_smoked.perception.cues.objects import ObjectDetector, ObjectSettings
from you_just_smoked.perception.cues.puff import PuffDetector
from you_just_smoked.perception.cues.rolling import RollingDetector
from you_just_smoked.perception.landmarks import MediaPipeSceneReader
from you_just_smoked.perception.models import FACE_DETECTOR, HAND_LANDMARKER, ensure_model
from you_just_smoked.perception.pipeline import PerceptionPipeline
from you_just_smoked.runtime.clock import SystemClock
from you_just_smoked.runtime.commands import Command, Stop
from you_just_smoked.runtime.engine import Engine, EngineDeps
from you_just_smoked.storage.database import connect
from you_just_smoked.storage.episodes import EpisodeRepository
from you_just_smoked.ui.tray import Tray

if TYPE_CHECKING:
    from you_just_smoked.app.config import Config
    from you_just_smoked.app.paths import AppPaths
    from you_just_smoked.notify.base import Notifier
    from you_just_smoked.perception.cues.base import CueDetector

log = logging.getLogger(__name__)


def build_perception(config: Config, paths: AppPaths) -> PerceptionPipeline:
    reader = MediaPipeSceneReader(
        ensure_model(HAND_LANDMARKER, paths.models),
        ensure_model(FACE_DETECTOR, paths.models),
    )
    detectors: list[CueDetector] = [RollingDetector(), FlameDetector(), PuffDetector()]
    if config.objects is not None:
        settings = ObjectSettings(config.objects.model, config.objects.min_score)
        detectors.append(ObjectDetector(settings))
    return PerceptionPipeline(reader, detectors)


def run_app(config: Config, paths: AppPaths) -> None:
    """Show the tray on this thread and run the engine on a worker; return on quit."""
    language = resolve_language(config.language)
    commands: queue.Queue[Command] = queue.Queue()
    notifier = DesktopNotifierAdapter(APP_NAME)
    tray = Tray(APP_NAME, commands.put, language)

    def engine_thread() -> None:
        try:
            _run_engine(config, paths, _Shared(language, commands, notifier, tray))
        except Exception:
            log.exception("The engine stopped unexpectedly")
        finally:
            tray.stop()

    worker = threading.Thread(target=engine_thread, name="engine")
    try:
        tray.run(setup=worker.start)
    finally:
        commands.put(Stop())
        if worker.is_alive():
            worker.join(timeout=10)
        notifier.close()


@dataclass(frozen=True, slots=True)
class _Shared:
    """What the engine thread receives from the main thread."""

    language: str
    commands: queue.Queue[Command]
    notifier: Notifier
    tray: Tray


def _run_engine(config: Config, paths: AppPaths, shared: _Shared) -> None:
    with ExitStack() as stack:
        connection = connect(paths.database)
        stack.callback(connection.close)
        perception = build_perception(config, paths)
        stack.callback(perception.close)
        camera = CameraController(OpenCVCamera(config.camera), keep_open=config.camera.keep_open)
        stack.callback(camera.close)

        engine = Engine(
            EngineDeps(
                tracker=EpisodeTracker(config.tracker),
                camera=camera,
                perception=perception,
                episodes=EpisodeRepository(connection),
                notifier=shared.notifier,
                clock=SystemClock(),
                sampling=config.sampling,
                language=shared.language,
                on_status=shared.tray.show,
                commands=shared.commands,
            )
        )
        engine.run()
