"""Pillow drawings for the shapes Tk cannot antialias: cards, rings, bars and badges.

Every function returns an RGBA image and has no Tk dependency, so it can be tested
headless. Shapes are drawn at 4x and scaled down for smooth edges.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import cos, radians, sin

from PIL import Image, ImageDraw

_SCALE = 4


def card(width: int, height: int, *, color: str, radius: int, outside: str) -> Image.Image:
    """A rounded card. Corners are filled with `outside` and kept hard-edged, so a
    transparency key can cut them out without leaving a halo."""
    image = Image.new("RGBA", (width, height), outside)
    ImageDraw.Draw(image).rounded_rectangle((0, 0, width - 1, height - 1), radius, fill=color)
    return image


@dataclass(frozen=True, slots=True)
class RingStyle:
    color: str
    track: str
    width: int
    background: str


@dataclass(frozen=True, slots=True)
class BarStyle:
    color: str
    highlight: str
    """Used for the last bar, which is today."""

    background: str


def ring(size: int, fraction: float, style: RingStyle) -> Image.Image:
    """A progress ring starting at 12 o'clock, clockwise, with round caps."""
    big = size * _SCALE
    stroke = style.width * _SCALE
    image = Image.new("RGBA", (big, big), style.background)
    draw = ImageDraw.Draw(image)
    box = (stroke // 2, stroke // 2, big - stroke // 2 - 1, big - stroke // 2 - 1)
    draw.ellipse(box, outline=style.track, width=stroke)
    fraction = min(max(fraction, 0.0), 1.0)
    if fraction >= 1.0:
        draw.ellipse(box, outline=style.color, width=stroke)
    elif fraction > 0:
        end = -90 + 360 * fraction
        draw.arc(box, -90, end, fill=style.color, width=stroke)
        _cap(draw, big, stroke, -90, style.color)
        _cap(draw, big, stroke, end, style.color)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def bars(values: Sequence[int], size: tuple[int, int], style: BarStyle) -> Image.Image:
    """A small bar chart, one rounded bar per value."""
    width, height = size
    image = Image.new("RGBA", (width * _SCALE, height * _SCALE), style.background)
    draw = ImageDraw.Draw(image)
    slot = image.width / max(len(values), 1)
    bar = slot * 0.56
    peak = max(max(values, default=0), 1)
    for index, value in enumerate(values):
        left = slot * index + (slot - bar) / 2
        top = image.height - (image.height - _SCALE) * value / peak
        top = min(top, image.height - bar / 2)
        fill = style.highlight if index == len(values) - 1 else style.color
        draw.rounded_rectangle((left, top, left + bar, image.height - 1), bar / 2, fill=fill)
    return image.resize(size, Image.Resampling.LANCZOS)


def dot(size: int, *, color: str, background: str) -> Image.Image:
    """A smooth filled circle, used for badges and the status light."""
    big = size * _SCALE
    image = Image.new("RGBA", (big, big), background)
    ImageDraw.Draw(image).ellipse((0, 0, big - 1, big - 1), fill=color)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def _cap(draw: ImageDraw.ImageDraw, big: int, stroke: int, angle: float, color: str) -> None:
    radius = big / 2 - stroke  # PIL strokes inward from the inset box: this is the centreline
    center = big / 2
    x = center + radius * cos(radians(angle))
    y = center + radius * sin(radians(angle))
    half = stroke / 2
    draw.ellipse((x - half, y - half, x + half, y + half), fill=color)


def pill(width: int, height: int, *, color: str, background: str) -> Image.Image:
    """A fully rounded button shape with smooth edges against `background`."""
    image = Image.new("RGBA", (width * _SCALE, height * _SCALE), background)
    radius = image.height / 2
    ImageDraw.Draw(image).rounded_rectangle(
        (0, 0, image.width - 1, image.height - 1), radius, fill=color
    )
    return image.resize((width, height), Image.Resampling.LANCZOS)
