# AdPilot

A Hivemind-powered paid-ads operator. Bring a business; AdPilot creates a Hivemind project, runs a multi-step Strategist Chain on top of the project's intelligence layer, and produces ready-to-push LinkedIn and Facebook ad drafts. Built for the Myosin Hivemind Hackathon — Marketing Automations track.

## What this submission demonstrates

- **Hivemind Depth:** Every generation chains four Hivemind calls: `intelligence_get_report` (competitive + attention) → `knowledge_search` (Myosin frameworks) → `chat(Strategist)` for gap analysis → `chat(Ghostwriter)` per angle.
- **Roadmap Viability:** Every workspace is a real Hivemind project. The whole loop is project-scoped from day one.
- **Originality:** First Hivemind-loop framing for *paid creative ops* (not organic posts). The two-tier degradation (instant Tier A when reports are pending, quiet Tier B enhancement when ready) is the core design move.
- **Demo Clarity:** 5-7 min Loom screencast at the link below.

## Live demo

- **Loom walkthrough:** [URL to be added before submission]
- **Source:** this repository

## Architecture

- **Frontend:** Next.js 15 + Tailwind v4, custom editorial design system (Fraunces serif + Geist sans + JetBrains Mono).
- **Sidecar:** FastAPI on `localhost:8000` with SSE streams for the chain trace and workspace events.
- **Reused:** all existing `scripts/*.py` modules for FB/LI campaign create + image generation — no rewrite.

## The Strategist Chain

Verbatim trace structure from a chain run:

```
chain_step intelligence_pull    running
chain_step intelligence_pull    complete  {"present": true}
chain_step knowledge_search     running
chain_step knowledge_search     complete  {"hits": 5}
chain_step strategist_diagnosis running
chain_step strategist_diagnosis complete  {"tier": "B", "angles": 5}
chain_step ghostwriter_drafts   running
chain_step ghostwriter_drafts   complete  {"count": 10}
result                                    {"drafts": [...]}
```

## Two-tier graceful degradation

Intelligence reports can take up to one hour to generate. The user does not wait:

- **Tier A** — runs the moment onboarding completes. Inputs: user-provided business context + Myosin knowledge layer.
- **Tier B** — runs after intelligence reports complete. Same chain plus `competitive_intelligence` + `attention_landscape` as Strategist context.

When intelligence becomes ready, eligible drafts get an `✨ Enhance with market intelligence` action that regenerates them in Tier B. No backward-looking quality labels — the affordance is forward-looking.

## Hivemind APIs used

| Endpoint | When | Why |
|---|---|---|
| `POST /api/v1/projects` | Onboarding | Every workspace is a real Hivemind project. |
| `POST /api/intelligence/reports/generate` | Onboarding (background task) | Kicks off competitive_intelligence + attention_landscape. |
| `GET /api/intelligence/jobs/:id` | Every 60s while pending | Poller updates state, SSE-pushes `intelligence_ready`. |
| `GET /api/intelligence/reports/:project_id/:type` | Start of every chain | Optional — chain proceeds with `None` if pending. |
| `POST /api/knowledge/search` | Every chain | Pulls Myosin frameworks (Narrative Health Audit, etc.). |
| `POST /api/v1/chat` (Strategist) | Generate + Diagnose | Project-scoped gap analysis. |
| `POST /api/v1/chat` (Ghostwriter) | Generate + Diagnose | Per-angle copy drafting. |

Single generation = 4 chained Hivemind calls. Single diagnose = same. Both grounded in project-scoped intelligence (when ready) plus the knowledge layer.

## Product opportunity (gaps found during the build)

- `/api/v1/chat` has no first-class way to *attach* a project's Intelligence report to a conversation. We pass excerpts in-prompt. A `conversation.attach_report(report_id)` primitive would let downstream tools (like AdPilot) chain intelligence + chat without re-passing context every call.
- Intelligence jobs lack a webhook callback. We poll every 60s. A webhook would cut server-side load and improve UX.
- No standard schema for "ground a Ghostwriter output in a specific framework name" — the Strategist had to do framework retrieval and pass excerpts through manually.

## Run locally

```bash
# 1. Fill .env (see .env.example)
#    HIVEMIND_API_KEY=
#    HIVEMIND_INTELLIGENCE_API_KEY=
#    HIVEMIND_BASE_URL=https://hivemind.myosin.xyz
#    OPENAI_API_KEY=
#    LINKEDIN_ACCESS_TOKEN=
#    FACEBOOK_ACCESS_TOKEN=

# 2. Python sidecar
pip install -r requirements.txt
uvicorn server.main:app --port 8000

# 3. Next.js (separate terminal)
cd web && npm install && npm run dev

# 4. Open http://localhost:3000 — redirects to /onboard
```

## Project structure

```
aurevon-ads/                       # this repo
├── scripts/                       # existing Python modules — reused unchanged
│   ├── li_*.py                   # LinkedIn analytics + campaign
│   ├── fb_*.py                   # Facebook insights + campaign
│   └── generate_image.py         # OpenAI image gen + compositing
├── server/                        # FastAPI sidecar
│   ├── main.py                   # app + CORS + routers
│   ├── deps.py                   # lazy singletons
│   ├── models.py                 # Pydantic models
│   ├── events.py                 # in-process pub/sub
│   ├── hivemind/
│   │   ├── client.py             # HivemindClient — 6 API methods
│   │   ├── strategist_chain.py   # 4-call chain, tier A/B branching
│   │   ├── diagnose_chain.py     # Diagnose chain on perf data
│   │   ├── poller.py             # Intelligence job poller
│   │   ├── prompts.py            # Strategist + Ghostwriter + Diagnose system prompts
│   │   └── types.py
│   ├── store/
│   │   ├── workspace.py          # WorkspaceStore (JSON)
│   │   └── db.py                 # DraftsDB (SQLite)
│   ├── platforms/                # Token validators + push wrappers
│   ├── normalize/                # Cross-platform metric normalization
│   └── routes/
│       ├── workspace.py          # POST /workspace, GET /workspace/me, PATCH focus
│       ├── events.py             # SSE /workspace/events
│       ├── generate.py           # SSE /generate
│       ├── drafts.py             # CRUD + push + regenerate
│       ├── analytics.py          # GET /analytics
│       └── diagnose.py           # SSE /diagnose + POST /diagnose/accept
├── web/                          # Next.js 15 frontend
│   ├── app/
│   │   ├── onboard/page.tsx
│   │   ├── workspace/
│   │   │   ├── drafts/page.tsx
│   │   │   ├── analytics/page.tsx
│   │   │   └── diagnose/page.tsx
│   │   └── api/image/route.ts    # local image proxy
│   ├── components/               # UI primitives + feature components
│   └── lib/api.ts                # typed client + SSE helpers
├── tests/                        # pytest tests for server modules
└── docs/
    ├── specs/2026-05-13-adpilot-hackathon-design.md
    └── superpowers/plans/2026-05-13-adpilot-hackathon.md
```

## License

Hackathon submission. Code under repo's existing license.
