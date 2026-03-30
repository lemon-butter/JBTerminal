"""Terminal emulator widget -- renders PTY output and handles input via pyte."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import pyte
from PyQt6.QtCore import (
    QRect,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import (
    QClipboard,
    QColor,
    QFont,
    QFontDatabase,
    QFontMetricsF,
    QGuiApplication,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QResizeEvent,
    QWheelEvent,
    QInputMethodEvent,
)
from PyQt6.QtWidgets import QWidget

from src.terminal.terminal_config import TerminalConfig
from src.theme.tokens import COLORS


# ---- ANSI color mapping: pyte color name -> theme token key ----
_PYTE_COLOR_MAP: Dict[str, str] = {
    "black":   "ansi_black",
    "red":     "ansi_red",
    "green":   "ansi_green",
    "brown":   "ansi_yellow",
    "yellow":  "ansi_yellow",
    "blue":    "ansi_blue",
    "magenta": "ansi_magenta",
    "cyan":    "ansi_cyan",
    "white":   "ansi_white",
    # bright variants map to the same tokens (we brighten them)
    "brightblack":   "ansi_black",
    "brightred":     "ansi_red",
    "brightgreen":   "ansi_green",
    "brightyellow":  "ansi_yellow",
    "brightblue":    "ansi_blue",
    "brightmagenta": "ansi_magenta",
    "brightcyan":    "ansi_cyan",
    "brightwhite":   "text_primary",
}

# Standard 256-color palette (first 16 entries match ANSI)
_ANSI_256: List[str] = [
    "#1a1a3e", "#FF4466", "#00FF88", "#FFCC00",
    "#00AAFF", "#FF66FF", "#00FFCC", "#e0e0e0",
    # Bright variants
    "#555577", "#FF6688", "#33FFAA", "#FFDD44",
    "#44BBFF", "#FF88FF", "#44FFDD", "#ffffff",
]
# Generate 216 color cube (indices 16..231)
for _r in range(6):
    for _g in range(6):
        for _b in range(6):
            _rv = 0 if _r == 0 else 55 + _r * 40
            _gv = 0 if _g == 0 else 55 + _g * 40
            _bv = 0 if _b == 0 else 55 + _b * 40
            _ANSI_256.append(f"#{_rv:02x}{_gv:02x}{_bv:02x}")
# Generate 24 grayscale entries (indices 232..255)
for _i in range(24):
    _v = 8 + _i * 10
    _ANSI_256.append(f"#{_v:02x}{_v:02x}{_v:02x}")


def _resolve_color(
    color: str,
    default_token: str,
    bright: bool = False,
) -> QColor:
    """Resolve a pyte color descriptor to a QColor.

    *color* may be:
      - "default" -> use the design-token *default_token*
      - a named ANSI color ("red", "brightcyan", ...)
      - a 256-color index string ("0" .. "255")
      - a 6-hex-digit direct color ("aabbcc")
    """
    if not color or color == "default":
        return QColor(COLORS.get(default_token, "#ffffff"))

    # Named ANSI color
    key = color.lower().replace(" ", "").replace("light", "bright")
    if key in _PYTE_COLOR_MAP:
        c = QColor(COLORS.get(_PYTE_COLOR_MAP[key], "#ffffff"))
        if bright and not key.startswith("bright"):
            c = c.lighter(130)
        return c

    # 256-color index
    if color.isdigit():
        idx = int(color)
        if 0 <= idx < len(_ANSI_256):
            return QColor(_ANSI_256[idx])

    # Direct hex color (6 digits)
    if re.fullmatch(r"[0-9a-fA-F]{6}", color):
        return QColor(f"#{color}")

    return QColor(COLORS.get(default_token, "#ffffff"))


# ---- Key translation helpers ----

_QT_KEY_TO_VT100: Dict[int, bytes] = {
    Qt.Key.Key_Return:    b"\r",
    Qt.Key.Key_Enter:     b"\r",
    Qt.Key.Key_Backspace: b"\x7f",
    Qt.Key.Key_Tab:       b"\t",
    Qt.Key.Key_Escape:    b"\x1b",
    Qt.Key.Key_Up:        b"\x1b[A",
    Qt.Key.Key_Down:      b"\x1b[B",
    Qt.Key.Key_Right:     b"\x1b[C",
    Qt.Key.Key_Left:      b"\x1b[D",
    Qt.Key.Key_Home:      b"\x1b[H",
    Qt.Key.Key_End:       b"\x1b[F",
    Qt.Key.Key_Insert:    b"\x1b[2~",
    Qt.Key.Key_Delete:    b"\x1b[3~",
    Qt.Key.Key_PageUp:    b"\x1b[5~",
    Qt.Key.Key_PageDown:  b"\x1b[6~",
    Qt.Key.Key_F1:        b"\x1bOP",
    Qt.Key.Key_F2:        b"\x1bOQ",
    Qt.Key.Key_F3:        b"\x1bOR",
    Qt.Key.Key_F4:        b"\x1bOS",
    Qt.Key.Key_F5:        b"\x1b[15~",
    Qt.Key.Key_F6:        b"\x1b[17~",
    Qt.Key.Key_F7:        b"\x1b[18~",
    Qt.Key.Key_F8:        b"\x1b[19~",
    Qt.Key.Key_F9:        b"\x1b[20~",
    Qt.Key.Key_F10:       b"\x1b[21~",
    Qt.Key.Key_F11:       b"\x1b[23~",
    Qt.Key.Key_F12:       b"\x1b[24~",
}


class TerminalWidget(QWidget):
    """Terminal emulator widget using pyte backend.

    Renders the pyte screen buffer via QPainter and translates keyboard
    input into bytes written to the associated PTY.
    """

    # Emitted when the widget wants to write data to the PTY
    input_ready = pyqtSignal(bytes)
    # Emitted when the terminal is resized (new cols, rows)
    size_changed = pyqtSignal(int, int)

    def __init__(
        self,
        config: Optional[TerminalConfig] = None,
        parent: QWidget = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("terminal")

        # Config
        self._config = config or TerminalConfig()

        # ---- pyte backend ----
        self._cols = 80
        self._rows = 24
        self._screen = pyte.Screen(self._cols, self._rows)
        self._screen.set_mode(pyte.modes.LNM)  # auto line-feed on CR
        self._stream = pyte.Stream(self._screen)

        # Scrollback
        self._scrollback: List[dict] = []  # list of row dicts (line -> char)
        self._scrollback_max = self._config.scrollback_lines
        self._scroll_offset = 0  # 0 = bottom (live), >0 = scrolled up

        # ---- Font / metrics ----
        self._font = QFont()
        self._apply_font_config()

        # ---- Cursor blink ----
        self._cursor_visible = True
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._toggle_cursor)
        if self._config.cursor_blink:
            self._blink_timer.start(530)

        # ---- Selection ----
        self._selection_start: Optional[Tuple[int, int]] = None  # (col, row_in_buffer)
        self._selection_end: Optional[Tuple[int, int]] = None
        self._selecting = False

        # ---- IME composition ----
        self._composing_text = ""

        # ---- Widget setup ----
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setMinimumSize(200, 100)

        # Force initial metrics calculation
        self._recalc_metrics()

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def feed(self, data: bytes) -> None:
        """Feed raw bytes from the PTY into the terminal emulator."""
        # Before feeding, save lines that scroll off the top
        old_top = self._top_line_content()
        try:
            self._stream.feed(data.decode("utf-8", errors="replace"))
        except Exception:
            pass
        new_top = self._top_line_content()
        if old_top != new_top:
            self._push_scrollback()

        # Auto-scroll to bottom on new output
        if self._scroll_offset > 0:
            self._scroll_offset = 0
        self.update()

    def set_config(self, config: TerminalConfig) -> None:
        """Apply new configuration."""
        self._config = config
        self._scrollback_max = config.scrollback_lines
        self._apply_font_config()
        if config.cursor_blink:
            self._blink_timer.start(530)
        else:
            self._blink_timer.stop()
            self._cursor_visible = True
        self._recalc_metrics()
        self.update()

    def get_selected_text(self) -> str:
        """Return the currently selected text, or empty string."""
        if self._selection_start is None or self._selection_end is None:
            return ""
        return self._extract_selection()

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _apply_font_config(self) -> None:
        families = [f.strip() for f in self._config.font_family.split(",")]
        found = False
        for fam in families:
            if fam in QFontDatabase.families():
                self._font.setFamily(fam)
                found = True
                break
        if not found:
            self._font.setFamily("Menlo")
        self._font.setPixelSize(self._config.font_size)
        self._font.setStyleHint(QFont.StyleHint.Monospace)
        self._font.setFixedPitch(True)

    def _recalc_metrics(self) -> None:
        fm = QFontMetricsF(self._font)
        self._cell_width = fm.horizontalAdvance("M")
        self._cell_height = fm.height() * self._config.line_spacing
        self._baseline_offset = fm.ascent()

        # Recalculate grid size
        w = self.width()
        h = self.height()
        if w > 0 and h > 0:
            new_cols = max(1, int(w / self._cell_width))
            new_rows = max(1, int(h / self._cell_height))
            if new_cols != self._cols or new_rows != self._rows:
                self._cols = new_cols
                self._rows = new_rows
                self._screen.resize(self._rows, self._cols)
                self.size_changed.emit(self._cols, self._rows)

    def _top_line_content(self) -> str:
        """Snapshot the first visible line for scroll detection."""
        if self._screen.buffer and 0 in self._screen.buffer:
            line = self._screen.buffer[0]
            return "".join(line[c].data for c in sorted(line.keys()))
        return ""

    def _push_scrollback(self) -> None:
        """Save the top screen line into the scrollback buffer."""
        if self._screen.history.top:
            for hist_line in self._screen.history.top:
                if len(self._scrollback) >= self._scrollback_max:
                    self._scrollback.pop(0)
                self._scrollback.append(hist_line)
            self._screen.history.top.clear()

    def _toggle_cursor(self) -> None:
        self._cursor_visible = not self._cursor_visible
        self.update()

    # ------------------------------------------------------------------ #
    #  Painting                                                           #
    # ------------------------------------------------------------------ #

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        bg = QColor(COLORS["bg_terminal"])
        painter.fillRect(self.rect(), bg)
        painter.setFont(self._font)

        cw = self._cell_width
        ch = self._cell_height
        baseline = self._baseline_offset

        default_fg = QColor(COLORS["text_primary"])
        default_bg = bg

        screen = self._screen

        for row_idx in range(self._rows):
            # Determine which buffer row to draw
            if self._scroll_offset > 0:
                sb_row = len(self._scrollback) - self._scroll_offset + row_idx
                if 0 <= sb_row < len(self._scrollback):
                    line = self._scrollback[sb_row]
                elif sb_row >= len(self._scrollback):
                    buf_row = sb_row - len(self._scrollback)
                    line = screen.buffer.get(buf_row, {})
                else:
                    line = {}
            else:
                line = screen.buffer.get(row_idx, {})

            y = row_idx * ch

            for col_idx in range(self._cols):
                x = col_idx * cw
                char = line.get(col_idx, screen.default_char)

                # Determine colors
                fg_color = _resolve_color(
                    char.fg, "text_primary", bright=bool(getattr(char, 'bold', False))
                ) if hasattr(char, 'fg') else default_fg
                bg_color = _resolve_color(
                    char.bg, "bg_terminal"
                ) if hasattr(char, 'bg') else default_bg

                # Handle reverse video
                if hasattr(char, 'reverse') and char.reverse:
                    fg_color, bg_color = bg_color, fg_color

                # Handle selection highlight
                if self._is_selected(col_idx, row_idx):
                    fg_color = QColor(COLORS["bg_terminal"])
                    bg_color = QColor(COLORS["accent"])

                # Draw cell background
                cell_rect = QRect(int(x), int(y), int(cw) + 1, int(ch) + 1)
                if bg_color != default_bg or self._is_selected(col_idx, row_idx):
                    painter.fillRect(cell_rect, bg_color)

                # Draw character
                data = char.data if hasattr(char, 'data') else " "
                if data and data != " ":
                    # Bold
                    font = QFont(self._font)
                    if hasattr(char, 'bold') and char.bold:
                        font.setBold(True)
                    if hasattr(char, 'italics') and char.italics:
                        font.setItalic(True)
                    painter.setFont(font)
                    painter.setPen(fg_color)
                    painter.drawText(int(x), int(y + baseline), data)
                    if font != self._font:
                        painter.setFont(self._font)

                # Underline
                if hasattr(char, 'underscore') and char.underscore:
                    painter.setPen(fg_color)
                    uy = int(y + ch - 1)
                    painter.drawLine(int(x), uy, int(x + cw), uy)

        # ---- Draw cursor ----
        if self._cursor_visible and self._scroll_offset == 0:
            cx = screen.cursor.x
            cy = screen.cursor.y
            cursor_x = int(cx * cw)
            cursor_y = int(cy * ch)
            cursor_color = QColor(COLORS["accent"])
            cursor_color.setAlpha(180)
            painter.fillRect(
                QRect(cursor_x, cursor_y, max(int(cw), 2), int(ch)),
                cursor_color,
            )
            # Draw the character under cursor in contrasting color
            cursor_line = screen.buffer.get(cy, {})
            cursor_char = cursor_line.get(cx, screen.default_char)
            cdata = cursor_char.data if hasattr(cursor_char, 'data') else " "
            if cdata and cdata != " ":
                painter.setPen(QColor(COLORS["bg_terminal"]))
                painter.drawText(cursor_x, int(cursor_y + baseline), cdata)

        # ---- Draw IME composition text ----
        if self._composing_text:
            cx = screen.cursor.x
            cy = screen.cursor.y
            ime_x = int(cx * cw)
            ime_y = int(cy * ch)
            # Underlined composition text
            painter.setPen(QColor(COLORS["accent"]))
            painter.drawText(ime_x, int(ime_y + baseline), self._composing_text)
            # Underline
            comp_w = int(len(self._composing_text) * cw)
            painter.drawLine(ime_x, int(ime_y + ch - 1), ime_x + comp_w, int(ime_y + ch - 1))

        painter.end()

    # ------------------------------------------------------------------ #
    #  Selection                                                          #
    # ------------------------------------------------------------------ #

    def _pixel_to_cell(self, x: int, y: int) -> Tuple[int, int]:
        col = max(0, min(int(x / self._cell_width), self._cols - 1))
        row = max(0, min(int(y / self._cell_height), self._rows - 1))
        return col, row

    def _is_selected(self, col: int, row: int) -> bool:
        if self._selection_start is None or self._selection_end is None:
            return False
        s = self._selection_start
        e = self._selection_end
        # Normalize so s <= e
        if (s[1], s[0]) > (e[1], e[0]):
            s, e = e, s
        if row < s[1] or row > e[1]:
            return False
        if row == s[1] and row == e[1]:
            return s[0] <= col <= e[0]
        if row == s[1]:
            return col >= s[0]
        if row == e[1]:
            return col <= e[0]
        return True

    def _extract_selection(self) -> str:
        if self._selection_start is None or self._selection_end is None:
            return ""
        s = self._selection_start
        e = self._selection_end
        if (s[1], s[0]) > (e[1], e[0]):
            s, e = e, s

        lines: List[str] = []
        for row in range(s[1], e[1] + 1):
            line_chars: List[str] = []
            start_col = s[0] if row == s[1] else 0
            end_col = e[0] if row == e[1] else self._cols - 1
            buf_line = self._screen.buffer.get(row, {})
            for col in range(start_col, end_col + 1):
                char = buf_line.get(col, self._screen.default_char)
                line_chars.append(char.data if hasattr(char, 'data') else " ")
            lines.append("".join(line_chars).rstrip())
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Events                                                             #
    # ------------------------------------------------------------------ #

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._recalc_metrics()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        modifiers = event.modifiers()

        # Cmd+C -> copy selection (macOS)
        if (
            modifiers & Qt.KeyboardModifier.ControlModifier
            and key == Qt.Key.Key_C
            and self._selection_start is not None
        ):
            text = self.get_selected_text()
            if text:
                clipboard = QGuiApplication.clipboard()
                if clipboard:
                    clipboard.setText(text)
                self._clear_selection()
                return

        # Cmd+V -> paste (macOS)
        if modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_V:
            clipboard = QGuiApplication.clipboard()
            if clipboard:
                text = clipboard.text()
                if text:
                    self.input_ready.emit(text.encode("utf-8"))
            return

        # Clear selection on any key press
        self._clear_selection()

        # Ctrl+key combos (send control character)
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
                ctrl_char = bytes([key - Qt.Key.Key_A + 1])
                self.input_ready.emit(ctrl_char)
                return
            if key == Qt.Key.Key_BracketLeft:
                self.input_ready.emit(b"\x1b")
                return
            if key == Qt.Key.Key_Backslash:
                self.input_ready.emit(b"\x1c")
                return
            if key == Qt.Key.Key_BracketRight:
                self.input_ready.emit(b"\x1d")
                return

        # Special keys
        if key in _QT_KEY_TO_VT100:
            seq = _QT_KEY_TO_VT100[key]
            # Application cursor mode
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Right, Qt.Key.Key_Left):
                if pyte.modes.DECAPPKEY in self._screen.mode:
                    seq = seq.replace(b"[", b"O")
            self.input_ready.emit(seq)
            return

        # Normal text input
        text = event.text()
        if text:
            self.input_ready.emit(text.encode("utf-8"))

    def inputMethodEvent(self, event: QInputMethodEvent) -> None:  # noqa: N802
        """Handle IME composition (Korean/CJK input)."""
        commit = event.commitString()
        preedit = event.preeditString()

        if commit:
            self._composing_text = ""
            self.input_ready.emit(commit.encode("utf-8"))
        else:
            self._composing_text = preedit

        self.update()
        event.accept()

    def inputMethodQuery(self, query):  # noqa: N802
        """Provide IME with cursor position info."""
        if query == Qt.InputMethodQuery.ImCursorRectangle:
            cx = self._screen.cursor.x
            cy = self._screen.cursor.y
            from PyQt6.QtCore import QRectF
            return QRectF(
                cx * self._cell_width,
                cy * self._cell_height,
                self._cell_width,
                self._cell_height,
            )
        return super().inputMethodQuery(query)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            col, row = self._pixel_to_cell(int(event.position().x()), int(event.position().y()))
            self._selection_start = (col, row)
            self._selection_end = (col, row)
            self._selecting = True
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._selecting:
            col, row = self._pixel_to_cell(int(event.position().x()), int(event.position().y()))
            self._selection_end = (col, row)
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._selecting = False
            # Clear selection if start == end (just a click)
            if self._selection_start == self._selection_end:
                self._clear_selection()
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        delta = event.angleDelta().y()
        scroll_lines = max(1, abs(delta) // 40)
        max_offset = len(self._scrollback)
        if delta > 0:
            # Scroll up
            self._scroll_offset = min(self._scroll_offset + scroll_lines, max_offset)
        else:
            # Scroll down
            self._scroll_offset = max(self._scroll_offset - scroll_lines, 0)
        self.update()
        event.accept()

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(
            int(80 * self._cell_width),
            int(24 * self._cell_height),
        )

    def _clear_selection(self) -> None:
        self._selection_start = None
        self._selection_end = None
        self.update()
