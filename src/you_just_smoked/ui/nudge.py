"""The nudge: slides in once per episode, and turns "I'll wait" into a small challenge.

    ASK ──wait──▶ COUNTDOWN ──time up──▶ CELEBRATE ──5 more──▶ COUNTDOWN
     │                │                       │
     └─smoking / no───┴──smoking──────────────┴──OK──▶ hidden

The countdown runs until the goal the nudge offered ("make it to 30 min?").
"Hide" folds it into a tab on the screen edge; when time is up it chimes and
comes back by itself to celebrate.
"""

from __future__ import annotations

import math
import time
import tkinter as tk
from collections.abc import Callable
from enum import StrEnum
from typing import TYPE_CHECKING

from you_just_smoked.domain.episode import Answer
from you_just_smoked.domain.tracker import Phase
from you_just_smoked.i18n import TIP_COUNT, text
from you_just_smoked.ui import confetti, render, theme
from you_just_smoked.ui.anim import Tween, ease_in_cubic
from you_just_smoked.ui.controls import (
    PRIMARY,
    QUIET,
    SECONDARY,
    Box,
    PillButton,
    Surface,
    TextStyle,
)
from you_just_smoked.ui.shell import make_floating, scale_factor, work_area
from you_just_smoked.ui.sound import Chime
from you_just_smoked.ui.tab import EdgeTab

if TYPE_CHECKING:
    from you_just_smoked.notify.base import AnswerCallback
    from you_just_smoked.notify.messages import NudgeText
    from you_just_smoked.runtime.status import Status

_W, _H = theme.NUDGE_WIDTH, theme.NUDGE_HEIGHT
_BODY = TextStyle(10, theme.MUTED, wrap=_W - 32)
_TIP = TextStyle(10, theme.TEXT, wrap=190)
_CLOCK = TextStyle(16, theme.TEXT, "bold", "center")
_GOLD_HEADLINE = TextStyle(15, theme.GOLD, "bold", wrap=_W - 32)
_AUTO_HIDE_S = 120
_TIP_EVERY_S = 20
_EXTRA_S = 5 * 60


class Stage(StrEnum):
    HIDDEN = "hidden"
    ASK = "ask"
    COUNTDOWN = "countdown"
    CELEBRATE = "celebrate"


