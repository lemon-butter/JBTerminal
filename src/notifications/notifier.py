"""Notifier — macOS system notifications."""

from __future__ import annotations

import logging
import subprocess
from typing import Optional

from PyQt6.QtCore import QObject

logger = logging.getLogger(__name__)


def _try_pyobjc() -> bool:
    """Return True if pyobjc notification API is available."""
    try:
        import objc  # noqa: F401
        from Foundation import NSObject  # noqa: F401
        import UserNotifications  # noqa: F401
        return True
    except ImportError:
        return False


class Notifier(QObject):
    """Sends macOS native notifications via pyobjc or osascript.

    Prefers ``UNUserNotificationCenter`` from pyobjc; falls back to
    ``osascript`` if pyobjc is unavailable.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._use_pyobjc = _try_pyobjc()
        self._permission_requested = False
        self._permission_granted: Optional[bool] = None

        if self._use_pyobjc:
            self._request_permission()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def notify(self, title: str, body: str, sound: bool = True) -> None:
        """Send a notification.

        Parameters
        ----------
        title:
            Notification title.
        body:
            Notification body text.
        sound:
            Whether to play the default alert sound.
        """
        if self._use_pyobjc:
            self._notify_pyobjc(title, body, sound)
        else:
            self._notify_osascript(title, body, sound)

    # ------------------------------------------------------------------
    # pyobjc implementation
    # ------------------------------------------------------------------

    def _request_permission(self) -> None:
        """Request notification permission (non-blocking)."""
        if self._permission_requested:
            return
        self._permission_requested = True

        try:
            import UserNotifications as UN

            center = UN.UNUserNotificationCenter.currentNotificationCenter()

            def _handler(granted: bool, error: object) -> None:
                self._permission_granted = granted
                if not granted:
                    logger.warning(
                        "Notification permission denied (error=%s)", error
                    )

            center.requestAuthorizationWithOptions_completionHandler_(
                UN.UNAuthorizationOptionAlert | UN.UNAuthorizationOptionSound,
                _handler,
            )
        except Exception as exc:
            logger.warning("Failed to request notification permission: %s", exc)
            self._use_pyobjc = False

    def _notify_pyobjc(self, title: str, body: str, sound: bool) -> None:
        try:
            import UserNotifications as UN
            import uuid as _uuid

            content = UN.UNMutableNotificationContent.alloc().init()
            content.setTitle_(title)
            content.setBody_(body)
            if sound:
                content.setSound_(UN.UNNotificationSound.defaultSound())

            request = UN.UNNotificationRequest.requestWithIdentifier_content_trigger_(
                _uuid.uuid4().hex, content, None
            )
            center = UN.UNUserNotificationCenter.currentNotificationCenter()
            center.addNotificationRequest_withCompletionHandler_(request, None)
        except Exception as exc:
            logger.warning("pyobjc notification failed, falling back: %s", exc)
            self._notify_osascript(title, body, sound)

    # ------------------------------------------------------------------
    # osascript fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _notify_osascript(title: str, body: str, sound: bool) -> None:
        """Send notification via AppleScript (always available on macOS)."""
        # Escape double quotes for AppleScript
        t = title.replace('"', '\\"')
        b = body.replace('"', '\\"')
        sound_clause = ' sound name "default"' if sound else ""
        script = (
            f'display notification "{b}" with title "{t}"{sound_clause}'
        )
        try:
            subprocess.Popen(
                ["osascript", "-e", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            logger.warning("osascript notification failed: %s", exc)
