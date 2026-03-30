"""Theme manager — load, switch, and apply themes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication

from src.theme.tokens import COLORS, get_color as _get_color


class ThemeManager(QObject):
    """Manages theme loading, switching, and QSS generation.

    Usage::

        tm = ThemeManager()
        tm.load_preset("Neon Dark", dark_colors)
        tm.load_preset("Neon Light", light_colors)
        tm.set_active("Neon Dark")
        tm.apply_theme(app)
    """

    theme_changed = pyqtSignal(dict)  # full token dict

    _QSS_PATH = Path(__file__).parent / "neon_theme.qss"

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._presets: Dict[str, Dict[str, str]] = {}
        self._active_name: str = ""
        self._active_colors: Dict[str, str] = dict(COLORS)
        self._qss_template: str = ""
        self._load_qss_template()

    # ------------------------------------------------------------------
    # QSS template
    # ------------------------------------------------------------------

    def _load_qss_template(self) -> None:
        if self._QSS_PATH.exists():
            self._qss_template = self._QSS_PATH.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Preset management
    # ------------------------------------------------------------------

    def load_preset(self, name: str, colors: Dict[str, str]) -> None:
        """Register a named preset."""
        self._presets[name] = dict(colors)

    def preset_names(self) -> list[str]:
        """Return list of registered preset names."""
        return list(self._presets.keys())

    def set_active(self, name: str) -> None:
        """Switch to a registered preset by name."""
        if name not in self._presets:
            raise KeyError(f"Unknown preset: {name!r}")
        self._active_name = name
        self._active_colors = dict(self._presets[name])
        self.theme_changed.emit(dict(self._active_colors))

    @property
    def active_name(self) -> str:
        return self._active_name

    @property
    def colors(self) -> Dict[str, str]:
        """Current active color dict (read-only copy)."""
        return dict(self._active_colors)

    # ------------------------------------------------------------------
    # Color access
    # ------------------------------------------------------------------

    def get_color(self, key: str) -> str:
        """Get a color *string* value by token key."""
        return self._active_colors.get(key, "#ff00ff")

    def get_qcolor(self, key: str) -> QColor:
        """Get a QColor by token key."""
        return _get_color(key, self._active_colors)

    # ------------------------------------------------------------------
    # QSS generation
    # ------------------------------------------------------------------

    def get_qss(self) -> str:
        """Generate the complete QSS with current tokens replaced."""
        qss = self._qss_template
        # Sort by key length descending so longer keys are replaced first
        # (e.g., @accent_hover before @accent)
        sorted_keys = sorted(self._active_colors.keys(), key=len, reverse=True)
        for key in sorted_keys:
            qss = qss.replace(f"@{key}", self._active_colors[key])
        return qss

    # ------------------------------------------------------------------
    # Apply to application
    # ------------------------------------------------------------------

    def apply_theme(self, app: QApplication) -> None:
        """Set the generated QSS on the QApplication."""
        app.setStyleSheet(self.get_qss())
