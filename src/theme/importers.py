"""Theme importers — parse JetBrains .icls and Terminal.app .terminal files."""

from __future__ import annotations

import plistlib
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# JetBrains IDE theme import (.icls)
# ---------------------------------------------------------------------------

# Maps JetBrains color attribute names to our token keys.
# JetBrains .icls stores colors as hex RGB without '#' (e.g. "282a36").
_JB_ATTR_MAP: Dict[str, str] = {
    # Backgrounds
    "CONSOLE_BACKGROUND_KEY": "bg_terminal",

    # Text
    "TEXT":                    "text_primary",
    "DEFAULT_FOREGROUND":     "text_primary",

    # ANSI colors
    "ANSI 0":  "ansi_black",
    "ANSI 1":  "ansi_red",
    "ANSI 2":  "ansi_green",
    "ANSI 3":  "ansi_yellow",
    "ANSI 4":  "ansi_blue",
    "ANSI 5":  "ansi_magenta",
    "ANSI 6":  "ansi_cyan",
    "ANSI 7":  "ansi_white",
    "ANSI 8":  "ansi_bright_black",
    "ANSI 9":  "ansi_bright_red",
    "ANSI 10": "ansi_bright_green",
    "ANSI 11": "ansi_bright_yellow",
    "ANSI 12": "ansi_bright_blue",
    "ANSI 13": "ansi_bright_magenta",
    "ANSI 14": "ansi_bright_cyan",
    "ANSI 15": "ansi_bright_white",
}

# Additional option-based mappings (from <option name="..." value="..."/>)
_JB_OPTION_MAP: Dict[str, str] = {
    "BACKGROUND":         "bg_primary",
    "FOREGROUND":         "text_primary",
    "SELECTION_BACKGROUND": "accent_medium",
    "CARET_ROW_COLOR":    "bg_hover",
    "LINE_NUMBERS_COLOR": "text_muted",
    "RIGHT_MARGIN_COLOR": "border_default",
    "GUTTER_BACKGROUND":  "bg_secondary",
}


def _normalize_jb_color(raw: str) -> str:
    """Convert a JetBrains hex color (e.g. '282a36' or '0x282a36') to '#282a36'."""
    raw = raw.strip().lower()
    if raw.startswith("0x"):
        raw = raw[2:]
    if raw.startswith("#"):
        raw = raw[1:]
    # Some JetBrains colors are AARRGGBB (8 hex digits)
    if len(raw) == 8:
        raw = raw[2:]  # strip alpha prefix
    return f"#{raw}"


def import_jetbrains_theme(path: str) -> Dict[str, str]:
    """Parse a JetBrains .icls XML file and return a token-compatible colors dict.

    Parameters
    ----------
    path:
        Filesystem path to the ``.icls`` file.

    Returns
    -------
    dict:
        A colors dict compatible with ``ThemeManager.load_preset()``.
        Missing keys are filled from the default dark preset.
    """
    from src.theme.tokens import COLORS as _DEFAULTS

    tree = ET.parse(path)
    root = tree.getroot()

    colors: Dict[str, str] = {}

    # Parse <colors> section: <option name="..." value="..."/>
    colors_section = root.find(".//colors")
    if colors_section is not None:
        for option in colors_section.findall("option"):
            name = option.get("name", "")
            value = option.get("value", "")
            if name in _JB_OPTION_MAP and value:
                colors[_JB_OPTION_MAP[name]] = _normalize_jb_color(value)

    # Parse <attributes> section for console colors
    attributes_section = root.find(".//attributes")
    if attributes_section is not None:
        for attr in attributes_section.findall("option"):
            attr_name = attr.get("name", "")
            if attr_name not in _JB_ATTR_MAP:
                continue
            token_key = _JB_ATTR_MAP[attr_name]
            # Value can be in child <value><option name="FOREGROUND" value="..."/></value>
            value_el = attr.find("value")
            if value_el is not None:
                for sub_opt in value_el.findall("option"):
                    sub_name = sub_opt.get("name", "")
                    sub_value = sub_opt.get("value", "")
                    if sub_name == "FOREGROUND" and sub_value:
                        colors[token_key] = _normalize_jb_color(sub_value)
                        break
                    elif sub_name == "BACKGROUND" and sub_value:
                        # For CONSOLE_BACKGROUND_KEY, use background
                        if "bg" in token_key or "BACKGROUND" in attr_name:
                            colors[token_key] = _normalize_jb_color(sub_value)
                            break

    # Derive additional tokens from what we have
    _derive_missing_tokens(colors)

    # Fill remaining keys from defaults
    result: Dict[str, str] = dict(_DEFAULTS)
    result.update(colors)
    return result


# ---------------------------------------------------------------------------
# Terminal.app theme import (.terminal)
# ---------------------------------------------------------------------------

# Terminal.app stores ANSI colors as NSArchiver data blobs for NSColor objects.
# The plist also has some direct keys we can use.

