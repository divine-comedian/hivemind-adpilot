"""Workspace onboarding endpoint.

POST /workspace returns 201 immediately after creating the Hivemind project
and persisting state. Intelligence reports are kicked off in a background task
so the user never waits on them.
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from server.deps import hivemind, workspace_store, poller
from server.models import OnboardIn
from server.platforms import linkedin as li
from server.platforms import facebook as fb


router = APIRouter()


@router.post("/workspace", status_code=201)
async def create_workspace(payload: OnboardIn):
    # 1. Validate platform tokens fast
    ok_li, msg_li = li.validate_token(payload.linkedin.access_token)
    if not ok_li:
        raise HTTPException(400, f"LinkedIn token invalid: {msg_li}")
    ok_fb, msg_fb = fb.validate_token(payload.facebook.access_token)
    if not ok_fb:
        raise HTTPException(400, f"Facebook token invalid: {msg_fb}")

    # 2. Create Hivemind project
    hm = hivemind()
    proj = hm.create_project(
        name=payload.business.name,
        description=payload.business.description,
        website_url=str(payload.business.website),
        audiences=payload.business.audiences,
        geographies=payload.business.geographies,
        stage=payload.business.stage,
    )
    project_id = proj.get("id") or proj.get("data", {}).get("id")
    if not project_id:
        raise HTTPException(502, f"Hivemind create_project did not return id: {proj}")

    # 3. Persist tokens to disk (gitignored)
    tokens_path = workspace_store().path.parent / ".tokens.env"
    tokens_path.write_text(
        f"LINKEDIN_TOKEN={payload.linkedin.access_token}\n"
        f"FACEBOOK_TOKEN={payload.facebook.access_token}\n"
    )
    os.environ["LINKEDIN_TOKEN"] = payload.linkedin.access_token
    os.environ["FACEBOOK_TOKEN"] = payload.facebook.access_token

    state = {
        "workspace_id": f"ws_{uuid.uuid4().hex[:8]}",
        "business": {
            "name": payload.business.name,
            "website": str(payload.business.website),
            "description": payload.business.description,
            "audiences": payload.business.audiences,
            "geographies": payload.business.geographies,
            "stage": payload.business.stage,
            "voice_notes": payload.brand.voice_notes,
            "focus_notes": "",
        },
        "brand": payload.brand.model_dump(),
        "hivemind": {"project_id": project_id, "reports": {}},
        "platforms": {
            "linkedin": {
                "account_id": payload.linkedin.account_id,
                "org_urn": payload.linkedin.org_urn,
                "token_ref": "LINKEDIN_TOKEN",
            },
            "facebook": {
                "account_id": payload.facebook.account_id,
                "page_id": payload.facebook.page_id,
                "token_ref": "FACEBOOK_TOKEN",
            },
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    workspace_store().save(state)

    # 4. Kick off intelligence reports in background after the response is sent
    # Schedule report kickoff on the running event loop so the poller's
    # asyncio.create_task in track() actually has a loop available.
    asyncio.create_task(_kick_off_reports_async(project_id, payload.business.description, payload.business.audiences))

    return state


@router.get("/workspace/me")
def get_workspace():
    return workspace_store().load()


from pydantic import BaseModel as _PydBaseModel


class FocusPatch(_PydBaseModel):
    focus_notes: str


@router.patch("/workspace")
def patch_workspace(body: FocusPatch):
    state = workspace_store().load()
    if not state:
        raise HTTPException(404, "no workspace")
    state["business"]["focus_notes"] = body.focus_notes
    workspace_store().save(state)
    return state


async def _kick_off_reports_async(project_id: str, description: str, audiences: list[str]) -> None:
    """Runs on the main event loop after the HTTP response is sent. Never blocks the client."""
    hm = hivemind()
    p = poller()
    for report_type in ("competitive_intelligence", "attention_landscape"):
        try:
            resp = hm.intelligence_generate(
                report_type=report_type,
                project_id=project_id,
                description=description,
                audiences=audiences,
            )
            job_id = resp.get("data", {}).get("job_id")
            if job_id:
                workspace_store().update_report_status(report_type, {
                    "job_id": job_id,
                    "status": "queued",
                })
                p.track(report_type, job_id)
        except Exception as exc:
            workspace_store().update_report_status(report_type, {
                "job_id": None, "status": "failed", "error": str(exc),
            })
