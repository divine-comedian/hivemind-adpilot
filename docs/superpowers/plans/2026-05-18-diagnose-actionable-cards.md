# Actionable Diagnose Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reframe the diagnose pipeline so a single strategist call produces (a) a written take, (b) tweak cards per existing ad with pre-filled refine guidance, and (c) new-angle cards with one-click "Generate ad" buttons — eliminating the eager ghostwriter fan-out and eager image generation.

**Architecture:** One Hivemind call to `genius-strategist` with `analytics_rows + current_ad_copy` returns `{summary, tweaks[], new_angles[], kill_recommendations[]}`. The diagnose route stops persisting replacement drafts up-front. The diagnose page renders three orthogonal sections: pause (existing), tweak (new — wires straight into `/drafts/{id}/refine` with prefilled guidance), and new-angle (new — wires into a new `POST /drafts/from-angle` endpoint that fans out ghostwriter for one platform on demand). Refining a published draft no longer 409s; it spawns a sibling draft instead of superseding the live one.

**Tech Stack:** Python 3.12 / FastAPI / pytest; Next.js 15 (App Router) / TypeScript / Tailwind. Existing Hivemind client (`server/hivemind/client.py`) and strategist chain (`server/hivemind/strategist_chain.py`) are reused.

**Out of scope:** Image generation (already on-demand via `/drafts/{id}/regenerate-image` and `AdOperationsCard`), kill-recommendation flow (unchanged — the platform pause action stays), the demo-mode mock for diagnose stays (just updated to new shape).

---

## File map

**Modify (backend):**
- `server/hivemind/prompts.py` — rewrite `diagnose_text(...)` for new schema; add `_compact_active_ad(...)` helper.
- `server/hivemind/diagnose_chain.py` — drop ghostwriter fan-out; single call; new return shape.
- `server/routes/diagnose.py` — drop eager image gen loop; new SSE result payload; reuse `analytics` + `drafts_db` to assemble `current_ad_copy`.
- `server/routes/drafts.py` — (1) relax `/drafts/{id}/refine` to allow refining pushed drafts (spawn sibling, no supersede); (2) add `POST /drafts/from-angle`.
- `server/demo.py` — update `demo_diagnosis_result()` to new shape.

**Modify (frontend):**
- `web/lib/api.ts` — new types (`DiagnoseTweak`, `DiagnoseNewAngle`, updated `DiagnoseResult`); new method `draftFromAngle`.
- `web/app/workspace/diagnose/page.tsx` — full rewrite of result section: summary, pause section (unchanged), tweak cards, new-angle cards.

**Create (frontend):**
- `web/components/TweakCard.tsx` — card UI for one tweak: critique + prefilled guidance textarea + Refine button.
- `web/components/NewAngleCard.tsx` — card UI for one new angle: rationale + per-platform "Generate ad" buttons.

**Modify (tests):**
- `tests/server/hivemind/test_diagnose_chain.py` — assert single Hivemind call + new return shape.
- `tests/server/routes/test_drafts.py` *(create if absent)* — covers (a) refine on pushed draft now succeeds, (b) `POST /drafts/from-angle` persists a draft from an angle.

---

## Phase 1 — Backend: new diagnose contract

### Task 1.1: New `diagnose_text` prompt schema

**Files:**
- Modify: `server/hivemind/prompts.py:268-298`

- [ ] **Step 1: Add `_compact_active_ad` helper above `diagnose_text`**

Insert near the other `_compact_*` helpers (e.g. after `_compact_angle` at ~line 60):

```python
def _compact_active_ad(ad: dict[str, Any]) -> dict[str, Any]:
    return {
        "ad_id": ad.get("ad_id") or ad.get("id") or "",
        "draft_id": ad.get("draft_id") or "",
        "platform": ad.get("platform") or "",
        "headline": _clip_text(ad.get("headline", ""), 140),
        "body": _clip_text(ad.get("body", ""), 500),
        "cta": ad.get("cta", ""),
        "spend": float(ad.get("spend", 0)),
        "impressions": int(ad.get("impressions", 0)),
        "clicks": int(ad.get("clicks", 0)),
        "ctr": float(ad.get("ctr", 0)),
        "conversions": int(ad.get("conversions", 0)),
    }
```

- [ ] **Step 2: Replace `diagnose_text` body with new schema**

Replace the function (currently at `server/hivemind/prompts.py:268-298`) with:

