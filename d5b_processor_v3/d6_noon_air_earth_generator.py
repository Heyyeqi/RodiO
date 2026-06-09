#!/usr/bin/env python3
"""
D6 Noon Air Earth Generator — Standalone color grading pass toward Noon Air Earth aesthetic.

PROHIBITIONS (enforced by module-level assertions and runtime checks):
  - Does NOT modify pwa/earth3d.js
  - Does NOT modify DAY_TEXTURE_VARIANT
  - Does NOT write to pwa/assets/earth/production/
  - Does NOT write to pwa/assets/earth/candidates/
  - Does NOT write to pwa/assets/source/
  - Does NOT execute git add, commit, or push
  - Does NOT overwrite any existing candidate JPG
  - Default mode is 2K dry-run only; --full-res required for 8K
  - Output ONLY to: d5b_processor_v3/d5b_output/noon_air_candidates/

Visual target: Noon Air Earth / 正午空气蓝地球
Spec authority: docs/rodio_day_earth_target_color_spec_and_benchmark_matrix.md
Design authority: docs/phase_b1_noon_air_generator_script_design.md
Decisions: docs/phase_b1_1_noon_air_open_questions_resolution.md
"""

import os
import sys
import json
import math
import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageDraw

# ── Path constants ─────────────────────────────────────────────────────────────
REPO_ROOT    = Path(__file__).resolve().parent.parent
SOURCE_PATH  = REPO_ROOT / "pwa/assets/source/earth_day_source_21600x10800.jpg"
BASELINE_PATH = REPO_ROOT / "pwa/assets/earth/candidates/d5z_b_8192x4096.jpg"
OUT_DIR      = REPO_ROOT / "d5b_processor_v3/d5b_output/noon_air_candidates"
CROPS_DIR    = OUT_DIR / "compare_crops"
PROD_DIR     = REPO_ROOT / "pwa/assets/earth/production"
CAND_DIR     = REPO_ROOT / "pwa/assets/earth/candidates"

# ── Module-level safety assertions (evaluated at import time) ──────────────────
assert "production" not in str(OUT_DIR), "OUT_DIR must not be inside production/"
assert OUT_DIR != CAND_DIR,             "OUT_DIR must not be pwa/assets/earth/candidates/"
assert OUT_DIR != PROD_DIR,             "OUT_DIR must not be pwa/assets/earth/production/"
assert not OUT_DIR.is_relative_to(PROD_DIR), "OUT_DIR must not be inside production/"
assert not OUT_DIR.is_relative_to(CAND_DIR), "OUT_DIR must not be inside candidates/"

# ── Working resolutions ────────────────────────────────────────────────────────
RES_2K = (2048, 1024)
RES_8K = (8192, 4096)

# ── Global base adjustment parameters (spec §4.1) ─────────────────────────────
GLOBAL_BASE = {
    "brightness":   +0.04,    # +3% to +6%, midpoint
    "contrast":     -0.045,   # -3% to -6%, midpoint
    "saturation":   -0.06,    # -4% to -8%, midpoint
    "blue_channel": +0.06,    # +4% to +8%, midpoint
    "green_sat":    -0.12,    # -8% to -15%, midpoint
    "yellow_sat":   -0.08,    # -5% to -12%, midpoint
}

# ── Atmospheric overlay parameters (spec §4.2) ────────────────────────────────
ATMOSPHERE = {
    "color_rgb": (143, 196, 230),  # #8FC4E6
    "opacity":   0.06,             # 4–8%, hard cap 10%
}

# ── Noon Air ocean regions (spec §5.1–5.2) ────────────────────────────────────
# Each entry: (name, lon_w, lon_e, lat_s, lat_n, hue_shift, sat_delta, lit_delta,
#              feather_px_8k, ocean_only, deep_only, priority, cross_antimeridian)
NOON_AIR_OCEAN_REGIONS = [
    # priority 0 — global deep ocean base
    dict(name="global_deep_base",      lon_w=-180, lon_e=180,  lat_s=-90,  lat_n=90,
         hue_shift=+2,  sat_delta=-0.04, lit_delta=-0.02,
         feather_px_8k=0,  ocean_only=True,  deep_only=True,  priority=0, cross_am=False),
    # priority 1 — ocean basins
    dict(name="pacific_deep_north",    lon_w=130,  lon_e=240,  lat_s=0,    lat_n=60,
         hue_shift=+3,  sat_delta=-0.05, lit_delta=-0.02,
         feather_px_8k=60, ocean_only=True, deep_only=True, priority=1, cross_am=True),
    dict(name="pacific_deep_south",    lon_w=140,  lon_e=280,  lat_s=-60,  lat_n=0,
         hue_shift=+3,  sat_delta=-0.05, lit_delta=-0.02,
         feather_px_8k=60, ocean_only=True, deep_only=True, priority=1, cross_am=True),
    dict(name="atlantic_deep",         lon_w=-80,  lon_e=20,   lat_s=-50,  lat_n=65,
         hue_shift=+2,  sat_delta=-0.03, lit_delta=-0.01,
         feather_px_8k=50, ocean_only=True, deep_only=True, priority=1, cross_am=False),
    dict(name="indian_ocean_deep",     lon_w=40,   lon_e=120,  lat_s=-50,  lat_n=25,
         hue_shift=+2,  sat_delta=-0.06, lit_delta=-0.02,
         feather_px_8k=50, ocean_only=True, deep_only=True, priority=1, cross_am=False),
    dict(name="southern_ocean",        lon_w=-180, lon_e=180,  lat_s=-70,  lat_n=-50,
         hue_shift=+4,  sat_delta=-0.04, lit_delta=-0.01,
         feather_px_8k=40, ocean_only=True, deep_only=False, priority=1, cross_am=False),
    dict(name="arctic_ocean",          lon_w=-180, lon_e=180,  lat_s=70,   lat_n=90,
         hue_shift=+5,  sat_delta=-0.03, lit_delta=+0.01,
         feather_px_8k=30, ocean_only=True, deep_only=False, priority=1, cross_am=False),
    # priority 2 — continental shelf / mid-shallow
    dict(name="yellow_sea_bohai",      lon_w=117,  lon_e=127,  lat_s=28,   lat_n=42,
         hue_shift=+4,  sat_delta=-0.02, lit_delta=+0.04,
         feather_px_8k=20, ocean_only=True, deep_only=False, priority=2, cross_am=False),
    dict(name="east_china_sea",        lon_w=118,  lon_e=132,  lat_s=24,   lat_n=34,
         hue_shift=+3,  sat_delta=+0.01, lit_delta=+0.05,
         feather_px_8k=20, ocean_only=True, deep_only=False, priority=2, cross_am=False),
    dict(name="sea_of_japan",          lon_w=128,  lon_e=142,  lat_s=34,   lat_n=52,
         hue_shift=+2,  sat_delta=-0.04, lit_delta=-0.03,
         feather_px_8k=20, ocean_only=True, deep_only=False, priority=2, cross_am=False),
    dict(name="south_china_sea_north", lon_w=105,  lon_e=125,  lat_s=15,   lat_n=25,
         hue_shift=+3,  sat_delta=+0.02, lit_delta=+0.04,
         feather_px_8k=24, ocean_only=True, deep_only=False, priority=2, cross_am=False),
    dict(name="persian_gulf",          lon_w=47,   lon_e=60,   lat_s=22,   lat_n=30,
         hue_shift=+3,  sat_delta=+0.02, lit_delta=+0.05,
         feather_px_8k=16, ocean_only=True, deep_only=False, priority=2, cross_am=False),
    dict(name="north_sea_baltic",      lon_w=-5,   lon_e=30,   lat_s=52,   lat_n=66,
         hue_shift=+4,  sat_delta=-0.02, lit_delta=+0.03,
         feather_px_8k=16, ocean_only=True, deep_only=False, priority=2, cross_am=False),
    dict(name="australian_shelf",      lon_w=110,  lon_e=160,  lat_s=-40,  lat_n=-10,
         hue_shift=+3,  sat_delta=+0.01, lit_delta=+0.03,
         feather_px_8k=24, ocean_only=True, deep_only=False, priority=2, cross_am=False),
]

