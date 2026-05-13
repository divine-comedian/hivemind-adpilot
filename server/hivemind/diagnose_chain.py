"""DiagnoseChain — given recent perf, return kill recommendations + replacement drafts."""

from __future__ import annotations
import json
from typing import Any, Callable

from server.hivemind.client import HivemindClient
from server.hivemind.prompts import DIAGNOSE_SYSTEM, GHOSTWRITER_SYSTEM
from server.hivemind.strategist_chain import KNOWLEDGE_QUERY
from server.hivemind.types import Tier


class DiagnoseChain:
    def __init__(self, hivemind: HivemindClient):
        self.hm = hivemind

    def diagnose(
        self,
        *,
        project_id: str,
        performance_data: list[dict],
        active_creative_copy: list[dict],
        platforms: list[str],
        on_step: Callable[[str, str, dict], None] | None = None,
    ) -> dict[str, Any]:
        def emit(step: str, status: str, payload: dict | None = None):
            if on_step:
                on_step(step, status, payload or {})

        emit("intelligence_pull", "running")
        competitive = self.hm.intelligence_get_report(project_id, "competitive_intelligence")
        attention = self.hm.intelligence_get_report(project_id, "attention_landscape")
        intelligence_present = competitive is not None or attention is not None
        emit("intelligence_pull", "complete", {"present": intelligence_present})

        emit("knowledge_search", "running")
        knowledge = self.hm.knowledge_search(query=KNOWLEDGE_QUERY, limit=5, project_id=project_id)
        emit("knowledge_search", "complete", {})

        emit("strategist_diagnosis", "running")
        diagnose_payload = {
            "performance_data": performance_data,
            "active_creative_copy": active_creative_copy,
            "intelligence_reports": {
                "competitive_intelligence": competitive,
                "attention_landscape": attention,
            } if intelligence_present else None,
            "knowledge_excerpts": knowledge.get("results", []),
        }
        diag_resp = self.hm.chat(
            persona="Strategist",
            messages=[
                {"role": "system", "content": DIAGNOSE_SYSTEM},
                {"role": "user", "content": json.dumps(diagnose_payload, default=str)},
            ],
            project_id=project_id,
        )
        diag = json.loads(diag_resp["reply"])
        tier: Tier = diag.get("tier", "A")
        emit("strategist_diagnosis", "complete", {"tier": tier})

        emit("ghostwriter_drafts", "running")
        replacement_drafts: list[dict] = []
        for angle in diag.get("replacement_angles", []):
            for platform in platforms:
                ghost_payload = {"angle": angle, "voice_notes": "", "format": f"{platform}_feed"}
                ghost_resp = self.hm.chat(
                    persona="Ghostwriter",
                    messages=[
                        {"role": "system", "content": GHOSTWRITER_SYSTEM},
                        {"role": "user", "content": json.dumps(ghost_payload)},
                    ],
                    project_id=project_id,
                )
                replacement_drafts.append({
                    **json.loads(ghost_resp["reply"]),
                    "angle_id": angle["id"],
                    "platform": platform,
                    "framework_cited": angle.get("framework_cited"),
                })
        emit("ghostwriter_drafts", "complete", {"count": len(replacement_drafts)})

        return {
            "summary": diag.get("summary", ""),
            "kill_recommendations": diag.get("kill_recommendations", []),
            "replacement_drafts": replacement_drafts,
            "tier": tier,
        }
