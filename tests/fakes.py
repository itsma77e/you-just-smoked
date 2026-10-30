"""In-memory stand-ins for the engine's ports."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta

import numpy as np

from you_just_smoked.domain.cues import Cue, CueObservation
from you_just_smoked.domain.episode import Answer, Episode
from you_just_smoked.domain.sampling import CaptureMode
from you_just_smoked.notify.base import AnswerCallback
from you_just_smoked.notify.messages import NudgeText
from you_just_smoked.perception.frame import Frame, Image
from you_just_smoked.perception.pipeline import Perception
from you_just_smoked.perception.scene import Scene
from you_just_smoked.runtime.ports import CameraUnavailableError

from factories import T0, face


class FakeClock:
    def __init__(self, start: datetime = T0) -> None:
        self.current = start

    def now(self) -> datetime:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)


class FakeCamera:
    def __init__(self) -> None:
        self.modes: list[CaptureMode] = []
        self.broken = False
        self.closed = False

    def grab(self, mode: CaptureMode) -> Image | None:
        self.modes.append(mode)
        if mode is CaptureMode.OFF:
            return None
        if self.broken:
            raise CameraUnavailableError("unplugged")
        return np.zeros((4, 4, 3), dtype=np.uint8)

    def close(self) -> None:
        self.closed = True


class ScriptedPerceiver:
    """Sees the queued cues, one batch per frame; an empty scene once the script runs out."""

    def __init__(self) -> None:
        self.script: deque[list[Cue]] = deque()

    def show(self, *cues: Cue) -> None:
        self.script.append(list(cues))

    def perceive(self, frame: Frame) -> Perception:
        if not self.script:
            return Perception(Scene(), [])
        cues = self.script.popleft()
        observations = [CueObservation(cue, 1.0, frame.at) for cue in cues]
        return Perception(Scene(face=face()), observations)


class InMemoryEpisodes:
    def __init__(self) -> None:
        self.episodes: list[Episode] = []

    def add(self, episode: Episode) -> None:
        self.episodes.append(episode)

    def ended_since(self, moment: datetime) -> list[Episode]:
        return [e for e in self.episodes if e.ended_at >= moment]

    def last_cigarette_at(self) -> datetime | None:
        smoked = [e.ended_at for e in self.episodes if e.counts_as_cigarette]
        return max(smoked, default=None)


class RecordingNotifier:
    def __init__(self) -> None:
        self.nudges: list[tuple[NudgeText, AnswerCallback]] = []

    def nudge(self, text: NudgeText, on_answer: AnswerCallback) -> None:
        self.nudges.append((text, on_answer))

    def answer_last(self, answer: Answer) -> None:
        self.nudges[-1][1](answer)

    def close(self) -> None:
        pass
