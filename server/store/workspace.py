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

    def update_enrichment_status(self, project_id: str, status: str) -> None:
        with self._lock:
            data = self.load() or {}
            hivemind = data.setdefault("hivemind", {})
            hivemind["project_id"] = project_id
            hivemind["enrichment_status"] = status
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, default=str))
            tmp.replace(self.path)

    def update_project_info(self, project_id: str, info: dict[str, Any]) -> None:
        with self._lock:
            data = self.load() or {}
            if data.get("hivemind", {}).get("project_id") != project_id:
                return
            project = data.setdefault("project", {})
            for key in ("project_name", "description", "geographics", "audiences"):
                value = info.get(key)
                if value is not None:
                    project[key] = value
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, default=str))
            tmp.replace(self.path)
