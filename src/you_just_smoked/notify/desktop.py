"""Native notifications with buttons, via desktop-notifier on a private asyncio loop."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import TYPE_CHECKING

from desktop_notifier import Button, DesktopNotifier, Icon

from you_just_smoked.domain.episode import Answer

if TYPE_CHECKING:
    from concurrent.futures import Future
    from pathlib import Path

    from you_just_smoked.notify.base import AnswerCallback
    from you_just_smoked.notify.messages import NudgeText

log = logging.getLogger(__name__)


class DesktopNotifierAdapter:
    def __init__(self, app_name: str, icon: Path | None = None) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, name="notify", daemon=True)
        self._thread.start()
        self._notifier = DesktopNotifier(
            app_name=app_name, app_icon=Icon(path=icon) if icon else None
        )

    def nudge(self, text: NudgeText, on_answer: AnswerCallback) -> None:
        future = asyncio.run_coroutine_threadsafe(self._send(text, on_answer), self._loop)
        future.add_done_callback(_log_failure)

    async def _send(self, text: NudgeText, on_answer: AnswerCallback) -> None:
        def answer(value: Answer) -> Button:
            return Button(title=_label(text, value), on_pressed=lambda: on_answer(value))

        await self._notifier.send(
            title=text.title,
            message=text.body,
            buttons=[answer(Answer.WAIT), answer(Answer.SMOKING), answer(Answer.FALSE_ALARM)],
        )

    def close(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=2)


def _label(text: NudgeText, answer: Answer) -> str:
    match answer:
        case Answer.WAIT:
            return text.wait
        case Answer.SMOKING:
            return text.smoking
        case Answer.FALSE_ALARM:
            return text.false_alarm


def _log_failure(future: Future[None]) -> None:
    if (error := future.exception()) is not None:
        log.warning("Could not show the notification: %s", error)
