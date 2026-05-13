"""LinkedIn helpers — validate token, push a creative."""

import httpx


def validate_token(access_token: str) -> tuple[bool, str]:
    r = httpx.get(
        "https://api.linkedin.com/v2/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if r.status_code == 200:
        return True, "ok"
    return False, f"HTTP {r.status_code}: {r.text[:200]}"
