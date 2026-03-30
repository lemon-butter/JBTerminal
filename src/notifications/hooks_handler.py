"""Claude Code Hooks handler — receives and routes hook events.

Claude Code can emit hook events (Stop, StopFailure, Notification) as JSON.
This module parses those events and routes them to the appropriate handlers:
  - Notifier for system notifications
  - StateDetector for status updates
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class HookEventType(str, Enum):
    """Known Claude Code hook event types."""
    STOP = "Stop"
    STOP_FAILURE = "StopFailure"
    NOTIFICATION = "Notification"
    TOOL_START = "ToolStart"
    TOOL_END = "ToolEnd"
    STATUS = "Status"


class HookEvent:
    """Parsed representation of a Claude Code hook event."""

    __slots__ = ("event_type", "message", "title", "data", "raw")

    def __init__(
        self,
        event_type: str,
        message: str = "",
        title: str = "",
        data: Optional[Dict[str, Any]] = None,
        raw: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.event_type = event_type
        self.message = message
        self.title = title
        self.data = data or {}
        self.raw = raw or {}

    def __repr__(self) -> str:
        return (
            f"HookEvent(type={self.event_type!r}, "
            f"title={self.title!r}, message={self.message!r})"
        )


class HooksHandler(QObject):
    """Parses Claude Code hook JSON events and emits typed signals.

    Usage::

        handler = HooksHandler()
        handler.hook_stop.connect(on_stop)
        handler.hook_notification.connect(on_notif)
        handler.feed(raw_json_bytes)

    The handler can also be connected to a Notifier and StateDetector
    via :meth:`connect_notifier` and :meth:`connect_state_detector`.
    """

    # Signals for each event type
    hook_stop = pyqtSignal(object)            # HookEvent
    hook_stop_failure = pyqtSignal(object)    # HookEvent
    hook_notification = pyqtSignal(object)    # HookEvent
    hook_tool_start = pyqtSignal(object)      # HookEvent
    hook_tool_end = pyqtSignal(object)        # HookEvent
    hook_status = pyqtSignal(object)          # HookEvent
    hook_unknown = pyqtSignal(object)         # HookEvent

    # Convenience: any event at all
    hook_event = pyqtSignal(object)           # HookEvent

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._notifier: Optional[Any] = None
        self._state_detector: Optional[Any] = None
        self._pane_id: str = ""
        self._config: Optional[Any] = None
        self._workspace_id: Optional[str] = None

        self._signal_map: Dict[str, pyqtSignal] = {
            HookEventType.STOP: self.hook_stop,
            HookEventType.STOP_FAILURE: self.hook_stop_failure,
            HookEventType.NOTIFICATION: self.hook_notification,
            HookEventType.TOOL_START: self.hook_tool_start,
            HookEventType.TOOL_END: self.hook_tool_end,
            HookEventType.STATUS: self.hook_status,
        }

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_pane_id(self, pane_id: str) -> None:
        """Associate this handler with a specific pane."""
        self._pane_id = pane_id

    def set_workspace_id(self, workspace_id: Optional[str]) -> None:
        """Set the current workspace ID for notification filtering."""
        self._workspace_id = workspace_id

    def connect_notifier(self, notifier: Any) -> None:
        """Connect a Notifier instance for system notifications.

        The notifier must have a ``notify`` method matching the
        :class:`~src.notifications.notifier.Notifier` interface.
        """
        self._notifier = notifier

    def connect_state_detector(self, state_detector: Any) -> None:
        """Connect a StateDetector for status routing.

        The state_detector must have a ``feed`` method matching the
        :class:`~src.status.state_detector.StateDetector` interface.
        """
        self._state_detector = state_detector

    def connect_config(self, config: Any) -> None:
        """Connect a Config instance for notification filtering."""
        self._config = config

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def feed(self, raw: bytes | str) -> None:
        """Parse raw JSON data and route the event.

        Parameters
        ----------
        raw:
            JSON bytes or string from Claude Code hooks output.
            May contain multiple JSON objects separated by newlines.
        """
        text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw

        for line in text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                logger.debug("HooksHandler: skipping non-JSON line: %s", line[:80])
                continue

            event = self._parse_event(data)
            if event is not None:
                self._route_event(event)

    def _parse_event(self, data: Dict[str, Any]) -> Optional[HookEvent]:
        """Parse a JSON dict into a HookEvent."""
        if not isinstance(data, dict):
            return None

        event_type = data.get("type") or data.get("event") or data.get("hook") or ""
        message = data.get("message") or data.get("body") or data.get("text") or ""
        title = data.get("title") or data.get("name") or ""

        # Normalise event_type: Claude Code may send lowercase variants
        type_map = {v.value.lower(): v.value for v in HookEventType}
        normalised = type_map.get(event_type.lower(), event_type)

        return HookEvent(
            event_type=normalised,
            message=str(message),
            title=str(title),
            data=data.get("data", {}),
            raw=data,
        )

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def _route_event(self, event: HookEvent) -> None:
        """Route a parsed event to the appropriate signal and handler."""
        # Emit the generic signal
        self.hook_event.emit(event)

        # Emit the type-specific signal
        sig = self._signal_map.get(event.event_type)
        if sig is not None:
            sig.emit(event)
        else:
            self.hook_unknown.emit(event)

        # Route to Notifier
        if event.event_type == HookEventType.STOP:
            self._send_notification(
                title=event.title or "Task Complete",
                body=event.message or "Claude Code has finished.",
                category="task_complete",
            )
        elif event.event_type == HookEventType.STOP_FAILURE:
            self._send_notification(
                title=event.title or "Task Failed",
                body=event.message or "Claude Code encountered an error.",
                category="task_error",
            )
        elif event.event_type == HookEventType.NOTIFICATION:
            self._send_notification(
                title=event.title or "JBTerminal",
                body=event.message,
                category="task_complete",
            )

        # Route to StateDetector
        if self._state_detector and self._pane_id:
            state_text = self._event_to_state_text(event)
            if state_text:
                self._state_detector.feed(
                    self._pane_id, state_text.encode("utf-8")
                )

    def _send_notification(
        self, title: str, body: str, category: str = "task_complete"
    ) -> None:
        """Send notification through the Notifier, respecting config."""
        if self._notifier is None:
            return

        # Check config for notification permission
        if self._config is not None:
            enabled = self._config.get_notifications_enabled(self._workspace_id)
            if not enabled:
                logger.debug("Notifications disabled for workspace %s", self._workspace_id)
                return

        self._notifier.notify(title, body, category=category)

    @staticmethod
    def _event_to_state_text(event: HookEvent) -> str:
        """Convert a hook event into synthetic PTY text for StateDetector."""
        mapping = {
            HookEventType.STOP: "\u2714 Done",          # check mark
            HookEventType.STOP_FAILURE: "\u2717 Error:", # cross mark
            HookEventType.TOOL_START: "Running:",
            HookEventType.TOOL_END: "Running:",
        }
        return mapping.get(event.event_type, "")
