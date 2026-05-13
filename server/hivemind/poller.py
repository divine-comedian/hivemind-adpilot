"""Background poller for intelligence-report jobs.

Polls each tracked job every 60s. On terminal status, updates workspace state
and publishes an `intelligence_ready` (or `report_failed`) event.
"""

from __future__ import annotations
import asyncio
import logging

from server.events import bus
from server.hivemind.client import HivemindClient
from server.store.workspace import WorkspaceStore


TERMINAL = {"completed", "completed_partial", "completed_healed", "failed"}
SUCCESS = {"completed", "completed_partial", "completed_healed"}


log = logging.getLogger(__name__)


class IntelligencePoller:
    def __init__(self, hivemind: HivemindClient, store: WorkspaceStore, interval: float = 60.0):
        self.hm = hivemind
        self.store = store
        self.interval = interval
        self._tasks: dict[str, asyncio.Task] = {}

    def track(self, report_type: str, job_id: str) -> None:
        if job_id in self._tasks and not self._tasks[job_id].done():
            return
        self._tasks[job_id] = asyncio.create_task(self._poll_loop(report_type, job_id))

    async def _poll_loop(self, report_type: str, job_id: str) -> None:
        while True:
            try:
                resp = self.hm.intelligence_get_job(job_id)
                status = resp.get("data", {}).get("status", "queued")
            except Exception as exc:
                log.warning("poller error for %s: %s", job_id, exc)
                await asyncio.sleep(self.interval)
                continue

            self.store.update_report_status(report_type, {
                "job_id": job_id,
                "status": status,
                "last_synced_at": resp.get("data", {}).get("completed_at"),
            })

            if status in TERMINAL:
                event_type = "intelligence_ready" if status in SUCCESS else "report_failed"
                bus.publish({
                    "type": event_type,
                    "report_type": report_type,
                    "job_id": job_id,
                    "status": status,
                })
                return
            await asyncio.sleep(self.interval)

    def shutdown(self) -> None:
        for t in self._tasks.values():
            t.cancel()
