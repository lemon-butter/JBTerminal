"""Sidebar — workspace list widget."""

from __future__ import annotations

import sys

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.models.enums import PaneState
from src.models.workspace import Workspace


# Status colors for the indicator dot
_STATUS_COLORS: dict[PaneState, str] = {
    PaneState.IDLE: "#555577",
    PaneState.THINKING: "#00FFCC",
    PaneState.TOOL_USE: "#FF66FF",
    PaneState.DONE: "#00FF88",
    PaneState.ERROR: "#FF4466",
    PaneState.WAITING: "#FFCC00",
}


class WorkspaceItemWidget(QWidget):
    """Custom widget for a workspace list item."""

    def __init__(self, workspace: Workspace, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar_item")
        self.workspace = workspace

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Status indicator dot
        self._indicator = QLabel("●")
        self._indicator.setFixedWidth(14)
        self._indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_indicator()
        layout.addWidget(self._indicator)

        # Name + path
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        text_layout.setContentsMargins(0, 0, 0, 0)

        self._name_label = QLabel(workspace.name or "Unnamed")
        self._name_label.setObjectName("workspace_name")
        text_layout.addWidget(self._name_label)

        self._path_label = QLabel(workspace.path)
        self._path_label.setObjectName("workspace_path")
        self._path_label.setStyleSheet("color: #8888aa; font-size: 11px;")
        text_layout.addWidget(self._path_label)

        layout.addLayout(text_layout, 1)

        # Inline rename editor (hidden)
        self._edit = QLineEdit()
        self._edit.setVisible(False)
        self._edit.editingFinished.connect(self._finish_rename)
        layout.addWidget(self._edit)

    def update_state(self, state: PaneState) -> None:
        self.workspace.state = state
        self._update_indicator()

    def _update_indicator(self) -> None:
        color = _STATUS_COLORS.get(self.workspace.state, "#555577")
        self._indicator.setStyleSheet(f"color: {color};")

    def start_rename(self) -> None:
        self._name_label.setVisible(False)
        self._path_label.setVisible(False)
        self._edit.setText(self.workspace.name)
        self._edit.setVisible(True)
        self._edit.setFocus()
        self._edit.selectAll()

    def _finish_rename(self) -> None:
        new_name = self._edit.text().strip()
        self._edit.setVisible(False)
        self._name_label.setVisible(True)
        self._path_label.setVisible(True)
        if new_name:
            self.workspace.name = new_name
            self._name_label.setText(new_name)


class Sidebar(QWidget):
    """Workspace list sidebar."""

    workspace_selected = pyqtSignal(str)  # (workspace_path)
    workspace_added = pyqtSignal(str)     # (workspace_path)
    workspace_removed = pyqtSignal(str)   # (workspace_id)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setMinimumWidth(180)
        self.setMaximumWidth(400)
        # Default width is 240px, set via splitter sizes in MainWindow.
        # Do NOT use setFixedWidth — it prevents splitter drag resize.

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 8, 8)

        header_label = QLabel("Workspaces")
        header_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        header_layout.addWidget(header_label)

        header_layout.addStretch()

        add_btn = QPushButton("+")
        add_btn.setFixedSize(24, 24)
        add_btn.setToolTip("Add Workspace")
        add_btn.clicked.connect(self._on_add_workspace)
        header_layout.addWidget(add_btn)

        layout.addWidget(header)

        # Workspace list
        self._list = QListWidget()
        self._list.setObjectName("workspace_list")
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._list)

        self._workspaces: list[Workspace] = []

    def add_workspace(self, workspace: Workspace) -> None:
        """Add a workspace to the sidebar."""
        self._workspaces.append(workspace)
        item = QListWidgetItem(self._list)
        widget = WorkspaceItemWidget(workspace)
        item.setSizeHint(widget.sizeHint())
        self._list.setItemWidget(item, widget)

    def remove_workspace(self, index: int) -> None:
        """Remove workspace at index."""
        if 0 <= index < len(self._workspaces):
            ws = self._workspaces.pop(index)
            self._list.takeItem(index)
            self.workspace_removed.emit(ws.id)

    def get_workspace(self, index: int) -> Workspace | None:
        """Get workspace by index."""
        if 0 <= index < len(self._workspaces):
            return self._workspaces[index]
        return None

    def update_workspace_state(self, workspace_id: str, state: PaneState) -> None:
        """Update the status indicator for a workspace."""
        for i, ws in enumerate(self._workspaces):
            if ws.id == workspace_id:
                item = self._list.item(i)
                if item:
                    widget = self._list.itemWidget(item)
                    if isinstance(widget, WorkspaceItemWidget):
                        widget.update_state(state)
                break

    @staticmethod
    def _pick_folder() -> str:
        """Open a native macOS folder picker, or Qt fallback on other OS."""
        if sys.platform == "darwin":
            try:
                from AppKit import NSOpenPanel, NSModalResponseOK
                panel = NSOpenPanel.openPanel()
                panel.setCanChooseDirectories_(True)
                panel.setCanChooseFiles_(False)
                panel.setAllowsMultipleSelection_(False)
                result = panel.runModal()
                if result == NSModalResponseOK:
                    urls = panel.URLs()
                    if urls and len(urls) > 0:
                        return str(urls[0].path())
                return ""
            except ImportError:
                pass
        # Fallback: Qt dialog
        from PyQt6.QtWidgets import QFileDialog
        return QFileDialog.getExistingDirectory(None, "Select Workspace Folder")

    def _on_add_workspace(self) -> None:
        path = self._pick_folder()
        if path:
            import os
            name = os.path.basename(path)
            ws = Workspace(name=name, path=path)
            self.add_workspace(ws)
            self.workspace_added.emit(path)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        index = self._list.row(item)
        if 0 <= index < len(self._workspaces):
            ws = self._workspaces[index]
            # Update active styling
            for i in range(self._list.count()):
                w = self._list.itemWidget(self._list.item(i))
                if w:
                    obj_name = "sidebar_item_active" if i == index else "sidebar_item"
                    w.setObjectName(obj_name)
            self.workspace_selected.emit(ws.path)

    def _on_context_menu(self, pos: object) -> None:
        item = self._list.itemAt(pos)
        if item is None:
            return
        index = self._list.row(item)

        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        remove_action = menu.addAction("Remove")

        action = menu.exec(self._list.mapToGlobal(pos))
        if action == rename_action:
            widget = self._list.itemWidget(item)
            if isinstance(widget, WorkspaceItemWidget):
                widget.start_rename()
        elif action == remove_action:
            self.remove_workspace(index)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        widget = self._list.itemWidget(item)
        if isinstance(widget, WorkspaceItemWidget):
            widget.start_rename()
