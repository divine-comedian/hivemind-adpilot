"""User-message builders for the chat() calls.

Hivemind's /api/v1/chat takes a single `text` string and (optionally) a persona slug.
When we force a persona, Hivemind injects that persona's system prompt + does its
own RAG/intel retrieval (using projectId). Our job here is just to:
  1. State the specific task and required output shape.
  2. Pass the structured payload as JSON inside the text.
  3. Note the tier so the persona knows whether to lean on enriched context.
"""

from __future__ import annotations
import json
from typing import Any

from server.hivemind.types import Tier


def _clip_text(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip() + "..."


def _clip_list(value: Any, *, items: int = 4, item_limit: int = 180) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_clip_text(item, item_limit) for item in value[:items] if str(item).strip()]


def _compact_business(business: dict[str, Any]) -> dict[str, Any]:
    return {
        "website_url": business.get("website_url", ""),
        "project_name": _clip_text(business.get("project_name", ""), 140),
        "description": _clip_text(business.get("description", ""), 1200),
        "geographics": _clip_list(business.get("geographics"), items=5, item_limit=80),
        "voice_notes": _clip_text(business.get("voice_notes", ""), 500),
        "focus_notes": _clip_text(business.get("focus_notes", ""), 500),
    }


def _compact_angle(angle: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": angle.get("id", ""),
        "title": _clip_text(angle.get("title", ""), 100),
        "angle": _clip_text(angle.get("angle_description") or angle.get("angle", ""), 900),
        "fit_reason": _clip_text(angle.get("fit_reason") or angle.get("reasoning", ""), 1200),
        "hivemind_hooks": _clip_list(angle.get("hivemind_hooks"), items=4, item_limit=160),
        "project_information": _clip_list(angle.get("project_information"), items=5, item_limit=160),
    }


def strategist_generate_text(
    *,
    tier: Tier,
    business: dict[str, Any],
    current_active_ads: list[dict],
    platforms: list[str],
    count: int,
) -> str:
    payload = {
        "tier": tier,
        "business": _compact_business(business),
        "current_active_ads": current_active_ads,
        "target_platforms": platforms,
        "angle_count": count,
    }
    return (
        "Diagnose creative gaps in this business's paid-ad strategy and propose "
        f"{count} new angles that fill them.\n\n"
        f"Tier: {tier} — "
        + ("project intel/social context is enriched and attached to your context; lead with intelligence-derived gaps."
           if tier == "B"
           else "project intel is still enriching; ground every gap in the business's stated voice/audience and named Myosin frameworks.")
        + "\n\nReturn ONLY a JSON object with this exact shape, no surrounding prose:\n"
        '{\n'
        '  "diagnosed_gaps": ["one short sentence per gap, max 5"],\n'
        '  "opportunity_angles": [\n'
        '    {"id": "a1", "angle": "...", "rationale": "...", "framework_cited": "<Myosin framework name | null>"}\n'
        '  ],\n'
        '  "tier": "A" | "B",\n'
        '  "framework_cited": "<primary framework you leaned on>"\n'
        '}\n\n'
        "Anti-patterns: never propose generic angles ('show value', 'highlight benefits'). "
        "Every angle must be specific. Never cite a framework you don't actually use.\n\n"
        f"Payload:\n{json.dumps(payload, default=str)}"
    )


def ghostwriter_text(*, angle: dict, voice_notes: str, platform: str) -> str:
    payload = {"angle": _compact_angle(angle), "voice_notes": _clip_text(voice_notes, 500), "format": f"{platform}_feed"}
    return (
        f"Draft a single paid-ad creative for {platform}.\n\n"
        "Return ONLY a JSON object with this exact shape:\n"
        '{\n'
        '  "headline": "<= 70 chars",\n'
        '  "body": "<= 150 chars",\n'
        '  "cta": "LEARN_MORE | SIGN_UP | DOWNLOAD | GET_QUOTE | SUBSCRIBE | REGISTER | APPLY",\n'
        '  "image_prompt": "short prompt for an image generator — cinematic, abstract; never describe text or logos",\n'
        '  "rationale": "one sentence on why this copy serves the angle"\n'
        '}\n\n'
        "Voice: match voice_notes exactly. If voice_notes is empty, default to confident-but-grounded.\n"
        "linkedin_feed: professional, no exclamation points, no emoji. fb_feed: same, with slightly more curiosity-driven hooks.\n\n"
        f"Payload:\n{json.dumps(payload, default=str)}"
    )


