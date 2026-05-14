# AdPilot — Hivemind Hackathon Design Spec

**Date:** 2026-05-13
**Status:** Draft (pre-hack)
**Author:** Mitch + Claude
**Hackathon:** Hivemind Hackathon, Marketing Automations track (€150)
**Build window:** 14:30 May 13 → 09:00 May 14 (~18.5 hours, solo)
**Demo:** Aurevon Intelligence as the onboarded business

---

## 1. Overview

AdPilot is a Hivemind-powered paid-ads operator. A business onboards in under two minutes, the onboarding form doubles as Hivemind project creation, and from then on AdPilot runs the full paid-creative loop on top of that project's intelligence layer:

1. **Onboard** — short form → `POST /api/v1/projects` → store project_id, FB + LI tokens locally. Intelligence reports are kicked off async; **the user does not wait for them**.
2. **Generate (tier A — instant)** — runs immediately on user inputs + Myosin knowledge layer. Strategist + Ghostwriter chain drafts N angle concepts → image gen → preview grid. This is the wow-moment path, available the second onboarding completes.
3. **Generate (tier B — enhanced)** — once intelligence reports complete (typically minutes to ~1h after onboarding), the same chain re-runs with `competitive_intelligence` and `attention_landscape` injected as additional grounding. UI surfaces this as an upgrade, not a do-over.
4. **Push** — approved drafts get pushed to LinkedIn + Facebook as DRAFT/PAUSED ads (never auto-active).
5. **Aggregate** — cross-platform analytics pull, normalized into one view.
6. **Diagnose** — Strategist re-reads recent perf + the project's standing intelligence reports → recommends pauses, replacements, and new angles; user one-clicks each action. Same tier-A/tier-B graceful degradation: if reports aren't ready, diagnose runs on perf + knowledge layer alone.

The repo is currently Aurevon-only. This spec extracts the Aurevon parts behind a generic workspace abstraction so any business is a first-class input.

**Core design principle: never block on slow upstreams.** Intelligence reports can take up to an hour. The user gets full functionality on their inputs alone and intelligence flows in as a quiet enhancement when ready.

## 2. Why this wins on the rubric

The Marketing Automations track's strong-submission heuristic is *"chains multiple Hivemind calls, pulls specific frameworks from the knowledge layer, and produces output that could not exist without Hivemind."* AdPilot's generate and diagnose flows each chain 3-4 Hivemind calls and ground them in project-scoped intelligence reports.

| Criterion | Weight | How AdPilot scores |
|---|---|---|
| **Hivemind Depth** | 30% | Every creative is grounded in: (a) a project-scoped Intelligence report, (b) the Myosin knowledge layer (Narrative Health Audit, Ghostwriter frameworks), (c) the Strategist persona's diagnosis chain. Not a wrapper. |
| **Roadmap Viability** | 25% | Generic from day one. Multi-tenant rewrite is local-state-only, but every API call is already project-scoped. Hivemind could ship this as an integration tomorrow. |
| **Demo Clarity** | 20% | Live demo onboards Aurevon, runs the loop end-to-end on real spend data, pushes real DRAFT creatives to LinkedIn. 5-7 min, no mocks visible. |
| **Originality** | 25% | The strategist-loop framing for *paid creative ops* (not organic posts) is unclaimed in the brief exemplars. Closes a real gap. |

## 3. Goals & non-goals

### Goals

1. End-to-end loop: onboard → generate → preview → push → analytics → diagnose, working on Aurevon's real accounts.
2. Hivemind project creation is the onboarding step (not a side effect).
3. Every Strategist call is project-scoped and chained with at least one knowledge-layer retrieval.
4. UI is intentionally designed, not a default Tailwind starter — the editorial aesthetic reinforces the "strategist" framing.
5. Ships as a public GitHub repo + Loom screencast that an AI judge can ingest end-to-end.

### Non-goals

- Real multi-tenancy (auth, per-user storage, billing) — single-tenant local state.
- Lead-gen, video, carousel, story formats — single-image feed ads only.
- Auto-activation of ads — every push lands in DRAFT/PAUSED. Manual activation in the platform UI.
- Real-time perf updates — analytics is pull-on-demand.
- Mobile-responsive polish — desktop-only for the hackathon (note in README).

## 4. Demo narrative (5-7 minutes, scripted)

