# LinkedIn Scripts Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build thin Python CLI scripts for LinkedIn ad analytics and campaign management, plus a shared session guard.

**Architecture:** Scripts are thin API wrappers that read credentials from `.env` via `python-dotenv`, make REST API calls to LinkedIn Marketing API v202602, and output structured JSON to stdout. Errors go to stderr with non-zero exit codes. CLI scripts use argparse; `li_auth.py` is a library module (no CLI) imported by other scripts. `session_guard.py` tracks per-session spend/image caps via a local JSON file.

**Deferred:** The `q=statistics` multi-pivot analytics endpoint (spec line 115) is not included in this plan. It will be added when SKILL.md orchestration needs multi-pivot cross-cutting analysis.

**Tech Stack:** Python 3.12, requests, python-dotenv, pytest, pytest-mock

**Spec:** `docs/specs/2026-03-14-aurevon-ads-skill-design.md`

---

## Chunk 1: Project Scaffolding + Session Guard

### Task 1: Project scaffolding

**Files:**
- Create: `scripts/__init__.py` (empty)
- Create: `scripts/config.py` (shared env loading + LinkedIn headers)
- Create: `tests/__init__.py` (empty)
- Create: `tests/conftest.py` (shared fixtures)
- Create: `requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
requests>=2.31.0
python-dotenv>=1.0.0
openai>=1.0.0
Pillow>=10.0.0
pytest>=8.0.0
pytest-mock>=3.14.0
```

- [ ] **Step 2: Create scripts/config.py**

```python
"""Shared configuration: env loading, LinkedIn API helpers."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (parent of scripts/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


def get_env(key: str) -> str:
    """Get required env var or exit with error."""
    value = os.getenv(key)
    if not value:
        print(f"Error: {key} not set in .env", file=sys.stderr)
        sys.exit(1)
    return value


def linkedin_headers() -> dict:
    """Return standard LinkedIn API headers with auth."""
    return {
        "Authorization": f"Bearer {get_env('LINKEDIN_ACCESS_TOKEN')}",
        "LinkedIn-Version": "202602",
        "X-Restli-Protocol-Version": "2.0.0",
    }


LINKEDIN_BASE_URL = "https://api.linkedin.com/rest"
```

- [ ] **Step 3: Create empty __init__.py files and conftest.py**

`scripts/__init__.py` — empty file.

`tests/__init__.py` — empty file.

`tests/conftest.py`:

```python
"""Shared test fixtures."""

import os
import pytest


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Set test env vars so scripts don't need a real .env."""
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "test-token-123")
    monkeypatch.setenv("LINKEDIN_AD_ACCOUNT_ID", "520217301")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
```

- [ ] **Step 4: Verify imports work**

Run: `cd /home/mitch/github/aurevon-ads && python -c "from scripts.config import linkedin_headers, LINKEDIN_BASE_URL; print('OK')"`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt scripts/__init__.py scripts/config.py tests/__init__.py tests/conftest.py
git commit -m "feat: add project scaffolding with shared config and test fixtures"
```

---

### Task 2: Session guard

**Files:**
- Create: `scripts/session_guard.py`
- Create: `tests/test_session_guard.py`

- [ ] **Step 1: Write failing tests for session guard**

`tests/test_session_guard.py`:

```python
"""Tests for session_guard.py — per-session spend and image cap enforcement."""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.session_guard import (
    SessionGuard,
    SessionOverLimitError,
    DEFAULT_MAX_SPEND,
    DEFAULT_MAX_IMAGES,
    DEFAULT_WINDOW_HOURS,
)


@pytest.fixture
def state_file(tmp_path):
    """Provide a temp path for session state."""
    return tmp_path / "session_state.json"


@pytest.fixture
def guard(state_file):
    """Create a SessionGuard with default limits using temp state file."""
    return SessionGuard(state_file=state_file)


class TestSessionGuardInit:
    def test_creates_fresh_session_on_first_use(self, guard, state_file):
        status = guard.check()
        assert status["remaining_spend"] == DEFAULT_MAX_SPEND
        assert status["remaining_images"] == DEFAULT_MAX_IMAGES
        assert state_file.exists()

    def test_loads_existing_session(self, guard, state_file):
        guard.record_spend(1.00)
        guard.record_image()

        guard2 = SessionGuard(state_file=state_file)
        status = guard2.check()
        assert status["remaining_spend"] == pytest.approx(DEFAULT_MAX_SPEND - 1.00)
        assert status["remaining_images"] == DEFAULT_MAX_IMAGES - 1


