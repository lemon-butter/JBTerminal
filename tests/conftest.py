"""Shared test fixtures."""

import os
import pytest


def _ensure_qt_platform():
    """Set up Qt platform plugin path for headless/CI environments."""
    if "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    try:
        import PyQt6
        plugin_dir = os.path.join(
            os.path.dirname(PyQt6.__file__), "Qt6", "plugins"
        )
        if os.path.isdir(plugin_dir):
            os.environ.setdefault("QT_PLUGIN_PATH", plugin_dir)
    except ImportError:
        pass


_ensure_qt_platform()

from PyQt6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    """Provide a QApplication instance for widget tests."""
    app = QApplication.instance() or QApplication([])
    yield app
