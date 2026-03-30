"""State detector — detects Claude Code state from PTY output."""

from __future__ import annotations

import re
import time
from typing import Dict, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from src.models.enums import PaneState


class StateDetector(QObject):
    """Parses PTY output to detect Claude Code state.

    Receives raw PTY output bytes via :meth:`feed`, decodes UTF-8, runs
    regex pattern matching, and emits :pyqtSignal:`state_changed` when the
    detected state transitions.

    Debounce: the same state is not re-emitted and a minimum of 200 ms
    must elapse between emissions.
    """

    state_changed = pyqtSignal(str, str)  # (pane_id, state: PaneState value)

    # Minimum interval between signal emissions (seconds)
    _DEBOUNCE_SEC = 0.200

    # --- Pattern definitions (compiled once) ---
    # Order matters: first match wins.  More specific patterns come first.

    _PATTERNS = [
        # ERROR — must come before DONE since both can appear together
        (PaneState.ERROR, re.compile(
            r"(?:"
            r"Error:|ERROR:|error:|\u2717|"  # "Error:", "✗"
            r"\x1b\[31m"                     # red ANSI escape
            r")"
        )),
        # WAITING — user input requested
        (PaneState.WAITING, re.compile(
            r"(?:"
            r"\?\s*$|"                                # "? " at end of line
            r"Do you want to proceed|"
            r"Allow|Deny|"
            r"\[Y/n\]|\[y/N\]|"
            r"Press Enter|"
            r"permission"
            r")",
            re.IGNORECASE,
        )),
        # TOOL_USE — tool execution
        (PaneState.TOOL_USE, re.compile(
            r"(?:"
            r"Running:|Reading:|Writing:|Editing:|Searching:|"
            r"Execute|Bash|Read|Edit|Write|Glob|Grep"
            r")"
        )),
        # THINKING — AI generating
        (PaneState.THINKING, re.compile(
            r"(?:"
            r"Thinking\.\.\.|"
            r"\u280b|\u280d|\u280e|\u2819|\u2838|\u2830|\u2821|\u2806|"  # braille spinner chars
            r"\u25cf\s*$|"  # solid dot
            r"Generating"
            r")"
        )),
        # DONE — task completed
        (PaneState.DONE, re.compile(
            r"(?:"
            r"\u2713|\u2714|"        # check marks ✓ ✔
            r"Done|Completed|"
            r"finished"
            r")",
            re.IGNORECASE,
        )),
        # IDLE — prompt visible (checked last)
        (PaneState.IDLE, re.compile(
            r"(?:"
            r"\$\s*$|"            # "$ " at end
            r"\u276f\s*$|"        # "❯ " at end
            r">\s*$"              # "> " at end
            r")"
        )),
    ]

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pane_states: Dict[str, str] = {}
        self._last_emit: Dict[str, float] = {}

    def feed(self, pane_id: str, data: bytes) -> None:
        """Receive raw PTY output and detect state.

        Parameters
        ----------
        pane_id:
            Identifier for the terminal pane.
        data:
            Raw bytes from the PTY.
        """
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            return

        detected = self._detect(text)
        if detected is None:
            return

        now = time.monotonic()
        prev_state = self._pane_states.get(pane_id)
        prev_time = self._last_emit.get(pane_id, 0.0)

        # Debounce: skip if same state or too soon
        if detected == prev_state and (now - prev_time) < self._DEBOUNCE_SEC:
            return
        if detected != prev_state or (now - prev_time) >= self._DEBOUNCE_SEC:
            self._pane_states[pane_id] = detected
            self._last_emit[pane_id] = now
            self.state_changed.emit(pane_id, detected)

    def get_state(self, pane_id: str) -> str:
        """Return the last known state for *pane_id*, or IDLE."""
        return self._pane_states.get(pane_id, PaneState.IDLE.value)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _detect(self, text: str) -> Optional[str]:
        """Return the first matching PaneState value, or None."""
        # Only look at the last 512 chars to keep matching fast
        tail = text[-512:] if len(text) > 512 else text
        for state, pattern in self._PATTERNS:
            if pattern.search(tail):
                return state.value
        return None
