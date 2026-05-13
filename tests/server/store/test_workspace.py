import json
import pytest
from server.store.workspace import WorkspaceStore


def test_save_and_load_workspace(tmp_path):
    store = WorkspaceStore(state_path=tmp_path / "ws.json")
    data = {
        "workspace_id": "ws_1",
        "business": {"name": "Demo", "description": "test", "audiences": [], "geographies": [], "stage": "seed", "voice_notes": "", "focus_notes": ""},
        "brand": {"logo_path": "", "accent_hex": "#000", "voice_notes": ""},
        "hivemind": {"project_id": "p1", "reports": {}},
        "platforms": {"linkedin": {}, "facebook": {}},
        "created_at": "2026-05-13T15:00:00Z",
    }
    store.save(data)
    loaded = store.load()
    assert loaded["workspace_id"] == "ws_1"


def test_load_missing_returns_none(tmp_path):
    store = WorkspaceStore(state_path=tmp_path / "missing.json")
    assert store.load() is None


def test_update_report_status(tmp_path):
    store = WorkspaceStore(state_path=tmp_path / "ws.json")
    store.save({"workspace_id": "ws_1", "hivemind": {"project_id": "p", "reports": {}}})
    store.update_report_status("competitive_intelligence", {"job_id": "j-1", "status": "queued"})
    loaded = store.load()
    assert loaded["hivemind"]["reports"]["competitive_intelligence"]["job_id"] == "j-1"
