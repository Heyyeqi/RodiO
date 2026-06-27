#!/usr/bin/env python3.11
"""
global_v2_pipeline.py — Global Noon Air Baseline v1 Tile Pipeline

Standard (locked 2026-06-25):
  Source:       BMNG 21K GeoTIFF (topo_bathy 200408, August)
  GEBCO:        global uniform blend=0.35, 8-tile GeoTIFF set (2026 sub_ice)
  GSHHG:        L1 full-res (GSHHS_f_L1.shp), per-LOD zone/strength
  LOD policy:   independent per LOD (geometric params scale with resolution)
  Color params: uniform across LODs (tone curves unchanged)
  Seam policy:  10km overlap expand → process → crop to tile bounds
  Output:       tiles_v2_enhanced/ (JPEG q=92)

LOD params:
  16k: grid 4×2, tile 4096×4096, zone=10km, gshhg_strength=0.15
  8k:  grid 2×1, tile 4096×4096, zone=6km,  gshhg_strength=0.12
  4k:  grid 2×1, tile 2048×2048, zone=3km,  gshhg_strength=0.10

Usage:
  python3 global_v2_pipeline.py                           # all LODs, all tiles
  python3 global_v2_pipeline.py --lod 16k                 # single LOD
  python3 global_v2_pipeline.py --lod 16k --tile 2 0      # single tile
  python3 global_v2_pipeline.py --dry-run                 # print plan, no output
  python3 global_v2_pipeline.py --noon-air                # also apply Stage 14+15 → tiles_noon_air_v2/
  python3 global_v2_pipeline.py --noon-air --lod 16k --tile 3 0  # single tile, both outputs
"""

from __future__ import annotations

import sys

# ── Dependency guard ─────────────────────────────────────────────────────────
# This script requires python3.11 with pyshp/scipy/tifffile/Pillow installed.
# If you see ModuleNotFoundError here, run:
#   python3.11 -m pip install -r scripts/geo/requirements.txt --break-system-packages
# Then invoke as:
#   python3.11 scripts/geo/global_v2_pipeline.py   (NOT plain python3)
if sys.version_info < (3, 11):
    sys.exit(
        f"ERROR: python3.11+ required (got {sys.version.split()[0]})\n"
        "Run with: python3.11 scripts/geo/global_v2_pipeline.py"
    )
try:
    import shapefile as _shapefile_check  # noqa: F401
    import tifffile as _tifffile_check    # noqa: F401
    import scipy                           # noqa: F401
except ModuleNotFoundError as e:
    sys.exit(
        f"ERROR: missing dependency — {e}\n"
        "Install with:\n"
        "  python3.11 -m pip install -r scripts/geo/requirements.txt --break-system-packages\n"
        "Then run with python3.11, not python3."
    )

import argparse
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import shapefile
import tifffile
from scipy.ndimage import distance_transform_edt

Image.MAX_IMAGE_PIXELS = None  # BMNG 21K exceeds PIL default limit

# ── Paths ────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent.parent
BMNG_TIF = ROOT / "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/21600x10800_geotiff/world.topo.bathy.200408.3x21600x10800_geo.tif"
GEBCO_DIR = ROOT / "d5b_processor_v3/source_cache/gee_global/external_raw/gebco/gebco_2026_sub_ice_topo_geotiff"
GSHHG_L1  = ROOT / "pwa/assets/source/coastline/gshhg/GSHHS_shp/f/GSHHS_f_L1.shp"
OUT_BASE               = ROOT / "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_v2_enhanced"
NOON_AIR_OUT_BASE      = ROOT / "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_noon_air_v2"
ISLAND_V2_OUT_BASE     = ROOT / "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_v2_enhanced_islands"
ISLAND_NA_OUT_BASE     = ROOT / "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_noon_air_v2_islands"

# ── Small-island visibility pass constants ────────────────────────────────────
# Targets: L1 polygons with area < threshold → oceanic island groups
# (continents, Greenland, Borneo etc. are excluded by the area ceiling)
ISLAND_AREA_MAX_KM2  = 5000.0  # km²: include up to ~Okinawa/Réunion scale
ISLAND_GLOW_PX       = 5.0     # pixel radius for outer glow (16k ≈ 12km)
ISLAND_GLOW_STRENGTH = 0.10    # max blend strength — very subtle
# Pale shallow-water turquoise (lighter than DEPTH_PALETTE nearshore entry)
ISLAND_GLOW_COLOR    = np.array([130, 185, 208], dtype=np.float32)
# LOD strength scaling: finer tiles keep full strength; coarser dial back slightly
_ISLAND_LOD_SCALE    = {"16k": 1.0, "8k": 0.85, "4k": 0.70}

# ── LOD configuration ────────────────────────────────────────────────────────

LOD_CONFIGS = {
    "16k": dict(grid_x=4, grid_y=2, tile_w=4096, tile_h=4096, zone_km=10.0, gshhg_strength=0.15, gebco_blend=0.35, jpeg_q=92),
    "8k":  dict(grid_x=2, grid_y=1, tile_w=4096, tile_h=4096, zone_km=6.0,  gshhg_strength=0.12, gebco_blend=0.35, jpeg_q=92),
    "4k":  dict(grid_x=2, grid_y=1, tile_w=2048, tile_h=2048, zone_km=3.0,  gshhg_strength=0.10, gebco_blend=0.35, jpeg_q=92),
}

