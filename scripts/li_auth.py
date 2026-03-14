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