```python
def diagnose_text(
    *,
    tier: Tier,
    active_ads: list[dict],
) -> str:
    payload = {
        "tier": tier,
        "active_ads": [_compact_active_ad(ad) for ad in active_ads],
    }
    return (
        "Diagnose this paid-ad account. Review each active ad's copy and recent performance, "
        "then return an editorial take, per-ad tweak suggestions, pause recommendations for the worst ads, "
        "and entirely new angles worth testing.\n\n"
        f"Tier: {tier} — "
        + ("intel context is attached." if tier == "B" else "intel is still enriching; rely on knowledge layer.")
        + "\n\nReturn ONLY a JSON object with this exact shape:\n"
        '{\n'
        '  "summary": "2-3 paragraphs of editorial prose — name the underlying pattern, cite a framework",\n'
        '  "kill_recommendations": [\n'
        '    {"target_id": "<ad_id from active_ads>", "platform": "linkedin | facebook", "reasoning": "...", "framework_cited": "name | null"}\n'
        '  ],\n'
        '  "tweaks": [\n'
        '    {\n'
        '      "draft_id": "<draft_id from active_ads>",\n'
        '      "ad_id": "<ad_id from active_ads>",\n'
        '      "platform": "linkedin | facebook",\n'
        '      "critique": "one-sentence read on why this ad is underperforming or could be sharpened",\n'
        '      "refine_guidance": "imperative paragraph the ghostwriter can act on directly — concrete, not abstract",\n'
        '      "framework_cited": "name | null"\n'
        '    }\n'
        '  ],\n'
        '  "new_angles": [\n'
        '    {"id": "n1", "title": "5-8 word title", "angle": "2 sentences", "rationale": "why this is worth testing", "framework_cited": "name | null"}\n'
        '  ],\n'
        '  "tier": "A" | "B"\n'
        '}\n\n'
        "Rules:\n"
        "- Only recommend killing an ad if its CTR is in the bottom decile AND spend >= $5, OR impressions > 1000 with zero clicks.\n"
        "- Suggest a tweak only when the current ad is salvageable — not when it should be killed.\n"
        "- `refine_guidance` must be specific enough that a ghostwriter could rewrite the ad from it alone. No 'make it punchier'.\n"
        "- `new_angles` must be distinct from the angles already implied by the active ads.\n"
        "- Never invent ad_ids or draft_ids that are not in active_ads.\n\n"
        f"Payload:\n{json.dumps(payload, default=str)}"
    )
```

- [ ] **Step 3: Commit**

```bash
git add server/hivemind/prompts.py
git commit -m "feat(diagnose): new strategist prompt schema with tweaks + new_angles"
```

---

### Task 1.2: Refactor `DiagnoseChain.diagnose()` to a single call

**Files:**
- Modify: `server/hivemind/diagnose_chain.py`
- Modify: `tests/server/hivemind/test_diagnose_chain.py`

- [ ] **Step 1: Rewrite the failing test**

Replace `tests/server/hivemind/test_diagnose_chain.py` with:

```python
import json
from unittest.mock import MagicMock
from server.hivemind.diagnose_chain import DiagnoseChain


def _chat_response(payload: dict) -> dict:
    return {"status": "success", "data": {"response": json.dumps(payload)}}


def _diagnose_payload(tier: str) -> dict:
    return {
        "summary": "Anchored too far upstream of buyer intent.",
        "kill_recommendations": [
            {"target_id": "ad-0", "platform": "linkedin", "reasoning": "0 clicks on 5000 impressions.", "framework_cited": "Narrative Health Audit"}
        ],
        "tweaks": [
            {
                "draft_id": "d_abc",
                "ad_id": "ad-1",
                "platform": "linkedin",
                "critique": "Headline buries the proof point.",
                "refine_guidance": "Lead with the 3x conversion stat. Keep the body under 110 chars. Use SIGN_UP as CTA.",
                "framework_cited": "Hook-Stat-Action",
            }
        ],
        "new_angles": [
            {"id": "n1", "title": "ROI-led founder pitch", "angle": "Frame the offer around CFO objections.", "rationale": "Active ads target ops, not finance.", "framework_cited": "JTBD"}
        ],
        "tier": tier,
    }


def test_diagnose_returns_summary_tweaks_and_new_angles():
    hivemind = MagicMock()
    hivemind.chat.side_effect = [_chat_response(_diagnose_payload("A"))]
    chain = DiagnoseChain(hivemind=hivemind)
    result = chain.diagnose(
        project_id="proj-1",
        tier="A",
        active_ads=[
            {"ad_id": "ad-0", "draft_id": "d_zzz", "platform": "linkedin", "headline": "Old", "body": "b", "cta": "LEARN_MORE", "impressions": 5000, "clicks": 0, "spend": 50, "ctr": 0, "conversions": 0},
            {"ad_id": "ad-1", "draft_id": "d_abc", "platform": "linkedin", "headline": "We 3x conv.", "body": "b", "cta": "LEARN_MORE", "impressions": 800, "clicks": 12, "spend": 20, "ctr": 0.015, "conversions": 1},
        ],
    )
    assert result["summary"].startswith("Anchored")
    assert len(result["kill_recommendations"]) == 1
    assert result["tweaks"][0]["draft_id"] == "d_abc"
    assert result["new_angles"][0]["id"] == "n1"
    assert result["tier"] == "A"
    assert hivemind.chat.call_count == 1
    assert hivemind.chat.call_args.kwargs["persona"] == "genius-strategist"
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `venv/bin/pytest tests/server/hivemind/test_diagnose_chain.py -v`
Expected: FAIL — `chain.diagnose()` still takes old `performance_data` kwarg / returns `replacement_drafts`.

- [ ] **Step 3: Rewrite `DiagnoseChain.diagnose()`**

Replace the entire body of `server/hivemind/diagnose_chain.py` with:

```python
"""DiagnoseChain — single strategist call returning summary + tweaks + new_angles + kills."""

