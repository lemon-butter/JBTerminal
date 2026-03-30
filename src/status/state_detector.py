"""State detector — detects Claude Code state from PTY output."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class StateDetector(QObject):
    """Parses PTY output to detect Claude Code state."""

    state_changed = pyqtSignal(str, str)  # (pane_id, state: PaneState value)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
