"""Pane view — individual pane with header and terminal widget."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget


class PaneView(QWidget):
    """Single pane containing a header and terminal widget."""

    def __init__(self, pane_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pane_id = pane_id
        self.setObjectName("pane_view")
