"""Tests for Team D — Status & Features modules (non-GUI subset).

GUI widget tests require a running QApplication and are in
``test_status_features_gui.py``.  This file contains only tests that
do not need a display or QApplication.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.settings.config import Config


# --------------------------------------------------------------------------
# Config
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
        assert cfg.remove_workspace(ws_id) is True
        assert len(cfg.get_workspaces()) == 0
        assert cfg.remove_workspace("nonexistent") is False

    def test_notifications_global(self, tmp_path: Path):
        cfg = Config(tmp_path / "cfg.json")
        cfg.load()
        assert cfg.get_notifications_enabled() is True
        cfg.set_notifications_enabled(False)
        assert cfg.get_notifications_enabled() is False

    def test_notifications_per_workspace(self, tmp_path: Path):
        cfg = Config(tmp_path / "cfg.json")
        cfg.load()
        ws_id = cfg.add_workspace("ws", "/tmp/ws")
        cfg.set_notifications_enabled(True, ws_id)
        # Global is True (default), workspace override also True
        assert cfg.get_notifications_enabled(ws_id) is True

        # Turn off globally
        cfg.set_notifications_enabled(False)
        # Workspace override should still be True
        assert cfg.get_notifications_enabled(ws_id) is True

        # Turn off workspace specifically
        cfg.set_notifications_enabled(False, ws_id)
        assert cfg.get_notifications_enabled(ws_id) is False

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

    def test_save_creates_dirs(self, tmp_path: Path):
        path = tmp_path / "sub" / "deep" / "cfg.json"
        cfg = Config(path)
        cfg.load()
        cfg.set_theme("Custom")
        cfg.save()
        assert path.exists()

    def test_get_with_default(self, tmp_path: Path):
        cfg = Config(tmp_path / "cfg.json")
        cfg.load()
        assert cfg.get("nonexistent_key", "fallback") == "fallback"
        cfg.set("custom_key", 42)
        assert cfg.get("custom_key") == 42


# --------------------------------------------------------------------------
# StateDetector — logic-only tests (no signal emission)
# --------------------------------------------------------------------------


class TestStateDetectorLogic:
    """Test the _detect method directly without needing QApplication."""

    def _make_detector(self):
        # Import at test time to avoid module-level QApplication issues
        # We need to ensure QApplication exists before creating QObject
        # So we skip these if import fails
        pytest.importorskip("PyQt6.QtWidgets")
        # Just test the static _detect patterns
        from src.status.state_detector import StateDetector
        return StateDetector.__new__(StateDetector)

    def test_detect_idle(self):
        det = self._make_detector()
        assert det._detect("user@host ~ $ ") == "idle"

    def test_detect_thinking(self):
        det = self._make_detector()
        assert det._detect("Thinking...") == "thinking"

    def test_detect_tool_use(self):
        det = self._make_detector()
        assert det._detect("Reading: /some/file.py") == "tool_use"

    def test_detect_error(self):
        det = self._make_detector()
        assert det._detect("Error: something failed") == "error"

    def test_detect_done(self):
        det = self._make_detector()
        assert det._detect("\u2713 Task completed") == "done"

    def test_detect_waiting(self):
        det = self._make_detector()
        assert det._detect("Do you want to proceed? [Y/n] ") == "waiting"

    def test_detect_no_match(self):
        det = self._make_detector()
        assert det._detect("random text with no patterns") is None


# --------------------------------------------------------------------------
# SessionWatcher — parse_tail logic (no QFileSystemWatcher needed)
# --------------------------------------------------------------------------


class TestSessionWatcherParseTail:
    def test_parse_valid_jsonl(self, tmp_path: Path):
        from src.status.session_watcher import SessionWatcher
        # Create instance without starting watcher
        watcher = SessionWatcher.__new__(SessionWatcher)

        jsonl = tmp_path / "session.jsonl"
        lines = [
            json.dumps({
                "type": "assistant",
                "message": {
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                    "content": []
                }
            }),
            json.dumps({
                "type": "tool_result",
                "message": {
                    "content": [{"type": "tool_use", "name": "Bash"}]
                }
            }),
            json.dumps({
                "type": "error",
                "error": {"message": "rate limited"}
            }),
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

    def test_parse_missing_file(self, tmp_path: Path):
        from src.status.session_watcher import SessionWatcher
        watcher = SessionWatcher.__new__(SessionWatcher)
        result = watcher._parse_tail(str(tmp_path / "nonexistent.jsonl"))
        assert result is None

    def test_read_tail(self):
        from src.status.session_watcher import SessionWatcher
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for i in range(100):
                f.write(f"line {i}\n")
            f.flush()
            lines = SessionWatcher._read_tail(f.name, 10)
            assert len(lines) == 10
            assert "line 90\n" in lines
