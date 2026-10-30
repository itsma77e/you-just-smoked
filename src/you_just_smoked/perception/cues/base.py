from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from you_just_smoked.domain.cues import CueObservation
    from you_just_smoked.perception.frame import Frame
    from you_just_smoked.perception.scene import Scene


class CueDetector(Protocol):
    def detect(self, frame: Frame, scene: Scene) -> list[CueObservation]:
        """Return what this detector sees in one frame. Must be fast and side-effect free."""
        ...

    def close(self) -> None:
        """Release any model held by the detector."""
        ...


def closeness(distance: float, reach: float) -> float:
    """1.0 when touching, falling linearly to 0.0 at `reach`."""
    if reach <= 0:
        return 0.0
    return max(0.0, 1.0 - distance / reach)
