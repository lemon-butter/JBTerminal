"""Shared enums used across all modules."""

from enum import Enum


class PaneState(str, Enum):
    """Workspace/pane status for sidebar indicator."""
    IDLE = "idle"
    THINKING = "thinking"
    TOOL_USE = "tool_use"
    DONE = "done"
    ERROR = "error"
    WAITING = "waiting"


class SplitDirection(str, Enum):
    """Split pane direction."""
    HORIZONTAL = "horizontal"  # left/right
    VERTICAL = "vertical"      # top/bottom
