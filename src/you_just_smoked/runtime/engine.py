"""The main loop: decide when to look, look, update the tracker, react to its events.

All state lives on the engine thread. The interface only `submit`s commands and
renders the latest `Status` that the engine publishes.
"""

from __future__ import annotations

import logging
import queue
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from you_just_smoked.domain.events import EpisodeClosed, EpisodeOpened, EpisodeResumed
from you_just_smoked.domain.sampling import (
    Presence,
    SamplingPlan,
    SamplingSettings,
    Situation,
    plan_sampling,
)
from you_just_smoked.domain.stats import WaitWindow
from you_just_smoked.domain.summary import Summary, summarize
from you_just_smoked.notify.messages import nudge_text
from you_just_smoked.perception.frame import Frame
from you_just_smoked.runtime.commands import (
    AnswerNudge,
    Command,
    LogCigarette,
    Pause,
    Resume,
    Stop,
)
from you_just_smoked.runtime.ports import CameraUnavailableError
from you_just_smoked.runtime.status import Status

if TYPE_CHECKING:
    from collections.abc import Iterable

    from you_just_smoked.domain.episode import Answer
    from you_just_smoked.domain.events import TrackerEvent
    from you_just_smoked.domain.sampling import CaptureMode
    from you_just_smoked.domain.tracker import EpisodeTracker
    from you_just_smoked.notify.base import Notifier
    from you_just_smoked.perception.frame import Image
    from you_just_smoked.runtime.clock import Clock
    from you_just_smoked.runtime.ports import EpisodeLog, FrameSource, Perceiver

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EngineDeps:
    tracker: EpisodeTracker
    camera: FrameSource
    perception: Perceiver
    episodes: EpisodeLog
    notifier: Notifier
    clock: Clock
    sampling: SamplingSettings = field(default_factory=SamplingSettings)
    language: str = "en"
    wait: WaitWindow = field(default_factory=WaitWindow)
    on_status: Callable[[Status], None] = lambda _status: None
    commands: queue.Queue[Command] = field(default_factory=queue.Queue)
    """Inbox shared with other threads. Pass your own to submit before the engine exists."""


class Engine:
    """Must be created and run on the same thread that created its adapters."""

    def __init__(self, deps: EngineDeps) -> None:
        self._deps = deps
        self._tracker = deps.tracker
        self._commands = deps.commands
        self._presence = Presence(deps.sampling.away_after)
        self._session_start = deps.clock.now()
        self._paused_until: datetime | None = None
        self._attentive_until: datetime | None = None
        self._camera_error: str | None = None
        self._history = deps.episodes.all()
        self._offered_waits: dict[datetime, timedelta] = {}
        """The wait each open nudge offered, keyed by episode start, until it is answered."""
        """In-memory mirror of the log; it only changes when an episode closes."""

    def submit(self, command: Command) -> None:
        """Thread-safe. The command is applied on the engine thread, in order."""
        self._commands.put(command)

    def run(self) -> None:
        """Block until a `Stop` command arrives."""
        try:
            while True:
                interval = self.step()
                if not self._serve_commands_until(self._deps.clock.now() + interval):
                    return
        finally:
            self._deps.camera.close()

    def step(self) -> timedelta:
        """Run one sampling cycle and return how long to wait before the next one.

        The wait is planned after looking, so a frame that raises suspicion makes the
        very next frame come at the streaming rate instead of after a full idle interval.
        """
        now = self._deps.clock.now()
        self._handle(self._tracker.tick(now))
        image = self._grab(self._plan(now).mode)
        if image is not None:
            self._perceive(Frame(image, self._deps.clock.now()))
        self._publish()
        return self._plan(self._deps.clock.now()).interval

    def _plan(self, now: datetime) -> SamplingPlan:
        situation = Situation(
            self._tracker.phase,
            self._tracker.suspicion(now),
            paused=self._is_paused(now),
            away=self._presence.away,
            attentive=self._attentive_until is not None and now < self._attentive_until,
        )
        return plan_sampling(situation, self._deps.sampling)

    def apply(self, command: Command) -> bool:
        """Apply one command now. Returns False when the engine should stop."""
        now = self._deps.clock.now()
        match command:
            case LogCigarette():
                self._handle(self._tracker.log_cigarette(now))
            case Pause(duration=duration):
                self._paused_until = now + duration
            case Resume():
                self._paused_until = None
            case AnswerNudge(episode_started_at=started_at, answer=answer):
                target = self._offered_waits.pop(started_at, None)
                events = self._tracker.answer(started_at, answer, now, wait_target=target)
                self._handle(events)
            case Stop():
                return False
        self._publish()
        return True

    def process_pending(self) -> bool:
        """Apply every queued command without waiting. Returns False if one was `Stop`."""
        while True:
            try:
                command = self._commands.get_nowait()
            except queue.Empty:
                return True
            if not self.apply(command):
                return False

    def _serve_commands_until(self, deadline: datetime) -> bool:
        while (remaining := (deadline - self._deps.clock.now()).total_seconds()) > 0:
            try:
                command = self._commands.get(timeout=remaining)
            except queue.Empty:
                return True
            if not self.apply(command):
                return False
        return True

    def _grab(self, mode: CaptureMode) -> Image | None:
        try:
            image = self._deps.camera.grab(mode)
        except CameraUnavailableError as error:
            if self._camera_error != str(error):
                log.warning("Camera unavailable: %s", error)
            self._camera_error = str(error)
            return None
        self._camera_error = None
        return image

    def _perceive(self, frame: Frame) -> None:
        perception = self._deps.perception.perceive(frame)
        scene = perception.scene
        self._presence.update(scene.someone_visible)
        if scene.hand_near_face():
            self._attentive_until = frame.at + self._deps.sampling.attention
        log.debug(
            "frame: face=%s hands=%d near_face=%s cues=%s",
            scene.face is not None,
            len(scene.hands),
            scene.hand_near_face(),
            [(o.cue.value, round(o.confidence, 2)) for o in perception.observations],
        )
        for observation in perception.observations:
            self._handle(self._tracker.observe(observation))

    def _handle(self, events: Iterable[TrackerEvent]) -> None:
        for event in events:
            match event:
                case EpisodeOpened(started_at=started_at):
                    self._nudge(started_at)
                case EpisodeClosed(episode=episode):
                    self._deps.episodes.add(episode)
                    self._history.append(episode)
                    log.info("Episode closed: %s", episode.outcome)
                case EpisodeResumed(postponed_for=postponed_for):
                    log.info("Smoking resumed after waiting %s", postponed_for)

    def _nudge(self, started_at: datetime) -> None:
        now = self._deps.clock.now()
        stats = self._summary(now).stats
        text = nudge_text(stats, now, self._deps.language, window=self._deps.wait)
        self._offered_waits = {started_at: text.wait_for}

        def on_answer(answer: Answer) -> None:
            self.submit(AnswerNudge(started_at, answer))

        self._deps.notifier.nudge(text, on_answer)

    def _summary(self, now: datetime) -> Summary:
        return summarize(self._history, now=now, session_start=self._session_start)

    def _is_paused(self, now: datetime) -> bool:
        if self._paused_until is not None and now >= self._paused_until:
            self._paused_until = None
        return self._paused_until is not None

    def _publish(self) -> None:
        now = self._deps.clock.now()
        status = Status(
            at=now,
            phase=self._tracker.phase,
            summary=self._summary(now),
            paused_until=self._paused_until,
            camera_error=self._camera_error,
        )
        self._deps.on_status(status)
