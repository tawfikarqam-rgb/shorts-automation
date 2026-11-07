#!/usr/bin/env python3
"""Create a branded 9:16 Shorts thumbnail from an already downloaded scene image.

The script deliberately reuses an existing scene image (preferably a Cloudflare
FLUX image) to avoid an extra image-generation API call for every Short.
"""
import json
import os
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

IMAGE_DIR = Path("MoneyPrinterTurbo/storage/local_videos")
MANIFEST = IMAGE_DIR / "image_manifest.json"
OUTPUT = Path("output/thumbnail.jpg")
SIZE = (1080, 1920)
FONT_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


def choose_source(manifest_path=MANIFEST):
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Image manifest not found: {manifest_path}")
    paths = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(paths, list):
        raise ValueError("Image manifest must contain a list")
    candidates = [Path(item) for item in paths if isinstance(item, str)]
    # Prefer AI-generated artwork when present; otherwise use the first licensed image.
    candidates.sort(key=lambda path: (0 if path.name.startswith("cloudflare_scene_") else 1, str(path)))
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size >= 10000:
            return candidate
    raise FileNotFoundError("No usable source image was found in image_manifest.json")


def wrap_headline(draw, headline, font, max_width):
    words = str(headline or "A STORY WORTH KNOWING").split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), candidate, font=font, stroke_width=2)[2] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) > 3:
        lines = lines[:3]
        last = lines[-1]
        while last and draw.textbbox((0, 0), last + "…", font=font, stroke_width=2)[2] > max_width:
            last = last.rsplit(" ", 1)[0] if " " in last else last[:-1]
        lines[-1] = (last or lines[-1][:12]) + "…"
    return lines


def create_thumbnail(source_path, output_path=OUTPUT, title="", channel="business", font_path=FONT_PATH):
    source_path = Path(source_path)
    output_path = Path(output_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"Thumbnail source image not found: {source_path}")
    if not title or not str(title).strip():
        raise ValueError("STORY_TOPIC is required to create a story-specific thumbnail")

    with Image.open(source_path) as source:
        image = ImageOps.fit(source.convert("RGB"), SIZE, method=Image.Resampling.LANCZOS, centering=(0.5, 0.42))

    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    gradient = ImageDraw.Draw(overlay)
    for y in range(0, 1120, 4):
        alpha = int(205 * (1 - y / 1120))
        gradient.rectangle((0, y, SIZE[0], y + 4), fill=(0, 0, 0, alpha))
    image = Image.alpha_composite(image.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(image)

    font_file = Path(font_path)
    if not font_file.is_file():
        raise FileNotFoundError(f"Thumbnail font not found: {font_file}")

    label = "HISTORY" if str(channel).lower() == "history" else "BUSINESS"
    label_font = ImageFont.truetype(str(font_file), 38)
    headline_font = ImageFont.truetype(str(font_file), 88)

    # Small channel label with a high-contrast capsule.
    label_box = draw.textbbox((0, 0), label, font=label_font)
    label_width = label_box[2] - label_box[0]
    draw.rounded_rectangle((68, 104, 68 + label_width + 58, 178), radius=24, fill=(10, 18, 32, 225))
    draw.text((97, 116), label, font=label_font, fill=(255, 211, 92, 255))

    headline = str(title).strip().upper()
    lines = wrap_headline(draw, headline, headline_font, 930)
    while len(lines) > 2 and headline_font.size > 62:
        headline_font = ImageFont.truetype(str(font_file), headline_font.size - 6)
        lines = wrap_headline(draw, headline, headline_font, 930)

    y = 245
    for line in lines:
        draw.text(
            (68, y), line, font=headline_font, fill=(255, 255, 255, 255),
            stroke_width=5, stroke_fill=(0, 0, 0, 210)
        )
        y += headline_font.size + 24

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output_path, format="JPEG", quality=90, optimize=True, progressive=True)
    with Image.open(output_path) as saved:
        if saved.size != SIZE:
            raise ValueError(f"Unexpected thumbnail dimensions: {saved.size}")
        if saved.format != "JPEG":
            raise ValueError("Thumbnail output is not JPEG")
    if output_path.stat().st_size == 0:
        raise ValueError("Thumbnail output is empty")
    return output_path


def main():
    source = choose_source()
    title = os.environ.get("STORY_TOPIC", "").strip()
    channel = os.environ.get("CHANNEL_NAME", "business").strip().lower()
    result = create_thumbnail(source, OUTPUT, title, channel)
    print(f"THUMBNAIL_GENERATION=SUCCESS")
    print(f"THUMBNAIL_SOURCE={source.name}")
    print(f"THUMBNAIL_FILE={result}")
    print(f"THUMBNAIL_SIZE_BYTES={result.stat().st_size}")


if __name__ == "__main__":
    main()