The judges see this exact sequence. Every step is real, not mocked.

1. **(0:30)** "I'm onboarding Aurevon Intelligence — a real business spending real money on FB and LinkedIn." Fill form: name, website, one-paragraph description, target audiences, geography, brand assets (logo + accent color). Paste FB + LI access tokens. Submit.
2. **(0:20)** Land on drafts page. "Notice — onboarding completed in seconds. The intelligence reports take up to an hour, but the product doesn't make me wait." Point at the brewing chip. Open the Refine panel: "I can keep shaping context while they run."
3. **(0:45)** Click Generate. "The Strategist Chain runs on my inputs plus Hivemind's knowledge layer right now — intelligence reports aren't in yet, but the product doesn't wait on them." Show 4-step trace: pull (skipped, no reports yet) → knowledge search → Strategist gap analysis → Ghostwriter drafts. Five draft cards appear.
4. **(0:45)** Hover a card → rationale panel showing which Myosin framework the angle leans on. Open one card's detail modal → show the full Strategist trace.
5. **(0:30)** "While I've been demo-ing, the reports came in." (Pre-warmed for Aurevon — the chip flips to ready on cue.) Soft banner: "Market intelligence is ready — 5 drafts can be enhanced." An ✨ Enhance affordance appears on each existing card. Click Enhance on one. A new card appears next to the original (faded, marked superseded) with a different rationale citing the `competitive_intelligence` report directly.
6. **(0:30)** "I approve these three." Click. "Push to LinkedIn." Receives real LinkedIn creative URNs back, links open in a new tab.
7. **(0:45)** Switch to Analytics tab. "This is Aurevon's last 30 days, normalized across both platforms." Aggregated metrics: spend, CPM, CTR, conversions, all platform-tagged. Shows the underperforming "intel gap" ad with 0 impressions.
8. **(1:15)** Click Diagnose. The Strategist Chain returns: kill these 2 ads with reasoning, here are 3 replacement angles citing why each fills the diagnosed gap (now leveraging the now-ready intelligence reports). One-click accept on each replacement → generates images → drops into Drafts.
9. **(0:15)** Wrap: "Onboarding to wow in seconds. Intelligence layer flows in quietly as it completes. The whole loop is project-scoped — any business that onboards gets the same Strategist trained on its own intelligence layer."

## 5. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Browser (Next.js + Tailwind)                  │
│  /onboard   /workspace/drafts   /workspace/analytics   /diagnose │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP (JSON)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  FastAPI sidecar (Python, localhost)             │
│  - /workspace          POST  create from onboarding form         │
│  - /workspace/me       GET   current workspace state             │
│  - /generate           POST  run Strategist Chain → drafts       │
│  - /drafts             GET   list drafts                         │
│  - /drafts/:id/push    POST  push to LinkedIn / Facebook         │
│  - /analytics          GET   normalized cross-platform pull      │
│  - /diagnose           POST  run diagnose Strategist Chain       │
│  - /diagnose/accept    POST  apply a diagnose recommendation     │
└──────┬─────────────────────┬────────────────────┬───────────────┘
       │                     │                    │
       ▼                     ▼                    ▼
┌──────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│  scripts/    │  │  scripts/hivemind.py│  │  workspace_state.   │
│  (existing)  │  │  (new)              │  │  json + SQLite      │
│              │  │                     │  │                     │
│  fb_*.py     │  │  - HivemindClient   │  │  Single-tenant      │
│  li_*.py     │  │  - StrategistChain  │  │  state. Tokens      │
│  gen_image   │  │  - DiagnoseChain    │  │  encrypted at rest. │
└──────────────┘  └─────────────────────┘  └─────────────────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │  Hivemind APIs      │
                  │  - /api/v1/projects │
                  │  - /api/v1/chat     │
                  │  - /api/knowledge   │
                  │  - /api/intelligence│
                  └─────────────────────┘
