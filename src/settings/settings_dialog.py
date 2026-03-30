"""Settings dialog — font, theme, terminal, notification preferences."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.settings.config import Config
from src.settings.font_picker import FontPicker
from src.settings.theme_picker import ThemePicker


class SettingsDialog(QDialog):
    """Application settings dialog with General, Appearance, Terminal,
    and Notifications tabs.

    Emits signals when settings are applied so the main window can
    react immediately.
    """

    # Emitted when font settings change: (family, size)
    font_applied = pyqtSignal(str, int)
    # Emitted when theme changes: (theme_name,)
    theme_applied = pyqtSignal(str)
    # Emitted when terminal settings change: (line_spacing, scrollback, cursor_blink)
    terminal_applied = pyqtSignal(float, int, bool)

    def __init__(
        self,
        config: Optional[Config] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("settings_dialog")
        self.setWindowTitle("Settings")
        self.setMinimumSize(520, 480)

        self._config = config or Config()

        # --- Tabs ---
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_general_tab(), "General")
        self._tabs.addTab(self._build_appearance_tab(), "Appearance")
        self._tabs.addTab(self._build_terminal_tab(), "Terminal")
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

    def _build_terminal_tab(self) -> QWidget:
        """Build the Terminal settings tab with line spacing, scrollback, and cursor blink."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # -- Line spacing slider --
        line_spacing_container = QWidget()
        ls_layout = QHBoxLayout(line_spacing_container)
        ls_layout.setContentsMargins(0, 0, 0, 0)

        self._line_spacing_slider = QSlider(Qt.Orientation.Horizontal)
        self._line_spacing_slider.setMinimum(80)   # 0.8x
        self._line_spacing_slider.setMaximum(200)  # 2.0x
        self._line_spacing_slider.setSingleStep(5)
        self._line_spacing_slider.setTickInterval(20)
        self._line_spacing_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._line_spacing_slider.setValue(100)

        self._line_spacing_label = QLabel("1.00x")
        self._line_spacing_label.setFixedWidth(48)
        self._line_spacing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._line_spacing_slider.valueChanged.connect(self._on_line_spacing_changed)

        ls_layout.addWidget(self._line_spacing_slider, 1)
        ls_layout.addWidget(self._line_spacing_label)

        form.addRow("Line spacing:", line_spacing_container)

        # -- Scrollback buffer size --
        self._scrollback_spin = QSpinBox()
        self._scrollback_spin.setRange(100, 1_000_000)
        self._scrollback_spin.setSingleStep(1000)
        self._scrollback_spin.setValue(10000)
        self._scrollback_spin.setSuffix(" lines")
        form.addRow("Scrollback buffer:", self._scrollback_spin)

        # -- Cursor blink toggle --
        self._cursor_blink_check = QCheckBox("Enable cursor blinking")
        self._cursor_blink_check.setChecked(True)
        form.addRow("Cursor:", self._cursor_blink_check)

        layout.addLayout(form)
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
    # Helpers
    # ------------------------------------------------------------------

    def _on_line_spacing_changed(self, value: int) -> None:
        """Update label when slider moves."""
        spacing = value / 100.0
        self._line_spacing_label.setText(f"{spacing:.2f}x")

    # ------------------------------------------------------------------
    # Config I/O
    # ------------------------------------------------------------------

    def _load_from_config(self) -> None:
        """Populate UI from Config."""
        # Font
        font = self._config.get_font()
        self._font_picker.set_font(font["family"], font["size"])

        # Theme
        self._theme_picker.set_theme(self._config.get_theme())

        # Terminal settings
        line_spacing = self._config.get("line_spacing", 1.0)
        self._line_spacing_slider.setValue(int(float(line_spacing) * 100))
        self._on_line_spacing_changed(self._line_spacing_slider.value())

        scrollback = self._config.get("scrollback_lines", 10000)
        self._scrollback_spin.setValue(int(scrollback))

        cursor_blink = self._config.get("cursor_blink", True)
        self._cursor_blink_check.setChecked(bool(cursor_blink))

        # Notifications
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
        """Write current dialog state back to Config, save, and emit signals."""
        # Font
        family, size = self._font_picker.get_font()
        self._config.set_font(family, size)

        # Theme
        theme = self._theme_picker.get_theme()
        self._config.set_theme(theme)

        # Terminal settings
        line_spacing = self._line_spacing_slider.value() / 100.0
        scrollback = self._scrollback_spin.value()
        cursor_blink = self._cursor_blink_check.isChecked()

        self._config.set("line_spacing", line_spacing)
        self._config.set("scrollback_lines", scrollback)
        self._config.set("cursor_blink", cursor_blink)

        # Notifications
        self._config.set_notifications_enabled(
            self._global_notif_check.isChecked()
        )
        for ws_id, cb in self._ws_checks:
            self._config.set_notifications_enabled(cb.isChecked(), ws_id)

        self._config.save()

        # Emit signals so the main window can react immediately
        self.font_applied.emit(family, size)
        self.theme_applied.emit(theme)
        self.terminal_applied.emit(line_spacing, scrollback, cursor_blink)

    def _on_ok(self) -> None:
        self._apply()
        self.accept()