class TestSpendTracking:
    def test_record_spend_updates_total(self, guard):
        guard.record_spend(0.20)
        status = guard.check()
        assert status["remaining_spend"] == pytest.approx(DEFAULT_MAX_SPEND - 0.20)

    def test_raises_when_spend_exceeds_limit(self, guard):
        guard.record_spend(DEFAULT_MAX_SPEND - 0.01)
        with pytest.raises(SessionOverLimitError, match="spend"):
            guard.require_budget(0.20)

    def test_require_budget_passes_when_under_limit(self, guard):
        guard.require_budget(0.20)  # should not raise


class TestImageTracking:
    def test_record_image_updates_count(self, guard):
        guard.record_image()
        guard.record_image()
        status = guard.check()
        assert status["remaining_images"] == DEFAULT_MAX_IMAGES - 2

    def test_raises_when_images_exceed_limit(self, guard):
        for _ in range(DEFAULT_MAX_IMAGES):
            guard.record_image()
        with pytest.raises(SessionOverLimitError, match="image"):
            guard.require_image()


class TestSessionExpiry:
    def test_session_resets_after_window(self, guard, state_file):
        guard.record_spend(5.00)

        # Fake the session start to be past the window
        state = json.loads(state_file.read_text())
        state["session_start"] = time.time() - (DEFAULT_WINDOW_HOURS * 3600 + 1)
        state_file.write_text(json.dumps(state))

        guard2 = SessionGuard(state_file=state_file)
        status = guard2.check()
        assert status["remaining_spend"] == DEFAULT_MAX_SPEND

    def test_session_persists_within_window(self, guard, state_file):
        guard.record_spend(5.00)
        guard2 = SessionGuard(state_file=state_file)
        status = guard2.check()
        assert status["remaining_spend"] == pytest.approx(DEFAULT_MAX_SPEND - 5.00)


class TestReset:
    def test_manual_reset_clears_session(self, guard):
        guard.record_spend(5.00)
        guard.record_image()
        guard.reset()
        status = guard.check()
        assert status["remaining_spend"] == DEFAULT_MAX_SPEND
        assert status["remaining_images"] == DEFAULT_MAX_IMAGES


