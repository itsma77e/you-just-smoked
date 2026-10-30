"""The streak of waits seen through, with jollies that forgive a slip.

Every third successful wait earns a jolly. Smoking during a wait spends one
instead of breaking the streak; with no jolly left the streak starts over.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from you_just_smoked.domain.episode import Episode

JOLLY_EVERY = 3


@dataclass(frozen=True, slots=True)
class Streak:
    current: int = 0
    best: int = 0
    jollies: int = 0
    successes: int = 0
    """All successful waits ever, which is what earns jollies."""

    @property
    def to_next_jolly(self) -> int:
        return JOLLY_EVERY - self.successes % JOLLY_EVERY

    def after(self, succeeded: bool) -> Streak:
        if succeeded:
            successes = self.successes + 1
            current = self.current + 1
            earned = 1 if successes % JOLLY_EVERY == 0 else 0
            return Streak(current, max(self.best, current), self.jollies + earned, successes)
        if self.jollies:
            return replace(self, jollies=self.jollies - 1)
        return replace(self, current=0)


def streak(history: Iterable[Episode]) -> Streak:
    result = Streak()
    for episode in sorted(history, key=lambda e: e.ended_at):
        succeeded = episode.wait_succeeded
        if succeeded is not None:
            result = result.after(succeeded)
    return result