_TERMINAL_APP_KEY_MAP: Dict[str, str] = {
    "BackgroundColor":              "bg_primary",
    "TextColor":                    "text_primary",
    "TextBoldColor":                "text_secondary",
    "CursorColor":                  "accent",
    "SelectionColor":               "accent_medium",
    "ANSIBlackColor":               "ansi_black",
    "ANSIRedColor":                 "ansi_red",
    "ANSIGreenColor":               "ansi_green",
    "ANSIYellowColor":              "ansi_yellow",
    "ANSIBlueColor":                "ansi_blue",
    "ANSIMagentaColor":             "ansi_magenta",
    "ANSICyanColor":                "ansi_cyan",
    "ANSIWhiteColor":               "ansi_white",
    "ANSIBrightBlackColor":         "ansi_bright_black",
    "ANSIBrightRedColor":           "ansi_bright_red",
    "ANSIBrightGreenColor":         "ansi_bright_green",
    "ANSIBrightYellowColor":        "ansi_bright_yellow",
    "ANSIBrightBlueColor":          "ansi_bright_blue",
    "ANSIBrightMagentaColor":       "ansi_bright_magenta",
    "ANSIBrightCyanColor":          "ansi_bright_cyan",
    "ANSIBrightWhiteColor":         "ansi_bright_white",
}


def _extract_nscolor_rgb(data: bytes) -> Optional[str]:
    """Best-effort extraction of RGB from an NSKeyedArchiver color blob.

    Terminal.app encodes NSColor objects as NSKeyedArchiver binary data.
    We attempt to find calibrated RGB float components in the blob.
    Returns a hex color string or None.
    """
    # Strategy: look for sequences of 3-4 doubles (RGB or RGBA) in the data.
    # NSCalibratedRGBColor stores components as doubles.
    # We scan for plausible float triplets in [0.0, 1.0].
    if len(data) < 24:
        return None

    best: Optional[str] = None
    # Try to find the string "NSRGB" which precedes the color data in some formats
    nsrgb_idx = data.find(b"NSRGB")
    if nsrgb_idx >= 0:
        # After NSRGB marker, there may be length byte then ASCII floats separated by spaces
        after = data[nsrgb_idx + 5:]
        # Skip any non-ASCII preamble bytes (length prefix, type info)
        start = 0
        while start < len(after) and (after[start:start+1] < b'0' or after[start:start+1] > b'9'):
            start += 1
        if start < len(after):
            ascii_part = after[start:start+60]
            try:
                text = ascii_part.decode("ascii", errors="ignore")
                parts = text.split()
                if len(parts) >= 3:
                    r = max(0.0, min(1.0, float(parts[0])))
                    g = max(0.0, min(1.0, float(parts[1])))
                    b = max(0.0, min(1.0, float(parts[2])))
                    return "#{:02x}{:02x}{:02x}".format(
                        int(r * 255), int(g * 255), int(b * 255)
                    )
            except (ValueError, IndexError):
                pass

    # Fallback: scan for 3 consecutive doubles in [0, 1]
    for offset in range(0, len(data) - 23):
        try:
            vals = struct.unpack_from(">ddd", data, offset)
            if all(0.0 <= v <= 1.0 for v in vals):
                r, g, b = vals
                return "#{:02x}{:02x}{:02x}".format(
                    int(r * 255), int(g * 255), int(b * 255)
                )
        except struct.error:
            continue
        # Also try little-endian
        try:
            vals = struct.unpack_from("<ddd", data, offset)
            if all(0.0 <= v <= 1.0 for v in vals):
                r, g, b = vals
                return "#{:02x}{:02x}{:02x}".format(
                    int(r * 255), int(g * 255), int(b * 255)
                )
        except struct.error:
            continue

    return None


