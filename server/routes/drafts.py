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


@router.post("/drafts/{draft_id}/push")
def push_draft(draft_id: str, body: PushIn):
    d = drafts_db().get_draft(draft_id)
    if not d:
        raise HTTPException(404)
    state = workspace_store().load()
    li = state["platforms"]["linkedin"]
    fb = state["platforms"]["facebook"]

    click_url = state["business"]["website"]

    # Hackathon fallback: pull default ad container from env if client didn't supply
    campaign_id = body.campaign_id or os.environ.get("LI_DEFAULT_CAMPAIGN_ID", "")
    adset_id = body.adset_id or os.environ.get("FB_DEFAULT_ADSET_ID", "")

    if body.platform == "linkedin":
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
    chain = StrategistChain(hivemind=hivemind())
    result = chain.generate(
        project_id=state["hivemind"]["project_id"],
        business=state["business"],
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
