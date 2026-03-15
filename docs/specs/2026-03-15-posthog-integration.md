# PostHog Integration for aurevon-ads

## Context

Ad platform APIs (LinkedIn, Facebook) only track pre-click metrics — impressions, clicks, spend. PostHog tracks what happens after the click: demo form starts, submissions, checkouts, payments. Without connecting these, we can't measure true ROI or know which creatives drive actual conversions vs just clicks. The journal already flags this: "Zero tracked conversions — PostHog not connected to LinkedIn conversions yet."

This adds PostHog as a third data source so `/ads report` and `/ads optimize` can correlate ad spend with real conversion data.

## Implementation

### Step 1: Update `scripts/config.py`

Add PostHog base URL constant and auth helper, matching existing pattern:

```python
POSTHOG_BASE_URL = "https://us.posthog.com"

def posthog_headers() -> dict:
    """Return standard PostHog API headers with auth."""
    return {
        "Authorization": f"Bearer {get_env('POSTHOG_API_KEY')}",
        "Content-Type": "application/json",
    }
```

### Step 2: Update `tests/conftest.py`

Add to `mock_env` fixture:
```python
monkeypatch.setenv("POSTHOG_API_KEY", "phx_test-posthog-key-789")
monkeypatch.setenv("POSTHOG_PROJECT_ID", "335835")
```

### Step 3: Create `scripts/ph_auth.py` + `tests/test_ph_auth.py`

Token validation via `GET /api/projects/{project_id}/`. Returns `{"valid": bool, "project_name": ..., ...}`. Follows `fb_auth.py` exactly.

### Step 4: Create `scripts/ph_insights.py` + `tests/test_ph_insights.py`

Subcommand-based CLI (matching `li_campaign.py` pattern with `argparse` subparsers):

| Command | What it fetches | API |
|---------|----------------|-----|
| `traffic` | Daily pageviews + unique visitors | POST query (HogQL) |
| `funnel` | Counts per funnel step: demo_form_started → submitted → checkout → payment | POST query (HogQL) |
| `events` | Counts for all 15 tracked events | POST query (HogQL) |
| `experiment` | Experiment status + results by feature flag key | GET experiments API |

**CLI interface** (subcommands with per-command flags):
```bash
python3 -m scripts.ph_insights traffic --days 7
python3 -m scripts.ph_insights traffic --start 2026-03-08 --end 2026-03-15
python3 -m scripts.ph_insights funnel --days 30
python3 -m scripts.ph_insights events --days 7
python3 -m scripts.ph_insights experiment --id landing-page-v2
```

**Subparser structure** (like `li_campaign.py`):
```python
sub = parser.add_subparsers(dest="command")

# traffic — daily pageviews + unique visitors
p_traffic = sub.add_parser("traffic")
p_traffic.add_argument("--days", type=int, default=7)
p_traffic.add_argument("--start", type=str, help="YYYY-MM-DD, overrides --days")
p_traffic.add_argument("--end", type=str, help="YYYY-MM-DD, defaults to today")

# funnel — conversion funnel step counts
p_funnel = sub.add_parser("funnel")
p_funnel.add_argument("--days", type=int, default=7)
p_funnel.add_argument("--start", type=str)
p_funnel.add_argument("--end", type=str)

# events — all tracked event counts
p_events = sub.add_parser("events")
p_events.add_argument("--days", type=int, default=7)
p_events.add_argument("--start", type=str)
p_events.add_argument("--end", type=str)

# experiment — experiment status + results
p_exp = sub.add_parser("experiment")
p_exp.add_argument("--id", required=True, help="Feature flag key (e.g. landing-page-v2)")
```

**Key functions:**
- `build_query(command, start_date, end_date)` → HogQL query dict (returns None for experiment)
- `fetch_traffic(project_id, start_date, end_date)` → `{"command": "traffic", "results": [...]}`
- `fetch_funnel(project_id, start_date, end_date)` → `{"command": "funnel", "results": [...]}`
- `fetch_events(project_id, start_date, end_date)` → `{"command": "events", "results": [...]}`
- `fetch_experiment(project_id, experiment_id)` → `{"command": "experiment", "experiment": {...}, "results": {...}}`
- `_handle_error(resp, context)` → print + sys.exit(1) (matching `li_campaign.py` pattern)
- `main()` — subparser dispatch + JSON output to stdout

**HogQL over Insight API:** SQL-like queries are readable, maintainable, and keep scripts thin. The skill layer interprets results.

**PostHog query response transform:** Response is `{"columns": [...], "results": [[...], ...]}` — zip columns with each row to produce list of dicts.

### Step 5: Update SKILL.md

**`/ads report`** — add PostHog pull after LinkedIn/Facebook:
```bash
python3 -m scripts.ph_insights traffic --days 7
python3 -m scripts.ph_insights funnel --days 7
```
Add analysis guidance: conversion funnel drop-off rates, cost-per-demo-start, cost-per-payment.

**`/ads optimize`** — add post-click quality analysis:
- High CTR + low demo conversion = audience/landing page problem, not creative
- Experiment impact on conversion rates

**Key Identifiers** — add PostHog section with project ID, env vars, funnel events, active experiment.

### Step 6: User adds `.env` vars

```
POSTHOG_API_KEY=<create at PostHog > Settings > Personal API Keys>
POSTHOG_PROJECT_ID=335835
```

## Files Modified
- `scripts/config.py` — add `POSTHOG_BASE_URL`, `posthog_headers()`
- `tests/conftest.py` — add PostHog env vars to `mock_env`
- `/home/mitch/.claude/skills/aurevon-ads/SKILL.md` — update `/ads report`, `/ads optimize`, Key Identifiers

## Files Created
- `scripts/ph_auth.py` — token validation (pattern: `fb_auth.py`)
- `scripts/ph_insights.py` — analytics CLI with 4 subcommands (pattern: `li_campaign.py` subparsers)
- `tests/test_ph_auth.py` — auth tests (pattern: `test_fb_auth.py`)
- `tests/test_ph_insights.py` — insights tests (pattern: `test_fb_insights.py`)

## Verification

1. `pytest tests/test_ph_auth.py tests/test_ph_insights.py` — new tests pass
2. `pytest` — full suite still passes
3. After adding API key to `.env`:
   - `python3 -m scripts.ph_auth` — validates token
   - `python3 -m scripts.ph_insights traffic --days 7` — returns daily traffic JSON
   - `python3 -m scripts.ph_insights funnel --days 7` — returns funnel event counts
   - `python3 -m scripts.ph_insights experiment --id landing-page-v2` — returns experiment data
4. Run `/ads report` — confirms PostHog data appears alongside LinkedIn/Facebook metrics