class NudgePopup:
    def __init__(
        self,
        root: tk.Tk,
        language: str,
        anchor: Callable[[], tuple[int, int]],
        chime: Callable[[Chime], None],
    ) -> None:
        """`anchor` returns where the popup's bottom-right corner should go."""
        self._window = tk.Toplevel(root)
        self._outside = make_floating(self._window)
        self._window.withdraw()
        self._canvas = tk.Canvas(self._window, highlightthickness=0, bg=self._outside)
        self._canvas.pack(fill="both", expand=True)
        self._surface = Surface(self._canvas, scale_factor(root))
        self._language = language
        self._anchor = anchor
        self._chime = chime
        self._tab = EdgeTab(root, on_open=self._reopen)
        self.stage = Stage.HIDDEN
        """What the popup is showing; it may be off screen while a countdown runs."""
        self._visible = False
        self._on_answer: AnswerCallback | None = None
        self._deadline = 0.0
        self._started = 0.0
        self._wait_s = 0.0
        self._round_s = 0.0
        self._gained_s = 0.0
        self._shown_at = 0.0
        self._build()

    # Engine-facing ----------------------------------------------------------------------

    def ask(self, nudge: NudgeText, on_answer: AnswerCallback) -> None:
        self._on_answer = on_answer
        self._wait_s = nudge.wait_for.total_seconds()
        self._gained_s = 0.0
        self._surface.text(
            "ask-title", 16, 18, nudge.title, TextStyle(15, weight="bold", wrap=_W - 32)
        )
        self._surface.text("ask-body", 16, 72, nudge.body, _BODY)
        self._ask_buttons(nudge)
        self._switch(Stage.ASK)
        self._shown_at = time.monotonic()
        self._slide_in()
        self._chime(Chime.NUDGE)

    def on_status(self, status: Status) -> None:
        """Lighting up during the challenge ends it quietly: no scolding."""
        if self.stage is Stage.COUNTDOWN and status.phase is Phase.ACTIVE:
            self._hide()

    def tick(self) -> None:
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
        minutes = math.ceil(seconds / 60)
        title = text("challenge_title", self._language, minutes=minutes)
        self._surface.text("count-title", 128, 22, title, TextStyle(13, weight="bold", wrap=196))
        self._switch(Stage.COUNTDOWN)
        self._draw_countdown(self._started)

    def _draw_countdown(self, now: float) -> None:
        remaining = self._deadline - now
        if remaining <= 0:
            self._celebrate()
            return
        fraction = remaining / self._round_s
        self._tab.update(remaining, fraction)
        if not self._visible:
            return
        style = render.RingStyle(theme.GOLD, theme.TRACK, 8, theme.CARD)
        self._surface.image(
            "count-ring", render.ring(self._surface.px(96), fraction, style), 16, 24
        )
        minutes, seconds = divmod(int(remaining + 0.999), 60)
        self._surface.text("count-clock", 64, 72, f"{minutes}:{seconds:02}", _CLOCK)
        tip = int((now - self._started) // _TIP_EVERY_S) % TIP_COUNT
        self._surface.text("count-tip", 128, 74, text(f"tip_{tip}", self._language), _TIP)

    def _celebrate(self) -> None:
        self._gained_s += self._round_s
        minutes = round(self._gained_s / 60)
        title = text("celebrate_title", self._language, minutes=minutes)
        self._surface.text("party-title", 16, 22, title, _GOLD_HEADLINE)
        self._switch(Stage.CELEBRATE)
        self._tab.hide()
        if not self._visible:
            self._slide_in()
        self._chime(Chime.DONE)
        confetti.burst(
            self._canvas,
            (self._surface.px(_W / 2), self._surface.px(60)),
            scale=self._surface.scale,
        )

    # Building and switching -------------------------------------------------------------

    def _build(self) -> None:
        width, height = self._surface.px(_W), self._surface.px(_H)
        card = render.card(
            width,
            height,
            color=theme.CARD,
            radius=self._surface.px(theme.RADIUS),
            outside=self._outside,
        )
        self._surface.image("card", card, 0, 0)
        self._window.geometry(f"{width}x{height}")
        lang = self._language
        self._surface.text("party-body", 16, 72, text("celebrate_body", lang), _BODY)
        buttons = (
            (
                "count-hide",
                Box(128, 156, 84, 32),
                SECONDARY,
                "challenge_hide",
                self._hide_keep_counting,
            ),
            ("count-smoke", Box(218, 156, 106, 32), QUIET, "smoking", self._hide),
            (
                "party-more",
                Box(16, 156, 150, 32),
                PRIMARY,
                "celebrate_more",
                lambda: self._start_countdown(_EXTRA_S),
            ),
            ("party-done", Box(174, 156, 150, 32), SECONDARY, "celebrate_done", self._hide),
        )
        for tag, box, style, key, action in buttons:
            PillButton(self._surface, tag, box, style, action).draw(text(key, lang))

    def _ask_buttons(self, nudge: NudgeText) -> None:
        buttons = (
            ("ask-wait", Box(16, 126, 150, 34), PRIMARY, nudge.wait, Answer.WAIT),
            ("ask-smoke", Box(174, 126, 150, 34), SECONDARY, nudge.smoking, Answer.SMOKING),
            ("ask-false", Box(16, 168, 308, 26), QUIET, nudge.false_alarm, Answer.FALSE_ALARM),
        )
        for tag, box, style, label, answer in buttons:
            self._canvas.delete(tag)
            button = PillButton(self._surface, tag, box, style, self._answer_handler(answer))
            button.draw(label)

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

    def _hide_keep_counting(self) -> None:
        self._slide_out()
        self._tab.show()
        self._draw_countdown(time.monotonic())

    def _hide(self) -> None:
        self.stage = Stage.HIDDEN
        self._tab.hide()
        self._slide_out()

    def _reopen(self) -> None:
        if self.stage is Stage.COUNTDOWN and not self._visible:
            self._tab.hide()
            self._slide_in()
            self._draw_countdown(time.monotonic())

    # Motion -----------------------------------------------------------------------------

    def _slide_in(self) -> None:
        self._visible = True
        right, bottom = self._anchor()
        width, height = self._surface.px(_W), self._surface.px(_H)
        x = right - width
        y = max(bottom - height, work_area(self._window).top)
        self._window.wm_attributes("-alpha", 0.0)
        self._window.deiconify()
        start_x = x + self._surface.px(40)

        def step(t: float) -> None:
            self._window.geometry(f"{width}x{height}+{round(start_x + (x - start_x) * t)}+{y}")
            self._window.wm_attributes("-alpha", t)

        Tween(self._window, 280, step)

    def _slide_out(self) -> None:
        if not self._visible:
            return
        self._visible = False
        x, y = self._window.winfo_x(), self._window.winfo_y()
        shift = self._surface.px(40)

        def step(t: float) -> None:
            self._window.geometry(f"+{round(x + shift * t)}+{y}")
            self._window.wm_attributes("-alpha", 1 - t)

        Tween(self._window, 200, step, done=self._window.withdraw, ease=ease_in_cubic)


_PREFIXES = {Stage.ASK: "ask", Stage.COUNTDOWN: "count", Stage.CELEBRATE: "party"}
