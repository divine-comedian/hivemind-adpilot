# Hackathon Submission Fields

## Project Name
AdPilot

## Tracks
Marketing Automations

## Summary
Hivemind-powered paid-ads operator. Paste a URL; AdPilot creates a real Hivemind project (Hivemind handles scrape + AI extract + social + competitive intel server-side) and uses the `genius-strategist` and `ghostwriter` chat personas to generate, push, diagnose, and refresh paid creatives across LinkedIn and Facebook. Real spend data, real DRAFT/PAUSED creatives pushed to platforms.

## Workflow
1. User pastes a website URL. AdPilot calls `POST /api/v1/projects` with `{website_url}`. Hivemind returns 202 and runs enrichment (scrape → AI extract → social → intel reports) asynchronously. AdPilot starts polling `GET /api/v1/projects/:id` until `enrichment_status: ready`.
2. User lands on Drafts immediately and can generate ads without waiting on enrichment (Tier A — `projectId` is set but reports aren't yet attached).
3. When `enrichment_status` flips to `ready`, an SSE `enrichment_ready` event fires. An "✨ Enhance with market intelligence" affordance appears on existing Tier-A drafts. One click regenerates the draft in Tier B — same chain, but now Hivemind auto-attaches the project's intel + social context via `projectId`.
4. The first time the user clicks Push on a draft, a slide-out panel collects LinkedIn or Facebook ad-platform credentials. Approved drafts push as PAUSED creatives.
5. Analytics aggregates 30-day perf across both platforms.
6. Diagnose runs the same two-call chain (Strategist → Ghostwriter) on recent perf — returns kill recommendations + replacement angles, each citing a specific Myosin framework.

## Hivemind Usage
- `POST /api/v1/projects` — every workspace is a real Hivemind project. Onboarding sends just `{website_url}`; Hivemind enriches the rest server-side.
- `GET /api/v1/projects/:id` — polled every 60s; SSE-pushes `enrichment_ready` (or `enrichment_failed`) to the UI on terminal status.
- `POST /api/v1/chat` (`persona: genius-strategist`) — project-scoped gap analysis. RAG retrieval + intel/social attachment happen server-side via `projectId`.
- `POST /api/v1/chat` (`persona: ghostwriter`) — per-angle copy drafting per platform.

Single generation = 1 Strategist call + 1 Ghostwriter call per (angle × platform). Single diagnose = same shape on perf data. Both rely on Hivemind's server-side RAG + intel attachment rather than client-side excerpt-passing.

## Demo URL
[Loom URL — add before submitting]

## Artifact URL
[GitHub repo URL]

## Product Opportunity
See README's "Product opportunity" section. Three concrete API gaps:

1. **No way to *explicitly attach* an Intelligence report to a single chat conversation.** Intel/social context is bundled implicitly through `projectId`, which is great for the common case, but offers no control over which report variant gets pinned. A `conversation.attach_report(report_id)` primitive would help.
2. **No webhook callback when project enrichment completes.** We poll `GET /projects/:id` every 60s. A webhook would cut server-side load and improve UX.
3. **No standard schema for grounding a Ghostwriter output in a specific framework name.** Today this is a `framework_cited` field by Strategist convention only — no first-class API support.

Beyond gaps: AdPilot is "what every Hivemind project gets" if Hivemind ships a first-party paid-ads operator. The Tier A/B graceful-degradation pattern generalizes to any feature that needs enrichment — it should never gate first-use.
