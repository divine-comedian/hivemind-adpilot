# Aurevon Ads Skill — Design Spec

**Date:** 2026-03-14
**Status:** Draft
**Author:** Mitch + Claude

## Overview

A Claude Code skill for full-lifecycle Facebook and LinkedIn ad management for Aurevon Intelligence. Combines cross-platform campaign management, performance analytics, and creative production (hivemind copywriting + OpenAI image generation) into a single `/ads` skill with programmable guardrails.

## Problem

Aurevon currently manages Facebook and LinkedIn ads through platform UIs manually. There is no unified view of cross-platform performance, no systematic creative production pipeline, and no learning journal to track what works over time. Current state:

- **Facebook:** Traffic campaign running since Feb 12, $111 CAD spent, 429 landing page views at $0.26/view. One ad ("Custom Business Intelligence") getting all traffic — two others ("affordable intel", "intel gap") at 0 impressions.
- **LinkedIn:** Website visits campaign since Mar 10, ~$193 CAD spent at $50/day, 345 clicks at $0.56/click. Zero conversions, zero engagement.

## Goals

1. Unified cross-platform reporting and comparison
2. Creative production pipeline: hivemind copy + OpenAI images + brand consistency
3. Campaign creation as drafts (PAUSED/DRAFT) requiring manual activation
4. Performance optimization recommendations with approval gates
5. Learning journal that makes the skill smarter over time
6. Programmable guardrails at both prompt and code layers

## Non-Goals

- Ad spend budget management (handled in platform UIs)
- Account billing or payment configuration
- Video or carousel ad formats (single image feed ads only)
- Automated campaign activation (always requires manual approval)
- LinkedIn lead gen forms or event ads

## Architecture

### Approach: Thin Scripts + Smart Prompt

SKILL.md handles orchestration, workflow logic, and cross-platform reasoning. Python scripts are thin, single-purpose API wrappers. Guardrails are enforced at both layers independently.

### File Structure

```
~/.claude/skills/aurevon-ads/
  SKILL.md                        # Command routing, workflows, guardrails
  .env                            # API keys
  scripts/
    fb_insights.py                # Pull Facebook campaign/ad performance data
    fb_campaign.py                # Create/update/pause Facebook campaigns, ad sets, ads
    li_analytics.py               # Pull LinkedIn campaign analytics
    li_campaign.py                # Create/update/pause LinkedIn campaigns, creatives
    generate_image.py             # OpenAI image gen with ad format size presets
    session_guard.py              # Enforce per-session spend + image caps
  reference/
    fb_ad_specs.md                # Dimensions, character limits, placement rules
    li_ad_specs.md                # Dimensions, targeting facets, format rules
    aurevon_brand.md              # Brand colors, fonts, voice guidelines for image prompts
  memory/
    journal.md                    # Rolling 30-day learning journal
    journal_archive.md            # Compacted summaries of older observations
  drafts/                         # Generated ad drafts awaiting approval
```

### Dependencies

- `requests` — HTTP calls to Facebook Graph API and LinkedIn REST API
- `openai` — OpenAI Python SDK for image generation
- `python-dotenv` — .env file loading
- `Pillow` — Image handling (save, resize if needed)

## API Integration

### Facebook Marketing API (v25.0)

**Base URL:** `https://graph.facebook.com/v25.0`

**Authentication:** Long-lived access token via `FACEBOOK_ACCESS_TOKEN` env var.

**Endpoints used:**

| Script | Endpoint | Method | Purpose |
|--------|----------|--------|---------|
| `fb_insights.py` | `act_{id}/insights` | GET | Account-level performance |
| `fb_insights.py` | `{campaign_id}/insights` | GET | Campaign-level performance |
| `fb_insights.py` | `{ad_id}/insights` | GET | Ad-level performance |
| `fb_campaign.py` | `act_{id}/campaigns` | POST | Create campaign (PAUSED) |
| `fb_campaign.py` | `act_{id}/adsets` | POST | Create ad set |
| `fb_campaign.py` | `act_{id}/adimages` | POST | Upload ad image, get image_hash |
| `fb_campaign.py` | `act_{id}/adcreatives` | POST | Create AdCreative (image_hash + copy + CTA) |
| `fb_campaign.py` | `act_{id}/ads` | POST | Create ad (references AdCreative) |
| `fb_campaign.py` | `{campaign_id}` | POST | Update campaign status/budget |

