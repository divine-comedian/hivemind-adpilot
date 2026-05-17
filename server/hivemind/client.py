"""HivemindClient — public Hivemind API wrapper.

Source of truth: hivemind.myosin.xyz/api-docs (mirrored in hivemind-plugin/skills/hivemind/references/api-reference.md).

Endpoints:
  - POST /api/v1/projects        create; returns 202; enrichment runs async
  - GET  /api/v1/projects/:id    poll until enrichment_status == ready
  - POST /api/v1/chat            text + optional persona + optional projectId
  - POST /api/knowledge/search   kept for future use; not called by the chain

Auth: x-api-key header for all endpoints.
"""

from __future__ import annotations
from typing import Any, Literal
import httpx


PersonaSlug = Literal["ghostwriter", "genius-strategist", "gtm-architect", "general-assistant"]
Stage = Literal["idea", "pre-launch", "launch", "growth", "scale", "n/a"]
EnrichmentStatus = Literal["enriching", "ready", "failed"]


class HivemindClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(timeout=httpx.Timeout(60.0, read=120.0))

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key, "Content-Type": "application/json"}

    def _raise_for_status(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = response.text
            try:
                body = response.json()
                detail = body.get("error") or body.get("message") or body.get("detail") or detail
            except ValueError:
                pass
            raise httpx.HTTPStatusError(
                f"{exc}. Response body: {detail}",
                request=exc.request,
                response=exc.response,
            ) from exc

    # ---- Projects ----

    def create_project(
        self,
        *,
        website_url: str | None = None,
        description: str | None = None,
        project_name: str | None = None,
        project_type: list[str] | None = None,
        stage: Stage | None = None,
        chains: list[str] | None = None,
        audiences: list[str] | None = None,
        channels: list[str] | None = None,
        geographics: list[str] | None = None,
        objectives: list[str] | None = None,
        legal_considerations: str | None = None,
        social_handles: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if not website_url and not description:
            raise ValueError("create_project requires website_url or description")
        body: dict[str, Any] = {}
        if website_url:
            body["website_url"] = website_url
        if description:
            body["description"] = description
        if project_name:
            body["project_name"] = project_name
        if project_type:
            body["project_type"] = project_type
        if stage:
            body["stage"] = stage
        if chains:
            body["chains"] = chains
        if audiences:
            body["audiences"] = audiences
        if channels:
            body["channels"] = channels
        if geographics:
            body["geographics"] = geographics
        if objectives:
            body["objectives"] = objectives
        if legal_considerations:
            body["legal_considerations"] = legal_considerations
        if social_handles:
            body["social_handles"] = social_handles
        r = self._http.post(
            f"{self.base_url}/api/v1/projects",
            json=body,
            headers=self._headers(),
        )
        self._raise_for_status(r)
        return r.json()

    def get_project(self, project_id: str) -> dict[str, Any]:
        r = self._http.get(
            f"{self.base_url}/api/v1/projects/{project_id}",
            headers=self._headers(),
        )
        self._raise_for_status(r)
        return r.json()

    def update_project(self, project_id: str, **fields: Any) -> dict[str, Any]:
        body = {key: value for key, value in fields.items() if value is not None}
        r = self._http.patch(
            f"{self.base_url}/api/v1/projects/{project_id}",
            json=body,
            headers=self._headers(),
        )
        self._raise_for_status(r)
        return r.json()

    # ---- Chat ----

    def chat(
        self,
        *,
        text: str,
        persona: PersonaSlug | None = None,
        project_id: str | None = None,
        start_conversation: bool = False,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"text": text}
        if persona:
            body["persona"] = persona
        if start_conversation and conversation_id:
            raise ValueError("start_conversation and conversation_id are mutually exclusive")
        if conversation_id:
            body["conversationId"] = conversation_id
        elif project_id:
            body["projectId"] = project_id
        if start_conversation:
            body["startConversation"] = True
        r = self._http.post(
            f"{self.base_url}/api/v1/chat",
            json=body,
            headers=self._headers(),
        )
        self._raise_for_status(r)
        return r.json()

    # ---- Knowledge ----

    def knowledge_search(
        self,
        *,
        query: str,
        relevance_threshold: float = 0.6,
        max_results: int = 5,
        persona_id: PersonaSlug | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "query": query,
            "relevanceThreshold": relevance_threshold,
            "maxResults": max_results,
        }
        if persona_id:
            body["personaId"] = persona_id
        if project_id:
            body["projectId"] = project_id
        r = self._http.post(
            f"{self.base_url}/api/knowledge/search",
            json=body,
            headers=self._headers(),
        )
        self._raise_for_status(r)
        return r.json()
