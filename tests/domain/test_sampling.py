import pytest

from you_just_smoked.domain.sampling import (
    CaptureMode,
    Presence,
    SamplingSettings,
    plan_sampling,
)
from you_just_smoked.domain.tracker import Phase

SETTINGS = SamplingSettings()


@pytest.mark.parametrize(
    ("phase", "suspicion", "paused", "away", "mode", "interval"),
    [
        (Phase.IDLE, 0.0, False, False, CaptureMode.SNAPSHOT, SETTINGS.idle_interval),
        (Phase.IDLE, 0.0, False, True, CaptureMode.SNAPSHOT, SETTINGS.away_interval),
        (Phase.IDLE, 0.5, False, True, CaptureMode.STREAM, SETTINGS.stream_interval),
        (Phase.ACTIVE, 0.0, False, False, CaptureMode.SNAPSHOT, SETTINGS.active_interval),
        (Phase.POSTPONED, 0.5, False, False, CaptureMode.STREAM, SETTINGS.stream_interval),
        (Phase.REFRACTORY, 0.0, False, False, CaptureMode.OFF, SETTINGS.active_interval),
        (Phase.IDLE, 0.9, True, False, CaptureMode.OFF, SETTINGS.active_interval),
    ],
)
def test_plan(
    phase: Phase,
    suspicion: float,
    paused: bool,
    away: bool,
    mode: CaptureMode,
    interval: object,
) -> None:
    plan = plan_sampling(phase, suspicion, paused=paused, away=away, settings=SETTINGS)
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
