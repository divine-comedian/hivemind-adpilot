"""Facebook campaign and ad management.

CLI usage:
    # Discovery
    python3 -m scripts.fb_campaign list-campaigns
    python3 -m scripts.fb_campaign list-adsets --campaign-id 6952504195779
    python3 -m scripts.fb_campaign list-ads --campaign-id 6952504195779
    python3 -m scripts.fb_campaign list-ads --adset-id 6955623856979

    # Campaign management
    python3 -m scripts.fb_campaign create-campaign --name "Aurevon Traffic" --objective OUTCOME_TRAFFIC --daily-budget 25
    python3 -m scripts.fb_campaign update-campaign --campaign-id 12345 --status PAUSED

    # Image upload
    python3 -m scripts.fb_campaign upload-image --image-path drafts/image.png

    # Ad set creation (auto-detects campaign budget + optimization goal)
    python3 -m scripts.fb_campaign create-adset --campaign-id 12345 --name "Canada ICP" \\
        --interests interests.json --countries CA
    python3 -m scripts.fb_campaign update-adset --adset-id 12345 --status PAUSED

    # Ad creation (upload + creative + ad in one step)
    python3 -m scripts.fb_campaign create-ad --adset-id 12345 --image-path drafts/image.png \\
        --headline "Title" --body "Body text" --cta LEARN_MORE --url https://aurevon.ca

    # Full flow (adset + upload + creative + ad)
    python3 -m scripts.fb_campaign create-full-ad --campaign-id 12345 --image-path drafts/image.png \\
        --adset-name "Canada ICP" --headline "Title" --body "Body" --cta LEARN_MORE --url https://aurevon.ca

    # Ad status management
    python3 -m scripts.fb_campaign pause-ad --ad-id 12345
    python3 -m scripts.fb_campaign activate-ad --ad-id 12345
"""

import argparse
import json
import sys
from pathlib import Path

import requests

from scripts.config import get_env, facebook_params, FACEBOOK_BASE_URL

VALID_OBJECTIVES = [
    "OUTCOME_TRAFFIC", "OUTCOME_AWARENESS", "OUTCOME_ENGAGEMENT",
    "OUTCOME_LEADS", "OUTCOME_SALES", "OUTCOME_APP_PROMOTION",
]
VALID_STATUSES = ["ACTIVE", "PAUSED", "ARCHIVED"]
VALID_CTAS = [
    "LEARN_MORE", "SIGN_UP", "DOWNLOAD", "GET_QUOTE", "SUBSCRIBE",
    "BOOK_TRAVEL", "CONTACT_US", "APPLY_NOW", "SHOP_NOW", "NO_BUTTON",
]
VALID_BID_STRATEGIES = [
    "LOWEST_COST_WITHOUT_CAP", "LOWEST_COST_WITH_BID_CAP", "COST_CAP",
]

# Default ICP targeting for Aurevon Intelligence
DEFAULT_FLEXIBLE_SPEC = [{
    "interests": [
        {"id": "6002884511422", "name": "Small business"},
        {"id": "6003371567474", "name": "Entrepreneurship"},
        {"id": "6003135342008", "name": "Business analytics"},
        {"id": "6003279598823", "name": "Marketing"},
        {"id": "6788379980003", "name": "Business leaders"},
    ],
    "behaviors": [
        {"id": "6002714898572", "name": "Small business owners"},
    ],
    "industries": [
        {"id": "6262428231783", "name": "Business Decision Makers"},
    ],
}]


def _load_interests(path: str | None) -> list[dict] | None:
    """Load flexible_spec targeting from a JSON file, or return defaults.

    Pass "default" or None to use DEFAULT_FLEXIBLE_SPEC.
    Pass "none" to skip interest targeting.
    Pass a file path to load custom targeting JSON.
    """
    if path is None or path == "default":
        return DEFAULT_FLEXIBLE_SPEC
    if path == "none":
        return None
    return json.loads(Path(path).read_text())


def _act(account_id: str) -> str:
    """Normalize account ID to act_ format."""
    account_id = account_id.removeprefix("act_")
    return f"act_{account_id}"


def _handle_error(resp: requests.Response, context: str) -> None:
    """Print error and exit on non-success response."""
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
            f"Error ({context}): HTTP {resp.status_code}: {error_msg}",
            file=sys.stderr,
        )
    sys.exit(1)


