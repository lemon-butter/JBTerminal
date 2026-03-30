"""Tab bar — multi-terminal tab management."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt, QMimeData, QPoint
from PyQt6.QtGui import QDrag, QMouseEvent, QPainter, QColor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)


class TabButton(QWidget):
    """Individual tab button with name and close button."""

    clicked = pyqtSignal(int)           # (index)
    close_clicked = pyqtSignal(int)     # (index)
    double_clicked = pyqtSignal(int)    # (index)
    rename_finished = pyqtSignal(int, str)  # (index, new_name)

    def __init__(self, index: int, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.index = index
        self._name = name
        self._active = False
        self._drag_start: QPoint | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 4, 0)
        layout.setSpacing(4)

        self._label = QLabel(name)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._label)

        self._close_btn = QPushButton("✕")
        self._close_btn.setFixedSize(16, 16)
        self._close_btn.setVisible(False)  # visible on hover
        self._close_btn.clicked.connect(lambda: self.close_clicked.emit(self.index))
        layout.addWidget(self._close_btn)

        # Inline rename editor (hidden by default)
        self._edit = QLineEdit()
        self._edit.setVisible(False)
        self._edit.editingFinished.connect(self._finish_rename)
        layout.addWidget(self._edit)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        self._label.setText(value)

    def set_active(self, active: bool) -> None:
        self._active = active
        if active:
            self.setStyleSheet(
                "background-color: #0a0a1a; border-bottom: 2px solid #00FFCC;"
            )
            self._label.setStyleSheet("color: #00FFCC; font-weight: bold;")
        else:
            self.setStyleSheet(
                "background-color: #12122a; border-bottom: 2px solid transparent;"
            )
            self._label.setStyleSheet("color: #8888aa;")

    def start_rename(self) -> None:
        """Start inline rename."""
        self._label.setVisible(False)
        self._close_btn.setVisible(False)
        self._edit.setText(self._name)
        self._edit.setVisible(True)
        self._edit.setFocus()
        self._edit.selectAll()

    def _finish_rename(self) -> None:
        new_name = self._edit.text().strip()
        self._edit.setVisible(False)
        self._label.setVisible(True)
        if new_name and new_name != self._name:
            self._name = new_name
            self._label.setText(new_name)
            self.rename_finished.emit(self.index, new_name)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.pos()
            self.clicked.emit(self.index)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.index)
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start is not None and event.buttons() & Qt.MouseButton.LeftButton:
            distance = (event.pos() - self._drag_start).manhattanLength()
            if distance > 10:
                drag = QDrag(self)
                mime = QMimeData()
                mime.setText(str(self.index))
                # Also set custom MIME type so pane views can identify tab drags
                mime.setData(
                    TerminalTabBar.TAB_MIME_TYPE,
                    str(self.index).encode("utf-8"),
                )
                drag.setMimeData(mime)
                drag.exec(Qt.DropAction.MoveAction)
                self._drag_start = None
        super().mouseMoveEvent(event)

    def enterEvent(self, event: object) -> None:
        self._close_btn.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event: object) -> None:
        if not self._edit.isVisible():
            self._close_btn.setVisible(False)
        super().leaveEvent(event)


class TerminalTabBar(QWidget):
    """Tab bar for multiple terminal tabs within a workspace."""

    tab_added = pyqtSignal()
    tab_closed = pyqtSignal(int)       # (tab_index)
    tab_selected = pyqtSignal(int)     # (tab_index)
    tab_renamed = pyqtSignal(int, str) # (tab_index, new_name)
    tab_moved_to_pane = pyqtSignal(int, str)  # (tab_index, pane_id) — tab dragged onto a pane

    # MIME type for tab drag data
    TAB_MIME_TYPE = "application/x-jbterminal-tab"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("tab_bar")
        self.setFixedHeight(36)
        self.setAcceptDrops(True)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(72, 0, 8, 0)  # 72px left for macOS traffic lights
        self._layout.setSpacing(0)

        self._tabs: list[TabButton] = []
        self._active_index: int = -1
        self._drop_indicator_index: int = -1  # Visual drop position indicator

        # Add button
        self._add_btn = QPushButton("+")
        self._add_btn.setFixedSize(28, 28)
        self._add_btn.setToolTip("New Tab")
        self._add_btn.clicked.connect(self._on_add_clicked)

        self._layout.addStretch()
        self._layout.addWidget(self._add_btn)

    @property
    def tab_count(self) -> int:
        return len(self._tabs)

    @property
    def active_index(self) -> int:
        return self._active_index

    def add_tab(self, name: str = "Terminal") -> int:
        """Add a new tab. Returns the index of the new tab."""
        index = len(self._tabs)
        tab_btn = TabButton(index, name)
        tab_btn.clicked.connect(self._on_tab_clicked)
        tab_btn.close_clicked.connect(self._on_tab_close_clicked)
        tab_btn.double_clicked.connect(self._on_tab_double_clicked)
        tab_btn.rename_finished.connect(self._on_tab_rename_finished)
        self._tabs.append(tab_btn)

        # Insert before stretch + add button
        insert_pos = self._layout.count() - 2  # before stretch and add_btn
        self._layout.insertWidget(insert_pos, tab_btn)

        self.select_tab(index)
        return index

    def close_tab(self, index: int) -> None:
        """Close tab at index."""
        if index < 0 or index >= len(self._tabs):
            return
        if len(self._tabs) <= 1:
            return  # Don't close last tab

        tab_btn = self._tabs.pop(index)
        self._layout.removeWidget(tab_btn)
        tab_btn.deleteLater()

        # Re-index remaining tabs
        for i, tb in enumerate(self._tabs):
            tb.index = i

        # Adjust active index
        if self._active_index >= len(self._tabs):
            self.select_tab(len(self._tabs) - 1)
        elif self._active_index > index:
            self._active_index -= 1
            self._update_active_styles()
        else:
            self.select_tab(min(self._active_index, len(self._tabs) - 1))

    def select_tab(self, index: int) -> None:
        """Select tab at index."""
        if index < 0 or index >= len(self._tabs):
            return
        self._active_index = index
        self._update_active_styles()
        self.tab_selected.emit(index)

    def rename_tab(self, index: int, name: str) -> None:
        """Rename tab at index."""
        if 0 <= index < len(self._tabs):
            self._tabs[index].name = name

    def _update_active_styles(self) -> None:
        for i, tb in enumerate(self._tabs):
            tb.set_active(i == self._active_index)

    def _on_add_clicked(self) -> None:
        self.tab_added.emit()

    def _on_tab_clicked(self, index: int) -> None:
        self.select_tab(index)

    def _on_tab_close_clicked(self, index: int) -> None:
        self.tab_closed.emit(index)

    def _on_tab_double_clicked(self, index: int) -> None:
        if 0 <= index < len(self._tabs):
            self._tabs[index].start_rename()

    def _on_tab_rename_finished(self, index: int, new_name: str) -> None:
        self.tab_renamed.emit(index, new_name)

    # --- Drag and drop reorder ---

    def _drop_target_index(self, x: float) -> int:
        """Determine the target tab index for a drop at the given x coordinate."""
        for i, tb in enumerate(self._tabs):
            if x < tb.x() + tb.width() / 2:
                return i
        return len(self._tabs) - 1

    def dragEnterEvent(self, event: object) -> None:
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: object) -> None:
        """Update visual drop indicator during drag."""
        if event.mimeData().hasText():
            self._drop_indicator_index = self._drop_target_index(event.position().x())
            self.update()  # trigger repaint for indicator
            event.acceptProposedAction()

    def dragLeaveEvent(self, event: object) -> None:
        """Clear visual indicator when drag leaves the tab bar."""
        self._drop_indicator_index = -1
        self.update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: object) -> None:
        self._drop_indicator_index = -1
        self.update()

        source_index_str = event.mimeData().text()
        try:
            source_index = int(source_index_str)
        except (ValueError, TypeError):
            event.ignore()
            return

        # Determine target position based on drop x coordinate
        target_index = self._drop_target_index(event.position().x())

        if source_index != target_index and 0 <= source_index < len(self._tabs):
            tab = self._tabs.pop(source_index)
            self._tabs.insert(target_index, tab)
            # Re-index and re-layout
            for i, tb in enumerate(self._tabs):
                tb.index = i
            # Rebuild layout order (remove all tabs, re-add in order)
            for tb in self._tabs:
                self._layout.removeWidget(tb)
            insert_pos = 0
            for tb in self._tabs:
                self._layout.insertWidget(insert_pos, tb)
                insert_pos += 1
            # Update active index to follow the moved tab
            if self._active_index == source_index:
                self._active_index = target_index
            elif source_index < self._active_index <= target_index:
                self._active_index -= 1
            elif target_index <= self._active_index < source_index:
                self._active_index += 1
            self._update_active_styles()

        event.acceptProposedAction()

    def paintEvent(self, event: object) -> None:
        """Draw drop position indicator line during drag."""
        super().paintEvent(event)
        if self._drop_indicator_index < 0 or not self._tabs:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#00FFCC")
        color.setAlpha(200)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        # Draw a 3px wide indicator line at the drop position
        idx = self._drop_indicator_index
        if idx < len(self._tabs):
            x = self._tabs[idx].x() - 1
        else:
            last = self._tabs[-1]
            x = last.x() + last.width() - 1
        painter.drawRect(x, 4, 3, self.height() - 8)
        painter.end()
