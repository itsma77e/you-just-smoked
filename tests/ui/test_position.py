from pathlib import Path

from you_just_smoked.ui.position import PositionStore


def test_round_trip(tmp_path: Path) -> None:
    store = PositionStore(tmp_path / "ui" / "widget.json")
    assert store.load() is None
    store.save(120, -40)
    assert store.load() == (120, -40)


def test_corrupt_file_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "widget.json"
    path.write_text("{not json", encoding="utf-8")
    assert PositionStore(path).load() is None
