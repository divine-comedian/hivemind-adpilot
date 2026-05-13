"""Pre-warm Aurevon's intelligence reports so the live demo doesn't wait an hour.

This is per-business setup, not "building" — it satisfies the hackathon rule.
Run this once before the demo. Re-runs are safely no-ops if reports already exist.

Usage:
    HIVEMIND_API_KEY=... AUREVON_PROJECT_ID=<uuid> python -m scripts.prewarm_aurevon
"""

import os
import sys
from server.hivemind.client import HivemindClient


def main():
    base = os.environ.get("HIVEMIND_BASE_URL", "https://hivemind.myosin.xyz")
    api_key = os.environ.get("HIVEMIND_API_KEY")
    if not api_key:
        print("Set HIVEMIND_API_KEY first", file=sys.stderr)
        sys.exit(1)
    hm = HivemindClient(
        api_key=api_key,
        intel_key=os.environ.get("HIVEMIND_INTELLIGENCE_API_KEY", api_key),
        base_url=base,
    )

    project_id = os.environ.get("AUREVON_PROJECT_ID")
    if not project_id:
        print("Set AUREVON_PROJECT_ID to the Hivemind project for Aurevon", file=sys.stderr)
        sys.exit(1)

    description = (
        "Aurevon Intelligence delivers $25 AI-powered intelligence reports in five minutes — "
        "competitive analysis, market positioning, and custom research for SMBs. Free demo, "
        "paid unlock. Audiences: data-curious operators, founders pre-PMF, sports analysts."
    )

    for report_type in ("competitive_intelligence", "attention_landscape"):
        existing = hm.intelligence_get_report(project_id, report_type)
        if existing:
            short_id = str(existing.get("id", "?"))[:8]
            print(f"{report_type}: already exists ({short_id}...)")
            continue
        resp = hm.intelligence_generate(
            report_type=report_type,
            project_id=project_id,
            description=description,
            audiences=["data-curious operators", "sports analysts", "SMB founders"],
        )
        job_id = resp.get("data", {}).get("job_id")
        print(f"{report_type}: queued {job_id}")

    print("Done. Reports may take up to an hour to complete.")


if __name__ == "__main__":
    main()
