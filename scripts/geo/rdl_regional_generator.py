#!/usr/bin/env python3.11
"""
rdl_regional_generator.py — Regional Detail Layer tile generator

Generates a single high-resolution tile for a specific geographic region.
Reuses the same GEBCO + BMNG 21K + GSHHG sources as global_v2_pipeline.py,
but applies a stronger GEBCO blend (0.65 vs 0.35 global) and outputs at a
higher pixels-per-km ratio due to the smaller geographic extent.

Key insight: GEBCO is at ~460m/px (15 arc-second). At 4096px over a 10°×6°
region, we get ~0.28km/px — 9× more pixels per km than global tiles. This
resolves shallow reef platforms, atoll chains, and island groups.

Usage:
  python3.11 rdl_regional_generator.py --region maldives
  python3.11 rdl_regional_generator.py --region ryukyu --noon-air
  python3.11 rdl_regional_generator.py --list
  python3.11 rdl_regional_generator.py --all --noon-air

Output:
  tiles_rdl_regions/{region_id}/tile.jpg   (4096px, Noon Air optional)
  tiles_rdl_regions/{region_id}/bounds.json

Requires python3.11 with pyshp/scipy/tifffile/Pillow installed:
  python3.11 -m pip install -r scripts/geo/requirements.txt --break-system-packages
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 11):
    sys.exit(
        f"ERROR: python3.11+ required (got {sys.version.split()[0]})\n"
        "Run with: python3.11 scripts/geo/rdl_regional_generator.py"
    )
try:
    import shapefile as _sf_check  # noqa: F401
    import tifffile as _tf_check   # noqa: F401
    import scipy                    # noqa: F401
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
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import shapefile
import tifffile
from scipy.ndimage import distance_transform_edt

Image.MAX_IMAGE_PIXELS = None

# ── Paths (same as global_v2_pipeline.py) ────────────────────────────────────

ROOT      = Path(__file__).parent.parent.parent
BMNG_TIF  = ROOT / "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/21600x10800_geotiff/world.topo.bathy.200408.3x21600x10800_geo.tif"
GEBCO_DIR = ROOT / "d5b_processor_v3/source_cache/gee_global/external_raw/gebco/gebco_2026_sub_ice_topo_geotiff"
GSHHG_L1  = ROOT / "pwa/assets/source/coastline/gshhg/GSHHS_shp/f/GSHHS_f_L1.shp"
RDL_OUT   = ROOT / "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions"

# ── Region definitions ────────────────────────────────────────────────────────
# lon_w, lon_e, lat_s, lat_n — chosen to include the archipelago + context water

REGIONS = {
    "maldives": {
        "label": "马尔代夫",
        "bounds": (71.5, 74.5, -1.5, 8.5),
        "description": "Maldives atoll chain + Lakshadweep approach",
    },
    "ryukyu": {
        "label": "琉球 / 冲绳",
        "bounds": (122.5, 132.5, 23.5, 30.0),
        "description": "Ryukyu Islands chain including Okinawa",
    },
    "philippines_central": {
        "label": "菲律宾中部",
        "bounds": (117.0, 127.0, 6.0, 18.0),
        "description": "Philippine archipelago central region",
    },
    "south_china_sea": {
        "label": "南海",
        "bounds": (108.0, 120.0, 8.0, 22.0),
        "description": "South China Sea including Paracel & Spratly Islands",
    },
    "great_barrier_reef": {
        "label": "大堡礁",
        "bounds": (142.5, 153.5, -25.0, -10.0),
        "description": "Great Barrier Reef and Coral Sea",
    },
    "caribbean_bahamas": {
        "label": "加勒比 / 巴哈马",
        "bounds": (-85.0, -70.0, 17.0, 27.5),
        "description": "Bahamas archipelago and Caribbean island chain",
    },
    "hawaii": {
        "label": "夏威夷",
        "bounds": (-161.5, -154.0, 18.0, 23.0),
        "description": "Hawaiian island chain",
    },
    "indonesia_east": {
        "label": "印度尼西亚东部",
        "bounds": (120.0, 135.0, -10.0, 1.0),
        "description": "Eastern Indonesian archipelago including Sulawesi",
    },
}

# ── Pipeline parameters ───────────────────────────────────────────────────────

OUTPUT_PX     = 4096          # output tile width in pixels
GEBCO_BLEND   = 0.65          # stronger than global 0.35 — richer ocean depth
GSHHG_ZONE_KM = 8.0           # coastal clarity zone
GSHHG_STR     = 0.20          # coastal clarity strength
JPEG_Q        = 92
POLY_MARGIN   = 1.5           # degrees margin for polygon loading
SEAM_KM       = 8.0           # seam overlap for GSHHG

# Ice/snow suppress (same constants as global pipeline)
_ICE_LUMA_FADE_LOW  = 200.0
_ICE_LUMA_FADE_HIGH = 235.0

# GEBCO depth palette (identical to global pipeline)
DEPTH_PALETTE = [
    (    0,  (180, 160, 120)),
    (  -50,  ( 32,  95, 148)),
    ( -200,  ( 20,  68, 124)),
    (-1500,  ( 12,  46,  98)),
    (-4000,  (  6,  29,  72)),
    (-99999, (  2,  13,  46)),
]

# ── Geometry helpers ──────────────────────────────────────────────────────────

def expand_bounds(lon_w, lon_e, lat_s, lat_n, km):
    lat_mid = (lat_s + lat_n) / 2
    deg_lat = km / 111.0
    deg_lon = km / max(111.0 * math.cos(math.radians(abs(lat_mid))), 0.5)
    return (
        max(-180, lon_w - deg_lon), min(180, lon_e + deg_lon),
        max( -90, lat_s - deg_lat), min( 90, lat_n + deg_lat),
    )

def geo_to_px(lon, lat, lon_w, lon_e, lat_s, lat_n, w, h):
    px = (lon - lon_w) / (lon_e - lon_w) * w
    py = (lat_n - lat) / (lat_n - lat_s) * h
    return px, py

def km_to_px(km, lat_mid, lon_w, lon_e, w):
    deg_lon_per_km = 1.0 / max(111.0 * math.cos(math.radians(abs(lat_mid))), 0.5)
    deg_per_px = (lon_e - lon_w) / w
    return km * deg_lon_per_km / deg_per_px

def resolution_info(lon_w, lon_e, lat_s, lat_n, tw):
    lat_mid = (lat_s + lat_n) / 2
    km_per_deg = 111.0 * math.cos(math.radians(abs(lat_mid)))
    px_per_km = tw / ((lon_e - lon_w) * km_per_deg)
    return px_per_km

# ── BMNG source ───────────────────────────────────────────────────────────────

_bmng_cache = None

def load_bmng_crop(lon_w, lon_e, lat_s, lat_n, out_w, out_h):
    global _bmng_cache
    if _bmng_cache is None:
        print("  [bmng] loading 21K source TIF (21600×10800)…")
        _bmng_cache = Image.open(BMNG_TIF).copy()
    src_w, src_h = _bmng_cache.size
    x0 = max(0, min(round((lon_w + 180) / 360 * src_w), src_w))
    x1 = max(0, min(round((lon_e + 180) / 360 * src_w), src_w))
    y0 = max(0, min(round((90 - lat_n) / 180 * src_h), src_h))
    y1 = max(0, min(round((90 - lat_s) / 180 * src_h), src_h))
    crop = _bmng_cache.crop((x0, y0, x1, y1))
    return crop.resize((out_w, out_h), Image.LANCZOS)

# ── GEBCO depth ───────────────────────────────────────────────────────────────

def _gebco_path(lon_w, lon_e, lat_s, lat_n):
    def fmt(v): return str(int(v)) + ".0"
    n, s = fmt(lat_n), fmt(lat_s)
    w, e = fmt(lon_w), fmt(lon_e)
    return GEBCO_DIR / f"gebco_2026_sub_ice_n{n}_s{s}_w{w}_e{e}_geotiff.tif"

def load_gebco_elevation(lon_w, lon_e, lat_s, lat_n, out_w, out_h):
    lat_bands = []
    if lat_n > 0: lat_bands.append((0.0, 90.0))
    if lat_s < 0: lat_bands.append((-90.0, 0.0))
    lon_bands = []
    for ls in [-180.0, -90.0, 0.0, 90.0]:
        le = ls + 90.0
        if ls < lon_e and le > lon_w:
            lon_bands.append((ls, le))

    total_lon = lon_e - lon_w
    total_lat = lat_n - lat_s
    canvas = np.zeros((out_h, out_w), dtype=np.float32)

    for (qlon_w, qlon_e) in lon_bands:
        for (qlat_s, qlat_n) in lat_bands:
            path = _gebco_path(qlon_w, qlon_e, qlat_s, qlat_n)
            if not path.exists():
                print(f"  [gebco] WARNING: {path.name} not found, skipping")
                continue
            elev_raw = tifffile.imread(str(path)).astype(np.float32)
            isec_lon_w = max(lon_w, qlon_w); isec_lon_e = min(lon_e, qlon_e)
            isec_lat_s = max(lat_s, qlat_s); isec_lat_n = min(lat_n, qlat_n)
            qh, qw = elev_raw.shape
            sx0 = round((isec_lon_w - qlon_w) / 90 * qw)
            sx1 = round((isec_lon_e - qlon_w) / 90 * qw)
            sy0 = round((qlat_n - isec_lat_n) / 90 * qh)
            sy1 = round((qlat_n - isec_lat_s) / 90 * qh)
            sx0, sx1 = max(0, sx0), min(qw, sx1)
            sy0, sy1 = max(0, sy0), min(qh, sy1)
            elev_crop = elev_raw[sy0:sy1, sx0:sx1]
            dx0 = round((isec_lon_w - lon_w) / total_lon * out_w)
            dx1 = round((isec_lon_e - lon_w) / total_lon * out_w)
            dy0 = round((lat_n - isec_lat_n) / total_lat * out_h)
            dy1 = round((lat_n - isec_lat_s) / total_lat * out_h)
            dx0, dx1 = max(0, dx0), min(out_w, dx1)
            dy0, dy1 = max(0, dy0), min(out_h, dy1)
            dw, dh = dx1 - dx0, dy1 - dy0
            if dw <= 0 or dh <= 0 or elev_crop.size == 0:
                continue
            e_img = Image.fromarray(elev_crop, mode='F').resize((dw, dh), Image.BILINEAR)
            canvas[dy0:dy1, dx0:dx1] = np.array(e_img)
    return canvas

def elevation_to_rgb(elev):
    h, w = elev.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    thresholds = DEPTH_PALETTE
    for i, (depth_max, color) in enumerate(thresholds[:-1]):
        depth_min = thresholds[i + 1][0]
        if i == 0:
            mask = elev >= depth_max
        else:
            prev_depth_max = thresholds[i - 1][0]
            mask = (elev < prev_depth_max) & (elev >= depth_max)
        if i > 0:
            next_color = np.array(thresholds[i + 1][1], dtype=np.float32)
            this_color = np.array(color, dtype=np.float32)
            t = np.zeros_like(elev)
            band_range = float(depth_max - depth_min)
            if band_range != 0:
                t = np.clip((elev - depth_min) / band_range, 0, 1)
            blended = this_color[None, None, :] * t[..., None] + next_color[None, None, :] * (1 - t[..., None])
            rgb[mask] = np.clip(blended[mask], 0, 255).astype(np.uint8)
        else:
            rgb[mask] = color
    last_mask = elev < thresholds[-2][0]
    rgb[last_mask] = thresholds[-1][1]
    return rgb

# ── GSHHG coastline ───────────────────────────────────────────────────────────

def rasterize_land_mask(lon_w, lon_e, lat_s, lat_n, w, h):
    sf = shapefile.Reader(str(GSHHG_L1))
    mlon_w = lon_w - POLY_MARGIN; mlon_e = lon_e + POLY_MARGIN
    mlat_s = lat_s - POLY_MARGIN; mlat_n = lat_n + POLY_MARGIN
    mask_img = Image.new('L', (w, h), 0)
    draw = ImageDraw.Draw(mask_img)
    for sr in sf.iterShapeRecords():
        s = sr.shape
        bb = s.bbox
        if bb[2] < mlon_w or bb[0] > mlon_e or bb[3] < mlat_s or bb[1] > mlat_n:
            continue
        pts = s.points
        parts = list(s.parts) + [len(pts)]
        for pi in range(len(s.parts)):
            ring = pts[parts[pi]:parts[pi + 1]]
            if len(ring) < 3: continue
            pxring = [geo_to_px(lon, lat, lon_w, lon_e, lat_s, lat_n, w, h) for lon, lat in ring]
            draw.polygon(pxring, fill=255)
    return np.array(mask_img, dtype=bool)

def compute_coast_zone_weight(land_mask, zone_px):
    dist_from_land  = distance_transform_edt(~land_mask).astype(np.float32)
    dist_from_ocean = distance_transform_edt(land_mask).astype(np.float32)
    dist_to_boundary = np.minimum(dist_from_land, dist_from_ocean)
    return np.clip(1.0 - dist_to_boundary / max(zone_px, 1.0), 0.0, 1.0)

def apply_coastal_clarity(img_arr, zone_weight, strength):
    img_pil   = Image.fromarray(np.clip(img_arr, 0, 255).astype(np.uint8))
    sharpened = img_pil.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=0))
    sharp_arr = np.array(sharpened, dtype=np.float32)
    w = zone_weight[..., None] * strength
    return np.clip(img_arr * (1 - w) + sharp_arr * w, 0, 255)

# ── Stage 14+15 lazy loader (same as global pipeline) ────────────────────────

_vue_instance = None

def _load_vue():
    global _vue_instance
    if _vue_instance is not None:
        return _vue_instance
    import importlib.util
    rendering_dir = ROOT / "core" / "rendering"
    pce_spec = importlib.util.spec_from_file_location(
        "core.rendering.perceptual_calibration_engine",
        rendering_dir / "perceptual_calibration_engine.py",
    )
    pce_mod = importlib.util.module_from_spec(pce_spec)
    sys.modules["core.rendering.perceptual_calibration_engine"] = pce_mod
    pce_spec.loader.exec_module(pce_mod)
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

# ── Regional tile compositor ──────────────────────────────────────────────────

def generate_region(region_id: str, noon_air: bool = False, dry_run: bool = False):
    if region_id not in REGIONS:
        print(f"ERROR: unknown region '{region_id}'. Use --list to see options.")
        sys.exit(1)

    cfg  = REGIONS[region_id]
    lon_w, lon_e, lat_s, lat_n = cfg["bounds"]
    lat_mid = (lat_s + lat_n) / 2

    # Compute output height maintaining aspect ratio
    lon_span = lon_e - lon_w
    lat_span = lat_n - lat_s
    tw = OUTPUT_PX
    th = round(tw * lat_span / lon_span)

    px_per_km = resolution_info(lon_w, lon_e, lat_s, lat_n, tw)

    print(f"\n{'═'*60}")
    print(f"  Region: {region_id}  ({cfg['label']})")
    print(f"  Bounds: lon[{lon_w},{lon_e}] lat[{lat_s},{lat_n}]")
    print(f"  Output: {tw}×{th}px  =  {1/px_per_km:.2f}km/px  ({px_per_km:.1f}px/km)")
    print(f"  GEBCO blend: {GEBCO_BLEND}  zone: {GSHHG_ZONE_KM}km  str: {GSHHG_STR}")
    print(f"{'═'*60}")

    out_dir = RDL_OUT / region_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "tile.jpg"

    if dry_run:
        print(f"  → DRY RUN: would write {out_path}")
        return out_path

    t0 = time.time()

    # 1. BMNG base
    print("  [1/4] BMNG 21K crop…")
    base = load_bmng_crop(lon_w, lon_e, lat_s, lat_n, tw, th)

    # 2. GEBCO depth tint (stronger blend for regional)
    print("  [2/4] GEBCO elevation → depth tint (blend=0.65)…")
    elev = load_gebco_elevation(lon_w, lon_e, lat_s, lat_n, tw, th)
    gebco_tint = elevation_to_rgb(elev)
    ocean_mask = elev < 0

    # 3. GSHHG coastal clarity (expanded for seam correctness)
    print(f"  [3/4] GSHHG coastline clarity (zone={GSHHG_ZONE_KM}km, seam={SEAM_KM}km)…")
    exp_lon_w, exp_lon_e, exp_lat_s, exp_lat_n = expand_bounds(lon_w, lon_e, lat_s, lat_n, SEAM_KM)
    exp_lon_span = exp_lon_e - exp_lon_w
    exp_lat_span = exp_lat_n - exp_lat_s
    exp_w = round(tw * exp_lon_span / lon_span)
    exp_h = round(th * exp_lat_span / lat_span)

    land_mask_exp  = rasterize_land_mask(exp_lon_w, exp_lon_e, exp_lat_s, exp_lat_n, exp_w, exp_h)
    zone_px        = km_to_px(GSHHG_ZONE_KM, lat_mid, exp_lon_w, exp_lon_e, exp_w)
    coast_weight_exp = compute_coast_zone_weight(land_mask_exp, zone_px)

    cx0 = round((lon_w - exp_lon_w) / exp_lon_span * exp_w)
    cx1 = cx0 + tw
    cy0 = round((exp_lat_n - lat_n) / exp_lat_span * exp_h)
    cy1 = cy0 + th
    coast_weight = coast_weight_exp[max(0,cy0):min(exp_h,cy1), max(0,cx0):min(exp_w,cx1)]
    if coast_weight.shape != (th, tw):
        cw_img   = Image.fromarray((coast_weight * 255).astype(np.uint8))
        coast_weight = np.array(cw_img.resize((tw, th), Image.BILINEAR)) / 255.0

    # 4. Composite with ice exclusion
    print("  [4/4] composite…")
    base_arr = np.array(base, dtype=np.float32)
    luma = 0.299 * base_arr[..., 0] + 0.587 * base_arr[..., 1] + 0.114 * base_arr[..., 2]
    ice_suppress = np.clip((_ICE_LUMA_FADE_HIGH - luma) / (_ICE_LUMA_FADE_HIGH - _ICE_LUMA_FADE_LOW), 0, 1)

    composite = base_arr.copy()
    om = ocean_mask[..., None]
    eff_blend = GEBCO_BLEND * om * ice_suppress[..., None]
    composite = composite * (1 - eff_blend) + gebco_tint.astype(np.float32) * eff_blend
    composite = apply_coastal_clarity(composite, coast_weight, GSHHG_STR)
    result = Image.fromarray(np.clip(np.rint(composite), 0, 255).astype(np.uint8))

    # Save base regional tile
    result.save(str(out_path), "JPEG", quality=JPEG_Q, optimize=True, progressive=True)
    elapsed = time.time() - t0
    print(f"  ✓ {out_path.name}  ({out_path.stat().st_size/1e6:.1f} MB)  in {elapsed:.0f}s")

    # Stage 14+15 (optional)
    if noon_air:
        vue = _load_vue()
        metadata = {"lod": "rdl", "lon_w": lon_w, "lon_e": lon_e, "lat_s": lat_s, "lat_n": lat_n}
        na_arr = vue.unify(np.array(result), metadata)
        na_path = out_dir / "tile_noon_air.jpg"
        Image.fromarray(na_arr).save(str(na_path), "JPEG", quality=JPEG_Q, optimize=True, progressive=True)
        print(f"  ✓ {na_path.name}  ({na_path.stat().st_size/1e6:.1f} MB)  [noon-air]")

    # Write bounds.json for frontend LOD registration
    bounds_data = {
        "region_id":   region_id,
        "label":       cfg["label"],
        "description": cfg["description"],
        "bounds": {"lon_w": lon_w, "lon_e": lon_e, "lat_s": lat_s, "lat_n": lat_n},
        "output_px":   tw,
        "output_h_px": th,
        "km_per_px":   round(1 / px_per_km, 4),
        "px_per_km":   round(px_per_km, 2),
        "gebco_blend": GEBCO_BLEND,
        "noon_air":    noon_air,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tile":        "tile.jpg",
        "tile_noon_air": "tile_noon_air.jpg" if noon_air else None,
        "uv": {
            "uMin": round((lon_w + 180) / 360, 6),
            "uMax": round((lon_e + 180) / 360, 6),
            "vMin": round((lat_s + 90) / 180, 6),
            "vMax": round((lat_n + 90) / 180, 6),
        },
    }
    bounds_path = out_dir / "bounds.json"
    bounds_path.write_text(json.dumps(bounds_data, indent=2))
    print(f"  ✓ {bounds_path.name}")

    return out_path


# ── Entry point ───────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="RDL Regional Detail Layer tile generator")
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--region", choices=list(REGIONS.keys()), help="Generate tile for this region")
    grp.add_argument("--all", action="store_true", help="Generate tiles for all regions")
    grp.add_argument("--list", action="store_true", help="List available regions and exit")
    p.add_argument("--noon-air", action="store_true", help="Also apply Stage 14+15 VUE → tile_noon_air.jpg")
    p.add_argument("--dry-run", action="store_true", help="Print plan without writing files")
    return p.parse_args()


def preflight():
    ok = True
    for path, label in [(BMNG_TIF, "BMNG 21K"), (GSHHG_L1, "GSHHG L1"), (GEBCO_DIR, "GEBCO dir")]:
        if path.exists():
            print(f"  ✓ {label}")
        else:
            print(f"  ✗ MISSING: {label}  ({path})")
            ok = False
    return ok


def main():
    args = parse_args()

    if args.list:
        print("\nAvailable regions:\n")
        for rid, cfg in REGIONS.items():
            b = cfg["bounds"]
            lon_span = b[1] - b[0]; lat_span = b[3] - b[2]
            lat_mid  = (b[2] + b[3]) / 2
            km_w = lon_span * 111 * math.cos(math.radians(abs(lat_mid)))
            px_km = OUTPUT_PX / km_w
            print(f"  {rid:<25} {cfg['label']:<16} "
                  f"lon[{b[0]},{b[1]}] lat[{b[2]},{b[3]}]  "
                  f"≈{1/px_km:.2f}km/px")
        return

    print("\nRDL Regional Detail Layer Generator")
    print("\nPreflight check:")
    if not preflight():
        sys.exit(1)

    regions_to_run = list(REGIONS.keys()) if args.all else [args.region]
    t_total = time.time()
    for rid in regions_to_run:
        generate_region(rid, noon_air=args.noon_air, dry_run=args.dry_run)

    elapsed = time.time() - t_total
    print(f"\n{'═'*60}")
    print(f"  Done: {len(regions_to_run)} region(s) in {elapsed:.0f}s")


if __name__ == "__main__":
    main()
