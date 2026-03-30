"""Tab bar — multi-terminal tab management."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget


class TerminalTabBar(QWidget):
    """Tab bar for multiple terminal tabs within a workspace."""

    tab_added = pyqtSignal()
    tab_closed = pyqtSignal(int)       # (tab_index)
    tab_selected = pyqtSignal(int)     # (tab_index)
    tab_renamed = pyqtSignal(int, str) # (tab_index, new_name)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("tab_bar")