# GEBCO depth → RGB tint (ocean only; land pixels skipped)
DEPTH_PALETTE = [
    (    0,  (180, 160, 120)),  # ≥0m: land (not applied)
    (  -50,  ( 32,  95, 148)),  # 0 to -50m: nearshore / reef
    ( -200,  ( 20,  68, 124)),  # -50 to -200m: continental shelf
    (-1500,  ( 12,  46,  98)),  # -200 to -1500m: slope
    (-4000,  (  6,  29,  72)),  # -1500 to -4000m: abyssal plain
    (-99999, (  2,  13,  46)),  # < -4000m: deep trench / basin
]

# GSHHG shapefile overlap margin when loading polygons (degrees)
# ensures polygons that straddle a tile boundary are included
POLY_MARGIN_DEG = 2.0

# Seam overlap: expand tile bounds before GSHHG distance transform, then crop
SEAM_OVERLAP_KM = 10.0

# ── Geometry helpers ─────────────────────────────────────────────────────────

def tile_bounds(x: int, y: int, cfg: dict) -> Tuple[float, float, float, float]:
    """Return (lon_w, lon_e, lat_s, lat_n) for tile (x, y) in this LOD config."""
    lon_span = 360.0 / cfg["grid_x"]
    lat_span = 180.0 / cfg["grid_y"]
    lon_w = -180.0 + x * lon_span
    lon_e = lon_w + lon_span
    # y=0 is top (north), y increases southward
    lat_n = 90.0 - y * lat_span
    lat_s = lat_n - lat_span
    return lon_w, lon_e, lat_s, lat_n


def expand_bounds(lon_w, lon_e, lat_s, lat_n, km: float) -> Tuple[float, float, float, float]:
    """Expand geographic bounds by km on all sides."""
    lat_mid = (lat_s + lat_n) / 2.0
    deg_lat = km / 111.0
    deg_lon = km / max(111.0 * math.cos(math.radians(abs(lat_mid))), 0.5)
    return (
        max(-180.0, lon_w - deg_lon),
        min( 180.0, lon_e + deg_lon),
        max( -90.0, lat_s - deg_lat),
        min(  90.0, lat_n + deg_lat),
    )


def geo_to_px(lon: float, lat: float,
              lon_w: float, lon_e: float, lat_s: float, lat_n: float,
              w: int, h: int) -> Tuple[float, float]:
    """Convert (lon, lat) to image pixel (x, y). y=0 is north."""
    px = (lon - lon_w) / (lon_e - lon_w) * w
    py = (lat_n - lat) / (lat_n - lat_s) * h
    return px, py


def km_to_px(km: float, lat_mid: float,
             lon_w: float, lon_e: float, w: int) -> float:
    """Convert km to approximate pixels at given latitude."""
    deg_lon_per_km = 1.0 / max(111.0 * math.cos(math.radians(abs(lat_mid))), 0.5)
    deg_per_px = (lon_e - lon_w) / w
    return km * deg_lon_per_km / deg_per_px


# ── BMNG source crop ─────────────────────────────────────────────────────────

_bmng_cache: Optional[Image.Image] = None

def load_bmng_crop(lon_w: float, lon_e: float, lat_s: float, lat_n: float,
                   out_w: int, out_h: int) -> Image.Image:
    """Crop the 21K GeoTIFF to geographic bounds, resize to (out_w, out_h)."""
    global _bmng_cache
    if _bmng_cache is None:
        print(f"  [bmng] loading 21K source TIF (21600×10800)…")
        _bmng_cache = Image.open(BMNG_TIF).copy()

    src_w, src_h = _bmng_cache.size  # 21600 × 10800

    # Pixel bounds in the 21K image (y=0 = north pole)
    x0 = round((lon_w + 180.0) / 360.0 * src_w)
    x1 = round((lon_e + 180.0) / 360.0 * src_w)
    y0 = round((90.0 - lat_n) / 180.0 * src_h)
    y1 = round((90.0 - lat_s) / 180.0 * src_h)

    x0 = max(0, min(x0, src_w))
    x1 = max(0, min(x1, src_w))
    y0 = max(0, min(y0, src_h))
    y1 = max(0, min(y1, src_h))

    crop = _bmng_cache.crop((x0, y0, x1, y1))
    return crop.resize((out_w, out_h), Image.LANCZOS)


# ── GEBCO depth tint ─────────────────────────────────────────────────────────

def _gebco_path(lon_w: float, lon_e: float, lat_s: float, lat_n: float) -> Path:
    """Return the GEBCO GeoTIFF path for a 90°×90° quadrant."""
    # Filenames use format: gebco_2026_sub_ice_n{N}_s{S}_w{W}_e{E}_geotiff.tif
    def fmt(v): return str(int(v)) + ".0"
    n, s = fmt(lat_n), fmt(lat_s)
    w, e = fmt(lon_w), fmt(lon_e)
    fname = f"gebco_2026_sub_ice_n{n}_s{s}_w{w}_e{e}_geotiff.tif"
    return GEBCO_DIR / fname


