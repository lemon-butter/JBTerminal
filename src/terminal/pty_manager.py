"""PTY process pool manager — spawns and manages terminal processes."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class PtyManager(QObject):
    """Manages PTY processes for all terminal panes."""

    pty_spawned = pyqtSignal(str)           # (pane_id)
    pty_exited = pyqtSignal(str, int)       # (pane_id, exit_code)
    pty_output = pyqtSignal(str, bytes)     # (pane_id, data)
    pty_cwd_changed = pyqtSignal(str, str)  # (pane_id, new_cwd)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._processes: dict[str, object] = {}  # pane_id -> PTY process

    def spawn(self, pane_id: str, cwd: str, shell: str = "") -> bool:
        """Spawn a new PTY process for the given pane."""
        raise NotImplementedError

    def write(self, pane_id: str, data: bytes) -> None:
        """Write data to PTY stdin."""
        raise NotImplementedError

    def resize(self, pane_id: str, cols: int, rows: int) -> None:
        """Resize PTY window."""
        raise NotImplementedError

    def kill(self, pane_id: str) -> None:
        """Kill a specific PTY process."""
        raise NotImplementedError

    def kill_all(self) -> None:
        """Kill all PTY processes (app shutdown)."""
        raise NotImplementedError