**Key metrics pulled:** impressions, clicks, spend, cpc, cpm, ctr, reach, actions (landing_page_view), cost_per_action_type, created_time.

**Breakdowns supported:** age, gender, placement, device.

### LinkedIn Marketing API (v202602)

**Base URL:** `https://api.linkedin.com/rest`

**Authentication:** OAuth 2.0 bearer token via `LINKEDIN_ACCESS_TOKEN` env var.

**Required headers:**
```
Authorization: Bearer {token}
Linkedin-Version: 202602
X-Restli-Protocol-Version: 2.0.0
```

**Endpoints used:**

| Script | Endpoint | Method | Purpose |
|--------|----------|--------|---------|
| `li_analytics.py` | `/adAnalytics?q=analytics` | GET | Performance by pivot |
| `li_analytics.py` | `/adAnalytics?q=statistics` | GET | Multi-pivot analysis |
| `li_campaign.py` | `/adAccounts/{id}/adCampaigns` | POST | Create campaign (DRAFT) |
| `li_campaign.py` | `/adAccounts/{id}/adCampaigns/{id}` | POST | Update (PARTIAL_UPDATE) |
| `li_campaign.py` | `/images?action=initializeUpload` | POST | Initialize image upload |
| `li_campaign.py` | `{uploadUrl}` | PUT | Upload image binary to LinkedIn CDN |
| `li_campaign.py` | `/adAccounts/{id}/adCreatives` | POST | Create creative (with image URN) |

**Key metrics pulled:** impressions, clicks, costInLocalCurrency, landingPageClicks, likes, shares, externalWebsiteConversions.

**Pivots supported:** CAMPAIGN, CREATIVE, MEMBER_COMPANY, MEMBER_JOB_TITLE, MEMBER_INDUSTRY, MEMBER_COUNTRY_V2.

### OpenAI Images API

**Endpoint:** `POST https://api.openai.com/v1/images/generations`

**Model:** `gpt-image-1` (preferred) or `dall-e-3` (fallback)

**Generation size:** 1536x1024 (closest supported landscape size for gpt-image-1). For dall-e-3 fallback: 1792x1024.

**Post-processing:** Pillow crops generated image to 1200x628 (1.91:1 ratio) for ad platform specs. Prompts instruct the model to keep key visual content centered, knowing top/bottom will be trimmed.

**Output:** Final cropped image at 1200x628 (landscape feed ad — works for both FB and LI sponsored content).

**Prompt construction:** Combines approved ad copy + brand guidelines from `aurevon_brand.md` + journal insights on past image performance. Includes composition instruction: "Keep all important visual elements in the center horizontal band — the top and bottom edges will be cropped."

## Token Management

Both platforms issue tokens that expire:

- **Facebook:** Long-lived tokens expire after ~60 days. No automatic refresh without user re-authentication via Meta Business Suite.
- **LinkedIn:** Access tokens expire after 60 days. Refresh tokens (365 days) available to approved Marketing Developer Platform partners.

### Strategy

- **`/ads status` always validates tokens first** — makes a lightweight API call to each platform and reports token health alongside campaign status
- **On token error (401/403):** skill stops immediately, displays clear message: "Facebook token expired. Regenerate at [Meta Business Settings URL] and update .env"
- **No automatic token refresh** — tokens are manually managed in `.env`. This is acceptable given the ~60 day lifetime and the manual-approval philosophy of the skill.
- **Token validation script:** Each platform script includes a `validate_token()` function called before any operation. Returns token status + days until estimated expiration if detectable.

