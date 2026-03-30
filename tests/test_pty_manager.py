"""Tests for PTY manager."""

import pytest


def test_pty_manager_init():
    """Test PtyManager can be instantiated (no QApp needed for basic init)."""
    pytest.importorskip("PyQt6")
    from src.terminal.pty_manager import PtyManager
    manager = PtyManager()
    assert manager._processes == {}
