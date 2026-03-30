"""Main application window — assembles sidebar, tab bar, split panes, status bar."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.models.enums import SplitDirection
from src.models.workspace import Workspace, WorkspaceTab
from src.models.pane_tree import get_all_leaves
from src.status.status_bar import StatusBar
from src.ui.sidebar import Sidebar
from src.ui.split_pane import SplitPaneContainer
from src.ui.tab_bar import TerminalTabBar


class MainWindow(QMainWindow):
    """Main application window."""

    pane_created = pyqtSignal(str, str)     # (pane_id, cwd)
    pane_closed = pyqtSignal(str)           # (pane_id)
    pane_focused = pyqtSignal(str)          # (pane_id)
    workspace_selected = pyqtSignal(str)    # (workspace_path)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("main_window")
        self.setWindowTitle("JBTerminal")
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)

        # Current workspace
        self._workspace: Workspace | None = None

        # --- Central widget ---
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Horizontal splitter: sidebar | work area ---
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._main_splitter.setHandleWidth(1)
        self._main_splitter.setChildrenCollapsible(False)
        main_layout.addWidget(self._main_splitter)

        # --- Sidebar (left) ---
        self._sidebar = Sidebar()
        self._main_splitter.addWidget(self._sidebar)

        # --- Work area (right) ---
        work_area = QWidget()
        work_layout = QVBoxLayout(work_area)
        work_layout.setContentsMargins(0, 0, 0, 0)
        work_layout.setSpacing(0)

        # Tab bar (top)
        self._tab_bar = TerminalTabBar()
        work_layout.addWidget(self._tab_bar)

        # Split pane container (center)
        self._split_pane = SplitPaneContainer()
        work_layout.addWidget(self._split_pane, 1)

        # Status bar (bottom)
        self._status_bar = StatusBar()
        self._status_bar.setFixedHeight(28)
        work_layout.addWidget(self._status_bar)

        self._main_splitter.addWidget(work_area)

        # Set initial splitter sizes: sidebar 240px, work area gets the rest
        self._main_splitter.setSizes([240, 960])

        # --- Signal connections ---
        self._sidebar.workspace_selected.connect(self._on_workspace_selected)
        self._tab_bar.tab_added.connect(self._on_tab_added)
        self._tab_bar.tab_closed.connect(self._on_tab_closed)
        self._tab_bar.tab_selected.connect(self._on_tab_selected)
        self._tab_bar.tab_renamed.connect(self._on_tab_renamed)
        self._split_pane.pane_split_requested.connect(self._on_pane_split_requested)
        self._split_pane.pane_close_requested.connect(self._on_pane_close_requested)
        self._split_pane.pane_focused.connect(self._on_pane_focused)

        # --- Keyboard shortcuts ---
        self._setup_shortcuts()

        # --- Initialize with a default tab ---
        self._tab_bar.add_tab("Terminal")

    @property
    def sidebar(self) -> Sidebar:
        return self._sidebar

    @property
    def tab_bar(self) -> TerminalTabBar:
        return self._tab_bar

    @property
    def split_pane(self) -> SplitPaneContainer:
        return self._split_pane

    @property
    def status_bar(self) -> StatusBar:
        return self._status_bar

    def set_workspace(self, workspace: Workspace) -> None:
        """Switch to a workspace, restoring its tabs and pane layout."""
        self._workspace = workspace

        # Clear existing tabs from tab bar
        while self._tab_bar.tab_count > 0:
            # Remove from end to avoid index issues
            idx = self._tab_bar.tab_count - 1
            if idx > 0:
                self._tab_bar.close_tab(idx)
            else:
                break

        # Build tabs from workspace model
        if workspace.tabs:
            # Rename first tab
            self._tab_bar.rename_tab(0, workspace.tabs[0].name)
            self._split_pane.set_root(workspace.tabs[0].pane_root)

            for i in range(1, len(workspace.tabs)):
                self._tab_bar.add_tab(workspace.tabs[i].name)

            self._tab_bar.select_tab(workspace.active_tab_index)

    def _setup_shortcuts(self) -> None:
        """Register keyboard shortcuts."""
        shortcuts = [
            ("Ctrl+T", self._on_new_tab),
            ("Ctrl+W", self._on_close_tab),
            ("Ctrl+D", self._on_split_horizontal),
            ("Ctrl+Shift+D", self._on_split_vertical),
            ("Ctrl+B", self._on_toggle_sidebar),
            ("Ctrl+,", self._on_open_settings),
        ]
        for key_str, callback in shortcuts:
            shortcut = QShortcut(QKeySequence(key_str), self)
            shortcut.activated.connect(callback)

    # --- Shortcut handlers ---

    def _on_new_tab(self) -> None:
        self._tab_bar.tab_added.emit()

    def _on_close_tab(self) -> None:
        idx = self._tab_bar.active_index
        if idx >= 0:
            self._tab_bar.tab_closed.emit(idx)

    def _on_split_horizontal(self) -> None:
        pane = self._split_pane.get_active_pane()
        if pane:
            self._on_pane_split_requested(pane.pane_id, SplitDirection.HORIZONTAL)

    def _on_split_vertical(self) -> None:
        pane = self._split_pane.get_active_pane()
        if pane:
            self._on_pane_split_requested(pane.pane_id, SplitDirection.VERTICAL)

    def _on_toggle_sidebar(self) -> None:
        self._sidebar.setVisible(not self._sidebar.isVisible())

    def _on_open_settings(self) -> None:
        # Settings dialog will be handled by Team D
        pass

    # --- Signal handlers ---

    def _on_workspace_selected(self, path: str) -> None:
        self.workspace_selected.emit(path)

    def _on_tab_added(self) -> None:
        cwd = self._workspace.path if self._workspace else ""
        tab_index = self._tab_bar.add_tab("Terminal")
        # Create new split pane root for the tab
        from src.models.pane_tree import PaneLeaf
        new_root = PaneLeaf()
        self._split_pane.set_root(new_root)
        # Add to workspace model
        if self._workspace:
            new_tab = self._workspace.add_tab("Terminal")
            new_tab.pane_root = new_root
        self.pane_created.emit(new_root.id, cwd)

    def _on_tab_closed(self, index: int) -> None:
        if self._tab_bar.tab_count <= 1:
            return
        # Emit close for all panes in this tab
        if self._workspace and 0 <= index < len(self._workspace.tabs):
            tab = self._workspace.tabs[index]
            for leaf in get_all_leaves(tab.pane_root):
                self.pane_closed.emit(leaf.id)
            self._workspace.remove_tab(index)
        self._tab_bar.close_tab(index)
        # Restore pane tree for now-active tab
        if self._workspace:
            active = self._workspace.active_tab
            if active:
                self._split_pane.set_root(active.pane_root)

    def _on_tab_selected(self, index: int) -> None:
        if self._workspace:
            self._workspace.active_tab_index = index
            active = self._workspace.active_tab
            if active:
                self._split_pane.set_root(active.pane_root)

    def _on_tab_renamed(self, index: int, new_name: str) -> None:
        if self._workspace:
            self._workspace.rename_tab(index, new_name)

    def _on_pane_split_requested(self, pane_id: str, direction: str) -> None:
        new_id = self._split_pane.split_pane(pane_id, SplitDirection(direction))
        if new_id:
            # Update workspace model
            if self._workspace:
                active = self._workspace.active_tab
                if active:
                    active.pane_root = self._split_pane.root
            cwd = self._workspace.path if self._workspace else ""
            self.pane_created.emit(new_id, cwd)

    def _on_pane_close_requested(self, pane_id: str) -> None:
        if self._split_pane.close_pane(pane_id):
            if self._workspace:
                active = self._workspace.active_tab
                if active:
                    active.pane_root = self._split_pane.root
            self.pane_closed.emit(pane_id)

    def _on_pane_focused(self, pane_id: str) -> None:
        if self._workspace:
            active = self._workspace.active_tab
            if active:
                active.active_pane_id = pane_id
        self.pane_focused.emit(pane_id)
