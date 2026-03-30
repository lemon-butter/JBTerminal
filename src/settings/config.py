"""Config — JSON-based settings persistence."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_CONFIG_PATH = Path.home() / ".jbterminal" / "config.json"

DEFAULT_VALUES: Dict[str, Any] = {
    "font_family": "JetBrains Mono",
    "font_size": 14,
    "theme": "Neon Dark",
    "notifications_enabled": True,
    "workspaces": [],
    "workspace_notifications": {},  # workspace_id -> bool
}


class Config:
    """Application settings with JSON persistence."""

    def __init__(self, path: Path = DEFAULT_CONFIG_PATH) -> None:
        self._path = path
        self._data: Dict[str, Any] = {}

    def load(self) -> None:
        """Load config from disk."""
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def save(self) -> None:
        """Save config to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def get(self, key: str, default: object = None) -> object:
        fallback = DEFAULT_VALUES.get(key, default)
        return self._data.get(key, fallback)

    def set(self, key: str, value: object) -> None:
        self._data[key] = value

    # --- Workspace management ---

    def get_workspaces(self) -> List[Dict[str, str]]:
        """Return list of workspace dicts with keys: id, name, path."""
        return list(self._data.get("workspaces", []))

    def add_workspace(self, name: str, path: str) -> str:
        """Add a workspace and return its generated id."""
        workspaces = self._data.setdefault("workspaces", [])
        ws_id = uuid.uuid4().hex[:8]
        workspaces.append({"id": ws_id, "name": name, "path": path})
        return ws_id

    def remove_workspace(self, ws_id: str) -> bool:
        """Remove a workspace by id. Returns True if found."""
        workspaces = self._data.get("workspaces", [])
        for i, ws in enumerate(workspaces):
            if ws.get("id") == ws_id:
                workspaces.pop(i)
                # Clean up notification setting
                notifs = self._data.get("workspace_notifications", {})
                notifs.pop(ws_id, None)
                return True
        return False

    # --- Theme ---

    def get_theme(self) -> str:
        """Return current theme name."""
        return str(self._data.get("theme", DEFAULT_VALUES["theme"]))

    def set_theme(self, name: str) -> None:
        self._data["theme"] = name

    # --- Font ---

    def get_font(self) -> Dict[str, Any]:
        """Return font dict with 'family' and 'size' keys."""
        return {
            "family": self._data.get("font_family", DEFAULT_VALUES["font_family"]),
            "size": self._data.get("font_size", DEFAULT_VALUES["font_size"]),
        }

    def set_font(self, family: str, size: int) -> None:
        self._data["font_family"] = family
        self._data["font_size"] = size

    # --- Notifications ---

    def get_notifications_enabled(self, workspace_id: Optional[str] = None) -> bool:
        """Return whether notifications are enabled.

        If *workspace_id* is given, check per-workspace override first,
        falling back to global setting.
        """
        global_enabled = self._data.get(
            "notifications_enabled", DEFAULT_VALUES["notifications_enabled"]
        )
        if workspace_id is None:
            return bool(global_enabled)
        ws_notifs = self._data.get("workspace_notifications", {})
        return bool(ws_notifs.get(workspace_id, global_enabled))

    def set_notifications_enabled(
        self, enabled: bool, workspace_id: Optional[str] = None
    ) -> None:
        if workspace_id is None:
            self._data["notifications_enabled"] = enabled
        else:
            ws_notifs = self._data.setdefault("workspace_notifications", {})
            ws_notifs[workspace_id] = enabled
