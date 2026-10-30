"""Colours, sizes and fonts in one place, so the look can change without touching layout code."""

from __future__ import annotations

import sys

CARD = "#1b1f27"
CARD_RAISED = "#252a34"
TRACK = "#2f3542"
TEXT = "#f4f1ea"
MUTED = "#8f97a6"
EMBER = "#ff7a1a"
EMBER_SOFT = "#ffb37a"
GOOD = "#3ecf8e"
GOLD = "#ffc94a"
DANGER = "#ff5a5f"

TRANSPARENT_KEY = "#010203"
"""Painted where the window should be see-through (Windows only)."""

RADIUS = 18
MARGIN = 16
GAP = 12

WIDGET_WIDTH = 300
WIDGET_HEIGHT = 104
WIDGET_EXPANDED_HEIGHT = 360
NUDGE_WIDTH = 340
NUDGE_HEIGHT = 204

FONT_FAMILY = {
    "win32": "Segoe UI",
    "darwin": "Helvetica Neue",
}.get(sys.platform, "DejaVu Sans")
