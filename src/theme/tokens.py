"""Design tokens — central source of truth for all colors, spacing, and dimensions."""

COLORS = {
    # === Backgrounds ===
    "bg_primary":    "#0a0a1a",
    "bg_secondary":  "#12122a",
    "bg_tertiary":   "#1a1a3e",
    "bg_hover":      "#242450",
    "bg_terminal":   "#08081a",

    # === Text ===
    "text_primary":  "#ffffff",
    "text_secondary": "#e0e0e0",
    "text_muted":    "#8888aa",
    "text_disabled": "#555577",

    # === Accent (Neon Cyan) ===
    "accent":        "#00FFCC",
    "accent_hover":  "#00DDaa",
    "accent_light":  "rgba(0, 255, 204, 0.10)",
    "accent_medium": "rgba(0, 255, 204, 0.25)",
    "accent_strong": "rgba(0, 255, 204, 0.40)",

    # === Secondary Accent (Neon Magenta) ===
    "accent2":       "#FF66FF",
    "accent2_light": "rgba(255, 102, 255, 0.10)",

    # === Status ===
    "status_success": "#00FF88",
    "status_warning": "#FFCC00",
    "status_error":  "#FF4466",
    "status_info":   "#00AAFF",

    # === Usage Spectrum ===
    "usage_low":     "#00FFCC",
    "usage_mid":     "#FFCC00",
    "usage_high":    "#FF8800",
    "usage_critical": "#FF4466",

    # === Borders ===
    "border_default": "#333366",
    "border_hover":  "rgba(0, 255, 204, 0.30)",
    "border_focus":  "rgba(0, 255, 204, 0.50)",

    # === Terminal ANSI ===
    "ansi_black":    "#1a1a3e",
    "ansi_red":      "#FF4466",
    "ansi_green":    "#00FF88",
    "ansi_yellow":   "#FFCC00",
    "ansi_blue":     "#00AAFF",
    "ansi_magenta":  "#FF66FF",
    "ansi_cyan":     "#00FFCC",
    "ansi_white":    "#e0e0e0",
}

RADIUS = {
    "sm":   4,
    "md":   8,
    "lg":   12,
    "xl":   16,
    "full": 9999,
}

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 16,
    "lg": 24,
    "xl": 32,
}

DIMENSIONS = {
    "titlebar_height":    40,
    "sidebar_width":      240,
    "sidebar_min_width":  180,
    "sidebar_max_width":  400,
    "tab_bar_height":     36,
    "status_bar_height":  28,
    "scrollbar_width":    8,
    "pane_divider_width": 4,
}

FONTS = {
    "ui_family":       "SF Pro Display, Inter, system-ui, sans-serif",
    "mono_family":     "JetBrains Mono, Fira Code, Menlo, monospace",
    "ui_size":         13,
    "ui_label_size":   12,
    "ui_header_size":  16,
    "terminal_size":   14,
    "status_bar_size": 11,
}

GLASS = {
    "bg":     "rgba(18, 18, 42, 0.85)",
    "border": "rgba(255, 255, 255, 0.08)",
}
