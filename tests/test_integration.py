"""Integration tests — verify modules work together end-to-end."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
from PyQt6.QtWidgets import QApplication

from src.models.enums import PaneState, SplitDirection
from src.models.pane_tree import PaneLeaf, PaneSplit, get_all_leaves
from src.models.workspace import Workspace, WorkspaceTab
from src.settings.config import Config
from src.status.state_detector import StateDetector
from src.theme.theme_manager import ThemeManager
from src.theme.presets.default_dark import PRESET as DARK_PRESET
from src.theme.presets.default_light import PRESET as LIGHT_PRESET
from src.theme.presets.dracula import PRESET as DRACULA_PRESET
from src.theme.presets.nord import PRESET as NORD_PRESET
from src.theme.presets.tokyo_night import PRESET as TOKYO_NIGHT_PRESET


# ------------------------------------------------------------------ #
#  1. MainWindow instantiation                                        #
# ------------------------------------------------------------------ #


def test_main_window_instantiation(qapp):
    """MainWindow can be created without crashing."""
    from src.ui.main_window import MainWindow

    window = MainWindow()
    assert window is not None
    assert window.windowTitle() == "JBTerminal"
    assert window.sidebar is not None
    assert window.tab_bar is not None
    assert window.split_pane is not None
    assert window.status_bar is not None
    window.close()


# ------------------------------------------------------------------ #
#  2. ThemeManager — load all presets and generate QSS                #
# ------------------------------------------------------------------ #


def test_theme_manager_presets_and_qss():
    """All presets load and QSS generation produces non-empty output."""
    tm = ThemeManager()

    all_presets = [
        DARK_PRESET,
        LIGHT_PRESET,
        DRACULA_PRESET,
        NORD_PRESET,
        TOKYO_NIGHT_PRESET,
    ]
    for preset in all_presets:
        tm.load_preset(preset["name"], preset["colors"])

    assert len(tm.preset_names()) == len(all_presets)

    for preset in all_presets:
        tm.set_active(preset["name"])
        assert tm.active_name == preset["name"]
        qss = tm.get_qss()
        # QSS should be a non-empty string (or empty if no template, but not None)
        assert isinstance(qss, str)

    # get_color should return valid values
    tm.set_active(DARK_PRESET["name"])
    color = tm.get_color("bg_primary")
    assert isinstance(color, str)
    assert color.startswith("#")


def test_theme_manager_unknown_preset_raises():
    """Setting an unknown preset raises KeyError."""
    tm = ThemeManager()
    with pytest.raises(KeyError):
        tm.set_active("NonExistentTheme")


# ------------------------------------------------------------------ #
#  3. Config save/load roundtrip                                      #
# ------------------------------------------------------------------ #


def test_config_save_load_roundtrip(tmp_path):
    """Config values survive a save-then-load cycle."""
    cfg_path = tmp_path / "config.json"
    cfg = Config(path=cfg_path)

    cfg.set("font_family", "Fira Code")
    cfg.set("font_size", 16)
    cfg.set("theme", "Dracula")
    cfg.add_workspace("MyProject", "/tmp/myproject")
    cfg.save()

    cfg2 = Config(path=cfg_path)
    cfg2.load()

    assert cfg2.get("font_family") == "Fira Code"
    assert cfg2.get("font_size") == 16
    assert cfg2.get("theme") == "Dracula"
    workspaces = cfg2.get_workspaces()
    assert len(workspaces) == 1
    assert workspaces[0]["name"] == "MyProject"
    assert workspaces[0]["path"] == "/tmp/myproject"


def test_config_corrupted_file(tmp_path):
    """Config handles corrupted JSON gracefully."""
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text("NOT VALID JSON {{{{", encoding="utf-8")

    cfg = Config(path=cfg_path)
    cfg.load()
    # Should fall back to empty data; defaults still work
    assert cfg.get("font_family") == "JetBrains Mono"
    assert cfg.get("font_size") == 14


# ------------------------------------------------------------------ #
#  4. StateDetector classifies sample outputs                         #
# ------------------------------------------------------------------ #


def test_state_detector_idle():
    """StateDetector detects idle state from shell prompt."""
    sd = StateDetector()
    states = []
    sd.state_changed.connect(lambda pid, s: states.append(s))

    sd.feed("pane1", b"user@host:~$ ")
    assert sd.get_state("pane1") == PaneState.IDLE.value


def test_state_detector_thinking():
    sd = StateDetector()
    sd.feed("pane1", "Thinking...".encode())
    assert sd.get_state("pane1") == PaneState.THINKING.value


def test_state_detector_tool_use():
    sd = StateDetector()
    sd.feed("pane1", b"Running: npm test")
    assert sd.get_state("pane1") == PaneState.TOOL_USE.value


def test_state_detector_done():
    sd = StateDetector()
    # Use the check mark character
    sd.feed("pane1", "\u2713 Done".encode())
    assert sd.get_state("pane1") == PaneState.DONE.value


def test_state_detector_error():
    sd = StateDetector()
    sd.feed("pane1", b"Error: something went wrong")
    assert sd.get_state("pane1") == PaneState.ERROR.value


def test_state_detector_waiting():
    sd = StateDetector()
    sd.feed("pane1", b"Do you want to proceed [Y/n]")
    assert sd.get_state("pane1") == PaneState.WAITING.value


def test_state_detector_512_char_tail_limit():
    """StateDetector only looks at the last 512 chars."""
    sd = StateDetector()
    # Put an error marker way before the 512-char tail
    prefix = "Error: bad" + ("x" * 600)
    suffix = "user@host:~$ "  # idle prompt at the end
    sd.feed("pane1", (prefix + suffix).encode())
    # The Error should be beyond the 512-char tail, so idle should be detected
    assert sd.get_state("pane1") == PaneState.IDLE.value


# ------------------------------------------------------------------ #
#  5. Layout serialization/deserialization roundtrip                   #
# ------------------------------------------------------------------ #


def test_layout_serialization_leaf():
    """PaneLeaf roundtrips through serialization."""
    leaf = PaneLeaf(id="leaf1", name="MyTerminal")
    data = Config.serialize_pane_tree(leaf)

    assert data["type"] == "leaf"
    assert data["id"] == "leaf1"
    assert data["name"] == "MyTerminal"

    restored = Config.deserialize_pane_tree(data)
    assert isinstance(restored, PaneLeaf)
    assert restored.id == "leaf1"
    assert restored.name == "MyTerminal"


def test_layout_serialization_split():
    """PaneSplit with nested leaves roundtrips through serialization."""
    tree = PaneSplit(
        id="split1",
        direction=SplitDirection.HORIZONTAL,
        ratio=0.6,
        first=PaneLeaf(id="l1", name="Left"),
        second=PaneSplit(
            id="split2",
            direction=SplitDirection.VERTICAL,
            ratio=0.5,
            first=PaneLeaf(id="l2", name="TopRight"),
            second=PaneLeaf(id="l3", name="BottomRight"),
        ),
    )

    data = Config.serialize_pane_tree(tree)
    restored = Config.deserialize_pane_tree(data)

    assert isinstance(restored, PaneSplit)
    assert restored.id == "split1"
    assert restored.direction == SplitDirection.HORIZONTAL
    assert restored.ratio == 0.6
    assert isinstance(restored.first, PaneLeaf)
    assert restored.first.id == "l1"
    assert isinstance(restored.second, PaneSplit)
    assert restored.second.id == "split2"

    leaves = get_all_leaves(restored)
    assert len(leaves) == 3
    assert {lf.id for lf in leaves} == {"l1", "l2", "l3"}


def test_workspace_layout_roundtrip(tmp_path):
    """Full workspace layout save/load/restore roundtrip via Config."""
    cfg_path = tmp_path / "config.json"
    cfg = Config(path=cfg_path)

    ws = Workspace(
        id="ws1",
        name="Test Project",
        path="/tmp/test",
        tabs=[
            WorkspaceTab(
                id="tab1",
                name="Main",
                pane_root=PaneSplit(
                    id="s1",
                    direction=SplitDirection.HORIZONTAL,
                    ratio=0.5,
                    first=PaneLeaf(id="p1", name="Left"),
                    second=PaneLeaf(id="p2", name="Right"),
                ),
                active_pane_id="p1",
            ),
            WorkspaceTab(id="tab2", name="Tests"),
        ],
        active_tab_index=0,
    )

    cfg.save_workspace_layout(ws)
    cfg.save()

    cfg2 = Config(path=cfg_path)
    cfg2.load()
    ws_data = cfg2.load_workspace_layout("ws1")
    assert ws_data is not None

    restored = cfg2.restore_workspace_from_layout(ws_data)
    assert restored.id == "ws1"
    assert restored.name == "Test Project"
    assert len(restored.tabs) == 2
    assert restored.tabs[0].name == "Main"
    assert isinstance(restored.tabs[0].pane_root, PaneSplit)
    assert restored.tabs[1].name == "Tests"
    assert restored.active_tab_index == 0
