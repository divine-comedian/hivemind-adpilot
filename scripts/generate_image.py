"""Generate ad images by combining background styles, headlines, and logo.

Uses OpenAI images.edit() API with the logo as input image reference.
Styles are loaded from reference/image_styles.json.

CLI usage:
    python3 -m scripts.generate_image --style 5 --headline "Your headline" --logo mark --output drafts/image.png
    python3 -m scripts.generate_image --format story --style 5 --headline "Your headline" --output drafts/image.png
    python3 -m scripts.generate_image --list-styles
    python3 -m scripts.generate_image --list-formats
    python3 -m scripts.generate_image --random --headline "Your headline" --logo mark --output drafts/image.png
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
_FONTS_DIR = _PROJECT_ROOT / "fonts"
# Brand palette — text color auto-selected for max contrast against background
_BRAND_PALETTE = [
    ("#cf995f", "Light Bronze"),
    ("#2e0f15", "Rich Mahogany"),
    ("#3b6064", "Dark Slate Grey"),
    ("#95b2b8", "Cool Steel"),
    ("#f9dc5c", "Royal Gold"),
]

_FONT_MAP = {
    "Geist-Bold": _FONTS_DIR / "Geist" / "static" / "Geist-Bold.ttf",
    "Geist-ExtraBold": _FONTS_DIR / "Geist" / "static" / "Geist-ExtraBold.ttf",
    "Geist-Black": _FONTS_DIR / "Geist" / "static" / "Geist-Black.ttf",
    "Geist-SemiBold": _FONTS_DIR / "Geist" / "static" / "Geist-SemiBold.ttf",
    "Geist-Medium": _FONTS_DIR / "Geist" / "static" / "Geist-Medium.ttf",
    "Raleway-Bold": _FONTS_DIR / "Raleway" / "static" / "Raleway-Bold.ttf",
    "Raleway-ExtraBold": _FONTS_DIR / "Raleway" / "static" / "Raleway-ExtraBold.ttf",
    "Raleway-Black": _FONTS_DIR / "Raleway" / "static" / "Raleway-Black.ttf",
    "EBGaramond-Bold": _FONTS_DIR / "EB_Garamond" / "static" / "EBGaramond-Bold.ttf",
    "EBGaramond-ExtraBold": _FONTS_DIR / "EB_Garamond" / "static" / "EBGaramond-ExtraBold.ttf",
}

# Ad format presets: maps format name to (api_size, crop_w, crop_h, description)
# api_size = closest supported OpenAI size; crop = final ad dimensions
AD_FORMATS = {
    "feed": {
        "api_size": "auto",
        "crop": (1200, 628),
        "ratio": "1.91:1",
        "crop_gravity": 0.5,
        "description": "Facebook/LinkedIn feed ad",
    },
    "square": {
        "api_size": "1024x1024",
        "crop": (1080, 1080),
        "ratio": "1:1",
        "crop_gravity": 0.5,  # center
        "description": "Facebook/Instagram square ad",
    },
    "story": {
        "api_size": "1024x1536",
        "crop": (1080, 1920),
        "ratio": "9:16",
        "crop_gravity": 0.5,  # center
        "description": "Facebook/Instagram story or reel",
    },
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


def get_format(name: str) -> dict:
    """Get an ad format preset by name."""
    fmt = AD_FORMATS.get(name)
    if not fmt:
        print(f"Error: Format '{name}' not found. Use --list-formats to see available.", file=sys.stderr)
        sys.exit(1)
    return fmt


def _build_structured_prompt(style: dict, headline: str, ad_format: str) -> str:
    """Build a JSON prompt for structured styles (new format).

    Text and logo are composited by Pillow post-generation.
    The AI only generates the background artwork with clear zones.
    """
    fmt = AD_FORMATS[ad_format]
    crop_w, crop_h = fmt["crop"]
    api_size = fmt["api_size"]
    if api_size == "auto":
        api_w, api_h = str(crop_w), str(crop_h)
    else:
        api_w, api_h = api_size.split("x")

    # Start from style's composition, adjust clear zones per format
    composition = dict(style["composition"])
    if ad_format == "story":
        composition["headline_safe_zone"] = {"x": 10, "y": 5, "w": 80, "h": 30}
        composition["logo_safe_zone"] = {"x": 35, "y": 82, "w": 30, "h": 12}
    elif ad_format == "square":
        composition["headline_safe_zone"] = {"x": 6, "y": 6, "w": 50, "h": 45}
        composition["logo_safe_zone"] = {"x": 74, "y": 76, "w": 20, "h": 18}

    spec = {
        "image": {
            "size": f"{api_w}x{api_h}",
            "orientation": {"feed": "landscape", "square": "square", "story": "portrait"}[ad_format],
        },
        "composition": composition,
        "color": style["color"],
        "materials": style["materials"],
        "lighting": style["lighting"],
        "clear_zones": {
            "headline_zone": composition["headline_safe_zone"],
            "logo_zone": composition["logo_safe_zone"],
            "note": "These zones MUST be kept clear — dark, uncluttered background only. Text and logo will be added in post-production.",
        },
        "restrictions": style["restrictions"] + [
            "no text of any kind",
            "no logos or brand marks",
        ],
    }

    preamble = (
        "Generate a background image for an ad. Do NOT include any text or logos. "
        "The clear_zones define areas that must be kept dark and uncluttered — "
        "text and branding will be overlaid in post-production."
    )
    return f"{preamble}\n\n{json.dumps(spec, indent=2)}"


def _build_legacy_prompt(style: dict, headline: str, logo_type: str, ad_format: str) -> str:
    """Build a freeform prompt for legacy styles (old format with 'prompt' field)."""
    fmt = AD_FORMATS[ad_format]
    # images.edit() doesn't accept "auto" — fall back to landscape 1536x1024
    # (matches the size coercion in generate_image())
    api_size = fmt["api_size"]
    if api_size == "auto":
        api_w, api_h = "1536", "1024"
    else:
        api_w, api_h = api_size.split("x")
    crop_w, crop_h = fmt["crop"]

    if ad_format == "story":
        layout = (
            "Take my brand image (provided) and place it small in the bottom-center "
            "with generous padding from the bottom edge. Reproduce it EXACTLY as provided "
            "— do not redraw or reinterpret the logo.\n\n"
            "Add this headline in large bold gold sans-serif font, centered horizontally "
            "in the upper third with generous padding. The text must be clean and flat "
            "— no text stroke, no text border, no text outline, no text shadow, no embossing."
        )
        orientation = "portrait"
    elif ad_format == "square":
        layout = (
            "Take my brand image (provided) and place it small in the bottom-right corner "
            "with generous padding from both edges. Reproduce it EXACTLY as provided "
            "— do not redraw or reinterpret the logo.\n\n"
            "Add this headline in large bold gold sans-serif font, left-aligned in the "
            "upper-left area with generous padding. The text must be clean and flat "
            "— no text stroke, no text border, no text outline, no text shadow, no embossing."
        )
        orientation = "square"
    else:
        layout = (
            "Take my brand image (provided) and place it small in the bottom-right corner "
            "with generous padding from both the bottom and right edges — do not place it "
            "flush against the edge. Reproduce it EXACTLY as provided "
            "— do not redraw or reinterpret the logo.\n\n"
            "Add this headline in large bold gold sans-serif font, left-aligned in the "
            "upper-left area with generous padding. The text must be clean and flat "
            "— no text stroke, no text border, no text outline, no text shadow, no embossing."
        )
        orientation = "landscape"

    crop_note = ""
    if (int(api_w), int(api_h)) != (crop_w, crop_h):
        crop_note = (
            f"\n\nIMPORTANT: The final image will be cropped from {api_w}x{api_h} to "
            f"{crop_w}x{crop_h}. Keep all text, logo, and key visual elements within "
            f"the center safe zone — edges will be trimmed."
        )

    return f"""Using this background style:
{style['prompt']}

