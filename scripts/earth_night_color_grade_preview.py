#!/usr/bin/env python3
"""
Generate a technical color-grade preview for:
  pwa/assets/earth_night_8k.jpg

Output:
  pwa/assets/earth_night_8k_preview_color_grade.jpg

This script never overwrites the production night texture.
It uses numpy vectorization for all heavy per-pixel operations.
"""

from __future__ import annotations

import colorsys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys

print("input path: initializing...", flush=True)

try:
    import numpy as np
except Exception as exc:  # pragma: no cover
    print("numpy is required to run this script.", flush=True)
    print(f"import error: {exc}", flush=True)
    print("install command: python -m pip install numpy", flush=True)
    sys.exit(1)

try:
    from PIL import Image, ImageFilter
except Exception as exc:  # pragma: no cover
    print("Pillow is required to run this script.", flush=True)
    print(f"import error: {exc}", flush=True)
    print("install command: python -m pip install Pillow", flush=True)
    sys.exit(1)


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "pwa" / "assets" / "earth_night_8k.jpg"
OUTPUT_PATH = ROOT / "pwa" / "assets" / "earth_night_8k_preview_color_grade.jpg"
BACKUP_PATH = ROOT / "pwa" / "assets" / "source" / "earth_night_8k_before_color_match.jpg"


@dataclass(frozen=True)
class GradeParams:
    shadow_sat_scale: float = 0.89
    middark_sat_scale: float = 0.93
    global_sat_scale: float = 0.965

    shadow_red_scale: float = 0.950
    shadow_green_scale: float = 1.000
    shadow_blue_scale: float = 1.003

    middark_red_scale: float = 0.980
    middark_green_scale: float = 1.000
    middark_blue_scale: float = 1.001

    shadow_hue_shift_deg: float = -9.5
    middark_hue_shift_deg: float = -4.0

    ocean_sat_scale: float = 0.93
    ocean_hue_shift_deg: float = -6.0
    ocean_red_scale: float = 0.970
    ocean_green_scale: float = 1.000
    ocean_blue_scale: float = 1.020

    shadow_gamma: float = 0.990
    global_gamma: float = 0.995
    global_contrast: float = 1.03

    highlight_red_scale: float = 1.030
    highlight_green_scale: float = 1.010
    highlight_blue_scale: float = 0.990

    unsharp_radius: float = 0.7
    unsharp_amount: float = 0.45
    unsharp_threshold: int = 4


PARAMS = GradeParams()


def format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    unit = units[0]
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            break
        value /= 1024.0
    return f"{value:.2f}{unit}"


def clamp01(array: np.ndarray) -> np.ndarray:
    return np.clip(array, 0.0, 1.0)


def smoothstep(edge0: float, edge1: float, value: np.ndarray) -> np.ndarray:
    if edge0 == edge1:
      return np.zeros_like(value)
    t = clamp01((value - edge0) / (edge1 - edge0))
    return t * t * (3.0 - 2.0 * t)


def mix(a: np.ndarray, b: np.ndarray, t: np.ndarray) -> np.ndarray:
    return a * (1.0 - t) + b * t


def shift_hue(h: np.ndarray, delta_deg: np.ndarray) -> np.ndarray:
    return np.mod(h + delta_deg / 360.0, 1.0)


def rgb_to_hsv_vectorized(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]

    maxc = np.max(rgb, axis=-1)
    minc = np.min(rgb, axis=-1)
    delta = maxc - minc

    v = maxc
    s = np.where(maxc > 0, delta / np.maximum(maxc, 1e-8), 0.0)
    h = np.zeros_like(maxc)

    mask = delta > 1e-8
    rmask = mask & (maxc == r)
    gmask = mask & (maxc == g)
    bmask = mask & (maxc == b)

    h[rmask] = np.mod((g[rmask] - b[rmask]) / delta[rmask], 6.0)
    h[gmask] = ((b[gmask] - r[gmask]) / delta[gmask]) + 2.0
    h[bmask] = ((r[bmask] - g[bmask]) / delta[bmask]) + 4.0
    h = np.mod(h / 6.0, 1.0)

    return h, s, v


