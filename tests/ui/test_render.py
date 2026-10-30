from PIL import Image

from you_just_smoked.ui import render

BACKGROUND = "#000000"
RED = (255, 0, 0, 255)
BARS = render.BarStyle("#444444", "#ff0000", BACKGROUND)


def red(image: Image.Image, xy: tuple[int, int]) -> int:
    pixel = image.getpixel(xy)
    assert isinstance(pixel, tuple)
    return int(pixel[0])


def test_card_keeps_corners_for_the_transparency_key() -> None:
    image = render.card(100, 60, color="#ffffff", radius=12, outside="#010203")
    assert image.getpixel((0, 0)) == (1, 2, 3, 255)
    assert image.getpixel((50, 30)) == (255, 255, 255, 255)


def test_ring_fills_clockwise_from_the_top() -> None:
    quarter = render.ring(80, 0.25, render.RingStyle("#ff0000", "#333333", 8, BACKGROUND))
    assert quarter.size == (80, 80)
    assert red(quarter, (70, 30)) > 200
    assert red(quarter, (10, 50)) < 100


def test_empty_ring_is_just_the_track() -> None:
    empty = render.ring(40, 0.0, render.RingStyle("#ff0000", "#333333", 4, BACKGROUND))
    assert max(red(empty, (x, y)) for x in range(40) for y in range(40)) < 120


def test_bars_highlight_today() -> None:
    image = render.bars([1, 3, 2], (90, 40), BARS)
    assert image.size == (90, 40)
    assert red(image, (75, 38)) > 200
    assert red(image, (15, 38)) < 100


def test_bars_handle_an_empty_week() -> None:
    image = render.bars([0] * 7, (70, 30), BARS)
    assert image.size == (70, 30)


def test_dot_is_round() -> None:
    image = render.dot(20, color="#ff0000", background=BACKGROUND)
    assert image.getpixel((10, 10)) == RED
    assert red(image, (0, 0)) < 60
