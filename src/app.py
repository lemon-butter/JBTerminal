"""Application setup — QApplication configuration and theme loading."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QApplication

from src.theme.tokens import COLORS, FONTS


def create_app(argv: list[str] | None = None) -> QApplication:
    """Create and configure the QApplication instance."""
    app = QApplication(argv or [])
    app.setApplicationName("JBTerminal")
    app.setOrganizationName("JBTerminal")

    # Load global QSS
    qss_path = Path(__file__).parent / "theme" / "neon_theme.qss"
    if qss_path.exists():
        qss = qss_path.read_text()
        # Replace token placeholders with actual values
        for key, value in COLORS.items():
            qss = qss.replace(f"@{key}", value)
        app.setStyleSheet(qss)

    return app
