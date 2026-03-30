"""Settings dialog — font, theme, notification preferences."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.settings.config import Config
from src.settings.font_picker import FontPicker
from src.settings.theme_picker import ThemePicker


class SettingsDialog(QDialog):
    """Application settings dialog with General, Appearance, and
    Notifications tabs.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("settings_dialog")
        self.setWindowTitle("Settings")
        self.setMinimumSize(520, 420)

        self._config = config or Config()

        # --- Tabs ---
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_general_tab(), "General")
        self._tabs.addTab(self._build_appearance_tab(), "Appearance")
        self._tabs.addTab(self._build_notifications_tab(), "Notifications")

        # --- Buttons ---
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        self._buttons.accepted.connect(self._on_ok)
        self._buttons.rejected.connect(self.reject)
        apply_btn = self._buttons.button(QDialogButtonBox.StandardButton.Apply)
        if apply_btn:
            apply_btn.clicked.connect(self._apply)

        # --- Main layout ---
        layout = QVBoxLayout(self)
        layout.addWidget(self._tabs)
        layout.addWidget(self._buttons)

        # Load current values
        self._load_from_config()

    # ------------------------------------------------------------------
    # Tab builders
    # ------------------------------------------------------------------

    def _build_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Font"))
        self._font_picker = FontPicker()
        layout.addWidget(self._font_picker)
        layout.addStretch()
        return tab

    def _build_appearance_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Theme"))
        self._theme_picker = ThemePicker()
        layout.addWidget(self._theme_picker)
        layout.addStretch()
        return tab

    def _build_notifications_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._global_notif_check = QCheckBox("Enable notifications")
        layout.addWidget(self._global_notif_check)

        layout.addWidget(QLabel("Per-workspace overrides:"))

        # Workspace toggles (populated from config)
        self._ws_checks: list[tuple[str, QCheckBox]] = []
        self._ws_container = QWidget()
        self._ws_layout = QVBoxLayout(self._ws_container)
        self._ws_layout.setContentsMargins(16, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._ws_container)
        layout.addWidget(scroll)
        layout.addStretch()

        return tab

    # ------------------------------------------------------------------
    # Config I/O
    # ------------------------------------------------------------------

    def _load_from_config(self) -> None:
        """Populate UI from Config."""
        font = self._config.get_font()
        self._font_picker.set_font(font["family"], font["size"])

        self._theme_picker.set_theme(self._config.get_theme())

        self._global_notif_check.setChecked(
            self._config.get_notifications_enabled()
        )

        # Workspace toggles
        for ws in self._config.get_workspaces():
            ws_id = ws.get("id", "")
            name = ws.get("name", ws.get("path", "unknown"))
            cb = QCheckBox(name)
            cb.setChecked(self._config.get_notifications_enabled(ws_id))
            self._ws_layout.addWidget(cb)
            self._ws_checks.append((ws_id, cb))

    def _apply(self) -> None:
        """Write current dialog state back to Config and save."""
        family, size = self._font_picker.get_font()
        self._config.set_font(family, size)

        self._config.set_theme(self._theme_picker.get_theme())

        self._config.set_notifications_enabled(
            self._global_notif_check.isChecked()
        )
        for ws_id, cb in self._ws_checks:
            self._config.set_notifications_enabled(cb.isChecked(), ws_id)

        self._config.save()

    def _on_ok(self) -> None:
        self._apply()
        self.accept()
