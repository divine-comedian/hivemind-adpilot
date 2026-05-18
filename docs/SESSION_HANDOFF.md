# AdPilot Session Handoff

Last updated: 2026-05-17

## Current State

AdPilot now has a two-stage onboarding and draft-generation flow:

1. User enters a website URL on `/onboard`.
2. Server creates or reuses a Hivemind project via `POST /api/v1/projects`.
3. `/onboard` shows editable Project Info from saved workspace state: title, description, geographics.
4. User approves Project Info and moves to `/workspace/drafts`.
5. Drafts page has an inline ad-set idea workflow:
   - `Give me some Ideas` calls Ghostwriter for 4 angle cards.
   - Angle cards show only title, angle description, and why it fits.
   - User can dismiss an angle, refine an angle in the same idea conversation, or use an angle.
   - `Use this angle` sends only `angle_id` through the browser URL. The server resolves the saved angle from workspace state.
   - Ad copy generation is one stateless Ghostwriter call that returns the whole ad set in one JSON response, instead of appending 6 messages to the idea conversation.
   - On success, the UI routes to `/workspace/ads`.
6. `/workspace/ads` is the generated ad inventory view:
   - Ads are grouped by Facebook and LinkedIn and sorted newest-first.
   - Cards clearly label ad title, ad subheader, CTA button text, generation date, and publish date.
   - Draft ads can connect/publish, refine copy with Ghostwriter guidance, or delete from the workspace.
   - Draft ads can also be edited directly from the card, including a CTA dropdown.
   - Published ads replace Refine with an Analytics button that links into `/workspace/analytics` for that ad.

Local workspace persistence:

- Workspace/project state lives in `workspace/workspace_state.json`.
- Draft data lives in `workspace/workspace.db`.
- `/onboard` now checks `GET /workspace/me` and surfaces an existing onboarded project instead of forcing a fresh URL entry.

## Important Implementation Notes

- Browser API calls default to the Next proxy at `/api/sidecar`, which forwards to FastAPI at `http://127.0.0.1:8000`.
- Hivemind project updates use `PATCH /api/v1/projects/:id` through `PATCH /workspace/project`.
- Angle refinement uses `conversationId` continuity with the Ghostwriter idea conversation.
- Ad-set copy generation intentionally does not use `conversationId`; it is a one-off Ghostwriter call with compacted context.
- Draft generation now creates a short-lived job with `POST /generate`, then streams `GET /generate/:job_id/events`; the EventSource URL no longer carries the JSON generation payload.
- Published ad metadata (`published_at`, `external_urn`, `external_url`) is surfaced from the latest `pushes` row on draft list/get responses.
- Deleting an ad marks it `discarded`; refining ad copy creates a new draft and marks the parent `superseded`.
- LinkedIn publish now passes the saved Organization URN through to image upload and post authoring; the connect panel explains that this is the Company Page owner for ad assets.
- Ghostwriter prompts now steer fixed-price offers away from `GET_QUOTE`, preferring `LEARN_MORE` or `SIGN_UP` unless the offer is custom-priced.
- Server prompt payloads are clipped/compacted before calling Hivemind to stay below chat text limits.
- Hivemind client errors now include response body detail when available.

## Verification

Last verified commands:

```bash
pytest
cd web && npm run build
cd web && npx tsc --noEmit
```

Results at handoff:

- `pytest`: 100 passed
- `npm run build`: blocked by Google Fonts fetch failures for Fraunces, Geist, and JetBrains Mono
- `npx tsc --noEmit`: passed

Local dev startup:

```bash
# terminal 1, repo root
python3 -m uvicorn server.main:app --reload --port 8000

# terminal 2
cd web
npm run dev
```

Next may choose `http://localhost:3002` or another open port if `3000` is occupied.

## Outstanding Tasks

- Add UX around long-running Ghostwriter generation: clearer loading copy, timeout/error state, and retry.
- Validate the single-call Ghostwriter ad-set response against exact count: 3 Facebook and 3 LinkedIn ads. Today the parser accepts whatever valid platform drafts are returned.
- Add API-level route tests for `/draft-ideas`, `/draft-ideas/refine`, and `/draft-ideas/dismiss` beyond helper coverage.
- Add a way to reset or switch workspace state. This is currently single-tenant and file-backed.
- Decide whether saved dismissed/refined angle history should be recoverable or audit-visible.
- Improve SSE proxy handling for `/workspace/events`; dev reloads can log noisy broken-pipe/terminated stream errors.
- Consider moving image generation out of the synchronous generation path or making failures visible per draft. It currently falls back to an empty image path on exception.
- Add UI tests or Playwright smoke checks for onboarding recovery, Project Info editing, idea generation, refine, dismiss, and use-angle flows.
- Review old docs/specs and README for drift against the current flow before any demo or PR.
