"""Font picker — system font list with monospace filtering and terminal preview."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QFontDatabase, QFontMetricsF
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


def _is_monospace(family: str) -> bool:
    """Heuristic check: a font is monospace if 'M' and 'i' have equal width."""
    font = QFont(family, 14)
    font.setStyleHint(QFont.StyleHint.Monospace)
    fm = QFontMetricsF(font)
    w_m = fm.horizontalAdvance("M")
    w_i = fm.horizontalAdvance("i")
    # Allow a tiny tolerance for rounding
    return abs(w_m - w_i) < 0.5


class FontPicker(QWidget):
    """Font selection widget with live terminal-style preview.

    By default only monospace fonts are shown (suitable for terminal use).
    A toggle checkbox allows showing all system fonts.

    The preview shows terminal-like sample text including a prompt and
    a representation of ANSI-colored output.
    """

    font_changed = pyqtSignal(str, int)  # (family, size)

    _TERMINAL_SAMPLE = (
        "$ echo hello\n"
        "hello\n"
        "$ ls -la\n"
        "drwxr-xr-x  5 user staff  160 Jan  1 12:00 .\n"
        "$ git status\n"
        "On branch main -- nothing to commit"
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Build font lists once
        all_families = sorted(set(QFontDatabase.families()))
        self._all_families = all_families
        self._mono_families = [f for f in all_families if _is_monospace(f)]
        # Ensure at least a few known monospace fonts are present
        for known in ("Menlo", "Monaco", "Courier New", "JetBrains Mono", "Fira Code"):
            if known in all_families and known not in self._mono_families:
                self._mono_families.append(known)
        self._mono_families.sort()

        # --- Widgets ---
        self._family_combo = QComboBox()
        self._family_combo.setEditable(False)
        self._family_combo.setMaxVisibleItems(20)

        self._show_all_check = QCheckBox("Show all fonts")
        self._show_all_check.setChecked(False)
        self._show_all_check.toggled.connect(self._rebuild_family_list)

        self._size_spin = QSpinBox()
        self._size_spin.setRange(6, 72)
        self._size_spin.setValue(14)
        self._size_spin.setSuffix(" px")

        self._preview = QLabel(self._TERMINAL_SAMPLE)
        self._preview.setWordWrap(True)
        self._preview.setMinimumHeight(80)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._preview.setStyleSheet(
            "QLabel { background: #0a0a1a; color: #e0e0e0; "
            "padding: 8px; border-radius: 4px; font-size: 13px; }"
        )

        # --- Layout ---
        row = QHBoxLayout()
        row.addWidget(self._family_combo, stretch=1)
        row.addWidget(self._size_spin)

        filter_row = QHBoxLayout()
        filter_row.addWidget(self._show_all_check)
        filter_row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addLayout(filter_row)
        layout.addWidget(self._preview)

        # --- Populate ---
        self._rebuild_family_list(False)

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
        # If the requested family is not in current list, switch to "all"
        idx = self._family_combo.findText(family)
        if idx < 0 and not self._show_all_check.isChecked():
            self._show_all_check.setChecked(True)
            idx = self._family_combo.findText(family)
        if idx >= 0:
            self._family_combo.setCurrentIndex(idx)
        self._size_spin.setValue(size)

    def get_font(self) -> tuple[str, int]:
        return self._family_combo.currentText(), self._size_spin.value()

    # ------------------------------------------------------------------

    def _rebuild_family_list(self, show_all: bool) -> None:
        """Rebuild the family combo box with filtered or all fonts."""
        current = self._family_combo.currentText()
        self._family_combo.blockSignals(True)
        self._family_combo.clear()

        families = self._all_families if show_all else self._mono_families
        self._family_combo.addItems(families)

        # Restore selection
        idx = self._family_combo.findText(current)
        if idx >= 0:
            self._family_combo.setCurrentIndex(idx)
        elif families:
            # Try to select a sensible default
            for default in ("JetBrains Mono", "Menlo", "Monaco"):
                idx = self._family_combo.findText(default)
                if idx >= 0:
                    self._family_combo.setCurrentIndex(idx)
                    break
            else:
                self._family_combo.setCurrentIndex(0)

        self._family_combo.blockSignals(False)
        self._update_preview()

    def _on_changed(self) -> None:
        self._update_preview()
        family = self._family_combo.currentText()
        size = self._size_spin.value()
        self.font_changed.emit(family, size)

    def _update_preview(self) -> None:
        family = self._family_combo.currentText()
        size = self._size_spin.value()
        if not family:
            return
        font = QFont(family, size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self._preview.setFont(font)
        self._preview.setText(self._TERMINAL_SAMPLE)
