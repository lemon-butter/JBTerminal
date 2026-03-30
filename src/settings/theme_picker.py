"""Theme picker — theme selection, live preview, and custom color editing."""

from __future__ import annotations

from typing import Dict, Optional

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


# ---------------------------------------------------------------------------
# Editable token keys — the most important ones shown in the color editor
# ---------------------------------------------------------------------------

_EDITABLE_TOKENS = [
    ("bg_primary", "Background"),
    ("bg_secondary", "Background Secondary"),
    ("bg_tertiary", "Background Tertiary"),
    ("bg_terminal", "Terminal Background"),
    ("text_primary", "Text"),
    ("text_secondary", "Text Secondary"),
    ("text_muted", "Text Muted"),
    ("accent", "Accent"),
    ("accent2", "Secondary Accent"),
    ("status_success", "Success"),
    ("status_warning", "Warning"),
    ("status_error", "Error"),
    ("status_info", "Info"),
    ("border_default", "Border"),
    ("ansi_black", "ANSI Black"),
    ("ansi_red", "ANSI Red"),
    ("ansi_green", "ANSI Green"),
    ("ansi_yellow", "ANSI Yellow"),
    ("ansi_blue", "ANSI Blue"),
    ("ansi_magenta", "ANSI Magenta"),
    ("ansi_cyan", "ANSI Cyan"),
    ("ansi_white", "ANSI White"),
]


# ---------------------------------------------------------------------------
# Helper: representative swatch colors for each preset
# ---------------------------------------------------------------------------

def _get_preset_summary(name: str) -> Dict[str, str]:
    """Return summary colors (bg, accent, text) for a theme name.

    Tries to pull from the ThemeManager if available, otherwise uses
    a built-in fallback map.
    """
    _FALLBACK = {
        "Neon Dark": {"bg": "#0a0a1a", "accent": "#00FFCC", "text": "#ffffff"},
        "Neon Light": {"bg": "#f0f0f8", "accent": "#009977", "text": "#0a0a1a"},
        "Dracula": {"bg": "#282a36", "accent": "#bd93f9", "text": "#f8f8f2"},
        "Nord": {"bg": "#2e3440", "accent": "#88c0d0", "text": "#eceff4"},
        "Tokyo Night": {"bg": "#1a1b26", "accent": "#7aa2f7", "text": "#c0caf5"},
    }
    app = QApplication.instance()
    if app is not None:
        tm = app.property("theme_manager")
        if tm is not None and hasattr(tm, "_presets") and name in tm._presets:
            colors = tm._presets[name]
            return {
                "bg": colors.get("bg_primary", "#282828"),
                "accent": colors.get("accent", "#888888"),
                "text": colors.get("text_primary", "#ffffff"),
            }
    return _FALLBACK.get(name, {"bg": "#282828", "accent": "#888888", "text": "#cccccc"})


def _color_swatch(colors: Dict[str, str], size: int = 16) -> QIcon:
    """Create a small icon with stacked color swatches."""
    w = size * 3
    h = size
    pixmap = QPixmap(w, h)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    for i, key in enumerate(("bg", "accent", "text")):
        color = QColor(colors.get(key, "#888888"))
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(i * size, 0, size - 1, h, 3, 3)
    painter.end()
    return QIcon(pixmap)


# ---------------------------------------------------------------------------
# ColorEditorDialog — color picker for individual tokens
# ---------------------------------------------------------------------------

