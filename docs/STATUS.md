# AdPilot — Build Status & Next Steps

**Last updated:** 2026-05-14 (post-audit revision)
**Branch:** master
**Hackathon deadline:** 09:00 today (Day 3) — submission closes

## Where we are

Implementation complete across all 10 phases of `docs/superpowers/plans/2026-05-13-adpilot-hackathon.md`. **42 commits** on master (`63e38ec` → `3442e35`). 85 backend tests passing. Next.js builds clean.

The full codebase audit landed in `docs/audit-2026-05-14.md`. 4 high-priority findings and 4 medium ones fixed; deferred items documented. See **Audit fixes** section below.

**Not yet done:** live smoke test with real Hivemind/LinkedIn/Facebook keys → Loom recording → submission form.

## What shipped (by phase)

| Phase | Status | Commits |
|---|---|---|
| 1. FastAPI sidecar scaffold | ✅ | 3 commits |
| 2. HivemindClient (6 API methods) | ✅ | 3 commits |
| 3. Strategist + Diagnose chains with tier A/B branching | ✅ | 3 commits |
| 4. WorkspaceStore + DraftsDB + IntelligencePoller + SSE | ✅ | 4 commits |
| 5. Next.js scaffold + design tokens + UI primitives + API client | ✅ | 4 commits |
| 6. Onboarding (POST /workspace + form UI) | ✅ | 5 commits |
| 7. Drafts page + /generate SSE + push + enhance affordance | ✅ | 4 commits |
| 8. Analytics endpoint + page | ✅ | 2 commits |
| 9. Diagnose SSE + accept + page | ✅ | 2 commits |
| 10. Prewarm script + README + HACKATHON.md | ✅ | 3 commits |
| Post-review fixes (5 issues) | ✅ | 5 commits |
| Codebase audit (8 findings) | ✅ | 4 commits |

## Critical fixes applied during post-implementation review

These were caught by the final code reviewer and patched (`a3175fe` through `519c6a8`):

1. **Poller event-loop bug.** `create_workspace` was sync → background task ran in a thread → `asyncio.create_task` inside `poller.track()` raised silently. Fixed: route is now `async def` and schedules the kickoff on the event loop. **Without this fix, the tier-A→B demo moment never fires.**
2. **Push 400s.** `DraftCard` didn't pass `campaign_id` / `adset_id`. Fixed: server falls back to `LI_DEFAULT_CAMPAIGN_ID` / `FB_DEFAULT_ADSET_ID` env vars.
3. **SystemExit propagation.** `scripts/generate_image.py` calls `sys.exit(1)` on budget exhaustion. Now caught in all three places that invoke it.
4. **Diagnose kill platform attribution.** Was a broken regex heuristic on the frontend. Now `DiagnoseKillRec` carries a `platform` field that the Strategist must populate.
5. **Atomic write in `update_report_status`.** Now matches `save()` tmp-file pattern.

## Audit fixes (2026-05-14)

Full report at `docs/audit-2026-05-14.md`. Eight findings fixed across 4 commits (`dcbacd5`, `a69f038`, `195c6a4`, `3442e35`):

**High-priority:**

1. **`.env.example` missing required vars.** Fresh checkouts couldn't run — `OPENAI_API_KEY`, `LINKEDIN_ACCESS_TOKEN`, `FACEBOOK_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID` were all absent. Now complete.
2. **Server restart silently broke workspace.** Tokens were written to `workspace/.tokens.env` but never loaded back. Every restart forced a re-onboard. Fixed with a `lifespan` hook in `server/main.py` that re-populates `os.environ` from disk on startup.
3. **Path traversal in `/api/image`.** `p.includes("/workspace/")` is bypassable (e.g. `/etc/workspace/../../etc/passwd`). Now resolves the absolute path and requires it to live under the actual workspace directory.
4. **`api.pushDraft` missing `adset_id` type.** Frontend couldn't pass a Facebook adset id even if it wanted to. Type extended; return value typed as `{external_urn, external_url}` instead of `unknown`.

**Dead/redundant code pruned:**

5. **Duplicated env-setup boilerplate** across `drafts.py`, `analytics.py`, `diagnose.py` — same 4 lines copied. Removed entirely; startup loader + canonical names handle it.
6. **`LINKEDIN_TOKEN` / `FACEBOOK_TOKEN` indirection.** Onboarding wrote tokens under one name but `scripts/*.py` read another, forcing every route to alias. Now writes canonical `LINKEDIN_ACCESS_TOKEN` / `FACEBOOK_ACCESS_TOKEN` / `FACEBOOK_PAGE_ID` directly.
7. **Dead `token_ref` field** in workspace state — never read. Removed.
8. **Late `BaseModel` import** at `workspace.py:98` (with a vestigial `_PydBaseModel` alias) — moved to top of file.

