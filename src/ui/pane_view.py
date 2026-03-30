"""Pane view — individual pane with header and terminal widget."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.models.enums import SplitDirection


class PaneView(QWidget):
    """Single pane containing a header and terminal widget placeholder."""

    split_requested = pyqtSignal(str, str)  # (pane_id, direction)
    close_requested = pyqtSignal(str)       # (pane_id)
    focused = pyqtSignal(str)               # (pane_id)
    tab_dropped = pyqtSignal(str, int)      # (pane_id, tab_index) — tab dragged onto this pane

    def __init__(self, pane_id: str, name: str = "Terminal", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pane_id = pane_id
        self.setObjectName("pane_view")
        self.setAcceptDrops(True)
        self._drop_highlight = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Header ---
        self._header = QWidget()
        self._header.setObjectName("pane_header")
        self._header.setFixedHeight(28)
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(8, 0, 4, 0)
        header_layout.setSpacing(4)

        self._name_label = QLabel(name)
        self._name_label.setObjectName("pane_name")
        header_layout.addWidget(self._name_label)

        header_layout.addStretch()

        self._split_h_btn = QPushButton("⬌")
        self._split_h_btn.setToolTip("Split Horizontal")
        self._split_h_btn.setFixedSize(22, 22)
        self._split_h_btn.clicked.connect(
            lambda: self.split_requested.emit(self.pane_id, SplitDirection.HORIZONTAL)
        )
        header_layout.addWidget(self._split_h_btn)

        self._split_v_btn = QPushButton("⬍")
        self._split_v_btn.setToolTip("Split Vertical")
        self._split_v_btn.setFixedSize(22, 22)
        self._split_v_btn.clicked.connect(
            lambda: self.split_requested.emit(self.pane_id, SplitDirection.VERTICAL)
        )
        header_layout.addWidget(self._split_v_btn)

        self._close_btn = QPushButton("✕")
        self._close_btn.setToolTip("Close Pane")
        self._close_btn.setFixedSize(22, 22)
        self._close_btn.clicked.connect(
            lambda: self.close_requested.emit(self.pane_id)
        )
        header_layout.addWidget(self._close_btn)

        layout.addWidget(self._header)

        # --- Content area (placeholder for terminal widget) ---
        self._content_area = QVBoxLayout()
        self._content_area.setContentsMargins(0, 0, 0, 0)
        self._placeholder = QLabel(f"Terminal: {pane_id}")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("background-color: #08081a; color: #00FFCC;")
        self._content_area.addWidget(self._placeholder)
        layout.addLayout(self._content_area)

    def set_widget(self, widget: QWidget) -> None:
        """Replace placeholder with actual terminal widget."""
        # Check if this widget is already in the content area
        for i in range(self._content_area.count()):
            item = self._content_area.itemAt(i)
            if item and item.widget() is widget:
                return  # already placed, nothing to do

        # Remove old content (but don't delete terminal widgets — only placeholders)
        while self._content_area.count():
            item = self._content_area.takeAt(0)
            w = item.widget()
            if w and w is not widget:
                if self._placeholder is not None and w is self._placeholder:
                    w.deleteLater()
                else:
                    # Just remove from layout, don't delete (it may be reused)
                    w.setParent(None)
        self._content_area.addWidget(widget)
        self._placeholder = None

    def set_name(self, name: str) -> None:
        """Update the pane header name."""
        self._name_label.setText(name)

    def set_close_visible(self, visible: bool) -> None:
        """Show or hide the close button (hide when it's the only pane)."""
        self._close_btn.setVisible(visible)

    # --- Drag-and-drop: accept tab drops ---

    def dragEnterEvent(self, event: object) -> None:
        from src.ui.tab_bar import TerminalTabBar
        if event.mimeData().hasFormat(TerminalTabBar.TAB_MIME_TYPE):
            self._drop_highlight = True
            self.update()
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: object) -> None:
        self._drop_highlight = False
        self.update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: object) -> None:
        from src.ui.tab_bar import TerminalTabBar
        self._drop_highlight = False
        self.update()
        if event.mimeData().hasFormat(TerminalTabBar.TAB_MIME_TYPE):
            tab_index_bytes = event.mimeData().data(TerminalTabBar.TAB_MIME_TYPE).data()
            try:
                tab_index = int(tab_index_bytes.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                event.ignore()
                return
            self.tab_dropped.emit(self.pane_id, tab_index)
            event.acceptProposedAction()
        else:
            event.ignore()

    def paintEvent(self, event: object) -> None:
        """Draw highlight border when a tab is being dragged over this pane."""
        super().paintEvent(event)
        if self._drop_highlight:
            painter = QPainter(self)
            color = QColor("#00FFCC")
            color.setAlpha(80)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRect(self.rect())
            # Draw a border
            border = QColor("#00FFCC")
            border.setAlpha(180)
            from PyQt6.QtGui import QPen
            painter.setPen(QPen(border, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
            painter.end()

    def mousePressEvent(self, event: object) -> None:
        """Emit focused signal when pane is clicked."""
        self.focused.emit(self.pane_id)
        super().mousePressEvent(event)
