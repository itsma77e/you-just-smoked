"""Model files: pinned by URL and SHA-256, downloaded once into the user cache."""

from __future__ import annotations

import hashlib
import logging
import urllib.request
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

_CHUNK = 1 << 16


@dataclass(frozen=True, slots=True)
class ModelSpec:
    filename: str
    url: str
    sha256: str


HAND_LANDMARKER = ModelSpec(
    filename="hand_landmarker.task",
    url="https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
    sha256="fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1",
)

FACE_DETECTOR = ModelSpec(
    filename="blaze_face_short_range.tflite",
    url="https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite",
    sha256="b4578f35940bf5a1a655214a1cce5cab13eba73c1297cd78e1a04c2380b0152f",
)


class ModelIntegrityError(RuntimeError):
    pass


def ensure_model(spec: ModelSpec, directory: Path) -> Path:
    """Return the local path of `spec`, downloading and verifying it if needed."""
    path = directory / spec.filename
    if path.exists() and _sha256(path) == spec.sha256:
        return path

    directory.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".part")
    log.info("Downloading %s", spec.url)
    with urllib.request.urlopen(spec.url, timeout=60) as response, partial.open("wb") as out:
        while chunk := response.read(_CHUNK):
            out.write(chunk)

    actual = _sha256(partial)
    if actual != spec.sha256:
        partial.unlink(missing_ok=True)
        raise ModelIntegrityError(f"{spec.filename}: expected {spec.sha256}, got {actual}")
    partial.replace(path)
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()
