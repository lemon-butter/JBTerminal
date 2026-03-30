"""Terminal emulator widget — renders PTY output and handles input."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget


class TerminalWidget(QWidget):
    """Terminal emulator widget using pyte backend."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("terminal")
