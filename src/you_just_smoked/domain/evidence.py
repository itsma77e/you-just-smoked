"""Turns a stream of noisy cue observations into one number that fades over time.

A single glimpse of a lighter should not mean anything. A lighter, then a flame
near the face a few seconds later, should. Each observation adds
`weight * confidence` and the total halves every `half_life`, so only cues that
arrive close together can push it over the episode threshold.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from types import MappingProxyType

from you_just_smoked.domain.cues import Cue, CueObservation

_NEGLIGIBLE = 0.05


@dataclass(frozen=True, slots=True)
class EvidenceSettings:
    weights: Mapping[Cue, float] = field(
        default_factory=lambda: MappingProxyType(
            {
                Cue.ROLLING: 0.35,
                Cue.LIGHTER: 0.5,
                Cue.PACK: 0.4,
                Cue.CIGARETTE: 0.6,
                Cue.FLAME: 0.9,
                Cue.PUFF: 0.45,
            }
        )
    )
    half_life: timedelta = timedelta(seconds=45)
    min_spacing: timedelta = timedelta(seconds=5)
    """A cue counts at most once per spacing, so streaming faster does not inflate it."""


class Evidence:
    """Exponentially decaying sum of weighted cue observations."""

    def __init__(self, settings: EvidenceSettings, *, cues: frozenset[Cue] | None = None) -> None:
        self._settings = settings
        self._accepted = cues
        self._value = 0.0
        self._updated_at: datetime | None = None
        self._since: datetime | None = None
        self._contributions: dict[Cue, float] = {}
        self._last_counted: dict[Cue, datetime] = {}

    @property
    def since(self) -> datetime | None:
        """When the current run of evidence started, or None if there is none."""
        return self._since

    def add(self, observation: CueObservation) -> None:
        cue = observation.cue
        if self._accepted is not None and cue not in self._accepted:
            return
        last = self._last_counted.get(cue)
        if last is not None and observation.at - last < self._settings.min_spacing:
            return
        if self.value(observation.at) < _NEGLIGIBLE:
            self.reset()
            self._since = observation.at
        self._decay_to(observation.at)
        amount = self._settings.weights.get(cue, 0.0) * observation.confidence
        self._value += amount
        self._contributions[cue] = self._contributions.get(cue, 0.0) + amount
        self._last_counted[cue] = observation.at

    def value(self, at: datetime) -> float:
        if self._updated_at is None:
            return 0.0
        return self._value * self._decay_factor(at - self._updated_at)

    def strongest_cue(self) -> Cue | None:
        if not self._contributions:
            return None
        return max(self._contributions, key=self._contributions.__getitem__)

    def reset(self) -> None:
        self._value = 0.0
        self._updated_at = None
        self._since = None
        self._contributions.clear()
        self._last_counted.clear()

    def _decay_to(self, at: datetime) -> None:
        if self._updated_at is not None and at <= self._updated_at:
            return
        if self._updated_at is not None:
            factor = self._decay_factor(at - self._updated_at)
            self._value *= factor
            for cue in self._contributions:
                self._contributions[cue] *= factor
        self._updated_at = at

    def _decay_factor(self, elapsed: timedelta) -> float:
        if elapsed <= timedelta(0):
            return 1.0
        return float(0.5 ** (elapsed / self._settings.half_life))