class TestCustomLimits:
    def test_custom_spend_limit(self, state_file, monkeypatch):
        monkeypatch.setenv("SESSION_MAX_SPEND", "5.00")
        g = SessionGuard(state_file=state_file)
        status = g.check()
        assert status["remaining_spend"] == 5.00

    def test_custom_image_limit(self, state_file, monkeypatch):
        monkeypatch.setenv("SESSION_MAX_IMAGES", "5")
        g = SessionGuard(state_file=state_file)
        status = g.check()
        assert status["remaining_images"] == 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/mitch/github/aurevon-ads && python -m pytest tests/test_session_guard.py -v`

Expected: ImportError — `scripts.session_guard` does not exist yet.

- [ ] **Step 3: Implement session_guard.py**

`scripts/session_guard.py`:

```python
"""Per-session spend and image generation cap enforcement.

Tracks cumulative spend and image count within a rolling session window.
Session resets automatically after SESSION_WINDOW_HOURS of inactivity.

CLI usage:
    python -m scripts.session_guard --check    # Show remaining budget
    python -m scripts.session_guard --reset    # Reset session
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

DEFAULT_MAX_SPEND = 10.00
DEFAULT_MAX_IMAGES = 20
DEFAULT_WINDOW_HOURS = 1

_STATE_DIR = Path(__file__).resolve().parent.parent / "memory"
_DEFAULT_STATE_FILE = _STATE_DIR / "session_state.json"


class SessionOverLimitError(Exception):
    """Raised when a session cap would be exceeded."""


class SessionGuard:
    def __init__(self, state_file: Path = _DEFAULT_STATE_FILE):
        self._state_file = Path(state_file)
        self._max_spend = float(os.getenv("SESSION_MAX_SPEND", DEFAULT_MAX_SPEND))
        self._max_images = int(os.getenv("SESSION_MAX_IMAGES", DEFAULT_MAX_IMAGES))
        self._window_seconds = float(os.getenv("SESSION_WINDOW_HOURS", DEFAULT_WINDOW_HOURS)) * 3600
        self._state = self._load_state()

    def _load_state(self) -> dict:
        if self._state_file.exists():
            state = json.loads(self._state_file.read_text())
            elapsed = time.time() - state.get("session_start", 0)
            if elapsed > self._window_seconds:
                return self._fresh_state()
            return state
        return self._fresh_state()

    def _fresh_state(self) -> dict:
        return {
            "session_start": time.time(),
            "total_spend": 0.0,
            "image_count": 0,
        }

    def _save(self) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(json.dumps(self._state, indent=2))

    def check(self) -> dict:
        """Return current session status."""
        self._save()
        return {
            "remaining_spend": round(self._max_spend - self._state["total_spend"], 2),
            "remaining_images": self._max_images - self._state["image_count"],
            "total_spend": round(self._state["total_spend"], 2),
            "image_count": self._state["image_count"],
            "max_spend": self._max_spend,
            "max_images": self._max_images,
        }

    def require_budget(self, amount: float) -> None:
        """Raise if spending amount would exceed session limit."""
        if self._state["total_spend"] + amount > self._max_spend:
            remaining = round(self._max_spend - self._state["total_spend"], 2)
            raise SessionOverLimitError(
                f"Session spend limit reached. Remaining: ${remaining}, requested: ${amount}"
            )

    def require_image(self) -> None:
        """Raise if generating another image would exceed session limit."""
        if self._state["image_count"] >= self._max_images:
            raise SessionOverLimitError(
                f"Session image limit reached ({self._max_images} images)"
            )

    def record_spend(self, amount: float) -> None:
        """Record a spend event."""
        self._state["total_spend"] += amount
        self._save()

    def record_image(self) -> None:
        """Record an image generation event."""
        self._state["image_count"] += 1
        self._save()

    def reset(self) -> None:
        """Manually reset the session."""
        self._state = self._fresh_state()
        self._save()


def main():
    parser = argparse.ArgumentParser(description="Session budget guard")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Show remaining budget")
    group.add_argument("--reset", action="store_true", help="Reset session")
    args = parser.parse_args()

    guard = SessionGuard()

    if args.check:
        status = guard.check()
        json.dump(status, sys.stdout, indent=2)
        print()
    elif args.reset:
        guard.reset()
        print("Session reset.", file=sys.stderr)
        status = guard.check()
        json.dump(status, sys.stdout, indent=2)
        print()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/mitch/github/aurevon-ads && python -m pytest tests/test_session_guard.py -v`

Expected: All 12 tests PASS.

- [ ] **Step 5: Test CLI interface manually**

Run: `cd /home/mitch/github/aurevon-ads && python -m scripts.session_guard --check`

Expected: JSON output with `remaining_spend: 10.0`, `remaining_images: 20`.

- [ ] **Step 6: Commit**

```bash
git add scripts/session_guard.py tests/test_session_guard.py
git commit -m "feat: add session guard with spend and image cap enforcement"
```

---

## Chunk 2: LinkedIn Analytics

### Task 3: Token validation helper

**Files:**
- Create: `scripts/li_auth.py` (library module — token validation, no CLI entrypoint)
- Create: `tests/test_li_auth.py`

- [ ] **Step 1: Write failing tests for token validation**

`tests/test_li_auth.py`:

```python
"""Tests for LinkedIn auth helpers — token validation."""

import pytest
import requests
from unittest.mock import patch, MagicMock

from scripts.li_auth import validate_token


class TestValidateToken:
    @patch("scripts.li_auth.requests.get")
    def test_valid_token_returns_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"id": 520217301, "name": "Aurevon Intelligence", "status": "ACTIVE"},
        )
        result = validate_token()
        assert result["valid"] is True
        assert result["account_name"] == "Aurevon Intelligence"

    @patch("scripts.li_auth.requests.get")
    def test_expired_token_returns_failure(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=401,
            json=lambda: {"status": 401, "code": "EXPIRED_ACCESS_TOKEN"},
        )
        result = validate_token()
        assert result["valid"] is False
        assert "expired" in result["error"].lower() or "401" in result["error"]

    @patch("scripts.li_auth.requests.get")
    def test_forbidden_returns_failure(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=403,
            json=lambda: {"status": 403, "message": "Not enough permissions"},
        )
        result = validate_token()
        assert result["valid"] is False

    @patch("scripts.li_auth.requests.get")
    def test_network_error_returns_failure(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("DNS failure")
        result = validate_token()
        assert result["valid"] is False
        assert "error" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/mitch/github/aurevon-ads && python -m pytest tests/test_li_auth.py -v`

Expected: ImportError — `scripts.li_auth` does not exist yet.

- [ ] **Step 3: Implement li_auth.py**

`scripts/li_auth.py`:

```python
"""LinkedIn authentication helpers — token validation."""

import requests
from scripts.config import get_env, linkedin_headers, LINKEDIN_BASE_URL


def validate_token() -> dict:
    """Validate LinkedIn access token by fetching the ad account.

    Returns dict with 'valid' (bool) and either account info or 'error' string.
    """
    account_id = get_env("LINKEDIN_AD_ACCOUNT_ID")
    url = f"{LINKEDIN_BASE_URL}/adAccounts/{account_id}"

    try:
        resp = requests.get(url, headers=linkedin_headers())
    except requests.RequestException as e:
        return {"valid": False, "error": f"Network error: {e}"}

    if resp.status_code == 200:
        data = resp.json()
        return {
            "valid": True,
            "account_id": data.get("id"),
            "account_name": data.get("name"),
            "status": data.get("status"),
            "currency": data.get("currency"),
        }

    try:
        error_body = resp.json()
        error_msg = error_body.get("message", error_body.get("code", "Unknown error"))
    except Exception:
        error_msg = resp.text

    return {"valid": False, "error": f"HTTP {resp.status_code}: {error_msg}"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/mitch/github/aurevon-ads && python -m pytest tests/test_li_auth.py -v`

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/li_auth.py tests/test_li_auth.py
git commit -m "feat: add LinkedIn token validation helper"
```

---

### Task 4: LinkedIn analytics script

**Files:**
- Create: `scripts/li_analytics.py`
- Create: `tests/test_li_analytics.py`

- [ ] **Step 1: Write failing tests for analytics**

`tests/test_li_analytics.py`:

```python
"""Tests for li_analytics.py — LinkedIn campaign analytics."""

import json
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import pytest
import requests as requests_lib

from scripts.li_analytics import fetch_analytics, build_analytics_url


ACCOUNT_ID = "520217301"


class TestBuildAnalyticsUrl:
    def test_campaign_pivot_default_date_range(self):
        url = build_analytics_url(
            account_id=ACCOUNT_ID,
            pivot="CAMPAIGN",
            start_date=date(2026, 3, 7),
            end_date=date(2026, 3, 14),
        )
        assert "q=analytics" in url
        assert "pivot=CAMPAIGN" in url
        assert f"accounts=urn%3Ali%3AsponsoredAccount%3A{ACCOUNT_ID}" in url
        assert "dateRange.start.year=2026" in url
        assert "dateRange.start.month=3" in url
        assert "dateRange.start.day=7" in url
        assert "dateRange.end.year=2026" in url
        assert "dateRange.end.month=3" in url
        assert "dateRange.end.day=14" in url

    def test_creative_pivot(self):
        url = build_analytics_url(
            account_id=ACCOUNT_ID,
            pivot="CREATIVE",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 14),
        )
        assert "pivot=CREATIVE" in url


class TestFetchAnalytics:
    @patch("scripts.li_analytics.requests.get")
    def test_returns_parsed_elements(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "elements": [
                    {
                        "pivotValue": "urn:li:sponsoredCampaign:555838216",
                        "impressions": 5000,
                        "clicks": 345,
                        "costInLocalCurrency": "193.00",
                        "landingPageClicks": 200,
                        "likes": 5,
                        "shares": 2,
                        "externalWebsiteConversions": 0,
                    }
                ]
            },
        )
        result = fetch_analytics(
            account_id=ACCOUNT_ID,
            pivot="CAMPAIGN",
            start_date=date(2026, 3, 7),
            end_date=date(2026, 3, 14),
        )
        assert len(result) == 1
        assert result[0]["impressions"] == 5000
        assert result[0]["clicks"] == 345

    @patch("scripts.li_analytics.requests.get")
    def test_401_raises_auth_error(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=401,
            text='{"status":401,"code":"EXPIRED_ACCESS_TOKEN"}',
            json=lambda: {"status": 401, "code": "EXPIRED_ACCESS_TOKEN"},
        )
        with pytest.raises(SystemExit):
            fetch_analytics(
                account_id=ACCOUNT_ID,
                pivot="CAMPAIGN",
                start_date=date(2026, 3, 7),
                end_date=date(2026, 3, 14),
            )

    @patch("scripts.li_analytics.requests.get")
    def test_empty_elements_returns_empty_list(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"elements": []},
        )
        result = fetch_analytics(
            account_id=ACCOUNT_ID,
            pivot="CAMPAIGN",
            start_date=date(2026, 3, 7),
            end_date=date(2026, 3, 14),
        )
        assert result == []

    @patch("scripts.li_analytics.requests.get")
    def test_network_error_exits(self, mock_get):
        mock_get.side_effect = requests_lib.ConnectionError("DNS failure")
        with pytest.raises(SystemExit):
            fetch_analytics(
                account_id=ACCOUNT_ID,
                pivot="CAMPAIGN",
                start_date=date(2026, 3, 7),
                end_date=date(2026, 3, 14),
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/mitch/github/aurevon-ads && python -m pytest tests/test_li_analytics.py -v`

Expected: ImportError — `scripts.li_analytics` does not exist yet.

- [ ] **Step 3: Implement li_analytics.py**

`scripts/li_analytics.py`:

```python
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
    """Build the LinkedIn adAnalytics URL with date range and pivot."""
    account_urn = quote(f"urn:li:sponsoredAccount:{account_id}", safe="")
    return (
        f"{LINKEDIN_BASE_URL}/adAnalytics"
        f"?q=analytics"
        f"&pivot={pivot}"
        f"&dateRange.start.year={start_date.year}"
        f"&dateRange.start.month={start_date.month}"
        f"&dateRange.start.day={start_date.day}"
        f"&dateRange.end.year={end_date.year}"
        f"&dateRange.end.month={end_date.month}"
        f"&dateRange.end.day={end_date.day}"
        f"&timeGranularity=ALL"
        f"&accounts={account_urn}"
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

    Exits with error on auth failure (401/403).
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/mitch/github/aurevon-ads && python -m pytest tests/test_li_analytics.py -v`

Expected: All 6 tests PASS.

- [ ] **Step 5: Smoke test against live API**

Run: `cd /home/mitch/github/aurevon-ads && python -m scripts.li_analytics --pivot CAMPAIGN --days 7`

Expected: JSON array of campaign analytics elements (may be empty if no activity in last 7 days). If token is valid, should not error.

- [ ] **Step 6: Commit**

```bash
git add scripts/li_analytics.py tests/test_li_analytics.py
git commit -m "feat: add LinkedIn analytics script with campaign/creative pivot support"
```

---

## Chunk 3: LinkedIn Campaign Management

### Task 5: LinkedIn campaign creation

**Files:**
- Create: `scripts/li_campaign.py`
- Create: `tests/test_li_campaign.py`

This script handles: create campaign (DRAFT), update campaign, upload image, create creative. Each is a subcommand.

- [ ] **Step 1: Write failing tests for campaign creation**

`tests/test_li_campaign.py`:

```python
"""Tests for li_campaign.py — LinkedIn campaign and creative management."""

import json
from unittest.mock import patch, MagicMock, mock_open

import pytest

from scripts.li_campaign import (
    create_campaign,
    update_campaign,
    initialize_image_upload,
    upload_image_binary,
    upload_image,
    create_creative,
)

ACCOUNT_ID = "520217301"


class TestCreateCampaign:
    @patch("scripts.li_campaign.requests.post")
    def test_creates_campaign_in_draft_status(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=201,
            headers={"x-restli-id": "555838300"},
            json=lambda: {},
        )
        result = create_campaign(
            account_id=ACCOUNT_ID,
            name="Test Campaign",
            objective="WEBSITE_VISITS",
            daily_budget_cad=50.00,
        )
        assert result["campaign_id"] == "555838300"

        # Verify the request body
        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert body["status"] == "DRAFT"
        assert body["name"] == "Test Campaign"
        assert body["dailyBudget"]["amount"] == "50.00"
        assert body["dailyBudget"]["currencyCode"] == "CAD"

    @patch("scripts.li_campaign.requests.post")
    def test_401_raises_auth_error(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=401,
            text="Unauthorized",
            json=lambda: {"status": 401},
        )
        with pytest.raises(SystemExit):
            create_campaign(
                account_id=ACCOUNT_ID,
                name="Test",
                objective="WEBSITE_VISITS",
                daily_budget_cad=50.00,
            )


class TestUpdateCampaign:
    @patch("scripts.li_campaign.requests.post")
    def test_updates_campaign_status(self, mock_post):
        mock_post.return_value = MagicMock(status_code=204)
        result = update_campaign(
            account_id=ACCOUNT_ID,
            campaign_id="555838300",
            updates={"status": "PAUSED"},
        )
        assert result["success"] is True

    @patch("scripts.li_campaign.requests.post")
    def test_update_fails_gracefully(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=400,
            text="Bad Request",
            json=lambda: {"message": "Invalid status"},
        )
        with pytest.raises(SystemExit):
            update_campaign(
                account_id=ACCOUNT_ID,
                campaign_id="555838300",
                updates={"status": "INVALID"},
            )


class TestImageUpload:
    @patch("scripts.li_campaign.requests.post")
    def test_initialize_upload_returns_upload_url_and_image_urn(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "value": {
                    "uploadUrl": "https://www.linkedin.com/dms-uploads/xxx",
                    "image": "urn:li:image:C4E22AQH1234567890",
                }
            },
        )
        result = initialize_image_upload(account_id=ACCOUNT_ID)
        assert result["upload_url"] == "https://www.linkedin.com/dms-uploads/xxx"
        assert result["image_urn"] == "urn:li:image:C4E22AQH1234567890"

    @patch("scripts.li_campaign.requests.put")
    def test_upload_binary_succeeds(self, mock_put):
        mock_put.return_value = MagicMock(status_code=201)
        result = upload_image_binary(
            upload_url="https://www.linkedin.com/dms-uploads/xxx",
            image_data=b"fake-image-bytes",
        )
        assert result["success"] is True


class TestUploadImage:
    @patch("scripts.li_campaign.upload_image_binary")
    @patch("scripts.li_campaign.initialize_image_upload")
    def test_chains_initialize_and_upload(self, mock_init, mock_upload, tmp_path):
        mock_init.return_value = {
            "upload_url": "https://www.linkedin.com/dms-uploads/xxx",
            "image_urn": "urn:li:image:C4E22AQH1234567890",
        }
        mock_upload.return_value = {"success": True}

        # Create a temp image file
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"fake-png-data")

        result = upload_image(account_id=ACCOUNT_ID, image_path=str(img_file))
        assert result["image_urn"] == "urn:li:image:C4E22AQH1234567890"
        mock_init.assert_called_once_with(ACCOUNT_ID)
        mock_upload.assert_called_once_with(
            "https://www.linkedin.com/dms-uploads/xxx",
            b"fake-png-data",
        )


class TestCreateCreative:
    @patch("scripts.li_campaign.requests.post")
    def test_creates_creative_with_image_and_copy(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=201,
            headers={"x-restli-id": "creative-id-123"},
            json=lambda: {},
        )
        result = create_creative(
            account_id=ACCOUNT_ID,
            campaign_id="555838300",
            image_urn="urn:li:image:C4E22AQH1234567890",
            headline="Custom Intelligence",
            intro_text="Get competitive insights for your business.",
            cta="LEARN_MORE",
            destination_url="https://aurevon.com",
        )
        assert result["creative_id"] == "creative-id-123"

        # Verify request body structure
        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert body["campaign"] == f"urn:li:sponsoredCampaign:555838300"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/mitch/github/aurevon-ads && python -m pytest tests/test_li_campaign.py -v`

Expected: ImportError — `scripts.li_campaign` does not exist yet.

- [ ] **Step 3: Implement li_campaign.py**

`scripts/li_campaign.py`:

```python
"""LinkedIn campaign and creative management.