```

### Why the FastAPI sidecar

- Reuses every existing `scripts/*.py` module unchanged. No Python-in-TypeScript rewrite.
- Clean HTTP boundary keeps Next.js dev experience normal (fetch from React, no spawning subprocesses from API routes).
- Local-only — both processes run on `localhost`, no auth needed for the hackathon.
- Existing CLI scripts stay usable on their own — the sidecar is additive, not invasive.

### Why local state (not Supabase)

- Demo is single-business. Multi-tenancy is a roadmap point, not a demo point.
- Avoids 4-6h of auth/db setup that doesn't show on screen.
- SQLite + a JSON workspace file = real persistence without infrastructure.

## 6. The Strategist Chain (the Hivemind-depth play)

This is the heart of the submission. Every generation and diagnosis runs the chain below. Each step is a separate Hivemind call.

> **Day-of verification:** The brief references "Strategist", "Ghostwriter", and "GTM Architect" as Hivemind personas. The exact `/api/v1/chat` request shape (whether persona is a body param, a path param, or an agent_id) gets confirmed in the first 30 min from `hivemind.myosin.xyz/api-docs`. The chain structure is unchanged regardless — only the wire format adapts.

### Two tiers, same chain shape

Intelligence reports can take up to an hour to generate. The chain is designed so reports are an **optional grounding input**, not a hard dependency. The same chain runs in two tiers:

- **Tier A — Instant.** Runs without intelligence reports. Inputs: user-provided business context (description, audiences, voice notes, focus notes) + Myosin knowledge layer. Available the moment onboarding completes.
- **Tier B — Enhanced.** Runs after reports complete. Same chain plus `competitive_intelligence` + `attention_landscape` injected as Strategist context. Produces sharper, market-grounded angles. Surfaced in UI as an enhancement banner, never as a do-over.

The Strategist's system prompt explicitly handles both modes: in tier A it leans harder on the knowledge layer and the user's voice notes; in tier B it leads with intelligence-derived gaps.

### Generate-mode chain

```
Step 1. Intelligence pull (optional)
  GET  /api/intelligence/reports/:project_id/competitive_intelligence
  GET  /api/intelligence/reports/:project_id/attention_landscape
  If either report is unavailable (job pending/failed), proceed with intelligence=null.
  This step never blocks — generation does not wait on reports.

Step 2. Knowledge retrieval
  POST /api/knowledge/search
  query: "narrative health audit framework anti-patterns paid ads"
  → pulls Myosin frameworks the Strategist will lean on.
  In tier A this is the primary grounding signal.

Step 3. Strategist diagnosis (creative gap analysis)
  POST /api/v1/chat
  persona: "Strategist"
  input: {
    business_context: { description, audiences, voice_notes, focus_notes },
    intelligence_reports: { competitive: …|null, attention: …|null },  // optional
    current_active_ads: […]|[],                                          // optional
    knowledge_excerpts: [...]
  }
  → returns: { diagnosed_gaps: [...], opportunity_angles: [...], tier: "A" | "B" }
  System prompt tells Strategist: "If intelligence is null, ground gaps in knowledge
  layer + user-stated audience. If intelligence is present, lead with it."

Step 4. Ghostwriter draft (per angle)
  POST /api/v1/chat
  persona: "Ghostwriter"
  input: { angle, project_voice, format: linkedin_feed | fb_feed }
  → returns: { headline, body, cta, image_prompt, rationale }
```

### Diagnose-mode chain

```
Step 1. Performance pull
  Local: scripts/li_analytics + scripts/fb_insights — last 30 days, all active ads.

Step 2. Intelligence pull (optional)
  Same as Generate step 1. If unavailable, proceed with intelligence=null.

Step 3. Strategist diagnosis
  POST /api/v1/chat
  persona: "Strategist"
  input: { performance_data, intelligence_reports?, active_creative_copy, knowledge_excerpts }
  → returns: { kill_recommendations: [...], replacement_angles: [...], tier: "A" | "B" }

Step 4. Ghostwriter draft (per replacement)
  Same as Generate-mode step 4.
```

### Background enhancement loop

The sidecar polls `GET /api/intelligence/jobs/:job_id` every 60 seconds while a job is non-terminal. When a job completes:

1. Update workspace state report status.
2. SSE-push `{ type: "intelligence_ready", report_type: "competitive_intelligence" }` to any connected UI.
3. Drafts page surfaces a banner: "Market intelligence is ready. Existing drafts were generated on your inputs alone — regenerate to ground them in competitive context."

We do not auto-regenerate. The user owns the decision. This is the "quietly enhance when ready" behavior.

**What makes this "leveraging" not "wrapping":** every chain pulls from project-scoped intelligence (when available) plus the knowledge layer (always), every diagnosis references a named Myosin framework, and the output is a concrete action (push this, kill that) — not advice the user has to interpret. The graceful tier-A/tier-B degradation is itself a "leveraging" move: it shapes the Strategist's behavior conditionally on which Hivemind signals are ready.

## 7. Pages

### 7.1 `/onboard` — Onboarding wizard

Single page, 3 sections stacked vertically (no multi-step routing — single-form for demo speed).

**Section A: Business basics**
- Business name (text)
- Website URL (text)
- One-paragraph description (textarea, 1-2000 chars — passed to Hivemind as the project's `description`)
- Target audiences (chip input, max 5)
- Target geographies (chip input, max 5)
- Project stage (select: seed / growth / mature)

**Section B: Brand**
- Logo upload (PNG with transparency, drag-drop)
- Accent color picker (single hex)
- Voice notes (textarea, optional — passed into Ghostwriter as voice grounding)

**Section C: Ad platform access**
- LinkedIn access token (password input)
- LinkedIn ad account ID (text)
- LinkedIn org URN (text)
- Facebook access token (password input)
- Facebook ad account ID (text)
- Facebook Page ID (text)
- Validate-on-blur for each — green check or red error before submit is allowed.

**On submit:**
1. `POST /workspace` → FastAPI does (in this exact order, fast steps first):
   1. Validate LI + FB tokens by calling each platform's `/me` endpoint.
   2. `POST /api/v1/projects` to Hivemind (passes name, description, website_url, categories, audiences, geographies, stage).
   3. Persist workspace state to disk.
   4. Return 201 to the client **immediately** — the user proceeds to the drafts page now.
   5. **In a background task** (after the response is sent): `POST /api/intelligence/reports/generate` for `competitive_intelligence` and `attention_landscape`, then start the polling loop.
2. Redirect to `/workspace/drafts`. A small status chip in the header reads "Market intelligence: brewing" and updates when reports complete. The user can generate immediately — first generation runs in tier A.

### Optional: "Refine your angle" panel (post-onboarding)

While reports are brewing, the drafts page exposes a small editable panel where the user can add `focus_notes` — free-text context that gets fed into every Strategist call (e.g. "we're trying to crack enterprise buyers", "competitor X just launched feature Y"). This gives the user something productive to do during the wait without feeling stuck, and the input compounds into every generation.

### 7.2 `/workspace/drafts` — Drafts + Generate

Two-column layout. Left rail: workspace switcher (just one for demo) + nav. Main column: header with primary CTA "Generate new drafts", intelligence status chip, and drafts grid.

**Header status chip** — small, top-right of the header:
- *Brewing:* "Market intelligence: brewing" with a soft pulse animation. Tooltip: "Competitive intelligence and attention landscape reports take up to an hour. Generations run on your inputs alone until they're ready."
- *Ready:* "Market intelligence: ready" in positive moss. Persistent for the rest of the session; on first transition to ready, also fires a soft banner above the drafts grid: "New ground-truth signal available. Regenerate any draft to ground it in market intelligence." Banner is dismissable.

**Generate action** — opens a side panel:
- Platform target (LinkedIn / Facebook / Both — default Both)
- Number of angles (slider, 3-8)
- Optional: "focus on" textarea (mirrors the workspace `focus_notes` panel — local override per generation)
- Submit → runs Strategist Chain, shows live progress trace (each chain step lights up as it completes).

**Drafts grid:**
- Each draft card: image preview (5:4 ratio), headline (display serif), body (small), CTA badge, platform badge, status badge (Draft / Pushed).
- Hover: card lifts, "Rationale" panel slides in from the right showing the Strategist's reasoning.
- Click: detail modal with full Strategist trace, regenerate-image button, edit copy fields, push button.

**Enhance affordance** (the action surface that replaces tier badges):
- Drafts generated *before* intelligence was ready get an inline action on the card: *"✨ Enhance with market intelligence"*.
- Action appears only when intelligence is ready, only on eligible drafts (no `parent_draft_id` chain tying them to a tier-B run).
- One click → runs the chain in tier B for that draft → new draft appears with `parent_draft_id` pointing at this one. Original is marked `superseded` but kept visible (faded) so the user can compare.
- Action disappears once the draft is enhanced or explicitly dismissed.
- We never label a draft "Tier A" or "lower-tier" — the affordance is forward-looking ("you can make this better"), not backward-looking ("this is lesser").

**Refine focus panel** — collapsible card below the header (collapsed by default):
- Textarea bound to `workspace.business.focus_notes`.
- Auto-saves on blur.
- A small line above the textarea: "This context feeds into every generation."

**Push action** — single button per draft, two-step confirm.

### 7.3 `/workspace/analytics` — Cross-platform performance

Single page, four sections.

**Section A: Top-line cards (4-up)**
- Total spend (last 30d), CPM, CTR, Conversions. Each card shows current value, delta vs. previous 30d, sparkline.

**Section B: Per-ad performance table**
- Sortable table: Ad name, Platform badge, Status, Impressions, Clicks, CTR, Spend, CPM, Conversions, Created at.
- Rows colored: green (top decile), red (bottom decile by CTR with spend > threshold).
- Click row → opens detail drawer.

**Section C: Platform comparison**
- Two-column side-by-side: LinkedIn vs Facebook, same metric set. Highlights which platform is performing better per metric.

**Section D: CTA**
- Prominent "Diagnose with Strategist" button at bottom.

### 7.4 `/workspace/diagnose` — Strategist recommendations

Linear page, top to bottom:

**Section A: The Diagnosis**
- Strategist's narrative summary at the top, large, editorial. 2-3 paragraphs.
- Quote a specific Myosin framework explicitly (with citation chip).

**Section B: Kill recommendations**
- Card list. Each card: the underperforming ad, its current perf numbers, the Strategist's reasoning, an "Approve pause" button.
- Approving calls the platform API to pause the ad and logs the action.

**Section C: Replacement angles**
- Same card pattern as drafts grid, but each card has a "Why this angle" panel surfacing the gap it addresses.
- "Accept all" or per-card "Accept and generate" — accepted angles run through Ghostwriter + image gen and land in Drafts.

## 8. Visual design system

The hackathon's Originality criterion (25%) rewards distinctive choices. Default-Tailwind-SaaS is the AI-slop trap. The visual direction below is intentional: **Editorial Confidence** — the aesthetic of a strategist's working notebook, not a marketing dashboard.

### Aesthetic direction

- **Mood:** Warm-paper background, deep-ink foreground, a single sharp accent. Bloomberg Businessweek meets a designer's notebook. Generous negative space. Numbers in monospace tabular figures so analytics rows align without jitter.
- **Anti-patterns:** No purple-to-blue gradients. No Inter as display. No bento-grid soft-shadow cards. No glassmorphism. No emoji.
- **Texture:** Subtle paper-grain noise on the body background (`background-image: noise.svg, opacity 0.02`). Borders are 1px warm-gray hairlines, not soft shadows.

### Typography

| Role | Font | Weights | Notes |
|---|---|---|---|
| Display | Fraunces | 400 (italic for emphasis), 600 | Variable serif. Use optical-sizing for large headings. |
| Body | Geist | 400, 500, 600 | Modern grotesque, distinctive without being Inter. |
| Mono / numerals | JetBrains Mono | 400, 500 | Tabular figures everywhere numbers appear. |

Type scale (px): 12, 14, 16, 18, 22, 28, 38, 56. Line-height 1.5 for body, 1.15 for display.

### Color tokens

```css
:root {
  /* Surfaces */
  --paper:        #F7F3EC;  /* page background, warm off-white */
  --surface:      #FFFFFE;  /* cards */
  --ink:          #1A1714;  /* primary text */
  --ink-muted:    #5C544A;  /* secondary text */
  --hairline:     #E5DDD0;  /* borders, dividers */

  /* Signal */
  --accent:       #BE3A2C;  /* oxide red — primary CTA, brand */
  --accent-soft:  #F5E0DC;  /* accent surface */
  --positive:     #2F7D52;  /* deep moss — winning ads */
  --negative:     #8C2A1F;  /* deep oxide — underperformers, destructive */
  --highlight:    #E8B449;  /* saffron — attention, "diagnose" */
}
```

All foreground/background pairs target WCAG AA (≥4.5:1 for body, ≥3:1 for large text). Verify each pair with a contrast checker during build before locking the tokens.

### Spatial system

- 4px base unit. Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64, 96.
- Page max-width: 1200px (centered, no rails). Page padding: 48px on desktop.
- Card padding: 24px. Grid gap: 24px.

### Motion

- 180ms ease-out for hover lifts. 260ms ease-out for slide-ins.
- Strategist Chain trace: each step fades + slides 8px on completion (staggered 80ms).
- `prefers-reduced-motion`: disables transforms, keeps fades.

### Critical UI rules (from ui-ux-pro-max checklist)

- All icons from Lucide (single icon family). No emoji.
- Focus rings: 2px solid accent, 2px offset.
- All buttons ≥40px tall. Touch targets ≥44px on interactive cards.
- Forms: label above input (not placeholder-only). Helper text below in 12px ink-muted. Errors inline below the field in negative.
- Loading: skeletons for grids, inline spinner only for ≤1s operations.
- Empty states: short copy + a single primary action.

## 9. API surface (FastAPI sidecar)

All endpoints local, no auth. Request/response JSON.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/workspace` | Create from onboarding form. Creates Hivemind project, kicks off intelligence reports, stores tokens. |
| `GET` | `/workspace/me` | Current workspace state including report job statuses. |
| `POST` | `/generate` | Run Strategist Chain (generate mode). Body: `{ platforms, count, focus_note }`. Returns drafts. Streams chain trace via SSE. |
| `GET` | `/drafts` | List all drafts with status. |
| `GET` | `/drafts/:id` | Single draft with full Strategist trace. |
| `PATCH` | `/drafts/:id` | Edit headline/body/CTA. |
| `POST` | `/drafts/:id/regenerate-image` | Re-run image gen for that draft. |
| `POST` | `/drafts/:id/push` | Push to platform. Body: `{ platform: "linkedin" \| "facebook", campaign_id }`. Returns URN. |
| `GET` | `/analytics` | Normalized cross-platform metrics. Query: `?window=30d`. |
| `POST` | `/diagnose` | Run Strategist Chain (diagnose mode). Returns kill list + replacement angles. Streams trace via SSE. |
| `POST` | `/diagnose/accept` | Body: `{ action: "kill" \| "replace", target_id, replacement_angle_id }`. Executes the action. |
| `GET`  | `/workspace/events` | SSE stream. Pushes `intelligence_ready`, `report_failed`, and other workspace-level state changes. |
| `POST` | `/drafts/:id/regenerate` | Re-run Strategist Chain for this draft. Forces tier B if intelligence is ready. Creates a new draft with `parent_draft_id` set to this one. |

