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
