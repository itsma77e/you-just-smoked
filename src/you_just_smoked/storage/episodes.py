"""Episode repository. Times are stored as UTC ISO-8601 strings, which sort correctly."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from you_just_smoked.domain.cues import Cue
from you_just_smoked.domain.episode import Answer, Episode, Outcome

if TYPE_CHECKING:
    import sqlite3

_COLUMNS = "started_at, ended_at, outcome, trigger, answer, postponed_seconds"


class EpisodeRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._db = connection

    def add(self, episode: Episode) -> None:
        postponed = episode.postponed_for.total_seconds() if episode.postponed_for else None
        with self._db:
            self._db.execute(
                f"INSERT INTO episodes ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    _encode(episode.started_at),
                    _encode(episode.ended_at),
                    episode.outcome.value,
                    episode.trigger.value if episode.trigger else None,
                    episode.answer.value if episode.answer else None,
                    postponed,
                ),
            )

    def all(self) -> list[Episode]:
        rows = self._db.execute(f"SELECT {_COLUMNS} FROM episodes ORDER BY ended_at")
        return [_decode_row(row) for row in rows]


def _encode(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return moment.astimezone(UTC).isoformat(timespec="milliseconds")


def _decode(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _decode_row(row: tuple[str, str, str, str | None, str | None, float | None]) -> Episode:
    started, ended, outcome, trigger, answer, postponed = row
    return Episode(
        started_at=_decode(started),
        ended_at=_decode(ended),
        outcome=Outcome(outcome),
        trigger=Cue(trigger) if trigger else None,
        answer=Answer(answer) if answer else None,
        postponed_for=timedelta(seconds=postponed) if postponed is not None else None,
    )
