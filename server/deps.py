"""Lazy singletons for the sidecar process."""

import os
from pathlib import Path
from server.hivemind.client import HivemindClient
from server.hivemind.poller import EnrichmentPoller
from server.store.workspace import WorkspaceStore
from server.store.db import DraftsDB


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = PROJECT_ROOT / "workspace"
WORKSPACE_DIR.mkdir(exist_ok=True)


_hm: HivemindClient | None = None
_ws: WorkspaceStore | None = None
_db: DraftsDB | None = None
_poller: EnrichmentPoller | None = None


def hivemind() -> HivemindClient:
    global _hm
    if _hm is None:
        _hm = HivemindClient(
            api_key=os.environ["HIVEMIND_API_KEY"],
            base_url=os.environ.get("HIVEMIND_BASE_URL", "https://hivemind.myosin.xyz"),
        )
    return _hm


def workspace_store() -> WorkspaceStore:
    global _ws
    if _ws is None:
        _ws = WorkspaceStore(state_path=WORKSPACE_DIR / "workspace_state.json")
    return _ws


def drafts_db() -> DraftsDB:
    global _db
    if _db is None:
        _db = DraftsDB(db_path=WORKSPACE_DIR / "workspace.db")
    return _db


def poller() -> EnrichmentPoller:
    global _poller
    if _poller is None:
        _poller = EnrichmentPoller(hivemind=hivemind(), store=workspace_store())
    return _poller
