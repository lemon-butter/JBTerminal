"""Theme picker — theme selection and preview."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget


class ThemePicker(QWidget):
    """Theme selection widget with live preview."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