from __future__ import annotations
from typing import Any, Callable

from server.hivemind.client import HivemindClient
from server.hivemind.prompts import diagnose_text
from server.hivemind.strategist_chain import _parse_json_reply
from server.hivemind.types import Tier


class DiagnoseChain:
    def __init__(self, hivemind: HivemindClient):
        self.hm = hivemind

    def diagnose(
        self,
        *,
        project_id: str,
        tier: Tier,
        active_ads: list[dict],
        on_step: Callable[[str, str, dict], None] | None = None,
    ) -> dict[str, Any]:
        def emit(step: str, status: str, payload: dict | None = None):
            if on_step:
                on_step(step, status, payload or {})

        emit("strategist", "running", {"tier": tier, "ads": len(active_ads)})
        resp = self.hm.chat(
            text=diagnose_text(tier=tier, active_ads=active_ads),
            persona="genius-strategist",
            project_id=project_id,
        )
        parsed = _parse_json_reply(resp["data"]["response"])
        emit("strategist", "complete", {
            "tier": tier,
            "tweaks": len(parsed.get("tweaks", [])),
            "new_angles": len(parsed.get("new_angles", [])),
            "kills": len(parsed.get("kill_recommendations", [])),
        })

        return {
            "summary": parsed.get("summary", ""),
            "kill_recommendations": parsed.get("kill_recommendations", []),
            "tweaks": parsed.get("tweaks", []),
            "new_angles": parsed.get("new_angles", []),
            "tier": tier,
        }
```

- [ ] **Step 4: Run test — expect PASS**

Run: `venv/bin/pytest tests/server/hivemind/test_diagnose_chain.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add server/hivemind/diagnose_chain.py tests/server/hivemind/test_diagnose_chain.py
git commit -m "feat(diagnose): single strategist call returns tweaks + new_angles"
```

---

### Task 1.3: Update the SSE route to assemble `active_ads` and drop eager image gen

**Files:**
- Modify: `server/routes/diagnose.py`
- Modify: `server/demo.py:142+` (`demo_diagnosis_result`)

- [ ] **Step 1: Update `demo_diagnosis_result` to new shape**

Find `demo_diagnosis_result` in `server/demo.py` (around line 142) and replace its body so it returns the new schema. Use this exact return value:

```python
def demo_diagnosis_result() -> dict[str, Any]:
    return {
        "summary": (
            "The current ad set is anchored to ops-language while spend keeps landing on finance buyers. "
            "Lead with concrete ROI proof, then test a second angle aimed at the CFO objection set."
        ),
        "kill_recommendations": [
            {
                "target_id": "demo-ad-killed",
                "platform": "linkedin",
                "reasoning": "0 clicks on 5,200 impressions — narrative is invisible to the audience.",
                "framework_cited": "Narrative Health Audit",
            }
        ],
        "tweaks": [
            {
                "draft_id": "d_demo1",
                "ad_id": "demo-ad-1",
                "platform": "linkedin",
                "critique": "Headline buries the proof point and the CTA is too soft for a buyer in evaluation.",
                "refine_guidance": (
                    "Lead with the '3x faster diligence' stat in the headline. Cut the body to one sentence "
                    "naming the outcome. Switch CTA to SIGN_UP."
                ),
                "framework_cited": "Hook-Stat-Action",
            }
        ],
        "new_angles": [
            {
                "id": "n_demo1",
                "title": "Founder-to-CFO economic case",
                "angle": "Frame the platform around the CFO's procurement objections instead of the ops team's day-to-day.",
                "rationale": "Spend is landing on finance ICPs; current ads speak ops dialect.",
                "framework_cited": "Jobs-to-be-Done",
            }
        ],
        "tier": "B",
    }
