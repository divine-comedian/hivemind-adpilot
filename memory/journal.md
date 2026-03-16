# Aurevon Ads — Learning Journal

## 2026-03-14 — Initial Setup & First Ad

### What Worked
- LinkedIn campaign "Website visits" running since Mar 10: 22,674 impressions, 383 clicks, $207.23 CAD in 30 days
- Best creative: 2.26% CTR (well above LinkedIn B2B benchmark of 0.4-0.6%)
- Cheapest CPC: $0.41 (creative #6)
- "Competitive paranoia" copy angle from Hivemind: "Your competitors are already researching you"

### What Didn't Work
- Zero tracked conversions across all 7 creatives (partly tracking gap — PostHog not connected to LinkedIn conversions yet)
- Creative #3: worst performer at 0.80% CTR, $0.69 CPC
- Original ad image prompt style (network/constellation visualization) looked like clip art — too literal

### Copy Insights
- Leading with FREE demo is the conversion hook, not $25 price
- Specificity works: "242 data sources", "5 minutes"
- Website's own copy "Your competitors are already researching you" resonates

### Image Insights
- Abstract cinematic backgrounds >> literal data visualizations
- Dark mahogany + bronze/gold sweep is the core visual identity
- Logo must be passed as input image to OpenAI images.edit() — images.generate() invents wrong logos
- Logo needs padding from edges, not flush to bottom

### Recommendations for Next Time
- Test more background styles from the 45-style library (especially creative styles 31-45)
- A/B test copy angles: competitive paranoia vs time scarcity vs information asymmetry
- Connect PostHog conversion tracking to LinkedIn to measure actual ROI

## 2026-03-14 — The Blind Spot Ad (Full /ads draft flow)

### What Worked
- Full end-to-end `/ads draft` flow: analyze top performers → hivemind riff on winning patterns → generate image → publish
- "The Blind Spot" angle: specificity of what competitors know (Google reviews, permits, suppliers) — riffs on the top performer (#1 Ad, 2.26% CTR)
- Paper Terrain style (#38) produced a strong visual — origami/shadow play in brand colors
- Shorter image headlines work better: "Stop being the last to know." is punchier than multi-line copy
- Separating image headline (short, punchy) from LinkedIn headline field (can add "Try it free.") gives flexibility

### Copy Insights
- Top 3 performing copy patterns (from 4-day cohort, excluding <1 day ads):
  1. Competitive paranoia: "they ARE tracking you" (2.26% CTR)
  2. Price anchoring + free preview: "$15K consultants vs free" ($0.41 CPC)
  3. Betting metaphor + speed: "every decision is a bet" (1.73% CTR)
- Hivemind produces best results when fed actual performance data + winning copy to riff on
- "Preview free" doesn't work as standalone text — needs a verb ("Try it free")

### Image Insights
- LESS TEXT ON IMAGES IS BETTER — short punchy headlines (5-7 words) > long sentences
- Image headline and LinkedIn headline can be different — image gets the hook, LinkedIn field adds detail
- Creative styles (31-45) produce more interesting backgrounds than safe corporate styles (1-30)
- Paper Terrain (#38) is a winner — bookmark for reuse

### Process Insights
- Always filter analytics by publication date — new ads (<2 days) skew the data
- Default draft flow: pull creative-level performance → fetch actual copy from posts → identify winning patterns → feed winners to hivemind → generate variations
- Need a `list-ad-copy` subcommand to avoid manual API calls for fetching post copy

### Recommendations for Next Time
- Build `list-ad-copy --campaign-id` into li_campaign.py
- Test more creative styles (31-45) — they produce more distinctive visuals
- Monitor The Blind Spot ad for 3-4 days before judging performance
- Try headline-only images (no intro text baked in) to test even more minimal approach

## 2026-03-14 — Batch Rotation (8 images)

### Styles That Worked
- **#33 Brutalist Shadow Study** (ad1 "Are you tracking them back?") — harsh diagonal shadow, great contrast, instant winner
- **#27 Amber Bokeh** (ad2 "$25K research. $25 report.") — warm, premium, good text legibility
- **#36 Chiaroscuro Fabric Fold** (ad4 "Insights that arrive on time.") — dramatic silk lighting
- **#9 Angular Dusk** (ad5 "Stop betting blind.") — clean geometric planes, good with full logo
- **#22 Golden Stream** (ad6 "Level the playing field.") — elegant single light trail, minimal
- **#5 Mahogany Glow** (ad8 "They're researching you already.") — simple dark vignette, lets copy punch
- **#38 Paper Terrain** (The Blind Spot ad, earlier) — origami shadow play, strong

### Styles That Failed
- **#40 Bisected Contrast** (ad2 first attempt) — ugly hard split, bad pattern, discarded
- **#31 Cracked Bronze Macro** (ad5 first attempt) — weird organic texture, looked like a tree stump not premium metal
- **#25 Smoke and Bronze** (ad6 first attempt) — looked like hellfire/flames, too aggressive

### Image Generation Learnings
- **Font rendering:** Must explicitly say "no text stroke, no text border, no text outline, no text shadow, no embossing" — OpenAI defaults to adding strokes/borders on some styles
- **Text placement:** Always upper-left works but should vary — some backgrounds have light areas at top that clash with gold text. Need to specify "place text over the darkest area"
- **Logo variation:** Should mix `mark` and `full` logo across the set, not use the same one every time
- **Background noise:** Simpler/calmer backgrounds (gradients, geometric, minimal) consistently outperform busy ones (macro textures, ink drops, high-detail patterns). Noise competes with the headline
- **Session guard:** generate_image.py now tracks spend/images properly — was missing before this batch
- **Color contrast:** When background has gold/bronze tones in the upper area, gold text gets lost. Either move text lower or use a style with a dark upper region

### Styles to Bookmark (reliable)
Tier 1 (proven winners): #5, #9, #22, #27, #33, #36, #38
Tier 2 (acceptable): #34, #42, #44
Avoid: #25, #31, #40

### Process Learnings
- Batch image generation should be wrapped in a proper CLI command, not ad-hoc bash chains
- Need a `list-ad-copy --campaign-id` subcommand to avoid manual API scripts
- When rotating, always filter by publication date — don't judge ads with <2 days of data

### Full Rotation Published
9 active creatives (8 fresh + The Blind Spot), 8 old creatives paused. All new ads keep the same intro text / copy angle as originals but add:
- Fresh background images from the style library
- Short punchy image headlines (5-7 words baked into image)
- LinkedIn headline field (old ads had none)

## 2026-03-14 — End of Day Summary

### What We Built Today
1. **LinkedIn scripts** — li_analytics.py, li_campaign.py (with create-ad 3-step flow, rotate-creatives, pause/activate), li_auth.py, session_guard.py, config.py
2. **Image generation** — generate_image.py CLI with 45 background styles, logo handling via images.edit(), session guard integration
3. **SKILL.md** — full `/ads` skill with status, report, draft, campaign, optimize, rotate commands
4. **Learning journal** — this file, capturing performance data and creative learnings
5. **Memory files** — product context, LinkedIn API gotchas, image gen guidelines, CLI design preferences

### Key Discoveries
- LinkedIn Advertising API requires ad account linked to the product in developer portal (not just OAuth scopes)
- Creatives endpoint uses version 202509, other endpoints use 202602
- Ad creation is a 3-step flow: upload image (org owner) → create DSC post → BATCH_CREATE creative
- LinkedIn posts are immutable — can't swap images, must create new ads to rotate visuals
- Hivemind = copy only, never visual direction. Image styles are a separate creative decision
- Less text on images is better. Short punchy headlines (5-7 words) win
- Simpler backgrounds outperform busy ones. Tier 1 styles: #5, #9, #22, #27, #33, #36, #38
- Default draft flow: pull performance → fetch copy from top performers → feed to hivemind → generate variations
- Always filter analytics by publication date before judging creative performance

### Outstanding TODOs for Next Session
- ~~**Facebook integration:** fb_insights.py and fb_campaign.py~~ — DONE (2026-03-15)
- **list-ad-copy subcommand:** add to li_campaign.py so we don't need manual API calls to fetch post content
- **Batch rotation command:** wrap the generate-all + publish-all + pause-old flow into a single CLI command
- **PostHog conversion tracking:** connect PostHog events to LinkedIn conversions so we can measure actual ROI, not just clicks
- **Reference files:** create li_ad_specs.md, fb_ad_specs.md, aurevon_brand.md in reference/
- **Cross-platform reporting:** update /ads report to pull both LinkedIn + Facebook data side by side

## 2026-03-15 — Facebook Ad Publishing (First E2E)

### What We Built
1. **fb_campaign.py** — Full Facebook campaign/ad management CLI (12 subcommands):
   - Discovery: `list-campaigns`, `list-adsets`, `list-ads` (by campaign or adset)
   - Campaign: `create-campaign`, `update-campaign`
   - Ad sets: `create-adset` (auto-detects campaign budget + optimization goal), `update-adset`
   - Ads: `create-ad` (3-step: upload + creative + ad), `create-full-ad` (4-step: adset + upload + creative + ad)
   - Status: `pause-ad`, `activate-ad`, `upload-image`
2. **Default ICP targeting** baked into `DEFAULT_FLEXIBLE_SPEC` — `--interests default` (the default) applies Aurevon's ICP without needing a JSON file
3. **First Facebook ad published:** "Fire Your Consultant — Price Anchor" under campaign 6952504195779, ad ID 6955623866979

### Facebook API Quirks (vs LinkedIn)
- **4-layer hierarchy:** Campaign → Ad Set → Ad Creative → Ad (LinkedIn is 3: Campaign → Post → Creative)
- **Campaign-level budget:** If campaign has `daily_budget`, adsets CANNOT also set one — must auto-detect via `_get_campaign_info()`
- **Optimization goal lock:** All adsets in a lowest-cost campaign must share the same `optimization_goal` — auto-detect from existing adsets
- **Advantage+ audience:** Required flag `targeting_automation.advantage_audience`. When enabled, age_min capped at 25, age_max floored at 65. Real age targeting comes from interest/behavior signals, not hard constraints
- **Auth via query params:** Facebook uses `access_token` as query param (vs LinkedIn's `Authorization` header + Rest.li version headers)
- **Image upload returns hash:** Facebook stores images by hash (not URN). Upload returns `image_hash` used in creative's `object_story_spec.link_data`
- **Budgets in cents:** Facebook budgets are in cents ($25 = 2500), different from LinkedIn's float format

### Copy Insights
- **Hivemind** produced strong price-anchoring copy when given full context: product details, angle, audience, format constraints
- Piping multi-line prompts via stdin to `hivemind ghostwriter` is the cleanest workflow for detailed briefs
- Image headline ("Fire your expensive consultant") + different Facebook headline ("Same Intel. 200x Cheaper. Ready Now.") = good complementary pairing — same angle, different hooks

### Targeting Insights
- Aurevon ICP targeting: Small business, Entrepreneurship, Business analytics, Marketing, Business leaders + Small business owners behavior + Business Decision Makers industry
- Dropped hospitality/restaurant interests from the original broad adset — too far from competitive intelligence buyers
- Facebook Page ID for Aurevon Intelligence: 973778689159824 (discovered via /me/accounts, NOT the ID the user suggested)

### Process Learnings
- Always verify Page IDs via `/me/accounts` API — the ID in Meta Business Suite URL is often wrong
- Build CLI scripts iteratively: basic version first, then fix API quirks as they surface during real e2e testing
- Default ICP targeting baked into the script (`--interests default`) eliminates the manual JSON step for every ad creation

## 2026-03-15 — Pixel & Insight Tag Installation

### What We Built
1. **Facebook Pixel** (ID: 2038438126722898) — created via API, installed in aurevon frontend
   - `components/facebook-pixel.tsx` — loads pixel, fires PageView on every page
   - `trackFbEvent("Lead")` on successful demo report creation
   - `trackFbEvent("InitiateCheckout")` on OTP flow start
2. **LinkedIn Insight Tag** (Partner ID: 8940172) — installed from LinkedIn-provided snippet
   - `components/linkedin-insight-tag.tsx` — loads tag, fires pageview on every page
   - `trackLinkedInConversion()` helper ready for conversion IDs from Campaign Manager
3. **Production-only guard** — both gated on `NEXT_PUBLIC_VERCEL_ENV === "production"`
4. **Type declarations** — `types/ad-pixels.d.ts` for `window.fbq` and `window.lintrk`

### Key Decisions
- Facebook Pixel partner ID ≠ ad account ID. Created fresh pixel via `POST act_{id}/adspixels`
- LinkedIn Insight Tag partner ID (8940172) ≠ ad account ID (520217301). Got snippet from LinkedIn Campaign Manager UI
- Used Next.js `<Script strategy="afterInteractive">` for both — non-blocking, loads after page hydration
- Events fire alongside existing PostHog events in demo-form.tsx, not as replacements

### Audience Strategy Defined
- **Layer 1 (now):** Website retargeting — all aurevon.ca visitors via pixel (need data to accumulate)
- **Layer 2 (once 100+ visitors):** 1% Lookalike from website visitors (Canada)
- **Layer 3 (existing):** Interest-based cold targeting via DEFAULT_FLEXIBLE_SPEC
- Copy strategy varies by funnel stage: cold = competitive paranoia, warm retarget = "try it free", hot = urgency

### Performance Snapshot (30-day, as of 2026-03-15)
- **Facebook:** $142 CAD spent, 549 clicks, 516 landing page views, $0.25 CPC, 1.5% CTR
- **LinkedIn:** ~$104 CAD spent, 172 clicks, $0.41-4.72 CPC, 0.15-2.3% CTR (high variance)
- Zero tracked conversions on both — pixel installation fixes this going forward

### Env Vars Added to Vercel (production only)
- `NEXT_PUBLIC_FACEBOOK_PIXEL_ID=2038438126722898`
- `NEXT_PUBLIC_LINKEDIN_PARTNER_ID=8940172`

### Outstanding TODOs
- Add `list-audiences`, `create-website-audience`, `create-lookalike` to fb_campaign.py
- Set up LinkedIn conversion rules in Campaign Manager, get conversion IDs
- Wire `trackLinkedInConversion()` into demo-form.tsx once conversion IDs exist
- Cross-platform reporting (/ads report pulling both platforms)
- `list-ad-copy --campaign-id` for li_campaign.py
