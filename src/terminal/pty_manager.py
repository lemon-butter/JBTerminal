"""PTY process pool manager -- spawns and manages terminal processes."""

from __future__ import annotations

import fcntl
import os
import pty
import signal
import struct
import subprocess
import termios
from dataclasses import dataclass, field
from typing import Dict, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal


@dataclass
class PtyProcess:
    """Holds state for a single PTY process."""
    pane_id: str
    pid: int
    fd: int  # master file descriptor
    cwd: str
    cols: int = 80
    rows: int = 24
    reader_thread: Optional["PtyReaderThread"] = field(default=None, repr=False)


class PtyReaderThread(QThread):
    """QThread that reads from a PTY master fd and emits data via signal."""

    data_ready = pyqtSignal(str, bytes)  # (pane_id, data)
    process_exited = pyqtSignal(str, int)  # (pane_id, exit_code)

    def __init__(
        self, pane_id: str, fd: int, pid: int, parent: QObject = None
    ) -> None:
        super().__init__(parent)
        self._pane_id = pane_id
        self._fd = fd
        self._pid = pid
        self._running = True

    def run(self) -> None:
        """Read loop -- runs in a background thread."""
        try:
            while self._running:
                try:
                    data = os.read(self._fd, 65536)
                    if not data:
                        break
                    self.data_ready.emit(self._pane_id, data)
                except OSError:
                    # fd closed or process gone
                    break
        finally:
            # Reap the child process
            exit_code = self._reap()
            self.process_exited.emit(self._pane_id, exit_code)

    def _reap(self) -> int:
        """Wait for child process and return exit code.

        Tries WNOHANG first; if that returns (0, 0) — meaning the child is
        still alive — do a blocking waitpid with a short timeout to avoid
        leaving zombie processes.
        """
        try:
            pid_result, status = os.waitpid(self._pid, os.WNOHANG)
            if pid_result == 0:
                # Child still running; give it a moment then try blocking
                import time
                time.sleep(0.1)
                pid_result, status = os.waitpid(self._pid, os.WNOHANG)
            if pid_result != 0 and os.WIFEXITED(status):
                return os.WEXITSTATUS(status)
            return -1
        except ChildProcessError:
            return -1
        except Exception:
            return -1

    def stop(self) -> None:
        """Signal the reader loop to stop."""
        self._running = False