**Hygiene:**

- `drafts/2026-*/` and `samples/` added to `.gitignore` so future generated artifacts aren't tracked (existing tracked PNGs left alone — purging history not worth the risk during hackathon).
- All planning docs (spec, plan, STATUS, audit) committed to git — were untracked before.

**Deferred items** (documented in audit report, not blocking):

- 112MB of generated drafts already in git history — needs `git filter-repo` to remove cleanly; post-hackathon.
- `scripts/prewarm_aurevon.py` imports from `server/` (reverses original layering) — low impact.
- Aurevon-specific brand hardcoding in `scripts/` — known limitation; onboarding collects values but doesn't pipe them through to the scripts layer. Acceptable for the demo (which runs on Aurevon's own account).

## What is NOT verified

Live integration depends on real API keys we haven't run with:

- **Hivemind `/api/v1/chat` request shape.** Client assumes `persona` is a JSON body field. Day-of verification from `hivemind.myosin.xyz/api-docs` may require adjusting `server/hivemind/client.py:chat()`.
- **Strategist + Ghostwriter persona names.** We use `"Strategist"` and `"Ghostwriter"` literally. May need to match exact persona slugs Hivemind expects.
- **LinkedIn + Facebook token validation flows.** Code is structurally correct; not exercised live.
- **Real image generation output.** Uses Aurevon's existing `_LOGOS["mark"]` and brand palette. Style id is hardcoded to `1` — may want to randomize for demo variety.
- **Tier A→B transition end-to-end.** Depends on Hivemind actually completing the intelligence report. Pre-warm is the workaround.

## Immediate next steps (in order)

### 1. Fill `.env` (5 min)

Copy `.env.example` to `.env` and fill every empty value. The file is now complete — it lists all required and optional vars including the new `LI_DEFAULT_CAMPAIGN_ID` / `FB_DEFAULT_ADSET_ID` fallbacks for push and the optional `AUREVON_PROJECT_ID` for prewarm.

Onboarding will also persist a subset of these (`LINKEDIN_ACCESS_TOKEN`, `FACEBOOK_ACCESS_TOKEN`, `FACEBOOK_PAGE_ID`) to `workspace/.tokens.env`, which the server reloads on every restart — so once onboarded, you don't need to re-fill those manually.

### 2. Pre-warm Aurevon intelligence reports (RUN ASAP — up to 1h)

```bash
AUREVON_PROJECT_ID=<uuid> python -m scripts.prewarm_aurevon
```

This kicks off `competitive_intelligence` + `attention_landscape` for Aurevon's project. Reports take up to an hour; start this before doing anything else.

If Aurevon doesn't have a Hivemind project yet, create one via the AdPilot onboarding flow once (using real Aurevon details), capture the project_id from the returned JSON, then run prewarm.

### 3. Verify Hivemind chat shape (10 min)

Open `hivemind.myosin.xyz/api-docs`. Confirm `/api/v1/chat`:
- Persona is a JSON body field named `persona` (vs. agent_id, path param, etc.)
- Response shape has `reply` at top level (vs. `data.reply`, `content`, etc.)

If different, update `server/hivemind/client.py:chat()` and any `.reply` accessors in `server/hivemind/strategist_chain.py` / `diagnose_chain.py`.

### 4. End-to-end smoke (15-20 min)

```bash
# Terminal 1
uvicorn server.main:app --port 8000

# Terminal 2
cd web && npm run dev
```

Walk this path:
1. Open `http://localhost:3000` → redirects to `/onboard`.
2. Fill the form with Aurevon details + real tokens. Submit.
3. **Watch server log** — within 60s you should see HTTP GET to `/api/intelligence/jobs/...`. **If you don't, the poller fix didn't take.** Re-check `server/routes/workspace.py` is `async def`.
4. Land on `/workspace/drafts`. Chip should say "Market intelligence: brewing".
5. Click **Generate drafts**. Watch the chain trace: `intelligence_pull` → `knowledge_search` → `strategist_diagnosis` → `ghostwriter_drafts`. Drafts populate.
6. If pre-warmed reports are already complete, chip flips to "ready", banner appears, Enhance affordance shows on existing drafts.
7. Click **Push to linkedin** on one. Verify a new PAUSED creative appears in LinkedIn Campaign Manager.
8. Navigate to `/workspace/analytics`. Verify Aurevon's real 30d data renders.
9. Navigate to `/workspace/diagnose`, click **Run diagnosis**. Verify summary, kill recs, replacement drafts.

### 5. Record Loom (15 min)

