"""Neon glow frame — container with glow border."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QWidget

from src.theme.tokens import COLORS, RADIUS, get_color


_GLOW_LAYERS = 6


class NeonFrame(QFrame):
    """Frame container with neon glow border.

    Children should be added to :pymethod:`layout` (a QVBoxLayout is created
    automatically).  The glow is painted *around* the frame via QPainter.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        glow_color: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._glow_color_str = glow_color or COLORS["accent"]
        self._inner_layout = QVBoxLayout(self)
        margin = _GLOW_LAYERS * 2 + 4
        self._inner_layout.setContentsMargins(margin, margin, margin, margin)

    # ------------------------------------------------------------------
    # Property
    # ------------------------------------------------------------------

    @property
    def glow_color(self) -> str:
        return self._glow_color_str

    @glow_color.setter
    def glow_color(self, value: str) -> None:
        self._glow_color_str = value
        self.update()

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        inset = _GLOW_LAYERS * 2.0
        rect = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        radius = float(RADIUS["lg"])
        glow_qc = QColor(self._glow_color_str)

        # --- Glow layers ---
        for i in range(_GLOW_LAYERS, 0, -1):
            expand = i * 2.0
            alpha = int(30 * (1.0 - i / (_GLOW_LAYERS + 1)))
            c = QColor(glow_qc)
            c.setAlpha(alpha)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(c)
            painter.drawRoundedRect(
                rect.adjusted(-expand, -expand, expand, expand),
                radius + i, radius + i,
            )

        # --- Background ---
        bg = get_color("bg_secondary")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, radius, radius)

        # --- Border ---
        border_c = QColor(glow_qc)
        border_c.setAlpha(80)
        pen = QPen(border_c, 1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

        painter.end()
