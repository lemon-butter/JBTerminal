"""Status bar — CTX / 5H / 7D usage display."""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from src.theme.tokens import COLORS, DIMENSIONS, FONTS


# ---------------------------------------------------------------------------
# Inline mini progress bar (fallback if NeonProgressBar is not ready)
# ---------------------------------------------------------------------------


class _MiniProgressBar(QWidget):
    """Tiny horizontal progress bar drawn with QPainter.

    Supports usage-spectrum colouring: green -> yellow -> orange -> red.
    """

    def __init__(self, label_text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value: float = 0.0
        self._label_text = label_text
        self.setFixedHeight(16)
        self.setMinimumWidth(60)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def set_value(self, v: float) -> None:
        self._value = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Draw label text on the left
        font = QFont(FONTS["mono_family"].split(",")[0].strip(), 9)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(QColor(COLORS["text_muted"]))
        label_rect_w = 28
        painter.drawText(0, 0, label_rect_w, h, Qt.AlignmentFlag.AlignVCenter, self._label_text)

        # Bar area
        bar_x = label_rect_w + 2
        bar_w = w - bar_x - 2
        bar_h = 6
        bar_y = (h - bar_h) // 2
        radius = 3.0

        # Background track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(COLORS["bg_tertiary"]))
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, radius, radius)

        # Filled portion
        fill_w = int(bar_w * self._value)
        if fill_w > 0:
            color = self._spectrum_color(self._value)
            painter.setBrush(color)
            painter.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, radius, radius)

        # Percentage text on the right
        pct_text = f"{int(self._value * 100)}%"
        painter.setPen(QColor(COLORS["text_secondary"]))
        painter.setFont(font)
        # Draw after bar, right-aligned
        painter.drawText(
            bar_x, 0, bar_w, h,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            pct_text,
        )

        painter.end()

    @staticmethod
    def _spectrum_color(v: float) -> QColor:
        if v < 0.50:
            return QColor(COLORS["usage_low"])
        if v < 0.80:
            return QColor(COLORS["usage_mid"])
        if v < 0.95:
            return QColor(COLORS["usage_high"])
        return QColor(COLORS["usage_critical"])


# ---------------------------------------------------------------------------
# StatusBar
# ---------------------------------------------------------------------------


class StatusBar(QWidget):
    """Bottom status bar showing usage metrics.

    Left section: 3 usage indicators (CTX, 5H, 7D).
    Right section: task duration label + settings gear button.
    """

    settings_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("status_bar")
        self.setFixedHeight(DIMENSIONS["status_bar_height"])

        # --- Usage indicators ---
        self._ctx_bar = _MiniProgressBar("CTX")
        self._fh_bar = _MiniProgressBar("5H")
        self._sd_bar = _MiniProgressBar("7D")

        # --- Task duration ---
        mono = FONTS["mono_family"].split(",")[0].strip()
        self._duration_label = QLabel("00:00")
        duration_font = QFont(mono, FONTS["status_bar_size"])
        duration_font.setWeight(QFont.Weight.Medium)
        self._duration_label.setFont(duration_font)
        self._duration_label.setStyleSheet(f"color: {COLORS['text_muted']};")

        # --- Settings button ---
        self._settings_btn = QPushButton("\u2699")  # gear unicode
        self._settings_btn.setFixedSize(22, 22)
        self._settings_btn.setFlat(True)
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 14px; border: none;"
        )
        self._settings_btn.clicked.connect(self.settings_clicked)

        # --- Layout ---
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(12)

        # Left: usage bars
        layout.addWidget(self._ctx_bar)
        layout.addWidget(self._fh_bar)
        layout.addWidget(self._sd_bar)

        layout.addStretch()

        # Right: duration + settings
        layout.addWidget(self._duration_label)
        layout.addWidget(self._settings_btn)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_usage(self, ctx: float, five_hour: float, seven_day: float) -> None:
        """Update usage bars. Values 0.0 -- 1.0."""
        self._ctx_bar.set_value(ctx)
        self._fh_bar.set_value(five_hour)
        self._sd_bar.set_value(seven_day)

    def update_task_duration(self, seconds: int) -> None:
        """Update the task duration display."""
        m, s = divmod(max(0, seconds), 60)
        h, m = divmod(m, 60)
        if h:
            self._duration_label.setText(f"{h}:{m:02d}:{s:02d}")
        else:
            self._duration_label.setText(f"{m:02d}:{s:02d}")