# ── Special sea regions (spec §11) ────────────────────────────────────────────
NOON_AIR_SPECIAL_SEAS = [
    # (name, lon_w, lon_e, lat_s, lat_n, hue_shift, sat_delta, lit_delta, feather_px_8k)
    dict(name="mediterranean",  lon_w=-6,  lon_e=37,  lat_s=30, lat_n=48,
         hue_shift=+2, sat_delta=-0.01, lit_delta=-0.01, feather_px_8k=20),
    dict(name="red_sea",        lon_w=32,  lon_e=44,  lat_s=12, lat_n=30,
         hue_shift=+2, sat_delta=+0.01, lit_delta=+0.02, feather_px_8k=12),
    dict(name="caribbean_deep", lon_w=-90, lon_e=-60, lat_s=10, lat_n=28,
         hue_shift=+2, sat_delta=+0.02, lit_delta=+0.03, feather_px_8k=24),
]

# ── Island halo definitions (spec §6) ─────────────────────────────────────────
# tropical=True uses cyan-blue; tropical=False uses cold blue-grey
NOON_AIR_ISLAND_HALOS = [
    # Tropical islands
    dict(name="maldives",          center=(73.5,   3.5),   halo_km=100, tropical=True,
         hue_shift=+5, sat_delta=+0.08, lit_delta=+0.08, blend=0.20, feather_px_8k=10),
    dict(name="seychelles",        center=(55.5,   -4.5),  halo_km=120, tropical=True,
         hue_shift=+5, sat_delta=+0.07, lit_delta=+0.07, blend=0.18, feather_px_8k=10),
    dict(name="mauritius_reunion", center=(57.5,  -20.0),  halo_km=120, tropical=True,
         hue_shift=+4, sat_delta=+0.06, lit_delta=+0.06, blend=0.15, feather_px_8k=10),
    dict(name="comoros",           center=(43.5,  -12.0),  halo_km=100, tropical=True,
         hue_shift=+5, sat_delta=+0.07, lit_delta=+0.07, blend=0.18, feather_px_8k=8),
    dict(name="bahamas",           center=(-76.5,  24.5),  halo_km=160, tropical=True,
         hue_shift=+4, sat_delta=+0.09, lit_delta=+0.10, blend=0.25, feather_px_8k=14),
    dict(name="lesser_antilles",   center=(-62.5,  15.0),  halo_km=140, tropical=True,
         hue_shift=+4, sat_delta=+0.07, lit_delta=+0.08, blend=0.20, feather_px_8k=12),
    dict(name="caribbean_cuba",    center=(-79.5,  21.5),  halo_km=180, tropical=True,
         hue_shift=+3, sat_delta=+0.06, lit_delta=+0.07, blend=0.18, feather_px_8k=16),
    dict(name="hawaii",            center=(-156.0, 20.5),  halo_km=160, tropical=True,
         hue_shift=+4, sat_delta=+0.07, lit_delta=+0.07, blend=0.18, feather_px_8k=14),
    dict(name="french_polynesia",  center=(-149.0,-17.5),  halo_km=300, tropical=True,
         hue_shift=+5, sat_delta=+0.08, lit_delta=+0.08, blend=0.22, feather_px_8k=20),
    dict(name="fiji",              center=(178.0, -18.0),  halo_km=160, tropical=True,
         hue_shift=+5, sat_delta=+0.08, lit_delta=+0.08, blend=0.20, feather_px_8k=14),
    dict(name="tonga_samoa",       center=(-172.0,-17.0),  halo_km=160, tropical=True,
         hue_shift=+5, sat_delta=+0.07, lit_delta=+0.08, blend=0.20, feather_px_8k=14),
    dict(name="micronesia_palau",  center=(135.0,   7.5),  halo_km=200, tropical=True,
         hue_shift=+5, sat_delta=+0.08, lit_delta=+0.08, blend=0.20, feather_px_8k=16),
    dict(name="solomon_vanuatu",   center=(159.0, -12.0),  halo_km=200, tropical=True,
         hue_shift=+5, sat_delta=+0.08, lit_delta=+0.08, blend=0.20, feather_px_8k=16),
    dict(name="indonesia_east",    center=(132.0,  -4.0),  halo_km=200, tropical=True,
         hue_shift=+4, sat_delta=+0.06, lit_delta=+0.06, blend=0.16, feather_px_8k=16),
    dict(name="philippines_south", center=(122.0,   8.5),  halo_km=180, tropical=True,
         hue_shift=+4, sat_delta=+0.06, lit_delta=+0.06, blend=0.16, feather_px_8k=14),
    dict(name="bermuda",           center=(-64.7,  32.3),  halo_km=80,  tropical=True,
         hue_shift=+4, sat_delta=+0.07, lit_delta=+0.07, blend=0.18, feather_px_8k=8),
    dict(name="azores",            center=(-27.5,  38.5),  halo_km=120, tropical=True,
         hue_shift=+3, sat_delta=+0.05, lit_delta=+0.05, blend=0.15, feather_px_8k=10),
    dict(name="canary_islands",    center=(-15.5,  28.0),  halo_km=140, tropical=True,
         hue_shift=+3, sat_delta=+0.05, lit_delta=+0.05, blend=0.15, feather_px_8k=12),
    # High-latitude islands — cold blue-grey palette
    dict(name="svalbard",          center=(17.5,  78.5),   halo_km=160, tropical=False,
         hue_shift=+6, sat_delta=-0.02, lit_delta=+0.04, blend=0.12, feather_px_8k=12),
    dict(name="franz_josef",       center=(55.0,  80.5),   halo_km=120, tropical=False,
         hue_shift=+6, sat_delta=-0.02, lit_delta=+0.03, blend=0.10, feather_px_8k=10),
    dict(name="canadian_arctic",   center=(-90.0, 74.0),   halo_km=300, tropical=False,
         hue_shift=+5, sat_delta=-0.01, lit_delta=+0.03, blend=0.12, feather_px_8k=20),
    dict(name="greenland_periph",  center=(-40.0, 65.0),   halo_km=200, tropical=False,
         hue_shift=+5, sat_delta=-0.01, lit_delta=+0.04, blend=0.12, feather_px_8k=16),
    dict(name="south_georgia",     center=(-36.5, -54.5),  halo_km=120, tropical=False,
         hue_shift=+5, sat_delta=-0.02, lit_delta=+0.03, blend=0.10, feather_px_8k=10),
    dict(name="south_shetland",    center=(-58.5, -62.5),  halo_km=160, tropical=False,
         hue_shift=+5, sat_delta=-0.02, lit_delta=+0.03, blend=0.10, feather_px_8k=12),
    dict(name="falkland_islands",  center=(-59.0, -51.5),  halo_km=140, tropical=False,
         hue_shift=+4, sat_delta=-0.01, lit_delta=+0.03, blend=0.10, feather_px_8k=12),
    dict(name="aleutian_islands",  center=(-170.0, 52.5),  halo_km=200, tropical=False,
         hue_shift=+4, sat_delta=-0.01, lit_delta=+0.03, blend=0.12, feather_px_8k=16),
]

# ── Protected regions for baseline floor guard (spec §15) ─────────────────────
PROTECTED_REGIONS = {
    "japan":           dict(lat_min=30,  lat_max=46,  lon_min=128, lon_max=148),
    "mediterranean":   dict(lat_min=30,  lat_max=48,  lon_min=-10, lon_max=42),
    "caribbean":       dict(lat_min=10,  lat_max=28,  lon_min=-90, lon_max=-60),
    "pacific_islands": dict(lat_min=-15, lat_max=20,  lon_min=140, lon_max=220),
}

