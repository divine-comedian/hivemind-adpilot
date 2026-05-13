"""Normalize LinkedIn + Facebook ad-level perf into one schema."""

from __future__ import annotations
from typing import Any


def normalize_li_row(row: dict) -> dict[str, Any]:
    return {
        "platform": "linkedin",
        "ad_id": (row.get("pivotValues") or [None])[0] or row.get("creative_id", ""),
        "ad_name": row.get("creative_name", ""),
        "impressions": int(row.get("impressions", 0)),
        "clicks": int(row.get("clicks", 0)),
        "spend": float(row.get("costInLocalCurrency", 0)),
        "ctr": float(row.get("ctr", 0)),
        "cpm": float(row.get("costPerImpression", 0)) * 1000,
        "conversions": int(row.get("externalWebsiteConversions", 0)),
        "status": row.get("status", "UNKNOWN"),
    }


def normalize_fb_row(row: dict) -> dict[str, Any]:
    actions = {a["action_type"]: int(a["value"]) for a in row.get("actions", []) if isinstance(a, dict)}
    return {
        "platform": "facebook",
        "ad_id": row.get("ad_id", ""),
        "ad_name": row.get("ad_name", ""),
        "impressions": int(row.get("impressions", 0)),
        "clicks": int(row.get("clicks", 0)),
        "spend": float(row.get("spend", 0)),
        "ctr": float(row.get("ctr", 0)) / 100.0 if row.get("ctr") else 0.0,
        "cpm": float(row.get("cpm", 0)),
        "conversions": actions.get("landing_page_view", 0),
        "status": "ACTIVE",
    }