### Streaming the Strategist Chain trace

The generate and diagnose endpoints both stream Server-Sent Events so the frontend can show the chain steps lighting up. Event shape:

```
event: chain_step
data: { "step": "intelligence_pull", "status": "running" }

event: chain_step
data: { "step": "intelligence_pull", "status": "complete", "elapsed_ms": 1240 }

event: result
data: { "drafts": [...] }
```

## 10. Data model

### `workspace_state.json` (single workspace)

```json
{
  "workspace_id": "ws_aurevon_demo",
  "business": {
    "name": "Aurevon Intelligence",
    "website": "https://aurevon.ca",
    "description": "...",
    "audiences": ["sports-bettors", "data-curious"],
    "geographies": ["CA", "US"],
    "stage": "seed",
    "focus_notes": ""
  },
  "brand": {
    "logo_path": "workspace/logo.png",
    "accent_hex": "#F26B1F",
    "voice_notes": "..."
  },
  "hivemind": {
    "project_id": "uuid",
    "reports": {
      "competitive_intelligence": {
        "job_id": "...",
        "status": "queued | in_progress | completed | completed_partial | completed_healed | failed",
        "queued_at": "...",
        "completed_at": "...",
        "last_synced_at": "..."
      },
      "attention_landscape": { /* same shape */ }
    }
  },
  "platforms": {
    "linkedin": { "account_id": "...", "org_urn": "...", "token_ref": "LINKEDIN_TOKEN" },
    "facebook": { "account_id": "...", "page_id": "...", "token_ref": "FACEBOOK_TOKEN" }
  },
  "created_at": "2026-05-13T14:30:00Z"
}
```

