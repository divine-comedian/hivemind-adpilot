"""LinkedIn campaign and creative management.

CLI usage:
    python -m scripts.li_campaign create-campaign --name "Test" --objective WEBSITE_VISITS --daily-budget 50
    python -m scripts.li_campaign update-campaign --campaign-id 123 --status PAUSED
    python -m scripts.li_campaign upload-image --image-path path/to/image.png
    python -m scripts.li_campaign create-ad --campaign-id 555838216 --image-path drafts/image.png \\
        --headline "Title" --intro-text "Body" --cta LEARN_MORE --url https://aurevon.ca
    python -m scripts.li_campaign list-creatives --campaign-id 555838216
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

# Organization URN for Aurevon Intelligence (image uploads must be owned by org)
_ORG_URN = "urn:li:organization:112708829"

# Creatives endpoint requires a different API version than other endpoints
_CREATIVES_VERSION = "202509"


def _headers(version: str | None = None) -> dict:
    """Return LinkedIn headers, optionally overriding the API version."""
    h = linkedin_headers()
    if version:
        h["LinkedIn-Version"] = version
    return h


def _handle_error(resp: requests.Response, context: str) -> None:
    """Print error and exit on non-success response."""
    if resp.status_code in (401, 403):
        print(
            f"Error: LinkedIn token invalid or forbidden (HTTP {resp.status_code}). "
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


# --- Campaign management ---

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
    resp = requests.post(url, headers={**_headers(), "Content-Type": "application/json"}, json=body)

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
        **_headers(),
        "Content-Type": "application/json",
        "X-RestLi-Method": "PARTIAL_UPDATE",
    }
    body = {"patch": {"$set": updates}}
    resp = requests.post(url, headers=headers, json=body)

    if resp.status_code not in (200, 204):
        _handle_error(resp, "update campaign")

    return {"success": True, "campaign_id": campaign_id, "updates": updates}


# --- Image upload ---

def upload_image(account_id: str, image_path: str, org_urn: str = _ORG_URN) -> dict:
    """Upload image to LinkedIn CDN. Owner is the organization (required for ad posts).

    Returns dict with image_urn.
    """
    # Step 1: Initialize upload with org as owner
    url = f"{LINKEDIN_BASE_URL}/images?action=initializeUpload"
    body = {
        "initializeUploadRequest": {
            "owner": org_urn,
        }
    }
    resp = requests.post(url, headers={**_headers(), "Content-Type": "application/json"}, json=body)

    if resp.status_code != 200:
        _handle_error(resp, "initialize image upload")

    data = resp.json()["value"]
    upload_url = data["uploadUrl"]
    image_urn = data["image"]

    # Step 2: Upload binary to CDN (uses manual auth, no Rest.li version headers)
    image_data = Path(image_path).read_bytes()
    headers = {
        "Authorization": f"Bearer {get_env('LINKEDIN_ACCESS_TOKEN')}",
        "Content-Type": "application/octet-stream",
    }
    resp = requests.put(upload_url, headers=headers, data=image_data)

    if resp.status_code not in (200, 201):
        _handle_error(resp, "image upload")

    return {"image_urn": image_urn}


# --- Ad creation (full 3-step flow) ---

def create_ad(
    account_id: str,
    campaign_id: str,
    image_path: str,
    headline: str,
    intro_text: str,
    cta: str,
    destination_url: str,
    status: str = "ACTIVE",
    org_urn: str = _ORG_URN,
) -> dict:
    """Create a LinkedIn image ad in one call (upload → post → creative).

    This is the full 3-step flow:
    1. Upload image with org as owner
    2. Create a DSC (Direct Sponsored Content) post via /rest/posts
    3. Create a creative referencing the post via BATCH_CREATE
    """
    # Step 1: Upload image
    print("Uploading image...", file=sys.stderr)
    img_result = upload_image(account_id, image_path, org_urn=org_urn)
    image_urn = img_result["image_urn"]
    print(f"Image uploaded: {image_urn}", file=sys.stderr)

    # Step 2: Create DSC post
    print("Creating post...", file=sys.stderr)
    post_url = f"{LINKEDIN_BASE_URL}/posts"
    post_body = {
        "adContext": {
            "dscAdAccount": f"urn:li:sponsoredAccount:{account_id}",
            "dscStatus": "ACTIVE",
        },
        "author": org_urn,
        "commentary": intro_text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "NONE",
            "thirdPartyDistributionChannels": [],
        },
        "content": {
            "media": {
                "title": headline,
                "id": image_urn,
            }
        },
        "contentCallToActionLabel": cta,
        "contentLandingPage": destination_url,
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": True,
    }
    resp = requests.post(
        post_url,
        headers={**_headers(), "Content-Type": "application/json"},
        json=post_body,
    )

    if resp.status_code != 201:
        _handle_error(resp, "create post")

    share_urn = resp.headers.get("x-restli-id", "")
    print(f"Post created: {share_urn}", file=sys.stderr)

    # Step 3: Create creative via BATCH_CREATE (requires version 202509)
    print("Creating creative...", file=sys.stderr)
    creative_url = f"{LINKEDIN_BASE_URL}/adAccounts/{account_id}/creatives"
    creative_body = {
        "elements": [
            {
                "content": {"reference": share_urn},
                "campaign": f"urn:li:sponsoredCampaign:{campaign_id}",
                "intendedStatus": status,
            }
        ]
    }
    resp = requests.post(
        creative_url,
        headers={
            **_headers(version=_CREATIVES_VERSION),
            "Content-Type": "application/json",
            "X-RestLi-Method": "BATCH_CREATE",
        },
        json=creative_body,
    )

    if resp.status_code not in (200, 201):
        # Report what was created so user can clean up if needed
        print(f"Warning: Post {share_urn} was created but creative failed.", file=sys.stderr)
        _handle_error(resp, "create creative")

    creative_id = resp.json()["elements"][0].get("id", "")
    print(f"Creative created: {creative_id}", file=sys.stderr)

    return {
        "creative_id": creative_id,
        "share_urn": share_urn,
        "image_urn": image_urn,
        "campaign_id": campaign_id,
        "status": status,
    }


# --- List creatives ---

def list_creatives(account_id: str, campaign_id: str) -> list[dict]:
    """List creatives for a campaign."""
    from urllib.parse import quote
    campaign_urn = quote(f"urn:li:sponsoredCampaign:{campaign_id}", safe="")
    url = (
        f"{LINKEDIN_BASE_URL}/adAccounts/{account_id}/creatives"
        f"?q=criteria&campaigns=List({campaign_urn})"
    )
    resp = requests.get(url, headers=_headers(version=_CREATIVES_VERSION))

    if resp.status_code != 200:
        _handle_error(resp, "list creatives")

    elements = resp.json().get("elements", [])
    return [
        {
            "id": e.get("id"),
            "name": e.get("name"),
            "status": e.get("intendedStatus"),
            "serving": e.get("isServing"),
            "review": e.get("review", {}).get("status"),
            "content_ref": e.get("content", {}).get("reference"),
        }
        for e in elements
    ]


def update_creative_status(account_id: str, creative_id: str, status: str) -> dict:
    """Update a creative's intendedStatus (ACTIVE, PAUSED, ARCHIVED)."""
    from urllib.parse import quote
    creative_urn = quote(creative_id, safe="")
    url = f"{LINKEDIN_BASE_URL}/adAccounts/{account_id}/creatives/{creative_urn}"
    resp = requests.post(
        url,
        headers={
            **_headers(version=_CREATIVES_VERSION),
            "Content-Type": "application/json",
            "X-RestLi-Method": "PARTIAL_UPDATE",
        },
        json={"patch": {"$set": {"intendedStatus": status}}},
    )

    if resp.status_code not in (200, 204):
        _handle_error(resp, f"update creative {creative_id}")

    return {"creative_id": creative_id, "status": status}


