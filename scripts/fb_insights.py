"""Facebook ad insights — pull performance data by level.

CLI usage:
    python3 -m scripts.fb_insights --level campaign --days 7
    python3 -m scripts.fb_insights --level ad --start 2026-03-01 --end 2026-03-14
    python3 -m scripts.fb_insights --level account --days 30
"""

import argparse
import json
import sys
from datetime import date, timedelta

import requests

from scripts.config import get_env, facebook_params, FACEBOOK_BASE_URL

VALID_LEVELS = ["account", "campaign", "ad"]

FIELDS = [
    "campaign_name",
    "campaign_id",
    "adset_name",
    "adset_id",
    "ad_name",
    "ad_id",
    "impressions",
    "clicks",
    "spend",
    "cpc",
    "cpm",
    "ctr",
    "reach",
    "actions",
    "cost_per_action_type",
    "created_time",
]


def build_insights_url(
    account_id: str,
    level: str,
    start_date: date,
    end_date: date,
) -> tuple[str, dict]:
    """Build the Facebook insights base URL and params dict.

    Returns (url, params) tuple. All query params go through requests
    to handle URL encoding correctly (especially time_range JSON).

    Account-level: GET /act_{id}/insights
    Campaign/ad-level: GET /act_{id}/insights?level=campaign|ad
    """
    account_id = account_id.removeprefix("act_")
    url = f"{FACEBOOK_BASE_URL}/act_{account_id}/insights"
    time_range = json.dumps({"since": start_date.isoformat(), "until": end_date.isoformat()})

    params = {
        "fields": ",".join(FIELDS),
        "time_range": time_range,
    }
    if level != "account":
        params["level"] = level

    return url, params


def fetch_insights(
    account_id: str,
    level: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Fetch insights from Facebook Graph API. Returns list of data dicts.

    Handles pagination via paging.next URLs.
    Exits with error on auth failure or network error.
    """
    url, params = build_insights_url(account_id, level, start_date, end_date)
    params.update(facebook_params())
    all_data = []

    while url:
        try:
            resp = requests.get(url, params=params)
        except requests.RequestException as e:
            print(f"Error: Network error fetching insights: {e}", file=sys.stderr)
            sys.exit(1)

        if resp.status_code != 200:
            try:
                error_body = resp.json()
                error_data = error_body.get("error", {})
                error_msg = error_data.get("message", str(error_body))
                error_code = error_data.get("code", "")
            except Exception:
                error_msg = resp.text
                error_code = ""

            if error_code == 190:
                print(
                    f"Error: Facebook token invalid ({error_msg}). "
                    f"Regenerate at Meta Business Settings and update .env",
                    file=sys.stderr,
                )
            else:
                print(
                    f"Error: Facebook API returned HTTP {resp.status_code}: {error_msg}",
                    file=sys.stderr,
                )
            sys.exit(1)

        body = resp.json()
        all_data.extend(body.get("data", []))

        # Pagination: Facebook embeds all params in the paging.next URL
        url = body.get("paging", {}).get("next")
        params = {}

    return all_data


def main():
    parser = argparse.ArgumentParser(description="Pull Facebook ad insights")
    parser.add_argument(
        "--level", choices=VALID_LEVELS, default="campaign",
        help="Insights level (default: campaign)",
    )
    parser.add_argument("--days", type=int, default=7, help="Days to look back (default: 7)")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD), overrides --days")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD), defaults to today")
    args = parser.parse_args()

    account_id = get_env("FACEBOOK_AD_ACCOUNT_ID")
    end_date = date.fromisoformat(args.end) if args.end else date.today()
    start_date = date.fromisoformat(args.start) if args.start else end_date - timedelta(days=args.days)

    data = fetch_insights(account_id, args.level, start_date, end_date)
    json.dump(data, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
