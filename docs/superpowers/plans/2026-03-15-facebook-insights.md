# Facebook Insights Integration — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `fb_insights.py` and `fb_auth.py` scripts that pull Facebook ad performance data via the Graph API, mirroring the LinkedIn analytics pattern, and update config/tests to support cross-platform reporting.

**Architecture:** Thin CLI wrappers over Facebook Graph API v25.0. `fb_auth.py` validates the token, `fb_insights.py` fetches insights at account/campaign/ad level. Both follow the same patterns as `li_auth.py` and `li_analytics.py` — argparse CLI, JSON to stdout, errors to stderr, non-zero exit on failure. Facebook authenticates via access_token query parameter (not Authorization header like LinkedIn).

**Tech Stack:** Python 3, requests, python-dotenv, pytest + unittest.mock

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `scripts/config.py` | Modify | Add `FACEBOOK_BASE_URL`, `facebook_params()` helper |
| `scripts/fb_auth.py` | Create | Token validation via `GET /act_{id}` |
| `scripts/fb_insights.py` | Create | Account/campaign/ad-level insights fetching |
| `tests/conftest.py` | Modify | Add Facebook env vars to mock fixture |
| `tests/test_fb_auth.py` | Create | Token validation tests |
| `tests/test_fb_insights.py` | Create | Insights fetching + URL building tests |

---

## Chunk 1: Config + Auth

### Task 1: Add Facebook config to `config.py`

**Files:**
- Modify: `scripts/config.py`

- [ ] **Step 1: Add Facebook base URL and auth helper**

Add after the existing LinkedIn constants at the bottom of `scripts/config.py`:

```python
FACEBOOK_BASE_URL = "https://graph.facebook.com/v25.0"


def facebook_params() -> dict:
    """Return default query params with Facebook access token."""
    return {"access_token": get_env("FACEBOOK_ACCESS_TOKEN")}
```

- [ ] **Step 2: Run existing tests to confirm no regressions**

Run: `pytest tests/ -v`
Expected: All existing tests PASS

- [ ] **Step 3: Commit**

```bash
git add scripts/config.py
git commit -m "feat: add Facebook base URL and auth helper to config"
```

---

### Task 2: Add Facebook env vars to test fixtures

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add Facebook mock env vars**

Add to the `mock_env` fixture in `tests/conftest.py`, after the existing `monkeypatch.setenv` calls:

```python
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "test-fb-token-456")
    monkeypatch.setenv("FACEBOOK_AD_ACCOUNT_ID", "22243234")
```

- [ ] **Step 2: Run existing tests to confirm no regressions**

Run: `pytest tests/ -v`
Expected: All existing tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add Facebook env vars to mock fixture"
```

---

### Task 3: Write `fb_auth.py` — token validation

**Files:**
- Create: `scripts/fb_auth.py`
- Create: `tests/test_fb_auth.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_fb_auth.py`:

```python
"""Tests for Facebook auth helpers — token validation."""

import pytest
import requests
from unittest.mock import patch, MagicMock

from scripts.fb_auth import validate_token


