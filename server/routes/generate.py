"""POST-like /generate as SSE — frontend passes payload as ?payload=<json> query param.

Returns a stream of `chain_step` events and a final `result` event with the drafts.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from sse_starlette.sse import EventSourceResponse

from server.deps import hivemind, workspace_store, drafts_db, WORKSPACE_DIR
from server.hivemind.strategist_chain import StrategistChain


router = APIRouter()


@router.get("/generate")
async def generate_stream(payload: str, request: Request):
    try:
        body = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(400, "payload must be JSON")

    platforms = body.get("platforms", ["linkedin"])
    count = int(body.get("count", 5))
    focus_note = body.get("focus_note", "")

    state = workspace_store().load()
    if not state:
        raise HTTPException(404, "No workspace — onboard first")
    if focus_note:
        state["business"]["focus_notes"] = focus_note
        workspace_store().save(state)

    chain = StrategistChain(hivemind=hivemind())

    queue: asyncio.Queue = asyncio.Queue()

    def on_step(step: str, status: str, payload: dict | None = None):
        queue.put_nowait({"event": "chain_step", "data": {"step": step, "status": status, "payload": payload or {}}})

    async def run_chain():
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: chain.generate(
                    project_id=state["hivemind"]["project_id"],
                    business=state["business"],
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
                except Exception:
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

            queue.put_nowait({"event": "result", "data": {"drafts": drafts_out, "tier": result["tier"]}})
        except Exception as exc:
            queue.put_nowait({"event": "error", "data": {"error": str(exc)}})
        finally:
            queue.put_nowait(None)  # sentinel

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
