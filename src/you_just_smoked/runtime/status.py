"""An immutable snapshot of the engine, published for the tray to read from its own thread."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from you_just_smoked.domain.stats import Stats
    from you_just_smoked.domain.tracker import Phase


@dataclass(frozen=True, slots=True)
class Status:
    at: datetime
    phase: Phase
    stats: Stats
    paused_until: datetime | None = None
    camera_error: str | None = None

    @property
    def paused(self) -> bool:
        return self.paused_until is not None and self.at < self.paused_until
