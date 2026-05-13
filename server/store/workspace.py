"""Single-tenant workspace state — JSON file on disk."""

from __future__ import annotations
import json
import threading
from pathlib import Path
from typing import Any


class WorkspaceStore:
    def __init__(self, state_path: Path):
        self.path = Path(state_path)
        self._lock = threading.Lock()

    def save(self, data: dict[str, Any]) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, default=str))
            tmp.replace(self.path)

    def load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        return json.loads(self.path.read_text())

    def update_report_status(self, report_type: str, status_dict: dict[str, Any]) -> None:
        with self._lock:
            data = self.load() or {}
            data.setdefault("hivemind", {}).setdefault("reports", {})[report_type] = status_dict
            self.path.write_text(json.dumps(data, indent=2, default=str))
