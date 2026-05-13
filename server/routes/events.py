"""SSE stream of workspace-level events."""

from sse_starlette.sse import EventSourceResponse
from fastapi import APIRouter
from server.events import bus
import json

router = APIRouter()


@router.get("/workspace/events")
async def events_stream():
    async def gen():
        async for ev in bus.subscribe():
            yield {"event": ev.get("type", "message"), "data": json.dumps(ev)}
    return EventSourceResponse(gen())
