"""Neon progress bar — usage indicator with gradient colors."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from src.theme.tokens import RADIUS, get_color


_GLOW_LAYERS = 6


class NeonProgressBar(QWidget):
    """Compact progress bar with neon gradient (usage_low -> usage_critical).

    The fill color transitions through the usage spectrum based on the
    current value:

    * 0.0 -- 0.50 : ``usage_low``
    * 0.50 -- 0.80 : ``usage_mid``
    * 0.80 -- 0.95 : ``usage_high``
    * 0.95 -- 1.00 : ``usage_critical``
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value: float = 0.0
        self._label: str = ""
        self.setFixedHeight(16)
        self.setMinimumWidth(60)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_value(self, value: float) -> None:
        """Set progress value in range 0.0 -- 1.0."""
        self._value = max(0.0, min(1.0, value))
        self.update()

    def value(self) -> float:
        return self._value

    def set_label(self, text: str) -> None:
        """Set a short text label (e.g. 'CTX', '5H')."""
        self._label = text
        self.update()

    def label(self) -> str:
        return self._label

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fill_color(self) -> QColor:
        """Pick the fill colour based on current value."""
        v = self._value
        if v < 0.50:
            return get_color("usage_low")
        elif v < 0.80:
            return get_color("usage_mid")
        elif v < 0.95:
            return get_color("usage_high")
        else:
            return get_color("usage_critical")

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        full_rect = QRectF(self.rect())
        radius = float(RADIUS["full"])  # pill-shaped
        track_radius = full_rect.height() / 2.0

        # --- Background track ---
        bg = get_color("bg_secondary")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(full_rect, track_radius, track_radius)

        if self._value <= 0.0:
            self._draw_label(painter, full_rect)
            painter.end()
            return

        # --- Filled portion ---
        fill_width = full_rect.width() * self._value
        fill_rect = QRectF(
            full_rect.x(), full_rect.y(),
            max(fill_width, full_rect.height()),  # at least a circle
            full_rect.height(),
        )

        fill_c = self._fill_color()

        # Glow layers on fill
        for i in range(_GLOW_LAYERS, 0, -1):
            expand = i * 1.0
            alpha = int(35 * (1.0 - i / (_GLOW_LAYERS + 1)))
            c = QColor(fill_c)
            c.setAlpha(alpha)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(c)
            gr = fill_rect.adjusted(-expand, -expand, expand, expand)
            painter.drawRoundedRect(gr, track_radius + i, track_radius + i)

        # Gradient fill
        grad = QLinearGradient(fill_rect.topLeft(), fill_rect.topRight())
        grad.setColorAt(0.0, QColor(fill_c))
        lighter = QColor(fill_c)
        lighter.setAlpha(200)
        grad.setColorAt(1.0, lighter)
        painter.setBrush(grad)
        painter.drawRoundedRect(fill_rect, track_radius, track_radius)

        # --- Label ---
        self._draw_label(painter, full_rect)
        painter.end()

    def _draw_label(self, painter: QPainter, rect: QRectF) -> None:
        if not self._label:
            return
        painter.setPen(get_color("text_primary"))
        font = painter.font()
        font.setPixelSize(max(9, int(rect.height() * 0.65)))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._label)