class ColorEditorDialog(QDialog):
    """Dialog that shows color pickers for key theme tokens.

    The user can adjust individual colors and save the result as a
    custom theme stored in the application config.
    """

    def __init__(
        self,
        theme_name: str,
        base_colors: Dict[str, str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Edit Theme - {theme_name}")
        self.setMinimumSize(420, 500)

        self._theme_name = theme_name
        self._colors = dict(base_colors)
        self._swatches: Dict[str, QPushButton] = {}

        # Build form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)

        for token_key, label in _EDITABLE_TOKENS:
            btn = QPushButton()
            btn.setFixedSize(60, 24)
            self._update_swatch_button(btn, self._colors.get(token_key, "#ff00ff"))
            btn.clicked.connect(lambda checked, k=token_key, b=btn: self._pick_color(k, b))
            self._swatches[token_key] = btn
            form_layout.addRow(label, btn)

        scroll.setWidget(form_widget)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        layout.addWidget(button_box)

    def _update_swatch_button(self, btn: QPushButton, hex_color: str) -> None:
        """Set the button background to the given color."""
        # Strip rgba(...) for display — show solid color
        qc = QColor(hex_color) if hex_color.startswith("#") else QColor(128, 128, 128)
        btn.setStyleSheet(
            f"background-color: {qc.name()}; border: 1px solid #555; border-radius: 3px;"
        )
        btn.setToolTip(hex_color)

    def _pick_color(self, token_key: str, btn: QPushButton) -> None:
        """Open a QColorDialog for the given token."""
        current_val = self._colors.get(token_key, "#ff00ff")
        initial = QColor(current_val) if current_val.startswith("#") else QColor(128, 128, 128)
        color = QColorDialog.getColor(initial, self, f"Pick color for {token_key}")
        if color.isValid():
            hex_val = color.name()
            self._colors[token_key] = hex_val
            self._update_swatch_button(btn, hex_val)

    def get_colors(self) -> Dict[str, str]:
        """Return the (possibly edited) full colors dict."""
        return dict(self._colors)


# ---------------------------------------------------------------------------
# ThemePicker — main widget
# ---------------------------------------------------------------------------

class ThemePicker(QWidget):
    """Theme selection widget with color swatches, edit button, and live preview.

    Displays a :class:`QListWidget` of available theme presets, each
    with a small swatch showing bg / accent / text colors.  Hovering over
    a theme temporarily applies it; leaving the list reverts to the
    current theme; clicking confirms the selection.
    """

    theme_selected = pyqtSignal(str)  # theme name

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._confirmed_theme: str = ""
        self._preview_active: bool = False

        # --- List ---
        self._list = QListWidget()
        self._list.setIconSize(QSize(48, 16))
        self._list.setMouseTracking(True)
        self._list.itemEntered.connect(self._on_item_hover)
        self._list.currentTextChanged.connect(self._on_theme_clicked)

        # --- Edit button ---
        self._edit_btn = QPushButton("Edit...")
        self._edit_btn.setFixedWidth(70)
        self._edit_btn.clicked.connect(self._on_edit_clicked)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self._edit_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)
        layout.addLayout(btn_layout)

        # Populate from ThemeManager if available, else use built-in names
        self._populate_list()

        # Revert preview on mouse leave
        self._list.viewport().installEventFilter(self)

    # ------------------------------------------------------------------
    # Population
    # ------------------------------------------------------------------

    def _populate_list(self) -> None:
        """Fill the list widget with known theme presets."""
        names = self._get_preset_names()
        for name in names:
            summary = _get_preset_summary(name)
            item = QListWidgetItem(_color_swatch(summary), name)
            self._list.addItem(item)

    def _get_preset_names(self) -> list:
        """Retrieve preset names from ThemeManager or use defaults."""
        app = QApplication.instance()
        if app is not None:
            tm = app.property("theme_manager")
            if tm is not None and hasattr(tm, "preset_names"):
                names = tm.preset_names()
                if names:
                    return names
        return ["Neon Dark", "Neon Light", "Dracula", "Nord", "Tokyo Night"]

    # ------------------------------------------------------------------
    # Live preview
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event) -> bool:  # type: ignore[override]
        """Revert live preview when the mouse leaves the list viewport."""
        from PyQt6.QtCore import QEvent
        if obj is self._list.viewport() and event.type() == QEvent.Type.Leave:
            self._revert_preview()
        return super().eventFilter(obj, event)

    def _on_item_hover(self, item: QListWidgetItem) -> None:
        """Temporarily apply the hovered theme for live preview."""
        if item is None:
            return
        name = item.text()
        app = QApplication.instance()
        if app is None:
            return
        tm = app.property("theme_manager")
        if tm is None or not hasattr(tm, "set_active"):
            return
        # Remember confirmed theme before first preview
        if not self._preview_active:
            self._confirmed_theme = tm.active_name
            self._preview_active = True
        try:
            tm.set_active(name)
            tm.apply_theme(app)
        except KeyError:
            pass

    def _revert_preview(self) -> None:
        """Revert to the confirmed (pre-hover) theme."""
        if not self._preview_active:
            return
        self._preview_active = False
        app = QApplication.instance()
        if app is None:
            return
        tm = app.property("theme_manager")
        if tm is None or not self._confirmed_theme:
            return
        try:
            tm.set_active(self._confirmed_theme)
            tm.apply_theme(app)
        except KeyError:
            pass

    def _on_theme_clicked(self, name: str) -> None:
        """Confirm the theme selection on click."""
        if not name:
            return
        self._preview_active = False
        self._confirmed_theme = name
        app = QApplication.instance()
        if app is not None:
            tm = app.property("theme_manager")
            if tm is not None and hasattr(tm, "set_active"):
                try:
                    tm.set_active(name)
                    tm.apply_theme(app)
                except KeyError:
                    pass
        self.theme_selected.emit(name)

    # ------------------------------------------------------------------
    # Edit button
    # ------------------------------------------------------------------

    def _on_edit_clicked(self) -> None:
        """Open the color editor for the currently selected theme."""
        item = self._list.currentItem()
        if item is None:
            return
        theme_name = item.text()

        # Get the base colors
        app = QApplication.instance()
        base_colors: Dict[str, str] = {}
        if app is not None:
            tm = app.property("theme_manager")
            if tm is not None and hasattr(tm, "_presets") and theme_name in tm._presets:
                base_colors = dict(tm._presets[theme_name])

        if not base_colors:
            from src.theme.tokens import COLORS
            base_colors = dict(COLORS)

        dialog = ColorEditorDialog(theme_name, base_colors, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            edited_colors = dialog.get_colors()
            custom_name = f"{theme_name} (Custom)"
            # Register in ThemeManager
            if app is not None:
                tm = app.property("theme_manager")
                if tm is not None and hasattr(tm, "load_preset"):
                    tm.load_preset(custom_name, edited_colors)
                    tm.set_active(custom_name)
                    tm.apply_theme(app)
            # Save custom theme to config
            self._save_custom_theme(custom_name, edited_colors)
            # Add to list if not already present
            existing = self._list.findItems(custom_name, Qt.MatchFlag.MatchExactly)
            if not existing:
                summary = {
                    "bg": edited_colors.get("bg_primary", "#282828"),
                    "accent": edited_colors.get("accent", "#888888"),
                    "text": edited_colors.get("text_primary", "#ffffff"),
                }
                new_item = QListWidgetItem(_color_swatch(summary), custom_name)
                self._list.addItem(new_item)
                self._list.setCurrentItem(new_item)
            else:
                self._list.setCurrentItem(existing[0])
            self._confirmed_theme = custom_name
            self.theme_selected.emit(custom_name)

    def _save_custom_theme(self, name: str, colors: Dict[str, str]) -> None:
        """Persist a custom theme to the application config."""
        from src.settings.config import Config
        config = Config()
        config.load()
        custom_themes: dict = config.get("custom_themes") or {}  # type: ignore[assignment]
        if not isinstance(custom_themes, dict):
            custom_themes = {}
        custom_themes[name] = colors
        config.set("custom_themes", custom_themes)
        config.save()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_theme(self, name: str) -> None:
        """Select theme by name."""
        items = self._list.findItems(name, Qt.MatchFlag.MatchExactly)
        if items:
            self._list.setCurrentItem(items[0])
        self._confirmed_theme = name

    def get_theme(self) -> str:
        item = self._list.currentItem()
        return item.text() if item else "Neon Dark"
