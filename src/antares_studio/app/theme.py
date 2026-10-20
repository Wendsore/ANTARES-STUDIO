"""Jetons visuels de l'éditeur (thème sombre par défaut, contrastes lisibles)."""

from __future__ import annotations

from PySide6.QtGui import QColor

WORKSPACE_BG = QColor("#1E1E24")
CANVAS_SHADOW = QColor(0, 0, 0, 120)
SELECTION = QColor("#4FC3F7")
SELECTION_FILL = QColor(79, 195, 247, 40)
HANDLE_FILL = QColor("#FFFFFF")
HANDLE_BORDER = QColor("#1E88E5")
ROTATE_HANDLE = QColor("#FFB74D")
GRID = QColor(255, 255, 255, 28)
GRID_MAJOR = QColor(255, 255, 255, 60)
SAFE_ZONE = QColor(255, 193, 7, 110)
RUBBER_BAND = QColor(79, 195, 247, 60)
LOCKED = QColor("#EF5350")
KEYFRAME = QColor("#FFD54F")
KEYFRAME_SELECTED = QColor("#FF7043")
PLAYHEAD = QColor("#FF5252")
TRACK_BG = QColor("#2A2A32")
TRACK_ALT_BG = QColor("#30303A")
TEXT = QColor("#ECEFF1")
TEXT_MUTED = QColor("#90A4AE")
