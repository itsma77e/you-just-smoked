from collections.abc import Iterator

import pytest

from you_just_smoked.capture.camera import CameraSettings
from you_just_smoked.capture.isolated import IsolatedCamera
from you_just_smoked.domain.sampling import CaptureMode
from you_just_smoked.runtime.ports import CameraUnavailableError

from fakes import StubCamera


@pytest.fixture
def camera() -> Iterator[IsolatedCamera]:
    isolated = IsolatedCamera(CameraSettings(), factory=StubCamera, recycle_after=3)
    yield isolated
    isolated.close()


def test_snapshots_come_back_from_the_helper(camera: IsolatedCamera) -> None:
    image = camera.grab(CaptureMode.SNAPSHOT)
    assert image is not None
    assert image.shape == (4, 4, 3)
    assert int(image[0, 0, 0]) == 7


def test_helper_is_restarted_after_enough_opens(camera: IsolatedCamera) -> None:
    for _ in range(4):
        camera.grab(CaptureMode.SNAPSHOT)
    assert camera.restarts == 2


def test_streaming_opens_once(camera: IsolatedCamera) -> None:
    for _ in range(5):
        camera.grab(CaptureMode.STREAM)
    assert camera.restarts == 1


def test_off_without_a_helper_starts_nothing(camera: IsolatedCamera) -> None:
    assert camera.grab(CaptureMode.OFF) is None
    assert camera.restarts == 0


def test_camera_errors_reach_the_engine() -> None:
    broken = IsolatedCamera(CameraSettings(index=99), factory=StubCamera)
    try:
        with pytest.raises(CameraUnavailableError, match="no such camera"):
            broken.grab(CaptureMode.SNAPSHOT)
    finally:
        broken.close()
