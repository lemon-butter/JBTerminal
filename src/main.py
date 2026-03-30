"""JBTerminal — AI CLI desktop terminal application."""

import logging
import os
import sys
import traceback

# Ensure Qt can find its platform plugins (dev mode and bundled .app)
def _find_qt_plugins() -> None:
    # 1. PyInstaller bundle: look relative to executable
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS  # type: ignore[attr-defined]
        candidate = os.path.join(base, "PyQt6", "Qt6", "plugins")
        if os.path.isdir(candidate):
            os.environ["QT_PLUGIN_PATH"] = candidate
            return
        # Also check Frameworks dir for BUNDLE mode
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(sys.executable)))
        candidate = os.path.join(app_dir, "Frameworks", "PyQt6", "Qt6", "plugins")
        if os.path.isdir(candidate):
            os.environ["QT_PLUGIN_PATH"] = candidate
            return
    # 2. Dev mode: use installed PyQt6
    try:
        import PyQt6
        candidate = os.path.join(os.path.dirname(PyQt6.__file__), "Qt6", "plugins")
        if os.path.isdir(candidate):
            os.environ.setdefault("QT_PLUGIN_PATH", candidate)
    except ImportError:
        pass

_find_qt_plugins()

from src.app import create_app
from src.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def main() -> int:
    app = create_app(sys.argv)
    window = MainWindow()
    window.show()
    try:
        return app.exec()
    except Exception:
        logger.critical("Unhandled exception in event loop:\n%s", traceback.format_exc())
        return 1
    finally:
        # Ensure cleanup runs even on abnormal exit
        try:
            window.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
