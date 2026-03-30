"""Theme manager — load, switch, and apply themes."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class ThemeManager(QObject):
    """Manages theme loading, switching, and QSS generation."""

    theme_changed = pyqtSignal(dict)  # full token dict

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    def get_color(self, key: str) -> str:
        """Get a color value by token key."""
        raise NotImplementedError

    def get_qss(self) -> str:
        """Generate complete QSS stylesheet with current tokens."""
        raise NotImplementedError
