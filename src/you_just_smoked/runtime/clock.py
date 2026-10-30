from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """The current time, timezone-aware, in the local time zone."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now().astimezone()
