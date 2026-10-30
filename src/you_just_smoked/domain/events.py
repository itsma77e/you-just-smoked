"""What the tracker tells the rest of the app. Only `EpisodeOpened` ever leads to a nudge."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from you_just_smoked.domain.cues import Cue
from you_just_smoked.domain.episode import Episode


@dataclass(frozen=True, slots=True)
class EpisodeOpened:
    started_at: datetime
    trigger: Cue | None


@dataclass(frozen=True, slots=True)
class EpisodeResumed:
    """A postponed episode turned into smoking after all."""

    started_at: datetime
    postponed_for: timedelta


@dataclass(frozen=True, slots=True)
class EpisodeClosed:
    episode: Episode


TrackerEvent = EpisodeOpened | EpisodeResumed | EpisodeClosed