def rotate_creatives(
    account_id: str,
    campaign_id: str,
    keep_ids: list[str] | None = None,
    pause_all: bool = False,
) -> dict:
    """Pause old creatives in a campaign. Optionally keep specific ones active.

    If pause_all is True, pauses everything (use before adding fresh ads).
    If keep_ids is provided, only those stay ACTIVE, rest get PAUSED.
    """
    creatives = list_creatives(account_id, campaign_id)
    paused = []
    kept = []

    for c in creatives:
        cid = c["id"]
        if c["status"] != "ACTIVE":
            continue
        if pause_all or (keep_ids and cid not in keep_ids):
            update_creative_status(account_id, cid, "PAUSED")
            paused.append(cid)
        else:
            kept.append(cid)

    return {"paused": paused, "kept_active": kept}


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

    # create-ad (full 3-step flow)
    p_ad = sub.add_parser("create-ad", help="Create a full image ad (upload + post + creative)")
    p_ad.add_argument("--campaign-id", required=True)
    p_ad.add_argument("--image-path", required=True, help="Path to ad image file")
    p_ad.add_argument("--headline", required=True)
    p_ad.add_argument("--intro-text", required=True)
    p_ad.add_argument("--cta", choices=VALID_CTAS, default="LEARN_MORE")
    p_ad.add_argument("--url", required=True, help="Destination URL")
    p_ad.add_argument("--status", choices=["ACTIVE", "DRAFT"], default="ACTIVE")

    # list-creatives
    p_list = sub.add_parser("list-creatives")
    p_list.add_argument("--campaign-id", required=True)

    # pause-creative
    p_pause = sub.add_parser("pause-creative", help="Pause a specific creative")
    p_pause.add_argument("--creative-id", required=True, help="Full creative URN")

    # activate-creative
    p_activate = sub.add_parser("activate-creative", help="Activate a paused creative")
    p_activate.add_argument("--creative-id", required=True, help="Full creative URN")

    # rotate-creatives
    p_rotate = sub.add_parser("rotate-creatives", help="Pause old creatives in a campaign")
    p_rotate.add_argument("--campaign-id", required=True)
    p_rotate.add_argument("--keep", nargs="*", help="Creative URNs to keep active (pause the rest)")
    p_rotate.add_argument("--pause-all", action="store_true", help="Pause all active creatives")

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
    elif args.command == "create-ad":
        result = create_ad(
            account_id, args.campaign_id, args.image_path,
            args.headline, args.intro_text, args.cta, args.url, args.status,
        )
    elif args.command == "list-creatives":
        result = list_creatives(account_id, args.campaign_id)
    elif args.command == "pause-creative":
        result = update_creative_status(account_id, args.creative_id, "PAUSED")
    elif args.command == "activate-creative":
        result = update_creative_status(account_id, args.creative_id, "ACTIVE")
    elif args.command == "rotate-creatives":
        result = rotate_creatives(account_id, args.campaign_id, args.keep, args.pause_all)
    else:
        print(f"Error: Unknown command '{args.command}'", file=sys.stderr)
        sys.exit(1)

    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
