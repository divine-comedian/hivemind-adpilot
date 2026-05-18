"""Background poller for project enrichment status.

Hivemind enriches a project asynchronously after POST /api/v1/projects:
website scrape → AI extraction → social scrape → intel side-effects → set
enrichment_status to 'ready' (or 'failed'). We poll GET /api/v1/projects/:id
every 60s until terminal, then publish an event.
"""

from __future__ import annotations
import asyncio
import logging

from server.events import bus
from server.hivemind.client import HivemindClient
from server.store.workspace import WorkspaceStore


TERMINAL = {"ready", "failed"}


log = logging.getLogger(__name__)


class EnrichmentPoller:
    def __init__(self, hivemind: HivemindClient, store: WorkspaceStore, interval: float = 60.0):
        self.hm = hivemind
        self.store = store
        self.interval = interval
        self._tasks: dict[str, asyncio.Task] = {}

    def track(self, project_id: str) -> None:
        if project_id in self._tasks and not self._tasks[project_id].done():
            return
        self._tasks[project_id] = asyncio.create_task(self._poll_loop(project_id))

    async def _poll_loop(self, project_id: str) -> None:
        while True:
            try:
                resp = self.hm.get_project(project_id)
                project = resp.get("data", resp)
                status = project.get("enrichment_status", "enriching")
            except Exception as exc:
                log.warning("poller error for %s: %s", project_id, exc)
                await asyncio.sleep(self.interval)
                continue

            self.store.update_enrichment_status(project_id, status)
            self.store.update_project_info(project_id, {
                "project_name": project.get("project_name") or project.get("project_title"),
                "description": project.get("description"),
                "geographics": project.get("geographics"),
                "audiences": project.get("audiences"),
            })

            if status in TERMINAL:
                event_type = "enrichment_ready" if status == "ready" else "enrichment_failed"
                bus.publish({
                    "type": event_type,
                    "project_id": project_id,
                    "status": status,
                })
                return
            await asyncio.sleep(self.interval)

    def shutdown(self) -> None:
        for t in self._tasks.values():
            t.cancel()
