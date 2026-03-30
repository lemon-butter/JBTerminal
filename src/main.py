"""JBTerminal — AI CLI desktop terminal application."""

import logging
import sys
import traceback

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