CLI usage:
    python -m scripts.li_campaign create-campaign --name "Test" --objective WEBSITE_VISITS --daily-budget 50
    python -m scripts.li_campaign update-campaign --campaign-id 123 --status PAUSED
    python -m scripts.li_campaign upload-image --image-path path/to/image.png
    python -m scripts.li_campaign create-creative --campaign-id 123 --image-urn "urn:li:image:xxx" \\
        --headline "Title" --intro-text "Body" --cta LEARN_MORE --url https://aurevon.com
"""

import argparse
import json
import sys
from pathlib import Path

import requests

from scripts.config import get_env, linkedin_headers, LINKEDIN_BASE_URL

VALID_OBJECTIVES = [
    "WEBSITE_VISITS", "BRAND_AWARENESS", "ENGAGEMENT", "VIDEO_VIEWS", "LEAD_GENERATION",
]
VALID_STATUSES = ["ACTIVE", "PAUSED", "ARCHIVED", "DRAFT"]
VALID_CTAS = [
    "LEARN_MORE", "SIGN_UP", "REGISTER", "DOWNLOAD", "APPLY", "GET_QUOTE", "SUBSCRIBE",
]


def _handle_error(resp: requests.Response, context: str) -> None:
    """Print error and exit on non-success response."""
    if resp.status_code in (401, 403):
        print(
            f"Error: LinkedIn token invalid (HTTP {resp.status_code}). "
            f"Regenerate your access token and update .env",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        detail = resp.json().get("message", resp.text)
    except Exception:
        detail = resp.text
    print(f"Error ({context}): HTTP {resp.status_code}: {detail}", file=sys.stderr)
    sys.exit(1)


def create_campaign(
    account_id: str,
    name: str,
    objective: str,
    daily_budget_cad: float,
) -> dict:
    """Create a LinkedIn campaign in DRAFT status."""
    url = f"{LINKEDIN_BASE_URL}/adAccounts/{account_id}/adCampaigns"
    body = {
        "account": f"urn:li:sponsoredAccount:{account_id}",
        "name": name,
        "objective": objective,
        "status": "DRAFT",
        "type": "SPONSORED_UPDATES",
        "costType": "CPM",
        "dailyBudget": {
            "amount": f"{daily_budget_cad:.2f}",
            "currencyCode": "CAD",
        },
        "unitCost": {
            "amount": "0",
            "currencyCode": "CAD",
        },
    }
    resp = requests.post(url, headers={**linkedin_headers(), "Content-Type": "application/json"}, json=body)

    if resp.status_code not in (200, 201):
        _handle_error(resp, "create campaign")

    campaign_id = resp.headers.get("x-restli-id", "")
    return {"campaign_id": campaign_id, "status": "DRAFT", "name": name}


def update_campaign(
    account_id: str,
    campaign_id: str,
    updates: dict,
) -> dict:
    """Update a LinkedIn campaign via PARTIAL_UPDATE."""
    url = f"{LINKEDIN_BASE_URL}/adAccounts/{account_id}/adCampaigns/{campaign_id}"
    headers = {
        **linkedin_headers(),
        "Content-Type": "application/json",
        "X-RestLi-Method": "PARTIAL_UPDATE",
    }
    body = {"patch": {"$set": updates}}
    resp = requests.post(url, headers=headers, json=body)

    if resp.status_code not in (200, 204):
        _handle_error(resp, "update campaign")

    return {"success": True, "campaign_id": campaign_id, "updates": updates}


def initialize_image_upload(account_id: str) -> dict:
    """Initialize a LinkedIn image upload. Returns upload_url and image_urn."""
    url = f"{LINKEDIN_BASE_URL}/images?action=initializeUpload"
    body = {
        "initializeUploadRequest": {
            "owner": f"urn:li:sponsoredAccount:{account_id}",
        }
    }
    resp = requests.post(url, headers={**linkedin_headers(), "Content-Type": "application/json"}, json=body)

    if resp.status_code != 200:
        _handle_error(resp, "initialize image upload")

    data = resp.json()["value"]
    return {
        "upload_url": data["uploadUrl"],
        "image_urn": data["image"],
    }


def upload_image_binary(upload_url: str, image_data: bytes) -> dict:
    """Upload image binary data to LinkedIn CDN."""
    headers = {
        "Authorization": f"Bearer {get_env('LINKEDIN_ACCESS_TOKEN')}",
        "Content-Type": "application/octet-stream",
    }
    resp = requests.put(upload_url, headers=headers, data=image_data)

    if resp.status_code not in (200, 201):
        _handle_error(resp, "image upload")

    return {"success": True}


def create_creative(
    account_id: str,
    campaign_id: str,
    image_urn: str,
    headline: str,
    intro_text: str,
    cta: str,
    destination_url: str,
) -> dict:
    """Create an ad creative with image and copy."""
    url = f"{LINKEDIN_BASE_URL}/adAccounts/{account_id}/adCreatives"
    body = {
        "account": f"urn:li:sponsoredAccount:{account_id}",
        "campaign": f"urn:li:sponsoredCampaign:{campaign_id}",
        "content": {
            "singleImage": {
                "image": image_urn,
                "headline": headline,
                "callToAction": cta,
            }
        },
        "intendedStatus": "ACTIVE",
        "commentary": intro_text,
        "destinationUrl": destination_url,
    }
    resp = requests.post(url, headers={**linkedin_headers(), "Content-Type": "application/json"}, json=body)

    if resp.status_code not in (200, 201):
        _handle_error(resp, "create creative")

    creative_id = resp.headers.get("x-restli-id", "")
    return {"creative_id": creative_id, "campaign_id": campaign_id}


def upload_image(account_id: str, image_path: str) -> dict:
    """Full image upload flow: initialize + upload binary. Returns image_urn."""
    init = initialize_image_upload(account_id)
    image_data = Path(image_path).read_bytes()
    upload_image_binary(init["upload_url"], image_data)
    return {"image_urn": init["image_urn"], "upload_url": init["upload_url"]}


def main():
    parser = argparse.ArgumentParser(description="LinkedIn campaign management")
    sub = parser.add_subparsers(dest="command", required=True)

    # create-campaign
    p_create = sub.add_parser("create-campaign")
    p_create.add_argument("--name", required=True)
    p_create.add_argument("--objective", choices=VALID_OBJECTIVES, default="WEBSITE_VISITS")
    p_create.add_argument("--daily-budget", type=float, required=True, help="Daily budget in CAD")

    # update-campaign
    p_update = sub.add_parser("update-campaign")
    p_update.add_argument("--campaign-id", required=True)
    p_update.add_argument("--status", choices=VALID_STATUSES)
    p_update.add_argument("--name", type=str)
    p_update.add_argument("--daily-budget", type=float)

    # upload-image
    p_img = sub.add_parser("upload-image")
    p_img.add_argument("--image-path", required=True, help="Path to image file")

    # create-creative
    p_creative = sub.add_parser("create-creative")
    p_creative.add_argument("--campaign-id", required=True)
    p_creative.add_argument("--image-urn", required=True)
    p_creative.add_argument("--headline", required=True)
    p_creative.add_argument("--intro-text", required=True)
    p_creative.add_argument("--cta", choices=VALID_CTAS, default="LEARN_MORE")
    p_creative.add_argument("--url", required=True, help="Destination URL")

    args = parser.parse_args()
    account_id = get_env("LINKEDIN_AD_ACCOUNT_ID")

    if args.command == "create-campaign":
        result = create_campaign(account_id, args.name, args.objective, args.daily_budget)
    elif args.command == "update-campaign":
        updates = {}
        if args.status:
            updates["status"] = args.status
        if args.name:
            updates["name"] = args.name
        if args.daily_budget:
            updates["dailyBudget"] = {"amount": f"{args.daily_budget:.2f}", "currencyCode": "CAD"}
        result = update_campaign(account_id, args.campaign_id, updates)
    elif args.command == "upload-image":
        result = upload_image(account_id, args.image_path)
    elif args.command == "create-creative":
        result = create_creative(
            account_id, args.campaign_id, args.image_urn,
            args.headline, args.intro_text, args.cta, args.url,
        )

    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/mitch/github/aurevon-ads && python -m pytest tests/test_li_campaign.py -v`

Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/li_campaign.py tests/test_li_campaign.py
git commit -m "feat: add LinkedIn campaign management with create, update, image upload, and creative creation"
```

---

### Task 6: Live integration smoke test

This is a manual verification step — read-only API calls only.

- [ ] **Step 1: Validate token**

Run: `cd /home/mitch/github/aurevon-ads && python -c "from scripts.li_auth import validate_token; import json; print(json.dumps(validate_token(), indent=2))"`

Expected: `{"valid": true, "account_name": "Aurevon Intelligence", ...}`

- [ ] **Step 2: Pull last 7 days of analytics**

Run: `cd /home/mitch/github/aurevon-ads && python -m scripts.li_analytics --pivot CAMPAIGN --days 7`

Expected: JSON array of analytics data (may be empty if no recent activity).

- [ ] **Step 3: Run full test suite**

Run: `cd /home/mitch/github/aurevon-ads && python -m pytest tests/ -v`

Expected: All tests PASS.

- [ ] **Step 4: Commit (if any fixups needed)**

Only if smoke tests revealed issues that required code changes.
