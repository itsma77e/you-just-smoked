"""When to look. The camera is off most of the time; it only streams while something is up.

Rolling takes a minute or two, so a snapshot every few seconds is enough to
notice it. Once a cue shows up we stream briefly to confirm or dismiss it, then
go back to sleep.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from you_just_smoked.domain.tracker import Phase


class CaptureMode(StrEnum):
    OFF = "off"
    SNAPSHOT = "snapshot"
    """Open the camera, grab a frame, release it."""

    STREAM = "stream"
    """Keep the camera open and sample at a steady rate."""


@dataclass(frozen=True, slots=True)
class SamplingPlan:
    mode: CaptureMode
    interval: timedelta


@dataclass(frozen=True, slots=True)
class SamplingSettings:
    idle_interval: timedelta = timedelta(seconds=15)
    stream_interval: timedelta = timedelta(milliseconds=500)
    active_interval: timedelta = timedelta(seconds=20)
    away_interval: timedelta = timedelta(seconds=60)
    stream_above: float = 0.15
    """Suspicion level (fraction of the threshold) that switches to streaming."""

    away_after: int = 3
    """Consecutive empty snapshots before assuming nobody is at the desk."""

    attention: timedelta = timedelta(seconds=20)
    """How long to stream after a hand comes near the face, so lighting up is not missed."""


@dataclass(frozen=True, slots=True)
class Situation:
    """What the engine knows right now that matters for when to look next."""

    phase: Phase
    suspicion: float
    paused: bool = False
    away: bool = False
    attentive: bool = False
    """A hand came near the face recently."""


def plan_sampling(now: Situation, settings: SamplingSettings) -> SamplingPlan:
    if now.paused or now.phase is Phase.REFRACTORY:
        return SamplingPlan(CaptureMode.OFF, settings.active_interval)
    watching = now.phase in (Phase.IDLE, Phase.POSTPONED)
    if now.suspicion >= settings.stream_above or (now.attentive and watching):
        return SamplingPlan(CaptureMode.STREAM, settings.stream_interval)
    if now.phase in (Phase.ACTIVE, Phase.POSTPONED):
        return SamplingPlan(CaptureMode.SNAPSHOT, settings.active_interval)
    if now.away:
        return SamplingPlan(CaptureMode.SNAPSHOT, settings.away_interval)
    return SamplingPlan(CaptureMode.SNAPSHOT, settings.idle_interval)


class Presence:
    """Tracks whether someone has been visible in recent frames."""

    def __init__(self, away_after: int) -> None:
        self._away_after = away_after
        self._empty_frames = 0

    @property
    def away(self) -> bool:
        return self._empty_frames >= self._away_after

    def update(self, someone_visible: bool) -> None:
        self._empty_frames = 0 if someone_visible else self._empty_frames + 1