def hsv_to_rgb_vectorized(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> np.ndarray:
    h6 = h * 6.0
    i = np.floor(h6).astype(np.int32)
    f = h6 - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))

    i = np.mod(i, 6)
    out = np.empty(h.shape + (3,), dtype=np.float32)

    masks = [i == k for k in range(6)]
    out[masks[0]] = np.stack((v[masks[0]], t[masks[0]], p[masks[0]]), axis=-1)
    out[masks[1]] = np.stack((q[masks[1]], v[masks[1]], p[masks[1]]), axis=-1)
    out[masks[2]] = np.stack((p[masks[2]], v[masks[2]], t[masks[2]]), axis=-1)
    out[masks[3]] = np.stack((p[masks[3]], q[masks[3]], v[masks[3]]), axis=-1)
    out[masks[4]] = np.stack((t[masks[4]], p[masks[4]], v[masks[4]]), axis=-1)
    out[masks[5]] = np.stack((v[masks[5]], p[masks[5]], q[masks[5]]), axis=-1)

    return out


def purple_bias_mask(h: np.ndarray, s: np.ndarray, b_dominance: np.ndarray) -> np.ndarray:
    hue_center = 0.72
    hue_width = 0.14
    dist = np.minimum(np.abs(h - hue_center), 1.0 - np.abs(h - hue_center))
    hue_weight = 1.0 - clamp01(dist / hue_width)
    sat_weight = smoothstep(0.10, 0.50, s)
    blue_weight = smoothstep(0.02, 0.18, b_dominance)
    return clamp01(hue_weight * sat_weight * blue_weight)


def ocean_like_mask(
    lum: np.ndarray,
    r: np.ndarray,
    g: np.ndarray,
    b: np.ndarray,
    shadow: np.ndarray,
    middark: np.ndarray,
) -> np.ndarray:
    low_mid_lum = 1.0 - smoothstep(0.24, 0.56, lum)
    blue_dom = smoothstep(0.03, 0.16, b - np.maximum(r, g))
    low_rg_split = 1.0 - smoothstep(0.02, 0.12, np.abs(g - r))
    darkness_pref = clamp01(0.65 * shadow + 0.45 * middark)
    return clamp01(low_mid_lum * blue_dom * low_rg_split * darkness_pref)


def ensure_backup_exists() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")
    BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_bytes(INPUT_PATH.read_bytes())


def apply_highlight_unsharp(base: Image.Image) -> Image.Image:
    sharpened = base.filter(
        ImageFilter.UnsharpMask(
            radius=PARAMS.unsharp_radius,
            percent=int(round(PARAMS.unsharp_amount * 100)),
            threshold=PARAMS.unsharp_threshold,
        )
    )

    base_arr = np.asarray(base, dtype=np.float32)
    sharp_arr = np.asarray(sharpened, dtype=np.float32)
    base_rgb = base_arr / 255.0
    lum = 0.2126 * base_rgb[..., 0] + 0.7152 * base_rgb[..., 1] + 0.0722 * base_rgb[..., 2]
    highlight = smoothstep(0.60, 0.80, lum)[..., None]
    merged = mix(base_arr, sharp_arr, highlight)
    merged = np.clip(np.round(merged), 0, 255).astype(np.uint8)
    return Image.fromarray(merged, mode="RGB")