def ghostwriter_angle_ideas_text(*, tier: Tier, business: dict[str, Any], count: int) -> str:
    payload = {"tier": tier, "business": _compact_business(business), "angle_count": count}
    return (
        "You are preparing paid social ad-set concepts for this project. Generate "
        f"{count} distinct ad-set angles the user can choose from before copy is drafted.\n\n"
        f"Tier: {tier} — "
        + ("project intel/social context is enriched and attached; use it to make the angles specific."
           if tier == "B"
           else "project intel is still enriching; use the supplied project profile and Hivemind knowledge layer.")
        + "\n\nEach angle should include a concise title, a two-sentence prose description of the angle, "
        "and a three-to-four sentence prose explanation of why it fits. The why-it-fits prose must explain "
        "the Hivemind hooks/frameworks being used, how the angle leverages project information, "
        "and why Ghostwriter thinks this is a good fit."
        + "\n\nReturn ONLY a JSON object with this exact shape, no markdown and no prose:\n"
        '{\n'
        '  "angles": [\n'
        '    {\n'
        '      "id": "angle_1",\n'
        '      "title": "5-8 word ad-set angle title",\n'
        '      "angle": "2 sentences of prose describing the angle in more detail.",\n'
        '      "fit_reason": "3-4 sentences explaining Hivemind hooks used, project information leveraged, and why this fits.",\n'
        '      "reasoning": "same as fit_reason"\n'
        '    }\n'
        '  ]\n'
        '}\n\n'
        "Rules: title must be 5-8 words. Each angle must be concrete enough to become an ad set. "
        "Avoid generic benefit statements. Name knowledge-file hooks or frameworks only when you are actually using them. "
        "Project information must come from the project context, not generic category assumptions.\n\n"
        f"Payload:\n{json.dumps(payload, default=str)}"
    )


def angle_extraction_text(*, raw_response: str) -> str:
    return (
        "Extract exactly the usable ad angles from this Ghostwriter response.\n\n"
        "Return ONLY JSON with this exact shape:\n"
        '{\n'
        '  "angles": [\n'
        '    {\n'
        '      "id": "angle_1",\n'
        '      "title": "5-8 word ad-set angle title",\n'
        '      "angle": "2 sentences of prose describing the angle in more detail.",\n'
        '      "fit_reason": "3-4 sentences explaining Hivemind hooks used, project information leveraged, and why this fits.",\n'
        '      "reasoning": "same as fit_reason"\n'
        '    }\n'
        '  ]\n'
        '}\n\n'
        "Do not invent angles that are not present. Normalize field names like rationale/why into fit_reason or reasoning.\n\n"
        f"Ghostwriter response:\n{raw_response}"
    )


def refine_angle_text(*, original_angle: dict[str, Any], guidance: str, business: dict[str, Any]) -> str:
    payload = {
        "original_angle": _compact_angle(original_angle),
        "user_refinement_guidance": _clip_text(guidance, 900),
        "project": _compact_business(business),
    }
    return (
        "Refine the selected paid social ad-set angle using the user's guidance. "
        "Keep continuity with the current conversation and preserve the same strategic job: "
        "produce a clearer, more useful ad-set angle card before copy is drafted.\n\n"
        "Use the original angle, the user's guidance, Hivemind knowledge hooks/frameworks, "
        "and relevant project information. Do not draft ads yet.\n\n"
        "Return ONLY JSON with this exact shape, no markdown and no prose:\n"
        '{\n'
        '  "angles": [\n'
        '    {\n'
        '      "id": "same id as original_angle.id",\n'
        '      "title": "5-8 word ad-set angle title",\n'
        '      "angle": "2 sentences of prose describing the refined angle in more detail.",\n'
        '      "fit_reason": "3-4 sentences explaining Hivemind hooks used, project information leveraged, and why this fits.",\n'
        '      "reasoning": "same as fit_reason"\n'
        '    }\n'
        '  ]\n'
        '}\n\n'
        "Title must be 5-8 words. The angle field must be exactly 2 prose sentences. "
        "The fit_reason field must be 3-4 prose sentences. Project information must be concrete. "
        "If the user's guidance conflicts with the project, adapt it rather than blindly following it.\n\n"
        f"Payload:\n{json.dumps(payload, default=str)}"
    )


