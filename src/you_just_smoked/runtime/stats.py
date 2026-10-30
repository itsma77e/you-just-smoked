from __future__ import annotations

from typing import TYPE_CHECKING

from you_just_smoked.domain.stats import Stats, compute_stats

if TYPE_CHECKING:
    from datetime import datetime

    from you_just_smoked.runtime.ports import EpisodeLog


def load_stats(log: EpisodeLog, *, now: datetime, session_start: datetime) -> Stats:
    """Read just enough of the log to compute today's and this session's numbers."""
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return compute_stats(
        log.ended_since(min(midnight, session_start)),
        now=now,
        session_start=session_start,
        last_cigarette_at=log.last_cigarette_at(),
    )
