"""Application setup — QApplication configuration and theme loading."""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from src.theme.theme_manager import ThemeManager
from src.theme.presets.default_dark import PRESET as DARK_PRESET
from src.theme.presets.default_light import PRESET as LIGHT_PRESET


def create_app(argv: list[str] | None = None) -> QApplication:
    """Create and configure the QApplication instance."""
    app = QApplication(argv or [])
    app.setApplicationName("JBTerminal")
    app.setOrganizationName("JBTerminal")

    # --- Theme ---
    theme_manager = ThemeManager()
    theme_manager.load_preset(DARK_PRESET["name"], DARK_PRESET["colors"])
    theme_manager.load_preset(LIGHT_PRESET["name"], LIGHT_PRESET["colors"])
    theme_manager.set_active(DARK_PRESET["name"])
    theme_manager.apply_theme(app)

    # Store on app so other code can access it
    app.setProperty("theme_manager", theme_manager)  # type: ignore[arg-type]

    return app