def ad_set_copy_text(
    *,
    angle: dict,
    project: dict[str, Any],
    voice_notes: str,
    platforms: list[str],
    ads_per_platform: int,
) -> str:
    payload = {
        "selected_angle": _compact_angle(angle),
        "project": _compact_business(project),
        "voice_notes": _clip_text(voice_notes, 500),
        "platforms": platforms,
        "ads_per_platform": ads_per_platform,
    }
    return (
        "Draft a complete paid-social ad set from the selected angle.\n\n"
        f"Create exactly {ads_per_platform} unique ads per platform for these platforms: {', '.join(platforms)}. "
        "Each variant must stay inside the same ad-set theme while using a different hook, proof emphasis, "
        "and opening line. Do not rely on prior conversation history; this message contains all required context.\n\n"
        "Return ONLY a JSON object with this exact shape:\n"
        '{\n'
        '  "drafts": [\n'
        '    {\n'
        '      "platform": "facebook | linkedin",\n'
        '      "variant": 1,\n'
        '      "headline": "<= 70 chars",\n'
        '      "body": "<= 150 chars",\n'
        '      "cta": "LEARN_MORE | SIGN_UP | DOWNLOAD | GET_QUOTE | SUBSCRIBE | REGISTER | APPLY",\n'
        '      "image_prompt": "short prompt for an image generator; never describe text or logos",\n'
        '      "rationale": "one sentence on why this variant works for the selected angle"\n'
        '    }\n'
        '  ]\n'
        '}\n\n'
        "linkedin: professional, specific, no emoji. facebook: clear hook with curiosity, no hype. "
        "The output must contain no platforms outside the requested list.\n\n"
        f"Payload:\n{json.dumps(payload, default=str)}"
    )


def refine_ad_copy_text(
    *,
    draft: dict[str, Any],
    guidance: str,
    project: dict[str, Any],
) -> str:
    payload = {
        "current_ad": {
            "platform": draft.get("platform", ""),
            "headline": _clip_text(draft.get("headline", ""), 140),
            "body": _clip_text(draft.get("body", ""), 500),
            "cta": _clip_text(draft.get("cta", ""), 40),
            "rationale": _clip_text(draft.get("rationale", ""), 500),
        },
        "user_refinement_guidance": _clip_text(guidance, 900),
        "project": _compact_business(project),
    }
    return (
        "Refine this single paid-social ad using the user's guidance. "
        "Preserve the platform and strategic intent, but rewrite the ad copy so it is materially improved.\n\n"
        "Return ONLY a JSON object with this exact shape:\n"
        '{\n'
        '  "headline": "<= 70 chars",\n'
        '  "body": "<= 150 chars",\n'
        '  "cta": "LEARN_MORE | SIGN_UP | DOWNLOAD | GET_QUOTE | SUBSCRIBE | REGISTER | APPLY",\n'
        '  "image_prompt": "short prompt for an image generator; never describe text or logos",\n'
        '  "rationale": "one sentence on why the refined copy is stronger"\n'
        '}\n\n'
        "Rules: keep the CTA as a platform-supported CTA. Do not add emoji. Do not return markdown. "
        "If the user's guidance conflicts with the project, adapt it while keeping the ad credible.\n\n"
        f"Payload:\n{json.dumps(payload, default=str)}"
    )


def diagnose_text(
    *,
    tier: Tier,
    performance_data: list[dict],
    active_creative_copy: list[dict],
) -> str:
    payload = {
        "tier": tier,
        "performance_data": performance_data,
        "active_creative_copy": active_creative_copy,
    }
    return (
        "Diagnose live ad performance and recommend kills + replacement angles.\n\n"
        f"Tier: {tier} — "
        + ("intel context is attached." if tier == "B" else "intel is still enriching; rely on knowledge layer.")
        + "\n\nReturn ONLY a JSON object:\n"
        '{\n'
        '  "summary": "2-3 paragraphs of editorial prose — name the underlying pattern, cite a framework",\n'
        '  "kill_recommendations": [\n'
        '    {"target_id": "ad-id", "platform": "linkedin | facebook", "reasoning": "...", "framework_cited": "name | null"}\n'
        '  ],\n'
        '  "replacement_angles": [\n'
        '    {"id": "r1", "angle": "...", "rationale": "...", "framework_cited": "name | null"}\n'
        '  ],\n'
        '  "tier": "A" | "B"\n'
        '}\n\n'
        "The `platform` field on each kill_recommendation MUST match the platform of the corresponding ad in performance_data.\n"
        "Only recommend killing an ad if its CTR is in the bottom decile AND it has at least $5 spend, "
        "OR it has > 1000 impressions and zero clicks. If no ads meet criteria, return empty kill_recommendations.\n\n"
        f"Payload:\n{json.dumps(payload, default=str)}"
    )
