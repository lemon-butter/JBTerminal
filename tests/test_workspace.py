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


def test_add_tab():
    ws = Workspace(name="test", path="/tmp")
    assert len(ws.tabs) == 1
    new_tab = ws.add_tab("Second")
    assert len(ws.tabs) == 2
    assert new_tab.name == "Second"
    assert ws.active_tab_index == 1
    assert ws.active_tab is new_tab


def test_add_tab_default_name():
    ws = Workspace(name="test", path="/tmp")
    tab = ws.add_tab()
    assert tab.name == "Terminal"


def test_remove_tab():
    ws = Workspace(name="test", path="/tmp")
    ws.add_tab("Second")
    ws.add_tab("Third")
    assert len(ws.tabs) == 3

    removed = ws.remove_tab(1)
    assert removed is not None
    assert removed.name == "Second"
    assert len(ws.tabs) == 2


def test_remove_tab_invalid_index():
    ws = Workspace(name="test", path="/tmp")
    assert ws.remove_tab(-1) is None
    assert ws.remove_tab(99) is None


def test_remove_tab_last_tab():
    ws = Workspace(name="test", path="/tmp")
    assert len(ws.tabs) == 1
    assert ws.remove_tab(0) is None  # Cannot remove last tab
    assert len(ws.tabs) == 1


def test_remove_tab_adjusts_active_index():
    ws = Workspace(name="test", path="/tmp")
    ws.add_tab("Second")
    ws.add_tab("Third")
    # active_tab_index is 2 (Third)
    assert ws.active_tab_index == 2

    # Remove tab before active
    ws.remove_tab(0)
    assert ws.active_tab_index == 1  # adjusted down


def test_remove_tab_active_at_end():
    ws = Workspace(name="test", path="/tmp")
    ws.add_tab("Second")
    # active is index 1
    ws.remove_tab(1)
    assert ws.active_tab_index == 0
    assert len(ws.tabs) == 1


def test_rename_tab():
    ws = Workspace(name="test", path="/tmp")
    assert ws.rename_tab(0, "New Name") is True
    assert ws.tabs[0].name == "New Name"


def test_rename_tab_invalid_index():
    ws = Workspace(name="test", path="/tmp")
    assert ws.rename_tab(-1, "Bad") is False
    assert ws.rename_tab(99, "Bad") is False
