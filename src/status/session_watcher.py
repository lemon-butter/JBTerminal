"""Session watcher — monitors Claude Code JSONL session files."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class SessionWatcher(QObject):
    """Watches ~/.claude/projects/ for session file changes."""

    session_changed = pyqtSignal(str, dict)  # (session_path, parsed_data)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
