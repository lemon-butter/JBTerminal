"""Neon tab bar — active tab glow indicator."""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from src.theme.tokens import COLORS, RADIUS, SPACING, get_color


_GLOW_LAYERS = 6


class _TabData:
    """Internal data for a single tab."""

    __slots__ = ("title",)

    def __init__(self, title: str) -> None:
        self.title = title


class NeonTabBar(QWidget):
    """Custom tab bar with glow on active tab.

    This is **not** a QTabBar subclass.  Tabs are rendered as rounded-rect
    buttons in a horizontal layout.  The active tab has a bottom glow line
    in the accent colour.

    Signals
    -------
    tab_clicked(int)
        Emitted when a tab is clicked (index).
    tab_close_clicked(int)
        Emitted when the close button of a tab is clicked.
    add_clicked()
        Emitted when the "+" button is clicked.
    """

    tab_clicked = pyqtSignal(int)
    tab_close_clicked = pyqtSignal(int)
    add_clicked = pyqtSignal()

    _TAB_MIN_WIDTH = 80
    _TAB_MAX_WIDTH = 200
    _TAB_HEIGHT = 32
    _ADD_BTN_WIDTH = 28
    _CLOSE_SIZE = 14

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._tabs: List[_TabData] = []
        self._active_index: int = -1
        self._hover_index: int = -1
        self._hover_close_index: int = -1

        self.setFixedHeight(self._TAB_HEIGHT + 4)  # 4px for bottom glow
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_tab(self, title: str) -> int:
        """Add a tab and return its index."""
        self._tabs.append(_TabData(title))
        idx = len(self._tabs) - 1
        if self._active_index < 0:
            self._active_index = 0
        self.update()
        return idx

    def remove_tab(self, index: int) -> None:
        if 0 <= index < len(self._tabs):
            self._tabs.pop(index)
            if self._active_index >= len(self._tabs):
                self._active_index = len(self._tabs) - 1
            self.update()

    def set_active(self, index: int) -> None:
        if 0 <= index < len(self._tabs):
            self._active_index = index
            self.update()

    def active_index(self) -> int:
        return self._active_index

    def tab_count(self) -> int:
        return len(self._tabs)

    def set_tab_title(self, index: int, title: str) -> None:
        if 0 <= index < len(self._tabs):
            self._tabs[index].title = title
            self.update()

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def _tab_width(self) -> float:
        """Compute uniform tab width based on available space."""
        n = len(self._tabs)
        if n == 0:
            return float(self._TAB_MIN_WIDTH)
        available = self.width() - self._ADD_BTN_WIDTH - SPACING["sm"]
        w = available / n
        return max(float(self._TAB_MIN_WIDTH), min(float(self._TAB_MAX_WIDTH), w))

    def _tab_rect(self, index: int) -> QRectF:
        tw = self._tab_width()
        x = index * tw
        return QRectF(x, 0, tw, self._TAB_HEIGHT)

    def _add_btn_rect(self) -> QRectF:
        n = len(self._tabs)
        tw = self._tab_width()
        x = n * tw + SPACING["xs"]
        return QRectF(x, 2, self._ADD_BTN_WIDTH, self._TAB_HEIGHT - 4)

    def _close_rect(self, tab_rect: QRectF) -> QRectF:
        cs = self._CLOSE_SIZE
        x = tab_rect.right() - cs - 6
        y = tab_rect.center().y() - cs / 2.0
        return QRectF(x, y, cs, cs)

    def _index_at(self, x: float, y: float) -> int:
        """Return tab index at position or -1."""
        for i in range(len(self._tabs)):
            if self._tab_rect(i).contains(x, y):
                return i
        return -1

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        old_hover = self._hover_index
        old_close = self._hover_close_index
        self._hover_index = self._index_at(pos.x(), pos.y())
        # Check close button hover
        self._hover_close_index = -1
        if self._hover_index >= 0:
            cr = self._close_rect(self._tab_rect(self._hover_index))
            if cr.contains(pos.x(), pos.y()):
                self._hover_close_index = self._hover_index
        if self._hover_index != old_hover or self._hover_close_index != old_close:
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event: object) -> None:  # type: ignore[override]
        self._hover_index = -1
        self._hover_close_index = -1
        self.update()
        super().leaveEvent(event)  # type: ignore[arg-type]

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        pos = event.position()
        # Check add button
        if self._add_btn_rect().contains(pos.x(), pos.y()):
            self.add_clicked.emit()
            return
        idx = self._index_at(pos.x(), pos.y())
        if idx < 0:
            return
        # Check close button
        cr = self._close_rect(self._tab_rect(idx))
        if cr.contains(pos.x(), pos.y()):
            self.tab_close_clicked.emit(idx)
            return
        self._active_index = idx
        self.tab_clicked.emit(idx)
        self.update()

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        accent_qc = get_color("accent")
        radius = float(RADIUS["md"])

        for i, tab in enumerate(self._tabs):
            rect = self._tab_rect(i)
            is_active = i == self._active_index
            is_hover = i == self._hover_index

            # Tab background
            if is_active:
                bg = get_color("bg_primary")
            elif is_hover:
                bg = get_color("bg_hover")
            else:
                bg = get_color("bg_secondary")

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bg)
            painter.drawRoundedRect(
                rect.adjusted(1, 1, -1, 0), radius, radius,
            )

            # Border
            if is_active:
                pen_c = get_color("accent_medium")
            else:
                pen_c = get_color("border_default")
            painter.setPen(QPen(pen_c, 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(
                rect.adjusted(1, 1, -1, 0), radius, radius,
            )

            # Active tab bottom glow line
            if is_active:
                glow_y = rect.bottom()
                for layer in range(_GLOW_LAYERS, 0, -1):
                    alpha = int(40 * (1.0 - layer / (_GLOW_LAYERS + 1)))
                    c = QColor(accent_qc)
                    c.setAlpha(alpha)
                    pen = QPen(c, float(layer))
                    painter.setPen(pen)
                    painter.drawLine(
                        int(rect.left() + radius),
                        int(glow_y + layer * 0.5),
                        int(rect.right() - radius),
                        int(glow_y + layer * 0.5),
                    )
                # Solid accent line
                painter.setPen(QPen(accent_qc, 2.0))
                painter.drawLine(
                    int(rect.left() + radius), int(glow_y),
                    int(rect.right() - radius), int(glow_y),
                )

            # Tab title text
            if is_active:
                text_c = accent_qc
            elif is_hover:
                text_c = get_color("text_secondary")
            else:
                text_c = get_color("text_muted")

            painter.setPen(text_c)
            text_rect = rect.adjusted(8, 0, -self._CLOSE_SIZE - 10, 0)
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                tab.title,
            )

            # Close button (visible on hover or active)
            if is_hover or is_active:
                cr = self._close_rect(rect)
                close_hover = i == self._hover_close_index
                xc = get_color("status_error") if close_hover else get_color("text_muted")
                painter.setPen(QPen(xc, 1.5))
                m = 3.0
                painter.drawLine(
                    int(cr.left() + m), int(cr.top() + m),
                    int(cr.right() - m), int(cr.bottom() - m),
                )
                painter.drawLine(
                    int(cr.right() - m), int(cr.top() + m),
                    int(cr.left() + m), int(cr.bottom() - m),
                )

        # --- "+" add button ---
        add_rect = self._add_btn_rect()
        is_add_hover = add_rect.contains(
            self.mapFromGlobal(self.cursor().pos()).x(),
            self.mapFromGlobal(self.cursor().pos()).y(),
        ) if self.underMouse() else False

        add_bg = get_color("bg_hover") if is_add_hover else get_color("bg_secondary")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(add_bg)
        painter.drawRoundedRect(add_rect, radius, radius)

        painter.setPen(QPen(get_color("border_default"), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(add_rect, radius, radius)

        add_text_c = accent_qc if is_add_hover else get_color("text_muted")
        painter.setPen(add_text_c)
        font = painter.font()
        font.setPixelSize(16)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(add_rect, Qt.AlignmentFlag.AlignCenter, "+")

        painter.end()
