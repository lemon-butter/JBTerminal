"""Session watcher — monitors Claude Code JSONL session files."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QFileSystemWatcher, QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)

_CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


class SessionWatcher(QObject):
    """Watches ``~/.claude/projects/`` for session file changes.

    Uses :class:`QFileSystemWatcher` for efficient change detection.
    Parses the last *N* lines of changed JSONL files and emits parsed
    data including message type, token counts, tool usage, and errors.
    """

    session_changed = pyqtSignal(str, dict)  # (session_path, parsed_data)

    # How many lines from the end to parse on each change
    _TAIL_LINES = 50

    def __init__(
        self,
        parent: QObject | None = None,
        projects_dir: Optional[Path] = None,
    ) -> None:
        super().__init__(parent)
        self._projects_dir = projects_dir or _CLAUDE_PROJECTS_DIR
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)
        self._watcher.directoryChanged.connect(self._on_dir_changed)

        # Scan timer to discover new session files periodically
        self._scan_timer = QTimer(self)
        self._scan_timer.setInterval(5000)  # 5 s
        self._scan_timer.timeout.connect(self._scan_directories)

        self._known_files: set[str] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin watching for session files."""
        if not self._projects_dir.exists():
            logger.warning("Claude projects dir not found: %s", self._projects_dir)
            # Start the scan timer anyway — directory may appear later
            self._scan_timer.start()
            return
        self._scan_directories()
        self._scan_timer.start()

    def stop(self) -> None:
        """Stop watching."""
        self._scan_timer.stop()
        files = self._watcher.files()
        if files:
            self._watcher.removePaths(files)
        dirs = self._watcher.directories()
        if dirs:
            self._watcher.removePaths(dirs)

    # ------------------------------------------------------------------
    # Internal — directory scanning
    # ------------------------------------------------------------------

    def _scan_directories(self) -> None:
        """Walk projects dir and watch any new JSONL files / directories."""
        if not self._projects_dir.exists():
            return

        base = str(self._projects_dir)
        if base not in (self._watcher.directories() or []):
            self._watcher.addPath(base)

        try:
            for root, dirs, files in os.walk(self._projects_dir):
                # Watch subdirectories
                for d in dirs:
                    dpath = os.path.join(root, d)
                    if dpath not in (self._watcher.directories() or []):
                        self._watcher.addPath(dpath)
                # Watch JSONL files
                for f in files:
                    if f.endswith(".jsonl"):
                        fpath = os.path.join(root, f)
                        if fpath not in self._known_files:
                            self._known_files.add(fpath)
                            self._watcher.addPath(fpath)
        except OSError as exc:
            logger.debug("Error scanning directories: %s", exc)

    # ------------------------------------------------------------------
    # Internal — file change handling
    # ------------------------------------------------------------------

    def _on_dir_changed(self, path: str) -> None:
        """A watched directory changed — rescan for new files."""
        self._scan_directories()

    def _on_file_changed(self, path: str) -> None:
        """A watched JSONL file changed — parse tail and emit."""
        if not path.endswith(".jsonl"):
            return
        parsed = self._parse_tail(path)
        if parsed is not None:
            self.session_changed.emit(path, parsed)

        # QFileSystemWatcher may drop the path after modification; re-add
        if path not in (self._watcher.files() or []):
            if os.path.exists(path):
                self._watcher.addPath(path)

    def _parse_tail(self, path: str) -> Optional[Dict[str, Any]]:
        """Parse the last N lines of a JSONL file.

        Returns a dict with aggregated information:
        - ``messages``: list of parsed message dicts
        - ``total_input_tokens``: int
        - ``total_output_tokens``: int
        - ``tool_uses``: list of tool names used
        - ``errors``: list of error strings
        - ``last_type``: str or None
        """
        try:
            lines = self._read_tail(path, self._TAIL_LINES)
        except OSError as exc:
            logger.debug("Cannot read %s: %s", path, exc)
            return None

        messages: List[Dict[str, Any]] = []
        total_input = 0
        total_output = 0
        tool_uses: List[str] = []
        errors: List[str] = []
        last_type: Optional[str] = None

        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = entry.get("type")
            if msg_type:
                last_type = msg_type

            # Token counts from message.usage
            usage = None
            message = entry.get("message", {})
            if isinstance(message, dict):
                usage = message.get("usage", {})
            if isinstance(usage, dict):
                total_input += usage.get("input_tokens", 0)
                total_output += usage.get("output_tokens", 0)

            # Tool usage
            content = message.get("content", []) if isinstance(message, dict) else []
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_name = block.get("name", "unknown")
                        tool_uses.append(tool_name)

            # Errors
            if msg_type == "error" or entry.get("error"):
                err_msg = entry.get("error", {})
                if isinstance(err_msg, dict):
                    err_msg = err_msg.get("message", str(err_msg))
                errors.append(str(err_msg))

            messages.append(entry)

        return {
            "messages": messages,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "tool_uses": tool_uses,
            "errors": errors,
            "last_type": last_type,
        }

    @staticmethod
    def _read_tail(path: str, n: int) -> List[str]:
        """Read last *n* lines of a file efficiently.

        For large files, seeks backwards from the end to avoid reading
        the entire file into memory.
        """
        file_size = os.path.getsize(path)  # raises OSError if missing

        # For small files (< 256 KB), just read the whole thing
        if file_size < 256 * 1024:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                all_lines = fh.readlines()
            return all_lines[-n:] if len(all_lines) > n else all_lines

        # For larger files, read from the end in chunks
        chunk_size = min(file_size, max(8192, n * 512))
        with open(path, "rb") as fh:
            fh.seek(max(0, file_size - chunk_size))
            data = fh.read()
        lines = data.decode("utf-8", errors="replace").splitlines(keepends=True)
        # Drop the first (potentially partial) line
        if lines and file_size > chunk_size:
            lines = lines[1:]
        return lines[-n:] if len(lines) > n else lines
