"""Drawing helpers on a Tk canvas, in logical pixels, plus a pill-shaped button.

Every item has a unique `name` and is created or updated in place, so a redraw is
just calling the same functions again with new values. Items can also join
`groups` (shared tags) for events and visibility; a name is never a group.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from PIL import ImageTk

from you_just_smoked.ui import render, theme

if TYPE_CHECKING:
    import tkinter as tk

    from PIL import Image

BUTTON_TAG = "button"
"""Shared by every button, so container click handlers can ignore button clicks."""

Weight = Literal["normal", "bold"]
Anchor = Literal["nw", "ne", "n", "center"]


@dataclass(frozen=True, slots=True)
class TextStyle:
    size: int
    color: str = theme.TEXT
    weight: Weight = "normal"
    anchor: Anchor = "nw"
    wrap: float | None = None


TIMER = TextStyle(24, weight="bold")
BODY = TextStyle(9)
MUTED = TextStyle(9, theme.MUTED)
SECTION = TextStyle(10, theme.MUTED, "bold")
LABEL = TextStyle(8, theme.MUTED, anchor="n")


class Surface:
    def __init__(self, canvas: tk.Canvas, scale: float) -> None:
        self.canvas = canvas
        self.scale = scale
        self._photos: dict[str, ImageTk.PhotoImage] = {}

    def px(self, value: float) -> int:
        return round(value * self.scale)

    def image(
        self,
        name: str,
        picture: Image.Image,
        x: float,
        y: float,
        *,
        groups: tuple[str, ...] = (),
    ) -> None:
        """Place `picture` (already in physical pixels) with its top-left at (x, y)."""
        photo = ImageTk.PhotoImage(picture)
        self._photos[name] = photo
        if self._exists(name):
            self.canvas.itemconfigure(name, image=photo)
            self.canvas.coords(name, self.px(x), self.px(y))
        else:
            position = (self.px(x), self.px(y))
            self.canvas.create_image(*position, image=photo, anchor="nw", tags=(name, *groups))

    def text(  # noqa: PLR0913 - position, content, style and grouping of one item
        self,
        name: str,
        x: float,
        y: float,
        value: str,
        style: TextStyle,
        *,
        groups: tuple[str, ...] = (),
    ) -> None:
        font = (theme.FONT_FAMILY, style.size, style.weight)
        wrap = self.px(style.wrap) if style.wrap else 0
        if self._exists(name):
            self.canvas.itemconfigure(name, text=value, fill=style.color, font=font, width=wrap)
            self.canvas.coords(name, self.px(x), self.px(y))
        else:
            self.canvas.create_text(
                self.px(x),
                self.px(y),
                text=value,
                fill=style.color,
                font=font,
                width=wrap,
                anchor=style.anchor,
                tags=(name, *groups),
            )

    def _exists(self, name: str) -> bool:
        items = self.canvas.find_withtag(name)
        if len(items) > 1:
            raise ValueError(f"{name!r} names {len(items)} items; use groups to share a tag")
        return bool(items)

    def show(self, tag: str, visible: bool) -> None:
        self.canvas.itemconfigure(tag, state="normal" if visible else "hidden")


@dataclass(frozen=True, slots=True)
class ButtonStyle:
    fill: str
    hover: str
    text: str


PRIMARY = ButtonStyle(theme.EMBER, theme.EMBER_SOFT, "#1a1205")
SECONDARY = ButtonStyle(theme.CARD_RAISED, theme.TRACK, theme.TEXT)
QUIET = ButtonStyle(theme.CARD, theme.CARD_RAISED, theme.MUTED)


@dataclass(frozen=True, slots=True)
class Box:
    x: float
    y: float
    width: float
    height: float


class PillButton:
    def __init__(  # noqa: PLR0913 - a button is described by all of these
        self,
        surface: Surface,
        tag: str,
        box: Box,
        style: ButtonStyle,
        on_click: Callable[[], None],
        *,
        background: str = theme.CARD,
    ) -> None:
        self._surface = surface
        self._tag = tag
        self._box = box
        self._on_click = on_click
        width, height = surface.px(box.width), surface.px(box.height)
        self._normal = render.pill(width, height, color=style.fill, background=background)
        self._hover = render.pill(width, height, color=style.hover, background=background)
        self._style = style
        canvas = surface.canvas
        for event, handler in (
            ("<Enter>", lambda _e: self._paint(self._hover)),
            ("<Leave>", lambda _e: self._paint(self._normal)),
            ("<ButtonRelease-1>", lambda _e: self._on_click()),
        ):
            canvas.tag_bind(tag, event, handler)

    def draw(self, label: str) -> None:
        self._paint(self._normal)
        box = self._box
        style = TextStyle(10, self._style.text, "bold", "center")
        center_x, center_y = box.x + box.width / 2, box.y + box.height / 2
        groups = (self._tag, BUTTON_TAG)
        self._surface.text(f"{self._tag}-label", center_x, center_y, label, style, groups=groups)

    def show(self, visible: bool) -> None:
        self._surface.show(self._tag, visible)

    def _paint(self, picture: Image.Image) -> None:
        box, groups = self._box, (self._tag, BUTTON_TAG)
        self._surface.image(f"{self._tag}-shape", picture, box.x, box.y, groups=groups)
        self._surface.canvas.tag_raise(f"{self._tag}-label")
