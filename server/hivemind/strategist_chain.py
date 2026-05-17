"""StrategistChain — the generate-mode chain.

Two real calls per generation:
  1. Strategist (persona=genius-strategist) — diagnose gaps + propose N angles.
  2. Ghostwriter (persona=ghostwriter) — one call per (angle, platform).

Hivemind's chat pipeline does its own RAG + intel attachment when projectId is
present, so there's no explicit knowledge_search step here. Tier A vs B is set
by the caller from the project's enrichment_status.
"""

from __future__ import annotations
import json
import os
import re
from typing import Any, Callable

import httpx

from server.hivemind.client import HivemindClient
from server.hivemind.prompts import (
    ad_set_copy_text,
    angle_extraction_text,
    ghostwriter_angle_ideas_text,
    ghostwriter_text,
    refine_ad_copy_text,
    refine_angle_text,
    strategist_generate_text,
)
from server.hivemind.types import BusinessContext, Tier


def _parse_json_reply(response_text: str) -> dict[str, Any]:
    """Tolerant parser: Hivemind may wrap JSON in markdown fences or prose."""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", response_text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def _listify(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _title_from_angle(angle: str) -> str:
    words = re.findall(r"[A-Za-z0-9$%]+", angle)
    title = " ".join(words[:8])
    return title or "Focused ad set angle"


def _normalize_angles(payload: dict[str, Any], count: int) -> list[dict[str, Any]]:
    angles = payload.get("angles") or payload.get("opportunity_angles") or []
    out: list[dict[str, Any]] = []
    for i, item in enumerate(angles[:count], start=1):
        angle = str(item.get("angle") or item.get("idea") or item.get("topic") or "").strip()
        angle_description = str(item.get("angle_description") or item.get("description") or "").strip()
        reasoning = str(item.get("reasoning") or item.get("rationale") or item.get("why") or "").strip()
        title = str(item.get("title") or item.get("headline") or "").strip()
        if not angle and angle_description:
            angle = angle_description
        if not angle:
            continue
        fit_reason = str(item.get("fit_reason") or item.get("why_good_fit") or "").strip()
        if not reasoning:
            parts = _listify(item.get("hivemind_hooks")) + _listify(item.get("project_information")) + _listify(fit_reason)
            reasoning = " ".join(parts)
        out.append({
            "id": str(item.get("id") or f"angle_{i}"),
            "title": title or _title_from_angle(angle),
            "angle": angle,
            "angle_description": angle,
            "hivemind_hooks": _listify(item.get("hivemind_hooks") or item.get("hooks")),
            "project_information": _listify(
                item.get("project_information") or item.get("project_info") or item.get("project_facts")
            ),
            "fit_reason": fit_reason or reasoning,
            "reasoning": reasoning,
        })
    return out


def _extract_angles_with_small_model(raw_response: str, count: int) -> list[dict[str, Any]]:
    """Use a cheap JSON extraction pass when configured; fall back to local parsing."""
    if os.environ.get("OPENAI_API_KEY"):
        try:
            from openai import OpenAI

            client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            resp = client.chat.completions.create(
                model=os.environ.get("ADPILOT_JSON_EXTRACT_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": angle_extraction_text(raw_response=raw_response)}],
                response_format={"type": "json_object"},
                temperature=0,
            )
            text = resp.choices[0].message.content or "{}"
            angles = _normalize_angles(json.loads(text), count)
            if angles:
                return angles
        except Exception:
            pass

    try:
        return _normalize_angles(_parse_json_reply(raw_response), count)
    except Exception:
        return []


