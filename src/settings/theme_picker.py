"""Theme picker — theme selection and preview."""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Available theme presets — maps name to representative colors
_THEME_PRESETS = {
    "Neon Dark": {
        "bg": "#0a0a1a",
        "accent": "#00FFCC",
        "text": "#ffffff",
    },
    "Light": {
        "bg": "#f5f5f5",
        "accent": "#0077CC",
        "text": "#222222",
    },
    "Monokai": {
        "bg": "#272822",
        "accent": "#A6E22E",
        "text": "#F8F8F2",
    },
    "Dracula": {
        "bg": "#282a36",
        "accent": "#BD93F9",
        "text": "#F8F8F2",
    },
    "Solarized Dark": {
        "bg": "#002b36",
        "accent": "#268bd2",
        "text": "#839496",
    },
}


def _color_swatch(colors: dict[str, str], size: int = 16) -> QIcon:
    """Create a small icon with stacked color swatches."""
    w = size * 3
    h = size
    pixmap = QPixmap(w, h)
    pixmap.fill(QColor(0, 0, 0, 0))

    from PyQt6.QtGui import QPainter

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    for i, key in enumerate(("bg", "accent", "text")):
        color = QColor(colors.get(key, "#888888"))
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(i * size, 0, size - 1, h, 3, 3)
    painter.end()
    return QIcon(pixmap)


class ThemePicker(QWidget):
    """Theme selection widget with color swatches.

    Displays a :class:`QListWidget` of available theme presets, each
    with a small swatch showing bg / accent / text colors.
    """

    theme_selected = pyqtSignal(str)  # theme name

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._list = QListWidget()
        self._list.setIconSize(QSize(48, 16))

        for name, colors in _THEME_PRESETS.items():
            item = QListWidgetItem(_color_swatch(colors), name)
            self._list.addItem(item)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)

        self._list.currentTextChanged.connect(self.theme_selected)

    def set_theme(self, name: str) -> None:
        """Select theme by name."""
        items = self._list.findItems(name, Qt.MatchFlag.MatchExactly)
        if items:
            self._list.setCurrentItem(items[0])

    def get_theme(self) -> str:
        item = self._list.currentItem()
        return item.text() if item else "Neon Dark"
