from collections.abc import Iterator
from datetime import timedelta, timezone
from pathlib import Path

import pytest

from you_just_smoked.domain.cues import Cue
from you_just_smoked.domain.episode import Answer, Episode, Outcome
from you_just_smoked.storage.database import connect
from you_just_smoked.storage.episodes import EpisodeRepository

from factories import at


@pytest.fixture
def repository(tmp_path: Path) -> Iterator[EpisodeRepository]:
    connection = connect(tmp_path / "data" / "episodes.sqlite3")
    yield EpisodeRepository(connection)
    connection.close()


def test_round_trips_every_field(repository: EpisodeRepository) -> None:
    episode = Episode(
        started_at=at(0),
        ended_at=at(minutes=5),
        outcome=Outcome.SMOKED,
        trigger=Cue.ROLLING,
        answer=Answer.WAIT,
        postponed_for=timedelta(minutes=3, seconds=20),
    )
    repository.add(episode)
    assert repository.ended_since(at(0)) == [episode]


def test_round_trips_a_manual_entry(repository: EpisodeRepository) -> None:
    episode = Episode(at(0), at(0), Outcome.SMOKED, trigger=None)
    repository.add(episode)
    assert repository.ended_since(at(0)) == [episode]


def test_filters_by_end_time_across_time_zones(repository: EpisodeRepository) -> None:
    rome = timezone(timedelta(hours=1))
    repository.add(Episode(at(0), at(minutes=1), Outcome.SMOKED, Cue.FLAME))
    repository.add(Episode(at(0), at(minutes=10), Outcome.SMOKED, Cue.FLAME))
    since = at(minutes=5).astimezone(rome)
    assert [e.ended_at for e in repository.ended_since(since)] == [at(minutes=10)]


def test_last_cigarette_ignores_other_outcomes(repository: EpisodeRepository) -> None:
    assert repository.last_cigarette_at() is None
    repository.add(Episode(at(0), at(minutes=1), Outcome.SMOKED, Cue.FLAME))
    repository.add(Episode(at(0), at(minutes=9), Outcome.RESISTED, Cue.FLAME))
    assert repository.last_cigarette_at() == at(minutes=1)


def test_rejects_naive_timestamps(repository: EpisodeRepository) -> None:
    naive = at(0).replace(tzinfo=None)
    with pytest.raises(ValueError, match="timezone-aware"):
        repository.add(Episode(naive, naive, Outcome.SMOKED, None))


def test_migrations_are_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "episodes.sqlite3"
    connect(path).close()
    connection = connect(path)
    assert connection.execute("PRAGMA user_version").fetchone() == (1,)
    connection.close()