GUARD_THRESHOLDS = {
    "mean_rgb_delta":  8.0,
    "luminance_delta": 0.04,
}

# ── Benchmark crops for compare output (spec §5.15) ───────────────────────────
BENCHMARK_CROPS = {
    "maldives":          dict(lon=73.5,    lat=3.5,    w=640, h=320),
    "bahamas":           dict(lon=-76.5,   lat=24.5,   w=640, h=320),
    "caribbean":         dict(lon=-75.0,   lat=18.0,   w=640, h=320),
    "antarctica":        dict(lon=0.0,     lat=-80.0,  w=640, h=320),
    "greenland":         dict(lon=-42.0,   lat=72.0,   w=640, h=320),
    "yellow_east_china": dict(lon=123.0,   lat=32.0,   w=640, h=320),
    "japan":             dict(lon=136.0,   lat=37.0,   w=640, h=320),
    "sahara":            dict(lon=20.0,    lat=25.0,   w=640, h=320),
    "mediterranean":     dict(lon=16.0,    lat=39.0,   w=640, h=320),
    "red_sea":           dict(lon=38.0,    lat=21.0,   w=640, h=320),
    "french_polynesia":  dict(lon=-149.0,  lat=-17.5,  w=640, h=320),
    "hawaii":            dict(lon=-156.0,  lat=20.0,   w=640, h=320),
    "tibetan_plateau":   dict(lon=90.0,    lat=33.0,   w=640, h=320),
    "amazon":            dict(lon=-60.0,   lat=-3.0,   w=640, h=320),
    "pacific_islands":   dict(lon=170.0,   lat=10.0,   w=640, h=320),
    "europe_wide":       dict(lon=15.0,    lat=50.0,   w=640, h=320),
}


# ══════════════════════════════════════════════════════════════════════════════
# Grid helpers
# ══════════════════════════════════════════════════════════════════════════════

def build_grids(h: int, w: int):
    lat = np.linspace(90, -90, h, dtype=np.float32)
    lon = np.linspace(-180, 180, w, dtype=np.float32)
    LON, LAT = np.meshgrid(lon, lat)
    return LAT, LON


def km_to_pixels(radius_km: float, image_width: int) -> int:
    """Convert halo radius in km to pixels at given equirectangular image width."""
    KM_PER_PX_8K = 40075.0 / 8192.0
    base_px = radius_km / KM_PER_PX_8K
    return max(1, round(base_px * image_width / 8192))


def scale_feather(feather_px_8k: int, image_width: int) -> int:
    """Scale feather radius from 8K baseline to current working resolution."""
    return max(1, round(feather_px_8k * image_width / 8192))


def feather_mask(mask: np.ndarray, feather_px: int) -> np.ndarray:
    """Apply Gaussian blur to a binary mask to produce a soft boundary."""
    if feather_px <= 0:
        return mask.astype(np.float32)
    mask_img = Image.fromarray((mask * 255).astype(np.uint8))
    blurred = mask_img.filter(ImageFilter.GaussianBlur(radius=feather_px))
    return np.array(blurred, dtype=np.float32) / 255.0


def region_mask_rect(LAT: np.ndarray, LON: np.ndarray,
                     lat_min: float, lat_max: float,
                     lon_min: float, lon_max: float,
                     feather_px: int = 0,
                     cross_antimeridian: bool = False) -> np.ndarray:
    """Build float32 [0,1] rect mask; handles cross-antimeridian bounds."""
    if cross_antimeridian or lon_max > 180:
        lon_max_wrap = lon_max if lon_max <= 180 else lon_max - 360
        m = (LAT >= lat_min) & (LAT <= lat_max) & (
            (LON >= lon_min) | (LON <= lon_max_wrap)
        )
    else:
        m = (LAT >= lat_min) & (LAT <= lat_max) & (LON >= lon_min) & (LON <= lon_max)
    return feather_mask(m.astype(np.float32), feather_px)


def circle_mask(LAT: np.ndarray, LON: np.ndarray,
                center_lon: float, center_lat: float,
                radius_px: int, feather_px: int,
                image_width: int) -> np.ndarray:
    """Build a circular mask in pixel space centered on (center_lon, center_lat)."""
    H, W = LAT.shape
    cx = (center_lon + 180.0) / 360.0 * W
    cy = (90.0 - center_lat) / 180.0 * H
    ys = np.arange(H, dtype=np.float32)
    xs = np.arange(W, dtype=np.float32)
    XX, YY = np.meshgrid(xs, ys)
    dist = np.sqrt((XX - cx) ** 2 + (YY - cy) ** 2)
    mask = (dist <= radius_px).astype(np.float32)
    return feather_mask(mask, feather_px)


# ══════════════════════════════════════════════════════════════════════════════
# Pixel classifiers
# ══════════════════════════════════════════════════════════════════════════════

def luminance(f32: np.ndarray) -> np.ndarray:
    return f32[:, :, 0] * 0.299 + f32[:, :, 1] * 0.587 + f32[:, :, 2] * 0.114


def sat_hsv(f32: np.ndarray) -> np.ndarray:
    mx = f32.max(axis=2)
    mn = f32.min(axis=2)
    return np.where(mx > 1e-6, (mx - mn) / mx, 0.0)


def ocean_px(f32: np.ndarray) -> np.ndarray:
    """Float mask of ocean pixels: blue-dominant, not ice."""
    R, G, B = f32[:, :, 0], f32[:, :, 1], f32[:, :, 2]
    is_blue = (B > R + 15) & (B > G + 5) & (R < 120)
    is_ice  = (R > 200) & (G > 200) & (B > 200)
    return (is_blue & ~is_ice).astype(np.float32)


def deep_ocean_px(f32: np.ndarray) -> np.ndarray:
    """Float mask of clearly deep-ocean pixels."""
    R, G, B = f32[:, :, 0], f32[:, :, 1], f32[:, :, 2]
    return ((R < 80) & (B > 85) & (B > R + 30) & (G < B * 0.65)).astype(np.float32)


def land_px(f32: np.ndarray) -> np.ndarray:
    """Float mask of non-ocean, non-ice pixels."""
    R, G, B = f32[:, :, 0], f32[:, :, 1], f32[:, :, 2]
    is_ocean = (B > R + 20) & (B > G + 10) & (R < 100)
    is_ice   = (R > 220) & (G > 220) & (B > 220)
    return (~is_ocean & ~is_ice).astype(np.float32)


def ice_px(f32: np.ndarray) -> np.ndarray:
    """Float mask of snow/ice pixels: near-white and near-neutral."""
    lum    = luminance(f32)
    spread = f32.max(axis=2) - f32.min(axis=2)
    return ((lum > 155) & (spread < 55)).astype(np.float32)


def desert_px(f32: np.ndarray) -> np.ndarray:
    """Float mask of warm-tone bright land pixels (desert candidates)."""
    R, G, B = f32[:, :, 0], f32[:, :, 1], f32[:, :, 2]
    lum = luminance(f32)
    land = land_px(f32)
    warm = (R > G) & (R > B + 10) & (lum > 110)
    return (land * warm.astype(np.float32))


# ══════════════════════════════════════════════════════════════════════════════
# HSL-delta helpers
# ══════════════════════════════════════════════════════════════════════════════

def rgb_to_hsl_array(f32: np.ndarray):
    """Convert float32 [0,255] RGB array to HSL arrays (H in degrees, S and L in [0,1])."""
    r = f32[:, :, 0] / 255.0
    g = f32[:, :, 1] / 255.0
    b = f32[:, :, 2] / 255.0
    c_max = np.maximum(np.maximum(r, g), b)
    c_min = np.minimum(np.minimum(r, g), b)
    delta = c_max - c_min

    L = (c_max + c_min) / 2.0
    S = np.where(delta < 1e-7, 0.0,
                 delta / (1.0 - np.abs(2.0 * L - 1.0) + 1e-7))
    S = np.clip(S, 0.0, 1.0)

    H = np.zeros_like(L)
    mask_r = (c_max == r) & (delta > 1e-7)
    mask_g = (c_max == g) & (delta > 1e-7)
    mask_b = (c_max == b) & (delta > 1e-7)
    H[mask_r] = (60.0 * ((g[mask_r] - b[mask_r]) / (delta[mask_r] + 1e-7)) % 360)
    H[mask_g] = (60.0 * ((b[mask_g] - r[mask_g]) / (delta[mask_g] + 1e-7)) + 120.0) % 360
    H[mask_b] = (60.0 * ((r[mask_b] - g[mask_b]) / (delta[mask_b] + 1e-7)) + 240.0) % 360

    return H, S, L


