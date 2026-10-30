"""Interface text. To add a language, copy `en.py`, translate it and register it below."""

from __future__ import annotations

import locale
from datetime import timedelta
from types import MappingProxyType

from you_just_smoked.i18n import en, it

CATALOGS = MappingProxyType({"en": en.STRINGS, "it": it.STRINGS})
LANGUAGES = tuple(CATALOGS)
TIP_COUNT = 6


def resolve_language(preference: str) -> str:
    """Map a config value ("auto", "en", "it", ...) to a supported language."""
    if preference in CATALOGS:
        return preference
    name = (locale.getlocale()[0] or "").lower()
    return next((code for code in LANGUAGES if name.startswith(code)), "en")


def text(key: str, language: str, **values: object) -> str:
    return CATALOGS[language][key].format(**values)


def format_duration(duration: timedelta) -> str:
    """Compact and language-neutral: "45 min", "1 h", "1 h 20 min", "2 d 3 h"."""
    minutes = int(duration.total_seconds() // 60)
    days, minutes = divmod(minutes, 24 * 60)
    hours, minutes = divmod(minutes, 60)
    if days:
        return f"{days} d {hours} h" if hours else f"{days} d"
    if hours:
        return f"{hours} h {minutes} min" if minutes else f"{hours} h"
    return f"{minutes} min"
