from you_just_smoked.ui.icon import draw_icon


def test_ember_turns_grey_when_paused() -> None:
    ember = (49, 33)
    assert draw_icon().getpixel(ember) != draw_icon(paused=True).getpixel(ember)
    assert draw_icon().size == (64, 64)
