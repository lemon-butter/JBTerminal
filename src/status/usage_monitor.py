"""Usage monitor — tracks CTX / 5H / 7D usage from Claude Code."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt6.QtCore import (
    QFileSystemWatcher,
    QObject,
    QThread,
    QTimer,
    pyqtSignal,
)

logger = logging.getLogger(__name__)

_CLAUDE_DIR = Path.home() / ".claude"
_STATUSLINE_PATH = _CLAUDE_DIR / "statusline.json"
_PROJECTS_DIR = _CLAUDE_DIR / "projects"


class _UsageWorker(QObject):
    """Background worker that polls usage data.

    Runs in a QThread.  Uses QFileSystemWatcher for change-driven updates
    and a QTimer fallback for periodic checks.
    """

    usage_updated = pyqtSignal(dict)  # {"ctx": float, "5h": float, "7d": float}

    def __init__(self) -> None:
        super().__init__()
        self._watcher: Optional[QFileSystemWatcher] = None
        self._timer: Optional[QTimer] = None
        self._last_data: Optional[Dict[str, float]] = None

    def start(self) -> None:
        """Set up watcher and timer. Called after moveToThread."""
        self._watcher = QFileSystemWatcher(self)

        # Watch statusline file if it exists
        if _STATUSLINE_PATH.exists():
            self._watcher.addPath(str(_STATUSLINE_PATH))
        # Also watch the directory so we notice when the file is created
        if _CLAUDE_DIR.exists():
            self._watcher.addPath(str(_CLAUDE_DIR))

        self._watcher.fileChanged.connect(self._on_file_changed)
        self._watcher.directoryChanged.connect(self._on_dir_changed)

        # Fallback timer — 1 s for statusline, doubles as session poll
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

        # Initial read
        self._poll()

    def stop(self) -> None:
        if self._timer:
            self._timer.stop()

    # ------------------------------------------------------------------

    def _on_file_changed(self, path: str) -> None:
        if path == str(_STATUSLINE_PATH):
            self._read_statusline()
        # QFileSystemWatcher may drop paths after edit; re-add
        if not os.path.exists(path):
            return
        if path not in (self._watcher.files() if self._watcher else []):
            if self._watcher:
                self._watcher.addPath(path)

    def _on_dir_changed(self, _path: str) -> None:
        # The statusline file might have been (re)created
        if _STATUSLINE_PATH.exists():
            if self._watcher and str(_STATUSLINE_PATH) not in (self._watcher.files() or []):
                self._watcher.addPath(str(_STATUSLINE_PATH))
            self._read_statusline()

    def _poll(self) -> None:
        """Periodic poll — tries statusline first, then session files."""
        if _STATUSLINE_PATH.exists():
            self._read_statusline()
        else:
            self._read_session_files()

    # ------------------------------------------------------------------
    # Strategy 1: statusline JSON
    # ------------------------------------------------------------------

    def _read_statusline(self) -> None:
        try:
            text = _STATUSLINE_PATH.read_text(encoding="utf-8")
            data = json.loads(text)
        except (OSError, json.JSONDecodeError) as exc:
            logger.debug("Failed to read statusline: %s", exc)
            return

        ctx = self._extract_float(data, "context_window", "used_percentage") / 100.0
        fh = self._extract_float(data, "rate_limits", "five_hour") / 100.0
        sd = self._extract_float(data, "rate_limits", "seven_day") / 100.0

        self._emit({"ctx": self._clamp(ctx), "5h": self._clamp(fh), "7d": self._clamp(sd)})

    @staticmethod
    def _extract_float(data: dict, *keys: str) -> float:
        """Drill into nested dict and return float, defaulting to 0."""
        current: Any = data
        for k in keys:
            if isinstance(current, dict):
                current = current.get(k, 0)
            else:
                return 0.0
        try:
            return float(current)
        except (TypeError, ValueError):
            return 0.0

    # ------------------------------------------------------------------
    # Strategy 2: session JSONL files
    # ------------------------------------------------------------------

    def _read_session_files(self) -> None:
        """Fallback: scan most recent JSONL for token counts."""
        if not _PROJECTS_DIR.exists():
            return

        # Find the most recently modified .jsonl
        latest: Optional[Path] = None
        latest_mtime = 0.0
        try:
            for root, _dirs, files in os.walk(_PROJECTS_DIR):
                for f in files:
                    if f.endswith(".jsonl"):
                        p = Path(root) / f
                        try:
                            mt = p.stat().st_mtime
                        except OSError:
                            continue
                        if mt > latest_mtime:
                            latest_mtime = mt
                            latest = p
        except OSError:
            return

        if latest is None:
            return

        total_input = 0
        total_output = 0
        try:
            with open(latest, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    msg = entry.get("message", {})
                    if not isinstance(msg, dict):
                        continue
                    usage = msg.get("usage", {})
                    if isinstance(usage, dict):
                        total_input += usage.get("input_tokens", 0)
                        total_output += usage.get("output_tokens", 0)
        except OSError:
            return

        # Approximate: assume 200k context window
        window_size = 200_000
        total_tokens = total_input + total_output
        ctx = min(total_tokens / window_size, 1.0)

        self._emit({"ctx": ctx, "5h": 0.0, "7d": 0.0})

    # ------------------------------------------------------------------

    def _emit(self, data: Dict[str, float]) -> None:
        if data != self._last_data:
            self._last_data = data
            self.usage_updated.emit(data)

    @staticmethod
    def _clamp(v: float) -> float:
        return max(0.0, min(1.0, v))


class UsageMonitor(QObject):
    """Monitors Claude Code usage via Statusline JSON or session files.

    Background work is performed in a dedicated QThread; only
    ``usage_updated`` signals arrive on the main thread.
    """

    usage_updated = pyqtSignal(dict)  # {"ctx": float, "5h": float, "7d": float}

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: Optional[QThread] = None
        self._worker: Optional[_UsageWorker] = None

    def start(self) -> None:
        """Spin up the background worker thread."""
        if self._thread is not None:
            return

        self._thread = QThread(self)
        self._worker = _UsageWorker()
        self._worker.moveToThread(self._thread)
        self._worker.usage_updated.connect(self.usage_updated)
        self._thread.started.connect(self._worker.start)
        self._thread.start()

    def stop(self) -> None:
        """Stop and clean up the worker thread."""
        if self._worker:
            self._worker.stop()
        if self._thread:
            self._thread.quit()
            self._thread.wait(3000)
            if self._thread.isRunning():
                self._thread.terminate()
            self._thread = None
            self._worker = None
