"""Neon tab bar — active tab glow indicator."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget


class NeonTabBar(QWidget):
    """Tab bar with neon glow on active tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
