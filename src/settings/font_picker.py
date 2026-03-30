"""Font picker — system font list with preview."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget


class FontPicker(QWidget):
    """Font selection widget with live preview."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
