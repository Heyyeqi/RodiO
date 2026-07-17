#!/usr/bin/env python3
"""
Generate earlyMorning sky gradient PNG for RodiO.
Output: pwa/assets/sky/earlyMorning_sky_gradient.png  (3072×4096)
        pwa/assets/sky/earlyMorning_sky_gradient_preview.png (768×1024)

No external dependencies beyond Pillow.
Does NOT modify any RodiO runtime code.
"""

import math
import os
from PIL import Image

# ── color stops (y position, R, G, B) ──────────────────────────────────────
STOPS = [
    (0.000, 0x05, 0x11, 0x1D),
    (0.200, 0x0B, 0x22, 0x38),
    (0.340, 0x1D, 0x52, 0x78),
    (0.405, 0xCF, 0xEF, 0xFF),  # horizon glow centre
    (0.520, 0x8D, 0xBD, 0xDA),
    (1.000, 0x31, 0x59, 0x7B),
]

# ── horizon glow params ─────────────────────────────────────────────────────
GLOW_CENTER   = 0.405
GLOW_COLOR    = (0xEA, 0xFB, 0xFF)
GLOW_CORE_SIG = 0.030   # gaussian sigma for core
GLOW_OUTER_SIG= 0.095   # gaussian sigma for outer
GLOW_CORE_STR = 0.35
GLOW_OUTER_STR= 0.18

# ── ordered dithering (4×4 Bayer, max amplitude ±0.6/255) ──────────────────
BAYER_4 = [
    [ 0, 8, 2,10],
    [12, 4,14, 6],
    [ 3,11, 1, 9],
    [15, 7,13, 5],
]
DITHER_AMP = 0.6   # per-channel, in [0,255] space


def smoothstep(edge0, edge1, x):
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0))) if edge1 != edge0 else (0.0 if x < edge0 else 1.0)
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def sample_stops(y):
    """Interpolate base gradient from colour stops using smoothstep."""
    if y <= STOPS[0][0]:
        return STOPS[0][1], STOPS[0][2], STOPS[0][3]
    if y >= STOPS[-1][0]:
        return STOPS[-1][1], STOPS[-1][2], STOPS[-1][3]
    for i in range(len(STOPS) - 1):
        y0, r0, g0, b0 = STOPS[i]
        y1, r1, g1, b1 = STOPS[i + 1]
        if y0 <= y <= y1:
            # smoothstep within this segment
            t = smoothstep(y0, y1, y)
            return lerp(r0, r1, t), lerp(g0, g1, t), lerp(b0, b1, t)
    return STOPS[-1][1], STOPS[-1][2], STOPS[-1][3]


def gaussian(x, sigma):
    return math.exp(-0.5 * (x / sigma) ** 2)


def generate(width, height, out_path):
    img = Image.new("RGB", (width, height))
    pixels = img.load()

    for row in range(height):
        y = row / (height - 1)
        br, bg, bb = sample_stops(y)

        # horizon glow
        dist = y - GLOW_CENTER
        core  = gaussian(dist, GLOW_CORE_SIG)  * GLOW_CORE_STR
        outer = gaussian(dist, GLOW_OUTER_SIG) * GLOW_OUTER_STR
        glow  = min(core + outer, 1.0)
        gr, gg, gb = GLOW_COLOR

        fr = lerp(br, gr, glow)
        fg = lerp(bg, gg, glow)
        fb = lerp(bb, gb, glow)

        for col in range(width):
            # Bayer ordered dither: deterministic, no randomness
            bayer_val = BAYER_4[row % 4][col % 4]          # 0..15
            d = (bayer_val / 15.0 - 0.5) * DITHER_AMP      # ±0.3 in [0,255]

            r = max(0, min(255, round(fr + d)))
            g = max(0, min(255, round(fg + d)))
            b = max(0, min(255, round(fb + d)))
            pixels[col, row] = (r, g, b)

    img.save(out_path, "PNG", optimize=False, compress_level=6)
    size = os.path.getsize(out_path)
    print(f"  → {out_path}  ({width}×{height}, {size/1024:.0f} KB)")


if __name__ == "__main__":
    base = os.path.join(os.path.dirname(__file__), "..", "pwa", "assets", "sky")
    os.makedirs(base, exist_ok=True)

    main_path    = os.path.join(base, "earlyMorning_sky_gradient.png")
    preview_path = os.path.join(base, "earlyMorning_sky_gradient_preview.png")

    print("Generating earlyMorning sky gradient …")
    generate(3072, 4096, main_path)
    generate( 768, 1024, preview_path)
    print("Done.")