class TestValidateToken:
    @patch("scripts.fb_auth.requests.get")
    def test_valid_token_returns_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "id": "act_22243234",
                "name": "Aurevon Intelligence",
                "account_status": 1,
                "currency": "CAD",
                "balance": "0",
            },
        )
        result = validate_token()
        assert result["valid"] is True
        assert result["account_id"] == "22243234"
        assert result["account_name"] == "Aurevon Intelligence"
        assert result["currency"] == "CAD"

    @patch("scripts.fb_auth.requests.get")
    def test_expired_token_returns_failure(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=400,
            json=lambda: {
                "error": {
                    "message": "Error validating access token: Session has expired",
                    "type": "OAuthException",
                    "code": 190,
                }
            },
        )
        result = validate_token()
        assert result["valid"] is False
        assert "expired" in result["error"].lower() or "190" in result["error"]

    @patch("scripts.fb_auth.requests.get")
    def test_invalid_token_returns_failure(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=400,
            json=lambda: {
                "error": {
                    "message": "Invalid OAuth access token",
                    "type": "OAuthException",
                    "code": 190,
                }
            },
        )
        result = validate_token()
        assert result["valid"] is False

    @patch("scripts.fb_auth.requests.get")
    def test_network_error_returns_failure(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("DNS failure")
        result = validate_token()
        assert result["valid"] is False
        assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_fb_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.fb_auth'`

- [ ] **Step 3: Write the implementation**

Create `scripts/fb_auth.py`:

```python
"""Facebook authentication helpers — token validation.

Validates the Facebook access token by fetching the ad account.

CLI usage:
    python -m scripts.fb_auth
"""

import json
import sys

import requests

from scripts.config import get_env, facebook_params, FACEBOOK_BASE_URL


def validate_token() -> dict:
    """Validate Facebook access token by fetching the ad account.

    Returns dict with 'valid' (bool) and either account info or 'error' string.
    """
    account_id = get_env("FACEBOOK_AD_ACCOUNT_ID").removeprefix("act_")
    url = f"{FACEBOOK_BASE_URL}/act_{account_id}"
    params = {**facebook_params(), "fields": "id,name,account_status,currency,balance"}

    try:
        resp = requests.get(url, params=params)
    except requests.RequestException as e:
        return {"valid": False, "error": f"Network error: {e}"}

    if resp.status_code == 200:
        data = resp.json()
        return {
            "valid": True,
            "account_id": data.get("id", "").replace("act_", ""),
            "account_name": data.get("name"),
            "account_status": data.get("account_status"),
            "currency": data.get("currency"),
            "balance": data.get("balance"),
        }

    try:
        error_body = resp.json()
        error_data = error_body.get("error", {})
        error_msg = error_data.get("message", str(error_body))
    except Exception:
        error_msg = resp.text

    return {"valid": False, "error": f"HTTP {resp.status_code}: {error_msg}"}


def main():
    result = validate_token()
    json.dump(result, sys.stdout, indent=2)
    print()
    if not result["valid"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_fb_auth.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/fb_auth.py tests/test_fb_auth.py
git commit -m "feat: add Facebook token validation (fb_auth.py)"
```

---

## Chunk 2: Facebook Insights

### Task 4: Write `fb_insights.py` — insights fetching

**Files:**
- Create: `scripts/fb_insights.py`
- Create: `tests/test_fb_insights.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_fb_insights.py`:

```python
"""Tests for fb_insights.py — Facebook ad insights."""

import json
from datetime import date
from unittest.mock import patch, MagicMock

import pytest
import requests as requests_lib

from scripts.fb_insights import fetch_insights, build_insights_url


ACCOUNT_ID = "22243234"


class TestBuildInsightsUrl:
    def test_account_level_url(self):
        url, params = build_insights_url(
            account_id=ACCOUNT_ID,
            level="account",
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 14),
        )
        assert f"act_{ACCOUNT_ID}/insights" in url
        assert "2026-03-08" in params["time_range"]
        assert "2026-03-14" in params["time_range"]
        assert "level" not in params

    def test_campaign_level_url(self):
        url, params = build_insights_url(
            account_id=ACCOUNT_ID,
            level="campaign",
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 14),
        )
        assert f"act_{ACCOUNT_ID}/insights" in url
        assert params["level"] == "campaign"

    def test_ad_level_url(self):
        url, params = build_insights_url(
            account_id=ACCOUNT_ID,
            level="ad",
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 14),
        )
        assert params["level"] == "ad"

    def test_includes_required_fields(self):
        url, params = build_insights_url(
            account_id=ACCOUNT_ID,
            level="account",
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 14),
        )
        fields = params["fields"]
        assert "impressions" in fields
        assert "clicks" in fields
        assert "spend" in fields
        assert "cpc" in fields
        assert "ctr" in fields
        assert "actions" in fields

    def test_strips_act_prefix_if_present(self):
        url, params = build_insights_url(
            account_id=f"act_{ACCOUNT_ID}",
            level="account",
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 14),
        )
        assert f"act_{ACCOUNT_ID}/insights" in url
        assert f"act_act_{ACCOUNT_ID}" not in url


class TestFetchInsights:
    @patch("scripts.fb_insights.requests.get")
    def test_returns_parsed_data(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [
                    {
                        "campaign_name": "Aurevon Traffic",
                        "campaign_id": "120218765432",
                        "impressions": "15234",
                        "clicks": "429",
                        "spend": "111.00",
                        "cpc": "0.26",
                        "ctr": "2.82",
                        "actions": [
                            {"action_type": "landing_page_view", "value": "429"}
                        ],
                    }
                ],
            },
        )
        result = fetch_insights(
            account_id=ACCOUNT_ID,
            level="campaign",
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 14),
        )
        assert len(result) == 1
        assert result[0]["impressions"] == "15234"
        assert result[0]["clicks"] == "429"

    @patch("scripts.fb_insights.requests.get")
    def test_handles_pagination(self, mock_get):
        """Facebook paginates large result sets via paging.next URL."""
        page1_response = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [{"campaign_id": "111", "impressions": "100"}],
                "paging": {"next": "https://graph.facebook.com/v25.0/page2"},
            },
        )
        page2_response = MagicMock(
            status_code=200,
            json=lambda: {
                "data": [{"campaign_id": "222", "impressions": "200"}],
            },
        )
        mock_get.side_effect = [page1_response, page2_response]

        result = fetch_insights(
            account_id=ACCOUNT_ID,
            level="campaign",
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 14),
        )
        assert len(result) == 2
        assert mock_get.call_count == 2

    @patch("scripts.fb_insights.requests.get")
    def test_auth_error_exits(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=400,
            text='{"error":{"message":"Error validating access token","type":"OAuthException","code":190}}',
            json=lambda: {
                "error": {
                    "message": "Error validating access token",
                    "type": "OAuthException",
                    "code": 190,
                }
            },
        )
        with pytest.raises(SystemExit):
            fetch_insights(
                account_id=ACCOUNT_ID,
                level="campaign",
                start_date=date(2026, 3, 8),
                end_date=date(2026, 3, 14),
            )

    @patch("scripts.fb_insights.requests.get")
    def test_empty_data_returns_empty_list(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"data": []},
        )
        result = fetch_insights(
            account_id=ACCOUNT_ID,
            level="account",
            start_date=date(2026, 3, 8),
            end_date=date(2026, 3, 14),
        )
        assert result == []

    @patch("scripts.fb_insights.requests.get")
    def test_network_error_exits(self, mock_get):
        mock_get.side_effect = requests_lib.ConnectionError("DNS failure")
        with pytest.raises(SystemExit):
            fetch_insights(
                account_id=ACCOUNT_ID,
                level="campaign",
                start_date=date(2026, 3, 8),
                end_date=date(2026, 3, 14),
            )

    @patch("scripts.fb_insights.requests.get")
    def test_rate_limit_error_exits(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=400,
            text='{"error":{"message":"Too many calls","type":"OAuthException","code":613}}',
            json=lambda: {
                "error": {
                    "message": "Too many calls",
                    "type": "OAuthException",
                    "code": 613,
                }
            },
        )
        with pytest.raises(SystemExit):
            fetch_insights(
                account_id=ACCOUNT_ID,
                level="campaign",
                start_date=date(2026, 3, 8),
                end_date=date(2026, 3, 14),
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_fb_insights.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.fb_insights'`

- [ ] **Step 3: Write the implementation**

Create `scripts/fb_insights.py`:

```python
"""Facebook ad insights — pull performance data by level.

CLI usage:
    python -m scripts.fb_insights --level campaign --days 7
    python -m scripts.fb_insights --level ad --start 2026-03-01 --end 2026-03-14
    python -m scripts.fb_insights --level account --days 30
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_fb_insights.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/fb_insights.py tests/test_fb_insights.py
git commit -m "feat: add Facebook insights fetching (fb_insights.py)"
```

---

## Chunk 3: Live Smoke Test

### Task 5: Smoke test against live Facebook API

**Files:** None (manual verification)

- [ ] **Step 1: Validate token**

Run: `python -m scripts.fb_auth`
Expected: JSON with `"valid": true`, account name, currency CAD

- [ ] **Step 2: Pull account-level insights (last 30 days)**

Run: `python -m scripts.fb_insights --level account --days 30`
Expected: JSON array with at least one element containing impressions, clicks, spend

- [ ] **Step 3: Pull campaign-level insights (last 30 days)**

Run: `python -m scripts.fb_insights --level campaign --days 30`
Expected: JSON array with campaign_name, campaign_id for the traffic campaign

- [ ] **Step 4: Pull ad-level insights (last 30 days)**

Run: `python -m scripts.fb_insights --level ad --days 30`
Expected: JSON array with ad_name, ad_id, per-ad metrics

- [ ] **Step 5: Verify cross-platform data is comparable**

Run both:
```bash
python -m scripts.fb_insights --level campaign --days 7
python -m scripts.li_analytics --pivot CAMPAIGN --days 7
```
Expected: Both return JSON with comparable metric fields (impressions, clicks, spend/costInLocalCurrency)

- [ ] **Step 6: Fix any issues found during smoke testing**

If API returns unexpected fields or errors, adjust `FIELDS` list or error handling accordingly.

- [ ] **Step 7: Commit any fixes**

```bash
git add -u
git commit -m "fix: adjust fb_insights for live API responses"
```
