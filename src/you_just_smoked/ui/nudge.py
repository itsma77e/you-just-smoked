"""The nudge: slides in once per episode, and turns "I'll wait" into a small challenge.

    ASK ──wait──▶ COUNTDOWN ──time up──▶ CELEBRATE ──5 more──▶ COUNTDOWN
     │                │                       │
     └─smoking / no───┴──smoking──────────────┴──OK──▶ hidden

The countdown runs until the goal the nudge offered ("make it to 30 min?") and
keeps company: streak, the next badge, today against yesterday, the pace, tips.
"Hide" folds it into a tab on the screen edge; when time is up it chimes and
comes back by itself to celebrate.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

from you_just_smoked.domain.episode import Answer
from you_just_smoked.domain.tracker import Phase
from you_just_smoked.i18n import text
from you_just_smoked.ui import confetti, render, theme
from you_just_smoked.ui.controls import (
    PRIMARY,
    QUIET,
    SECONDARY,
    Box,
    ButtonStyle,
    PillButton,
    TextStyle,
)
from you_just_smoked.ui.sliding import SlidingCard
from you_just_smoked.ui.sound import Chime
from you_just_smoked.ui.tab import EdgeTab
from you_just_smoked.ui.viewmodel import celebration_line, companion_lines

if TYPE_CHECKING:
    import tkinter as tk
    from collections.abc import Callable

    from you_just_smoked.domain.summary import Summary
    from you_just_smoked.notify.base import AnswerCallback
    from you_just_smoked.notify.messages import NudgeText
    from you_just_smoked.runtime.status import Status

_W, _H = theme.NUDGE_WIDTH, theme.NUDGE_HEIGHT
_HALF = (_W - 40) / 2
_TITLE = TextStyle(15, weight="bold", wrap=_W - 32)
_BODY = TextStyle(10, theme.MUTED, wrap=_W - 32)
_COUNT_TITLE = TextStyle(13, weight="bold", wrap=_W - 144)
_COMPANION = TextStyle(10, theme.TEXT, wrap=_W - 144)
_CLOCK = TextStyle(16, theme.TEXT, "bold", "center")
_GOLD_HEADLINE = TextStyle(15, theme.GOLD, "bold", wrap=_W - 32)
_STREAK = TextStyle(11, theme.TEXT, "bold", wrap=_W - 32)
_AUTO_HIDE_S = 120
_EXTRA_S = 5 * 60
_COMPANION_EVERY_S = 10


@dataclass(frozen=True, slots=True)
class PopupActions:
    chime: Callable[[Chime], None]
    show_stats: Callable[[], None]
    computer_day: timedelta
    """Length of a day at the computer, for the pace line."""


class Stage(StrEnum):
    HIDDEN = "hidden"
    ASK = "ask"
    COUNTDOWN = "countdown"
    CELEBRATE = "celebrate"


_PREFIXES = {Stage.ASK: "ask", Stage.COUNTDOWN: "count", Stage.CELEBRATE: "party"}


class NudgePopup:
    def __init__(
        self,
        root: tk.Tk,
        language: str,
        anchor: Callable[[], tuple[int, int]],
        actions: PopupActions,
    ) -> None:
        """`anchor` returns where the popup's bottom-right corner should go."""
        self._card = SlidingCard(root, (_W, _H))
        self._surface = self._card.surface
        self._canvas = self._card.canvas
        self._tab = EdgeTab(root, on_open=self._reopen)
        self._language = language
        self._anchor = anchor
        self._actions = actions
        self.stage = Stage.HIDDEN
        """What the popup is showing; it may be off screen while a countdown runs."""
        self._summary: Summary | None = None
        self._goal: timedelta | None = None
        self._on_answer: AnswerCallback | None = None
        self._wait_s = self._round_s = self._gained_s = 0.0
        self._started = self._deadline = self._shown_at = 0.0
        self._now = datetime.now().astimezone()
        self._build()

    # Engine-facing ----------------------------------------------------------------------

    def ask(self, nudge: NudgeText, on_answer: AnswerCallback) -> None:
        self._on_answer = on_answer
        self._wait_s = nudge.wait_for.total_seconds()
        self._goal = nudge.goal
        self._gained_s = 0.0
        self._surface.text("ask-title", 16, 18, nudge.title, _TITLE)
        self._surface.text("ask-body", 16, 72, nudge.body, _BODY)
        for tag, box, style, label, answer in (
            ("ask-wait", Box(16, 126, _HALF, 34), PRIMARY, nudge.wait, Answer.WAIT),
            (
                "ask-smoke",
                Box(24 + _HALF, 126, _HALF, 34),
                SECONDARY,
                nudge.smoking,
                Answer.SMOKING,
            ),
            ("ask-false", Box(16, 168, _W - 32, 26), QUIET, nudge.false_alarm, Answer.FALSE_ALARM),
        ):
            self._canvas.delete(tag)
            self._button(tag, box, style, label, self._answer_handler(answer))
        self._switch(Stage.ASK)
        self._shown_at = time.monotonic()
        self._card.slide_in(self._anchor)
        self._actions.chime(Chime.NUDGE)

    def on_status(self, status: Status) -> None:
        """Lighting up during the challenge ends it quietly: no scolding."""
        self._summary = status.summary
        if self.stage is Stage.COUNTDOWN and status.phase is Phase.ACTIVE:
            self._hide()

    def tick(self, wall_clock: datetime) -> None:
        self._now = wall_clock
        now = time.monotonic()
        if self.stage is Stage.ASK and now - self._shown_at > _AUTO_HIDE_S:
            self._hide()
        elif self.stage is Stage.COUNTDOWN:
            self._draw_countdown(now)

    # Stages -----------------------------------------------------------------------------

    def _answer(self, answer: Answer) -> None:
        if self._on_answer is not None:
            self._on_answer(answer)
            self._on_answer = None
        if answer is Answer.WAIT:
            self._start_countdown(self._wait_s)
        else:
            self._hide()

    def _start_countdown(self, seconds: float) -> None:
        self._round_s = seconds
        self._started = time.monotonic()
        self._deadline = self._started + seconds
        title = text("challenge_title", self._language, minutes=math.ceil(seconds / 60))
        self._surface.text("count-title", 128, 22, title, _COUNT_TITLE)
        self._switch(Stage.COUNTDOWN)
        self._draw_countdown(self._started)

    def _draw_countdown(self, now: float) -> None:
        remaining = self._deadline - now
        if remaining <= 0:
            self._celebrate()
            return
        fraction = remaining / self._round_s
        self._tab.update(remaining, fraction)
        if not self._card.visible:
            return
        style = render.RingStyle(theme.GOLD, theme.TRACK, 8, theme.CARD)
        ring = render.ring(self._surface.px(96), fraction, style)
        self._surface.image("count-ring", ring, 16, 24)
        minutes, seconds = divmod(int(remaining + 0.999), 60)
        self._surface.text("count-clock", 64, 72, f"{minutes}:{seconds:02}", _CLOCK)
        self._surface.text("count-companion", 128, 56, self._companion_line(now), _COMPANION)

    def _celebrate(self) -> None:
        self._gained_s += self._round_s
        minutes = round(self._gained_s / 60)
        title = text("celebrate_title", self._language, minutes=minutes)
        self._surface.text("party-title", 16, 22, title, _GOLD_HEADLINE)
        if self._summary is not None:
            streak = celebration_line(self._summary, self._language)
            self._surface.text("party-streak", 16, 60, streak, _STREAK)
        self._switch(Stage.CELEBRATE)
        self._tab.hide()
        if not self._card.visible:
            self._card.slide_in(self._anchor)
        self._actions.chime(Chime.DONE)
        origin = (self._surface.px(_W / 2), self._surface.px(60))
        confetti.burst(self._canvas, origin, scale=self._surface.scale)

    def _companion_line(self, now: float) -> str:
        if self._summary is None:
            return ""
        lines = companion_lines(
            self._summary, self._now, self._language, self._goal, self._actions.computer_day
        )
        return lines[int((now - self._started) // _COMPANION_EVERY_S) % len(lines)]

    # Building, switching, hiding --------------------------------------------------------

    def _build(self) -> None:
        self._surface.text("party-body", 16, 90, text("celebrate_body", self._language), _BODY)
        stats, more = self._actions.show_stats, lambda: self._start_countdown(_EXTRA_S)
        for tag, box, style, key, action in (
            ("count-hide", Box(16, 156, 88, 32), SECONDARY, "challenge_hide", self._fold),
            ("count-stats", Box(112, 156, 96, 32), SECONDARY, "stats_button", stats),
            ("count-smoke", Box(216, 156, _W - 232, 32), QUIET, "smoking", self._hide),
            ("party-more", Box(16, 156, _HALF, 32), PRIMARY, "celebrate_more", more),
            (
                "party-done",
                Box(24 + _HALF, 156, _HALF, 32),
                SECONDARY,
                "celebrate_done",
                self._hide,
            ),
        ):
            self._button(tag, box, style, text(key, self._language), action)

    def _button(
        self, tag: str, box: Box, style: ButtonStyle, label: str, action: Callable[[], None]
    ) -> None:
        PillButton(self._surface, tag, box, style, action).draw(label)

    def _answer_handler(self, answer: Answer) -> Callable[[], None]:
        return lambda: self._answer(answer)

    def _switch(self, stage: Stage) -> None:
        """Show only the items of `stage`; items are grouped by tag prefix."""
        self.stage = stage
        for item in self._canvas.find_all():
            prefixes = {tag.split("-", 1)[0] for tag in self._canvas.gettags(item)}
            staged = prefixes & set(_PREFIXES.values())
            if staged:
                visible = _PREFIXES.get(stage) in staged
                self._canvas.itemconfigure(item, state="normal" if visible else "hidden")

    def _fold(self) -> None:
        """Hide the challenge into the edge tab; the countdown keeps running."""
        self._card.slide_out()
        self._tab.show()
        self._draw_countdown(time.monotonic())

    def _hide(self) -> None:
        self.stage = Stage.HIDDEN
        self._tab.hide()
        self._card.slide_out()

    def _reopen(self) -> None:
        if self.stage is Stage.COUNTDOWN and not self._card.visible:
            self._tab.hide()
            self._card.slide_in(self._anchor)
            self._draw_countdown(time.monotonic())
