"""Demo-mode fixtures and helpers."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any


def demo_mode() -> bool:
    return os.environ.get("ADPILOT_DEMO_MODE", "").lower() in {"1", "true", "yes", "on"}


def demo_workspace() -> dict[str, Any]:
    return {
        "workspace_id": "ws_demo",
        "hivemind": {
            "project_id": os.environ.get("ADPILOT_DEMO_PROJECT_ID", "demo-project"),
            "website_url": os.environ.get("ADPILOT_DEMO_WEBSITE_URL", "https://aurevon.ca"),
            "enrichment_status": "ready",
        },
        "project": {
            "project_name": os.environ.get("ADPILOT_DEMO_PROJECT_NAME", "Aurevon Intelligence"),
            "description": (
                "Fixed-price competitive intelligence reports for local businesses that need "
                "fast clarity before spending more on marketing."
            ),
            "geographics": ["Canada", "United States"],
        },
        "business": {
            "voice_notes": "Confident, practical, and specific. Avoid hype and fear-based framing.",
            "focus_notes": "Emphasize the fixed-price report and fast path to better local decisions.",
        },
        "platforms": {},
        "project_approved_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "demo": True,
    }


def demo_drafts(workspace_id: str = "ws_demo") -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    base = {
        "workspace_id": workspace_id,
        "image_path": "",
        "strategist_trace": {"mode": "demo_seed"},
        "source": "demo",
        "source_angle_id": "angle_demo",
        "tier": "B",
        "parent_draft_id": None,
    }
    return [
        {
            **base,
            "id": "d_demo_fb_1",
            "platform": "facebook",
            "headline": "See The Local Moves You Miss",
            "body": "A fixed-price report shows where competitors are winning attention before you spend more.",
            "cta": "LEARN_MORE",
            "rationale": "Frames the report as a practical shortcut to local clarity.",
            "status": "pushed",
            "created_at": (now - timedelta(days=10)).isoformat(),
        },
        {
            **base,
            "id": "d_demo_li_1",
            "platform": "linkedin",
            "headline": "Competitive Clarity Before Campaign Spend",
            "body": "Know the market gaps, offers, and messages that matter before increasing your budget.",
            "cta": "LEARN_MORE",
            "rationale": "Connects the offer to lower-risk planning for operators.",
            "status": "pushed",
            "created_at": (now - timedelta(days=9)).isoformat(),
        },
        {
            **base,
            "id": "d_demo_fb_2",
            "platform": "facebook",
            "headline": "A $50 Map Of Your Market",
            "body": "Find the competitors, keywords, and positioning gaps that shape local demand.",
            "cta": "SIGN_UP",
            "rationale": "Makes the fixed price explicit and action-oriented.",
            "status": "draft",
            "created_at": (now - timedelta(days=1)).isoformat(),
        },
    ]


def demo_analytics_rows() -> list[dict[str, Any]]:
    return [
        {
            "platform": "facebook",
            "ad_id": "1009001",
            "ad_name": "See The Local Moves You Miss",
            "impressions": 18420,
            "clicks": 392,
            "spend": 486.25,
            "ctr": 0.0213,
            "cpm": 26.40,
            "conversions": 34,
            "status": "ACTIVE",
        },
        {
            "platform": "linkedin",
            "ad_id": "urn:li:sponsoredCreative:99001",
            "ad_name": "Competitive Clarity Before Campaign Spend",
            "impressions": 9120,
            "clicks": 82,
            "spend": 612.80,
            "ctr": 0.0090,
            "cpm": 67.19,
            "conversions": 11,
            "status": "ACTIVE",
        },
        {
            "platform": "facebook",
            "ad_id": "1009002",
            "ad_name": "Stop Guessing What Competitors Know",
            "impressions": 12600,
            "clicks": 61,
            "spend": 318.40,
            "ctr": 0.0048,
            "cpm": 25.27,
            "conversions": 3,
            "status": "ACTIVE",
        },
        {
            "platform": "linkedin",
            "ad_id": "urn:li:sponsoredCreative:99002",
            "ad_name": "Local Signals For Better Budget Calls",
            "impressions": 6540,
            "clicks": 97,
            "spend": 402.10,
            "ctr": 0.0148,
            "cpm": 61.48,
            "conversions": 14,
            "status": "ACTIVE",
        },
    ]


def demo_diagnosis_result() -> dict[str, Any]:
    return {
        "summary": (
            "The account has one clear underperformer: the competitor-fear framing is getting reach, "
            "but not intent. The stronger pattern is practical clarity before budget decisions: ads that "
            "name the fixed-price report and the specific market questions it answers are earning better "
            "click-through and conversion density.\n\n"
            "The next move is to pause the lowest-intent fear-led creative and replace it with proof-led "
            "copy that makes the $50 report feel like a small, rational first step before larger spend."
        ),
        "kill_recommendations": [
            {
                "target_id": "1009002",
                "platform": "facebook",
                "reasoning": "Low CTR with meaningful spend suggests the fear-led competitor hook is not creating qualified intent.",
                "framework_cited": "Narrative Health Audit",
            }
        ],
        "replacement_drafts": [
            {
                "platform": "facebook",
                "headline": "Know Before You Spend More",
                "body": "A $50 report shows the local gaps, competitors, and messages worth acting on.",
                "cta": "LEARN_MORE",
                "rationale": "Replaces fear with a practical decision-making promise.",
                "angle_id": "demo_replacement_1",
            },
            {
                "platform": "linkedin",
                "headline": "Market Clarity For The Next Budget Call",
                "body": "Use a fixed-price report to see where local competitors are winning attention.",
                "cta": "LEARN_MORE",
                "rationale": "Gives operators a concrete reason to use the report before approving spend.",
                "angle_id": "demo_replacement_2",
            },
        ],
        "tier": "B",
    }


def analytics_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [r for r in rows if "error" not in r]
    return {
        "total_spend": round(sum(r["spend"] for r in valid), 2),
        "total_impressions": sum(r["impressions"] for r in valid),
        "total_clicks": sum(r["clicks"] for r in valid),
        "total_conversions": sum(r["conversions"] for r in valid),
        "avg_ctr": round(sum(r["ctr"] for r in valid) / len(valid), 4) if valid else 0,
        "avg_cpm": round(sum(r["cpm"] for r in valid) / len(valid), 2) if valid else 0,
    }


def ensure_demo_data(store, db) -> dict[str, Any] | None:
    if not demo_mode():
        return None
    state = store.load()
    if not state:
        state = demo_workspace()
        store.save(state)

    existing = db.list_drafts(workspace_id=state["workspace_id"])
    if not existing:
        for draft in demo_drafts(state["workspace_id"]):
            db.insert_draft(draft)
            if draft["status"] == "pushed":
                urn = "fb:1009001" if draft["platform"] == "facebook" else "urn:li:sponsoredCreative:99001"
                db.mark_pushed(
                    draft["id"],
                    external_urn=urn,
                    external_url=f"https://demo.adpilot.local/{draft['platform']}/{draft['id']}",
                )
    return state