def load_gebco_elevation(lon_w: float, lon_e: float, lat_s: float, lat_n: float,
                          out_w: int, out_h: int) -> np.ndarray:
    """
    Load GEBCO elevation (m) for the requested bounds, resampled to (out_w, out_h).
    Handles cases where bounds span multiple GEBCO quadrants (8k/4k tiles).
    """
    # Determine which GEBCO quads are needed (quads are 90°×90°)
    # Northern vs southern hemisphere
    lat_bands = []
    if lat_n > 0:
        lat_bands.append((0.0, 90.0))
    if lat_s < 0:
        lat_bands.append((-90.0, 0.0))

    lon_bands = []
    for lon_start in [-180.0, -90.0, 0.0, 90.0]:
        lon_end = lon_start + 90.0
        if lon_start < lon_e and lon_end > lon_w:
            lon_bands.append((lon_start, lon_end))

    # Total canvas for the requested region
    total_lon = lon_e - lon_w
    total_lat = lat_n - lat_s

    canvas = np.zeros((out_h, out_w), dtype=np.float32)

    for (qlon_w, qlon_e) in lon_bands:
        for (qlat_s, qlat_n) in lat_bands:
            path = _gebco_path(qlon_w, qlon_e, qlat_s, qlat_n)
            if not path.exists():
                print(f"  [gebco] WARNING: {path.name} not found, skipping quad")
                continue

            elev_raw = tifffile.imread(str(path)).astype(np.float32)
            # elev_raw shape: (21600, 21600) covering (qlat_n → qlat_s) top-to-bottom

            # Intersection of requested bounds with this quad
            isec_lon_w = max(lon_w, qlon_w)
            isec_lon_e = min(lon_e, qlon_e)
            isec_lat_s = max(lat_s, qlat_s)
            isec_lat_n = min(lat_n, qlat_n)

            qh, qw = elev_raw.shape  # 21600 × 21600

            # Source pixels in GEBCO quad
            sx0 = round((isec_lon_w - qlon_w) / 90.0 * qw)
            sx1 = round((isec_lon_e - qlon_w) / 90.0 * qw)
            sy0 = round((qlat_n - isec_lat_n) / 90.0 * qh)
            sy1 = round((qlat_n - isec_lat_s) / 90.0 * qh)
            sx0, sx1 = max(0, sx0), min(qw, sx1)
            sy0, sy1 = max(0, sy0), min(qh, sy1)

            elev_crop = elev_raw[sy0:sy1, sx0:sx1]

            # Destination pixels in output canvas
            dx0 = round((isec_lon_w - lon_w) / total_lon * out_w)
            dx1 = round((isec_lon_e - lon_w) / total_lon * out_w)
            dy0 = round((lat_n - isec_lat_n) / total_lat * out_h)
            dy1 = round((lat_n - isec_lat_s) / total_lat * out_h)
            dx0, dx1 = max(0, dx0), min(out_w, dx1)
            dy0, dy1 = max(0, dy0), min(out_h, dy1)

            dw, dh = dx1 - dx0, dy1 - dy0
            if dw <= 0 or dh <= 0 or elev_crop.size == 0:
                continue

            # Downsample GEBCO crop to destination size
            elev_img = Image.fromarray(elev_crop, mode='F')
            elev_img = elev_img.resize((dw, dh), Image.BILINEAR)
            canvas[dy0:dy1, dx0:dx1] = np.array(elev_img)

    return canvas


def elevation_to_rgb(elev: np.ndarray) -> np.ndarray:
    """Map elevation (m, float32) to RGB (uint8) using 5-level depth palette."""
    h, w = elev.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    thresholds = DEPTH_PALETTE  # (max_depth, color), descending depth order

    for i, (depth_max, color) in enumerate(thresholds[:-1]):
        depth_min = thresholds[i + 1][0]
        # pixels in this depth band
        if i == 0:
            mask = elev >= depth_max  # land (≥0m)
        else:
            prev_depth_max = thresholds[i - 1][0]
            mask = (elev < prev_depth_max) & (elev >= depth_max)

        # interpolate within band for smooth gradient
        if i > 0:
            next_color = np.array(thresholds[i + 1][1], dtype=np.float32)
            this_color = np.array(color, dtype=np.float32)
            t = np.zeros_like(elev)
            band_range = float(depth_max - depth_min)
            if band_range != 0:
                t = np.clip((elev - depth_min) / band_range, 0.0, 1.0)
            blended = this_color[None, None, :] * t[..., None] + next_color[None, None, :] * (1 - t[..., None])
            rgb[mask] = np.clip(blended[mask], 0, 255).astype(np.uint8)
        else:
            rgb[mask] = color

    # deepest band
    last_mask = elev < thresholds[-2][0]
    rgb[last_mask] = thresholds[-1][1]

    return rgb


