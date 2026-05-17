"""DiagnoseChain — given recent perf, return kill recommendations + replacement drafts."""

from __future__ import annotations
from typing import Any, Callable

from server.hivemind.client import HivemindClient
from server.hivemind.prompts import diagnose_text, ghostwriter_text
from server.hivemind.strategist_chain import _parse_json_reply
from server.hivemind.types import Tier


class DiagnoseChain:
    def __init__(self, hivemind: HivemindClient):
        self.hm = hivemind

    def diagnose(
        self,
        *,
        project_id: str,
        tier: Tier,
        performance_data: list[dict],
        active_creative_copy: list[dict],
        platforms: list[str],
        voice_notes: str = "",
        on_step: Callable[[str, str, dict], None] | None = None,
    ) -> dict[str, Any]:
        def emit(step: str, status: str, payload: dict | None = None):
            if on_step:
                on_step(step, status, payload or {})

        emit("strategist", "running", {"tier": tier})
        diag_resp = self.hm.chat(
            text=diagnose_text(
                tier=tier,
                performance_data=performance_data,
                active_creative_copy=active_creative_copy,
            ),
            persona="genius-strategist",
            project_id=project_id,
        )
        diag = _parse_json_reply(diag_resp["data"]["response"])
        emit("strategist", "complete", {"tier": tier})

        emit("ghostwriter", "running")
        replacement_drafts: list[dict] = []
        for angle in diag.get("replacement_angles", []):
            for platform in platforms:
                ghost_resp = self.hm.chat(
                    text=ghostwriter_text(angle=angle, voice_notes=voice_notes, platform=platform),
                    persona="ghostwriter",
                    project_id=project_id,
                )
                replacement_drafts.append({
                    **_parse_json_reply(ghost_resp["data"]["response"]),
                    "angle_id": angle["id"],
                    "platform": platform,
                    "framework_cited": angle.get("framework_cited"),
                })
        emit("ghostwriter", "complete", {"count": len(replacement_drafts)})

        return {
            "summary": diag.get("summary", ""),
            "kill_recommendations": diag.get("kill_recommendations", []),
            "replacement_drafts": replacement_drafts,
            "tier": tier,
        }
