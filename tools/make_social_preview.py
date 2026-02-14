"""Generate GitHub social preview image (1280x640).

One-time script. Run from the repo root:
    python tools/make_social_preview.py

Output: assets/social-preview.png
Upload manually via GitHub repo Settings > Social preview.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = REPO_ROOT / "assets" / "logo-256.png"
OUTPUT_PATH = REPO_ROOT / "assets" / "social-preview.png"

BG_COLOR = (42, 42, 58)  # #2A2A3A — logo outline color
TEXT_COLOR = (255, 255, 255)
TAGLINE_COLOR = (200, 200, 220)

WIDTH, HEIGHT = 1280, 640


def main() -> None:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Place logo centered, upper portion
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo = logo.resize((256, 256), Image.NEAREST)
    logo_x = (WIDTH - 256) // 2
    logo_y = 100
    img.paste(logo, (logo_x, logo_y), logo)

    # Title text
    try:
        title_font = ImageFont.truetype("arial.ttf", 64)
        tagline_font = ImageFont.truetype("arial.ttf", 28)
    except OSError:
        title_font = ImageFont.load_default()
        tagline_font = ImageFont.load_default()

    title = "GridFab"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 390), title, fill=TEXT_COLOR, font=title_font)

    tagline = "Pixel art editor where AI and humans edit the same sprite"
    bbox = draw.textbbox((0, 0), tagline, font=tagline_font)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 475), tagline, fill=TAGLINE_COLOR, font=tagline_font)

    img.save(str(OUTPUT_PATH))
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