def render_gebco_tint(lon_w: float, lon_e: float, lat_s: float, lat_n: float,
                       out_w: int, out_h: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Returns:
      tint_rgb: (H, W, 3) uint8 — depth color map
      ocean_mask: (H, W) bool — True where GEBCO says elevation < 0 (ocean)
    """
    elev = load_gebco_elevation(lon_w, lon_e, lat_s, lat_n, out_w, out_h)
    tint_rgb = elevation_to_rgb(elev)
    ocean_mask = elev < 0
    return tint_rgb, ocean_mask


# ── GSHHG coastline clarity ──────────────────────────────────────────────────

def rasterize_land_mask(lon_w: float, lon_e: float, lat_s: float, lat_n: float,
                         w: int, h: int) -> np.ndarray:
    """
    Rasterize GSHHG L1 polygons within bounds to a binary land mask (bool array).
    Returns bool array shape (h, w), True = land.
    """
    sf = shapefile.Reader(str(GSHHG_L1))

    # Expand search bounds by margin for polygons that straddle the boundary
    mlon_w = lon_w - POLY_MARGIN_DEG
    mlon_e = lon_e + POLY_MARGIN_DEG
    mlat_s = lat_s - POLY_MARGIN_DEG
    mlat_n = lat_n + POLY_MARGIN_DEG

    mask_img = Image.new('L', (w, h), 0)
    draw = ImageDraw.Draw(mask_img)

    n_polys = 0
    for shape_rec in sf.iterShapeRecords():
        s = shape_rec.shape
        bbox = s.bbox  # [minLon, minLat, maxLon, maxLat]
        # Quick rejection: skip if entirely outside expanded bounds
        if bbox[2] < mlon_w or bbox[0] > mlon_e or bbox[3] < mlat_s or bbox[1] > mlat_n:
            continue

        pts = s.points
        parts = list(s.parts) + [len(pts)]
        for pi in range(len(s.parts)):
            ring = pts[parts[pi]:parts[pi + 1]]
            if len(ring) < 3:
                continue
            pixel_ring = []
            for lon, lat in ring:
                px, py = geo_to_px(lon, lat, lon_w, lon_e, lat_s, lat_n, w, h)
                pixel_ring.append((px, py))
            draw.polygon(pixel_ring, fill=255)
            n_polys += 1

    return np.array(mask_img, dtype=bool)


def compute_coast_zone_weight(land_mask: np.ndarray, zone_px: float) -> np.ndarray:
    """
    Compute coastal zone weight [0, 1] using distance transform.
    Pixels within zone_px of the land/sea boundary get weight 1.0,
    falling off smoothly to 0 at zone_px distance.
    """
    # Distance from each pixel to nearest True (land) pixel
    dist_from_land = distance_transform_edt(~land_mask).astype(np.float32)
    # Distance from each land pixel to nearest False (ocean) pixel
    dist_from_ocean = distance_transform_edt(land_mask).astype(np.float32)
    # Distance to nearest boundary (either direction)
    dist_to_boundary = np.minimum(dist_from_land, dist_from_ocean)
    # Weight: 1 at boundary, 0 at zone_px
    weight = np.clip(1.0 - dist_to_boundary / max(zone_px, 1.0), 0.0, 1.0)
    return weight


def apply_coastal_clarity(img_arr: np.ndarray, zone_weight: np.ndarray,
                           strength: float) -> np.ndarray:
    """
    Apply unsharp mask clarity enhancement within the coastal zone.
    img_arr: (H, W, 3) float32
    zone_weight: (H, W) float32 [0, 1]
    strength: blend factor for sharpened vs original (0.15 = subtle)
    """
    img_pil = Image.fromarray(np.clip(img_arr, 0, 255).astype(np.uint8))
    # Unsharp mask: radius=2, percent=50, threshold=0
    sharpened = img_pil.filter(ImageFilter.UnsharpMask(radius=2, percent=50, threshold=0))
    sharp_arr = np.array(sharpened, dtype=np.float32)

    w = zone_weight[..., None] * strength
    result = img_arr * (1.0 - w) + sharp_arr * w
    return np.clip(result, 0.0, 255.0)


# ── Small-island visibility pass ─────────────────────────────────────────────

def rasterize_small_island_mask(
    lon_w: float, lon_e: float, lat_s: float, lat_n: float,
    w: int, h: int,
) -> np.ndarray:
    """
    Rasterize L1 polygons with area < ISLAND_AREA_MAX_KM2 to a bool mask.
    Returns (h, w) bool — True = small oceanic island pixel.

    Skips continent-scale polygons (Eurasia, Americas, Africa, large islands
    like Greenland/Borneo) which are already clearly visible at global view.
    """
    sf = shapefile.Reader(str(GSHHG_L1))
    fields = [f[0] for f in sf.fields[1:]]

    mlon_w = lon_w - POLY_MARGIN_DEG
    mlon_e = lon_e + POLY_MARGIN_DEG
    mlat_s = lat_s - POLY_MARGIN_DEG
    mlat_n = lat_n + POLY_MARGIN_DEG

    mask_img = Image.new('L', (w, h), 0)
    draw = ImageDraw.Draw(mask_img)

    for shape_rec in sf.iterShapeRecords():
        rec  = dict(zip(fields, shape_rec.record))
        area = float(rec.get('area', 0))
        if area >= ISLAND_AREA_MAX_KM2:
            continue  # large landmass — skip

        s    = shape_rec.shape
        bbox = s.bbox
        if bbox[2] < mlon_w or bbox[0] > mlon_e or bbox[3] < mlat_s or bbox[1] > mlat_n:
            continue

        pts   = s.points
        parts = list(s.parts) + [len(pts)]
        for pi in range(len(s.parts)):
            ring = pts[parts[pi]:parts[pi + 1]]
            if len(ring) < 3:
                continue
            pixel_ring = [
                geo_to_px(lon, lat, lon_w, lon_e, lat_s, lat_n, w, h)
                for lon, lat in ring
            ]
            draw.polygon(pixel_ring, fill=255)

    return np.array(mask_img, dtype=bool)


def small_island_visibility_pass(
    composite_arr: np.ndarray,
    small_island_mask: np.ndarray,
    ocean_mask: np.ndarray,
    lod: str,
) -> np.ndarray:
    """
    Apply a subtle outer-glow around small oceanic islands.

    Effect: pixels within ISLAND_GLOW_PX of a small-island edge that are
    classified as ocean receive a light lift toward pale shallow-water blue.
    Strength is very low (max 10%) — the goal is "not invisible" not "map symbol".

    Only ocean pixels are modified; island land pixels are untouched.
    The glow fades linearly from the island edge outward.
    """
    if not small_island_mask.any():
        return composite_arr

    # Distance from each pixel to nearest small-island pixel (0 on island itself)
    dist_from_island = distance_transform_edt(~small_island_mask).astype(np.float32)

    # Glow weight: 1.0 at edge, 0.0 at ISLAND_GLOW_PX distance
    glow = np.clip(1.0 - dist_from_island / max(ISLAND_GLOW_PX, 1.0), 0.0, 1.0)

    # Apply only to ocean pixels (not land, not small-island land itself)
    ocean_only = ocean_mask & ~small_island_mask
    eff_strength = ISLAND_GLOW_STRENGTH * _ISLAND_LOD_SCALE.get(lod, 1.0)
    w_eff = glow * ocean_only.astype(np.float32) * eff_strength
    w_eff = w_eff[..., None]  # broadcast over RGB

    result = composite_arr * (1.0 - w_eff) + ISLAND_GLOW_COLOR * w_eff
    return np.clip(result, 0.0, 255.0)


# ── Composite ─────────────────────────────────────────────────────────────────

# ── Stage 14+15 lazy loader ───────────────────────────────────────────────────

_vue_instance = None


def _load_vue():
    """Load VisualUnificationEngine (Stage 14+15) without triggering __init__.py.

    core/rendering/__init__.py eagerly imports D6Renderer and other heavy
    modules. We bypass it by loading the two needed files directly via
    importlib, injecting them into sys.modules so relative imports resolve.
    """
    global _vue_instance
    if _vue_instance is not None:
        return _vue_instance

    import importlib.util
    rendering_dir = ROOT / "core" / "rendering"

    # Step 1: load perceptual_calibration_engine (no relative imports of its own)
    pce_spec = importlib.util.spec_from_file_location(
        "core.rendering.perceptual_calibration_engine",
        rendering_dir / "perceptual_calibration_engine.py",
    )
    pce_mod = importlib.util.module_from_spec(pce_spec)
    sys.modules["core.rendering.perceptual_calibration_engine"] = pce_mod
    pce_spec.loader.exec_module(pce_mod)

    # Step 2: load visual_unification_engine (imports .perceptual_calibration_engine)
    vue_spec = importlib.util.spec_from_file_location(
        "core.rendering.visual_unification_engine",
        rendering_dir / "visual_unification_engine.py",
    )
    vue_mod = importlib.util.module_from_spec(vue_spec)
    vue_mod.__package__ = "core.rendering"
    sys.modules["core.rendering.visual_unification_engine"] = vue_mod
    vue_spec.loader.exec_module(vue_mod)

    _vue_instance = vue_mod.VisualUnificationEngine()
    print("  [noon-air] VisualUnificationEngine + Stage 15 loaded")
    return _vue_instance


# ── Ice/snow exclusion constants ──────────────────────────────────────────────

_ICE_LUMA_FADE_LOW  = 200.0   # below: full GEBCO blend
_ICE_LUMA_FADE_HIGH = 235.0   # above: GEBCO blend = 0 (ice/snow excluded)


def composite_tile(base: Image.Image,
                   gebco_tint: np.ndarray, ocean_mask: np.ndarray,
                   coast_weight: np.ndarray,
                   cfg: dict) -> Image.Image:
    """
    Layer order:
      1. BMNG base (land and ocean)
      2. GEBCO depth tint blended on ocean pixels only, ice/snow excluded
      3. GSHHG coastal clarity applied within zone

    Ice exclusion: GEBCO sub_ice_topo has negative elevation values under the
    Antarctic ice sheet, causing ocean_mask=True even beneath the ice. A
    luminance-based fade mask suppresses the blend on bright (ice/snow) pixels.
    """
    base_arr = np.array(base, dtype=np.float32)
    blend = cfg["gebco_blend"]

    # Step 1: GEBCO ocean blend with ice/snow exclusion
    # Compute per-pixel luminance (Rec.601)
    luma = (0.299 * base_arr[..., 0] +
            0.587 * base_arr[..., 1] +
            0.114 * base_arr[..., 2])
    # Fade from 1.0 (normal blend) → 0.0 (fully excluded) as luma rises toward ice
    ice_suppress = np.clip(
        (_ICE_LUMA_FADE_HIGH - luma) / (_ICE_LUMA_FADE_HIGH - _ICE_LUMA_FADE_LOW),
        0.0, 1.0,
    )

    composite = base_arr.copy()
    om = ocean_mask[..., None]
    effective_blend = blend * om * ice_suppress[..., None]
    composite = composite * (1.0 - effective_blend) + gebco_tint.astype(np.float32) * effective_blend

    # Step 2: GSHHG coastal clarity
    composite = apply_coastal_clarity(composite, coast_weight, cfg["gshhg_strength"])

    return Image.fromarray(np.clip(np.rint(composite), 0, 255).astype(np.uint8))


# ── Tile processor ────────────────────────────────────────────────────────────

def process_tile(lod: str, x: int, y: int, cfg: dict, dry_run: bool = False, noon_air: bool = False, island: bool = False) -> Path:
    """Process a single tile. Returns the output path."""
    t0 = time.time()
    lon_w, lon_e, lat_s, lat_n = tile_bounds(x, y, cfg)
    w, h = cfg["tile_w"], cfg["tile_h"]
    lat_mid = (lat_s + lat_n) / 2.0

    _base_dir = ISLAND_V2_OUT_BASE if island else OUT_BASE
    out_dir = _base_dir / lod
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"tile_{x}_{y}.jpg"

    label = f"[{lod}] tile_{x}_{y} lon[{lon_w:.0f},{lon_e:.0f}] lat[{lat_s:.0f},{lat_n:.0f}]"
    print(f"\n{'─'*60}")
    print(f"  {label}")
    if island:
        print(f"  island-pass: area<{ISLAND_AREA_MAX_KM2:.0f}km², glow={ISLAND_GLOW_PX}px, str={ISLAND_GLOW_STRENGTH*_ISLAND_LOD_SCALE.get(lod,1.):.3f}")
    if dry_run:
        print(f"  → DRY RUN: would write {out_path}")
        if noon_air:
            na_dir = ISLAND_NA_OUT_BASE if island else NOON_AIR_OUT_BASE
            print(f"  → DRY RUN: noon-air → {na_dir / lod / f'tile_{x}_{y}.jpg'}")
        return out_path

    # 1. BMNG base
    print(f"  [1/4] BMNG crop…")
    base = load_bmng_crop(lon_w, lon_e, lat_s, lat_n, w, h)

    # 2. GEBCO depth tint
    print(f"  [2/4] GEBCO elevation → depth tint…")
    gebco_tint, ocean_mask = render_gebco_tint(lon_w, lon_e, lat_s, lat_n, w, h)

    # 3. GSHHG coastal clarity (with seam overlap)
    print(f"  [3/4] GSHHG coastline clarity (zone={cfg['zone_km']}km, overlap={SEAM_OVERLAP_KM}km)…")
    exp_lon_w, exp_lon_e, exp_lat_s, exp_lat_n = expand_bounds(
        lon_w, lon_e, lat_s, lat_n, SEAM_OVERLAP_KM
    )
    exp_lon_span = exp_lon_e - exp_lon_w
    exp_lat_span = exp_lat_n - exp_lat_s
    # Scale expanded resolution proportionally
    exp_w = round(w * exp_lon_span / (lon_e - lon_w))
    exp_h = round(h * exp_lat_span / (lat_n - lat_s))

    # Rasterize land mask at expanded bounds
    land_mask_exp = rasterize_land_mask(exp_lon_w, exp_lon_e, exp_lat_s, exp_lat_n, exp_w, exp_h)

    # Compute zone in expanded space, then crop to tile bounds
    zone_px = km_to_px(cfg["zone_km"], lat_mid, exp_lon_w, exp_lon_e, exp_w)
    coast_weight_exp = compute_coast_zone_weight(land_mask_exp, zone_px)

    # Crop expanded coast weight back to tile bounds
    cx0 = round((lon_w - exp_lon_w) / exp_lon_span * exp_w)
    cx1 = cx0 + w
    cy0 = round((exp_lat_n - lat_n) / exp_lat_span * exp_h)
    cy1 = cy0 + h
    cx0, cx1 = max(0, cx0), min(exp_w, cx1)
    cy0, cy1 = max(0, cy0), min(exp_h, cy1)
    coast_weight = coast_weight_exp[cy0:cy1, cx0:cx1]
    # Ensure exact size (rounding may cause ±1 pixel difference)
    if coast_weight.shape != (h, w):
        cw_img = Image.fromarray((coast_weight * 255).astype(np.uint8))
        coast_weight = np.array(cw_img.resize((w, h), Image.BILINEAR)) / 255.0

    # 4. Composite
    total_steps = 4 + (1 if island else 0)
    print(f"  [4/{total_steps}] composite (GEBCO blend={cfg['gebco_blend']}, GSHHG str={cfg['gshhg_strength']})…")
    result = composite_tile(base, gebco_tint, ocean_mask, coast_weight, cfg)
    result_arr = np.array(result, dtype=np.float32)

    # 5. Small-island visibility pass (optional)
    if island:
        print(f"  [5/{total_steps}] small-island visibility pass (L1 area<{ISLAND_AREA_MAX_KM2:.0f}km²)…")
        small_island_mask = rasterize_small_island_mask(lon_w, lon_e, lat_s, lat_n, w, h)
        n_island_px = int(small_island_mask.sum())
        print(f"    {n_island_px} small-island pixels in tile")
        result_arr = small_island_visibility_pass(result_arr, small_island_mask, ocean_mask, lod)

    result = Image.fromarray(np.clip(np.rint(result_arr), 0, 255).astype(np.uint8))

    # Save V2 tile (out_path already set correctly above — island or baseline)
    result.save(str(out_path), "JPEG", quality=cfg["jpeg_q"], optimize=True, progressive=True)
    elapsed = time.time() - t0
    size_mb = out_path.stat().st_size / 1e6
    print(f"  ✓ saved {out_path.name} ({size_mb:.1f} MB) in {elapsed:.0f}s")

    # Stage 14+15: Noon Air color layer (optional)
    if noon_air:
        vue = _load_vue()
        metadata = {"lod": lod, "lon_w": lon_w, "lon_e": lon_e, "lat_s": lat_s, "lat_n": lat_n}
        na_arr = vue.unify(np.array(result), metadata)
        na_img = Image.fromarray(na_arr)
        # If island pass active, save to _islands candidate dir; otherwise standard dir
        if island:
            na_dir = ISLAND_NA_OUT_BASE / lod
        else:
            na_dir = NOON_AIR_OUT_BASE / lod
        na_dir.mkdir(parents=True, exist_ok=True)
        na_path = na_dir / f"tile_{x}_{y}.jpg"
        na_img.save(str(na_path), "JPEG", quality=cfg["jpeg_q"], optimize=True, progressive=True)
        na_mb = na_path.stat().st_size / 1e6
        variant = "noon-air-islands" if island else "noon-air"
        print(f"  ✓ [{variant}] saved {na_path.name} ({na_mb:.1f} MB)")

    return out_path


# ── LOD orchestrator ──────────────────────────────────────────────────────────

def process_lod(lod: str, cfg: dict, tile_filter: Optional[Tuple[int, int]], dry_run: bool, noon_air: bool = False, island: bool = False) -> dict:
    """Process all tiles for one LOD. Returns summary dict."""
    print(f"\n{'═'*60}")
    print(f"  LOD: {lod}  grid: {cfg['grid_x']}×{cfg['grid_y']}  tile: {cfg['tile_w']}×{cfg['tile_h']}")
    print(f"  zone={cfg['zone_km']}km  strength={cfg['gshhg_strength']}  blend={cfg['gebco_blend']}")
    if noon_air:
        na_dir = ISLAND_NA_OUT_BASE if island else NOON_AIR_OUT_BASE
        print(f"  noon-air: Stage 14+15 → {na_dir / lod}")
    if island:
        print(f"  island-pass: small islands (area<{ISLAND_AREA_MAX_KM2:.0f}km²) → {ISLAND_V2_OUT_BASE / lod}")
    print(f"{'═'*60}")

    results = []
    t_lod = time.time()

    for y in range(cfg["grid_y"]):
        for x in range(cfg["grid_x"]):
            if tile_filter and (x, y) != tile_filter:
                continue
            out_path = process_tile(lod, x, y, cfg, dry_run=dry_run, noon_air=noon_air, island=island)
            results.append({"tile": f"{x}_{y}", "path": str(out_path)})

    elapsed = time.time() - t_lod
    print(f"\n  LOD {lod}: {len(results)} tile(s) in {elapsed:.0f}s")

    if not dry_run:
        v2_base  = ISLAND_V2_OUT_BASE if island else OUT_BASE
        _write_manifest(v2_base, lod, cfg, results, island=island, noon_air=False)
        if noon_air:
            na_base = ISLAND_NA_OUT_BASE if island else NOON_AIR_OUT_BASE
            # Build noon_air result paths from tile coords
            na_results = [
                {"tile": r["tile"], "path": str(na_base / lod / f"tile_{r['tile']}.jpg")}
                for r in results
            ]
            _write_manifest(na_base, lod, cfg, na_results, island=island, noon_air=True)

    return {"lod": lod, "tiles": results, "elapsed_s": round(elapsed, 1)}


def _write_manifest(out_base: Path, lod: str, cfg: dict, results: list, island: bool = False, noon_air: bool = False):
    variant_parts = []
    if noon_air:
        variant_parts.append("noon_air")
    if island:
        variant_parts.append("island_visibility_pass")
    variant = "+".join(variant_parts) if variant_parts else "v2_baseline"

    manifest = {
        "standard": "Global Noon Air Baseline v1",
        "variant": variant,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lod": lod,
        "source": "BMNG_21K_GeoTIFF",
        "source_image": str(BMNG_TIF.name),
        "gebco_source": "GEBCO_2026_sub_ice_GeoTIFF",
        "gshhg_source": "GSHHS_f_L1.shp (full resolution, ~25m accuracy)",
        "gebco_blend": cfg["gebco_blend"],
        "gshhg_zone_km": cfg["zone_km"],
        "gshhg_strength": cfg["gshhg_strength"],
        "seam_overlap_km": SEAM_OVERLAP_KM,
        "island_pass": island,
        "island_area_max_km2": ISLAND_AREA_MAX_KM2 if island else None,
        "island_glow_px": ISLAND_GLOW_PX if island else None,
        "island_glow_strength": ISLAND_GLOW_STRENGTH if island else None,
        "jpeg_quality": cfg["jpeg_q"],
        "grid_x": cfg["grid_x"],
        "grid_y": cfg["grid_y"],
        "tile_size": cfg["tile_w"],
        "complete": True,
        "tiles": [r["tile"] for r in results],
        "projection": "EPSG:4326",
        "tile_pattern": "tile_{x}_{y}.jpg",
        "width": cfg["grid_x"] * cfg["tile_w"],
        "height": cfg["grid_y"] * cfg["tile_h"],
    }
    manifest_path = out_base / lod / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"  manifest [{variant}] → {manifest_path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Global Noon Air Baseline v1 Tile Pipeline")
    p.add_argument("--lod", choices=list(LOD_CONFIGS.keys()), help="Process only this LOD (default: all)")
    p.add_argument("--tile", nargs=2, type=int, metavar=("X", "Y"), help="Process only tile X Y (requires --lod)")
    p.add_argument("--dry-run", action="store_true", help="Print plan without writing files")
    p.add_argument("--no-cache", action="store_true", help="Don't reuse cached BMNG in memory")
    p.add_argument("--noon-air", action="store_true", help="Also apply Stage 14+15 (VUE) → tiles_noon_air_v2/")
    p.add_argument("--islands", action="store_true", help="Small-island visibility pass → tiles_*_islands/ (candidate output)")
    return p.parse_args()


def preflight_check():
    """Verify required inputs exist before starting."""
    ok = True
    for path, label in [
        (BMNG_TIF,  "BMNG 21K GeoTIFF"),
        (GSHHG_L1,  "GSHHG L1 shapefile"),
        (GEBCO_DIR, "GEBCO GeoTIFF directory"),
    ]:
        if not path.exists():
            print(f"  ✗ MISSING: {label}\n    {path}")
            ok = False
        else:
            print(f"  ✓ {label}")

    # Check GEBCO quads
    expected_quads = [
        "gebco_2026_sub_ice_n90.0_s0.0_w-180.0_e-90.0_geotiff.tif",
        "gebco_2026_sub_ice_n90.0_s0.0_w-90.0_e0.0_geotiff.tif",
        "gebco_2026_sub_ice_n90.0_s0.0_w0.0_e90.0_geotiff.tif",
        "gebco_2026_sub_ice_n90.0_s0.0_w90.0_e180.0_geotiff.tif",
        "gebco_2026_sub_ice_n0.0_s-90.0_w-180.0_e-90.0_geotiff.tif",
        "gebco_2026_sub_ice_n0.0_s-90.0_w-90.0_e0.0_geotiff.tif",
        "gebco_2026_sub_ice_n0.0_s-90.0_w0.0_e90.0_geotiff.tif",
        "gebco_2026_sub_ice_n0.0_s-90.0_w90.0_e180.0_geotiff.tif",
    ]
    missing_quads = [q for q in expected_quads if not (GEBCO_DIR / q).exists()]
    if missing_quads:
        for q in missing_quads:
            print(f"  ✗ MISSING GEBCO quad: {q}")
        ok = False
    else:
        print(f"  ✓ GEBCO 8 quadrant tiles")

    return ok


def main():
    args = parse_args()
    tile_filter = tuple(args.tile) if args.tile else None

    noon_air = args.noon_air
    island   = args.islands

    print("\nGlobal Noon Air Baseline v1 — Tile Pipeline")
    print(f"  output: {ISLAND_V2_OUT_BASE if island else OUT_BASE}")
    if noon_air:
        print(f"  noon-air output: {ISLAND_NA_OUT_BASE if island else NOON_AIR_OUT_BASE}")
    if island:
        print(f"  island-pass: ON  (area<{ISLAND_AREA_MAX_KM2:.0f}km², glow={ISLAND_GLOW_PX}px, strength={ISLAND_GLOW_STRENGTH})")
    print(f"  dry-run: {args.dry_run}")
    print("\nPreflight check:")
    if not preflight_check():
        print("\n✗ Preflight failed. Aborting.")
        sys.exit(1)

    lods_to_run = [args.lod] if args.lod else list(LOD_CONFIGS.keys())

    all_results = []
    t_total = time.time()
    for lod in lods_to_run:
        cfg = LOD_CONFIGS[lod]
        result = process_lod(lod, cfg, tile_filter=tile_filter, dry_run=args.dry_run, noon_air=noon_air, island=island)
        all_results.append(result)

    total_elapsed = time.time() - t_total
    print(f"\n{'═'*60}")
    print(f"  Pipeline complete in {total_elapsed:.0f}s")
    for r in all_results:
        print(f"  {r['lod']}: {len(r['tiles'])} tile(s) in {r['elapsed_s']}s")


if __name__ == "__main__":
    main()
