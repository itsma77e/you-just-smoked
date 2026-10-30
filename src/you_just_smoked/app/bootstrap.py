"""Wires the real adapters together. The only module that knows about all of them.

Threads: the Tk interface owns the main thread (Tk requires it). The engine thread
creates and owns everything stateful (database, models, camera), so none of it
is ever touched from two threads. They meet only at two queues: commands to the
engine, and messages to the interface.
"""

from __future__ import annotations

import logging
import queue
import threading
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from you_just_smoked.app.paths import APP_NAME
from you_just_smoked.capture.isolated import IsolatedCamera
from you_just_smoked.domain.tracker import EpisodeTracker
from you_just_smoked.i18n import resolve_language
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
from you_just_smoked.ui.app import Shutdown, StatusChanged, TkNotifier, UiApp, UiSettings
from you_just_smoked.ui.position import PositionStore

if TYPE_CHECKING:
    from collections.abc import Callable

    from you_just_smoked.app.config import Config
    from you_just_smoked.app.paths import AppPaths
    from you_just_smoked.notify.base import Notifier
    from you_just_smoked.perception.cues.base import CueDetector
    from you_just_smoked.runtime.status import Status

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
    """Show the widget on this thread and run the engine on a worker; return on quit."""
    language = resolve_language(config.language)
    commands: queue.Queue[Command] = queue.Queue()
    positions = PositionStore(paths.widget_position)
    settings = UiSettings(
        APP_NAME,
        language,
        positions,
        sound=config.sound,
        computer_day=timedelta(hours=config.computer_hours),
    )
    ui = UiApp(commands.put, settings, SystemClock())
    shared = _Shared(
        language,
        commands,
        TkNotifier(ui.post),
        on_status=lambda status: ui.post(StatusChanged(status)),
    )

    def engine_thread() -> None:
        try:
            _run_engine(config, paths, shared)
        except Exception:
            log.exception("The engine stopped unexpectedly")
        finally:
            ui.post(Shutdown())

    worker = threading.Thread(target=engine_thread, name="engine")
    worker.start()
    try:
        ui.run()
    finally:
        commands.put(Stop())
        worker.join(timeout=10)


@dataclass(frozen=True, slots=True)
class _Shared:
    """What the engine thread receives from the main thread."""

    language: str
    commands: queue.Queue[Command]
    notifier: Notifier
    on_status: Callable[[Status], None]


def _run_engine(config: Config, paths: AppPaths, shared: _Shared) -> None:
    with ExitStack() as stack:
        connection = connect(paths.database)
        stack.callback(connection.close)
        perception = build_perception(config, paths)
        stack.callback(perception.close)
        camera = IsolatedCamera(config.camera)
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
                wait=config.wait,
                on_status=shared.on_status,
                commands=shared.commands,
            )
        )
        engine.run()
