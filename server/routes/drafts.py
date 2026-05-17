"""Drafts list / get / patch / push / regenerate."""

import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.deps import hivemind, workspace_store, drafts_db, WORKSPACE_DIR
from server.hivemind.strategist_chain import StrategistChain


router = APIRouter()


class DraftPatch(BaseModel):
    headline: str
    body: str
    cta: str


class PushIn(BaseModel):
    platform: str  # linkedin | facebook
    campaign_id: str | None = None
    adset_id: str | None = None  # facebook needs this


class RefineIn(BaseModel):
    guidance: str


def _business_from_state(state: dict) -> dict:
    project = state.get("project", {})
    return {
        "website_url": state["hivemind"]["website_url"],
        "project_name": project.get("project_name", ""),
        "description": project.get("description", ""),
        "geographics": project.get("geographics", []),
        "voice_notes": state.get("business", {}).get("voice_notes", ""),
        "focus_notes": state.get("business", {}).get("focus_notes", ""),
    }


@router.get("/drafts")
def list_drafts():
    state = workspace_store().load()
    if not state:
        return []
    return drafts_db().list_drafts(workspace_id=state["workspace_id"])


@router.get("/drafts/{draft_id}")
def get_draft(draft_id: str):
    d = drafts_db().get_draft(draft_id)
    if not d:
        raise HTTPException(404)
    return d


@router.patch("/drafts/{draft_id}")
def patch_draft(draft_id: str, body: DraftPatch):
    drafts_db().update_draft_copy(draft_id, body.headline, body.body, body.cta)
    return drafts_db().get_draft(draft_id)


@router.delete("/drafts/{draft_id}")
def delete_draft(draft_id: str):
    d = drafts_db().get_draft(draft_id)
    if not d:
        raise HTTPException(404)
    drafts_db().mark_discarded(draft_id)
    return {"ok": True}


@router.post("/drafts/{draft_id}/push")
def push_draft(draft_id: str, body: PushIn):
    d = drafts_db().get_draft(draft_id)
    if not d:
        raise HTTPException(404)
    state = workspace_store().load()
    platforms_state = state.get("platforms", {})
    click_url = state["hivemind"]["website_url"]

    # Hackathon fallback: pull default ad container from env if client didn't supply
    campaign_id = body.campaign_id or os.environ.get("LI_DEFAULT_CAMPAIGN_ID", "")
    adset_id = body.adset_id or os.environ.get("FB_DEFAULT_ADSET_ID", "")

    if body.platform == "linkedin":
        li = platforms_state.get("linkedin")
        if not li:
            raise HTTPException(412, "LinkedIn credentials not connected — PATCH /workspace/credentials first")
        if not campaign_id:
            raise HTTPException(400, "campaign_id required for LinkedIn push (or set LI_DEFAULT_CAMPAIGN_ID env)")
        from scripts.li_campaign import create_ad as li_create_ad
        result = li_create_ad(
            account_id=li["account_id"],
            campaign_id=campaign_id,
            image_path=d["image_path"],
            headline=d["headline"],
            intro_text=d["body"],
            cta=d["cta"],
            destination_url=click_url,
            status="PAUSED",
        )
        urn = result["creative_id"]
        url = f"https://www.linkedin.com/campaignmanager/accounts/{li['account_id']}/creatives/"
    elif body.platform == "facebook":
        fb = platforms_state.get("facebook")
        if not fb:
            raise HTTPException(412, "Facebook credentials not connected — PATCH /workspace/credentials first")
        if not adset_id:
            raise HTTPException(400, "adset_id required for Facebook push (or set FB_DEFAULT_ADSET_ID env)")
        from scripts.fb_campaign import upload_image as fb_upload, create_ad_creative, create_ad as fb_create_ad
        img = fb_upload(account_id=fb["account_id"], image_path=d["image_path"])
        creative = create_ad_creative(
            account_id=fb["account_id"],
            image_hash=img["image_hash"],
            headline=d["headline"],
            body=d["body"],
            cta=d["cta"],
            destination_url=click_url,
        )
        ad = fb_create_ad(
            account_id=fb["account_id"],
            adset_id=adset_id,
            creative_id=creative["creative_id"],
            name=d["headline"][:40],
            status="PAUSED",
        )
        urn = f"fb:{ad['ad_id']}"
        url = f"https://www.facebook.com/adsmanager/manage/ads?act={fb['account_id']}&selected_ad_ids={ad['ad_id']}"
    else:
        raise HTTPException(400, "platform must be linkedin or facebook")

    drafts_db().mark_pushed(draft_id, external_urn=urn, external_url=url)
    return {"external_urn": urn, "external_url": url}


