"""Optional TOML configuration. Every key has a default; unknown keys are an error, not a typo
that silently does nothing. See `docs/configuration.md` for the full list.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any, TypeVar

from you_just_smoked.capture.camera import CameraSettings
from you_just_smoked.domain.sampling import SamplingSettings
from you_just_smoked.domain.stats import WaitWindow
from you_just_smoked.domain.tracker import TrackerSettings

T = TypeVar("T")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ObjectsConfig:
    model: Path
    min_score: float = 0.5


@dataclass(frozen=True, slots=True)
class Config:
    language: str = "auto"
    camera: CameraSettings = field(default_factory=CameraSettings)
    sampling: SamplingSettings = field(default_factory=SamplingSettings)
    tracker: TrackerSettings = field(default_factory=TrackerSettings)
    wait: WaitWindow = field(default_factory=WaitWindow)
    """How far away the goal offered by the nudge may be."""

    sound: bool = True

    objects: ObjectsConfig | None = None


def load_config(path: Path) -> Config:
    if not path.exists():
        return Config()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{path}: {error}") from error
    return parse_config(data)


def parse_config(data: dict[str, Any]) -> Config:
    root = _Table(data, "")
    camera = root.table("camera")
    sampling = root.table("sampling")
    episode = root.table("episode")
    nudge = root.table("nudge")
    objects = root.table("objects")
    config = Config(
        language=root.get("language", str, "auto"),
        camera=CameraSettings(
            index=camera.get("index", int, 0),
            width=camera.get("width", int, None),
            height=camera.get("height", int, None),
            keep_open=camera.get("keep_open", bool, False),
        ),
        sampling=SamplingSettings(
            idle_interval=_seconds(sampling.get("idle_seconds", float, 15)),
            stream_interval=_seconds(sampling.get("stream_seconds", float, 0.5)),
            active_interval=_seconds(sampling.get("active_seconds", float, 20)),
            away_interval=_seconds(sampling.get("away_seconds", float, 60)),
        ),
        tracker=TrackerSettings(
            threshold=episode.get("threshold", float, 1.0),
            quiet_period=_minutes(episode.get("quiet_minutes", float, 6)),
            refractory_period=_minutes(episode.get("refractory_minutes", float, 5)),
        ),
        wait=_wait_window(nudge),
        sound=nudge.get("sound", bool, True),
        objects=_objects(objects),
    )
    for table in (root, camera, sampling, episode, nudge, objects):
        table.reject_unknown()
    return config


def _wait_window(table: _Table) -> WaitWindow:
    shortest = table.get("min_wait_minutes", float, 5)
    longest = table.get("max_wait_minutes", float, 25)
    try:
        return WaitWindow(_minutes(shortest), _minutes(longest))
    except ValueError as error:
        raise ConfigError(f"[nudge] {error}") from error


def _objects(table: _Table) -> ObjectsConfig | None:
    model = table.get("model", str, None)
    min_score = table.get("min_score", float, 0.5)
    if model is None:
        return None
    return ObjectsConfig(Path(model).expanduser(), min_score)


class _Table:
    def __init__(self, data: dict[str, Any], name: str) -> None:
        self._data = data
        self._name = name
        self._seen: set[str] = set()

    def table(self, key: str) -> _Table:
        value = self._take(key, {})
        if not isinstance(value, dict):
            raise ConfigError(f"[{key}] must be a table")
        return _Table(value, key)

    def get(self, key: str, kind: type[T], default: T) -> T:
        value = self._take(key, default)
        if value is default:
            return default
        if kind is float and isinstance(value, int) and not isinstance(value, bool):
            value = float(value)
        if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
            raise ConfigError(f"{self._where(key)} must be {kind.__name__}, got {value!r}")
        return value

    def reject_unknown(self) -> None:
        unknown = set(self._data) - self._seen
        if unknown:
            raise ConfigError(f"unknown setting(s): {', '.join(sorted(map(self._where, unknown)))}")

    def _take(self, key: str, default: object) -> Any:
        self._seen.add(key)
        return self._data.get(key, default)

    def _where(self, key: str) -> str:
        return f"{self._name}.{key}" if self._name else key


def _seconds(value: float) -> timedelta:
    return timedelta(seconds=value)


def _minutes(value: float) -> timedelta:
    return timedelta(minutes=value)
