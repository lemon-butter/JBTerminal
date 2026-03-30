"""Neon progress bar — usage indicator with gradient colors."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget


class NeonProgressBar(QWidget):
    """Progress bar with neon gradient (usage_low → usage_critical)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
