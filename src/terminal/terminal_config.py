"""Terminal configuration — font, line spacing, scrollback buffer."""

from dataclasses import dataclass


@dataclass
class TerminalConfig:
    """Per-terminal configuration."""
    font_family: str = "JetBrains Mono"
    font_size: int = 14
    line_spacing: float = 1.0
    scrollback_lines: int = 10000
    cursor_blink: bool = True