class StrategistChain:
    def __init__(self, hivemind: HivemindClient):
        self.hm = hivemind

    def generate(
        self,
        *,
        project_id: str,
        tier: Tier,
        business: BusinessContext,
        current_active_ads: list[dict],
        platforms: list[str],
        count: int,
        on_step: Callable[[str, str, dict], None] | None = None,
    ) -> dict[str, Any]:
        def emit(step: str, status: str, payload: dict | None = None):
            if on_step:
                on_step(step, status, payload or {})

        emit("strategist", "running", {"tier": tier})
        strategist_resp = self.hm.chat(
            text=strategist_generate_text(
                tier=tier,
                business=business,
                current_active_ads=current_active_ads,
                platforms=platforms,
                count=count,
            ),
            persona="genius-strategist",
            project_id=project_id,
        )
        strategist_output = _parse_json_reply(strategist_resp["data"]["response"])
        emit("strategist", "complete", {
            "tier": tier,
            "angles": len(strategist_output.get("opportunity_angles", [])),
        })

        emit("ghostwriter", "running")
        drafts: list[dict] = []
        for angle in strategist_output.get("opportunity_angles", [])[:count]:
            for platform in platforms:
                ghost_resp = self.hm.chat(
                    text=ghostwriter_text(
                        angle=angle,
                        voice_notes=business.get("voice_notes", ""),
                        platform=platform,
                    ),
                    persona="ghostwriter",
                    project_id=project_id,
                )
                drafts.append({
                    **_parse_json_reply(ghost_resp["data"]["response"]),
                    "angle_id": angle["id"],
                    "platform": platform,
                    "framework_cited": angle.get("framework_cited"),
                })
        emit("ghostwriter", "complete", {"count": len(drafts)})

        return {
            "tier": tier,
            "strategist_output": strategist_output,
            "drafts": drafts,
        }

    def suggest_angles(
        self,
        *,
        project_id: str,
        tier: Tier,
        business: BusinessContext,
        count: int = 4,
        on_step: Callable[[str, str, dict], None] | None = None,
    ) -> dict[str, Any]:
        def emit(step: str, status: str, payload: dict | None = None):
            if on_step:
                on_step(step, status, payload or {})

        emit("ghostwriter", "running", {"count": count})
        text = ghostwriter_angle_ideas_text(tier=tier, business=business, count=count)
        try:
            resp = self.hm.chat(
                text=text,
                persona="ghostwriter",
                project_id=project_id,
                start_conversation=True,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 403:
                raise
            resp = self.hm.chat(text=text, persona="ghostwriter", project_id=project_id)

        raw_response = resp["data"]["response"]
        angles = _extract_angles_with_small_model(raw_response, count)
        if len(angles) < count:
            parsed = _parse_json_reply(raw_response)
            angles = _normalize_angles(parsed, count)
        if not angles:
            raise ValueError("Ghostwriter returned no usable ad angles")

        conversation_id = resp.get("data", {}).get("conversation_id")
        emit("ghostwriter", "complete", {"count": len(angles), "conversation_id": conversation_id})
        return {
            "tier": tier,
            "angles": angles[:count],
            "conversation_id": conversation_id,
            "raw_response": raw_response,
        }

    def generate_from_angle(
        self,
        *,
        project_id: str,
        tier: Tier,
        business: BusinessContext,
        angle: dict[str, Any],
        platforms: list[str],
        ads_per_platform: int = 3,
        conversation_id: str | None = None,
        on_step: Callable[[str, str, dict], None] | None = None,
    ) -> dict[str, Any]:
        def emit(step: str, status: str, payload: dict | None = None):
            if on_step:
                on_step(step, status, payload or {})

        emit("ghostwriter", "running", {
            "angle_id": angle.get("id"),
            "platforms": platforms,
            "ads_per_platform": ads_per_platform,
        })

        total = max(1, ads_per_platform)
        text = ad_set_copy_text(
            angle=angle,
            project=business,
            voice_notes=business.get("voice_notes", ""),
            platforms=platforms,
            ads_per_platform=total,
        )
        resp = self.hm.chat(
            text=text,
            persona="ghostwriter",
            project_id=project_id,
        )
        parsed = _parse_json_reply(resp["data"]["response"])
        drafts = []
        for draft in parsed.get("drafts", []):
            platform = draft.get("platform")
            if platform not in platforms:
                continue
            drafts.append({
                **draft,
                "angle_id": angle.get("id"),
                "platform": platform,
                "variant": draft.get("variant") or len([d for d in drafts if d.get("platform") == platform]) + 1,
            })

        emit("ghostwriter", "complete", {"count": len(drafts)})
        return {
            "tier": tier,
            "strategist_output": {
                "selected_angle": angle,
                "source_conversation_id": conversation_id,
                "mode": "ad_set",
            },
            "drafts": drafts,
        }

    def refine_angle(
        self,
        *,
        project_id: str,
        business: BusinessContext,
        angle: dict[str, Any],
        guidance: str,
        conversation_id: str | None,
    ) -> dict[str, Any]:
        text = refine_angle_text(original_angle=angle, guidance=guidance, business=business)
        if conversation_id:
            resp = self.hm.chat(
                text=text,
                persona="ghostwriter",
                project_id=project_id,
                conversation_id=conversation_id,
            )
        else:
            try:
                resp = self.hm.chat(
                    text=text,
                    persona="ghostwriter",
                    project_id=project_id,
                    start_conversation=True,
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 403:
                    raise
                resp = self.hm.chat(text=text, persona="ghostwriter", project_id=project_id)

        raw_response = resp["data"]["response"]
        refined = _extract_angles_with_small_model(raw_response, 1)
        if not refined:
            refined = _normalize_angles(_parse_json_reply(raw_response), 1)
        if not refined:
            raise ValueError("Ghostwriter returned no usable refined angle")

        refined_angle = {**refined[0], "id": angle.get("id") or refined[0]["id"]}
        return {
            "angle": refined_angle,
            "conversation_id": conversation_id or resp.get("data", {}).get("conversation_id"),
        }

    def refine_draft_copy(
        self,
        *,
        project_id: str,
        tier: Tier,
        business: BusinessContext,
        draft: dict[str, Any],
        guidance: str,
    ) -> dict[str, Any]:
        resp = self.hm.chat(
            text=refine_ad_copy_text(draft=draft, guidance=guidance, project=business),
            persona="ghostwriter",
            project_id=project_id,
        )
        refined = _parse_json_reply(resp["data"]["response"])
        return {
            "tier": tier,
            "strategist_output": {
                "mode": "refine_ad_copy",
                "parent_draft_id": draft.get("id"),
                "guidance": guidance,
            },
            "draft": {
                **refined,
                "platform": draft["platform"],
                "angle_id": draft.get("source_angle_id"),
            },
        }
