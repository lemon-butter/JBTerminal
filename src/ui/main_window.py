"""Main application window — assembles sidebar, tab bar, split panes, status bar."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QMainWindow, QWidget


class MainWindow(QMainWindow):
    """Main application window."""

    pane_created = pyqtSignal(str, str)   # (pane_id, cwd)
    pane_closed = pyqtSignal(str)         # (pane_id)
    pane_focused = pyqtSignal(str)        # (pane_id)
    workspace_selected = pyqtSignal(str)  # (workspace_path)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("main_window")
        self.setWindowTitle("JBTerminal")
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)
