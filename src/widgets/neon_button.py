"""Neon glow button — QPainter multi-layer glow effect."""

from __future__ import annotations

from PyQt6.QtWidgets import QPushButton, QWidget


class NeonButton(QPushButton):
    """Button with neon glow effect via QPainter."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
