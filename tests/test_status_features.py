"""Tests for Team D — Status & Features modules."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

from src.models.enums import PaneState
from src.settings.config import Config


# --------------------------------------------------------------------------
# Helper: check if we can create a QApplication
# --------------------------------------------------------------------------

def _can_create_qapp() -> bool:
    """Return True if a QApplication can be created in this environment."""
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            return True
        # Try creating one — may abort on headless macOS
        app = QApplication([])
        return True
    except Exception:
        return False


_HAS_QAPP = _can_create_qapp()
needs_gui = pytest.mark.skipif(not _HAS_QAPP, reason="No display / QApplication not available")


# --------------------------------------------------------------------------
# Config (no GUI needed)
# --------------------------------------------------------------------------


class TestConfig:
    def test_defaults(self, tmp_path: Path):
        cfg = Config(tmp_path / "cfg.json")
        cfg.load()
        assert cfg.get_theme() == "Neon Dark"
        font = cfg.get_font()
        assert font["family"] == "JetBrains Mono"
        assert font["size"] == 14

    def test_save_load(self, tmp_path: Path):
        path = tmp_path / "cfg.json"
        cfg = Config(path)
        cfg.load()
        cfg.set_font("Menlo", 16)
        cfg.set_theme("Monokai")
        cfg.save()

        cfg2 = Config(path)
        cfg2.load()
        assert cfg2.get_theme() == "Monokai"
        assert cfg2.get_font()["family"] == "Menlo"
        assert cfg2.get_font()["size"] == 16

    def test_workspaces(self, tmp_path: Path):
        cfg = Config(tmp_path / "cfg.json")
        cfg.load()
        ws_id = cfg.add_workspace("test", "/tmp/test")
        assert len(cfg.get_workspaces()) == 1
        assert cfg.get_workspaces()[0]["id"] == ws_id
        cfg.remove_workspace(ws_id)
        assert len(cfg.get_workspaces()) == 0

    def test_notifications(self, tmp_path: Path):
        cfg = Config(tmp_path / "cfg.json")
        cfg.load()
        assert cfg.get_notifications_enabled() is True
        cfg.set_notifications_enabled(False)
        assert cfg.get_notifications_enabled() is False

        ws_id = cfg.add_workspace("ws", "/tmp/ws")
        cfg.set_notifications_enabled(True, ws_id)
        # Global is off, but workspace override is on
        assert cfg.get_notifications_enabled(ws_id) is True

    def test_remove_workspace_cleans_notifications(self, tmp_path: Path):
        cfg = Config(tmp_path / "cfg.json")
        cfg.load()
        ws_id = cfg.add_workspace("ws", "/tmp/ws")
        cfg.set_notifications_enabled(False, ws_id)
        cfg.remove_workspace(ws_id)
        # After removal, should fall back to global default (True)
        assert cfg.get_notifications_enabled(ws_id) is True

    def test_load_corrupted(self, tmp_path: Path):
        path = tmp_path / "cfg.json"
        path.write_text("NOT JSON!!!")
        cfg = Config(path)
        cfg.load()  # should not raise
        assert cfg.get_theme() == "Neon Dark"


# --------------------------------------------------------------------------
# StateDetector (pure logic, needs QObject but no widgets)
# --------------------------------------------------------------------------


class TestStateDetector:
    @needs_gui
    def test_idle_detection(self, qapp):
        from src.status.state_detector import StateDetector
        det = StateDetector()
        states = []
        det.state_changed.connect(lambda pid, s: states.append((pid, s)))
        det.feed("p1", b"user@host ~ $ ")
        assert len(states) == 1
        assert states[0] == ("p1", PaneState.IDLE.value)

    @needs_gui
    def test_thinking_detection(self, qapp):
        from src.status.state_detector import StateDetector
        det = StateDetector()
        states = []
        det.state_changed.connect(lambda pid, s: states.append((pid, s)))
        det.feed("p1", b"Thinking...")
        assert len(states) == 1
        assert states[0] == ("p1", PaneState.THINKING.value)

    @needs_gui
    def test_tool_use_detection(self, qapp):
        from src.status.state_detector import StateDetector
        det = StateDetector()
        states = []
        det.state_changed.connect(lambda pid, s: states.append((pid, s)))
        det.feed("p1", b"Reading: /some/file.py")
        assert states[-1][1] == PaneState.TOOL_USE.value

    @needs_gui
    def test_error_detection(self, qapp):
        from src.status.state_detector import StateDetector
        det = StateDetector()
        states = []
        det.state_changed.connect(lambda pid, s: states.append((pid, s)))
        det.feed("p1", b"Error: something went wrong")
        assert states[-1][1] == PaneState.ERROR.value

    @needs_gui
    def test_done_detection(self, qapp):
        from src.status.state_detector import StateDetector
        det = StateDetector()
        states = []
        det.state_changed.connect(lambda pid, s: states.append((pid, s)))
        det.feed("p1", "\u2713 Done".encode("utf-8"))
        assert states[-1][1] == PaneState.DONE.value

    @needs_gui
    def test_waiting_detection(self, qapp):
        from src.status.state_detector import StateDetector
        det = StateDetector()
        states = []
        det.state_changed.connect(lambda pid, s: states.append((pid, s)))
        det.feed("p1", b"Do you want to proceed? [Y/n] ")
        assert states[-1][1] == PaneState.WAITING.value

    @needs_gui
    def test_debounce_same_state(self, qapp):
        from src.status.state_detector import StateDetector
        det = StateDetector()
        states = []
        det.state_changed.connect(lambda pid, s: states.append((pid, s)))
        det.feed("p1", b"$ ")
        det.feed("p1", b"$ ")  # same state, within debounce
        assert len(states) == 1

    @needs_gui
    def test_get_state(self, qapp):
        from src.status.state_detector import StateDetector
        det = StateDetector()
        assert det.get_state("missing") == PaneState.IDLE.value
        det.feed("p1", b"Error: fail")
        assert det.get_state("p1") == PaneState.ERROR.value


# --------------------------------------------------------------------------
# SessionWatcher
# --------------------------------------------------------------------------


class TestSessionWatcher:
    @needs_gui
    def test_parse_tail(self, qapp, tmp_path: Path):
        from src.status.session_watcher import SessionWatcher
        watcher = SessionWatcher(projects_dir=tmp_path)
        jsonl = tmp_path / "session.jsonl"
        lines = [
            json.dumps({"type": "assistant", "message": {"usage": {"input_tokens": 100, "output_tokens": 50}}}),
            json.dumps({"type": "tool_result", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}}),
            json.dumps({"type": "error", "error": {"message": "rate limited"}}),
            "NOT VALID JSON",
        ]
        jsonl.write_text("\n".join(lines) + "\n")

        result = watcher._parse_tail(str(jsonl))
        assert result is not None
        assert result["total_input_tokens"] == 100
        assert result["total_output_tokens"] == 50
        assert "Bash" in result["tool_uses"]
        assert len(result["errors"]) == 1
        assert result["last_type"] == "error"


# --------------------------------------------------------------------------
# StatusBar
# --------------------------------------------------------------------------


class TestStatusBar:
    @needs_gui
    def test_creation(self, qapp):
        from src.status.status_bar import StatusBar
        bar = StatusBar()
        assert bar.objectName() == "status_bar"
        assert bar.fixedHeight() == 28 or bar.maximumHeight() == 28

    @needs_gui
    def test_update_usage(self, qapp):
        from src.status.status_bar import StatusBar
        bar = StatusBar()
        bar.update_usage(0.5, 0.75, 0.1)
        assert bar._ctx_bar._value == 0.5
        assert bar._fh_bar._value == 0.75
        assert bar._sd_bar._value == 0.1

    @needs_gui
    def test_update_task_duration(self, qapp):
        from src.status.status_bar import StatusBar
        bar = StatusBar()
        bar.update_task_duration(65)
        assert bar._duration_label.text() == "01:05"
        bar.update_task_duration(3661)
        assert bar._duration_label.text() == "1:01:01"

    @needs_gui
    def test_settings_signal(self, qapp):
        from src.status.status_bar import StatusBar
        bar = StatusBar()
        signals = []
        bar.settings_clicked.connect(lambda: signals.append(True))
        bar._settings_btn.click()
        assert len(signals) == 1


# --------------------------------------------------------------------------
# UsageMonitor
# --------------------------------------------------------------------------


class TestUsageMonitor:
    @needs_gui
    def test_creation(self, qapp):
        from src.status.usage_monitor import UsageMonitor
        mon = UsageMonitor()
        assert hasattr(mon, "usage_updated")


# --------------------------------------------------------------------------
# Notifier
# --------------------------------------------------------------------------


class TestNotifier:
    @needs_gui
    def test_creation(self, qapp):
        from src.notifications.notifier import Notifier
        n = Notifier()
        assert isinstance(n, Notifier)

    @needs_gui
    def test_osascript_fallback(self, qapp, monkeypatch):
        from src.notifications.notifier import Notifier
        import subprocess
        n = Notifier()
        n._use_pyobjc = False
        calls = []
        monkeypatch.setattr(
            subprocess, "Popen",
            lambda *a, **kw: calls.append(a)
        )
        n.notify("Test", "Body", sound=False)
        assert len(calls) == 1


# --------------------------------------------------------------------------
# FontPicker
# --------------------------------------------------------------------------


class TestFontPicker:
    @needs_gui
    def test_creation(self, qapp):
        from src.settings.font_picker import FontPicker
        fp = FontPicker()
        family, size = fp.get_font()
        assert isinstance(family, str)
        assert isinstance(size, int)

    @needs_gui
    def test_set_font(self, qapp):
        from src.settings.font_picker import FontPicker
        fp = FontPicker()
        fp.set_font("Menlo", 18)
        _, size = fp.get_font()
        assert size == 18

    @needs_gui
    def test_signal(self, qapp):
        from src.settings.font_picker import FontPicker
        fp = FontPicker()
        received = []
        fp.font_changed.connect(lambda f, s: received.append((f, s)))
        fp._size_spin.setValue(20)
        assert len(received) >= 1
        assert received[-1][1] == 20


# --------------------------------------------------------------------------
# ThemePicker
# --------------------------------------------------------------------------


class TestThemePicker:
    @needs_gui
    def test_creation(self, qapp):
        from src.settings.theme_picker import ThemePicker
        tp = ThemePicker()
        assert tp._list.count() >= 2

    @needs_gui
    def test_set_theme(self, qapp):
        from src.settings.theme_picker import ThemePicker
        tp = ThemePicker()
        tp.set_theme("Neon Dark")
        assert tp.get_theme() == "Neon Dark"

    @needs_gui
    def test_signal(self, qapp):
        from src.settings.theme_picker import ThemePicker
        tp = ThemePicker()
        received = []
        tp.theme_selected.connect(lambda n: received.append(n))
        tp.set_theme("Dracula")
        assert "Dracula" in received


# --------------------------------------------------------------------------
# SettingsDialog
# --------------------------------------------------------------------------


class TestSettingsDialog:
    @needs_gui
    def test_creation(self, qapp, tmp_path: Path):
        from src.settings.settings_dialog import SettingsDialog
        cfg = Config(tmp_path / "cfg.json")
        cfg.load()
        dlg = SettingsDialog(config=cfg)
        assert dlg.objectName() == "settings_dialog"

    @needs_gui
    def test_apply(self, qapp, tmp_path: Path):
        from src.settings.settings_dialog import SettingsDialog
        cfg_path = tmp_path / "cfg.json"
        cfg = Config(cfg_path)
        cfg.load()
        dlg = SettingsDialog(config=cfg)
        dlg._theme_picker.set_theme("Dracula")
        dlg._apply()
        assert cfg.get_theme() == "Dracula"
        assert cfg_path.exists()
