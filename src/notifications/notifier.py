"""Notifier — macOS system notifications."""

from __future__ import annotations

from PyQt6.QtCore import QObject


class Notifier(QObject):
    """Sends macOS native notifications via pyobjc or osascript."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
