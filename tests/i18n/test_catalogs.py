from datetime import timedelta
from string import Formatter

import pytest

from you_just_smoked.i18n import (
    CATALOGS,
    LANGUAGES,
    TIP_COUNT,
    format_duration,
    resolve_language,
    text,
)


def placeholders(template: str) -> set[str]:
    return {name for _, name, _, _ in Formatter().parse(template) if name}


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_language_has_the_same_keys_and_placeholders(language: str) -> None:
    english = CATALOGS["en"]
    catalog = CATALOGS[language]
    assert catalog.keys() == english.keys()
    for key, template in english.items():
        assert placeholders(catalog[key]) == placeholders(template), key


def test_tips_are_all_there() -> None:
    for language in LANGUAGES:
        assert all(text(f"tip_{i}", language) for i in range(TIP_COUNT))


def test_explicit_language_wins_over_the_system_locale() -> None:
    assert resolve_language("it") == "it"
    assert resolve_language("auto") in LANGUAGES


@pytest.mark.parametrize(
    ("duration", "expected"),
    [
        (timedelta(seconds=59), "0 min"),
        (timedelta(minutes=45), "45 min"),
        (timedelta(hours=1), "1 h"),
        (timedelta(hours=1, minutes=20), "1 h 20 min"),
        (timedelta(days=2), "2 d"),
        (timedelta(days=2, hours=3, minutes=10), "2 d 3 h"),
    ],
)
def test_format_duration(duration: timedelta, expected: str) -> None:
    assert format_duration(duration) == expected