@router.post("/drafts/{draft_id}/regenerate")
def regenerate_draft(draft_id: str):
    parent = drafts_db().get_draft(draft_id)
    if not parent:
        raise HTTPException(404)
    state = workspace_store().load()
    tier = "B" if state.get("hivemind", {}).get("enrichment_status") == "ready" else "A"
    business = {
        "website_url": state["hivemind"]["website_url"],
        "voice_notes": state["business"].get("voice_notes", ""),
        "focus_notes": state["business"].get("focus_notes", ""),
    }
    chain = StrategistChain(hivemind=hivemind())
    result = chain.generate(
        project_id=state["hivemind"]["project_id"],
        tier=tier,
        business=business,
        current_active_ads=[],
        platforms=[parent["platform"]],
        count=1,
    )
    if not result["drafts"]:
        raise HTTPException(502, "Chain returned no drafts")
    d = result["drafts"][0]

    new_id = f"d_{uuid.uuid4().hex[:8]}"
    from scripts import generate_image as gi
    image_path = WORKSPACE_DIR / "drafts" / f"{new_id}.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        gi.generate_image(style_id=1, headline=d["headline"], logo_type="mark", output_path=str(image_path), ad_format="feed")
        img = str(image_path)
    except (Exception, SystemExit):
        img = ""

    row = {
        "id": new_id,
        "workspace_id": state["workspace_id"],
        "platform": d["platform"],
        "headline": d["headline"],
        "body": d["body"],
        "cta": d["cta"],
        "image_path": img,
        "rationale": d.get("rationale", ""),
        "strategist_trace": result["strategist_output"],
        "source": "regenerate",
        "source_angle_id": d.get("angle_id"),
        "tier": result["tier"],
        "parent_draft_id": draft_id,
        "status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    drafts_db().insert_draft(row)
    drafts_db().mark_superseded(draft_id)
    return row


@router.post("/drafts/{draft_id}/refine")
def refine_draft(draft_id: str, body: RefineIn):
    guidance = body.guidance.strip()
    if not guidance:
        raise HTTPException(400, "guidance is required")

    parent = drafts_db().get_draft(draft_id)
    if not parent:
        raise HTTPException(404)
    if parent["status"] == "pushed":
        raise HTTPException(409, "Published ads cannot be refined")

    state = workspace_store().load()
    if not state:
        raise HTTPException(404, "No workspace — onboard first")

    tier = "B" if state.get("hivemind", {}).get("enrichment_status") == "ready" else "A"
    chain = StrategistChain(hivemind=hivemind())
    result = chain.refine_draft_copy(
        project_id=state["hivemind"]["project_id"],
        tier=tier,
        business=_business_from_state(state),
        draft=parent,
        guidance=guidance,
    )
    d = result["draft"]

    new_id = f"d_{uuid.uuid4().hex[:8]}"
    from scripts import generate_image as gi
    image_path = WORKSPACE_DIR / "drafts" / f"{new_id}.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        gi.generate_image(style_id=1, headline=d["headline"], logo_type="mark", output_path=str(image_path), ad_format="feed")
        img = str(image_path)
    except (Exception, SystemExit):
        img = ""

    row = {
        "id": new_id,
        "workspace_id": state["workspace_id"],
        "platform": parent["platform"],
        "headline": d["headline"],
        "body": d["body"],
        "cta": d["cta"],
        "image_path": img,
        "rationale": d.get("rationale", ""),
        "strategist_trace": result["strategist_output"],
        "source": "refine",
        "source_angle_id": d.get("angle_id"),
        "tier": result["tier"],
        "parent_draft_id": draft_id,
        "status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    drafts_db().insert_draft(row)
    drafts_db().mark_superseded(draft_id)
    return drafts_db().get_draft(new_id)
