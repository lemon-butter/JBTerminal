"""Status bar — CTX / 5H / 7D usage display."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget


class StatusBar(QWidget):
    """Bottom status bar showing usage metrics."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("status_bar")
