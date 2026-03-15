"""Facebook authentication helpers — token validation.

Validates the Facebook access token by fetching the ad account.

CLI usage:
    python3 -m scripts.fb_auth
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
            "account_id": data.get("id", "").removeprefix("act_"),
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