```

- [ ] **Step 2: Rewrite the SSE route's `run_chain()` body**

In `server/routes/diagnose.py`, replace the entire `async def run_chain():` block inside `diagnose_stream` with this implementation. (Keep everything outside `run_chain` unchanged — the `request`, `queue`, `on_step`, `event_gen`, and the `return EventSourceResponse(...)` line.)

```python
    async def run_chain():
        loop = asyncio.get_running_loop()
        try:
            if demo_mode() and os.environ.get("ADPILOT_DEMO_MOCK_DIAGNOSE", "true").lower() in {"1", "true", "yes", "on"}:
                on_step("strategist", "running", {"tier": tier})
                await asyncio.sleep(0.35)
                on_step("strategist", "complete", {"tier": tier})
                result = demo_diagnosis_result()
            else:
                # Join analytics rows with the draft copy we shipped (by external_urn -> draft_id)
                pushed = [
                    d for d in drafts_db().list_drafts(workspace_id=state["workspace_id"])
                    if d.get("status") == "pushed" and d.get("external_urn")
                ]
                copy_by_urn = {d["external_urn"]: d for d in pushed}
                # Normalize: ad_id from the analytics row equals the part after "fb:" / "urn:li:..." last segment
                def _draft_for(row: dict) -> dict | None:
                    ad_id = row.get("ad_id", "")
                    # Facebook URNs look like "fb:<id>"; LinkedIn URNs look like "urn:li:sponsoredCreative:<id>".
                    fb_key = f"fb:{ad_id}"
                    if fb_key in copy_by_urn:
                        return copy_by_urn[fb_key]
                    for urn, draft in copy_by_urn.items():
                        if urn.endswith(f":{ad_id}"):
                            return draft
                    return None

                active_ads: list[dict] = []
                for row in rows:
                    d = _draft_for(row)
                    active_ads.append({
                        "ad_id": row.get("ad_id", ""),
                        "draft_id": d.get("id") if d else "",
                        "platform": row.get("platform", ""),
                        "headline": d.get("headline", "") if d else row.get("ad_name", ""),
                        "body": d.get("body", "") if d else "",
                        "cta": d.get("cta", "") if d else "",
                        "spend": row.get("spend", 0),
                        "impressions": row.get("impressions", 0),
                        "clicks": row.get("clicks", 0),
                        "ctr": row.get("ctr", 0),
                        "conversions": row.get("conversions", 0),
                    })

                result = await loop.run_in_executor(
                    None,
                    lambda: chain.diagnose(
                        project_id=state["hivemind"]["project_id"],
                        tier=tier,
                        active_ads=active_ads,
                        on_step=on_step,
                    ),
                )

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
                    "tweaks": result["tweaks"],
                    "new_angles": result["new_angles"],
                    "tier": result["tier"],
                },
            })
        except Exception as exc:
            log.exception("diagnose chain failed")
            queue.put_nowait({"event": "error", "data": {"error": str(exc)}})
        finally:
            queue.put_nowait(None)
```

- [ ] **Step 3: Drop the unused `from scripts import generate_image as gi` import**

That import lives at the top of the old `run_chain` block — verify it's gone after the rewrite. Also remove `voice_notes = state["business"].get("voice_notes", "")` (no longer used in the call).

- [ ] **Step 4: Smoke-test the import path**

Run: `venv/bin/python -c "from server.routes import diagnose; print('ok')"`
Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add server/routes/diagnose.py server/demo.py
git commit -m "feat(diagnose): assemble active_ads from drafts; drop eager image+ghostwriter"
```

---

## Phase 2 — Backend: action endpoints

### Task 2.1: Allow refining a pushed draft (spawn sibling, no supersede)

**Files:**
- Modify: `server/routes/drafts.py` — `refine_draft` (around line 209-271)
- Modify (or create): `tests/server/routes/test_drafts_refine.py`

- [ ] **Step 1: Write the failing test**

Create `tests/server/routes/test_drafts_refine.py`:

```python
import json
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def _bootstrap(tmpdir: str):
    os.environ["ADPILOT_WORKSPACE_DIR"] = tmpdir
    os.environ["ADPILOT_DEMO_MODE"] = "false"
    # Force a fresh deps singleton
    from importlib import reload
    from server import deps as deps_module
    reload(deps_module)
    from server import main as main_module
    reload(main_module)
    return main_module.app


def _seed_pushed_draft(workspace_id: str) -> str:
    from server.deps import drafts_db
    db = drafts_db()
    draft_id = "d_pushed1"
    db.insert_draft({
        "id": draft_id,
        "workspace_id": workspace_id,
        "platform": "linkedin",
        "headline": "Old headline",
        "body": "Old body",
        "cta": "LEARN_MORE",
        "image_path": "",
        "rationale": "",
        "strategist_trace": {},
        "source": "generate",
        "source_angle_id": None,
        "tier": "A",
        "parent_draft_id": None,
        "status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    db.mark_pushed(draft_id, external_urn="urn:li:sponsoredCreative:123", external_url="https://example/x")
    return draft_id


def test_refine_pushed_draft_creates_sibling_without_superseding_parent():
    with tempfile.TemporaryDirectory() as tmp:
        app = _bootstrap(tmp)
        client = TestClient(app)

        # Seed a workspace + a pushed draft
        from server.deps import workspace_store
        workspace_store().save({
            "workspace_id": "ws1",
            "hivemind": {"project_id": "p1", "website_url": "https://x.test", "enrichment_status": "ready"},
            "business": {"voice_notes": "", "focus_notes": ""},
            "platforms": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        pushed_id = _seed_pushed_draft("ws1")

        # Mock the strategist chain so we don't hit Hivemind
        fake_result = {
            "tier": "A",
            "strategist_output": {"mode": "refine_ad_copy"},
            "draft": {"headline": "New", "body": "New body", "cta": "SIGN_UP", "rationale": "r"},
        }
        with patch("server.routes.drafts.StrategistChain") as Chain, \
             patch("server.routes.drafts.gi.generate_image", side_effect=Exception("no openai")) if False else patch.object(__import__("scripts.generate_image", fromlist=["generate_image"]), "generate_image", side_effect=Exception("no openai")):
            instance = Chain.return_value
            instance.refine_draft_copy = MagicMock(return_value=fake_result)

            resp = client.post(f"/drafts/{pushed_id}/refine", json={"guidance": "make it sharper"})
            assert resp.status_code == 200, resp.text
            new_draft = resp.json()
            assert new_draft["headline"] == "New"
            assert new_draft["parent_draft_id"] == pushed_id
            assert new_draft["status"] == "draft"

        # Parent must still be 'pushed', not 'superseded'
        from server.deps import drafts_db
        parent_after = drafts_db().get_draft(pushed_id)
        assert parent_after["status"] == "pushed"
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `venv/bin/pytest tests/server/routes/test_drafts_refine.py -v`
Expected: FAIL — current endpoint returns 409 for pushed drafts.

- [ ] **Step 3: Relax the refine endpoint**

In `server/routes/drafts.py`, locate the `refine_draft` function. Remove the 409 guard and skip `mark_superseded` when the parent is published. The change:

Replace:

```python
    if parent["status"] == "pushed":
        raise HTTPException(409, "Published ads cannot be refined")
