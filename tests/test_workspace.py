"""Tests for workspace model."""

from src.models.enums import PaneState
from src.models.workspace import Workspace, WorkspaceTab


def test_workspace_tab_default():
    tab = WorkspaceTab()
    assert tab.state == PaneState.IDLE
    assert tab.active_pane_id == tab.pane_root.id


def test_workspace_default():
    ws = Workspace(name="test", path="/tmp/test")
    assert len(ws.tabs) == 1
    assert ws.active_tab is ws.tabs[0]


def test_workspace_active_tab_none():
    ws = Workspace(name="test", path="/tmp")
    ws.active_tab_index = 99
    assert ws.active_tab is None