def import_terminal_app_theme(path: str) -> Dict[str, str]:
    """Parse a Terminal.app .terminal plist file and return a token-compatible colors dict.

    Parameters
    ----------
    path:
        Filesystem path to the ``.terminal`` file.

    Returns
    -------
    dict:
        A colors dict compatible with ``ThemeManager.load_preset()``.
        Missing keys are filled from the default dark preset.
    """
    from src.theme.tokens import COLORS as _DEFAULTS

    file_path = Path(path)
    with open(file_path, "rb") as f:
        plist = plistlib.load(f)

    colors: Dict[str, str] = {}

    for plist_key, token_key in _TERMINAL_APP_KEY_MAP.items():
        value = plist.get(plist_key)
        if value is None:
            continue
        if isinstance(value, bytes):
            hex_color = _extract_nscolor_rgb(value)
            if hex_color:
                colors[token_key] = hex_color
        elif isinstance(value, str):
            # Occasionally stored as plain hex
            if value.startswith("#") or (len(value) == 6 and all(c in "0123456789abcdefABCDEF" for c in value)):
                colors[token_key] = value if value.startswith("#") else f"#{value}"

    # Also set bg_terminal from background
    if "bg_primary" in colors and "bg_terminal" not in colors:
        colors["bg_terminal"] = colors["bg_primary"]

    # Derive additional tokens from what we have
    _derive_missing_tokens(colors)

    # Fill remaining keys from defaults
    result: Dict[str, str] = dict(_DEFAULTS)
    result.update(colors)
    return result


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _derive_missing_tokens(colors: Dict[str, str]) -> None:
    """Fill in derivative tokens from existing extracted colors in-place."""
    # bg_secondary / bg_tertiary from bg_primary
    if "bg_primary" in colors:
        bg = colors["bg_primary"]
        if "bg_secondary" not in colors:
            colors["bg_secondary"] = _lighten(bg, 0.06)
        if "bg_tertiary" not in colors:
            colors["bg_tertiary"] = _lighten(bg, 0.12)
        if "bg_hover" not in colors:
            colors["bg_hover"] = _lighten(bg, 0.18)
        if "bg_terminal" not in colors:
            colors["bg_terminal"] = _darken(bg, 0.03)

    # Text variants
    if "text_primary" in colors:
        tp = colors["text_primary"]
        if "text_secondary" not in colors:
            colors["text_secondary"] = _alpha_blend(tp, 0.88)
        if "text_muted" not in colors:
            colors["text_muted"] = _alpha_blend(tp, 0.55)
        if "text_disabled" not in colors:
            colors["text_disabled"] = _alpha_blend(tp, 0.35)

    # Accent variants
    if "accent" in colors:
        acc = colors["accent"]
        if "accent_hover" not in colors:
            colors["accent_hover"] = _darken(acc, 0.1)
        if "accent_light" not in colors:
            r, g, b = _hex_to_rgb(acc)
            colors["accent_light"] = f"rgba({r}, {g}, {b}, 0.10)"
        if "accent_medium" not in colors:
            r, g, b = _hex_to_rgb(acc)
            colors["accent_medium"] = f"rgba({r}, {g}, {b}, 0.25)"
        if "accent_strong" not in colors:
            r, g, b = _hex_to_rgb(acc)
            colors["accent_strong"] = f"rgba({r}, {g}, {b}, 0.40)"

    # Status from ANSI
    ansi_status = [
        ("status_success", "ansi_green"),
        ("status_warning", "ansi_yellow"),
        ("status_error", "ansi_red"),
        ("status_info", "ansi_blue"),
    ]
    for status_key, ansi_key in ansi_status:
        if status_key not in colors and ansi_key in colors:
            colors[status_key] = colors[ansi_key]

    # Usage spectrum
    usage_map = [
        ("usage_low", "status_success"),
        ("usage_mid", "status_warning"),
        ("usage_high", "ansi_yellow"),
        ("usage_critical", "status_error"),
    ]
    for usage_key, source_key in usage_map:
        if usage_key not in colors and source_key in colors:
            colors[usage_key] = colors[source_key]

    # Borders
    if "border_default" not in colors and "bg_hover" in colors:
        colors["border_default"] = colors["bg_hover"]
    if "border_hover" not in colors and "accent" in colors:
        r, g, b = _hex_to_rgb(colors["accent"])
        colors["border_hover"] = f"rgba({r}, {g}, {b}, 0.30)"
    if "border_focus" not in colors and "accent" in colors:
        r, g, b = _hex_to_rgb(colors["accent"])
        colors["border_focus"] = f"rgba({r}, {g}, {b}, 0.50)"

    # Secondary accent — default to magenta ANSI if present
    if "accent2" not in colors and "ansi_magenta" in colors:
        colors["accent2"] = colors["ansi_magenta"]
    if "accent2" in colors and "accent2_light" not in colors:
        r, g, b = _hex_to_rgb(colors["accent2"])
        colors["accent2_light"] = f"rgba({r}, {g}, {b}, 0.10)"


def _hex_to_rgb(hex_color: str) -> tuple:
    """Parse '#rrggbb' to (r, g, b) ints."""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return (128, 128, 128)


def _lighten(hex_color: str, amount: float) -> str:
    """Lighten a hex color by blending toward white."""
    r, g, b = _hex_to_rgb(hex_color)
    r = min(255, int(r + (255 - r) * amount))
    g = min(255, int(g + (255 - g) * amount))
    b = min(255, int(b + (255 - b) * amount))
    return f"#{r:02x}{g:02x}{b:02x}"


def _darken(hex_color: str, amount: float) -> str:
    """Darken a hex color by blending toward black."""
    r, g, b = _hex_to_rgb(hex_color)
    r = max(0, int(r * (1 - amount)))
    g = max(0, int(g * (1 - amount)))
    b = max(0, int(b * (1 - amount)))
    return f"#{r:02x}{g:02x}{b:02x}"


def _alpha_blend(hex_color: str, alpha: float) -> str:
    """Return the hex color with components scaled by alpha (simulating over black)."""
    r, g, b = _hex_to_rgb(hex_color)
    r = int(r * alpha)
    g = int(g * alpha)
    b = int(b * alpha)
    return f"#{r:02x}{g:02x}{b:02x}"