```

with: (delete it — no replacement)

Then near the end of the function, replace:

```python
    drafts_db().insert_draft(row)
    drafts_db().mark_superseded(draft_id)
    return drafts_db().get_draft(new_id)
```

with:

```python
    drafts_db().insert_draft(row)
    if parent["status"] != "pushed":
        drafts_db().mark_superseded(draft_id)
    return drafts_db().get_draft(new_id)
```

- [ ] **Step 4: Run test — expect PASS**

Run: `venv/bin/pytest tests/server/routes/test_drafts_refine.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add server/routes/drafts.py tests/server/routes/test_drafts_refine.py
git commit -m "feat(drafts): refine of pushed drafts spawns sibling instead of 409"
```

---

### Task 2.2: New endpoint `POST /drafts/from-angle`

**Files:**
- Modify: `server/routes/drafts.py`
- Modify (or create): `tests/server/routes/test_drafts_from_angle.py`

- [ ] **Step 1: Write the failing test**

Create `tests/server/routes/test_drafts_from_angle.py`:

```python
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def _bootstrap(tmpdir: str):
    os.environ["ADPILOT_WORKSPACE_DIR"] = tmpdir
    os.environ["ADPILOT_DEMO_MODE"] = "false"
    from importlib import reload
    from server import deps as deps_module
    reload(deps_module)
    from server import main as main_module
    reload(main_module)
    return main_module.app


