"""Pane view — individual pane with header and terminal widget."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt
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

    def __init__(self, pane_id: str, name: str = "Terminal", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.pane_id = pane_id
        self.setObjectName("pane_view")

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
        # Remove old content
        while self._content_area.count():
            item = self._content_area.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._content_area.addWidget(widget)
        self._placeholder = None

    def set_name(self, name: str) -> None:
        """Update the pane header name."""
        self._name_label.setText(name)

    def set_close_visible(self, visible: bool) -> None:
        """Show or hide the close button (hide when it's the only pane)."""
        self._close_btn.setVisible(visible)

    def mousePressEvent(self, event: object) -> None:
        """Emit focused signal when pane is clicked."""
        self.focused.emit(self.pane_id)
        super().mousePressEvent(event)
