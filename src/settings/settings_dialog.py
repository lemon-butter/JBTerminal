"""Settings dialog — font, theme, notification preferences."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QWidget


class SettingsDialog(QDialog):
    """Application settings dialog."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settings_dialog")
        self.setWindowTitle("Settings")
