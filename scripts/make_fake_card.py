"""Generate a fake camera SD card for development.

Creates <out>/DCIM/100MEDIA/PICT000N.JPG test shots (plus some junk files a
real FAT card accumulates, to prove the scanner skips them). Replace the
whole folder with a copy of a real card's contents whenever you like — the
layout is identical.

Usage:  python scripts/make_fake_card.py [--out sandbox/fakecard] [--count 6]
"""

from __future__ import annotations

import argparse
import colorsys
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def make_shot(n: int, w: int = 1280, h: int = 960) -> Image.Image:
    rng = random.Random(n)  # deterministic per shot
    hue = (n * 0.137) % 1.0

    def col(h_, s, v):
        r, g, b = colorsys.hsv_to_rgb(h_ % 1.0, s, v)
        return (int(r * 255), int(g * 255), int(b * 255))

    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    # sky gradient
    top, bottom = col(hue, 0.55, 0.95), col(hue + 0.08, 0.35, 0.65)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    # sun
    cx, cy, r = rng.randint(w // 5, w - w // 5), rng.randint(h // 6, h // 3), rng.randint(60, 110)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col(hue + 0.45, 0.25, 1.0))
    # mountains
    horizon = int(h * 0.62)
    pts = [(0, h)] + [(int(w * i / 8), horizon - rng.randint(0, h // 4)) for i in range(9)] + [(w, h)]
    d.polygon(pts, fill=col(hue + 0.5, 0.5, 0.30))
    # balloons
    for _ in range(rng.randint(3, 7)):
        bx, by, br = rng.randint(0, w), rng.randint(h // 3, h - 60), rng.randint(14, 42)
        d.ellipse([bx - br, by - br, bx + br, by + br], fill=col(rng.random(), 0.8, 0.95))
    try:
        font = ImageFont.load_default(size=36)
    except TypeError:
        font = ImageFont.load_default()
    d.text((30, h - 70), f"TEST SHOT {n}", fill="white", font=font)
    return img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("sandbox/fakecard"))
    ap.add_argument("--count", type=int, default=6)
    args = ap.parse_args()

    media = args.out / "DCIM" / "100MEDIA"
    media.mkdir(parents=True, exist_ok=True)
    for n in range(1, args.count + 1):
        path = media / f"PICT{n:04d}.JPG"
        make_shot(n).save(path, "JPEG", quality=88)
        print(f"  {path}")
    # junk a real card accumulates — the scanner must ignore all of it
    (media / "._PICT0001.JPG").write_bytes(b"\x00\x05\x16\x07 not a real jpeg")
    (media / "PICT0001.THM").write_bytes(b"thumbnail junk")
    (args.out / "MISC").mkdir(exist_ok=True)
    print(f"fake card ready at {args.out} ({args.count} shots + junk files)")


if __name__ == "__main__":
    main()
