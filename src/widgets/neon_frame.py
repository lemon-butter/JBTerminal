"""Neon glow frame — container with glow border."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QWidget


class NeonFrame(QFrame):
    """Frame container with neon glow border."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
