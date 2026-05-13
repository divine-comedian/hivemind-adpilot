# Hackathon Submission Fields

## Project Name
AdPilot

## Tracks
Marketing Automations

## Summary
Hivemind-powered paid-ads operator. Bring a business; onboarding creates a Hivemind project and AdPilot runs a multi-call Strategist Chain on top of the project's intelligence layer to generate, push, diagnose, and refresh paid creatives across LinkedIn and Facebook. Real spend data, real DRAFT creatives pushed to platforms.

## Workflow
1. User onboards a business in a 3-section form. Onboarding creates a real Hivemind project via `POST /api/v1/projects` and kicks off `competitive_intelligence` + `attention_landscape` reports.
2. User immediately lands on Drafts and can generate ads without waiting on reports (Tier A — runs on user inputs + Myosin knowledge layer).
3. When reports complete (typically minutes to ~1h), an "✨ Enhance with market intelligence" affordance appears on existing drafts. One click regenerates the draft in Tier B with intelligence-grounded reasoning.
4. Approved drafts push to LinkedIn / Facebook as DRAFT/PAUSED creatives.
5. Analytics aggregates 30-day perf across both platforms.
6. Diagnose runs the Strategist Chain on recent perf — returns kill recommendations + replacement angles, each citing a specific Myosin framework.

## Hivemind Usage
- `POST /api/v1/projects` — every workspace is a real Hivemind project.
- `POST /api/intelligence/reports/generate` (competitive_intelligence + attention_landscape) — kicked off async during onboarding.
- `GET /api/intelligence/jobs/:id` — polled every 60s; SSE-pushes `intelligence_ready` to the UI on completion.
- `GET /api/intelligence/reports/:project_id/:type` — pulled at the top of every Strategist Chain run.
- `POST /api/knowledge/search` — pulls Myosin frameworks (Narrative Health Audit, etc.) as Strategist grounding.
- `POST /api/v1/chat` — Strategist persona for gap analysis (project-scoped); Ghostwriter persona for per-angle copy drafting.

Single generation = 4 chained Hivemind calls. Single diagnose = same. Both grounded in project-scoped intelligence (when ready) plus the knowledge layer.

## Demo URL
[Loom URL — add before submitting]

## Artifact URL
[GitHub repo URL]

## Product Opportunity
See README's "Product opportunity" section. Three concrete API gaps:

1. **No way to attach an Intelligence report to a chat conversation.** We currently pass excerpts in-prompt. A `conversation.attach_report(report_id)` primitive would let downstream tools chain intelligence + chat without re-passing context every call.
2. **No webhook callback when an intelligence job completes.** We poll `/jobs/:id` every 60s. A webhook would cut server-side load and improve UX.
3. **No standard schema for grounding a Ghostwriter output in a specific framework name.** The Strategist had to do framework retrieval and pass excerpts through manually.

Beyond gaps: AdPilot is "what every Hivemind project gets" if Hivemind ships a first-party paid-ads operator. The Tier A/B graceful-degradation pattern generalizes to any feature that needs Intelligence reports — they should never gate first-use.
