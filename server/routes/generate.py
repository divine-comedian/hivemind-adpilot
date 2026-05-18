"""Draft generation routes.

The browser creates a short-lived generation job with POST /generate, then opens
GET /generate/{job_id}/events for SSE. This keeps the generation payload out of
the EventSource URL.
"""

import asyncio
import json
import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, HTTPException
from sse_starlette.sse import EventSourceResponse

log = logging.getLogger(__name__)

from server.deps import hivemind, workspace_store, drafts_db, WORKSPACE_DIR
from server.hivemind.strategist_chain import StrategistChain
from server.models import DraftIdeaDismissIn, DraftIdeaRefineIn, GenerateJobIn


router = APIRouter()
GENERATE_JOB_TTL = timedelta(minutes=15)
_generate_jobs: dict[str, dict] = {}
_generate_jobs_lock = threading.Lock()


def _prune_generation_jobs(now: datetime | None = None) -> None:
    cutoff = (now or datetime.now(timezone.utc)) - GENERATE_JOB_TTL
    expired = [
        job_id
        for job_id, job in _generate_jobs.items()
        if job["created_at"] < cutoff
    ]
    for job_id in expired:
        _generate_jobs.pop(job_id, None)


def _store_generation_payload(payload: dict) -> str:
    job_id = f"gen_{uuid.uuid4().hex}"
    with _generate_jobs_lock:
        _prune_generation_jobs()
        _generate_jobs[job_id] = {
            "payload": payload,
            "created_at": datetime.now(timezone.utc),
        }
    return job_id


def _get_generation_payload(job_id: str) -> dict | None:
    with _generate_jobs_lock:
        _prune_generation_jobs()
        job = _generate_jobs.get(job_id)
        if not job:
            return None
        return dict(job["payload"])


def _delete_generation_job(job_id: str) -> None:
    with _generate_jobs_lock:
        _generate_jobs.pop(job_id, None)


def _business_from_state(state: dict) -> dict:
    project = state.get("project", {})
    return {
        "website_url": state["hivemind"]["website_url"],
        "project_name": project.get("project_name", ""),
        "description": project.get("description", ""),
        "geographics": project.get("geographics", []),
        "audiences": project.get("audiences", []),
        "voice_notes": state.get("business", {}).get("voice_notes", ""),
        "focus_notes": state.get("business", {}).get("focus_notes", ""),
    }


def _angle_from_state(state: dict, angle_id: str | None) -> dict | None:
    if not angle_id:
        return None
    current = state.get("last_angle_ideas") or {}
    for angle in current.get("angles", []):
        if angle.get("id") == angle_id:
            return angle
    return None


