"""Config — JSON-based settings persistence."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".jbterminal" / "config.json"


class Config:
    """Application settings with JSON persistence."""

    def __init__(self, path: Path = DEFAULT_CONFIG_PATH) -> None:
        self._path = path
        self._data: dict = {}

    def load(self) -> None:
        """Load config from disk."""
        if self._path.exists():
            self._data = json.loads(self._path.read_text())

    def save(self) -> None:
        """Save config to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2))

    def get(self, key: str, default: object = None) -> object:
        return self._data.get(key, default)

    def set(self, key: str, value: object) -> None:
        self._data[key] = value