{layout}
{headline}

Generate a {orientation} image at {api_w}x{api_h} for a {fmt['description']}.{crop_note}"""


def build_prompt(style: dict, headline: str, logo_type: str, ad_format: str = "feed") -> str:
    """Build the image generation prompt from components.

    Detects style format: structured (has 'composition' key) vs legacy (has 'prompt' key).
    """
    if "composition" in style:
        return _build_structured_prompt(style, headline, ad_format)
    return _build_legacy_prompt(style, headline, logo_type, ad_format)


def generate_image(
    style_id: int,
    headline: str,
    logo_type: str,
    output_path: str,
    ad_format: str = "feed",
) -> dict:
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

    fmt = get_format(ad_format)
    style = get_style(style_id)
    logo_path = _LOGOS.get(logo_type)
    if not logo_path or not logo_path.exists():
        print(f"Error: Logo type '{logo_type}' not found. Use 'mark' or 'full'.", file=sys.stderr)
        sys.exit(1)

    prompt = build_prompt(style, headline, logo_type, ad_format)
    is_structured = "composition" in style

    client = OpenAI(api_key=get_env("OPENAI_API_KEY"))

    if is_structured:
        # Structured styles: images.generate() (no input image, logo composited after)
        result = client.images.generate(
            model="gpt-image-1.5",
            prompt=prompt,
            size=fmt["api_size"],
        )
    else:
        # Legacy styles: images.edit() with logo as input image
        # images.edit() doesn't support 'auto' — use 1536x1024 for landscape
        edit_size = fmt["api_size"]
        if edit_size == "auto":
            edit_size = "1536x1024"
        result = client.images.edit(
            model="gpt-image-1.5",
            image=logo_path.open("rb"),
            prompt=prompt,
            size=edit_size,
        )

    # Record spend and image count after successful generation
    guard.record_spend(0.17)
    guard.record_image()

    image_bytes = base64.b64decode(result.data[0].b64_json)

    # Crop to target ad dimensions
    img = Image.open(io.BytesIO(image_bytes))
    crop_w, crop_h = fmt["crop"]
    api_w, api_h = img.size

    gravity = fmt.get("crop_gravity", 0.5)

    if (api_w, api_h) == (crop_w, crop_h):
        img_final = img.resize((crop_w, crop_h), Image.LANCZOS)
    else:
        scale = max(crop_w / api_w, crop_h / api_h)
        resized_w = round(api_w * scale)
        resized_h = round(api_h * scale)
        img_resized = img.resize((resized_w, resized_h), Image.LANCZOS)

        left = round((resized_w - crop_w) * 0.5)
        top = round((resized_h - crop_h) * gravity)
        img_final = img_resized.crop((left, top, left + crop_w, top + crop_h))

    # Composite text and logo for structured styles (pixel-perfect placement)
    if is_structured:
        from PIL import ImageDraw, ImageFont
        import numpy as np

        typo = style["typography"]
        img_final = img_final.convert("RGBA")

        # --- Load font and wrap text ---
        font_name = typo.get("font", "Geist-Bold")
        font_path = _FONT_MAP.get(font_name)
        if not font_path or not font_path.exists():
            print(f"Warning: Font '{font_name}' not found, falling back to Geist-Bold", file=sys.stderr)
            font_path = _FONT_MAP["Geist-Bold"]

        size_pct = typo.get("size_pct", 11)
        font_size = round(crop_h * size_pct / 100)
        font = ImageFont.truetype(str(font_path), font_size)
        line_height_mult = typo.get("line_height", 1.15)
        alignment = typo.get("alignment", "left")

        draw = ImageDraw.Draw(img_final)
        max_text_w = round(crop_w * 0.50)
        words = headline.split()
        lines = []
        current_line = ""
        for word in words:
            test = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] <= max_text_w:
                current_line = test
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        line_h = round(font_size * line_height_mult)
        text_block_w = max(draw.textbbox((0, 0), l, font=font)[2] for l in lines)
        text_block_h = line_h * len(lines)

        # --- Auto-detect best text placement ---
        gray = np.array(img_final.convert("L"), dtype=np.float32)
        pad = 25
        scan_w = text_block_w + pad * 2
        scan_h = text_block_h + pad * 2
        margin_x = round(crop_w * 0.05)
        margin_y = round(crop_h * 0.08)

        # Rule of thirds intersection points
        thirds = [
            (crop_w / 3, crop_h / 3),
            (2 * crop_w / 3, crop_h / 3),
            (crop_w / 3, 2 * crop_h / 3),
            (2 * crop_w / 3, 2 * crop_h / 3),
        ]

        best_score = float("inf")
        best_pos = (margin_x, margin_y)
        for y in range(margin_y, crop_h - scan_h - margin_y, 12):
            for x in range(margin_x, crop_w - scan_w - margin_x, 12):
                region = gray[y:y + scan_h, x:x + scan_w]
                mean = float(region.mean())
                std = float(region.std())

                # Distance to nearest rule-of-thirds intersection
                cx, cy = x + scan_w / 2, y + scan_h / 2
                thirds_dist = min(
                    ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5
                    for tx, ty in thirds
                ) / crop_w

                score = mean * 0.5 + std * 0.35 + thirds_dist * 40
                if score < best_score:
                    best_score = score
                    best_pos = (x + pad, y + pad)

        # --- Pick best text color for contrast against background ---
        tx, ty = best_pos
        # Sample average RGB in the text zone
        text_region = np.array(img_final.convert("RGB"))[
            ty:ty + text_block_h, tx:tx + text_block_w
        ]
        bg_r = float(text_region[:, :, 0].mean())
        bg_g = float(text_region[:, :, 1].mean())
        bg_b = float(text_region[:, :, 2].mean())

        # Relative luminance (WCAG formula)
        def _luminance(r, g, b):
            rs, gs, bs = r / 255, g / 255, b / 255
            rl = rs / 12.92 if rs <= 0.03928 else ((rs + 0.055) / 1.055) ** 2.4
            gl = gs / 12.92 if gs <= 0.03928 else ((gs + 0.055) / 1.055) ** 2.4
            bl = bs / 12.92 if bs <= 0.03928 else ((bs + 0.055) / 1.055) ** 2.4
            return 0.2126 * rl + 0.7152 * gl + 0.0722 * bl

        bg_lum = _luminance(bg_r, bg_g, bg_b)
        best_contrast = 0
        text_color = "#f9dc5c"  # fallback: Royal Gold
        for hex_color, name in _BRAND_PALETTE:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            fg_lum = _luminance(r, g, b)
            # WCAG contrast ratio
            lighter = max(fg_lum, bg_lum)
            darker = min(fg_lum, bg_lum)
            ratio = (lighter + 0.05) / (darker + 0.05)
            if ratio > best_contrast:
                best_contrast = ratio
                text_color = hex_color
                text_color_name = name

        print(
            f"Text placement: ({tx}, {ty}) = "
            f"({tx / crop_w * 100:.0f}%, {ty / crop_h * 100:.0f}%) "
            f"| color: {text_color_name} ({text_color}) contrast={best_contrast:.1f}:1",
            file=sys.stderr,
        )
        y_cursor = ty
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            if alignment == "center":
                x = tx + (text_block_w - line_w) // 2
            elif alignment == "right":
                x = tx + text_block_w - line_w
            else:
                x = tx
            draw.text((x, y_cursor), line, fill=text_color, font=font)
            y_cursor += line_h

        # --- Composite logo kitty-corner to text ---
        logo_img = Image.open(logo_path).convert("RGBA")
        logo_target_w = round(crop_w * 0.14)
        logo_scale = logo_target_w / logo_img.width
        logo_resized = logo_img.resize(
            (round(logo_img.width * logo_scale), round(logo_img.height * logo_scale)),
            Image.LANCZOS,
        )

        text_in_left = (tx + text_block_w / 2) < crop_w / 2
        text_in_top = (ty + text_block_h / 2) < crop_h / 2
        logo_margin_x = round(crop_w * 0.04)
        logo_margin_y = round(crop_h * 0.06)

        if text_in_left:
            lx = crop_w - logo_resized.width - logo_margin_x
        else:
            lx = logo_margin_x
        if text_in_top:
            ly = crop_h - logo_resized.height - logo_margin_y
        else:
            ly = logo_margin_y

        img_final.paste(logo_resized, (lx, ly), logo_resized)
        img_final = img_final.convert("RGB")

    # Save cropped image
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img_final.save(str(out), "PNG")

    # Save raw image alongside
    raw_path = out.with_name(out.stem + "_raw" + out.suffix)
    raw_path.write_bytes(image_bytes)

    return {
        "output": str(out),
        "raw": str(raw_path),
        "size": f"{img_final.size[0]}x{img_final.size[1]}",
        "format": ad_format,
        "ratio": fmt["ratio"],
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
    parser.add_argument("--format", choices=list(AD_FORMATS.keys()), default="feed", help="Ad format preset (default: feed)")
    parser.add_argument("--output", type=str, help="Output file path for cropped image")
    parser.add_argument("--list-styles", action="store_true", help="List available styles and exit")
    parser.add_argument("--list-formats", action="store_true", help="List available ad format presets and exit")
    parser.add_argument("--category", type=str, help="Filter styles by category (with --list-styles)")
    args = parser.parse_args()

    if args.list_formats:
        for name, fmt in AD_FORMATS.items():
            crop_w, crop_h = fmt["crop"]
            print(f"  {name:8s}  {fmt['ratio']:6s}  {crop_w}x{crop_h}  (API: {fmt['api_size']})  {fmt['description']}")
        return

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

    result = generate_image(args.style, args.headline, args.logo, args.output, args.format)
    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
