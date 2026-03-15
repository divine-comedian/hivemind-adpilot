"""LinkedIn campaign analytics — pull performance data by pivot.

CLI usage:
    python -m scripts.li_analytics --pivot CAMPAIGN --days 7
    python -m scripts.li_analytics --pivot CREATIVE --start 2026-03-01 --end 2026-03-14
"""

import argparse
import json
import sys
from datetime import date, timedelta
from urllib.parse import quote

import requests

from scripts.config import get_env, linkedin_headers, LINKEDIN_BASE_URL

VALID_PIVOTS = [
    "CAMPAIGN", "CREATIVE", "MEMBER_COMPANY", "MEMBER_JOB_TITLE",
    "MEMBER_INDUSTRY", "MEMBER_COUNTRY_V2",
]


def build_analytics_url(
    account_id: str,
    pivot: str,
    start_date: date,
    end_date: date,
) -> str:
    """Build the LinkedIn adAnalytics URL with date range and pivot.

    Uses Rest.li parenthesized object notation required by LinkedIn API v202602.
    """
    account_urn = quote(f"urn:li:sponsoredAccount:{account_id}", safe="")
    date_range = (
        f"(start:(year:{start_date.year},month:{start_date.month},day:{start_date.day}),"
        f"end:(year:{end_date.year},month:{end_date.month},day:{end_date.day}))"
    )
    return (
        f"{LINKEDIN_BASE_URL}/adAnalytics"
        f"?q=analytics"
        f"&pivot={pivot}"
        f"&dateRange={date_range}"
        f"&timeGranularity=ALL"
        f"&accounts=List({account_urn})"
        f"&fields=impressions,clicks,costInLocalCurrency,landingPageClicks,"
        f"likes,shares,externalWebsiteConversions"
    )


def fetch_analytics(
    account_id: str,
    pivot: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Fetch analytics from LinkedIn API. Returns list of element dicts.

    Exits with error on auth failure (401/403) or network error.
    """
    url = build_analytics_url(account_id, pivot, start_date, end_date)

    try:
        resp = requests.get(url, headers=linkedin_headers())
    except requests.RequestException as e:
        print(f"Error: Network error fetching analytics: {e}", file=sys.stderr)
        sys.exit(1)

    if resp.status_code in (401, 403):
        print(
            f"Error: LinkedIn token invalid (HTTP {resp.status_code}). "
            f"Regenerate your access token and update .env",
            file=sys.stderr,
        )
        sys.exit(1)

    if resp.status_code != 200:
        print(f"Error: LinkedIn API returned HTTP {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)

    return resp.json().get("elements", [])


def main():
    parser = argparse.ArgumentParser(description="Pull LinkedIn campaign analytics")
    parser.add_argument("--pivot", choices=VALID_PIVOTS, default="CAMPAIGN", help="Analytics pivot")
    parser.add_argument("--days", type=int, default=7, help="Number of days to look back (default: 7)")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD), overrides --days")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD), defaults to today")
    args = parser.parse_args()

    account_id = get_env("LINKEDIN_AD_ACCOUNT_ID")
    end_date = date.fromisoformat(args.end) if args.end else date.today()
    start_date = date.fromisoformat(args.start) if args.start else end_date - timedelta(days=args.days)

    elements = fetch_analytics(account_id, args.pivot, start_date, end_date)
    json.dump(elements, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
