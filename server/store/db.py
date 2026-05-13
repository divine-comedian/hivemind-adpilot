"""SQLite store for drafts, pushes, and diagnoses."""

from __future__ import annotations
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any
from datetime import datetime, timezone


SCHEMA = """
CREATE TABLE IF NOT EXISTS drafts (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  platform TEXT NOT NULL,
  headline TEXT,
  body TEXT,
  cta TEXT,
  image_path TEXT,
  rationale TEXT,
  strategist_trace TEXT,
  source TEXT,
  source_angle_id TEXT,
  tier TEXT,
  parent_draft_id TEXT,
  status TEXT NOT NULL DEFAULT 'draft'
);

CREATE TABLE IF NOT EXISTS pushes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  draft_id TEXT NOT NULL,
  pushed_at TEXT NOT NULL,
  platform TEXT NOT NULL,
  external_urn TEXT,
  external_url TEXT,
  FOREIGN KEY (draft_id) REFERENCES drafts(id)
);

CREATE TABLE IF NOT EXISTS diagnoses (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  performance_snapshot TEXT,
  strategist_trace TEXT,
  summary TEXT,
  killed_ad_ids TEXT,
  accepted_replacement_ids TEXT
);

CREATE INDEX IF NOT EXISTS idx_drafts_workspace ON drafts(workspace_id);
CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts(status);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DraftsDB:
    def __init__(self, db_path: Path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._conn() as c:
            c.executescript(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        return c

    # ---- drafts ----

    def insert_draft(self, d: dict[str, Any]) -> None:
        with self._lock, self._conn() as c:
            c.execute(
                """INSERT INTO drafts
                (id, workspace_id, created_at, platform, headline, body, cta, image_path,
                 rationale, strategist_trace, source, source_angle_id, tier, parent_draft_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    d["id"], d["workspace_id"], d.get("created_at") or _now(),
                    d["platform"], d.get("headline", ""), d.get("body", ""), d.get("cta", ""),
                    d.get("image_path", ""), d.get("rationale", ""),
                    json.dumps(d.get("strategist_trace", {})),
                    d.get("source", "generate"), d.get("source_angle_id"),
                    d.get("tier", "A"), d.get("parent_draft_id"),
                    d.get("status", "draft"),
                ),
            )

    def get_draft(self, draft_id: str) -> dict[str, Any] | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["strategist_trace"] = json.loads(d["strategist_trace"] or "{}")
        return d

    def list_drafts(self, workspace_id: str) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM drafts WHERE workspace_id = ? ORDER BY created_at DESC",
                (workspace_id,),
            ).fetchall()
        out = []
        for row in rows:
            d = dict(row)
            d["strategist_trace"] = json.loads(d["strategist_trace"] or "{}")
            out.append(d)
        return out

    def update_draft_copy(self, draft_id: str, headline: str, body: str, cta: str) -> None:
        with self._lock, self._conn() as c:
            c.execute(
                "UPDATE drafts SET headline=?, body=?, cta=? WHERE id=?",
                (headline, body, cta, draft_id),
            )

    def mark_pushed(self, draft_id: str, external_urn: str, external_url: str) -> None:
        with self._lock, self._conn() as c:
            c.execute("UPDATE drafts SET status='pushed' WHERE id=?", (draft_id,))
            c.execute(
                "INSERT INTO pushes (draft_id, pushed_at, platform, external_urn, external_url) "
                "SELECT id, ?, platform, ?, ? FROM drafts WHERE id = ?",
                (_now(), external_urn, external_url, draft_id),
            )

    def mark_superseded(self, draft_id: str) -> None:
        with self._lock, self._conn() as c:
            c.execute("UPDATE drafts SET status='superseded' WHERE id=?", (draft_id,))

    # ---- diagnoses ----

    def insert_diagnosis(self, d: dict[str, Any]) -> None:
        with self._lock, self._conn() as c:
            c.execute(
                """INSERT INTO diagnoses
                (id, workspace_id, created_at, performance_snapshot, strategist_trace, summary,
                 killed_ad_ids, accepted_replacement_ids)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    d["id"], d["workspace_id"], d.get("created_at") or _now(),
                    json.dumps(d.get("performance_snapshot", [])),
                    json.dumps(d.get("strategist_trace", {})),
                    d.get("summary", ""),
                    json.dumps(d.get("killed_ad_ids", [])),
                    json.dumps(d.get("accepted_replacement_ids", [])),
                ),
            )
