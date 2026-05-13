import pytest
from server.store.db import DraftsDB


@pytest.fixture
def db(tmp_path):
    return DraftsDB(db_path=tmp_path / "test.db")


def test_insert_and_fetch_draft(db):
    draft = {
        "id": "d-1", "workspace_id": "ws_1", "platform": "linkedin",
        "headline": "Hook", "body": "Body", "cta": "LEARN_MORE",
        "image_path": "drafts/d-1.png", "rationale": "r",
        "strategist_trace": {"step": "x"}, "source": "generate",
        "source_angle_id": "a1", "tier": "A", "parent_draft_id": None,
        "status": "draft",
    }
    db.insert_draft(draft)
    fetched = db.get_draft("d-1")
    assert fetched["headline"] == "Hook"
    assert fetched["tier"] == "A"


def test_list_drafts_filters_by_workspace(db):
    for i in range(3):
        db.insert_draft({
            "id": f"d-{i}", "workspace_id": "ws_1", "platform": "linkedin",
            "headline": f"H{i}", "body": "b", "cta": "LEARN_MORE",
            "image_path": "", "rationale": "", "strategist_trace": {},
            "source": "generate", "source_angle_id": "a", "tier": "A",
            "parent_draft_id": None, "status": "draft",
        })
    drafts = db.list_drafts(workspace_id="ws_1")
    assert len(drafts) == 3


def test_mark_pushed(db):
    db.insert_draft({
        "id": "d-1", "workspace_id": "ws_1", "platform": "linkedin",
        "headline": "H", "body": "b", "cta": "LEARN_MORE", "image_path": "",
        "rationale": "", "strategist_trace": {}, "source": "generate",
        "source_angle_id": "a", "tier": "A", "parent_draft_id": None, "status": "draft",
    })
    db.mark_pushed("d-1", external_urn="urn:li:sponsoredCreative:1", external_url="https://...")
    assert db.get_draft("d-1")["status"] == "pushed"
