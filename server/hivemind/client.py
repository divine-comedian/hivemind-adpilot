"""HivemindClient — wraps the public Hivemind API + Intelligence API.

Day-of verification: the exact /api/v1/chat shape (persona param name) is confirmed
from hivemind.myosin.xyz/api-docs during the first 30 min of the build. Update
the chat() method once verified.
"""

from __future__ import annotations
from typing import Any
import httpx


class HivemindClient:
    def __init__(self, api_key: str, intel_key: str, base_url: str):
        self.api_key = api_key
        self.intel_key = intel_key
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(timeout=httpx.Timeout(60.0, read=120.0))

    def _headers(self, *, intel: bool = False) -> dict[str, str]:
        key = self.intel_key if intel else self.api_key
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    # ---- Projects ----

    def create_project(
        self,
        *,
        name: str,
        description: str,
        website_url: str | None = None,
        categories: list[str] | None = None,
        audiences: list[str] | None = None,
        geographies: list[str] | None = None,
        stage: str | None = None,
    ) -> dict[str, Any]:
        body = {"name": name, "description": description}
        if website_url:
            body["website_url"] = website_url
        if categories:
            body["categories"] = categories
        if audiences:
            body["audiences"] = audiences
        if geographies:
            body["geographies"] = geographies
        if stage:
            body["stage"] = stage
        r = self._http.post(
            f"{self.base_url}/api/v1/projects",
            json=body,
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    # ---- Chat ----

    def chat(
        self,
        *,
        persona: str,
        messages: list[dict[str, str]],
        project_id: str | None = None,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"persona": persona, "messages": messages}
        if project_id:
            body["project_id"] = project_id
        if metadata:
            body["metadata"] = metadata
        r = self._http.post(
            f"{self.base_url}/api/v1/chat",
            json=body,
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    # ---- Knowledge ----

    def knowledge_search(
        self,
        *,
        query: str,
        limit: int = 5,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"query": query, "limit": limit}
        if project_id:
            body["project_id"] = project_id
        r = self._http.post(
            f"{self.base_url}/api/knowledge/search",
            json=body,
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    # ---- Intelligence ----

    REPORT_TYPES = ("competitive_intelligence", "attention_landscape", "ecosystem_dynamics")

    def intelligence_generate(
        self,
        *,
        report_type: str,
        project_id: str,
        description: str,
        website_url: str | None = None,
        categories: list[str] | None = None,
        audiences: list[str] | None = None,
        geographics: list[str] | None = None,
        stage: str | None = None,
        window_days: int = 30,
    ) -> dict[str, Any]:
        assert report_type in self.REPORT_TYPES
        body: dict[str, Any] = {
            "report_type": report_type,
            "project_id": project_id,
            "description": description,
            "window_days": window_days,
        }
        if website_url:
            body["website_url"] = website_url
        if categories:
            body["categories"] = categories
        if audiences:
            body["audiences"] = audiences
        if geographics:
            body["geographics"] = geographics
        if stage:
            body["stage"] = stage
        r = self._http.post(
            f"{self.base_url}/api/intelligence/reports/generate",
            json=body,
            headers=self._headers(intel=True),
        )
        r.raise_for_status()
        return r.json()

    def intelligence_get_job(self, job_id: str) -> dict[str, Any]:
        r = self._http.get(
            f"{self.base_url}/api/intelligence/jobs/{job_id}",
            headers=self._headers(intel=True),
        )
        r.raise_for_status()
        return r.json()

    def intelligence_get_report(self, project_id: str, report_type: str) -> dict[str, Any] | None:
        r = self._http.get(
            f"{self.base_url}/api/intelligence/reports/{project_id}/{report_type}",
            headers=self._headers(intel=True),
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json().get("data")
