import tkinter as tk
from collections.abc import Iterator

import pytest
from PIL import Image

from you_just_smoked.ui.controls import BODY, Surface


@pytest.fixture(scope="module")
def root() -> Iterator[tk.Tk]:
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    yield window
    window.destroy()


@pytest.fixture
def surface(root: tk.Tk) -> Iterator[Surface]:
    canvas = tk.Canvas(root)
    yield Surface(canvas, scale=1.0)
    canvas.destroy()


def test_items_sharing_a_group_are_updated_by_their_own_name(surface: Surface) -> None:
    dot = Image.new("RGBA", (4, 4))
    surface.image("badge-0", dot, 0, 0, groups=("badge-hover-0",))
    surface.text("glyph-0", 2, 2, "1h", BODY, groups=("badge-hover-0",))
    surface.image("badge-0", dot, 1, 1)
    surface.text("glyph-0", 2, 2, "2h", BODY)
    options = surface.canvas.itemconfigure("glyph-0")
    assert options is not None
    assert options["text"][-1] == "2h"
    assert len(surface.canvas.find_withtag("badge-hover-0")) == 2


def test_a_name_used_by_two_items_is_reported(surface: Surface) -> None:
    surface.canvas.create_text(0, 0, tags="twice")
    surface.canvas.create_text(0, 0, tags="twice")
    with pytest.raises(ValueError, match="use groups"):
        surface.text("twice", 0, 0, "x", BODY)
