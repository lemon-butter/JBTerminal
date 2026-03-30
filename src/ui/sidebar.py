"""Sidebar — workspace list widget."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget


class Sidebar(QWidget):
    """Workspace list sidebar."""

    workspace_selected = pyqtSignal(str)  # (workspace_path)
    workspace_added = pyqtSignal(str)     # (workspace_path)
    workspace_removed = pyqtSignal(str)   # (workspace_id)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