def hsl_to_rgb_array(H: np.ndarray, S: np.ndarray, L: np.ndarray) -> np.ndarray:
    """Convert HSL arrays back to float32 [0,255] RGB array."""
    C = (1.0 - np.abs(2.0 * L - 1.0)) * S
    X = C * (1.0 - np.abs((H / 60.0) % 2.0 - 1.0))
    m = L - C / 2.0

    R = np.zeros_like(H)
    G = np.zeros_like(H)
    B = np.zeros_like(H)

    for lo, hi, ri, gi, bi in [
        (0,   60,  C, X, np.zeros_like(H)),
        (60,  120, X, C, np.zeros_like(H)),
        (120, 180, np.zeros_like(H), C, X),
        (180, 240, np.zeros_like(H), X, C),
        (240, 300, X, np.zeros_like(H), C),
        (300, 360, C, np.zeros_like(H), X),
    ]:
        m_seg = (H >= lo) & (H < hi)
        R[m_seg] = ri[m_seg] if hasattr(ri, '__getitem__') else ri
        G[m_seg] = gi[m_seg] if hasattr(gi, '__getitem__') else gi
        B[m_seg] = bi[m_seg] if hasattr(bi, '__getitem__') else bi

    out = np.stack([(R + m) * 255.0, (G + m) * 255.0, (B + m) * 255.0], axis=2)
    return np.clip(out, 0, 255)


def apply_hsl_delta(f32: np.ndarray, mask: np.ndarray,
                    hue_shift: float = 0.0,
                    sat_delta: float = 0.0,
                    lit_delta: float = 0.0,
                    hue_range: tuple = None) -> np.ndarray:
    """
    Apply HSL-delta adjustments to pixels selected by mask.
    hue_range: (min_hue, max_hue) in degrees to restrict which hues are modified.
    """
    out = f32.copy()
    H, S, L = rgb_to_hsl_array(f32)

    active = mask > 0

    if hue_range is not None:
        hue_gate = (H >= hue_range[0]) & (H <= hue_range[1])
        active = active & hue_gate

    if not active.any():
        return out

    H_new = np.where(active, (H + hue_shift) % 360, H)
    S_new = np.where(active, np.clip(S + sat_delta, 0.0, 1.0), S)
    L_new = np.where(active, np.clip(L + lit_delta, 0.0, 1.0), L)

    adjusted = hsl_to_rgb_array(H_new, S_new, L_new)
    mask3 = mask[:, :, np.newaxis]
    out = out * (1.0 - mask3) + adjusted * mask3
    return np.clip(out, 0, 255)


# ══════════════════════════════════════════════════════════════════════════════
# Module: validate_assets
# ══════════════════════════════════════════════════════════════════════════════

def validate_assets(baseline_path: Path, log: list):
    log.append("[VALIDATE] Checking assets...")

    if not SOURCE_PATH.exists():
        sys.exit(f"[VALIDATE] ABORT: Source not found: {SOURCE_PATH}")

    # Check baseline (d5z_b) — ABORT if missing (Q3 decision: hard abort)
    if not baseline_path.exists():
        print(f"""
[GUARD] ERROR: d5z_b baseline file not found.
  Expected: {baseline_path}
  The E1 / d5z_b baseline floor comparison cannot be performed.
  This candidate generation cannot be trusted without baseline verification.

  Resolution: Ensure d5z_b_8192x4096.jpg is present in pwa/assets/earth/candidates/.
  Copy it from production:
    cp pwa/assets/earth/production/d5z_b_8192x4096.jpg \\
       pwa/assets/earth/candidates/d5z_b_8192x4096.jpg

  Aborting.
""", file=sys.stderr)
        sys.exit(1)

    log.append(f"[VALIDATE] Source: {SOURCE_PATH} — OK")
    log.append(f"[VALIDATE] Baseline: {baseline_path} — OK")
    log.append(f"[VALIDATE] Output dir: {OUT_DIR}")


def validate_resolution(arr: np.ndarray, expected_wh: tuple, log: list):
    H, W = arr.shape[:2]
    ew, eh = expected_wh
    if W != ew or H != eh:
        sys.exit(f"[VALIDATE] ABORT: Expected {ew}×{eh}, got {W}×{H}")
    assert arr.dtype == np.uint8, "Array must be uint8"
    log.append(f"[VALIDATE] Resolution {W}×{H} — OK")


def ensure_safe_output_path(out_dir: Path, log: list):
    """Runtime assertion that output path is safe (redundant with module-level, but explicit)."""
    prod_str = str(PROD_DIR.resolve())
    cand_str = str(CAND_DIR.resolve())
    out_str  = str(out_dir.resolve())
    if prod_str in out_str:
        sys.exit(f"[SAFETY] ABORT: Output path contains production/: {out_dir}")
    if out_str == cand_str:
        sys.exit(f"[SAFETY] ABORT: Output path is candidates/: {out_dir}")
    log.append(f"[SAFETY] Output path assertion: PASS")


# ══════════════════════════════════════════════════════════════════════════════
# Module: load_source
# ══════════════════════════════════════════════════════════════════════════════

def load_source(res: tuple, log: list) -> np.ndarray:
    w, h = res
    log.append(f"[LOAD] Loading source: {SOURCE_PATH}")
    img = Image.open(SOURCE_PATH).convert("RGB")
    sw, sh = img.size
    log.append(f"[LOAD] Source size: {sw}×{sh}")
    if (sw, sh) != (w, h):
        t0 = datetime.now()
        img = img.resize((w, h), Image.LANCZOS)
        elapsed = (datetime.now() - t0).total_seconds()
        log.append(f"[LOAD] Downscaled to {w}×{h} in {elapsed:.1f}s")
    arr = np.array(img, dtype=np.uint8)
    log.append(f"[LOAD] Array shape: {arr.shape}, dtype: {arr.dtype}")
    return arr


def load_baseline_d5zb(res: tuple, baseline_path: Path, log: list) -> np.ndarray:
    w, h = res
    log.append(f"[LOAD] Loading d5z_b baseline: {baseline_path}")
    img = Image.open(baseline_path).convert("RGB")
    bw, bh = img.size
    if (bw, bh) != (w, h):
        img = img.resize((w, h), Image.LANCZOS)
    arr = np.array(img, dtype=np.uint8)
    log.append(f"[LOAD] Baseline loaded: {arr.shape}")
    return arr


# ══════════════════════════════════════════════════════════════════════════════
# Module: apply_global_base_adjustment (spec §4.1)
# ══════════════════════════════════════════════════════════════════════════════