# --- Campaign management ---

def list_campaigns(account_id: str) -> list[dict]:
    """List all campaigns in the ad account."""
    url = f"{FACEBOOK_BASE_URL}/{_act(account_id)}/campaigns"
    params = {
        **facebook_params(),
        "fields": "id,name,status,objective,daily_budget,lifetime_budget,created_time",
        "limit": 50,
    }
    all_campaigns = []
    while url:
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            _handle_error(resp, "list campaigns")
        body = resp.json()
        all_campaigns.extend(body.get("data", []))
        url = body.get("paging", {}).get("next")
        params = {}

    return [
        {
            "id": c.get("id"),
            "name": c.get("name"),
            "status": c.get("status"),
            "objective": c.get("objective"),
            "daily_budget": c.get("daily_budget"),
        }
        for c in all_campaigns
    ]


def create_campaign(
    account_id: str,
    name: str,
    objective: str,
    daily_budget_cents: int,
    status: str = "PAUSED",
) -> dict:
    """Create a Facebook campaign.

    Facebook budgets are in cents (e.g. $25.00 = 2500).
    Campaigns are created PAUSED by default — activate after adding ads.
    """
    url = f"{FACEBOOK_BASE_URL}/{_act(account_id)}/campaigns"
    params = {
        **facebook_params(),
        "name": name,
        "objective": objective,
        "status": status,
        "special_ad_categories": "[]",
        "daily_budget": str(daily_budget_cents),
    }
    resp = requests.post(url, params=params)

    if resp.status_code != 200:
        _handle_error(resp, "create campaign")

    data = resp.json()
    return {"campaign_id": data["id"], "name": name, "status": status}


def update_campaign(account_id: str, campaign_id: str, updates: dict) -> dict:
    """Update a Facebook campaign (status, name, budget, etc.)."""
    url = f"{FACEBOOK_BASE_URL}/{campaign_id}"
    params = {**facebook_params(), **updates}
    resp = requests.post(url, params=params)

    if resp.status_code != 200:
        _handle_error(resp, "update campaign")

    return {"success": True, "campaign_id": campaign_id, "updates": updates}


# --- Image upload ---

def upload_image(account_id: str, image_path: str) -> dict:
    """Upload an image to Facebook ad account.

    Returns dict with image_hash (used when creating ad creatives).
    """
    url = f"{FACEBOOK_BASE_URL}/{_act(account_id)}/adimages"
    image_data = Path(image_path).read_bytes()
    files = {"filename": (Path(image_path).name, image_data, "image/png")}
    resp = requests.post(url, params=facebook_params(), files=files)

    if resp.status_code != 200:
        _handle_error(resp, "upload image")

    data = resp.json()
    images = data.get("images", {})
    # Facebook returns {images: {filename: {hash: "...", url: "..."}}}
    img_info = next(iter(images.values()))
    return {
        "image_hash": img_info["hash"],
        "image_url": img_info.get("url", ""),
    }


# --- Ad Set management ---

def _get_campaign_info(campaign_id: str) -> dict:
    """Fetch campaign details to detect budget type and optimization goal.

    Returns dict with:
        has_campaign_budget: bool — True if budget is set at campaign level
        optimization_goal: str — from existing adsets, or "LINK_CLICKS" default
    """
    # Check if campaign has a budget
    resp = requests.get(
        f"{FACEBOOK_BASE_URL}/{campaign_id}",
        params={**facebook_params(), "fields": "daily_budget,lifetime_budget"},
    )
    info = {"has_campaign_budget": False, "optimization_goal": "LINK_CLICKS"}

    if resp.status_code == 200:
        data = resp.json()
        if data.get("daily_budget") or data.get("lifetime_budget"):
            info["has_campaign_budget"] = True

    # Check existing adsets for optimization_goal (must match within campaign)
    resp2 = requests.get(
        f"{FACEBOOK_BASE_URL}/{campaign_id}/adsets",
        params={**facebook_params(), "fields": "optimization_goal", "limit": 1},
    )
    if resp2.status_code == 200:
        adsets = resp2.json().get("data", [])
        if adsets:
            info["optimization_goal"] = adsets[0].get("optimization_goal", "LINK_CLICKS")

    return info


