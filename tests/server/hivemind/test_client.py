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


@respx.mock
def test_chat_posts_with_persona(client):
    route = respx.post("https://hm.test/api/v1/chat").mock(
        return_value=httpx.Response(200, json={"reply": "hi", "trace_id": "t-1"})
    )
    result = client.chat(
        persona="Strategist",
        messages=[{"role": "user", "content": "Hello"}],
        project_id="proj-123",
    )
    assert route.called
    assert result["reply"] == "hi"


@respx.mock
def test_knowledge_search_posts_query(client):
    route = respx.post("https://hm.test/api/knowledge/search").mock(
        return_value=httpx.Response(200, json={"results": [{"id": "k-1", "body": "..."}]})
    )
    result = client.knowledge_search(query="narrative health audit", limit=5)
    assert route.called
    assert len(result["results"]) == 1