def test_from_angle_persists_draft_no_image():
    with tempfile.TemporaryDirectory() as tmp:
        app = _bootstrap(tmp)
        client = TestClient(app)

        from server.deps import workspace_store
        workspace_store().save({
            "workspace_id": "ws1",
            "hivemind": {"project_id": "p1", "website_url": "https://x.test", "enrichment_status": "ready"},
            "business": {"voice_notes": "", "focus_notes": ""},
            "platforms": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        chain_return = {
            "tier": "B",
            "strategist_output": {"selected_angle": {"id": "n1"}, "mode": "ad_set"},
            "drafts": [
                {"headline": "H", "body": "B", "cta": "SIGN_UP", "rationale": "r", "platform": "linkedin", "angle_id": "n1"}
            ],
        }
        with patch("server.routes.drafts.StrategistChain") as Chain:
            instance = Chain.return_value
            instance.generate_from_angle = MagicMock(return_value=chain_return)

            resp = client.post("/drafts/from-angle", json={
                "angle": {"id": "n1", "title": "Founder-to-CFO", "angle": "Frame the CFO objection."},
                "platform": "linkedin",
            })
            assert resp.status_code == 200, resp.text
            d = resp.json()
            assert d["headline"] == "H"
            assert d["platform"] == "linkedin"
            assert d["image_path"] == ""
            assert d["source"] == "diagnose_new_angle"
            assert d["status"] == "draft"
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `venv/bin/pytest tests/server/routes/test_drafts_from_angle.py -v`
Expected: FAIL — endpoint does not exist (404).

- [ ] **Step 3: Add the endpoint**

Append to `server/routes/drafts.py`:

```python
class FromAngleIn(BaseModel):
    angle: dict
    platform: str  # linkedin | facebook


@router.post("/drafts/from-angle")
def draft_from_angle(body: FromAngleIn):
    if body.platform not in ("linkedin", "facebook"):
        raise HTTPException(400, "platform must be linkedin or facebook")
    state = workspace_store().load()
    if not state:
        raise HTTPException(404, "No workspace — onboard first")
    tier = "B" if state.get("hivemind", {}).get("enrichment_status") == "ready" else "A"

    chain = StrategistChain(hivemind=hivemind())
    result = chain.generate_from_angle(
        project_id=state["hivemind"]["project_id"],
        tier=tier,
        business=_business_from_state(state),
        angle=body.angle,
        platforms=[body.platform],
        ads_per_platform=1,
    )
    if not result["drafts"]:
        raise HTTPException(502, "Ghostwriter returned no drafts")
    d = result["drafts"][0]

    new_id = f"d_{uuid.uuid4().hex[:8]}"
    row = {
        "id": new_id,
        "workspace_id": state["workspace_id"],
        "platform": body.platform,
        "headline": d.get("headline", ""),
        "body": d.get("body", ""),
        "cta": d.get("cta", ""),
        "image_path": "",
        "rationale": d.get("rationale", ""),
        "strategist_trace": result["strategist_output"],
        "source": "diagnose_new_angle",
        "source_angle_id": body.angle.get("id"),
        "tier": result["tier"],
        "parent_draft_id": None,
        "status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    drafts_db().insert_draft(row)
    return drafts_db().get_draft(new_id)
```

- [ ] **Step 4: Run test — expect PASS**

Run: `venv/bin/pytest tests/server/routes/test_drafts_from_angle.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add server/routes/drafts.py tests/server/routes/test_drafts_from_angle.py
git commit -m "feat(drafts): POST /drafts/from-angle generates copy-only draft from an angle"
```

---

## Phase 3 — Frontend

### Task 3.1: New TypeScript types + API method

**Files:**
- Modify: `web/lib/api.ts:144` (around `acceptDiagnose`)

- [ ] **Step 1: Add types above `j<T>` (or alongside the other interfaces near line 60-70)**

Insert near the existing interfaces:

```ts
export interface DiagnoseKill {
  target_id: string;
  platform: "linkedin" | "facebook";
  reasoning: string;
  framework_cited: string | null;
}

export interface DiagnoseTweak {
  draft_id: string;
  ad_id: string;
  platform: "linkedin" | "facebook";
  critique: string;
  refine_guidance: string;
  framework_cited: string | null;
}

export interface DiagnoseNewAngle {
  id: string;
  title: string;
  angle: string;
  rationale: string;
  framework_cited: string | null;
}

export interface DiagnoseResult {
  diagnose_id: string;
  summary: string;
  kill_recommendations: DiagnoseKill[];
  tweaks: DiagnoseTweak[];
  new_angles: DiagnoseNewAngle[];
  tier: "A" | "B";
}
```

- [ ] **Step 2: Add `draftFromAngle` to the `api` object**

Inside the `api = { ... }` block in `web/lib/api.ts`, add a method (immediately below `regenerateDraftImage`):

```ts
  draftFromAngle: (body: { angle: Record<string, unknown>; platform: "linkedin" | "facebook" }) =>
    j<Draft>(`/drafts/from-angle`, { method: "POST", body: JSON.stringify(body) }),
```

- [ ] **Step 3: Typecheck**

Run: `cd web && npx tsc --noEmit`
Expected: no output (clean).

- [ ] **Step 4: Commit**

```bash
git add web/lib/api.ts
git commit -m "feat(api): diagnose result types + draftFromAngle method"
```

---

### Task 3.2: `TweakCard` component

**Files:**
- Create: `web/components/TweakCard.tsx`

- [ ] **Step 1: Create the component**

```tsx
"use client";

import { Pencil } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Textarea } from "@/components/ui/Textarea";
import { DiagnoseTweak, api } from "@/lib/api";

interface Props {
  tweak: DiagnoseTweak;
  onRefined: () => void;
}

export function TweakCard({ tweak, onRefined }: Props) {
  const [guidance, setGuidance] = useState(tweak.refine_guidance);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refine = async () => {
    if (!tweak.draft_id) {
      setError("This ad has no linked draft in the workspace; cannot refine.");
      return;
    }
    if (!guidance.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.refineDraft(tweak.draft_id, guidance.trim());
      setDone(true);
      onRefined();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Refine failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-center gap-2 flex-wrap">
        <Badge>{tweak.platform}</Badge>
        {tweak.framework_cited && <Badge tone="highlight">{tweak.framework_cited}</Badge>}
        <span className="font-mono text-[11px] text-[var(--color-ink-muted)]">{tweak.ad_id}</span>
      </div>
      <p className="text-sm">{tweak.critique}</p>
      <div>
        <label className="font-mono text-[11px] uppercase tracking-widest text-[var(--color-ink-muted)] mb-2 block">
          Refine guidance (editable)
        </label>
        <Textarea
          value={guidance}
          onChange={(e) => setGuidance(e.target.value)}
          disabled={busy || done}
          className="min-h-[110px]"
        />
      </div>
      {error && <p className="text-sm text-[var(--color-negative)]">{error}</p>}
      <div className="flex justify-end">
        <Button size="sm" onClick={refine} disabled={busy || done || !guidance.trim()}>
          <Pencil className="w-4 h-4" />
          {done ? "Refined ✓" : busy ? "Refining…" : "Refine ad"}
        </Button>
      </div>
    </Card>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd web && npx tsc --noEmit`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add web/components/TweakCard.tsx
git commit -m "feat(diagnose): TweakCard renders critique + editable refine guidance"
```

---

### Task 3.3: `NewAngleCard` component

**Files:**
- Create: `web/components/NewAngleCard.tsx`

- [ ] **Step 1: Create the component**

```tsx
"use client";

import { Sparkles } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DiagnoseNewAngle, api } from "@/lib/api";

interface Props {
  angle: DiagnoseNewAngle;
  onGenerated: () => void;
}

export function NewAngleCard({ angle, onGenerated }: Props) {
  const [busy, setBusy] = useState<"linkedin" | "facebook" | null>(null);
  const [created, setCreated] = useState<{ linkedin: boolean; facebook: boolean }>({ linkedin: false, facebook: false });
  const [error, setError] = useState<string | null>(null);

  const generate = async (platform: "linkedin" | "facebook") => {
    setBusy(platform);
    setError(null);
    try {
      await api.draftFromAngle({ angle: angle as unknown as Record<string, unknown>, platform });
      setCreated((c) => ({ ...c, [platform]: true }));
      onGenerated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-center gap-2 flex-wrap">
        {angle.framework_cited && <Badge tone="highlight">{angle.framework_cited}</Badge>}
      </div>
      <h3 className="font-display text-xl leading-tight">{angle.title}</h3>
      <p className="text-sm">{angle.angle}</p>
      <p className="text-xs italic font-display border-t border-[var(--color-hairline)] pt-3 text-[var(--color-ink-muted)]">
        {angle.rationale}
      </p>
      {error && <p className="text-sm text-[var(--color-negative)]">{error}</p>}
      <div className="flex gap-2">
        <Button
          size="sm"
          variant="secondary"
          onClick={() => generate("linkedin")}
          disabled={busy !== null || created.linkedin}
          className="flex-1"
        >
          <Sparkles className="w-4 h-4" />
          {created.linkedin ? "LinkedIn ✓" : busy === "linkedin" ? "Generating…" : "Generate LinkedIn ad"}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => generate("facebook")}
          disabled={busy !== null || created.facebook}
          className="flex-1"
        >
          <Sparkles className="w-4 h-4" />
          {created.facebook ? "Facebook ✓" : busy === "facebook" ? "Generating…" : "Generate Facebook ad"}
        </Button>
      </div>
    </Card>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd web && npx tsc --noEmit`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add web/components/NewAngleCard.tsx
git commit -m "feat(diagnose): NewAngleCard with per-platform Generate buttons"
```

---

### Task 3.4: Rewrite `/workspace/diagnose` page

**Files:**
- Modify: `web/app/workspace/diagnose/page.tsx`

- [ ] **Step 1: Replace the whole file**

```tsx
"use client";
import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { ChainTrace } from "@/components/ChainTrace";
import { TweakCard } from "@/components/TweakCard";
import { NewAngleCard } from "@/components/NewAngleCard";
import { API_BASE, ChainStep, DiagnoseResult, api } from "@/lib/api";

export default function DiagnosePage() {
  const [steps, setSteps] = useState<ChainStep[]>([]);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<DiagnoseResult | null>(null);
  const [killed, setKilled] = useState<Set<string>>(new Set());

  const run = () => {
    setRunning(true);
    setSteps([]);
    setResult(null);
    const src = new EventSource(`${API_BASE}/diagnose`);
    src.addEventListener("chain_step", (e) => {
      const s = JSON.parse((e as MessageEvent).data);
      setSteps((arr) => [...arr.filter((x) => x.step !== s.step), s]);
    });
    src.addEventListener("result", (e) => {
      setResult(JSON.parse((e as MessageEvent).data));
      setRunning(false);
      src.close();
    });
    src.addEventListener("error", () => {
      setRunning(false);
      src.close();
    });
  };

  const acceptKill = async (target_id: string, platform: string) => {
    try {
      await api.acceptDiagnose({ action: "kill", target_id, platform });
      setKilled((prev) => new Set([...prev, target_id]));
    } catch (e) {
      console.error("Failed to kill", e);
    }
  };

  return (
    <>
      <header className="mb-10 flex items-center justify-between">
        <div>
          <h1 className="font-display text-4xl">Diagnose</h1>
          <p className="text-[var(--color-ink-muted)] mt-1">
            Strategist reviews recent performance and proposes specific next moves.
          </p>
        </div>
        <Button onClick={run} disabled={running} size="lg">
          {running ? "Running…" : "Run diagnosis"}
        </Button>
      </header>

      {steps.length > 0 && !result && (
        <Card><ChainTrace steps={steps} /></Card>
      )}

      {result && (
        <div className="space-y-10">
          <Card className="space-y-3">
            <p className="font-mono text-xs uppercase tracking-widest text-[var(--color-ink-muted)]">Strategist take</p>
            <p className="font-display text-xl leading-relaxed whitespace-pre-line">{result.summary}</p>
          </Card>

          {result.kill_recommendations.length > 0 && (
            <section>
              <h2 className="font-display text-2xl mb-4">Pause these</h2>
              <div className="space-y-3">
                {result.kill_recommendations.map((k) => {
                  const isKilled = killed.has(k.target_id);
                  return (
                    <Card key={k.target_id} className="flex items-start gap-4">
                      <div className="flex-1">
                        <p className="font-mono text-xs text-[var(--color-ink-muted)]">{k.target_id}</p>
                        <p className="mt-2">{k.reasoning}</p>
                        {k.framework_cited && (
                          <span className="inline-block mt-2 text-xs text-[var(--color-ink-muted)] italic">
                            {k.framework_cited}
                          </span>
                        )}
                      </div>
                      <Button
                        variant={isKilled ? "secondary" : "danger"}
                        onClick={() => acceptKill(k.target_id, k.platform)}
                        disabled={isKilled}
                      >
                        {isKilled ? "Paused ✓" : "Approve pause"}
                      </Button>
                    </Card>
                  );
                })}
              </div>
            </section>
          )}

          {result.tweaks.length > 0 && (
            <section>
              <h2 className="font-display text-2xl mb-2">Tweak existing ads</h2>
              <p className="text-sm text-[var(--color-ink-muted)] mb-4">
                Each card&apos;s guidance is editable — refine creates a new draft on the Ads page.
              </p>
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                {result.tweaks.map((t) => (
                  <TweakCard key={`${t.draft_id}-${t.ad_id}`} tweak={t} onRefined={() => {}} />
                ))}
              </div>
            </section>
          )}

          {result.new_angles.length > 0 && (
            <section>
              <h2 className="font-display text-2xl mb-2">Test new angles</h2>
              <p className="text-sm text-[var(--color-ink-muted)] mb-4">
                Generate copy on demand. Images aren&apos;t auto-generated — kick them off from the Ads page when ready.
              </p>
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                {result.new_angles.map((a) => (
                  <NewAngleCard key={a.id} angle={a} onGenerated={() => {}} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </>
  );
}
```

- [ ] **Step 2: Typecheck**

Run: `cd web && npx tsc --noEmit`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add web/app/workspace/diagnose/page.tsx
git commit -m "feat(diagnose): rewrite page to render summary + pause + tweaks + new angles"
```

---

## Phase 4 — Manual verification

### Task 4.1: End-to-end smoke (demo mode)

**Files:** none — manual check.

- [ ] **Step 1: Start the sidecar in demo mode**

```bash
ADPILOT_DEMO_MODE=true venv/bin/python -m uvicorn server.main:app --reload --port 8787
```

Expected: server starts on 8787.

- [ ] **Step 2: Start the web dev server**

```bash
cd web && npm run dev
```

Expected: Next.js dev server on 3000.

- [ ] **Step 3: Open `/workspace/diagnose` and click "Run diagnosis"**

Expected:
- Chain trace shows `strategist running` then `strategist complete` (no `ghostwriter` step).
- Result section shows: a summary block, one pause card, one tweak card, one new-angle card.
- The tweak card's textarea is pre-filled with the demo guidance text.
- Each new-angle card has both LinkedIn and Facebook generate buttons.

- [ ] **Step 4: Click "Refine ad" on the tweak card**

Expected: button shows "Refining…", then "Refined ✓". No console errors. Navigate to `/workspace/ads`: a new draft for the same platform with the refined headline appears.

- [ ] **Step 5: Click "Generate LinkedIn ad" on the new-angle card**

Expected: button shows "Generating…", then "LinkedIn ✓". On `/workspace/ads`, a new draft with `source=diagnose_new_angle` exists with an empty image slot + "Generate image" button (the on-demand image affordance already shipped).

- [ ] **Step 6: Stop both servers**

No commit — this task is verification only.

---

## Self-review notes

- **Spec coverage:** Summary → Task 1.1/1.2/3.4. Tweak cards with prefilled text → Task 1.1 (`refine_guidance` field) + Task 3.2 + Task 3.4. New-angle cards with inline generate → Task 2.2 + Task 3.3 + Task 3.4. Drop eager ghostwriter/image work → Task 1.2 + 1.3. Refine pushed-ads support → Task 2.1.
- **Out of scope reminder:** The "Generate image" affordance on draft cards and the `POST /drafts/{id}/regenerate-image` endpoint already exist — do not re-implement.
- **Cache invalidation:** The diagnose page does not currently call `reload()` on the ads list. The `onRefined` / `onGenerated` callbacks in TweakCard/NewAngleCard are wired as no-ops because the user navigates to `/workspace/ads` to see the result. If a "view created drafts inline" UX is wanted later, those hooks are the place to plug a toast or counter.
