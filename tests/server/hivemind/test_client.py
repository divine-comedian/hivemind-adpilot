import httpx
import pytest
import respx
from server.hivemind.client import HivemindClient


@pytest.fixture
def client():
    return HivemindClient(api_key="test-key", intel_key="intel-key", base_url="https://hm.test")


@respx.mock
def test_create_project_posts_correct_payload(client):
    route = respx.post("https://hm.test/api/v1/projects").mock(
        return_value=httpx.Response(201, json={"id": "proj-123", "name": "Demo"})
    )
    result = client.create_project(
        name="Demo",
        description="A test project",
        website_url="https://demo.test",
        categories=["SaaS"],
        audiences=["sales-leaders"],
        geographies=["US"],
        stage="seed",
    )
    assert route.called
    request_body = route.calls[0].request.read()
    assert b'"name":"Demo"' in request_body
    assert result["id"] == "proj-123"