class PtyManager(QObject):
    """Manages PTY processes for all terminal panes."""

    pty_spawned = pyqtSignal(str)           # (pane_id)
    pty_exited = pyqtSignal(str, int)       # (pane_id, exit_code)
    pty_output = pyqtSignal(str, bytes)     # (pane_id, data)
    pty_cwd_changed = pyqtSignal(str, str)  # (pane_id, new_cwd)

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)
        self._processes: Dict[str, PtyProcess] = {}

    def spawn(self, pane_id: str, cwd: str, shell: str = "") -> bool:
        """Spawn a new PTY process for the given pane.

        Uses subprocess.Popen with PTY slave as stdin/stdout/stderr.
        This avoids os.fork() which is unsafe after Qt is initialized on macOS.

        Returns True on success, False on failure.
        """
        if pane_id in self._processes:
            return False

        if not shell:
            shell = os.environ.get("SHELL", "/bin/zsh")

        if not os.path.isdir(cwd):
            cwd = os.path.expanduser("~")

        try:
            # Create a new pseudo-terminal pair
            master_fd, slave_fd = pty.openpty()

            # Set initial window size
            cols, rows = 80, 24
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

            # Build environment
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"
            env.setdefault("LANG", "en_US.UTF-8")

            # Spawn via subprocess.Popen — safe with Qt (no os.fork in parent)
            process = subprocess.Popen(
                [shell, "-l"],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=cwd,
                env=env,
                start_new_session=True,
                close_fds=True,
            )

            # Close slave in parent — only master is needed
            os.close(slave_fd)

            pid = process.pid

            proc = PtyProcess(
                pane_id=pane_id,
                pid=pid,
                fd=master_fd,
                cwd=cwd,
                cols=cols,
                rows=rows,
            )

            # Start reader thread
            reader = PtyReaderThread(pane_id, master_fd, pid, self)
            reader.data_ready.connect(self._on_data_ready)
            reader.process_exited.connect(self._on_process_exited)
            proc.reader_thread = reader
            self._processes[pane_id] = proc

            reader.start()
            self.pty_spawned.emit(pane_id)
            return True

        except Exception:
            return False

    def write(self, pane_id: str, data: bytes) -> None:
        """Write data to PTY stdin."""
        proc = self._processes.get(pane_id)
        if proc is None:
            return
        try:
            os.write(proc.fd, data)
        except OSError:
            pass

    def resize(self, pane_id: str, cols: int, rows: int) -> None:
        """Resize PTY window (sends SIGWINCH to the child process group)."""
        proc = self._processes.get(pane_id)
        if proc is None:
            return
        proc.cols = cols
        proc.rows = rows
        try:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(proc.fd, termios.TIOCSWINSZ, winsize)
            # Send SIGWINCH to the process group
            os.kill(proc.pid, signal.SIGWINCH)
        except OSError:
            pass

    def kill(self, pane_id: str) -> None:
        """Kill a specific PTY process and clean up."""
        proc = self._processes.pop(pane_id, None)
        if proc is None:
            return
        self._cleanup_process(proc)

    def kill_all(self) -> None:
        """Kill all PTY processes (app shutdown)."""
        pane_ids = list(self._processes.keys())
        for pane_id in pane_ids:
            self.kill(pane_id)

    def get_process(self, pane_id: str) -> Optional[PtyProcess]:
        """Return the PtyProcess for a given pane, or None."""
        return self._processes.get(pane_id)

    def has_process(self, pane_id: str) -> bool:
        """Check if a process exists for the given pane."""
        return pane_id in self._processes

    def remap(self, old_pane_id: str, new_pane_id: str) -> bool:
        """Re-key a PTY process from *old_pane_id* to *new_pane_id*.

        This is used when a terminal is moved between panes (e.g. via
        tab-to-pane drag-and-drop). The underlying PTY process and reader
        thread remain the same; only the lookup key changes.

        Returns True if the remap succeeded, False otherwise.
        """
        proc = self._processes.pop(old_pane_id, None)
        if proc is None:
            return False
        proc.pane_id = new_pane_id
        # Update the reader thread's pane_id so it emits signals with the new id
        if proc.reader_thread is not None:
            proc.reader_thread._pane_id = new_pane_id
        self._processes[new_pane_id] = proc
        return True

    def _cleanup_process(self, proc: PtyProcess) -> None:
        """Stop reader thread, close fd, kill child."""
        # Stop reader thread
        if proc.reader_thread is not None:
            proc.reader_thread.stop()
            proc.reader_thread.quit()
            proc.reader_thread.wait(3000)
            if proc.reader_thread.isRunning():
                proc.reader_thread.terminate()

        # Close the master fd
        try:
            os.close(proc.fd)
        except OSError:
            pass

        # Kill the child process
        try:
            os.kill(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except OSError:
            pass

        # Reap zombie — retry briefly if child is not yet exited
        for _ in range(3):
            try:
                pid_result, _ = os.waitpid(proc.pid, os.WNOHANG)
                if pid_result != 0:
                    break
                import time
                time.sleep(0.05)
            except ChildProcessError:
                break
            except OSError:
                break

    def _on_data_ready(self, pane_id: str, data: bytes) -> None:
        """Forward data from reader thread to pty_output signal."""
        self.pty_output.emit(pane_id, data)

    def _on_process_exited(self, pane_id: str, exit_code: int) -> None:
        """Handle process exit: clean up and emit signal."""
        proc = self._processes.pop(pane_id, None)
        if proc is not None:
            try:
                os.close(proc.fd)
            except OSError:
                pass
        self.pty_exited.emit(pane_id, exit_code)
