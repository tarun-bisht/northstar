#!/usr/bin/env python3
"""Make the feed cover images (assets/covers/<part>.png, 1200x630). Run once, or after changing the
look; the PNGs are committed. Feed items without a picture of their own use these, so readers
show a calm tile instead of a blank one. Needs Pillow (only for this script)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "assets" / "covers"
INK, PAPER, BRASS, MUTED = (21, 36, 58), (237, 241, 242), (154, 119, 43), (75, 90, 107)
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
PARTS = {
    "research": ("Research", "Papers and research updates"),
    "news": ("News", "World Radar, with the idea behind each story"),
    "exploration": ("Exploration", "Podcasts, videos, reads and things to try"),
    "shorts": ("Shorts", "Short videos worth a minute"),
    "languages": ("Languages", "A five-minute pack a day"),
    "reading": ("Papers of the week", "For you, trending and from leading groups"),
    "weekly": ("This week", "Research, knowledge and exploration"),
    "monthly": ("This month", "Deep dives and challenges"),
    "quarterly": ("The quarter", "A short look back"),
}


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def cover(key: str, title: str, sub: str) -> None:
    im = Image.new("RGB", (1200, 630), PAPER)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 18, 630], fill=BRASS)
    # a small star mark
    cx, cy, r = 1080, 120, 34
    d.polygon([(cx, cy - r), (cx + 9, cy - 9), (cx + r, cy), (cx + 9, cy + 9), (cx, cy + r),
               (cx - 9, cy + 9), (cx - r, cy), (cx - 9, cy - 9)], fill=BRASS)
    d.text((90, 100), "NORTHSTAR", font=font(SANS, 30), fill=MUTED)
    d.text((90, 250), title, font=font(SERIF, 96), fill=INK)
    d.text((92, 380), sub, font=font(SANS, 38), fill=MUTED)
    d.line([(90, 500), (290, 500)], fill=BRASS, width=4)
    im.save(OUT / f"{key}.png", optimize=True)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for k, (t, s) in PARTS.items():
        cover(k, t, s)
    print(f"{len(PARTS)} covers in {OUT}")
