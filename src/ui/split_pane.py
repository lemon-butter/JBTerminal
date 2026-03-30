"""Split pane container — recursive binary tree rendering."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from src.models.enums import SplitDirection
from src.models.pane_tree import (
    PaneLeaf,
    PaneNode,
    PaneSplit,
    find_parent,
    get_all_leaves,
    replace_node,
)
from src.ui.pane_divider import StyledSplitter
from src.ui.pane_view import PaneView


class SplitPaneContainer(QWidget):
    """Renders PaneNode binary tree as nested QSplitters."""

    pane_split_requested = pyqtSignal(str, str)  # (pane_id, direction)
    pane_close_requested = pyqtSignal(str)        # (pane_id)
    pane_focused = pyqtSignal(str)                # (pane_id)
    tab_dropped_on_pane = pyqtSignal(str, int)    # (pane_id, tab_index)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("split_pane")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # State
        self._root: PaneNode = PaneLeaf()
        self._pane_views: dict[str, PaneView] = {}
        self._active_pane_id: str = self._root.id
        self._root_widget: QWidget | None = None

        # Initial render
        self._rebuild()

    @property
    def root(self) -> PaneNode:
        return self._root

    def set_root(self, root: PaneNode) -> None:
        """Set a new pane tree root and rebuild the UI."""
        self._root = root
        leaves = get_all_leaves(root)
        if leaves and self._active_pane_id not in [l.id for l in leaves]:
            self._active_pane_id = leaves[0].id
        self._rebuild()

    def get_active_pane(self) -> PaneView | None:
        """Return the currently active PaneView."""
        return self._pane_views.get(self._active_pane_id)

    def get_pane_view(self, pane_id: str) -> PaneView | None:
        """Return PaneView by pane_id."""
        return self._pane_views.get(pane_id)

    def split_pane(self, pane_id: str, direction: SplitDirection) -> str | None:
        """Split the pane with given id. Returns new pane id, or None on failure."""
        leaves = get_all_leaves(self._root)
        if pane_id not in [l.id for l in leaves]:
            return None

        new_leaf = PaneLeaf()
        old_leaf = PaneLeaf(id=pane_id)  # preserve id
        # Find the old leaf's name
        for lf in leaves:
            if lf.id == pane_id:
                old_leaf = PaneLeaf(id=lf.id, name=lf.name)
                break

        split_node = PaneSplit(
            direction=direction,
            first=old_leaf,
            second=new_leaf,
        )

        self._root = replace_node(self._root, pane_id, split_node)
        self._active_pane_id = new_leaf.id
        self._rebuild()
        return new_leaf.id

    def close_pane(self, pane_id: str) -> bool:
        """Close pane with given id. Returns True on success."""
        leaves = get_all_leaves(self._root)
        if len(leaves) <= 1:
            return False  # Cannot close the last pane

        parent = find_parent(self._root, pane_id)
        if parent is None:
            # pane_id is root leaf — shouldn't happen if len > 1
            return False

        # Replace parent with the sibling
        if parent.first.id == pane_id:
            sibling = parent.second
        elif parent.second.id == pane_id:
            sibling = parent.first
        else:
            return False

        if parent.id == self._root.id:
            self._root = sibling
        else:
            self._root = replace_node(self._root, parent.id, sibling)

        # Update active pane
        remaining = get_all_leaves(self._root)
        if self._active_pane_id == pane_id and remaining:
            self._active_pane_id = remaining[0].id

        self._rebuild()
        return True

    def set_active_pane(self, pane_id: str) -> None:
        """Set the active pane by id."""
        if pane_id in self._pane_views:
            self._active_pane_id = pane_id
            self.pane_focused.emit(pane_id)

    def _rebuild(self) -> None:
        """Rebuild the widget tree from the pane model."""
        # Remove old root widget
        if self._root_widget is not None:
            self._layout.removeWidget(self._root_widget)
            self._root_widget.deleteLater()
            self._root_widget = None

        self._pane_views.clear()

        # Build new widget tree
        self._root_widget = self._build_widget(self._root)
        self._layout.addWidget(self._root_widget)

        # Update close button visibility
        leaves = get_all_leaves(self._root)
        single = len(leaves) <= 1
        for pv in self._pane_views.values():
            pv.set_close_visible(not single)

    def _build_widget(self, node: PaneNode) -> QWidget:
        """Recursively build QWidget tree from PaneNode tree."""
        if isinstance(node, PaneLeaf):
            pane_view = PaneView(pane_id=node.id, name=node.name)
            pane_view.split_requested.connect(self._on_split_requested)
            pane_view.close_requested.connect(self._on_close_requested)
            pane_view.focused.connect(self._on_pane_focused)
            pane_view.tab_dropped.connect(self._on_tab_dropped)
            self._pane_views[node.id] = pane_view
            return pane_view

        # PaneSplit
        splitter = StyledSplitter(node.direction)
        first_widget = self._build_widget(node.first)
        second_widget = self._build_widget(node.second)
        splitter.addWidget(first_widget)
        splitter.addWidget(second_widget)

        # Set ratio
        total = 1000
        first_size = int(total * node.ratio)
        second_size = total - first_size
        splitter.setSizes([first_size, second_size])

        return splitter

    def _on_split_requested(self, pane_id: str, direction: str) -> None:
        """Handle split request from PaneView."""
        self.pane_split_requested.emit(pane_id, direction)

    def _on_close_requested(self, pane_id: str) -> None:
        """Handle close request from PaneView."""
        self.pane_close_requested.emit(pane_id)

    def _on_pane_focused(self, pane_id: str) -> None:
        """Handle pane focus from PaneView."""
        self._active_pane_id = pane_id
        self.pane_focused.emit(pane_id)

    def _on_tab_dropped(self, pane_id: str, tab_index: int) -> None:
        """Handle tab dropped onto a pane — forward to MainWindow."""
        self.tab_dropped_on_pane.emit(pane_id, tab_index)
