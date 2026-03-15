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

FACEBOOK_BASE_URL = "https://graph.facebook.com/v25.0"


def facebook_params() -> dict:
    """Return default query params with Facebook access token."""
    return {"access_token": get_env("FACEBOOK_ACCESS_TOKEN")}
