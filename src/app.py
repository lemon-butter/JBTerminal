"""Application setup — QApplication configuration and theme loading."""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from src.theme.theme_manager import ThemeManager
from src.theme.presets.default_dark import PRESET as DARK_PRESET
from src.theme.presets.default_light import PRESET as LIGHT_PRESET
from src.theme.presets.dracula import PRESET as DRACULA_PRESET
from src.theme.presets.nord import PRESET as NORD_PRESET
from src.theme.presets.tokyo_night import PRESET as TOKYO_NIGHT_PRESET


def create_app(argv: list[str] | None = None) -> QApplication:
    """Create and configure the QApplication instance."""
    app = QApplication(argv or [])
    app.setApplicationName("JBTerminal")
    app.setOrganizationName("JBTerminal")

    # --- Theme ---
    theme_manager = ThemeManager()
    theme_manager.load_preset(DARK_PRESET["name"], DARK_PRESET["colors"])
    theme_manager.load_preset(LIGHT_PRESET["name"], LIGHT_PRESET["colors"])
    theme_manager.load_preset(DRACULA_PRESET["name"], DRACULA_PRESET["colors"])
    theme_manager.load_preset(NORD_PRESET["name"], NORD_PRESET["colors"])
    theme_manager.load_preset(TOKYO_NIGHT_PRESET["name"], TOKYO_NIGHT_PRESET["colors"])
    theme_manager.set_active(DARK_PRESET["name"])
    theme_manager.apply_theme(app)

    # Store on app as Python attribute (avoid QVariant/setProperty segfault)
    app._theme_manager = theme_manager  # type: ignore[attr-defined]

    # --- App icon ---
    try:
        from src.resources.icon import create_app_icon
        app.setWindowIcon(create_app_icon())
    except Exception:
        pass  # icon is optional, don't block startup

    return app