def apply_global_base_adjustment(f32: np.ndarray, log: list) -> np.ndarray:
    out = f32.copy()
    p = GLOBAL_BASE
    log.append("[MODULE 1] global_base_adjustment...")

    # Brightness: multiplicative
    out = out * (1.0 + p["brightness"])

    # Contrast: scale around midpoint 127.5
    midpoint = 127.5
    contrast_scale = 1.0 + p["contrast"]
    out = (out - midpoint) * contrast_scale + midpoint

    # Blue channel boost
    out[:, :, 2] = out[:, :, 2] * (1.0 + p["blue_channel"])

    # Global saturation reduction via HSL
    H, S, L = rgb_to_hsl_array(np.clip(out, 0, 255))
    S_new = np.clip(S + p["saturation"], 0.0, 1.0)
    # Green hue range desaturation (~80–160 degrees)
    green_gate = (H >= 80) & (H <= 160)
    S_new = np.where(green_gate, np.clip(S_new + p["green_sat"], 0.0, 1.0), S_new)
    # Yellow hue range desaturation (~40–80 degrees)
    yellow_gate = (H >= 40) & (H < 80)
    S_new = np.where(yellow_gate, np.clip(S_new + p["yellow_sat"], 0.0, 1.0), S_new)
    out = hsl_to_rgb_array(H, S_new, L)

    out = np.clip(out, 0, 255)
    log.append("[MODULE 1] global_base_adjustment — done")
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Module: apply_ocean_system (spec §5.1–5.2)
# ══════════════════════════════════════════════════════════════════════════════

def apply_ocean_system(f32: np.ndarray, LAT: np.ndarray, LON: np.ndarray,
                       log: list) -> np.ndarray:
    out = f32.copy()
    W = f32.shape[1]
    log.append("[MODULE 2] ocean_system...")

    regions_sorted = sorted(NOON_AIR_OCEAN_REGIONS, key=lambda r: r["priority"])
    for r in regions_sorted:
        fpx = scale_feather(r["feather_px_8k"], W)
        rmask = region_mask_rect(LAT, LON,
                                 lat_min=r["lat_s"], lat_max=r["lat_n"],
                                 lon_min=r["lon_w"], lon_max=r["lon_e"],
                                 feather_px=fpx,
                                 cross_antimeridian=r.get("cross_am", False))
        if r.get("deep_only"):
            pixel_gate = deep_ocean_px(out)
        elif r.get("ocean_only"):
            pixel_gate = ocean_px(out)
        else:
            pixel_gate = np.ones(f32.shape[:2], dtype=np.float32)

        combined = rmask * pixel_gate
        if combined.sum() < 10:
            continue

        out = apply_hsl_delta(out, combined,
                              hue_shift=r["hue_shift"],
                              sat_delta=r["sat_delta"],
                              lit_delta=r["lit_delta"])

    log.append(f"[MODULE 2] ocean_system — {len(NOON_AIR_OCEAN_REGIONS)} regions processed")
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Module: apply_shallow_water_shelf (spec §5.2)
# ══════════════════════════════════════════════════════════════════════════════

def apply_shallow_water_shelf(f32: np.ndarray, LAT: np.ndarray, LON: np.ndarray,
                               log: list) -> np.ndarray:
    """
    Brightness-as-depth proxy: lighter ocean pixels = shallower.
    Applies a gentle brightening gradient on continental shelf zones.
    """
    out = f32.copy()
    W = f32.shape[1]
    log.append("[MODULE 3] shallow_water_shelf...")

    ocean = ocean_px(out)
    lum = luminance(out) / 255.0

    # Shallow proxy: ocean pixels with luminance above shelf threshold
    shelf_threshold = 0.18
    shallow_proxy = ocean * np.clip((lum - shelf_threshold) / 0.25, 0.0, 1.0)

    # Shelf brightening pass
    shelf_gain = shallow_proxy[:, :, np.newaxis] * 0.06
    out = np.clip(out * (1.0 + shelf_gain), 0, 255)

    # Additional hue shift toward cyan in shallow zones
    out = apply_hsl_delta(out, shallow_proxy * 0.6,
                          hue_shift=+3, sat_delta=+0.04, lit_delta=0.0)

    log.append("[MODULE 3] shallow_water_shelf — done")
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Module: apply_island_halos (spec §6)
# ══════════════════════════════════════════════════════════════════════════════

def apply_island_halos(f32: np.ndarray, LAT: np.ndarray, LON: np.ndarray,
                       log: list) -> np.ndarray:
    out = f32.copy()
    W = f32.shape[1]
    log.append("[MODULE 4] island_halos...")

    deep_mask = deep_ocean_px(out)

    for halo in NOON_AIR_ISLAND_HALOS:
        clon, clat = halo["center"]
        radius_px = km_to_pixels(halo["halo_km"], W)
        fpx = scale_feather(halo["feather_px_8k"], W)

        cmask = circle_mask(LAT, LON, clon, clat, radius_px, fpx, W)

        # deep_gate: do not enhance pixels already classified as deep ocean
        if halo.get("deep_gate", True):
            cmask = cmask * (1.0 - deep_mask)

        if cmask.sum() < 1:
            continue

        # Tropical: warm cyan hue shift; high-lat: cold blue-grey hue shift
        if halo["tropical"]:
            hue_shift = halo["hue_shift"]   # pushes toward cyan-blue
        else:
            hue_shift = halo["hue_shift"]   # pushes toward cold blue-grey

        # Apply only to ocean pixels within halo
        ocean = ocean_px(out)
        effective = cmask * ocean

        out = apply_hsl_delta(out, effective * halo["blend"],
                              hue_shift=hue_shift,
                              sat_delta=halo["sat_delta"],
                              lit_delta=halo["lit_delta"])

    log.append(f"[MODULE 4] island_halos — {len(NOON_AIR_ISLAND_HALOS)} halos processed")
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Module: apply_polar_correction (spec §7)
# ══════════════════════════════════════════════════════════════════════════════

def apply_polar_correction(f32: np.ndarray, LAT: np.ndarray, log: list) -> np.ndarray:
    out = f32.copy()
    W = f32.shape[1]
    log.append("[MODULE 5] polar_correction...")

    ice = ice_px(out)

    # Antarctica: compress brightness of ice pixels below -65°
    for outer, inner, scale in [(-70, -65, 0.87), (70, 65, 0.90)]:
        if outer < 0:
            strength = np.clip((inner - LAT) / abs(inner - outer), 0.0, 1.0)
        else:
            strength = np.clip((LAT - inner) / abs(outer - inner), 0.0, 1.0)
        blend = (ice * strength)[:, :, np.newaxis]
        out = out * (1.0 - blend * (1.0 - scale))

    # Antarctica: push ice toward blue-white tone (#DDECF2)
    ant_mask = (LAT <= -60).astype(np.float32)
    ant_mask = feather_mask(ant_mask, scale_feather(30, W))
    ice_ant = ice * ant_mask

    # Shift Antarctica ice toward blue-white (#DDECF2 ≈ H=200, S=0.35, L=0.89)
    out = apply_hsl_delta(out, ice_ant * 0.4,
                          hue_shift=+8, sat_delta=-0.05, lit_delta=0.0)

    # Greenland: lighter touch
    gl_mask = (LAT >= 60).astype(np.float32)
    gl_mask = feather_mask(gl_mask, scale_feather(20, W))
    ice_gl = ice * gl_mask
    out = apply_hsl_delta(out, ice_gl * 0.3,
                          hue_shift=+5, sat_delta=-0.03, lit_delta=0.0)

    out = np.clip(out, 0, 255)
    log.append("[MODULE 5] polar_correction — Antarctica + Greenland done")
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Module: apply_desert_correction (spec §9)
# ══════════════════════════════════════════════════════════════════════════════

