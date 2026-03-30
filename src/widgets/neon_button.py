"""Neon glow button — QPainter multi-layer glow effect."""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QPushButton, QWidget

from src.theme.tokens import COLORS, RADIUS, get_color


_GLOW_LAYERS = 8


class NeonButton(QPushButton):
    """Button with neon glow effect via QPainter.

    The glow is rendered as concentric rounded rectangles with decreasing
    alpha, giving the appearance of a soft neon halo.

    Properties
    ----------
    glow_color : str
        Hex or rgba() color used for the glow.  Defaults to the ``accent``
        token from :mod:`src.theme.tokens`.
    """

    def __init__(
        self,
        text: str = "",
        parent: QWidget | None = None,
        *,
        glow_color: str | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._glow_color_str = glow_color or COLORS["accent"]
        self._hovered = False
        self._pressed = False
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMinimumHeight(32)

    # ------------------------------------------------------------------
    # glow_color property
    # ------------------------------------------------------------------

    @property
    def glow_color(self) -> str:
        return self._glow_color_str

    @glow_color.setter
    def glow_color(self, value: str) -> None:
        self._glow_color_str = value
        self.update()

    # ------------------------------------------------------------------
    # Event overrides
    # ------------------------------------------------------------------

    def enterEvent(self, event: object) -> None:  # type: ignore[override]
        self._hovered = True
        self.update()
        super().enterEvent(event)  # type: ignore[arg-type]

    def leaveEvent(self, event: object) -> None:  # type: ignore[override]
        self._hovered = False
        self.update()
        super().leaveEvent(event)  # type: ignore[arg-type]

    def mousePressEvent(self, event: object) -> None:  # type: ignore[override]
        self._pressed = True
        self.update()
        super().mousePressEvent(event)  # type: ignore[arg-type]

    def mouseReleaseEvent(self, event: object) -> None:  # type: ignore[override]
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(
            _GLOW_LAYERS * 2, _GLOW_LAYERS * 2,
            -_GLOW_LAYERS * 2, -_GLOW_LAYERS * 2,
        )
        radius = float(RADIUS["md"])
        glow_qc = QColor(self._glow_color_str)
        disabled = not self.isEnabled()

        # --- Draw glow layers (skip when disabled) ---
        if not disabled:
            base_alpha = 20 if not self._hovered else 40
            for i in range(_GLOW_LAYERS, 0, -1):
                expand = i * 2.5
                alpha = int(base_alpha * (1.0 - i / (_GLOW_LAYERS + 1)))
                c = QColor(glow_qc)
                c.setAlpha(alpha)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(c)
                painter.drawRoundedRect(
                    rect.adjusted(-expand, -expand, expand, expand),
                    radius + i, radius + i,
                )

        # --- Background fill ---
        if disabled:
            bg = get_color("bg_secondary")
        elif self._pressed:
            bg = QColor(self._glow_color_str)
        elif self._hovered:
            bg = get_color("bg_hover")
        else:
            bg = get_color("bg_tertiary")

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, radius, radius)

        # --- Border ---
        if not disabled:
            if self._pressed:
                border_c = QColor(self._glow_color_str)
            elif self._hovered:
                border_c = get_color("accent_medium")
            else:
                border_c = get_color("border_default")
        else:
            border_c = get_color("border_default")

        pen = QPen(border_c, 1.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

        # --- Text ---
        if disabled:
            text_c = get_color("text_disabled")
        elif self._pressed:
            text_c = get_color("bg_primary")
        else:
            text_c = QColor(self._glow_color_str)

        painter.setPen(text_c)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
        painter.end()
