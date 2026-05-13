from fastapi.testclient import TestClient
from server.main import app


def test_health_returns_ok():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_can_import_existing_scripts():
    # The whole point of the sidecar: reuse the existing scripts/ modules unchanged.
    from scripts import config, li_analytics, li_campaign, fb_insights, fb_campaign, generate_image
    assert callable(config.linkedin_headers)
    assert callable(config.facebook_params)