Tokens are stored in `workspace/.tokens.env` (gitignored), not in the JSON file. The state file references them by key name. For the hackathon this is sufficient; productionizing this is a roadmap line item.

### SQLite (`workspace.db`) — drafts, pushes, diagnoses

```
drafts (
  id TEXT PRIMARY KEY,
  workspace_id TEXT,
  created_at TIMESTAMP,
  platform TEXT,           -- linkedin | facebook
  headline TEXT,
  body TEXT,
  cta TEXT,
  image_path TEXT,
  rationale TEXT,
  strategist_trace JSON,    -- full chain output
  source TEXT,              -- generate | diagnose
  source_angle_id TEXT,     -- ties back to the angle in the trace
  tier TEXT,                -- A | B (internal metadata; drives the enhance affordance, never shown as a label)
  parent_draft_id TEXT,     -- when regenerated, points at the prior version
  status TEXT               -- draft | pushed | discarded | superseded
)

pushes (
  id TEXT PRIMARY KEY,
  draft_id TEXT,
  pushed_at TIMESTAMP,
  platform TEXT,
  external_urn TEXT,
  external_url TEXT
)

diagnoses (
  id TEXT PRIMARY KEY,
  workspace_id TEXT,
  created_at TIMESTAMP,
  performance_snapshot JSON,
  strategist_trace JSON,
  killed_ad_ids JSON,
  accepted_replacement_ids JSON
)
```