def apply_desert_correction(f32: np.ndarray, LAT: np.ndarray, LON: np.ndarray,
                             log: list) -> np.ndarray:
    out = f32.copy()
    W = f32.shape[1]
    log.append("[MODULE 6] desert_correction...")

    land = land_px(out)
    lum  = luminance(out)

    # Sahara / Egypt: darken overly bright desert pixels
    sahara_rm = region_mask_rect(LAT, LON, 15, 35, -15, 45,
                                 feather_px=scale_feather(16, W))
    sahara_land = land * sahara_rm
    # Pixels above brightness threshold get pulled down proportionally
    bright_mask = np.clip((lum - 180) / 75.0, 0.0, 1.0)
    apply_mask = sahara_land * bright_mask
    out = out * (1.0 - apply_mask[:, :, np.newaxis] * 0.06) + \
          out * 0.94 * apply_mask[:, :, np.newaxis]
    out = np.clip(out, 0, 255)

    # Arabia
    arabia_rm = region_mask_rect(LAT, LON, 10, 32, 35, 65,
                                 feather_px=scale_feather(14, W))
    arabia_land = land * arabia_rm
    bright_mask2 = np.clip((lum - 185) / 70.0, 0.0, 1.0)
    apply_mask2 = arabia_land * bright_mask2
    out = out * (1.0 - apply_mask2[:, :, np.newaxis] * 0.05) + \
          out * 0.95 * apply_mask2[:, :, np.newaxis]
    out = np.clip(out, 0, 255)

    # Central Asia / Tibetan Plateau: suppress over-yellowing
    plateau_rm = region_mask_rect(LAT, LON, 28, 42, 68, 105,
                                  feather_px=scale_feather(20, W))
    plateau_land = land * plateau_rm
    out = apply_hsl_delta(out, plateau_land * 0.5,
                          hue_shift=-5, sat_delta=-0.06, lit_delta=0.0,
                          hue_range=(30, 80))

    # Australia outback: slight reddening
    aus_rm = region_mask_rect(LAT, LON, -35, -16, 115, 140,
                               feather_px=scale_feather(20, W))
    aus_land = land * aus_rm
    out = apply_hsl_delta(out, aus_land * 0.3,
                          hue_shift=-8, sat_delta=+0.03, lit_delta=0.0,
                          hue_range=(20, 60))

    log.append("[MODULE 6] desert_correction — Sahara/Arabia/Plateau/Australia done")
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Module: apply_land_vegetation (spec §8)
# ══════════════════════════════════════════════════════════════════════════════

def apply_land_vegetation(f32: np.ndarray, LAT: np.ndarray, LON: np.ndarray,
                           log: list) -> np.ndarray:
    out = f32.copy()
    W = f32.shape[1]
    log.append("[MODULE 7] land_vegetation...")

    land = land_px(out)

    # Global green desaturation pass on land
    out = apply_hsl_delta(out, land * 0.6,
                          hue_shift=0, sat_delta=-0.08, lit_delta=0.0,
                          hue_range=(80, 160))

    # Tropical rainforest: push toward deep olive-green
    amazon_rm = region_mask_rect(LAT, LON, -15, 5, -75, -45,
                                  feather_px=scale_feather(20, W))
    congo_rm  = region_mask_rect(LAT, LON, -5,  8, 12, 32,
                                  feather_px=scale_feather(16, W))
    sea_rm    = region_mask_rect(LAT, LON, -10, 12, 95, 145,
                                  feather_px=scale_feather(20, W))

    for rm in [amazon_rm, congo_rm, sea_rm]:
        rf_land = land * rm
        out = apply_hsl_delta(out, rf_land * 0.5,
                              hue_shift=+5, sat_delta=-0.08, lit_delta=-0.04,
                              hue_range=(80, 145))

    log.append("[MODULE 7] land_vegetation — done")
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Module: apply_mountains_plateaus (spec §10)
# ══════════════════════════════════════════════════════════════════════════════

def apply_mountains_plateaus(f32: np.ndarray, LAT: np.ndarray, LON: np.ndarray,
                              log: list) -> np.ndarray:
    out = f32.copy()
    W = f32.shape[1]
    log.append("[MODULE 8] mountains_plateaus...")

    land = land_px(out)

    # Himalayas: ensure cool-toned; suppress over-warming
    himalaya_rm = region_mask_rect(LAT, LON, 27, 36, 72, 102,
                                    feather_px=scale_feather(12, W))
    out = apply_hsl_delta(out, land * himalaya_rm * 0.4,
                          hue_shift=-3, sat_delta=-0.03, lit_delta=0.0)

    # Alps / Rockies / Andes: preserve relief, don't over-process
    alps_rm    = region_mask_rect(LAT, LON, 44, 48, 5, 16,
                                   feather_px=scale_feather(8, W))
    rockies_rm = region_mask_rect(LAT, LON, 36, 55, -122, -104,
                                   feather_px=scale_feather(12, W))
    andes_rm   = region_mask_rect(LAT, LON, -55, 10, -82, -64,
                                   feather_px=scale_feather(12, W))

    for rm in [alps_rm, rockies_rm, andes_rm]:
        out = apply_hsl_delta(out, land * rm * 0.2,
                              hue_shift=0, sat_delta=-0.02, lit_delta=0.0)

    log.append("[MODULE 8] mountains_plateaus — done")
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Module: apply_special_seas (spec §11)
# ══════════════════════════════════════════════════════════════════════════════

def apply_special_seas(f32: np.ndarray, LAT: np.ndarray, LON: np.ndarray,
                       log: list) -> np.ndarray:
    out = f32.copy()
    W = f32.shape[1]
    log.append("[MODULE 9] special_seas...")

    ocean = ocean_px(out)

    for sea in NOON_AIR_SPECIAL_SEAS:
        fpx = scale_feather(sea["feather_px_8k"], W)
        rmask = region_mask_rect(LAT, LON,
                                 lat_min=_sea_lat_s(sea["name"]),
                                 lat_max=_sea_lat_n(sea["name"]),
                                 lon_min=sea["lon_w"],
                                 lon_max=sea["lon_e"],
                                 feather_px=fpx)
        combined = rmask * ocean
        if combined.sum() < 10:
            continue
        out = apply_hsl_delta(out, combined,
                              hue_shift=sea["hue_shift"],
                              sat_delta=sea["sat_delta"],
                              lit_delta=sea["lit_delta"])

    log.append(f"[MODULE 9] special_seas — {len(NOON_AIR_SPECIAL_SEAS)} seas processed")
    return out


def _sea_lat_s(name: str) -> float:
    return {"mediterranean": 30.0, "red_sea": 12.0, "caribbean_deep": 10.0}.get(name, -90.0)


def _sea_lat_n(name: str) -> float:
    return {"mediterranean": 48.0, "red_sea": 30.0, "caribbean_deep": 28.0}.get(name, 90.0)


# ══════════════════════════════════════════════════════════════════════════════
# Module: apply_final_harmony_guard (spec §5.14)
# ══════════════════════════════════════════════════════════════════════════════

def apply_final_harmony_guard(f32: np.ndarray, baseline_f32: np.ndarray,
                               LAT: np.ndarray, LON: np.ndarray,
                               log: list) -> np.ndarray:
    """
    Blend back toward baseline in protected regions where drift exceeds threshold.
    Threshold: mean_rgb_delta > 8 or luminance_delta > 0.04 * 255.
    """
    out = f32.copy()
    log.append("[MODULE 10] final_harmony_guard...")
    activated_any = False

    for name, bounds in PROTECTED_REGIONS.items():
        rm = region_mask_rect(LAT, LON,
                              lat_min=bounds["lat_min"], lat_max=bounds["lat_max"],
                              lon_min=bounds["lon_min"], lon_max=bounds["lon_max"],
                              feather_px=0)
        npx = int(rm.sum())
        if npx < 100:
            continue

        rgb_delta = float((np.abs(out - baseline_f32).mean(axis=2) * rm).sum() / npx)
        lum_delta = float((np.abs(luminance(out) - luminance(baseline_f32)) * rm).sum() / npx) / 255.0

        if rgb_delta > GUARD_THRESHOLDS["mean_rgb_delta"] or \
           lum_delta > GUARD_THRESHOLDS["luminance_delta"]:
            excess = max(rgb_delta / GUARD_THRESHOLDS["mean_rgb_delta"],
                         lum_delta / GUARD_THRESHOLDS["luminance_delta"])
            blend_back = min((excess - 1.0) * 0.4, 0.7)
            rm3 = rm[:, :, np.newaxis]
            blended = out * (1.0 - blend_back) + baseline_f32 * blend_back
            out = out * (1.0 - rm3) + blended * rm3
            log.append(f"[GUARD] {name}: rgb_delta={rgb_delta:.2f} lum_delta={lum_delta:.4f} "
                       f"— blend_back={blend_back:.2f} ACTIVATED")
            activated_any = True
        else:
            log.append(f"[GUARD] {name}: rgb_delta={rgb_delta:.2f} lum_delta={lum_delta:.4f} — OK")

    if not activated_any:
        log.append("[MODULE 10] final_harmony_guard — no regions triggered")

    return np.clip(out, 0, 255)


