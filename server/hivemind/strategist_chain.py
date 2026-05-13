"""StrategistChain — the generate-mode chain.

Step 1. Intelligence pull (optional, never blocks)
Step 2. Knowledge retrieval
Step 3. Strategist diagnosis (creative gap analysis)
Step 4. Ghostwriter draft per angle
"""

from __future__ import annotations
import json
from typing import Any, Callable

from server.hivemind.client import HivemindClient
from server.hivemind.prompts import STRATEGIST_SYSTEM, GHOSTWRITER_SYSTEM
from server.hivemind.types import BusinessContext, Tier


KNOWLEDGE_QUERY = "narrative health audit framework anti-patterns paid ads ghostwriter"


class StrategistChain:
    def __init__(self, hivemind: HivemindClient):
        self.hm = hivemind

    def generate(
        self,
        *,
        project_id: str,
        business: BusinessContext,
        current_active_ads: list[dict],
        platforms: list[str],
        count: int,
        on_step: Callable[[str, str, dict], None] | None = None,
    ) -> dict[str, Any]:
        """Run the chain. on_step(step_name, status, payload) is called between steps."""
        def emit(step: str, status: str, payload: dict | None = None):
            if on_step:
                on_step(step, status, payload or {})

        # Step 1 — Intelligence (optional)
        emit("intelligence_pull", "running")
        competitive = self.hm.intelligence_get_report(project_id, "competitive_intelligence")
        attention = self.hm.intelligence_get_report(project_id, "attention_landscape")
        intelligence_present = competitive is not None or attention is not None
        emit("intelligence_pull", "complete", {"present": intelligence_present})

        # Step 2 — Knowledge layer
        emit("knowledge_search", "running")
        knowledge = self.hm.knowledge_search(query=KNOWLEDGE_QUERY, limit=5, project_id=project_id)
        emit("knowledge_search", "complete", {"hits": len(knowledge.get("results", []))})

        # Step 3 — Strategist
        emit("strategist_diagnosis", "running")
        strategist_payload = {
            "business_context": business,
            "intelligence_reports": {
                "competitive_intelligence": competitive,
                "attention_landscape": attention,
            } if intelligence_present else None,
            "current_active_ads": current_active_ads,
            "knowledge_excerpts": knowledge.get("results", []),
            "target_platforms": platforms,
            "angle_count": count,
        }
        strategist_resp = self.hm.chat(
            persona="Strategist",
            messages=[
                {"role": "system", "content": STRATEGIST_SYSTEM},
                {"role": "user", "content": json.dumps(strategist_payload, default=str)},
            ],
            project_id=project_id,
        )
        strategist_output = json.loads(strategist_resp["reply"])
        tier: Tier = strategist_output.get("tier", "A")
        emit("strategist_diagnosis", "complete", {
            "tier": tier,
            "angles": len(strategist_output.get("opportunity_angles", [])),
        })

        # Step 4 — Ghostwriter per angle, per platform
        emit("ghostwriter_drafts", "running")
        drafts: list[dict] = []
        for angle in strategist_output.get("opportunity_angles", [])[:count]:
            for platform in platforms:
                ghost_payload = {
                    "angle": angle,
                    "voice_notes": business.get("voice_notes", ""),
                    "format": f"{platform}_feed",
                }
                ghost_resp = self.hm.chat(
                    persona="Ghostwriter",
                    messages=[
                        {"role": "system", "content": GHOSTWRITER_SYSTEM},
                        {"role": "user", "content": json.dumps(ghost_payload)},
                    ],
                    project_id=project_id,
                )
                ghost_output = json.loads(ghost_resp["reply"])
                drafts.append({
                    **ghost_output,
                    "angle_id": angle["id"],
                    "platform": platform,
                    "framework_cited": angle.get("framework_cited"),
                })
        emit("ghostwriter_drafts", "complete", {"count": len(drafts)})

        return {
            "tier": tier,
            "strategist_output": strategist_output,
            "drafts": drafts,
        }
