#!/usr/bin/env python3
"""
Generate pwa/assets/earth_night_lights_clean_8k.jpg

Extracts only true city lights from earth_night_8k.jpg.
Non-light areas (dark ocean, purple-grey land) are driven to pure black.
Original source file is never modified.

Algorithm:
  lum   = luminance(rgb)
  mask  = smoothstep(LOW, HIGH, lum)          # 0 = dark bg, 1 = bright lights
  clean = rgb * mask                           # zero out background
  clean = normalize_hue(clean)                 # optional: warm-shift residual blue cast
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
try:
    from PIL import Image
except ImportError:
    print("Pillow required: pip install Pillow")
    sys.exit(1)

ROOT       = Path(__file__).resolve().parents[1]
SRC        = ROOT / "pwa" / "assets" / "earth_night_8k.jpg"
DST        = ROOT / "pwa" / "assets" / "earth_night_lights_clean_8k.jpg"
PREVIEW    = ROOT / "pwa" / "assets" / "earth_night_lights_clean_preview.jpg"

# Smoothstep thresholds (0–1 normalised luminance).
# Pixels below LOW  → fully masked out (black).
# Pixels above HIGH → fully visible.
LOW  = 0.08
HIGH = 0.28

# Optional: pull residual blue dominance toward neutral.
# 0 = no correction, 1 = full.  0.3 is a light touch.
BLUE_CORRECTION = 0.30


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def process(rgb: np.ndarray) -> np.ndarray:
    f = rgb.astype(np.float32) / 255.0
    r, g, b = f[..., 0], f[..., 1], f[..., 2]

    # Luminance (Rec.709)
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b

    # Smoothstep mask — drives dark background to 0
    mask = smoothstep(LOW, HIGH, lum)          # shape (H, W)

    # Light-selective blue correction:
    # in the raw Black Marble, lit areas have a slight blue cast from atmosphere.
    # We nudge b toward mid where blue dominates, proportional to the mask.
    b_dom  = np.clip(b - np.maximum(r, g), 0.0, 1.0)
    b_pull = b_dom * BLUE_CORRECTION * mask
    b      = np.clip(b - b_pull, 0.0, 1.0)

    # Apply mask
    clean = np.stack([r, g, b], axis=-1) * mask[..., None]
    clean = np.clip(clean * 255.0, 0, 255).astype(np.uint8)
    return clean


def stats(arr: np.ndarray, label: str) -> None:
    f = arr.astype(np.float32) / 255.0
    lum = 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]
    lit = lum > 0.01
    pct = lit.sum() / lum.size * 100
    print(f"  {label}: lit pixels={pct:.2f}%  mean_lum_lit={lum[lit].mean():.3f}")


def main() -> int:
    print(f"source : {SRC}")
    print(f"output : {DST}")

    if not SRC.exists():
        print(f"ERROR: source not found: {SRC}")
        return 1

    print("loading…")
    # Suppress PIL decompression-bomb warning for large images
    Image.MAX_IMAGE_PIXELS = None
    img = Image.open(SRC).convert("RGB")
    print(f"  size: {img.size[0]}×{img.size[1]}")

    rgb = np.array(img)
    stats(rgb, "source")

    print(f"processing  (LOW={LOW}  HIGH={HIGH}  blue_correction={BLUE_CORRECTION})…")
    clean = process(rgb)
    stats(clean, "clean ")

    out = Image.fromarray(clean, mode="RGB")
    out.save(DST, quality=95, subsampling=0, optimize=False, progressive=False)
    print(f"saved: {DST}  ({DST.stat().st_size / 1e6:.1f} MB)")

    # Small preview (2048×1024) for quick visual check
    preview = out.resize((2048, 1024), Image.LANCZOS)
    preview.save(PREVIEW, quality=88)
    print(f"preview: {PREVIEW}")

    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