## Cross-Platform Metric Normalization

When comparing Facebook and LinkedIn metrics in `/ads report`, note these differences:

| Metric | Facebook | LinkedIn | Comparable? |
|--------|----------|----------|-------------|
| Clicks to site | `actions:landing_page_view` (fires on page load) | `landingPageClicks` (fires on click) | Approximate — FB is stricter |
| CTR | clicks / impressions | clicks / impressions | Yes |
| CPC | spend / clicks | costInLocalCurrency / clicks | Yes (same currency) |
| Reach | Unique users (deduplicated) | Approximate unique members | Approximate |
| Engagement | reactions + comments + shares | likes + shares + comments | Yes |

SKILL.md instructs Claude to note these caveats when presenting cross-platform comparisons.

## Commands

### `/ads report`

**Purpose:** Cross-platform performance comparison.

**Flow:**
1. Call `fb_insights.py` — last 7 days default (overridable), all active campaigns
2. Call `li_analytics.py` — same metrics, same date range
3. Claude compares: cost efficiency, CTR, reach, spend
4. **Creative staleness check:** pull created_time (FB) / campaign start date (LI) for each creative
   - Warning at 14 days without refresh
   - Alert at 30 days — "ad fatigue likely"
   - Flag CTR decline >20% week-over-week regardless of age
5. Output: formatted table + "Creative Health" column + cross-platform recommendations
6. Append observations to `journal.md`

**Cost:** $0 (read-only API calls)

### `/ads draft`

**Purpose:** Generate complete ad creatives (copy + image) for approval.

**Flow:**
1. Claude asks what the ad is for (or infers from context)
2. Invoke `hivemind-ghostwriter` skill with context from `aurevon_brand.md` + `journal.md`
3. Hivemind returns freeform copy. Claude parses it into structured ad fields:
   - Primary text (FB: 125 chars, LI: 150 chars)
   - Headline (FB: 40 chars, LI: 70 chars)
   - Description (FB: 30 chars)
   - CTA selection
   SKILL.md includes a prompt template that instructs hivemind to return copy labeled by field for easier parsing. Claude maps the output to the structured fields.
4. Present copy → user approves or edits
5. Call `session_guard.py --check` → verify budget remaining
6. Call `generate_image.py` with brand-aware prompt at 1200x628
7. Present image → user approves, requests regen, or discards
8. Save approved draft to `drafts/{date}_{campaign_name}/`
   ```
   image.png
   copy.json        # headline, primary_text, description, cta
   manifest.json    # platform targets, dimensions, status
   ```
9. Log copy/image observations to `journal.md`

**Cost:** ~$0.17 per image (OpenAI gpt-image-1 at 1536x1024 high quality). Budget for ~$0.20/image including conservative margin.

### `/ads campaign`

**Purpose:** Create full campaign structures from approved drafts.

**Flow:**
1. Claude asks: platform (FB/LI/both), objective, targeting, daily budget
2. Generates campaign structure:
   - **Facebook:** Campaign (PAUSED) → Ad Set (targeting + budget) → Upload image (get image_hash) → AdCreative (image_hash + copy + CTA) → Ad (references AdCreative)
   - **LinkedIn:** Campaign (DRAFT) → Upload image (initializeUpload → PUT binary → get image URN) → Creative (with image URN)
3. Present full structure for approval — names, targeting, budget, creative assignment
4. On approval, call `fb_campaign.py` / `li_campaign.py` to create
5. Campaigns created in PAUSED (FB) / DRAFT (LI) state
6. User activates manually in platform UI when ready