## 11. File structure (additions to existing repo)

```
aurevon-ads/                       # existing root
├── scripts/                       # existing — unchanged
│   ├── fb_*.py
│   ├── li_*.py
│   ├── generate_image.py
│   └── config.py                 # extended: reads workspace_state.json
├── server/                        # NEW — FastAPI sidecar
│   ├── main.py                   # FastAPI app, route registration
│   ├── routes/
│   │   ├── workspace.py
│   │   ├── generate.py
│   │   ├── drafts.py
│   │   ├── analytics.py
│   │   └── diagnose.py
│   ├── hivemind/
│   │   ├── client.py             # HivemindClient (chat, knowledge, intelligence, projects)
│   │   ├── strategist_chain.py   # Generate-mode chain
│   │   └── diagnose_chain.py     # Diagnose-mode chain
│   ├── store/
│   │   ├── workspace.py          # workspace_state.json I/O
│   │   └── db.py                 # SQLite ops for drafts/pushes/diagnoses
│   └── normalize/
│       ├── li_metrics.py         # LinkedIn → normalized
│       └── fb_metrics.py         # Facebook → normalized
├── web/                          # NEW — Next.js app
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx              # redirect → /onboard or /workspace/drafts
│   │   ├── onboard/page.tsx
│   │   └── workspace/
│   │       ├── drafts/page.tsx
│   │       ├── analytics/page.tsx
│   │       └── diagnose/page.tsx
│   ├── components/
│   │   ├── DraftCard.tsx
│   │   ├── StrategistTrace.tsx
│   │   ├── OnboardForm.tsx
│   │   ├── AnalyticsTable.tsx
│   │   └── ui/                   # buttons, inputs, badges
│   └── lib/
│       ├── api.ts                # typed client to FastAPI
│       └── sse.ts                # SSE consumer
├── workspace/                    # NEW — runtime state (gitignored)
│   ├── workspace_state.json
│   ├── workspace.db
│   ├── logo.png
│   └── drafts/                   # generated images
├── README.md                     # NEW or rewrite — demo walkthrough for AI judges
└── HACKATHON.md                  # NEW — submission notes, product opportunity
```

