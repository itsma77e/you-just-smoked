"""A smoking episode: from the first sign to the last puff, counted once."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from you_just_smoked.domain.cues import Cue


class Outcome(StrEnum):
    SMOKED = "smoked"
    RESISTED = "resisted"
    """The nudge was accepted and no smoking followed."""

    FALSE_ALARM = "false_alarm"
    """Kept as a label for calibration, never counted as a cigarette."""


class Answer(StrEnum):
    """What the user replied to the nudge."""

    WAIT = "wait"
    SMOKING = "smoking"
    FALSE_ALARM = "false_alarm"


@dataclass(frozen=True, slots=True)
class Episode:
    started_at: datetime
    ended_at: datetime
    outcome: Outcome
    trigger: Cue | None
    """The cue that contributed most to opening the episode. None when logged by hand."""

    answer: Answer | None = None
    postponed_for: timedelta | None = None
    """How long the user held off after choosing to wait, if they then smoked."""

    wait_target: timedelta | None = None
    """The wait the user accepted ("make it to 30 min" from 16 min is 14 min)."""

    @property
    def counts_as_cigarette(self) -> bool:
        return self.outcome is Outcome.SMOKED

    @property
    def wait_succeeded(self) -> bool | None:
        """Whether an accepted wait was seen through; None if no wait was accepted."""
        if self.answer is not Answer.WAIT or self.wait_target is None:
            return None
        if self.outcome is Outcome.RESISTED:
            return True
        return self.postponed_for is not None and self.postponed_for >= self.wait_target
