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


def plan_sampling(
    phase: Phase,
    suspicion: float,
    *,
    paused: bool,
    away: bool,
    settings: SamplingSettings,
) -> SamplingPlan:
    if paused or phase is Phase.REFRACTORY:
        return SamplingPlan(CaptureMode.OFF, settings.active_interval)
    if suspicion >= settings.stream_above:
        return SamplingPlan(CaptureMode.STREAM, settings.stream_interval)
    if phase in (Phase.ACTIVE, Phase.POSTPONED):
        return SamplingPlan(CaptureMode.SNAPSHOT, settings.active_interval)
    if away:
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
