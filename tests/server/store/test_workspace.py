from server.store.workspace import WorkspaceStore


def test_save_and_load_workspace(tmp_path):
    store = WorkspaceStore(state_path=tmp_path / "ws.json")
    data = {
        "workspace_id": "ws_1",
        "hivemind": {"project_id": "p1", "website_url": "https://demo.test", "enrichment_status": "enriching"},
        "business": {"voice_notes": "", "focus_notes": ""},
        "platforms": {},
        "created_at": "2026-05-14T05:00:00Z",
    }
    store.save(data)
    loaded = store.load()
    assert loaded["workspace_id"] == "ws_1"
    assert loaded["hivemind"]["enrichment_status"] == "enriching"


def test_load_missing_returns_none(tmp_path):
    store = WorkspaceStore(state_path=tmp_path / "missing.json")
    assert store.load() is None


def test_update_enrichment_status(tmp_path):
    store = WorkspaceStore(state_path=tmp_path / "ws.json")
    store.save({"workspace_id": "ws_1", "hivemind": {"project_id": "p1"}, "business": {}, "platforms": {}})
    store.update_enrichment_status("p1", "ready")
    loaded = store.load()
    assert loaded["hivemind"]["enrichment_status"] == "ready"
    assert loaded["hivemind"]["project_id"] == "p1"