# ══════════════════════════════════════════════════════════════════════════════
# Module: run_baseline_floor_guard (spec §5.14, Q3)
# ══════════════════════════════════════════════════════════════════════════════

def run_baseline_floor_guard(f32: np.ndarray, baseline_f32: np.ndarray,
                              LAT: np.ndarray, LON: np.ndarray,
                              log: list) -> dict:
    log.append("[GUARD] Running baseline floor guard (d5z_b comparison)...")
    guard_result = {"pass": True, "warnings": [], "regions": {}}

    for name, bounds in PROTECTED_REGIONS.items():
        rm = region_mask_rect(LAT, LON,
                              lat_min=bounds["lat_min"], lat_max=bounds["lat_max"],
                              lon_min=bounds["lon_min"], lon_max=bounds["lon_max"],
                              feather_px=0)
        npx = int(rm.sum())
        if npx < 100:
            guard_result["regions"][name] = {"error": "no pixels"}
            continue

        mean_rgb_delta = float(
            (np.abs(f32 - baseline_f32).mean(axis=2) * rm).sum() / npx)
        mean_lum_delta = float(
            (np.abs(luminance(f32) - luminance(baseline_f32)) * rm).sum() / npx) / 255.0

        passed = (mean_rgb_delta <= GUARD_THRESHOLDS["mean_rgb_delta"] and
                  mean_lum_delta <= GUARD_THRESHOLDS["luminance_delta"])

        guard_result["regions"][name] = {
            "mean_rgb_delta":  round(mean_rgb_delta, 3),
            "luminance_delta": round(mean_lum_delta, 4),
            "guard_pass":      passed,
        }

        status = "PASS" if passed else "FAIL"
        log.append(f"[GUARD]   {name}: rgb_delta={mean_rgb_delta:.2f}  "
                   f"lum_delta={mean_lum_delta:.4f}  {status}")

        if not passed:
            msg = (f"{name}: rgb_delta={mean_rgb_delta:.2f} "
                   f"(limit={GUARD_THRESHOLDS['mean_rgb_delta']}), "
                   f"lum_delta={mean_lum_delta:.4f} "
                   f"(limit={GUARD_THRESHOLDS['luminance_delta']})")
            guard_result["warnings"].append(msg)

    guard_result["pass"] = len(guard_result["warnings"]) == 0
    overall = "PASS" if guard_result["pass"] else f"FAIL ({len(guard_result['warnings'])} regions exceeded threshold)"
    log.append(f"[GUARD] Overall: {overall}")
    return guard_result


# ══════════════════════════════════════════════════════════════════════════════
# Module: generate_preview_crops (spec §5.15)
# ══════════════════════════════════════════════════════════════════════════════

def extract_crop(arr: np.ndarray, lon: float, lat: float, w: int, h: int) -> np.ndarray:
    H, W = arr.shape[:2]
    cx = int((lon + 180) / 360 * W)
    cy = int((90 - lat) / 180 * H)
    x0, x1 = cx - w // 2, cx + w // 2
    y0, y1 = cy - h // 2, cy + h // 2
    pad_l = max(0, -x0)
    pad_r = max(0, x1 - W)
    pad_t = max(0, -y0)
    pad_b = max(0, y1 - H)
    crop = arr[max(0, y0):min(H, y1), max(0, x0):min(W, x1)]
    if pad_l or pad_r or pad_t or pad_b:
        crop = np.pad(crop, ((pad_t, pad_b), (pad_l, pad_r), (0, 0)), mode="edge")
    return crop


def generate_preview_crops(noon_arr: np.ndarray, baseline_arr: np.ndarray,
                            crops_dir: Path, res_tag: str, log: list):
    log.append("[OUTPUT] Generating benchmark compare crops...")
    crops_dir.mkdir(parents=True, exist_ok=True)
    label_h = 26

    for region_name, spec in BENCHMARK_CROPS.items():
        lon, lat = spec["lon"], spec["lat"]
        # Scale crop dimensions to working resolution
        W = noon_arr.shape[1]
        scale = W / 8192
        cw = max(64, int(spec["w"] * scale))
        ch = max(32, int(spec["h"] * scale))

        crop_noon = extract_crop(noon_arr, lon, lat, cw, ch)
        crop_base = extract_crop(baseline_arr, lon, lat, cw, ch)

        gap = 2
        total_w = cw * 2 + gap
        total_h = ch + label_h
        canvas = Image.new("RGB", (total_w, total_h), (20, 20, 20))
        draw = ImageDraw.Draw(canvas)

        canvas.paste(Image.fromarray(crop_base), (0, label_h))
        canvas.paste(Image.fromarray(crop_noon), (cw + gap, label_h))
        draw.rectangle([0, 0, cw - 1, label_h - 2], fill=(40, 40, 40))
        draw.rectangle([cw + gap, 0, total_w - 1, label_h - 2], fill=(40, 40, 40))
        draw.text((4,         5), f"[{region_name}] d5z_b baseline", fill=(180, 180, 180))
        draw.text((cw + gap + 4, 5), f"[{region_name}] noon_air_v1",    fill=(120, 200, 150))

        out_path = crops_dir / f"{region_name}_d5zb_vs_noon_air_v1.jpg"
        canvas.save(out_path, "JPEG", quality=90)

    # Global preview
    global_w = min(1024, noon_arr.shape[1])
    global_h = global_w // 2
    global_img = Image.fromarray(noon_arr).resize((global_w, global_h), Image.LANCZOS)
    global_img.save(crops_dir.parent / f"noon_air_v1_{res_tag}_preview_global.jpg",
                    "JPEG", quality=88)

    # Diff heatmap
    diff = np.abs(noon_arr.astype(np.float32) - baseline_arr.astype(np.float32))
    diff_lum = diff.mean(axis=2)
    diff_norm = (diff_lum / (diff_lum.max() + 1e-6) * 255).astype(np.uint8)
    # False-color: blue=small diff, red=large diff
    diff_rgb = np.stack([
        diff_norm,
        np.zeros_like(diff_norm),
        (255 - diff_norm),
    ], axis=2)
    diff_img = Image.fromarray(diff_rgb)
    if diff_img.size[0] > 1024:
        diff_img = diff_img.resize((1024, 512), Image.LANCZOS)
    diff_img.save(crops_dir.parent / f"noon_air_v1_{res_tag}_diff_vs_d5zb.jpg",
                  "JPEG", quality=85)

    log.append(f"[OUTPUT] {len(BENCHMARK_CROPS)} compare crops saved to {crops_dir}")
    log.append(f"[OUTPUT] Global preview and diff heatmap saved.")


# ══════════════════════════════════════════════════════════════════════════════
# Module: write_summary_report (spec §5.16)
# ══════════════════════════════════════════════════════════════════════════════

