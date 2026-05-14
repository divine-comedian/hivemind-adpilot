"""Pulls and merges LinkedIn + Facebook ad-level perf for the workspace."""

from datetime import date, timedelta
from fastapi import APIRouter

from server.deps import workspace_store
from server.normalize.metrics import normalize_li_row, normalize_fb_row
from scripts import li_analytics, fb_insights


router = APIRouter()


@router.get("/analytics")
def get_analytics(window: str = "30d"):
    days = int(window.rstrip("d"))
    state = workspace_store().load()
    if not state:
        return {"rows": [], "summary": {}}

    end = date.today()
    start = end - timedelta(days=days)

    rows: list[dict] = []

    li_account = state["platforms"]["linkedin"]["account_id"]
    try:
        # scripts/ may call sys.exit() on failure — catch SystemExit too
        elements = li_analytics.fetch_analytics(
            account_id=li_account, pivot="CREATIVE", start_date=start, end_date=end
        )
        for r in elements:
            rows.append(normalize_li_row(r))
    except (Exception, SystemExit) as exc:
        rows.append({"platform": "linkedin", "error": f"{type(exc).__name__}: {exc}"})

    fb_account = state["platforms"]["facebook"]["account_id"]
    try:
        data = fb_insights.fetch_insights(
            account_id=fb_account, level="ad", start_date=start, end_date=end
        )
        for r in data:
            rows.append(normalize_fb_row(r))
    except (Exception, SystemExit) as exc:
        rows.append({"platform": "facebook", "error": f"{type(exc).__name__}: {exc}"})

    valid = [r for r in rows if "error" not in r]
    summary = {
        "total_spend": round(sum(r["spend"] for r in valid), 2),
        "total_impressions": sum(r["impressions"] for r in valid),
        "total_clicks": sum(r["clicks"] for r in valid),
        "total_conversions": sum(r["conversions"] for r in valid),
        "avg_ctr": round(sum(r["ctr"] for r in valid) / len(valid), 4) if valid else 0,
        "avg_cpm": round(sum(r["cpm"] for r in valid) / len(valid), 2) if valid else 0,
    }
    return {"rows": rows, "summary": summary}