Follow `docs/specs/2026-05-13-adpilot-hackathon-design.md` §4 demo narrative. Keep to 5-7 min. Voiceover should name every Hivemind API call as it happens, and explicitly call out the Tier-A → Tier-B moment.

### 6. Submit (10 min)

Use `HACKATHON.md` at repo root as the source. Paste fields into the submission portal. Add the Loom URL and the GitHub repo URL.

## Known gaps / things to watch

- **LinkedIn `_ORG_URN` is hardcoded to Aurevon** in `scripts/li_campaign.py:30`. Fine for demoing on Aurevon's own account. Document this in the README's caveats if a judge asks.
- **Style ID is hardcoded to `1`** in image gen calls. All drafts will use the same visual style. If demo polish matters: randomize across available style ids (see `scripts/generate_image.py:list_styles()`).
- **No webhook for intelligence completion.** Poller hits every 60s. If demo viewers expect instant feedback, mention this in the voiceover and tie it to the "product opportunity" section.
- **Drafts list returns `[]` instead of 404 when no workspace exists.** Low-stakes UX paper cut.
- **`/api/v1/chat` request shape still unverified.** Day-of check against Hivemind's docs is still pending — see step 3 of immediate next steps.

## Quick file map

```
docs/
  specs/2026-05-13-adpilot-hackathon-design.md   ← full spec
  superpowers/plans/2026-05-13-adpilot-hackathon.md  ← implementation plan (30 tasks)
  audit-2026-05-14.md                            ← codebase audit + fixes applied
  STATUS.md                                      ← this file
HACKATHON.md                                     ← submission form draft
README.md                                        ← judge-readable walkthrough
.env.example                                     ← env var template

server/
  main.py                ← FastAPI app entry
  deps.py                ← lazy singletons
  models.py              ← Pydantic OnboardIn
  events.py              ← in-process pub/sub
  hivemind/
    client.py            ← HivemindClient
    strategist_chain.py  ← generate chain (tier A/B)
    diagnose_chain.py    ← diagnose chain
    poller.py            ← intelligence job poller
    prompts.py           ← Strategist/Ghostwriter/Diagnose system prompts
    types.py
  store/
    workspace.py         ← WorkspaceStore (JSON)
    db.py                ← DraftsDB (SQLite)
  platforms/             ← LI + FB token validators
  normalize/metrics.py   ← cross-platform metric normalizers
  routes/                ← workspace, events, generate, drafts, analytics, diagnose

web/
  app/
    onboard/page.tsx
    workspace/
      drafts/page.tsx
      analytics/page.tsx
      diagnose/page.tsx
    api/image/route.ts   ← local image proxy for server-generated PNGs
  components/            ← UI primitives + feature components
  lib/api.ts             ← typed client + SSE helpers

scripts/                 ← existing Aurevon scripts, reused unchanged
  prewarm_aurevon.py     ← NEW — pre-warm intelligence reports for demo
```

## If something breaks

- **Poller never polls:** confirm `server/routes/workspace.py:create_workspace` is `async def` and uses `asyncio.create_task`.
- **Push 400s:** confirm `LI_DEFAULT_CAMPAIGN_ID` / `FB_DEFAULT_ADSET_ID` are in `.env` and the server was restarted after edits.
- **Push fails after server restart with "token not set":** confirm `workspace/.tokens.env` exists and is being read by the startup loader (check server logs at boot — the loader is silent on success but populates `os.environ`). If the file is missing, re-onboard.
- **Chain trace doesn't show:** check browser network tab for the SSE connection. CORS issues will be visible there.
- **Hivemind 401s:** keys are scoped per-project. Confirm Aurevon's project_id is in the key's scope.
- **Image gen fails:** check OpenAI quota and `scripts/session_guard.py` cap state.
- **Image proxy returns 403:** path must resolve to under `<repo>/workspace/`. The image proxy now enforces this strictly.

## Spec deviations / decisions during build

- Plan called for some script functions that didn't exist (`update_campaign_status`, `pause_ad`). Real signatures (`update_creative_status`, `update_ad_status`) used instead.
- Plan said `style_index=None` for random image gen. Real signature requires `style_id: int`. Hardcoded to `1`.
- Push endpoint fell back to env-based default campaign/adset IDs instead of requiring them in the request body (avoids UI churn).
- Plan called for tier badges on draft cards — dropped per design refinement. Internal `tier` metadata drives the Enhance affordance only; no user-facing label.
- Audit removed the `LINKEDIN_TOKEN` / `FACEBOOK_TOKEN` intermediate env names and the `token_ref` workspace field — onboarding now writes the canonical names that `scripts/*.py` already expect.
