"""Remembers where the user dragged the widget. Losing it is harmless, so errors are ignored."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)


class PositionStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> tuple[int, int] | None:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return int(data["x"]), int(data["y"])
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def save(self, x: int, y: int) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps({"x": x, "y": y}), encoding="utf-8")
        except OSError as error:
            log.debug("Could not save the widget position: %s", error)
