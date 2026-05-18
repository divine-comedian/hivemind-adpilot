"""Workspace endpoints.

Onboarding: just POST a website_url. Hivemind creates the project and runs
enrichment (scrape → AI extract → social → intel side-effects) asynchronously.
The poller watches GET /api/v1/projects/:id until enrichment_status is terminal.

Ad-platform credentials are deferred — collected later via PATCH /workspace/credentials
when the user first tries to push.
"""

import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from server.deps import hivemind, workspace_store, poller, drafts_db
from server.demo import ensure_demo_data
from server.models import CredentialsIn, OnboardIn, ProjectInfoPatch, VoicePatch
from server.platforms import linkedin as li
from server.platforms import facebook as fb


router = APIRouter()


def _project_data(payload: dict) -> dict:
    return payload.get("data", payload)


def _project_id(payload: dict) -> str | None:
    data = _project_data(payload)
    return data.get("id") or data.get("project_id") or payload.get("project_id")


def _project_info(data: dict, website_url: str) -> dict:
    return {
        "project_name": data.get("project_name") or data.get("project_title") or website_url,
        "description": data.get("description") or "",
        "geographics": data.get("geographics") or [],
    }


@router.post("/workspace", status_code=201)
async def create_workspace(payload: OnboardIn):
    hm = hivemind()
    proj = hm.create_project(website_url=str(payload.website_url))
    project_id = _project_id(proj)
    if not project_id:
        raise HTTPException(502, f"Hivemind create_project did not return id: {proj}")

    project_data = _project_data(proj)
    try:
        project_data = _project_data(hm.get_project(project_id))
    except Exception:
        pass
    enrichment_status = project_data.get("enrichment_status", "enriching")

    state = {
        "workspace_id": f"ws_{uuid.uuid4().hex[:8]}",
        "hivemind": {
            "project_id": project_id,
            "website_url": str(payload.website_url),
            "enrichment_status": enrichment_status,
        },
        "project": _project_info(project_data, str(payload.website_url)),
        "business": {
            "voice_notes": "",
            "focus_notes": "",
        },
        "platforms": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    workspace_store().save(state)

    if enrichment_status != "ready":
        poller().track(project_id)

    return state


@router.get("/workspace/me")
def get_workspace():
    ensure_demo_data(workspace_store(), drafts_db())
    return workspace_store().load()


@router.patch("/workspace/project")
def patch_project(body: ProjectInfoPatch):
    state = workspace_store().load()
    if not state:
        raise HTTPException(404, "no workspace")

    project_id = state["hivemind"]["project_id"]
    try:
        resp = hivemind().update_project(
            project_id,
            project_name=body.project_name,
            description=body.description,
            geographics=body.geographics,
        )
        data = _project_data(resp)
    except Exception as exc:
        raise HTTPException(502, f"Hivemind project update failed: {exc}") from exc

    state["project"] = {
        "project_name": data.get("project_name") or body.project_name,
        "description": data.get("description") if data.get("description") is not None else body.description,
        "geographics": data.get("geographics") if data.get("geographics") is not None else body.geographics,
    }
    workspace_store().save(state)
    return state


@router.post("/workspace/project/approve")
def approve_project():
    state = workspace_store().load()
    if not state:
        raise HTTPException(404, "no workspace")
    state["project_approved_at"] = datetime.now(timezone.utc).isoformat()
    workspace_store().save(state)
    return state


@router.patch("/workspace")
def patch_workspace(body: VoicePatch):
    state = workspace_store().load()
    if not state:
        raise HTTPException(404, "no workspace")
    state["business"]["voice_notes"] = body.voice_notes
    state["business"]["focus_notes"] = body.focus_notes
    workspace_store().save(state)
    return state


@router.patch("/workspace/credentials")
def patch_credentials(payload: CredentialsIn):
    state = workspace_store().load()
    if not state:
        raise HTTPException(404, "no workspace")
    platforms = state.setdefault("platforms", {})
    tokens_path = workspace_store().path.parent / ".tokens.env"
    token_lines: list[str] = []

    if payload.linkedin:
        ok, msg = li.validate_token(payload.linkedin.access_token)
        if not ok:
            raise HTTPException(400, f"LinkedIn token invalid: {msg}")
        platforms["linkedin"] = {
            "account_id": payload.linkedin.account_id,
            "org_urn": payload.linkedin.org_urn,
        }
        os.environ["LINKEDIN_ACCESS_TOKEN"] = payload.linkedin.access_token
        token_lines.append(f"LINKEDIN_ACCESS_TOKEN={payload.linkedin.access_token}")

    if payload.facebook:
        ok, msg = fb.validate_token(payload.facebook.access_token)
        if not ok:
            raise HTTPException(400, f"Facebook token invalid: {msg}")
        platforms["facebook"] = {
            "account_id": payload.facebook.account_id,
            "page_id": payload.facebook.page_id,
        }
        os.environ["FACEBOOK_ACCESS_TOKEN"] = payload.facebook.access_token
        os.environ["FACEBOOK_PAGE_ID"] = payload.facebook.page_id
        token_lines.append(f"FACEBOOK_ACCESS_TOKEN={payload.facebook.access_token}")
        token_lines.append(f"FACEBOOK_PAGE_ID={payload.facebook.page_id}")

    if token_lines:
        existing = tokens_path.read_text().splitlines() if tokens_path.exists() else []
        keep_keys = {line.split("=", 1)[0] for line in token_lines}
        merged = [ln for ln in existing if ln and ln.split("=", 1)[0] not in keep_keys] + token_lines
        tokens_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = tokens_path.with_suffix(".tmp")
        tmp.write_text("\n".join(merged) + "\n")
        tmp.replace(tokens_path)

    workspace_store().save(state)
    return state
