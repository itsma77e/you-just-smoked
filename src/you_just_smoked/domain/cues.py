"""The things we can see that suggest a cigarette is coming or happening."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Cue(StrEnum):
    ROLLING = "rolling"
    """Both hands working together in front of the body, as when rolling."""

    LIGHTER = "lighter"
    PACK = "pack"

    CIGARETTE = "cigarette"
    FLAME = "flame"
    """A small, bright, warm light source near the face or a hand."""

    PUFF = "puff"
    """A hand brought to the mouth holding something thin."""

    @property
    def is_consumption(self) -> bool:
        """True for cues that mean smoking is happening, not just being prepared."""
        return self in _CONSUMPTION


_CONSUMPTION = frozenset({Cue.CIGARETTE, Cue.FLAME, Cue.PUFF})


@dataclass(frozen=True, slots=True)
class CueObservation:
    cue: Cue
    confidence: float
    at: datetime

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")
