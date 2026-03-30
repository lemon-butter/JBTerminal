"""Split pane container — recursive binary tree rendering."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget


class SplitPaneContainer(QWidget):
    """Renders PaneNode binary tree as nested QSplitters."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("split_pane")
