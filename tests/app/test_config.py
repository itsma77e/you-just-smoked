from datetime import timedelta
from pathlib import Path

import pytest

from you_just_smoked.app.config import Config, ConfigError, load_config, parse_config


def test_missing_file_gives_defaults(tmp_path: Path) -> None:
    assert load_config(tmp_path / "nope.toml") == Config()


def test_reads_every_section(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        """
        language = "it"

        [camera]
        index = 1
        keep_open = true

        [sampling]
        idle_seconds = 30

        [episode]
        threshold = 1.5
        quiet_minutes = 8

        [objects]
        model = "~/models/smoking.tflite"
        min_score = 0.6
        """,
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.language == "it"
    assert config.camera.index == 1
    assert config.camera.keep_open
    assert config.sampling.idle_interval == timedelta(seconds=30)
    assert config.tracker.threshold == 1.5
    assert config.tracker.quiet_period == timedelta(minutes=8)
    assert config.objects is not None
    assert config.objects.model.name == "smoking.tflite"
    assert config.objects.min_score == 0.6


def test_integers_are_accepted_where_floats_are_expected() -> None:
    assert parse_config({"episode": {"threshold": 2}}).tracker.threshold == 2.0


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"camera": {"idnex": 1}}, "camera.idnex"),
        ({"colour": "red"}, "colour"),
        ({"camera": {"index": "zero"}}, "camera.index must be int"),
        ({"camera": {"keep_open": 1}}, "camera.keep_open must be bool"),
        ({"camera": {"index": True}}, "camera.index must be int"),
        ({"camera": 3}, r"\[camera\] must be a table"),
    ],
)
def test_rejects_mistakes_loudly(data: dict[str, object], message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        parse_config(data)


def test_reports_invalid_toml(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text("language = ", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)
