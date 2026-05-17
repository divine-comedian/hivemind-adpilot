import httpx
import pytest
import respx
from server.hivemind.client import HivemindClient


@pytest.fixture
def client():
    return HivemindClient(api_key="hm_k_test", base_url="https://hm.test")


@respx.mock
def test_create_project_requires_url_or_description(client):
    with pytest.raises(ValueError):
        client.create_project()


@respx.mock
def test_create_project_posts_correct_payload(client):
    route = respx.post("https://hm.test/api/v1/projects").mock(
        return_value=httpx.Response(202, json={"project_id": "proj-123", "enrichment_status": "enriching"})
    )
    result = client.create_project(
        website_url="https://demo.test",
        project_name="Demo",
        project_type=["SaaS"],
        audiences=["sales-leaders"],
        geographics=["US"],
        stage="growth",
    )
    assert route.called
    body = route.calls[0].request.read()
    assert b'"website_url":"https://demo.test"' in body
    assert b'"geographics":["US"]' in body
    assert b'"project_type":["SaaS"]' in body
    assert b'"stage":"growth"' in body
    assert result["project_id"] == "proj-123"

    headers = route.calls[0].request.headers
    assert headers["x-api-key"] == "hm_k_test"
    assert "authorization" not in headers


@respx.mock
def test_get_project(client):
    respx.get("https://hm.test/api/v1/projects/proj-123").mock(
        return_value=httpx.Response(200, json={"data": {"project_id": "proj-123", "enrichment_status": "ready"}})
    )
    result = client.get_project("proj-123")
    assert result["data"]["enrichment_status"] == "ready"


@respx.mock
def test_update_project_patches_allowed_fields(client):
    route = respx.patch("https://hm.test/api/v1/projects/proj-123").mock(
        return_value=httpx.Response(200, json={"data": {"id": "proj-123", "project_name": "Demo"}})
    )
    result = client.update_project(
        "proj-123",
        project_name="Demo",
        description="Updated",
        geographics=["CA"],
    )
    assert route.called
    body = route.calls[0].request.read()
    assert b'"project_name":"Demo"' in body
    assert b'"description":"Updated"' in body
    assert b'"geographics":["CA"]' in body
    assert result["data"]["project_name"] == "Demo"


@respx.mock
def test_chat_posts_with_persona_and_text(client):
    route = respx.post("https://hm.test/api/v1/chat").mock(
        return_value=httpx.Response(200, json={
            "status": "success",
            "data": {"response": "hi", "persona": {"id": "genius-strategist"}},
        })
    )
    result = client.chat(
        text="Diagnose gaps",
        persona="genius-strategist",
        project_id="proj-123",
    )
    assert route.called
    body = route.calls[0].request.read()
    assert b'"text":"Diagnose gaps"' in body
    assert b'"persona":"genius-strategist"' in body
    assert b'"projectId":"proj-123"' in body
    assert result["data"]["response"] == "hi"


@respx.mock
def test_chat_starts_and_appends_conversation(client):
    route = respx.post("https://hm.test/api/v1/chat").mock(
        return_value=httpx.Response(200, json={
            "status": "success",
            "data": {"response": "hi", "conversation_id": "conv-1"},
        })
    )
    client.chat(
        text="Give me ideas",
        persona="ghostwriter",
        project_id="proj-123",
        start_conversation=True,
    )
    start_body = route.calls[0].request.read()
    assert b'"projectId":"proj-123"' in start_body
    assert b'"startConversation":true' in start_body

    client.chat(
        text="Draft copy",
        persona="ghostwriter",
        project_id="proj-123",
        conversation_id="conv-1",
    )
    append_body = route.calls[1].request.read()
    assert b'"conversationId":"conv-1"' in append_body
    assert b'"projectId"' not in append_body


@respx.mock
def test_chat_error_includes_response_body(client):
    respx.post("https://hm.test/api/v1/chat").mock(
        return_value=httpx.Response(400, json={"error": "text_too_long"})
    )
    with pytest.raises(httpx.HTTPStatusError, match="text_too_long"):
        client.chat(text="x", persona="ghostwriter")


@respx.mock
def test_knowledge_search_includes_required_fields(client):
    route = respx.post("https://hm.test/api/knowledge/search").mock(
        return_value=httpx.Response(200, json={"data": {"chunks": [{"title": "Playbook"}]}})
    )
    result = client.knowledge_search(query="narrative health audit", max_results=5, relevance_threshold=0.7)
    assert route.called
    body = route.calls[0].request.read()
    assert b'"relevanceThreshold":0.7' in body
    assert b'"maxResults":5' in body
    assert result["data"]["chunks"][0]["title"] == "Playbook"
