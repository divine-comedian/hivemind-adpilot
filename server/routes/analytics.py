"""Pulls and merges LinkedIn + Facebook ad-level perf for the workspace."""

from datetime import date, timedelta
from fastapi import APIRouter

from server.deps import workspace_store
from server.demo import analytics_summary, demo_analytics_rows, demo_mode
from server.normalize.metrics import normalize_li_row, normalize_fb_row
from scripts import li_analytics, fb_insights


router = APIRouter()


@router.get("/analytics")
def get_analytics(window: str = "30d"):
    days = int(window.rstrip("d"))
    if demo_mode():
        rows = demo_analytics_rows()
        return {"rows": rows, "summary": analytics_summary(rows)}

    state = workspace_store().load()
    if not state:
        return {"rows": [], "summary": {}}

    end = date.today()
    start = end - timedelta(days=days)

    rows: list[dict] = []
    platforms_state = state.get("platforms", {})

    li = platforms_state.get("linkedin")
    if li:
        try:
            elements = li_analytics.fetch_analytics(
                account_id=li["account_id"], pivot="CREATIVE", start_date=start, end_date=end
            )
            for r in elements:
                rows.append(normalize_li_row(r))
        except (Exception, SystemExit) as exc:
            rows.append({"platform": "linkedin", "error": f"{type(exc).__name__}: {exc}"})

    fb = platforms_state.get("facebook")
    if fb:
        try:
            data = fb_insights.fetch_insights(
                account_id=fb["account_id"], level="ad", start_date=start, end_date=end
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