@router.post("/draft-ideas")
def draft_ideas():
    state = workspace_store().load()
    if not state:
        raise HTTPException(404, "No workspace — onboard first")

    tier = "B" if state.get("hivemind", {}).get("enrichment_status") == "ready" else "A"
    chain = StrategistChain(hivemind=hivemind())
    result = chain.suggest_angles(
        project_id=state["hivemind"]["project_id"],
        tier=tier,
        business=_business_from_state(state),
        count=4,
    )
    state["last_angle_ideas"] = {
        "conversation_id": result.get("conversation_id"),
        "angles": result["angles"],
        "tier": result["tier"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    workspace_store().save(state)
    return state["last_angle_ideas"]


@router.post("/draft-ideas/refine")
def refine_draft_idea(body: DraftIdeaRefineIn):
    state = workspace_store().load()
    if not state:
        raise HTTPException(404, "No workspace — onboard first")
    current = state.get("last_angle_ideas")
    if not current:
        raise HTTPException(404, "No angle ideas to refine")

    angle_id = body.angle.get("id")
    angles = current.get("angles", [])
    idx = next((i for i, item in enumerate(angles) if item.get("id") == angle_id), -1)
    if idx < 0:
        raise HTTPException(404, "Angle not found")

    chain = StrategistChain(hivemind=hivemind())
    result = chain.refine_angle(
        project_id=state["hivemind"]["project_id"],
        business=_business_from_state(state),
        angle=body.angle,
        guidance=body.guidance,
        conversation_id=body.conversation_id or current.get("conversation_id"),
    )
    angles[idx] = result["angle"]
    current["angles"] = angles
    current["conversation_id"] = result.get("conversation_id") or current.get("conversation_id")
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    state["last_angle_ideas"] = current
    workspace_store().save(state)
    return current


@router.post("/draft-ideas/dismiss")
def dismiss_draft_idea(body: DraftIdeaDismissIn):
    state = workspace_store().load()
    if not state:
        raise HTTPException(404, "No workspace — onboard first")
    current = state.get("last_angle_ideas")
    if not current:
        raise HTTPException(404, "No angle ideas to dismiss")
    current["angles"] = [angle for angle in current.get("angles", []) if angle.get("id") != body.angle_id]
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    state["last_angle_ideas"] = current
    workspace_store().save(state)
    return current


@router.post("/generate")
def create_generation_job(body: GenerateJobIn):
    payload = body.model_dump(exclude_none=True)
    return {"job_id": _store_generation_payload(payload)}


@router.get("/generate/{job_id}/events")
async def generate_stream(job_id: str, request: Request):
    body = _get_generation_payload(job_id)
    if body is None:
        raise HTTPException(404, "Generation job not found or expired")

    platforms = body.get("platforms", ["linkedin"])
    count = int(body.get("count", 5))
    focus_note = body.get("focus_note", "")
    selected_angle = body.get("angle") or None
    angle_id = body.get("angle_id")
    conversation_id = body.get("conversation_id")

    state = workspace_store().load()
    if not state:
        _delete_generation_job(job_id)
        raise HTTPException(404, "No workspace — onboard first")
    if focus_note:
        state["business"]["focus_notes"] = focus_note
        workspace_store().save(state)
    if not selected_angle and angle_id:
        selected_angle = _angle_from_state(state, angle_id)
        if not selected_angle:
            _delete_generation_job(job_id)
            raise HTTPException(404, "Angle not found")

    tier = "B" if state.get("hivemind", {}).get("enrichment_status") == "ready" else "A"
    business = _business_from_state(state)
    chain = StrategistChain(hivemind=hivemind())

    queue: asyncio.Queue = asyncio.Queue()

    def on_step(step: str, status: str, payload: dict | None = None):
        queue.put_nowait({"event": "chain_step", "data": {"step": step, "status": status, "payload": payload or {}}})

    async def run_chain():
        loop = asyncio.get_running_loop()
        try:
            if selected_angle:
                result = await loop.run_in_executor(
                    None,
                    lambda: chain.generate_from_angle(
                        project_id=state["hivemind"]["project_id"],
                        tier=tier,
                        business=business,
                        angle=selected_angle,
                        platforms=platforms,
                        ads_per_platform=int(body.get("ads_per_platform", 3)),
                        conversation_id=conversation_id,
                        on_step=on_step,
                    ),
                )
            else:
                result = await loop.run_in_executor(
                    None,
                    lambda: chain.generate(
                        project_id=state["hivemind"]["project_id"],
                        tier=tier,
                        business=business,
                        current_active_ads=[],
                        platforms=platforms,
                        count=count,
                        on_step=on_step,
                    ),
                )

            # Persist drafts + generate images
            from scripts import generate_image as gi
            drafts_out = []
            for d in result["drafts"]:
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
                    img_path_str = str(image_path)
                except (Exception, SystemExit):
                    log.exception("image generation failed for draft %s", draft_id)
                    img_path_str = ""

                row = {
                    "id": draft_id,
                    "workspace_id": state["workspace_id"],
                    "platform": d["platform"],
                    "headline": d["headline"],
                    "body": d["body"],
                    "cta": d["cta"],
                    "image_path": img_path_str,
                    "rationale": d.get("rationale", ""),
                    "strategist_trace": result["strategist_output"],
                    "source": "generate",
                    "source_angle_id": d.get("angle_id"),
                    "tier": result["tier"],
                    "parent_draft_id": None,
                    "status": "draft",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                drafts_db().insert_draft(row)
                drafts_out.append(row)

            queue.put_nowait({"event": "result", "data": {
                "drafts": drafts_out,
                "tier": result["tier"],
                "conversation_id": result.get("conversation_id"),
            }})
        except Exception as exc:
            queue.put_nowait({"event": "error", "data": {"error": str(exc)}})
        finally:
            queue.put_nowait(None)  # sentinel

    asyncio.create_task(run_chain())

    async def event_gen():
        try:
            while True:
                if await request.is_disconnected():
                    break
                ev = await queue.get()
                if ev is None:
                    break
                yield {"event": ev["event"], "data": json.dumps(ev["data"], default=str)}
        finally:
            _delete_generation_job(job_id)

    return EventSourceResponse(event_gen())
