"""The episode state machine. Many cues in, one episode and at most one nudge out.

    IDLE ──evidence ≥ threshold──▶ ACTIVE ──quiet──▶ REFRACTORY ──time──▶ IDLE
                                     │  ▲
                              "wait" │  │ consumption evidence ≥ threshold
                                     ▼  │
                                  POSTPONED ──quiet──▶ IDLE (resisted)

Only the IDLE → ACTIVE transition emits `EpisodeOpened`, so a nudge cannot be
sent twice for the same cigarette. Every other cue just refines the open episode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

from you_just_smoked.domain.cues import Cue, CueObservation
from you_just_smoked.domain.episode import Answer, Episode, Outcome
from you_just_smoked.domain.events import (
    EpisodeClosed,
    EpisodeOpened,
    EpisodeResumed,
    TrackerEvent,
)
from you_just_smoked.domain.evidence import Evidence, EvidenceSettings


class Phase(StrEnum):
    IDLE = "idle"
    ACTIVE = "active"
    POSTPONED = "postponed"
    REFRACTORY = "refractory"
    """Right after an episode: cues are ignored so one cigarette is never counted twice."""


@dataclass(frozen=True, slots=True)
class TrackerSettings:
    threshold: float = 1.0
    quiet_period: timedelta = timedelta(minutes=6)
    """How long without any cue before an open episode is considered over."""

    refractory_period: timedelta = timedelta(minutes=5)
    evidence: EvidenceSettings = field(default_factory=EvidenceSettings)


@dataclass(slots=True)
class _OpenEpisode:
    started_at: datetime
    trigger: Cue | None
    last_cue_at: datetime
    answer: Answer | None = None
    postponed_at: datetime | None = None
    postponed_for: timedelta | None = None
    wait_target: timedelta | None = None


class EpisodeTracker:
    def __init__(self, settings: TrackerSettings | None = None) -> None:
        self._settings = settings or TrackerSettings()
        self._watch = Evidence(self._settings.evidence)
        consumption = frozenset(cue for cue in Cue if cue.is_consumption)
        self._relapse = Evidence(self._settings.evidence, cues=consumption)
        self._phase = Phase.IDLE
        self._open: _OpenEpisode | None = None
        self._refractory_until: datetime | None = None

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def open_episode_started_at(self) -> datetime | None:
        return self._open.started_at if self._open else None

    def suspicion(self, at: datetime) -> float:
        """How close the current evidence is to the threshold, where 1.0 means reached."""
        match self._phase:
            case Phase.IDLE:
                return self._watch.value(at) / self._settings.threshold
            case Phase.POSTPONED:
                return self._relapse.value(at) / self._settings.threshold
            case _:
                return 0.0

    def observe(self, observation: CueObservation) -> list[TrackerEvent]:
        match self._phase:
            case Phase.IDLE:
                return self._observe_idle(observation)
            case Phase.ACTIVE:
                assert self._open is not None
                self._open.last_cue_at = observation.at
            case Phase.POSTPONED:
                return self._observe_postponed(observation)
            case Phase.REFRACTORY:
                pass
        return []

    def tick(self, now: datetime) -> list[TrackerEvent]:
        """Advance time-based transitions. Call it regularly, also when no frame was taken."""
        quiet = self._settings.quiet_period
        match self._phase:
            case Phase.ACTIVE:
                assert self._open is not None
                if now - self._open.last_cue_at >= quiet:
                    return [self._close(Outcome.SMOKED, self._open.last_cue_at, now)]
            case Phase.POSTPONED:
                assert self._open is not None
                if now - self._open.last_cue_at >= quiet:
                    return [self._close(Outcome.RESISTED, self._open.last_cue_at, now)]
            case Phase.REFRACTORY:
                assert self._refractory_until is not None
                if now >= self._refractory_until:
                    self._enter_idle()
            case Phase.IDLE:
                pass
        return []

    def answer(
        self,
        started_at: datetime,
        answer: Answer,
        now: datetime,
        *,
        wait_target: timedelta | None = None,
    ) -> list[TrackerEvent]:
        """Apply the user's reply to the nudge. Stale or repeated replies are ignored.

        `wait_target` is the wait the nudge offered, recorded when the user accepts it.
        """
        episode = self._open
        if episode is None or episode.started_at != started_at or episode.answer is not None:
            return []
        episode.answer = answer
        match answer:
            case Answer.WAIT:
                episode.wait_target = wait_target
                episode.postponed_at = now
                episode.last_cue_at = now
                self._relapse.reset()
                self._phase = Phase.POSTPONED
            case Answer.SMOKING:
                pass
            case Answer.FALSE_ALARM:
                return [self._close(Outcome.FALSE_ALARM, now, now)]
        return []

    def log_cigarette(self, now: datetime) -> list[TrackerEvent]:
        """The user says they just smoked. Closes the open episode or records a new one."""
        match self._phase:
            case Phase.IDLE:
                self._open = _OpenEpisode(started_at=now, trigger=None, last_cue_at=now)
            case Phase.POSTPONED:
                assert self._open is not None
                assert self._open.postponed_at is not None
                self._open.postponed_for = now - self._open.postponed_at
            case Phase.ACTIVE:
                pass
            case Phase.REFRACTORY:
                return []
        return [self._close(Outcome.SMOKED, now, now)]

    def _observe_idle(self, observation: CueObservation) -> list[TrackerEvent]:
        self._watch.add(observation)
        if self._watch.value(observation.at) < self._settings.threshold:
            return []
        started_at = self._watch.since or observation.at
        trigger = self._watch.strongest_cue()
        self._open = _OpenEpisode(started_at, trigger, last_cue_at=observation.at)
        self._phase = Phase.ACTIVE
        return [EpisodeOpened(started_at, trigger)]

    def _observe_postponed(self, observation: CueObservation) -> list[TrackerEvent]:
        assert self._open is not None
        assert self._open.postponed_at is not None
        self._open.last_cue_at = observation.at
        self._relapse.add(observation)
        if self._relapse.value(observation.at) < self._settings.threshold:
            return []
        postponed_for = observation.at - self._open.postponed_at
        self._open.postponed_for = postponed_for
        self._phase = Phase.ACTIVE
        return [EpisodeResumed(self._open.started_at, postponed_for)]

    def _close(self, outcome: Outcome, ended_at: datetime, now: datetime) -> EpisodeClosed:
        assert self._open is not None
        episode = Episode(
            started_at=self._open.started_at,
            ended_at=max(ended_at, self._open.started_at),
            outcome=outcome,
            trigger=self._open.trigger,
            answer=self._open.answer,
            postponed_for=self._open.postponed_for,
            wait_target=self._open.wait_target,
        )
        if outcome is Outcome.RESISTED:
            self._enter_idle()
        else:
            self._enter_refractory(now)
        return EpisodeClosed(episode)

    def _enter_idle(self) -> None:
        self._phase = Phase.IDLE
        self._open = None
        self._refractory_until = None
        self._watch.reset()
        self._relapse.reset()

    def _enter_refractory(self, now: datetime) -> None:
        self._enter_idle()
        self._phase = Phase.REFRACTORY
        self._refractory_until = now + self._settings.refractory_period
