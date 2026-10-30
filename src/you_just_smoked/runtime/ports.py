"""What the engine needs from the outside world. Adapters and test fakes both satisfy these."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from you_just_smoked.domain.episode import Episode
    from you_just_smoked.domain.sampling import CaptureMode
    from you_just_smoked.perception.frame import Frame, Image
    from you_just_smoked.perception.pipeline import Perception


class CameraUnavailableError(RuntimeError):
    """The camera could not be opened or stopped delivering frames."""


class FrameSource(Protocol):
    def grab(self, mode: CaptureMode) -> Image | None: ...

    def close(self) -> None: ...


class Perceiver(Protocol):
    def perceive(self, frame: Frame) -> Perception: ...


class EpisodeLog(Protocol):
    def add(self, episode: Episode) -> None: ...

    def all(self) -> list[Episode]:
        """Every episode, oldest first."""
        ...
