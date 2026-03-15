"""Generate ad images by combining background styles, headlines, and logo.

Uses OpenAI images.edit() API with the logo as input image reference.
Styles are loaded from reference/image_styles.json.

CLI usage:
    python -m scripts.generate_image --style 5 --headline "Your headline" --logo mark --output drafts/image.png
    python -m scripts.generate_image --style 34 --headline "Your headline" --logo full --output drafts/image.png
    python -m scripts.generate_image --list-styles
    python -m scripts.generate_image --list-styles --category atmospheric
    python -m scripts.generate_image --random --headline "Your headline" --logo mark --output drafts/image.png
"""

import argparse
import base64
import io
import json
import sys
from pathlib import Path

from scripts.config import get_env

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_STYLES_FILE = _PROJECT_ROOT / "reference" / "image_styles.json"
_LOGOS = {
    "mark": _PROJECT_ROOT / "logos" / "Aurevon_logo_mark.png",
    "full": _PROJECT_ROOT / "logos" / "Aurevon_Intelligence_logo.png",
}


def load_styles() -> list[dict]:
    """Load background styles from JSON file."""
    return json.loads(_STYLES_FILE.read_text())


def get_style(style_id: int) -> dict:
    """Get a specific style by ID."""
    styles = load_styles()
    for s in styles:
        if s["id"] == style_id:
            return s
    print(f"Error: Style {style_id} not found. Use --list-styles to see available.", file=sys.stderr)
    sys.exit(1)


def list_styles(category: str | None = None) -> list[dict]:
    """List available styles, optionally filtered by category."""
    styles = load_styles()
    if category:
        styles = [s for s in styles if s["category"] == category]
    return styles


def build_prompt(style: dict, headline: str, logo_type: str) -> str:
    """Build the image generation prompt from components."""
    logo_label = "logo mark" if logo_type == "mark" else "full logo"
    return f"""Using this background style:
{style['prompt']}

Take my brand image (provided) and place it small in the bottom-right corner with generous padding from both the bottom and right edges — do not place it flush against the edge. Reproduce it EXACTLY as provided — do not redraw or reinterpret the logo.

Add this headline in large bold gold sans-serif font, left-aligned in the upper-left area with generous padding. The text must be clean and flat — no text stroke, no text border, no text outline, no text shadow, no embossing:
{headline}

Generate a landscape image at 1536x1024 for a LinkedIn ad."""


def generate_image(style_id: int, headline: str, logo_type: str, output_path: str) -> dict:
    """Generate an ad image and save to output_path. Returns metadata dict."""
    from openai import OpenAI
    from PIL import Image
    from scripts.session_guard import SessionGuard, SessionOverLimitError

    # Check session budget before paid API call
    guard = SessionGuard()
    try:
        guard.require_budget(0.20)
        guard.require_image()
    except SessionOverLimitError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    style = get_style(style_id)
    logo_path = _LOGOS.get(logo_type)
    if not logo_path or not logo_path.exists():
        print(f"Error: Logo type '{logo_type}' not found. Use 'mark' or 'full'.", file=sys.stderr)
        sys.exit(1)

    prompt = build_prompt(style, headline, logo_type)

    client = OpenAI(api_key=get_env("OPENAI_API_KEY"))

    result = client.images.edit(
        model="gpt-image-1",
        image=logo_path.open("rb"),
        prompt=prompt,
        size="1536x1024",
    )

    # Record spend and image count after successful generation
    guard.record_spend(0.17)
    guard.record_image()

    image_bytes = base64.b64decode(result.data[0].b64_json)

    # Crop to 1200x628 (1.91:1 ratio for LinkedIn/Facebook feed ads)
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size
    target_w, target_h = 1200, 628
    img_resized = img.resize((target_w, int(h * target_w / w)), Image.LANCZOS)
    rw, rh = img_resized.size
    top = (rh - target_h) // 2
    img_cropped = img_resized.crop((0, top, target_w, top + target_h))

    # Save cropped image
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img_cropped.save(str(out), "PNG")

    # Save raw image alongside
    raw_path = out.with_name(out.stem + "_raw" + out.suffix)
    raw_path.write_bytes(image_bytes)

    return {
        "output": str(out),
        "raw": str(raw_path),
        "size": f"{img_cropped.size[0]}x{img_cropped.size[1]}",
        "style_id": style_id,
        "style_name": style["name"],
        "headline": headline,
        "logo": logo_type,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate ad images from style + headline + logo")
    parser.add_argument("--style", type=int, help="Style ID from image_styles.json")
    parser.add_argument("--random", action="store_true", help="Pick a random style")
    parser.add_argument("--headline", type=str, help="Headline text to render on the image")
    parser.add_argument("--logo", choices=["mark", "full"], default="mark", help="Logo variant (default: mark)")
    parser.add_argument("--output", type=str, help="Output file path for cropped image")
    parser.add_argument("--list-styles", action="store_true", help="List available styles and exit")
    parser.add_argument("--category", type=str, help="Filter styles by category (with --list-styles)")
    args = parser.parse_args()

    if args.list_styles:
        styles = list_styles(args.category)
        categories = {}
        for s in styles:
            cat = s["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(s)
        for cat, cat_styles in sorted(categories.items()):
            print(f"\n{cat.upper()}:")
            for s in cat_styles:
                print(f"  {s['id']:3d}. {s['name']}")
        print()
        return

    if args.random:
        import random
        styles = load_styles()
        style = random.choice(styles)
        args.style = style["id"]
        print(f"Random style: {style['id']} ({style['name']})", file=sys.stderr)

    if not args.style or not args.headline or not args.output:
        parser.error("--style (or --random), --headline, and --output are required")

    result = generate_image(args.style, args.headline, args.logo, args.output)
    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
