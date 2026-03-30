"""Main application window — assembles sidebar, tab bar, split panes, status bar."""

from __future__ import annotations

import os
from typing import Dict, Optional

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.models.enums import PaneState, SplitDirection
from src.models.workspace import Workspace, WorkspaceTab
from src.models.pane_tree import get_all_leaves
from src.notifications.hooks_handler import HooksHandler
from src.notifications.notifier import Notifier
from src.settings.config import Config
from src.settings.settings_dialog import SettingsDialog
from src.status.session_watcher import SessionWatcher
from src.status.state_detector import StateDetector
from src.status.status_bar import StatusBar
from src.status.usage_monitor import UsageMonitor
from src.terminal.pty_manager import PtyManager
from src.terminal.terminal_config import TerminalConfig
from src.terminal.terminal_widget import TerminalWidget
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

        # --- PTY Manager ---
        self._pty_manager = PtyManager(self)
        self._terminal_widgets: Dict[str, TerminalWidget] = {}

        # --- State Detector ---
        self._state_detector = StateDetector(self)

        # --- Notifier ---
        self._notifier = Notifier(self)
        self._notifier.show_requested.connect(self._bring_to_front)

        # --- Hooks Handler ---
        self._hooks_handler = HooksHandler(self)
        self._hooks_handler.connect_notifier(self._notifier)
        self._hooks_handler.connect_state_detector(self._state_detector)

        # --- Usage Monitor ---
        self._usage_monitor = UsageMonitor(self)

        # --- Session Watcher ---
        self._session_watcher = SessionWatcher(self)

        # --- Config ---
        self._config = Config()
        self._config.load()

        # Wire hooks handler to config
        self._hooks_handler.connect_config(self._config)

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

        # --- Signal connections (UI) ---
        self._sidebar.workspace_selected.connect(self._on_workspace_selected)
        self._tab_bar.tab_added.connect(self._on_tab_added)
        self._tab_bar.tab_closed.connect(self._on_tab_closed)
        self._tab_bar.tab_selected.connect(self._on_tab_selected)
        self._tab_bar.tab_renamed.connect(self._on_tab_renamed)
        self._split_pane.pane_split_requested.connect(self._on_pane_split_requested)
        self._split_pane.pane_close_requested.connect(self._on_pane_close_requested)
        self._split_pane.pane_focused.connect(self._on_pane_focused)
        self._split_pane.tab_dropped_on_pane.connect(self._on_tab_dropped_on_pane)

        # --- Signal connections (PTY integration) ---
        self._pty_manager.pty_output.connect(self._on_pty_output)
        self._pty_manager.pty_exited.connect(self._on_pty_exited)
        self.pane_created.connect(self._on_pane_created)
        self.pane_closed.connect(self._on_pane_closed_cleanup)

        # --- Signal connections (Status integration) ---
        self._pty_manager.pty_output.connect(self._state_detector.feed)
        self._state_detector.state_changed.connect(self._on_state_changed)
        self._usage_monitor.usage_updated.connect(self._on_usage_updated)
        self._status_bar.settings_clicked.connect(self._on_open_settings)

        # --- Start monitors ---
        self._usage_monitor.start()
        self._session_watcher.start()

        # --- Theme change connection ---
        app = QApplication.instance()
        if app is not None:
            tm = app.property("theme_manager")
            if tm is not None:
                tm.theme_changed.connect(self._on_theme_changed)

        # --- Keyboard shortcuts ---
        self._setup_shortcuts()

        # --- Restore layout or initialize default ---
        self._restore_layout_or_default()

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
        self._hooks_handler.set_workspace_id(workspace.id)

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
        dialog = SettingsDialog(config=self._config, parent=self)
        dialog.font_applied.connect(self._on_font_applied)
        dialog.theme_applied.connect(self._on_theme_applied)
        dialog.terminal_applied.connect(self._on_terminal_applied)
        dialog.exec()

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

    def _on_tab_dropped_on_pane(self, pane_id: str, tab_index: int) -> None:
        """Handle a tab being dragged and dropped onto a split pane.

        This moves the terminal from the dragged tab into the target pane,
        replacing whatever was there before. The source tab is then closed.
        """
        if not self._workspace:
            return
        if tab_index < 0 or tab_index >= len(self._workspace.tabs):
            return
        # Don't allow dropping the only tab
        if len(self._workspace.tabs) <= 1:
            return
        # Don't drop onto a pane that belongs to the same tab being dragged
        source_tab = self._workspace.tabs[tab_index]
        source_leaves = get_all_leaves(source_tab.pane_root)
        if pane_id in [lf.id for lf in source_leaves]:
            return

        # Get terminal widgets from source tab's panes
        source_pane_ids = [lf.id for lf in source_leaves]
        # Move the first terminal widget from source tab into target pane
        if source_pane_ids:
            first_source_id = source_pane_ids[0]
            tw = self._terminal_widgets.get(first_source_id)
            if tw is not None:
                # Re-map the terminal widget to the target pane
                self._terminal_widgets.pop(first_source_id, None)
                self._terminal_widgets[pane_id] = tw
                # Place in target pane view
                target_view = self._split_pane.get_pane_view(pane_id)
                if target_view is not None:
                    target_view.set_widget(tw)
                # Update PTY mapping — rewrite to target pane_id
                tw.input_ready.disconnect()
                tw.size_changed.disconnect()
                tw.input_ready.connect(
                    lambda data, pid=pane_id: self._pty_manager.write(pid, data)
                )
                tw.size_changed.connect(
                    lambda cols, rows, pid=pane_id: self._pty_manager.resize(pid, cols, rows)
                )
                # Remap PTY process from old pane_id to new
                self._pty_manager.remap(first_source_id, pane_id)

        # Close remaining source panes' PTY processes
        for sid in source_pane_ids[1:]:
            self._pty_manager.kill(sid)
            stw = self._terminal_widgets.pop(sid, None)
            if stw is not None:
                stw.deleteLater()

        # Remove the source tab from workspace model and tab bar
        self._workspace.remove_tab(tab_index)
        self._tab_bar.close_tab(tab_index)

    # ------------------------------------------------------------------ #
    #  PTY Integration                                                     #
    # ------------------------------------------------------------------ #

    def _on_pane_created(self, pane_id: str, cwd: str) -> None:
        """Spawn a PTY and wire up a TerminalWidget for a new pane."""
        if not cwd:
            cwd = os.path.expanduser("~")

        # Create terminal widget
        tw = TerminalWidget()
        self._terminal_widgets[pane_id] = tw

        # Connect terminal widget signals to PTY
        tw.input_ready.connect(lambda data, pid=pane_id: self._pty_manager.write(pid, data))
        tw.size_changed.connect(lambda cols, rows, pid=pane_id: self._pty_manager.resize(pid, cols, rows))

        # Place widget in its pane view
        pane_view = self._split_pane.get_pane_view(pane_id)
        if pane_view is not None:
            pane_view.set_widget(tw)

        # Spawn the PTY process
        self._pty_manager.spawn(pane_id, cwd)

    def _on_pane_closed_cleanup(self, pane_id: str) -> None:
        """Kill PTY and clean up terminal widget when a pane is closed."""
        self._pty_manager.kill(pane_id)
        tw = self._terminal_widgets.pop(pane_id, None)
        if tw is not None:
            tw.deleteLater()

    def _on_pty_output(self, pane_id: str, data: bytes) -> None:
        """Forward PTY output to the corresponding TerminalWidget."""
        tw = self._terminal_widgets.get(pane_id)
        if tw is not None:
            tw.feed(data)

    def _on_pty_exited(self, pane_id: str, exit_code: int) -> None:
        """Handle PTY process exit."""
        tw = self._terminal_widgets.get(pane_id)
        if tw is not None:
            tw.feed(f"\r\n[Process exited with code {exit_code}]\r\n".encode("utf-8"))

    # ------------------------------------------------------------------ #
    #  Status Integration                                                  #
    # ------------------------------------------------------------------ #

    def _on_state_changed(self, pane_id: str, state: str) -> None:
        """Update sidebar workspace state when Claude Code state changes."""
        if self._workspace:
            self._sidebar.update_workspace_state(
                self._workspace.id, PaneState(state)
            )

    def _on_usage_updated(self, data: dict) -> None:
        """Update status bar usage from UsageMonitor."""
        self._status_bar.update_usage(
            data.get("ctx", 0.0),
            data.get("5h", 0.0),
            data.get("7d", 0.0),
        )

    def _on_theme_changed(self, colors: dict) -> None:
        """Re-apply theme to all terminal widgets when theme changes."""
        # Update the global COLORS dict so terminal widgets pick up new values
        from src.theme.tokens import COLORS
        COLORS.update(colors)
        # Trigger repaint on all terminal widgets
        for tw in self._terminal_widgets.values():
            tw.update()

    # ------------------------------------------------------------------ #
    #  Settings handlers                                                   #
    # ------------------------------------------------------------------ #

    def _on_font_applied(self, family: str, size: int) -> None:
        """Update all terminal widgets when font changes."""
        for tw in self._terminal_widgets.values():
            cfg = TerminalConfig(
                font_family=family,
                font_size=size,
                line_spacing=tw._config.line_spacing,
                scrollback_lines=tw._config.scrollback_lines,
                cursor_blink=tw._config.cursor_blink,
            )
            tw.set_config(cfg)

    def _on_theme_applied(self, theme_name: str) -> None:
        """Switch the active theme and reapply QSS."""
        app = QApplication.instance()
        if app is not None:
            tm = app.property("theme_manager")
            if tm is not None:
                try:
                    tm.set_active(theme_name)
                    tm.apply_theme(app)
                except KeyError:
                    pass

    def _on_terminal_applied(
        self, line_spacing: float, scrollback: int, cursor_blink: bool
    ) -> None:
        """Update all terminal widgets when terminal settings change."""
        for tw in self._terminal_widgets.values():
            cfg = TerminalConfig(
                font_family=tw._config.font_family,
                font_size=tw._config.font_size,
                line_spacing=line_spacing,
                scrollback_lines=scrollback,
                cursor_blink=cursor_blink,
            )
            tw.set_config(cfg)

    def _bring_to_front(self) -> None:
        """Bring the main window to the front (notification action)."""
        self.raise_()
        self.activateWindow()
        self.showNormal()

    # ------------------------------------------------------------------ #
    #  Layout save/restore                                                 #
    # ------------------------------------------------------------------ #

    def _restore_layout_or_default(self) -> None:
        """Restore saved layout from config, or create a default tab."""
        layouts = self._config.load_layout()
        if layouts:
            # Restore workspaces into sidebar
            for ws_data in layouts:
                workspace = self._config.restore_workspace_from_layout(ws_data)
                self._sidebar.add_workspace(workspace)
            # Select the first workspace
            if layouts:
                first_ws = self._config.restore_workspace_from_layout(layouts[0])
                self.set_workspace(first_ws)
        else:
            # No saved layout — start with a single default tab
            self._tab_bar.add_tab("Terminal")

    def _save_layout(self) -> None:
        """Save current workspace layouts to config."""
        all_layouts = []
        for ws in self._sidebar._workspaces:
            self._config.save_workspace_layout(ws)
        # Collect all saved layouts
        all_layouts = self._config.load_layout()
        self._config.save_layout(all_layouts)
        self._config.save()

    # ------------------------------------------------------------------ #
    #  Lifecycle                                                           #
    # ------------------------------------------------------------------ #

    def closeEvent(self, event: QCloseEvent) -> None:
        """Save layout and clean up all resources on window close."""
        self._save_layout()
        self._pty_manager.kill_all()
        self._usage_monitor.stop()
        self._session_watcher.stop()
        super().closeEvent(event)
