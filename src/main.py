"""JBTerminal — AI CLI desktop terminal application."""

import logging
import os
import sys
import traceback

# Ensure Qt can find its platform plugins
try:
    import PyQt6
    _qt_plugin_dir = os.path.join(os.path.dirname(PyQt6.__file__), "Qt6", "plugins")
    if os.path.isdir(_qt_plugin_dir):
        os.environ.setdefault("QT_PLUGIN_PATH", _qt_plugin_dir)
except ImportError:
    pass

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
