# AdPilot

A Hivemind-powered paid-ads operator. Paste a website URL; Hivemind enriches the project (scrape + AI extract + social + competitive intel) in the background while AdPilot generates LinkedIn and Facebook ad drafts on top of the persona-driven chat API. Built for the Myosin Hivemind Hackathon — Marketing Automations track.

## What this submission demonstrates

- **Hivemind Depth:** Every generation runs through two persona-forced chat calls — `genius-strategist` for gap analysis, then `ghostwriter` per (angle × platform). Project enrichment, RAG retrieval, and intel attachment all happen server-side via `projectId`, so the chain stays focused.
- **Roadmap Viability:** Every workspace is a real Hivemind project. The whole loop is project-scoped from day one.
- **Originality:** First Hivemind-loop framing for *paid creative ops* (not organic posts). Two-tier graceful degradation (Tier A while enrichment is running, Tier B once it lands) is the core design move.
- **Demo Clarity:** 5-7 min Loom screencast at the link below.

## Live demo

- **Loom walkthrough:** [URL to be added before submission]
- **Source:** this repository

## Architecture

- **Frontend:** Next.js 15 + Tailwind v4, custom editorial design system (Fraunces serif + Geist sans + JetBrains Mono).
- **Sidecar:** FastAPI on `localhost:8000` with SSE streams for the chain trace and workspace events.
- **Reused:** all existing `scripts/*.py` modules for FB/LI campaign create + image generation — no rewrite.

## The chain

Verbatim trace structure from a generation run:

```
chain_step strategist   running   {"tier": "A"}
chain_step strategist   complete  {"tier": "A", "angles": 5}
chain_step ghostwriter  running
chain_step ghostwriter  complete  {"count": 10}
result                            {"drafts": [...], "tier": "A"}
```

Two persona-forced chat calls per generation. Hivemind's chat pipeline performs intent classification, RAG retrieval, social context fetch, and intel-report attachment server-side when a `projectId` is supplied — so the visible chain is short and the work is real.

## Two-tier graceful degradation

Project enrichment (Puppeteer scrape → AI extract → social scrape → intel side-effects) typically completes in a few minutes. The user does not wait:

- **Tier A** — runs the moment onboarding completes. The persona is forced but the project intel isn't yet attached; Hivemind's RAG layer carries the framework grounding.
- **Tier B** — runs once `enrichment_status` flips to `ready`. Same chain; Hivemind now attaches the project's intel + social context to every chat call via `projectId`.

When enrichment is ready, eligible drafts get an `✨ Enhance with market intelligence` action that regenerates them in Tier B. The affordance is forward-looking — no backward-looking quality labels.

## Hivemind APIs used

| Endpoint | When | Why |
|---|---|---|
| `POST /api/v1/projects` | Onboarding | Just a URL; Hivemind runs the rest of enrichment async. |
| `GET /api/v1/projects/:id` | Every 60s while enriching | Poller flips to `enrichment_ready` SSE on terminal status. |
| `POST /api/v1/chat` (`persona: genius-strategist`) | Generate + Diagnose | Project-scoped gap analysis. RAG + intel attached server-side. |
| `POST /api/v1/chat` (`persona: ghostwriter`) | Generate + Diagnose | Per-angle copy drafting per platform. |

Single generation = `1 + N×P` chat calls (one Strategist + one Ghostwriter per angle × platform). Single diagnose = same shape on perf data.

## Product opportunity (gaps found during the build)

- The chat API has no first-class way to *attach* a specific project Intelligence report to a single conversation explicitly — it's bundled implicitly via `projectId`. A `conversation.attach_report(report_id)` primitive would let downstream tools pin which report variant they want without re-passing context.
- No webhook callback when project enrichment completes. We poll `GET /projects/:id` every 60s. A webhook would cut server-side load and improve UX.
- No standard schema for "ground a Ghostwriter output in a specific framework name." The Strategist's output schema carries `framework_cited` by convention only.

## Run locally

```bash
# 1. Fill .env (see .env.example)
#    HIVEMIND_API_KEY=hm_k_...
#    HIVEMIND_BASE_URL=https://hivemind.myosin.xyz
#    OPENAI_API_KEY=

# 2. Python sidecar
pip install -r requirements.txt
uvicorn server.main:app --port 8000

# 3. Next.js (separate terminal)
cd web && npm install && npm run dev

# 4. Open http://localhost:3000 — redirects to /onboard
#    Paste a URL; you'll land on /workspace/drafts immediately.
#    Connect LinkedIn + Facebook on first push (slide-out panel).
```

## Project structure

```
hivemind-adpilot/                  # this repo
├── scripts/                       # existing Python modules — reused unchanged
│   ├── li_*.py                   # LinkedIn analytics + campaign
│   ├── fb_*.py                   # Facebook insights + campaign
│   └── generate_image.py         # OpenAI image gen + compositing
├── server/                        # FastAPI sidecar
│   ├── main.py                   # app + CORS + routers + token reload on startup
│   ├── deps.py                   # lazy singletons
│   ├── models.py                 # OnboardIn, CredentialsIn, VoicePatch
│   ├── events.py                 # in-process pub/sub
│   ├── hivemind/
│   │   ├── client.py             # HivemindClient — projects + chat + knowledge_search
│   │   ├── strategist_chain.py   # 2-call chain (strategist → ghostwriter per angle)
│   │   ├── diagnose_chain.py     # 2-call chain on perf data
│   │   ├── poller.py             # EnrichmentPoller — GET /projects/:id until ready
│   │   ├── prompts.py            # text builders for chat() calls
│   │   └── types.py
│   ├── store/
│   │   ├── workspace.py          # WorkspaceStore (JSON)
│   │   └── db.py                 # DraftsDB (SQLite)
│   ├── platforms/                # Token validators
│   ├── normalize/                # Cross-platform metric normalization
│   └── routes/
│       ├── workspace.py          # POST /workspace, GET /me, PATCH /credentials
│       ├── events.py             # SSE /workspace/events
│       ├── generate.py           # SSE /generate
│       ├── drafts.py             # CRUD + push + regenerate
│       ├── analytics.py          # GET /analytics
│       └── diagnose.py           # SSE /diagnose + POST /diagnose/accept
├── web/                          # Next.js 15 frontend
│   ├── app/
│   │   ├── onboard/page.tsx      # single URL field
│   │   ├── workspace/
│   │   │   ├── drafts/page.tsx
│   │   │   ├── analytics/page.tsx
│   │   │   └── diagnose/page.tsx
│   │   └── api/image/route.ts    # local image proxy
│   ├── components/               # UI primitives + feature components
│   │   ├── CredentialsPanel.tsx  # deferred ad-platform credential entry
│   │   ├── ChainTrace.tsx        # live SSE trace
│   │   └── ...
│   └── lib/api.ts                # typed client + SSE helpers
├── tests/                        # pytest tests for server modules + scripts
└── docs/
    └── specs/2026-05-13-adpilot-hackathon-design.md
```

## License

Hackathon submission. Code under repo's existing license.
