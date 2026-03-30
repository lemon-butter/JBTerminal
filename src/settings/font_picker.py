"""Font picker — system font list with preview."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class FontPicker(QWidget):
    """Font selection widget with live preview.

    Provides a :class:`QComboBox` of system fonts and a :class:`QSpinBox`
    for size.  A preview label updates in real time.
    """

    font_changed = pyqtSignal(str, int)  # (family, size)

    _SAMPLE_TEXT = "The quick brown fox jumps over the lazy dog 0123456789"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # --- Widgets ---
        self._family_combo = QComboBox()
        self._family_combo.setEditable(False)

        families = sorted(set(QFontDatabase.families()))
        self._family_combo.addItems(families)

        self._size_spin = QSpinBox()
        self._size_spin.setRange(6, 72)
        self._size_spin.setValue(14)
        self._size_spin.setSuffix(" px")

        self._preview = QLabel(self._SAMPLE_TEXT)
        self._preview.setWordWrap(True)
        self._preview.setMinimumHeight(40)

        # --- Layout ---
        row = QHBoxLayout()
        row.addWidget(self._family_combo, stretch=1)
        row.addWidget(self._size_spin)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addWidget(self._preview)

        # --- Connections ---
        self._family_combo.currentTextChanged.connect(self._on_changed)
        self._size_spin.valueChanged.connect(self._on_changed)

        # Initial preview
        self._update_preview()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def set_font(self, family: str, size: int) -> None:
        """Programmatically set font family and size."""
        idx = self._family_combo.findText(family)
        if idx >= 0:
            self._family_combo.setCurrentIndex(idx)
        self._size_spin.setValue(size)

    def get_font(self) -> tuple[str, int]:
        return self._family_combo.currentText(), self._size_spin.value()

    # ------------------------------------------------------------------

    def _on_changed(self) -> None:
        self._update_preview()
        family = self._family_combo.currentText()
        size = self._size_spin.value()
        self.font_changed.emit(family, size)

    def _update_preview(self) -> None:
        family = self._family_combo.currentText()
        size = self._size_spin.value()
        font = QFont(family, size)
        self._preview.setFont(font)
        self._preview.setText(self._SAMPLE_TEXT)