def create_adset(
    account_id: str,
    campaign_id: str,
    name: str,
    daily_budget_cents: int = 0,
    destination_url: str = "",
    countries: list[str] | None = None,
    age_min: int = 25,
    age_max: int = 65,
    bid_strategy: str = "LOWEST_COST_WITHOUT_CAP",
    status: str = "PAUSED",
    flexible_spec: list[dict] | None = None,
    advantage_audience: bool = True,
) -> dict:
    """Create an ad set with targeting.

    Auto-detects campaign budget and optimization goal from existing campaign
    to avoid Facebook API conflicts. When advantage_audience is True (default),
    age is clamped to 25-65 per Facebook requirements.

    flexible_spec: list of dicts with interests/behaviors/industries for
    detailed targeting. Each dict can have keys like:
        {"interests": [{"id": "600...", "name": "..."}],
         "behaviors": [{"id": "600...", "name": "..."}],
         "industries": [{"id": "608...", "name": "..."}]}
    """
    countries = countries or ["CA"]

    # Auto-detect campaign budget type and optimization goal
    campaign_info = _get_campaign_info(campaign_id)

    # Advantage+ audience requires age 25-65
    if advantage_audience:
        age_min = max(age_min, 18)
        age_min = min(age_min, 25)
        age_max = max(age_max, 65)

    url = f"{FACEBOOK_BASE_URL}/{_act(account_id)}/adsets"
    targeting = {
        "geo_locations": {"countries": countries},
        "age_min": age_min,
        "age_max": age_max,
    }
    if flexible_spec:
        targeting["flexible_spec"] = flexible_spec
    if advantage_audience:
        targeting["targeting_automation"] = {"advantage_audience": 1}

    params = {
        **facebook_params(),
        "name": name,
        "campaign_id": campaign_id,
        "billing_event": "IMPRESSIONS",
        "optimization_goal": campaign_info["optimization_goal"],
        "bid_strategy": bid_strategy,
        "targeting": json.dumps(targeting),
        "promoted_object": json.dumps({"page_id": get_env("FACEBOOK_PAGE_ID")}),
        "destination_type": "WEBSITE",
        "status": status,
    }

    # Only set adset budget if campaign doesn't have one
    if not campaign_info["has_campaign_budget"] and daily_budget_cents > 0:
        params["daily_budget"] = str(daily_budget_cents)

    resp = requests.post(url, params=params)

    if resp.status_code != 200:
        _handle_error(resp, "create adset")

    data = resp.json()
    return {"adset_id": data["id"], "name": name, "campaign_id": campaign_id, "status": status}


def list_adsets(account_id: str, campaign_id: str) -> list[dict]:
    """List ad sets in a campaign."""
    url = f"{FACEBOOK_BASE_URL}/{campaign_id}/adsets"
    params = {
        **facebook_params(),
        "fields": "id,name,status,effective_status,daily_budget,targeting,optimization_goal",
        "limit": 50,
    }
    all_adsets = []
    while url:
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            _handle_error(resp, "list adsets")
        body = resp.json()
        all_adsets.extend(body.get("data", []))
        url = body.get("paging", {}).get("next")
        params = {}

    return [
        {
            "id": a.get("id"),
            "name": a.get("name"),
            "status": a.get("status"),
            "effective_status": a.get("effective_status"),
            "daily_budget": a.get("daily_budget"),
            "optimization_goal": a.get("optimization_goal"),
        }
        for a in all_adsets
    ]


def update_adset_status(adset_id: str, status: str) -> dict:
    """Update an ad set's status (ACTIVE, PAUSED, ARCHIVED)."""
    url = f"{FACEBOOK_BASE_URL}/{adset_id}"
    params = {**facebook_params(), "status": status}
    resp = requests.post(url, params=params)

    if resp.status_code != 200:
        _handle_error(resp, f"update adset {adset_id}")

    return {"adset_id": adset_id, "status": status}


# --- Ad Creative + Ad creation ---

