"""Messages other threads send to the engine. They are applied in order on the engine thread."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from you_just_smoked.domain.episode import Answer


@dataclass(frozen=True, slots=True)
class LogCigarette:
    pass


@dataclass(frozen=True, slots=True)
class Pause:
    duration: timedelta


@dataclass(frozen=True, slots=True)
class Resume:
    pass


@dataclass(frozen=True, slots=True)
class AnswerNudge:
    episode_started_at: datetime
    answer: Answer


@dataclass(frozen=True, slots=True)
class Stop:
    pass


Command = LogCigarette | Pause | Resume | AnswerNudge | Stop