def write_summary_report(noon_f32: np.ndarray, baseline_f32: np.ndarray,
                          LAT: np.ndarray, LON: np.ndarray,
                          guard_result: dict, res_tag: str,
                          out_dir: Path, log: list):
    log.append("[OUTPUT] Computing metrics...")

    noon_lum  = float(luminance(noon_f32).mean())
    base_lum  = float(luminance(baseline_f32).mean())
    noon_mean = [float(noon_f32[:, :, c].mean()) for c in range(3)]
    base_mean = [float(baseline_f32[:, :, c].mean()) for c in range(3)]
    lum_delta = (noon_lum - base_lum) / 255.0

    benchmark_stats = {}
    for name, spec in BENCHMARK_CROPS.items():
        lon, lat = spec["lon"], spec["lat"]
        W = noon_f32.shape[1]
        cw = max(64, int(spec["w"] * W / 8192))
        ch = max(32, int(spec["h"] * W / 8192))
        crop = extract_crop(noon_f32, lon, lat, cw, ch)
        benchmark_stats[name] = {
            "mean_rgb": [round(float(crop[:, :, c].mean()), 1) for c in range(3)],
            "luminance": round(float(luminance(crop).mean()) / 255.0, 4),
        }

    metrics = {
        "version":    "noon_air_v1",
        "resolution": res_tag,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "source":     str(SOURCE_PATH.name),
        "baseline":   "d5z_b_8192x4096.jpg",
        "global": {
            "mean_rgb_noon":        [round(v, 1) for v in noon_mean],
            "mean_rgb_baseline":    [round(v, 1) for v in base_mean],
            "mean_rgb_delta":       [round(noon_mean[c] - base_mean[c], 2) for c in range(3)],
            "mean_luminance_noon":  round(noon_lum / 255.0, 4),
            "mean_luminance_base":  round(base_lum / 255.0, 4),
            "luminance_delta":      round(lum_delta, 4),
        },
        "protected_regions":  guard_result["regions"],
        "benchmark_regions":  benchmark_stats,
        "guard_result": {
            "pass":     guard_result["pass"],
            "warnings": guard_result["warnings"],
        },
    }

    metrics_path = out_dir / f"noon_air_v1_{res_tag}_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))
    log.append(f"[OUTPUT] Metrics saved: {metrics_path.name}")
    return metrics


# ══════════════════════════════════════════════════════════════════════════════
# Atmosphere overlay — must be last processing step (spec §4.2)
# ══════════════════════════════════════════════════════════════════════════════

def apply_atmosphere_overlay(f32: np.ndarray, log: list) -> np.ndarray:
    out = f32 / 255.0
    opacity = min(ATMOSPHERE["opacity"], 0.10)
    ar, ag, ab = [c / 255.0 for c in ATMOSPHERE["color_rgb"]]
    blend_r = np.full(out.shape[:2], ar, dtype=np.float32)
    blend_g = np.full(out.shape[:2], ag, dtype=np.float32)
    blend_b = np.full(out.shape[:2], ab, dtype=np.float32)

    def soft_light(base, blend):
        return base + opacity * (2 * blend - 1) * (base - base ** 2)

    out[:, :, 0] = soft_light(out[:, :, 0], blend_r)
    out[:, :, 1] = soft_light(out[:, :, 1], blend_g)
    out[:, :, 2] = soft_light(out[:, :, 2], blend_b)

    log.append(f"[MODULE 11] atmosphere_overlay — opacity={opacity*100:.1f}% done")
    return np.clip(out * 255.0, 0, 255)


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description="D6 Noon Air Earth Generator — 2K dry-run by default")
    p.add_argument("--input",      type=str, default=str(SOURCE_PATH),
                   help="Path to source JPG (default: 21.6K source)")
    p.add_argument("--output-dir", type=str, default=str(OUT_DIR),
                   help="Output directory (must not be production/ or candidates/)")
    p.add_argument("--baseline",   type=str, default=str(BASELINE_PATH),
                   help="Path to d5z_b baseline JPG for floor guard")
    p.add_argument("--full-res",   action="store_true",
                   help="Generate 8K output in addition to 2K dry-run (requires explicit flag)")
    p.add_argument("--preview-only", action="store_true",
                   help="Generate crops and metrics without saving full candidate JPG")
    p.add_argument("--dry-run",    action="store_true",
                   help="Validate assets and report paths without any processing")
    return p.parse_args()


def main():
    args = parse_args()

    out_dir      = Path(args.output_dir)
    baseline_pth = Path(args.baseline)

    log = []
    ts  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    log.append("=== Noon Air Earth Generator v1 ===")
    log.append(f"Timestamp: {ts}")

    resolutions = [RES_2K]
    if args.full_res:
        resolutions.append(RES_8K)
        log.append("Mode: 2K + 8K (--full-res)")
    else:
        log.append("Mode: DRY-RUN 2K (2048×1024 only)")

    # Asset validation (aborts if baseline missing)
    validate_assets(baseline_pth, log)
    ensure_safe_output_path(out_dir, log)

    if args.dry_run:
        log.append("[DRY-RUN] --dry-run flag set. Aborting before any processing.")
        out_dir.mkdir(parents=True, exist_ok=True)
        _flush_log(log, out_dir / "noon_air_v1_dry_run_log.txt")
        print("\n".join(log))
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "compare_crops").mkdir(parents=True, exist_ok=True)

    for res in resolutions:
        w, h   = res
        res_tag = f"{w}x{h}"
        log.append(f"\n--- Resolution: {res_tag} ---")

        # Load
        source_arr   = load_source(res, log)
        baseline_arr = load_baseline_d5zb(res, baseline_pth, log)
        validate_resolution(source_arr,   res, log)
        validate_resolution(baseline_arr, res, log)

        # Build grids
        LAT, LON = build_grids(h, w)
        f32 = source_arr.astype(np.float32)

        # Processing pipeline
        f32 = apply_global_base_adjustment(f32, log)
        f32 = apply_ocean_system(f32, LAT, LON, log)
        f32 = apply_shallow_water_shelf(f32, LAT, LON, log)
        f32 = apply_island_halos(f32, LAT, LON, log)
        f32 = apply_polar_correction(f32, LAT, log)
        f32 = apply_desert_correction(f32, LAT, LON, log)
        f32 = apply_land_vegetation(f32, LAT, LON, log)
        f32 = apply_mountains_plateaus(f32, LAT, LON, log)
        f32 = apply_special_seas(f32, LAT, LON, log)
        f32 = apply_final_harmony_guard(f32, baseline_arr.astype(np.float32),
                                        LAT, LON, log)
        f32 = apply_atmosphere_overlay(f32, log)

        noon_arr   = np.clip(f32, 0, 255).astype(np.uint8)
        base_f32   = baseline_arr.astype(np.float32)

        # Baseline floor guard — must pass before any output is saved
        guard_result = run_baseline_floor_guard(f32, base_f32, LAT, LON, log)
        if not guard_result["pass"]:
            warn_lines = "\n".join(f"  - {w}" for w in guard_result["warnings"])
            _flush_log(log, out_dir / f"noon_air_v1_{res_tag}_GUARD_FAIL_log.txt")
            sys.exit(
                f"[GUARD] ABORT: Baseline floor guard FAILED for {res_tag}. "
                f"Output NOT saved.\n"
                f"Failing regions:\n{warn_lines}\n"
                f"Review the guard log and adjust color parameters before retrying."
            )

        # Preview crops and metrics
        crops_dir = out_dir / "compare_crops"
        generate_preview_crops(noon_arr, baseline_arr, crops_dir, res_tag, log)
        write_summary_report(f32, base_f32, LAT, LON, guard_result,
                             res_tag, out_dir, log)

        # Save candidate JPG
        if not args.preview_only:
            candidate_path = out_dir / f"noon_air_v1_{res_tag}.jpg"
            Image.fromarray(noon_arr).save(candidate_path, "JPEG", quality=92, subsampling=0)
            size_kb = candidate_path.stat().st_size // 1024
            log.append(f"[OUTPUT] Saved: {candidate_path.name} ({size_kb}KB)")

    log.append("\n=== COMPLETE ===")
    log.append(f"Output: {out_dir}")
    log.append("Confirm: earth3d.js NOT modified.")
    log.append("Confirm: DAY_TEXTURE_VARIANT NOT modified.")
    log.append("Confirm: production/ NOT written.")
    log.append("Confirm: No git operations performed.")

    _flush_log(log, out_dir / f"noon_air_v1_log.txt")
    print("\n".join(log))


def _flush_log(log: list, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(log) + "\n")


if __name__ == "__main__":
    main()
