"""Usage monitor — tracks CTX / 5H / 7D usage from Claude Code."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class UsageMonitor(QObject):
    """Monitors Claude Code usage via Statusline JSON or session files."""

    usage_updated = pyqtSignal(dict)  # {"ctx": float, "5h": float, "7d": float}

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
