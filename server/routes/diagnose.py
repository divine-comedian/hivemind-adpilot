"""Diagnose chain endpoint + accept action."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from server.deps import hivemind, workspace_store, drafts_db, WORKSPACE_DIR
from server.hivemind.diagnose_chain import DiagnoseChain
from server.routes.analytics import get_analytics


router = APIRouter()


@router.get("/diagnose")
async def diagnose_stream(request: Request):
    state = workspace_store().load()
    if not state:
        raise HTTPException(404, "no workspace")
    tier = "B" if state.get("hivemind", {}).get("enrichment_status") == "ready" else "A"
    voice_notes = state["business"].get("voice_notes", "")
    perf = get_analytics(window="30d")
    rows = [r for r in perf["rows"] if not r.get("error")]
    chain = DiagnoseChain(hivemind=hivemind())
    queue: asyncio.Queue = asyncio.Queue()

    def on_step(step: str, status: str, payload: dict | None = None):
        queue.put_nowait({"event": "chain_step", "data": {"step": step, "status": status, "payload": payload or {}}})

    async def run_chain():
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: chain.diagnose(
                    project_id=state["hivemind"]["project_id"],
                    tier=tier,
                    performance_data=rows,
                    active_creative_copy=[],
                    platforms=["linkedin", "facebook"],
                    voice_notes=voice_notes,
                    on_step=on_step,
                ),
            )

            # Persist replacement drafts immediately so accept-all is one click
            from scripts import generate_image as gi
            for d in result["replacement_drafts"]:
                draft_id = f"d_{uuid.uuid4().hex[:8]}"
                image_path = WORKSPACE_DIR / "drafts" / f"{draft_id}.png"
                image_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    gi.generate_image(
                        style_id=1,
                        headline=d["headline"],
                        logo_type="mark",
                        output_path=str(image_path),
                        ad_format="feed",
                    )
                    img = str(image_path)
                except (Exception, SystemExit):
                    img = ""
                drafts_db().insert_draft({
                    "id": draft_id,
                    "workspace_id": state["workspace_id"],
                    "platform": d["platform"],
                    "headline": d["headline"],
                    "body": d["body"],
                    "cta": d["cta"],
                    "image_path": img,
                    "rationale": d.get("rationale", ""),
                    "strategist_trace": {"replacement_of": d.get("angle_id")},
                    "source": "diagnose",
                    "source_angle_id": d.get("angle_id"),
                    "tier": result["tier"],
                    "parent_draft_id": None,
                    "status": "draft",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                d["draft_id"] = draft_id

            diag_id = f"diag_{uuid.uuid4().hex[:8]}"
            drafts_db().insert_diagnosis({
                "id": diag_id,
                "workspace_id": state["workspace_id"],
                "performance_snapshot": rows,
                "strategist_trace": result,
                "summary": result["summary"],
                "killed_ad_ids": [],
                "accepted_replacement_ids": [],
            })
            queue.put_nowait({
                "event": "result",
                "data": {
                    "diagnose_id": diag_id,
                    "summary": result["summary"],
                    "kill_recommendations": result["kill_recommendations"],
                    "replacement_drafts": result["replacement_drafts"],
                    "tier": result["tier"],
                },
            })
        except Exception as exc:
            queue.put_nowait({"event": "error", "data": {"error": str(exc)}})
        finally:
            queue.put_nowait(None)

    asyncio.create_task(run_chain())

    async def event_gen():
        while True:
            if await request.is_disconnected():
                break
            ev = await queue.get()
            if ev is None:
                break
            yield {"event": ev["event"], "data": json.dumps(ev["data"], default=str)}

    return EventSourceResponse(event_gen())


class AcceptIn(BaseModel):
    action: str  # kill | replace
    target_id: str
    platform: str | None = None  # linkedin | facebook (required for kill)
    replacement_draft_id: str | None = None


@router.post("/diagnose/accept")
def accept(body: AcceptIn):
    state = workspace_store().load()
    if not state:
        raise HTTPException(404, "no workspace")

    if body.action == "kill":
        if not body.platform:
            raise HTTPException(400, "platform required for kill action")
        if body.platform == "linkedin":
            li = state.get("platforms", {}).get("linkedin")
            if not li:
                raise HTTPException(412, "LinkedIn credentials not connected")
            from scripts.li_campaign import update_creative_status
            update_creative_status(account_id=li["account_id"], creative_id=body.target_id, status="PAUSED")
        elif body.platform == "facebook":
            from scripts.fb_campaign import update_ad_status
            update_ad_status(ad_id=body.target_id, status="PAUSED")
        else:
            raise HTTPException(400, "platform must be linkedin or facebook")
        return {"status": "paused", "target": body.target_id, "platform": body.platform}

    if body.action == "replace":
        # Replacement drafts are already in DB from the diagnose run
        return {"status": "accepted", "draft_id": body.replacement_draft_id}

    raise HTTPException(400, "unknown action")
