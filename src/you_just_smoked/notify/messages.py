"""User-facing text. Encouraging, never shaming: the goal is a little more time, not guilt."""

from __future__ import annotations

import locale
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from you_just_smoked.domain.stats import next_milestone

if TYPE_CHECKING:
    from you_just_smoked.domain.stats import Stats

LANGUAGES = ("en", "it")

_TEXT: dict[str, dict[str, str]] = {
    "en": {
        "title_last": "Your last one was {ago} ago",
        "title_first": "About to smoke?",
        "body_counts": "{today} today. Can you make it to {goal}?",
        "body_first": "Even waiting a few minutes counts.",
        "wait": "I'll wait",
        "smoking": "Smoking anyway",
        "false_alarm": "Not smoking",
        "status_last": "Last: {ago} ago",
        "status_none": "No cigarettes logged",
        "status_today": "Today: {today}",
        "status_resisted": "Resisted: {resisted}",
        "status_held_off": "Held off: {held_off}",
        "status_paused": "Paused",
        "status_camera": "Camera unavailable",
        "menu_log": "I just smoked",
        "menu_pause": "Pause for 1 hour",
        "menu_resume": "Resume",
        "menu_quit": "Quit",
    },
    "it": {
        "title_last": "L'ultima è stata {ago} fa",
        "title_first": "Stai per fumare?",
        "body_counts": "Oggi sono {today}. Arrivi a {goal}?",
        "body_first": "Anche aspettare qualche minuto conta.",
        "wait": "Aspetto",
        "smoking": "Fumo lo stesso",
        "false_alarm": "Non sto fumando",
        "status_last": "Ultima: {ago} fa",
        "status_none": "Nessuna sigaretta registrata",
        "status_today": "Oggi: {today}",
        "status_resisted": "Resistite: {resisted}",
        "status_held_off": "Tempo guadagnato: {held_off}",
        "status_paused": "In pausa",
        "status_camera": "Webcam non disponibile",
        "menu_log": "Ho appena fumato",
        "menu_pause": "Pausa per 1 ora",
        "menu_resume": "Riprendi",
        "menu_quit": "Esci",
    },
}


@dataclass(frozen=True, slots=True)
class NudgeText:
    title: str
    body: str
    wait: str
    smoking: str
    false_alarm: str


def resolve_language(preference: str) -> str:
    """Map a config value ("auto", "en", "it") to a supported language."""
    if preference in LANGUAGES:
        return preference
    name = (locale.getlocale()[0] or "").lower()
    return "it" if name.startswith("it") else "en"


def nudge_text(stats: Stats, now: datetime, language: str) -> NudgeText:
    text = _TEXT[language]
    elapsed = stats.since_last(now)
    if elapsed is None:
        title, body = text["title_first"], text["body_first"]
    else:
        title = text["title_last"].format(ago=format_duration(elapsed))
        goal = format_duration(next_milestone(elapsed))
        body = text["body_counts"].format(today=stats.today, goal=goal)
    return NudgeText(title, body, text["wait"], text["smoking"], text["false_alarm"])


def status_lines(stats: Stats, now: datetime, language: str) -> list[str]:
    text = _TEXT[language]
    elapsed = stats.since_last(now)
    lines = [
        text["status_last"].format(ago=format_duration(elapsed))
        if elapsed is not None
        else text["status_none"],
        text["status_today"].format(today=stats.today),
    ]
    if stats.resisted_today:
        lines.append(text["status_resisted"].format(resisted=stats.resisted_today))
    if stats.held_off_today:
        lines.append(text["status_held_off"].format(held_off=format_duration(stats.held_off_today)))
    return lines


def phrase(key: str, language: str) -> str:
    """A fixed piece of interface text, such as a menu label."""
    return _TEXT[language][key]


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
