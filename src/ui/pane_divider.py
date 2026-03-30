"""Pane divider — styled QSplitter handle for split resize.

QSplitter handles this natively. This module provides a helper to style
QSplitter handles consistently with the design system (4px width, cursor change).
"""

from __future__ import annotations

from PyQt6.QtWidgets import QSplitter, QSplitterHandle

from src.models.enums import SplitDirection


class StyledSplitterHandle(QSplitterHandle):
    """Custom QSplitter handle with design-system styling."""

    def __init__(self, orientation: int, parent: QSplitter) -> None:
        super().__init__(orientation, parent)
        self.setObjectName("pane_divider")


class StyledSplitter(QSplitter):
    """QSplitter that creates StyledSplitterHandle instances."""

    def __init__(self, direction: SplitDirection, parent: object = None) -> None:
        from PyQt6.QtCore import Qt
        orientation = (
            Qt.Orientation.Horizontal
            if direction == SplitDirection.HORIZONTAL
            else Qt.Orientation.Vertical
        )
        super().__init__(orientation, parent)
        self.setHandleWidth(4)
        self.setChildrenCollapsible(False)
        self.setObjectName("pane_divider")

    def createHandle(self) -> QSplitterHandle:
        return StyledSplitterHandle(self.orientation(), self)