## 12. Build sequence (14-16h target)

| Phase | Work | Est | Cumulative |
|---|---|---|---|
| 1 | FastAPI sidecar scaffold + reuse existing scripts via clean imports | 1.5h | 1.5h |
| 2 | `HivemindClient` wrapper (chat, knowledge, intelligence, projects) | 1.5h | 3h |
| 3 | StrategistChain + DiagnoseChain implementations with tier-A/tier-B branching | 2h | 5h |
| 4 | Background intelligence-polling task + `/workspace/events` SSE stream | 1h | 6h |
| 5 | Next.js scaffold, fonts, color tokens, base components (Button, Card, Badge) | 1.5h | 7.5h |
| 6 | `/onboard` page + `POST /workspace` returns fast, kicks off reports in background | 2h | 9.5h |
| 7 | `/workspace/drafts` page: brewing chip, refine panel, SSE trace, push action, regenerate | 3h | 12.5h |
| 8 | `/workspace/analytics` page + `GET /analytics` normalized pull | 1.5h | 14h |
| 9 | `/workspace/diagnose` page + `POST /diagnose` + accept actions | 1.5h | 15.5h |
| 10 | Demo prep: README walkthrough, Loom screencast, submission form fields | 1.5h | 17h |

Buffer: ~1.5h for blockers (17h sequence in an 18.5h window). Cuts in order if behind: drop platform comparison (Section C of analytics) → drop in-place edit on drafts → drop the enhance affordance (still show the brewing/ready chip, just no per-draft enhance) → drop Facebook push (LinkedIn only) → drop the diagnose page entirely.

