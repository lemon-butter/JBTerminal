"""Glow effects — QGraphicsDropShadowEffect utilities."""

from __future__ import annotations

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QWidget


def apply_glow(
    widget: QWidget,
    color: str = "#00FFCC",
    radius: int = 25,
    offset: tuple[int, int] = (0, 0),
) -> QGraphicsDropShadowEffect:
    """Apply a neon glow effect to a widget."""
    effect = QGraphicsDropShadowEffect()
    effect.setOffset(*offset)
    effect.setBlurRadius(radius)
    effect.setColor(QColor(color))
    widget.setGraphicsEffect(effect)
    return effect
