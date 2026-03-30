"""Notifier — macOS system notifications with categories and actions."""

from __future__ import annotations

import logging
import subprocess
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


# Sound names for notification categories
_CATEGORY_SOUNDS = {
    "task_complete": "Glass",
    "task_error": "Sosumi",
}

# Default sound when no category specified
_DEFAULT_SOUND = "default"


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

    Supports notification categories ("task_complete", "task_error") with
    different sounds, and a "Show" action button to bring the app to front.
    """

    # Emitted when user clicks the "Show" action on a notification
    show_requested = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._use_pyobjc = _try_pyobjc()
        self._permission_requested = False
        self._permission_granted: Optional[bool] = None
        self._categories_registered = False
        self._delegate = None

        if self._use_pyobjc:
            self._request_permission()
            self._register_categories()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def notify(
        self,
        title: str,
        body: str,
        sound: bool = True,
        category: str = "",
    ) -> None:
        """Send a notification.

        Parameters
        ----------
        title:
            Notification title.
        body:
            Notification body text.
        sound:
            Whether to play an alert sound.
        category:
            Notification category: "task_complete", "task_error", or "".
            Different categories use different sounds.
        """
        if self._use_pyobjc:
            self._notify_pyobjc(title, body, sound, category)
        else:
            self._notify_osascript(title, body, sound, category)

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
                UN.UNAuthorizationOptionAlert
                | UN.UNAuthorizationOptionSound
                | UN.UNAuthorizationOptionBadge,
                _handler,
            )
        except Exception as exc:
            logger.warning("Failed to request notification permission: %s", exc)
            self._use_pyobjc = False

    def _register_categories(self) -> None:
        """Register notification categories with action buttons."""
        if self._categories_registered:
            return
        self._categories_registered = True

        try:
            import UserNotifications as UN

            # "Show" action — brings app to front
            show_action = (
                UN.UNNotificationAction.actionWithIdentifier_title_options_(
                    "SHOW_ACTION",
                    "Show",
                    UN.UNNotificationActionOptionForeground,
                )
            )

            # task_complete category
            complete_category = (
                UN.UNNotificationCategory.categoryWithIdentifier_actions_intentIdentifiers_options_(
                    "task_complete",
                    [show_action],
                    [],
                    0,
                )
            )

            # task_error category
            error_category = (
                UN.UNNotificationCategory.categoryWithIdentifier_actions_intentIdentifiers_options_(
                    "task_error",
                    [show_action],
                    [],
                    0,
                )
            )

            center = UN.UNUserNotificationCenter.currentNotificationCenter()
            center.setNotificationCategories_({complete_category, error_category})

            # Set delegate for handling actions
            self._setup_delegate(center)

        except Exception as exc:
            logger.warning("Failed to register notification categories: %s", exc)

    def _setup_delegate(self, center: object) -> None:
        """Set up a notification center delegate to handle action responses."""
        try:
            import objc
            from Foundation import NSObject

            notifier_ref = self

            class _NotificationDelegate(NSObject):
                """Handles notification action responses."""

                def userNotificationCenter_didReceiveNotificationResponse_withCompletionHandler_(
                    self, center, response, handler
                ):
                    action_id = response.actionIdentifier()
                    if action_id in (
                        "SHOW_ACTION",
                        "com.apple.UNNotificationDefaultActionIdentifier",
                    ):
                        # Emit signal to bring app to front
                        try:
                            notifier_ref.show_requested.emit()
                        except RuntimeError:
                            pass
                    if handler:
                        handler()

                def userNotificationCenter_willPresentNotification_withCompletionHandler_(
                    self, center, notification, handler
                ):
                    # Show notification even when app is in foreground
                    try:
                        import UserNotifications as UN
                        if handler:
                            handler(
                                UN.UNNotificationPresentationOptionBanner
                                | UN.UNNotificationPresentationOptionSound
                            )
                    except Exception:
                        if handler:
                            handler(0)

            self._delegate = _NotificationDelegate.alloc().init()
            center.setDelegate_(self._delegate)

        except Exception as exc:
            logger.debug("Could not set notification delegate: %s", exc)

    def _notify_pyobjc(
        self, title: str, body: str, sound: bool, category: str
    ) -> None:
        try:
            import UserNotifications as UN
            import uuid as _uuid

            content = UN.UNMutableNotificationContent.alloc().init()
            content.setTitle_(title)
            content.setBody_(body)

            if sound:
                sound_name = _CATEGORY_SOUNDS.get(category, _DEFAULT_SOUND)
                if sound_name == "default":
                    content.setSound_(UN.UNNotificationSound.defaultSound())
                else:
                    content.setSound_(
                        UN.UNNotificationSound.soundNamed_(sound_name)
                    )

            # Set category for action buttons
            if category:
                content.setCategoryIdentifier_(category)

            request = UN.UNNotificationRequest.requestWithIdentifier_content_trigger_(
                _uuid.uuid4().hex, content, None
            )
            center = UN.UNUserNotificationCenter.currentNotificationCenter()
            center.addNotificationRequest_withCompletionHandler_(request, None)
        except Exception as exc:
            logger.warning("pyobjc notification failed, falling back: %s", exc)
            self._notify_osascript(title, body, sound, category)

    # ------------------------------------------------------------------
    # osascript fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _notify_osascript(
        title: str, body: str, sound: bool, category: str = ""
    ) -> None:
        """Send notification via AppleScript (always available on macOS)."""
        # Escape double quotes for AppleScript
        t = title.replace('"', '\\"')
        b = body.replace('"', '\\"')
        sound_name = _CATEGORY_SOUNDS.get(category, _DEFAULT_SOUND) if sound else ""
        sound_clause = f' sound name "{sound_name}"' if sound_name else ""
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
