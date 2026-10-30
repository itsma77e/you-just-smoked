"""The tray icon, drawn in code so the repository ships no binary assets."""

from __future__ import annotations

from PIL import Image, ImageDraw

_SIZE = 64
_BACKGROUND = (32, 36, 44, 255)
_PAPER = (240, 240, 235, 255)
_EMBER = (255, 122, 26, 255)
_IDLE_EMBER = (120, 124, 132, 255)


def draw_icon(*, paused: bool = False) -> Image.Image:
    """A cigarette on a dark rounded tile; the ember goes grey while paused."""
    image = Image.new("RGBA", (_SIZE, _SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, _SIZE - 1, _SIZE - 1), radius=14, fill=_BACKGROUND)
    draw.rounded_rectangle((10, 28, 46, 38), radius=3, fill=_PAPER)
    draw.rounded_rectangle((44, 28, 54, 38), radius=3, fill=_IDLE_EMBER if paused else _EMBER)
    return image
