from fastapi.testclient import TestClient

from server.main import app
from server.routes import generate
from server.routes.generate import _angle_from_state


def test_angle_from_state_resolves_saved_angle_by_id():
    state = {
        "last_angle_ideas": {
            "angles": [
                {"id": "angle_1", "title": "First"},
                {"id": "angle_2", "title": "Second"},
            ]
        }
    }
    assert _angle_from_state(state, "angle_2") == {"id": "angle_2", "title": "Second"}


def test_angle_from_state_returns_none_for_missing_angle():
    assert _angle_from_state({"last_angle_ideas": {"angles": []}}, "angle_1") is None


def test_create_generation_job_stores_payload():
    generate._generate_jobs.clear()
    client = TestClient(app)

    response = client.post(
        "/generate",
        json={
            "platforms": ["facebook", "linkedin"],
            "angle_id": "angle_1",
            "ads_per_platform": 3,
        },
    )

    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert job_id.startswith("gen_")
    assert generate._get_generation_payload(job_id) == {
        "platforms": ["facebook", "linkedin"],
        "count": 5,
        "focus_note": "",
        "angle_id": "angle_1",
        "ads_per_platform": 3,
    }


def test_generate_events_returns_404_for_missing_job():
    client = TestClient(app)

    response = client.get("/generate/gen_missing/events")

    assert response.status_code == 404
    assert response.json()["detail"] == "Generation job not found or expired"


def test_generate_events_streams_result_from_server_side_job(monkeypatch, tmp_path):
    generate._generate_jobs.clear()
    inserted = []
    state = {
        "workspace_id": "ws_1",
        "hivemind": {
            "project_id": "proj_1",
            "website_url": "https://example.com",
            "enrichment_status": "ready",
        },
        "project": {
            "project_name": "Example",
            "description": "A useful product",
            "geographics": ["US"],
        },
        "business": {"voice_notes": "", "focus_notes": ""},
        "last_angle_ideas": {
            "angles": [{"id": "angle_1", "angle": "Reduce wasted spend"}],
        },
    }

    class FakeStore:
        def load(self):
            return state

        def save(self, data):
            state.update(data)

    class FakeDB:
        def insert_draft(self, draft):
            inserted.append(draft)

    class FakeChain:
        def __init__(self, hivemind):
            pass

        def generate_from_angle(self, *, tier, angle, platforms, ads_per_platform, on_step, **kwargs):
            on_step("ghostwriter", "running", {"angle_id": angle["id"]})
            on_step("ghostwriter", "complete", {"count": 1})
            return {
                "tier": tier,
                "strategist_output": {"selected_angle": angle},
                "drafts": [
                    {
                        "platform": platforms[0],
                        "headline": "Cut waste",
                        "body": "Find the spend that is not working.",
                        "cta": "Learn more",
                        "rationale": "Matches the selected angle.",
                        "angle_id": angle["id"],
                    }
                ],
            }

    monkeypatch.setattr(generate, "workspace_store", lambda: FakeStore())
    monkeypatch.setattr(generate, "drafts_db", lambda: FakeDB())
    monkeypatch.setattr(generate, "hivemind", lambda: object())
    monkeypatch.setattr(generate, "StrategistChain", FakeChain)
    monkeypatch.setattr(generate, "WORKSPACE_DIR", tmp_path)

    from scripts import generate_image

    monkeypatch.setattr(generate_image, "generate_image", lambda **kwargs: None)

    client = TestClient(app)
    job_response = client.post(
        "/generate",
        json={"platforms": ["linkedin"], "angle_id": "angle_1", "ads_per_platform": 1},
    )
    job_id = job_response.json()["job_id"]

    response = client.get(f"/generate/{job_id}/events")

    assert response.status_code == 200
    assert "event: chain_step" in response.text
    assert "event: result" in response.text
    assert '"drafts"' in response.text
    assert inserted[0]["headline"] == "Cut waste"
    assert generate._get_generation_payload(job_id) is None
