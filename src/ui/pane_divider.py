"""Pane divider — draggable split resize handle."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget


class PaneDivider(QWidget):
    """Draggable divider between split panes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pane_divider")
