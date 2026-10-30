import pytest

from you_just_smoked.domain.sampling import (
    CaptureMode,
    Presence,
    SamplingSettings,
    Situation,
    plan_sampling,
)
from you_just_smoked.domain.tracker import Phase

SETTINGS = SamplingSettings()


STREAM = SETTINGS.stream_interval
ACTIVE = SETTINGS.active_interval
AWAY = SETTINGS.away_interval
IDLE = SETTINGS.idle_interval


@pytest.mark.parametrize(
    ("phase", "suspicion", "flags", "mode", "interval"),
    [
        (Phase.IDLE, 0.0, "", CaptureMode.SNAPSHOT, IDLE),
        (Phase.IDLE, 0.0, "away", CaptureMode.SNAPSHOT, AWAY),
        (Phase.IDLE, 0.5, "away", CaptureMode.STREAM, STREAM),
        (Phase.IDLE, 0.0, "attentive", CaptureMode.STREAM, STREAM),
        (Phase.ACTIVE, 0.0, "", CaptureMode.SNAPSHOT, ACTIVE),
        (Phase.ACTIVE, 0.0, "attentive", CaptureMode.SNAPSHOT, ACTIVE),
        (Phase.POSTPONED, 0.5, "", CaptureMode.STREAM, STREAM),
        (Phase.POSTPONED, 0.0, "attentive", CaptureMode.STREAM, STREAM),
        (Phase.REFRACTORY, 0.0, "attentive", CaptureMode.OFF, ACTIVE),
        (Phase.IDLE, 0.9, "paused", CaptureMode.OFF, ACTIVE),
    ],
)
def test_plan(
    phase: Phase, suspicion: float, flags: str, mode: CaptureMode, interval: object
) -> None:
    situation = Situation(
        phase,
        suspicion,
        paused="paused" in flags,
        away="away" in flags,
        attentive="attentive" in flags,
    )
    plan = plan_sampling(situation, SETTINGS)
    assert plan.mode is mode
    assert plan.interval == interval


def test_presence_needs_several_empty_frames() -> None:
    presence = Presence(away_after=2)
    presence.update(someone_visible=False)
    assert not presence.away
    presence.update(someone_visible=False)
    assert presence.away
    presence.update(someone_visible=True)
    assert not presence.away
