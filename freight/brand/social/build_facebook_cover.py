#!/usr/bin/env python3
"""Render a Facebook cover from RETALLY's verified, unaltered PNG wordmark.

Offline-only utility. Does not modify a social account or web deployment.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT = 1640, 624
SCALE = 2
MASTER_SHA256 = "08421ccd7e8b1db752002f7ea177e76c83b6ee1cae40cf8b459368ade0c4eadd"
DEFAULT_MASTER = Path(__file__).resolve().parents[2] / "site/assets/brand/retally-wordmark-approved.png"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "retally-facebook-cover-1640x624.png"


def _font(size: int, *, strong: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    families = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if strong else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if strong else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in families:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    raise RuntimeError("A DejaVu Sans or Liberation Sans font is required")


def _master_is_verified(path: Path) -> bool:
    return path.name == "retally-wordmark-approved.png" and hashlib.sha256(path.read_bytes()).hexdigest() == MASTER_SHA256


def render(wordmark: Image.Image) -> Image.Image:
    """Create a mobile-safe cover without redrawing the trademark."""
    s = SCALE
    w, h = WIDTH * s, HEIGHT * s
    cover = Image.new("RGB", (w, h))
    pix = cover.load()
    for y in range(h):
        for x in range(w):
            u, v = x / w, y / h
            gleam = max(0.0, 1 - abs(u - .40) / .54) * max(0.0, 1 - abs(v - .12) / .9)
            z = int(17 * gleam)
            pix[x, y] = (10+z, 18+z, 21+z)
    overlay = Image.new("RGBA", (w, h), (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    d.ellipse((-500*s, -520*s, 520*s, 500*s), outline=(24,130,101,70), width=3*s)
    d.ellipse((1200*s, 170*s, 2120*s, 1090*s), outline=(24,130,101,80), width=3*s)
    for i in range(12):
        xx = (85 + i*140)*s
        d.line([(xx,0),(xx-250*s,h)], fill=(255,255,255,5), width=1*s)
    cover = Image.alpha_composite(cover.convert("RGBA"), overlay)

    shadow = Image.new("RGBA", (w,h), (0,0,0,0))
    sd = ImageDraw.Draw(shadow)
    card = (266*s, 76*s, 1374*s, 554*s)
    sd.rounded_rectangle((card[0],card[1]+10*s,card[2],card[3]+12*s), radius=30*s, fill=(0,0,0,165))
    shadow = shadow.filter(ImageFilter.GaussianBlur(25*s))
    cover = Image.alpha_composite(cover, shadow)
    d = ImageDraw.Draw(cover)
    d.rounded_rectangle(card, radius=30*s, fill=(255,255,255,255), outline=(205,226,218,255), width=2*s)
    d.rounded_rectangle((315*s,103*s,1325*s,110*s), radius=4*s, fill=(18,129,98,255))

    logo = wordmark.convert("RGBA")
    original_width, original_height = logo.size
    if original_width < 100 or original_height < 30:
        raise ValueError("Wordmark resolution is unexpectedly small")
    max_w, max_h = 936*s, 177*s
    ratio = min(max_w / original_width, max_h / original_height)
    logo = logo.resize((round(original_width * ratio), round(original_height * ratio)), Image.Resampling.LANCZOS)
    lx, ly = (w-logo.width)//2, 172*s + (177*s-logo.height)//2
    cover.alpha_composite(logo, (lx, ly))
    d = ImageDraw.Draw(cover)
    d.line([(558*s,377*s),(1082*s,377*s)], fill=(27,146,109,255), width=2*s)
    d.text((w//2, 401*s), "FREIGHT BILLING RECOVERY", font=_font(21*s, strong=True), fill=(60,77,73,255), anchor="mt")
    d.text((w//2, 449*s), "Find it. Prove it. Recover it.", font=_font(32*s, strong=True), fill=(23,36,33,255), anchor="mt")
    return cover.convert("RGB").resize((WIDTH,HEIGHT), Image.Resampling.LANCZOS)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wordmark", type=Path, default=DEFAULT_MASTER)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = ap.parse_args()
    if not _master_is_verified(args.wordmark):
        raise SystemExit("REFUSING: source is not the exact approved PNG master (filename/SHA-256 mismatch).")
    with Image.open(args.wordmark) as original:
        result = render(original)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    result.save(args.output, "PNG", optimize=True)
    print(f"Created {args.output}: {result.width}x{result.height} RGB, verified source SHA256={MASTER_SHA256}")


if __name__ == "__main__":
    main()
