"""Config — JSON-based settings persistence."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_CONFIG_PATH = Path.home() / ".jbterminal" / "config.json"

DEFAULT_VALUES: Dict[str, Any] = {
    "font_family": "Menlo",
    "font_size": 14,
    "theme": "Neon Dark",
    "line_spacing": 1.0,
    "scrollback_lines": 10000,
    "cursor_blink": True,
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

    # --- Layout state save/restore ---

    def save_layout(self, workspaces: List[Dict[str, Any]]) -> None:
        """Save workspace layout state (tabs, pane tree structure).

        Each workspace dict should contain:
          - id, name, path
          - active_tab_index
          - tabs: list of {id, name, pane_tree, active_pane_id}
        where pane_tree is the serialized PaneNode tree.
        """
        self._data["workspace_layouts"] = workspaces

    def load_layout(self) -> List[Dict[str, Any]]:
        """Load saved workspace layout state.

        Returns list of workspace layout dicts, or empty list.
        """
        return list(self._data.get("workspace_layouts", []))

    @staticmethod
    def serialize_pane_tree(node: Any) -> Dict[str, Any]:
        """Serialize a PaneNode tree to a JSON-compatible dict.

        Imported lazily to avoid circular imports.
        """
        from src.models.pane_tree import PaneLeaf, PaneSplit

        if isinstance(node, PaneLeaf):
            return {
                "type": "leaf",
                "id": node.id,
                "name": node.name,
            }
        elif isinstance(node, PaneSplit):
            return {
                "type": "split",
                "id": node.id,
                "direction": node.direction.value,
                "ratio": node.ratio,
                "first": Config.serialize_pane_tree(node.first),
                "second": Config.serialize_pane_tree(node.second),
            }
        # Fallback: treat as single leaf
        return {"type": "leaf", "id": "unknown", "name": "Terminal"}

    @staticmethod
    def deserialize_pane_tree(data: Dict[str, Any]) -> Any:
        """Deserialize a JSON dict back into a PaneNode tree."""
        from src.models.pane_tree import PaneLeaf, PaneSplit
        from src.models.enums import SplitDirection

        if data.get("type") == "leaf":
            return PaneLeaf(
                id=data.get("id", ""),
                name=data.get("name", "Terminal"),
            )
        elif data.get("type") == "split":
            return PaneSplit(
                id=data.get("id", ""),
                direction=SplitDirection(data.get("direction", "horizontal")),
                ratio=data.get("ratio", 0.5),
                first=Config.deserialize_pane_tree(data.get("first", {})),
                second=Config.deserialize_pane_tree(data.get("second", {})),
            )
        # Fallback
        return PaneLeaf()

    def save_workspace_layout(self, workspace: Any) -> None:
        """Convenience: save a single Workspace model object's layout.

        *workspace* is expected to be a ``src.models.workspace.Workspace`` instance.
        """
        tabs_data: List[Dict[str, Any]] = []
        for tab in workspace.tabs:
            tabs_data.append({
                "id": tab.id,
                "name": tab.name,
                "pane_tree": Config.serialize_pane_tree(tab.pane_root),
                "active_pane_id": tab.active_pane_id,
            })
        ws_data = {
            "id": workspace.id,
            "name": workspace.name,
            "path": workspace.path,
            "active_tab_index": workspace.active_tab_index,
            "tabs": tabs_data,
        }
        layouts = self._data.get("workspace_layouts", [])
        # Replace existing entry or append
        for i, existing in enumerate(layouts):
            if existing.get("id") == workspace.id:
                layouts[i] = ws_data
                self._data["workspace_layouts"] = layouts
                return
        layouts.append(ws_data)
        self._data["workspace_layouts"] = layouts

    def load_workspace_layout(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Load layout for a specific workspace by id."""
        for ws_data in self._data.get("workspace_layouts", []):
            if ws_data.get("id") == workspace_id:
                return ws_data
        return None

    def restore_workspace_from_layout(self, ws_data: Dict[str, Any]) -> Any:
        """Restore a Workspace model object from saved layout data.

        Returns a ``src.models.workspace.Workspace`` instance.
        """
        from src.models.workspace import Workspace, WorkspaceTab

        tabs: list = []
        for tab_data in ws_data.get("tabs", []):
            pane_tree = Config.deserialize_pane_tree(
                tab_data.get("pane_tree", {"type": "leaf"})
            )
            tab = WorkspaceTab(
                id=tab_data.get("id", ""),
                name=tab_data.get("name", "Terminal"),
                pane_root=pane_tree,
                active_pane_id=tab_data.get("active_pane_id", ""),
            )
            tabs.append(tab)

        if not tabs:
            tabs = [WorkspaceTab()]

        workspace = Workspace(
            id=ws_data.get("id", ""),
            name=ws_data.get("name", ""),
            path=ws_data.get("path", ""),
            tabs=tabs,
            active_tab_index=ws_data.get("active_tab_index", 0),
        )
        return workspace