def grade_image(image: Image.Image) -> Image.Image:
    rgb = np.asarray(image, dtype=np.float32) / 255.0
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]

    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    shadow = 1.0 - smoothstep(0.30, 0.45, lum)
    middark = np.minimum(smoothstep(0.28, 0.40, lum), 1.0 - smoothstep(0.50, 0.62, lum))
    middark = clamp01(middark)
    highlight = smoothstep(0.60, 0.80, lum)

    h, s, v = rgb_to_hsv_vectorized(rgb)
    b_dominance = b - np.maximum(r, g)
    bias = purple_bias_mask(h, s, b_dominance)
    ocean = ocean_like_mask(lum, r, g, b, shadow, middark)

    h = shift_hue(
        h,
        (PARAMS.shadow_hue_shift_deg * shadow * bias) +
        (PARAMS.middark_hue_shift_deg * middark * bias) +
        (PARAMS.ocean_hue_shift_deg * ocean)
    )

    s = clamp01(
        s
        * mix(np.ones_like(shadow), np.full_like(shadow, PARAMS.shadow_sat_scale), shadow)
        * mix(np.ones_like(middark), np.full_like(middark, PARAMS.middark_sat_scale), middark)
        * mix(np.ones_like(ocean), np.full_like(ocean, PARAMS.ocean_sat_scale), ocean)
        * PARAMS.global_sat_scale
    )

    rgb = hsv_to_rgb_vectorized(h, s, v)
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]

    shadow_rgb_weight = shadow * np.maximum(np.full_like(bias, 0.45), bias)
    middark_rgb_weight = middark * np.maximum(np.full_like(bias, 0.35), bias)

    r *= mix(np.ones_like(r), np.full_like(r, PARAMS.shadow_red_scale), shadow_rgb_weight)
    g *= mix(np.ones_like(g), np.full_like(g, PARAMS.shadow_green_scale), shadow_rgb_weight)
    b *= mix(np.ones_like(b), np.full_like(b, PARAMS.shadow_blue_scale), shadow_rgb_weight)

    r *= mix(np.ones_like(r), np.full_like(r, PARAMS.middark_red_scale), middark_rgb_weight)
    g *= mix(np.ones_like(g), np.full_like(g, PARAMS.middark_green_scale), middark_rgb_weight)
    b *= mix(np.ones_like(b), np.full_like(b, PARAMS.middark_blue_scale), middark_rgb_weight)

    r *= mix(np.ones_like(r), np.full_like(r, PARAMS.ocean_red_scale), ocean)
    g *= mix(np.ones_like(g), np.full_like(g, PARAMS.ocean_green_scale), ocean)
    b *= mix(np.ones_like(b), np.full_like(b, PARAMS.ocean_blue_scale), ocean)

    shadow_gamma = mix(np.ones_like(shadow), np.full_like(shadow, PARAMS.shadow_gamma), shadow)
    r = np.power(clamp01(r), shadow_gamma)
    g = np.power(clamp01(g), shadow_gamma)
    b = np.power(clamp01(b), shadow_gamma)

    contrast_weight = 0.5 * shadow + 0.35 * middark
    local_contrast = 1.0 + (PARAMS.global_contrast - 1.0) * contrast_weight
    midpoint = 0.5
    r = clamp01(midpoint + (r - midpoint) * local_contrast)
    g = clamp01(midpoint + (g - midpoint) * local_contrast)
    b = clamp01(midpoint + (b - midpoint) * local_contrast)

    r *= mix(np.ones_like(r), np.full_like(r, PARAMS.highlight_red_scale), highlight)
    g *= mix(np.ones_like(g), np.full_like(g, PARAMS.highlight_green_scale), highlight)
    b *= mix(np.ones_like(b), np.full_like(b, PARAMS.highlight_blue_scale), highlight)

    r = np.power(clamp01(r), PARAMS.global_gamma)
    g = np.power(clamp01(g), PARAMS.global_gamma)
    b = np.power(clamp01(b), PARAMS.global_gamma)

    out = np.stack((r, g, b), axis=-1)
    out = np.clip(np.round(out * 255.0), 0, 255).astype(np.uint8)
    return Image.fromarray(out, mode="RGB")


def main() -> int:
    print(f"input path: {INPUT_PATH}", flush=True)
    print(f"output path: {OUTPUT_PATH}", flush=True)
    print("starting image read...", flush=True)

    ensure_backup_exists()
    before_size = OUTPUT_PATH.stat().st_size if OUTPUT_PATH.exists() else 0
    image = Image.open(INPUT_PATH).convert("RGB")

    print(f"input size: {image.size[0]}x{image.size[1]}", flush=True)
    print(f"mode: {image.mode}", flush=True)
    print("starting processing...", flush=True)

    if image.size != (8192, 4096):
        print(
            f"Unexpected input size {image.size}; expected (8192, 4096).",
            file=sys.stderr,
            flush=True,
        )
        return 1

    graded = grade_image(image)
    print("base grade complete", flush=True)

    final_image = apply_highlight_unsharp(graded)
    print("highlight protection / unsharp complete", flush=True)

    final_image.save(
        OUTPUT_PATH,
        quality=97,
        subsampling=0,
        optimize=False,
        progressive=False,
    )

    after_size = OUTPUT_PATH.stat().st_size if OUTPUT_PATH.exists() else 0
    print(f"output size: {final_image.size[0]}x{final_image.size[1]}", flush=True)
    print(f"output file size: {format_bytes(after_size)}", flush=True)
    print(
        "output file size before/after: "
        f"{format_bytes(before_size)} -> {format_bytes(after_size)}",
        flush=True,
    )
    print(f"saved timestamp: {datetime.now().isoformat(timespec='seconds')}", flush=True)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
