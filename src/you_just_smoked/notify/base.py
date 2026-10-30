from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from you_just_smoked.domain.episode import Answer
    from you_just_smoked.notify.messages import NudgeText

AnswerCallback = Callable[["Answer"], None]


class Notifier(Protocol):
    def nudge(self, text: NudgeText, on_answer: AnswerCallback) -> None:
        """Show the nudge. `on_answer` may be called later, from any thread, at most once."""
        ...

    def close(self) -> None: ...
