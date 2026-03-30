"""Workspace and tab state model."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from src.models.enums import PaneState
from src.models.pane_tree import PaneLeaf, PaneNode


@dataclass
class WorkspaceTab:
    """A single terminal tab within a workspace."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Terminal"
    pane_root: PaneNode = field(default_factory=PaneLeaf)
    active_pane_id: str = ""
    state: PaneState = PaneState.IDLE

    def __post_init__(self) -> None:
        if not self.active_pane_id and isinstance(self.pane_root, PaneLeaf):
            self.active_pane_id = self.pane_root.id


@dataclass
class Workspace:
    """A project workspace with multiple tabs."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    path: str = ""
    tabs: list[WorkspaceTab] = field(default_factory=lambda: [WorkspaceTab()])
    active_tab_index: int = 0
    state: PaneState = PaneState.IDLE

    @property
    def active_tab(self) -> WorkspaceTab | None:
        if 0 <= self.active_tab_index < len(self.tabs):
            return self.tabs[self.active_tab_index]
        return None