def create_ad_creative(
    account_id: str,
    image_hash: str,
    headline: str,
    body: str,
    cta: str,
    destination_url: str,
    link_description: str = "",
) -> dict:
    """Create an ad creative with image, copy, and CTA."""
    page_id = get_env("FACEBOOK_PAGE_ID")
    url = f"{FACEBOOK_BASE_URL}/{_act(account_id)}/adcreatives"

    link_data = {
        "image_hash": image_hash,
        "link": destination_url,
        "message": body,
        "name": headline,
        "call_to_action": {"type": cta},
    }
    if link_description:
        link_data["description"] = link_description

    object_story_spec = {
        "page_id": page_id,
        "link_data": link_data,
    }

    params = {
        **facebook_params(),
        "object_story_spec": json.dumps(object_story_spec),
    }
    resp = requests.post(url, params=params)

    if resp.status_code != 200:
        _handle_error(resp, "create ad creative")

    data = resp.json()
    return {"creative_id": data["id"]}


def create_ad(
    account_id: str,
    adset_id: str,
    creative_id: str,
    name: str = "",
    status: str = "PAUSED",
) -> dict:
    """Create an ad linking an ad set to a creative."""
    url = f"{FACEBOOK_BASE_URL}/{_act(account_id)}/ads"
    params = {
        **facebook_params(),
        "adset_id": adset_id,
        "creative": json.dumps({"creative_id": creative_id}),
        "status": status,
    }
    if name:
        params["name"] = name
    resp = requests.post(url, params=params)

    if resp.status_code != 200:
        _handle_error(resp, "create ad")

    data = resp.json()
    return {"ad_id": data["id"], "adset_id": adset_id, "creative_id": creative_id, "status": status}


def create_full_ad(
    account_id: str,
    campaign_id: str,
    image_path: str,
    adset_name: str,
    daily_budget_cents: int,
    countries: list[str],
    age_min: int,
    age_max: int,
    headline: str,
    body: str,
    cta: str,
    destination_url: str,
    link_description: str = "",
    status: str = "PAUSED",
    flexible_spec: list[dict] | None = None,
) -> dict:
    """Create a full Facebook ad in one call (upload → adset → creative → ad).

    This is the full 4-step flow:
    1. Upload image to ad account
    2. Create ad set with targeting
    3. Create ad creative with image + copy
    4. Create ad linking adset to creative
    """
    # Step 1: Upload image
    print("Uploading image...", file=sys.stderr)
    img_result = upload_image(account_id, image_path)
    image_hash = img_result["image_hash"]
    print(f"Image uploaded: {image_hash}", file=sys.stderr)

    # Step 2: Create ad set
    print("Creating ad set...", file=sys.stderr)
    adset_result = create_adset(
        account_id, campaign_id, adset_name, daily_budget_cents,
        destination_url, countries, age_min, age_max, status=status,
        flexible_spec=flexible_spec,
    )
    adset_id = adset_result["adset_id"]
    print(f"Ad set created: {adset_id}", file=sys.stderr)

    # Step 3: Create ad creative
    print("Creating ad creative...", file=sys.stderr)
    creative_result = create_ad_creative(
        account_id, image_hash, headline, body, cta, destination_url, link_description,
    )
    creative_id = creative_result["creative_id"]
    print(f"Creative created: {creative_id}", file=sys.stderr)

    # Step 4: Create ad
    print("Creating ad...", file=sys.stderr)
    ad_name = f"{headline[:40]} — {adset_name}"
    ad_result = create_ad(account_id, adset_id, creative_id, name=ad_name, status=status)
    ad_id = ad_result["ad_id"]
    print(f"Ad created: {ad_id}", file=sys.stderr)

    return {
        "ad_id": ad_id,
        "adset_id": adset_id,
        "creative_id": creative_id,
        "image_hash": image_hash,
        "campaign_id": campaign_id,
        "status": status,
    }


# --- List / update ads ---

def list_ads(account_id: str, parent_id: str) -> list[dict]:
    """List ads under a parent object (adset ID or campaign ID)."""
    url = f"{FACEBOOK_BASE_URL}/{parent_id}/ads"
    params = {
        **facebook_params(),
        "fields": "id,name,status,effective_status,creative{id,name,image_hash,object_story_spec}",
    }
    all_ads = []
    while url:
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            _handle_error(resp, "list ads")
        body = resp.json()
        all_ads.extend(body.get("data", []))
        url = body.get("paging", {}).get("next")
        params = {}

    return [
        {
            "id": a.get("id"),
            "name": a.get("name"),
            "status": a.get("status"),
            "effective_status": a.get("effective_status"),
            "creative_id": a.get("creative", {}).get("id"),
        }
        for a in all_ads
    ]