**Why the brewing/ready chip is the *last* thing cut:** it's the visible expression of the core design principle (never block on slow upstreams) and the cleanest "this is real product thinking, not a demo trick" signal to judges.

## 13. Demo artifacts

Per the brief, judges are AI and need readable artifacts.

- **Artifact URL:** Public GitHub repo with a README that walks through the loop with screenshots and a Loom embed. The README also describes the Strategist Chain in plain language with a sequence diagram.
- **Demo URL:** Loom screencast of the 5-7 min flow. Includes timestamps in the description so a judge can jump to the Strategist Chain reveal.
- **Hivemind Usage section of submission:** Explicitly list every Hivemind API call and what it grounds. Quote one Strategist Chain output verbatim so the judge sees the depth.
- **Product Opportunity section:** "AdPilot is what happens when every Hivemind project gets a paid-ads operator built on its intelligence layer. The gap we encountered: there's no first-class way to pin a Ghostwriter conversation to an Intelligence report — we had to pass excerpts in-prompt. A `conversation.attach_report(report_id)` primitive would let downstream tools chain intelligence + chat without re-passing context every call."

## 14. Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Intelligence report takes too long during live demo | Now structural | Tier A/B graceful degradation handles this by design. The demo deliberately shows the wait + the quiet enhancement moment. Pre-warm Aurevon's reports beforehand for the tier-B reveal at the right beat. |
| User perceives pre-intelligence drafts as low-quality | Low | Drafts are not labeled with a tier. The enhance affordance is a forward-looking action ("make this better"), never a backward-looking quality label. The internal `tier` field is metadata that drives the affordance, not UI copy. |
| Background polling leaks / never stops | Medium | Polling task tracks all in-flight job IDs and exits once each is terminal (completed/failed). Sidecar shutdown cleans up tasks. |
| FB or LinkedIn token expires mid-demo | Medium | Refresh both tokens day-of. Have a backup recorded demo of the push step. |
| Hivemind chat rate-limited during demo | Low | Strategist Chain is 4 calls per generation; rate limit is per-minute. Stage at least one pre-recorded run. |
| Next.js + Tailwind setup eats more time than budgeted | Medium | Use Next.js 15 with `create-next-app --tailwind`. Pre-build the 4 page shells before adding logic. |
| FastAPI ↔ Next.js CORS issues | Low | Set `CORSMiddleware(allow_origins=["http://localhost:3000"])` from minute one. |
| Image gen rate-limit on OpenAI | Low | Existing `session_guard.py` already enforces caps. Pre-generate images for demo drafts as fallback. |
| Try to add too much polish, ship incomplete | High | Hard checkpoint at hour 12 (~02:30): if Phase 8 not started, cut diagnose-mode and ship generate + analytics only. |

## 15. What we're explicitly not building (defended)

- **Auth / multi-user.** Single-tenant local state. Multi-tenancy is a roadmap point.
- **Scheduled cron runs.** Manual trigger only for the demo. Cron is a one-config-line add post-hackathon.
- **In-place ad editing in the platform.** Push is one-way: draft goes out as DRAFT/PAUSED, user activates in LinkedIn/Facebook UI.
- **A/B test orchestration.** Not in scope. Drafts are pushed as separate creatives; rotation logic stays in the existing scripts.
- **Mobile responsive.** Desktop-only for the hackathon. Note in README.

## 16. Naming

Working name: **AdPilot**. Open to renaming during build. The submission can ship as AdPilot or any name the user prefers — naming is decoupled from the architecture.

---

*End of spec.*
