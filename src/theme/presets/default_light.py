"""Default light theme preset — inverted colors for light mode."""

PRESET = {
    "name": "Neon Light",
    "colors": {
        # === Backgrounds (light layer hierarchy) ===
        "bg_primary":    "#f0f0f8",
        "bg_secondary":  "#e4e4f0",
        "bg_tertiary":   "#d8d8e8",
        "bg_hover":      "#ccccdd",
        "bg_terminal":   "#f8f8ff",

        # === Text ===
        "text_primary":  "#0a0a1a",
        "text_secondary": "#222244",
        "text_muted":    "#666688",
        "text_disabled": "#aaaacc",

        # === Accent (teal / darker cyan for readability on light) ===
        "accent":        "#009977",
        "accent_hover":  "#00886a",
        "accent_light":  "rgba(0, 153, 119, 0.10)",
        "accent_medium": "rgba(0, 153, 119, 0.25)",
        "accent_strong": "rgba(0, 153, 119, 0.40)",

        # === Secondary Accent (Magenta — darker) ===
        "accent2":       "#cc44cc",
        "accent2_light": "rgba(204, 68, 204, 0.10)",

        # === Status ===
        "status_success": "#008855",
        "status_warning": "#cc9900",
        "status_error":  "#dd2244",
        "status_info":   "#0077cc",

        # === Usage Spectrum ===
        "usage_low":     "#009977",
        "usage_mid":     "#cc9900",
        "usage_high":    "#cc6600",
        "usage_critical": "#dd2244",

        # === Borders ===
        "border_default": "#bbbbdd",
        "border_hover":  "rgba(0, 153, 119, 0.30)",
        "border_focus":  "rgba(0, 153, 119, 0.50)",

        # === Terminal ANSI (normal) ===
        "ansi_black":    "#0a0a1a",
        "ansi_red":      "#cc2244",
        "ansi_green":    "#008855",
        "ansi_yellow":   "#aa8800",
        "ansi_blue":     "#0066bb",
        "ansi_magenta":  "#aa44aa",
        "ansi_cyan":     "#008877",
        "ansi_white":    "#e0e0e0",

        # === Terminal ANSI (bright) ===
        "ansi_bright_black":   "#555577",
        "ansi_bright_red":     "#ee4466",
        "ansi_bright_green":   "#22aa66",
        "ansi_bright_yellow":  "#ccaa22",
        "ansi_bright_blue":    "#2288dd",
        "ansi_bright_magenta": "#cc66cc",
        "ansi_bright_cyan":    "#22aa88",
        "ansi_bright_white":   "#f0f0f8",
    },
}