def update_ad_status(ad_id: str, status: str) -> dict:
    """Update an ad's status (ACTIVE, PAUSED, ARCHIVED)."""
    url = f"{FACEBOOK_BASE_URL}/{ad_id}"
    params = {**facebook_params(), "status": status}
    resp = requests.post(url, params=params)

    if resp.status_code != 200:
        _handle_error(resp, f"update ad {ad_id}")

    return {"ad_id": ad_id, "status": status}


def main():
    parser = argparse.ArgumentParser(description="Facebook campaign and ad management")
    sub = parser.add_subparsers(dest="command", required=True)

    # --- Discovery ---
    sub.add_parser("list-campaigns", help="List all campaigns in the ad account")

    p_las = sub.add_parser("list-adsets", help="List ad sets in a campaign")
    p_las.add_argument("--campaign-id", required=True)

    p_list = sub.add_parser("list-ads", help="List ads (by campaign or adset)")
    p_list_group = p_list.add_mutually_exclusive_group(required=True)
    p_list_group.add_argument("--campaign-id", help="List all ads in campaign")
    p_list_group.add_argument("--adset-id", help="List ads in a specific ad set")

    # --- Campaign management ---
    p_cc = sub.add_parser("create-campaign")
    p_cc.add_argument("--name", required=True)
    p_cc.add_argument("--objective", choices=VALID_OBJECTIVES, default="OUTCOME_TRAFFIC")
    p_cc.add_argument("--daily-budget", type=float, required=True, help="Daily budget in dollars (e.g. 25.00)")
    p_cc.add_argument("--status", choices=VALID_STATUSES, default="PAUSED")

    p_uc = sub.add_parser("update-campaign")
    p_uc.add_argument("--campaign-id", required=True)
    p_uc.add_argument("--status", choices=VALID_STATUSES)
    p_uc.add_argument("--name", type=str)
    p_uc.add_argument("--daily-budget", type=float)

    # --- Image upload ---
    p_img = sub.add_parser("upload-image")
    p_img.add_argument("--image-path", required=True, help="Path to image file")

    # --- Ad set management ---
    p_as = sub.add_parser("create-adset", help="Create ad set (auto-detects campaign budget/optimization)")
    p_as.add_argument("--campaign-id", required=True)
    p_as.add_argument("--name", required=True)
    p_as.add_argument("--daily-budget", type=float, default=0, help="Daily budget in dollars (skipped if campaign has budget)")
    p_as.add_argument("--countries", nargs="+", default=["CA"], help="Country codes (default: CA)")
    p_as.add_argument("--age-min", type=int, default=25)
    p_as.add_argument("--age-max", type=int, default=65)
    p_as.add_argument("--interests", type=str, default="default",
                       help="Targeting JSON file, 'default' for Aurevon ICP, or 'none' to skip")
    p_as.add_argument("--bid-strategy", choices=VALID_BID_STRATEGIES, default="LOWEST_COST_WITHOUT_CAP")
    p_as.add_argument("--status", choices=VALID_STATUSES, default="PAUSED")
    p_as.add_argument("--no-advantage-audience", action="store_true", help="Disable Advantage+ audience")

    p_uas = sub.add_parser("update-adset", help="Update ad set status")
    p_uas.add_argument("--adset-id", required=True)
    p_uas.add_argument("--status", choices=VALID_STATUSES, required=True)

    # --- Ad creation ---
    p_ad = sub.add_parser("create-ad", help="Upload image + create creative + ad for existing adset")
    p_ad.add_argument("--adset-id", required=True)
    p_ad.add_argument("--image-path", required=True, help="Path to ad image file")
    p_ad.add_argument("--headline", required=True)
    p_ad.add_argument("--body", required=True, help="Primary text / body copy")
    p_ad.add_argument("--cta", choices=VALID_CTAS, default="LEARN_MORE")
    p_ad.add_argument("--url", required=True, help="Destination URL")
    p_ad.add_argument("--link-description", default="", help="Link description text")
    p_ad.add_argument("--status", choices=VALID_STATUSES, default="PAUSED")

    p_full = sub.add_parser("create-full-ad", help="Full flow: adset + upload + creative + ad")
    p_full.add_argument("--campaign-id", required=True)
    p_full.add_argument("--image-path", required=True)
    p_full.add_argument("--adset-name", required=True, help="Ad set name")
    p_full.add_argument("--daily-budget", type=float, default=0, help="Daily budget in dollars (skipped if campaign has budget)")
    p_full.add_argument("--countries", nargs="+", default=["CA"])
    p_full.add_argument("--age-min", type=int, default=25)
    p_full.add_argument("--age-max", type=int, default=65)
    p_full.add_argument("--interests", type=str, default="default",
                         help="Targeting JSON file, 'default' for Aurevon ICP, or 'none' to skip")
    p_full.add_argument("--headline", required=True)
    p_full.add_argument("--body", required=True)
    p_full.add_argument("--cta", choices=VALID_CTAS, default="LEARN_MORE")
    p_full.add_argument("--url", required=True, help="Destination URL")
    p_full.add_argument("--link-description", default="")
    p_full.add_argument("--status", choices=VALID_STATUSES, default="PAUSED")

    # --- Ad status ---
    p_pause = sub.add_parser("pause-ad")
    p_pause.add_argument("--ad-id", required=True)

    p_activate = sub.add_parser("activate-ad")
    p_activate.add_argument("--ad-id", required=True)

    args = parser.parse_args()
    account_id = get_env("FACEBOOK_AD_ACCOUNT_ID")

    if args.command == "list-campaigns":
        result = list_campaigns(account_id)

    elif args.command == "list-adsets":
        result = list_adsets(account_id, args.campaign_id)

    elif args.command == "list-ads":
        parent_id = args.campaign_id or args.adset_id
        result = list_ads(account_id, parent_id)

    elif args.command == "create-campaign":
        daily_budget_cents = round(args.daily_budget * 100)
        result = create_campaign(account_id, args.name, args.objective, daily_budget_cents, args.status)

    elif args.command == "update-campaign":
        updates = {}
        if args.status:
            updates["status"] = args.status
        if args.name:
            updates["name"] = args.name
        if args.daily_budget:
            updates["daily_budget"] = str(round(args.daily_budget * 100))
        result = update_campaign(account_id, args.campaign_id, updates)

    elif args.command == "upload-image":
        result = upload_image(account_id, args.image_path)

    elif args.command == "create-adset":
        daily_budget_cents = round(args.daily_budget * 100)
        flexible_spec = _load_interests(args.interests)
        result = create_adset(
            account_id, args.campaign_id, args.name, daily_budget_cents,
            countries=args.countries, age_min=args.age_min, age_max=args.age_max,
            bid_strategy=args.bid_strategy, status=args.status,
            flexible_spec=flexible_spec,
            advantage_audience=not args.no_advantage_audience,
        )

    elif args.command == "update-adset":
        result = update_adset_status(args.adset_id, args.status)

    elif args.command == "create-ad":
        print("Uploading image...", file=sys.stderr)
        img_result = upload_image(account_id, args.image_path)
        image_hash = img_result["image_hash"]
        print(f"Image uploaded: {image_hash}", file=sys.stderr)

        print("Creating ad creative...", file=sys.stderr)
        creative_result = create_ad_creative(
            account_id, image_hash, args.headline, args.body,
            args.cta, args.url, args.link_description,
        )
        creative_id = creative_result["creative_id"]
        print(f"Creative created: {creative_id}", file=sys.stderr)

        print("Creating ad...", file=sys.stderr)
        ad_name = f"{args.headline[:40]}"
        result = create_ad(account_id, args.adset_id, creative_id, name=ad_name, status=args.status)
        result["creative_id"] = creative_id
        result["image_hash"] = image_hash

    elif args.command == "create-full-ad":
        daily_budget_cents = round(args.daily_budget * 100)
        flexible_spec = _load_interests(args.interests)
        result = create_full_ad(
            account_id, args.campaign_id, args.image_path,
            args.adset_name, daily_budget_cents, args.countries,
            args.age_min, args.age_max, args.headline, args.body,
            args.cta, args.url, args.link_description, args.status,
            flexible_spec=flexible_spec,
        )

    elif args.command == "pause-ad":
        result = update_ad_status(args.ad_id, "PAUSED")

    elif args.command == "activate-ad":
        result = update_ad_status(args.ad_id, "ACTIVE")

    else:
        print(f"Error: Unknown command '{args.command}'", file=sys.stderr)
        sys.exit(1)

    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
