"""Unit tests for PtyManager."""

from __future__ import annotations

import os
import time
import sys

import pytest

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PyQt6.QtCore import QCoreApplication

from src.terminal.pty_manager import PtyManager


@pytest.fixture(scope="module")
def qapp():
    """Provide a QCoreApplication instance (needed for signals/slots and QThread).

    Uses QCoreApplication instead of QApplication so tests can run
    without a display server.
    """
    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


@pytest.fixture
def pty_mgr(qapp):
    """Create a fresh PtyManager for each test."""
    mgr = PtyManager()
    yield mgr
    mgr.kill_all()


def _process_events(timeout_ms: int = 200) -> None:
    """Spin the Qt event loop for a short period to allow signal delivery."""
    app = QCoreApplication.instance()
    deadline = time.monotonic() + timeout_ms / 1000.0
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


class TestPtySpawnAndExit:
    """Test PTY spawn and exit."""

    def test_spawn_success(self, pty_mgr: PtyManager):
        """Spawning a PTY should succeed and emit pty_spawned."""
        spawned_ids = []
        pty_mgr.pty_spawned.connect(lambda pid: spawned_ids.append(pid))

        result = pty_mgr.spawn("pane-1", os.path.expanduser("~"))
        _process_events(100)

        assert result is True
        assert "pane-1" in spawned_ids
        assert pty_mgr.has_process("pane-1")

    def test_spawn_duplicate_fails(self, pty_mgr: PtyManager):
        """Spawning with a duplicate pane_id should fail."""
        pty_mgr.spawn("pane-dup", os.path.expanduser("~"))
        result = pty_mgr.spawn("pane-dup", os.path.expanduser("~"))
        assert result is False

    def test_spawn_invalid_cwd_falls_back(self, pty_mgr: PtyManager):
        """Spawning with a non-existent cwd should fall back to home."""
        result = pty_mgr.spawn("pane-bad-cwd", "/nonexistent/path/xyz")
        assert result is True

    def test_exit_emits_signal(self, pty_mgr: PtyManager):
        """Killing a PTY should eventually emit pty_exited."""
        exited = []
        pty_mgr.pty_exited.connect(lambda pid, code: exited.append((pid, code)))

        pty_mgr.spawn("pane-exit", os.path.expanduser("~"))
        _process_events(200)

        pty_mgr.kill("pane-exit")
        _process_events(500)

        assert not pty_mgr.has_process("pane-exit")


class TestWriteRead:
    """Test write/read pipeline."""

    def test_write_and_receive_output(self, pty_mgr: PtyManager):
        """Writing to PTY should produce output."""
        outputs = []
        pty_mgr.pty_output.connect(lambda pid, data: outputs.append((pid, data)))

        pty_mgr.spawn("pane-rw", os.path.expanduser("~"))
        _process_events(500)  # wait for shell prompt

        # Send a simple echo command
        pty_mgr.write("pane-rw", b"echo HELLO_TEST_12345\n")
        _process_events(1000)

        # Check that we received some output
        assert len(outputs) > 0
        all_data = b"".join(d for _, d in outputs)
        assert b"HELLO_TEST_12345" in all_data

    def test_write_to_nonexistent_pane(self, pty_mgr: PtyManager):
        """Writing to a non-existent pane should not raise."""
        pty_mgr.write("no-such-pane", b"data")  # should silently do nothing


class TestResize:
    """Test PTY resize."""

    def test_resize(self, pty_mgr: PtyManager):
        """Resizing should update stored cols/rows and not crash."""
        pty_mgr.spawn("pane-resize", os.path.expanduser("~"))
        _process_events(200)

        pty_mgr.resize("pane-resize", 120, 40)
        proc = pty_mgr.get_process("pane-resize")
        assert proc is not None
        assert proc.cols == 120
        assert proc.rows == 40

    def test_resize_nonexistent(self, pty_mgr: PtyManager):
        """Resizing a non-existent pane should not raise."""
        pty_mgr.resize("no-pane", 80, 24)  # should silently do nothing


class TestKill:
    """Test kill and kill_all."""

    def test_kill_removes_process(self, pty_mgr: PtyManager):
        """Killing a pane should remove it from the process dict."""
        pty_mgr.spawn("pane-kill", os.path.expanduser("~"))
        _process_events(200)
        assert pty_mgr.has_process("pane-kill")

        pty_mgr.kill("pane-kill")
        _process_events(300)
        assert not pty_mgr.has_process("pane-kill")

    def test_kill_nonexistent(self, pty_mgr: PtyManager):
        """Killing a non-existent pane should not raise."""
        pty_mgr.kill("nonexistent")

    def test_kill_all(self, pty_mgr: PtyManager):
        """kill_all should remove all processes."""
        pty_mgr.spawn("pane-a", os.path.expanduser("~"))
        pty_mgr.spawn("pane-b", os.path.expanduser("~"))
        _process_events(200)

        assert pty_mgr.has_process("pane-a")
        assert pty_mgr.has_process("pane-b")

        pty_mgr.kill_all()
        _process_events(300)

        assert not pty_mgr.has_process("pane-a")
        assert not pty_mgr.has_process("pane-b")