**Cost:** $0 (API calls only — campaigns don't spend until activated)

### `/ads optimize`

**Purpose:** Analyze and recommend changes to active campaigns.

**Flow:**
1. Pull performance data (same as `/ads report`)
2. Claude analyzes with journal context:
   - Underperformers: high CPC, low CTR, declining performance
   - Ads with 0 impressions (auction losers)
   - Budget distribution across campaigns
   - Creative staleness (age + performance decay)
3. Recommend specific actions: "Pause ad X", "Increase budget on Y", "Refresh creative Z — 28 days old, CTR down 30%"
4. Each action requires user approval before execution
5. Log observations + outcomes to `journal.md`

**Cost:** $0 (read-only analysis + approved write operations)

### `/ads status`

**Purpose:** Quick health check.

**Flow:**
1. Parallel calls to both platforms
2. Return: active campaign count, today's spend, delivery status, issues (budget exhausted, ads rejected, learning phase, creative staleness warnings)

**Cost:** $0 (read-only)

## Guardrails

### Python Layer (`session_guard.py`)

```python
SESSION_WINDOW_HOURS = 1        # Session resets after 1 hour of inactivity
SESSION_MAX_SPEND = 10.00       # USD — max generative API spend per session
SESSION_MAX_IMAGES = 20         # Max image generations per session
```

**Behavior:**
- Maintains `session_state.json` with running totals (spend, image count, session start timestamp)
- Every script calls `session_guard.check()` before any paid API call
- If over either cap (spend or image count), raises error and refuses
- Session resets automatically when gap between calls exceeds `SESSION_WINDOW_HOURS`
- Spend estimated conservatively (highest cost tier for ambiguous cases)
- `session_guard.py --check` returns remaining budget + images as structured output
- `session_guard.py --reset` allows manual session reset

**Enforced in scripts:**
- `generate_image.py` — checks before every generation, logs cost after
- All campaign creation scripts — checks before write operations (as a safety net, even though these are $0)

### Prompt Layer (SKILL.md)

- Before any image generation: call `session_guard.py --check`, display remaining budget to user
- Before any campaign creation: present full draft, wait for explicit "approved" / "yes" / "go ahead"
- Never batch-create — one campaign/ad at a time, each requiring approval
- If session guard returns over-limit, stop and inform user with remaining allowance
- Before any campaign status change (pause, archive): confirm with user

### What is NOT guarded (platform responsibility)

- Daily/lifetime ad spend budgets
- Account-level spend caps
- Billing limits
- Ad policy compliance (platform review handles this)

## Learning Journal

### Structure (`memory/journal.md`)

```markdown
## YYYY-MM-DD — [Context]

### What Worked
- [observation with specific metrics]

### What Didn't Work
- [observation with specific metrics]

### Copy Insights
- [what copy styles/approaches performed]

### Audience Insights
- [targeting observations]

### Budget Insights
- [spend efficiency observations]

### Image Insights
- [what image styles/approaches performed]

### Creative Staleness
- [age and decay observations]

### Recommendations for Next Time
- [actionable takeaways]
```

### Rules

- Claude reads `journal.md` at the start of every `/ads` command
- Claude appends after: report generation, optimization analysis, draft creation, campaign performance review
- Never deletes entries — append only
- Entries are dated and categorized
- **30-day rolling window:** entries older than 30 days are compacted into `journal_archive.md` as summarized insights (key learnings preserved, raw metrics dropped)
- **Compaction trigger:** runs only during `/ads report` or `/ads optimize` commands (which already do analysis), not during quick commands like `/ads status`
- **Compaction process:** Claude reads entries > 30 days old, summarizes key learnings per category (copy, audience, budget, image), appends summary block to `journal_archive.md`, removes original entries from `journal.md`
- `journal_archive.md` is consulted for long-term patterns but kept concise (target: under 200 lines)

## Reference Files

### `fb_ad_specs.md`

- Single image feed ad: 1200x628px, ratio 1.91:1
- Primary text: 125 characters (recommended)
- Headline: 40 characters
- Description: 30 characters
- File type: JPG or PNG
- Max file size: 30MB
- CTAs: Learn More, Sign Up, Get Quote, Download, Shop Now, etc.

### `li_ad_specs.md`

- Sponsored Content single image: 1200x628px
- Introductory text: 150 characters (recommended, 600 max)
- Headline: 70 characters (recommended, 200 max)
- File type: JPG or PNG
- Max file size: 5MB
- CTAs: Learn More, Sign Up, Register, Download, etc.
- Targeting facets: locations, industries, jobTitles, jobFunctions, seniorities, employers, skills, companyFollowers, segments

### `aurevon_brand.md`

- **Colors:** Bronze #cf995f (primary/CTA), Mahogany #2e0f15 (dark), Slate #3b6064 (secondary), Steel #95b2b8 (light accent), Gold #f9dc5c (highlights)
- **Font:** Geist (sans-serif)
- **Voice:** Professional, data-driven, authoritative but accessible. Targeting local business owners who want competitive intelligence.
- **Product:** AI-powered competitive intelligence reports, $25 CAD each
- **Key value props:** Custom business intelligence, affordable competitor analysis, 40+ industry categories
- **Image style:** Clean, professional, data-visualization aesthetic. Avoid stock photo feel. Prefer abstract/geometric patterns with brand colors or clean product screenshots.

## Error Handling

### API Failures

- **Token expired (401/403):** Stop immediately, display re-authentication instructions, do not retry
- **Rate limited (429 / FB error 613 / LI throttle):** Wait and retry once after 60 seconds. If still throttled, report to user and suggest trying later.
- **Network failure:** Retry once. On second failure, report error with details.

### Partial Failures (Campaign Creation)

Campaign creation chains multiple API calls (campaign → ad set → creative → ad). On failure mid-chain:
- Report exactly what was created and what failed
- Provide the IDs of created objects so user can clean up in platform UI if needed
- Do not attempt automatic rollback (deletions are destructive)

### Image Generation Failures

- If OpenAI returns an error (content policy, rate limit, etc.): report the error, do not charge against session budget
- If image is generated but user rejects it: charge the cost, decrement image count (the API call happened)

## Aurevon Ad Account Details

### Facebook

- **Account name:** (to be confirmed from API)
- **Currency:** CAD
- **Current campaign:** Traffic / Landing page views
- **Bidding:** ABSOLUTE_OCPM
- **Attribution:** 7-day click or 1-day view

### LinkedIn

- **Account name:** Aurevon Intelligence
- **Account ID:** (Campaign Group ID: 840928146, Campaign ID: 555838216)
- **Currency:** CAD
- **Current campaign:** Website visits — Sponsored Update
- **Bidding:** CPM
- **Daily budget:** $50 CAD

## Pre-Implementation Setup (Required)

These must be resolved before implementation begins. Add values to `.env`:

1. **`FACEBOOK_AD_ACCOUNT_ID`** — Get from Meta Ads Manager Settings, or call `GET /me/adaccounts` with your token. Format: `act_XXXXXXXXX`
2. **`FACEBOOK_ACCESS_TOKEN`** — Generate a long-lived token via Meta Business Settings → System Users. ~60 day lifetime.
3. **`LINKEDIN_AD_ACCOUNT_ID`** — The `sponsoredAccount` URN ID (not the campaign ID). Get from LinkedIn Campaign Manager URL or API.
4. **`LINKEDIN_ACCESS_TOKEN`** — OAuth 2.0 bearer token. ~60 day lifetime.
5. **`OPENAI_API_KEY`** — Confirm which account/org to use.

### `.env` Template

```env
# Facebook Marketing API
FACEBOOK_AD_ACCOUNT_ID=act_XXXXXXXXX
FACEBOOK_ACCESS_TOKEN=

# LinkedIn Marketing API
LINKEDIN_AD_ACCOUNT_ID=
LINKEDIN_ACCESS_TOKEN=

# OpenAI Images API
OPENAI_API_KEY=

# Guardrails (optional overrides)
SESSION_WINDOW_HOURS=1
SESSION_MAX_SPEND=10.00
SESSION_MAX_IMAGES=20
```
