#!/usr/bin/env python3
"""
B-6.2G-3B-R Structure Mask Generator — L01+L02 Coverage Supplement
====================================================================
Generates 2K structure masks from ETOPO1 (global bathymetry) and GSHHG
(vector coastlines). Outputs to d5b_processor_v3/d5b_output/structure_masks/.

Masks generated (P0):
  land_mask, ocean_mask, deep_ocean_mask, mid_ocean_mask,
  continental_shelf_mask, shallow_sea_mask, coastline_distance_mask

Masks generated (P1 — existing):
  mountain_mask, plateau_mask

Polar supplement masks (B-6.2P):
  antarctica_ice_mask, greenland_ice_mask, polar_land_ice_mask

Special sea water-only masks (B-6.2S-1):
  red_sea_water_mask, yellow_sea_water_mask, east_china_sea_water_mask,
  japan_sea_water_mask, mediterranean_water_mask, aegean_sea_water_mask,
  caribbean_water_mask, persian_gulf_water_mask, north_sea_water_mask,
  baltic_sea_water_mask, south_china_sea_water_mask

Inland water / lake masks (B-6.2G-1B):
  lake_mask_from_GSHHG_L2, lake_island_mask,
  inland_water_mask, large_lake_mask

Terrain / relief proxy masks (B-6.2G-2B):
  high_mountain_mask, plateau_refined_mask,
  lowland_or_basin_proxy, hill_or_relief_proxy

Major river proxy masks (B-6.2G-3B / B-6.2G-3B-R):
  major_river_proxy, river_buffer_proxy             — L01 baseline (55 shapes)
  major_river_proxy_l01_l02, river_buffer_proxy_l01_l02  — L01+L02 variant (55+2371)

SAFETY:
  - Does NOT modify d6_noon_air_earth_generator.py
  - Does NOT write to pwa/assets/earth/candidates/
  - Does NOT write to pwa/assets/earth/production/
  - Does NOT modify earth3d.js
  - Performs NO git operations

Usage:
  python3 scripts/generate_b6_structure_masks.py --resolution 2048x1024
  python3 scripts/generate_b6_structure_masks.py --resolution 2048x1024 --gshhg-tier f
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import netCDF4 as nc
import numpy as np
import shapefile
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation, distance_transform_edt, gaussian_filter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ETOPO1_PATH  = PROJECT_ROOT / "pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd"
GSHHG_BASE   = PROJECT_ROOT / "pwa/assets/source/coastline/gshhg/GSHHS_shp"
WDBII_BASE   = PROJECT_ROOT / "pwa/assets/source/coastline/gshhg/WDBII_shp"
OUTPUT_DIR   = PROJECT_ROOT / "d5b_processor_v3/d5b_output/structure_masks"

FORBIDDEN_WRITE_PATHS = [
    PROJECT_ROOT / "pwa/assets/earth/candidates",
    PROJECT_ROOT / "pwa/assets/earth/production",
    PROJECT_ROOT / "pwa",
]

# ---------------------------------------------------------------------------
# Special sea configurations
# ---------------------------------------------------------------------------
_SPECIAL_SEA_CONFIGS = [
    ('red_sea_water_mask',
     12.5, 30.0,  32.0,  44.0, None,
     'lat 12.5–30.0, lon 32.0–44.0',
     'Excludes Gulf of Aden at southern edge; bbox clips Bab-el-Mandeb'),
    ('yellow_sea_water_mask',
     30.0, 41.0, 119.0, 127.0, -100.0,
     'lat 30.0–41.0, lon 119.0–127.0',
     'Depth gate z>=-100 selects shallow shelf (avg depth ~44m)'),
    ('east_china_sea_water_mask',
     23.0, 34.0, 120.0, 131.0, None,
     'lat 23.0–34.0, lon 120.0–131.0',
     'Overlaps northern Yellow Sea; use together for composite'),
    ('japan_sea_water_mask',
     33.0, 52.0, 127.0, 142.0, None,
     'lat 33.0–52.0, lon 127.0–142.0',
     'Korea Strait minor bleed at southern edge'),
    ('mediterranean_water_mask',
     30.0, 46.5,  -6.0,  37.0, None,
     'lat 30.0–46.5, lon -6.0–37.0',
     'Includes Aegean, Adriatic, Tyrrhenian; use sub-masks for specificity'),
    ('aegean_sea_water_mask',
     36.0, 42.0,  23.0,  29.0, None,
     'lat 36.0–42.0, lon 23.0–29.0',
     'Sub-region of Mediterranean; no depth gate needed'),
    ('caribbean_water_mask',
      8.0, 25.0, -87.0, -58.0, None,
     'lat 8.0–25.0, lon -87.0–-58.0',
     'Large bbox; southern edge bleeds into Venezuela/Colombia coast'),
    ('persian_gulf_water_mask',
     22.5, 30.5,  47.5,  57.0, -100.0,
     'lat 22.5–30.5, lon 47.5–57.0',
     'Depth gate z>=-100; avg depth ~50m; very enclosed'),
    ('north_sea_water_mask',
     51.0, 62.0,  -4.0,  10.0, -200.0,
     'lat 51.0–62.0, lon -4.0–10.0',
     'Depth gate z>=-200; excludes deep Atlantic; includes Skagerrak'),
    ('baltic_sea_water_mask',
     53.5, 66.0,   9.5,  31.0, None,
     'lat 53.5–66.0, lon 9.5–31.0',
     'Includes Gulf of Finland, Gulf of Bothnia'),
    ('south_china_sea_water_mask',
      0.0, 25.0,  99.0, 122.0, None,
     'lat 0.0–25.0, lon 99.0–122.0',
     'Large bbox; western edge includes Gulf of Thailand'),
]

_SEA_PREVIEW_COLOURS = {
    'red_sea_water_mask':          (255,  80,  80),
    'yellow_sea_water_mask':       (255, 220,  40),
    'east_china_sea_water_mask':   (180, 230,  90),
    'japan_sea_water_mask':        ( 80, 190, 255),
    'mediterranean_water_mask':    (255, 150,  40),
    'aegean_sea_water_mask':       (255, 200,  90),
    'caribbean_water_mask':        ( 40, 255, 180),
    'persian_gulf_water_mask':     (200,  70, 210),
    'north_sea_water_mask':        ( 80,  80, 240),
    'baltic_sea_water_mask':       (130, 200, 255),
    'south_china_sea_water_mask':  ( 60, 200,  90),
}


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------
def assert_output_safety(out: Path) -> None:
    out_resolved = out.resolve()
    for forbidden in FORBIDDEN_WRITE_PATHS:
        try:
            out_resolved.relative_to(forbidden.resolve())
            sys.exit(f"[SAFETY ABORT] Output path {out} is inside forbidden path {forbidden}")
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def md5_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for blk in iter(lambda: f.read(chunk), b''):
            h.update(blk)
    return h.hexdigest()


def feather(mask: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    return np.clip(gaussian_filter(mask.astype(np.float32), sigma=sigma), 0.0, 1.0)


def px_for_latlon(lat: float, lon: float, w: int, h: int):
    col = int(round((lon + 180.0) / 360.0 * (w - 1)))
    row = int(round((90.0 - lat) / 180.0 * (h - 1)))
    return max(0, min(h - 1, row)), max(0, min(w - 1, col))


def _ring_to_pixels(ring, w: int, h: int):
    return [(float((lon + 180.0) / 360.0 * w),
             float((90.0 - lat) / 180.0 * h))
            for lon, lat in ring]


def _draw_shape(draw, shape, w: int, h: int, fill_outer: int = 255, fill_hole: int = 0):
    pts   = shape.points
    parts = list(shape.parts) + [len(pts)]
    for i in range(len(parts) - 1):
        ring = pts[parts[i]:parts[i + 1]]
        if len(ring) < 3:
            continue
        px = _ring_to_pixels(ring, w, h)
        draw.polygon(px, fill=fill_outer if i == 0 else fill_hole)


def _draw_polyline(draw, shape, w: int, h: int, fill: int = 255, width: int = 1):
    """Draw a WDBII Polyline (shapeType=3) — multi-part line segments."""
    pts   = shape.points
    parts = list(shape.parts) + [len(pts)]
    for i in range(len(parts) - 1):
        seg = pts[parts[i]:parts[i + 1]]
        if len(seg) < 2:
            continue
        px = _ring_to_pixels(seg, w, h)
        draw.line(px, fill=fill, width=width)


# ---------------------------------------------------------------------------
# ETOPO1 load
# ---------------------------------------------------------------------------
def load_etopo1(path: Path, target_h: int, target_w: int):
    print(f"[ETOPO1] Loading: {path}")
    t0 = time.time()
    ds = nc.Dataset(str(path), 'r')
    dim   = ds.variables['dimension'][:]
    W_src = int(dim[0])
    H_src = int(dim[1])
    z_raw = ds.variables['z'][:].astype(np.float32).reshape(H_src, W_src)
    ds.close()
    print(f"[ETOPO1] Source: {W_src}×{H_src}, z=[{z_raw.min():.0f}, {z_raw.max():.0f}] m  ({time.time()-t0:.1f}s)")
    ri = np.round(np.linspace(0, H_src - 1, target_h)).astype(int)
    ci = np.round(np.linspace(0, W_src - 1, target_w)).astype(int)
    z = z_raw[np.ix_(ri, ci)]
    del z_raw
    print(f"[ETOPO1] Downsampled to {target_w}×{target_h}, z=[{z.min():.0f}, {z.max():.0f}] m")
    return z, W_src, H_src


# ---------------------------------------------------------------------------
# GSHHG rasterize — L1 land
# ---------------------------------------------------------------------------
def rasterize_gshhg_land(shp_path: Path, w: int, h: int) -> np.ndarray:
    print(f"[GSHHG] Loading: {shp_path}")
    t0 = time.time()
    sf = shapefile.Reader(str(shp_path))
    img  = Image.new('L', (w, h), 0)
    draw = ImageDraw.Draw(img)
    antimeridian_warnings = 0
    n_shapes = 0
    for shape in sf.iterShapes():
        pts   = shape.points
        parts = list(shape.parts) + [len(pts)]
        n_shapes += 1
        for ring_idx in range(len(parts) - 1):
            ring = pts[parts[ring_idx]:parts[ring_idx + 1]]
            if len(ring) < 3:
                continue
            lons = [p[0] for p in ring]
            if any(abs(lons[i+1] - lons[i]) > 180 for i in range(len(lons) - 1)):
                antimeridian_warnings += 1
            px = _ring_to_pixels(ring, w, h)
            draw.polygon(px, fill=255 if ring_idx == 0 else 0)
    sf.close()
    elapsed = time.time() - t0
    print(f"[GSHHG] {n_shapes} shapes rendered in {elapsed:.1f}s")
    if antimeridian_warnings:
        print(f"[GSHHG] WARNING: {antimeridian_warnings} antimeridian-crossing ring(s)")
    land = np.array(img, dtype=np.float32) / 255.0
    print(f"[GSHHG] Land coverage: {land.mean()*100:.1f}%  ({int((land>0.5).sum()):,} px)")
    return land


# ---------------------------------------------------------------------------
# GSHHG rasterize — L2/L3 lake masks (B-6.2G-1B)
# ---------------------------------------------------------------------------
def make_lake_masks(gshhg_base: Path, tier: str, w: int, h: int) -> tuple:
    l2_path = gshhg_base / tier / f"GSHHS_{tier}_L2.shp"
    l3_path = gshhg_base / tier / f"GSHHS_{tier}_L3.shp"
    if not l2_path.exists():
        sys.exit(f"[ABORT] GSHHG L2 not found: {l2_path}")
    if not l3_path.exists():
        sys.exit(f"[ABORT] GSHHG L3 not found: {l3_path}")

    LARGE_THRESHOLD_KM2 = 10000.0

    print(f"[LAKE]  Loading L2: {l2_path}")
    t0 = time.time()
    sf_l2 = shapefile.Reader(str(l2_path))
    img_all   = Image.new('L', (w, h), 0)
    img_large = Image.new('L', (w, h), 0)
    draw_all   = ImageDraw.Draw(img_all)
    draw_large = ImageDraw.Draw(img_large)
    n_l2_total = n_l2_positive = n_l2_negative = 0
    l2_id_set = set()
    for sr in sf_l2.iterShapeRecords():
        n_l2_total += 1
        area = float(sr.record[5]) if sr.record[5] else 0.0
        if area <= 0.0:
            n_l2_negative += 1
            continue
        n_l2_positive += 1
        l2_id_set.add(str(sr.record[0]))
        _draw_shape(draw_all, sr.shape, w, h, 255)
        if area >= LARGE_THRESHOLD_KM2:
            _draw_shape(draw_large, sr.shape, w, h, 255)
    sf_l2.close()
    print(f"[LAKE]  L2: {n_l2_total} total | {n_l2_positive} positive | "
          f"{n_l2_negative} negative excluded  ({time.time()-t0:.1f}s)")

    print(f"[LAKE]  Loading L3: {l3_path}")
    t0 = time.time()
    sf_l3 = shapefile.Reader(str(l3_path))
    img_islands  = Image.new('L', (w, h), 0)
    draw_islands = ImageDraw.Draw(img_islands)
    n_l3_total = n_l3_linked = 0
    for sr in sf_l3.iterShapeRecords():
        n_l3_total += 1
        raw_pid = sr.record[3]
        parent_id = str(raw_pid) if raw_pid is not None else ''
        if parent_id and parent_id in l2_id_set:
            n_l3_linked += 1
        _draw_shape(draw_islands, sr.shape, w, h, 255)
    sf_l3.close()
    print(f"[LAKE]  L3: {n_l3_total} total | {n_l3_linked} parent_id verified  ({time.time()-t0:.1f}s)")

    lake_raw       = np.array(img_all,     dtype=np.float32) / 255.0
    lake_large_raw = np.array(img_large,   dtype=np.float32) / 255.0
    islands_raw    = np.array(img_islands, dtype=np.float32) / 255.0

    lake_hard   = lake_raw       > 0.5
    large_hard  = lake_large_raw > 0.5
    island_hard = islands_raw    > 0.5
    inland_water_hard = lake_hard  & ~island_hard
    large_lake_hard   = large_hard & ~island_hard

    px_lake   = int(lake_hard.sum())
    px_island = int(island_hard.sum())
    px_inland = int(inland_water_hard.sum())
    px_large  = int(large_lake_hard.sum())

    print(f"[LAKE]  lake_mask_from_GSHHG_L2 : {px_lake:>8,} px")
    print(f"[LAKE]  lake_island_mask         : {px_island:>8,} px")
    print(f"[LAKE]  inland_water_mask        : {px_inland:>8,} px")
    print(f"[LAKE]  large_lake_mask          : {px_large:>8,} px")

    stats = {
        'l2_total_shapes':           n_l2_total,
        'l2_positive_area_shapes':   n_l2_positive,
        'l2_negative_area_excluded': n_l2_negative,
        'l3_total_shapes':           n_l3_total,
        'l3_with_valid_parent_id':   n_l3_linked,
        'large_lake_threshold_km2':  LARGE_THRESHOLD_KM2,
        'lake_mask_px':              px_lake,
        'lake_island_mask_px':       px_island,
        'inland_water_mask_px':      px_inland,
        'large_lake_mask_px':        px_large,
        'watchlist_notes': {
            'aral_sea':     'Historical ~67,543 km²; current ~2,500 km²; included; flag at d6 integration',
            'lake_chad':    'Historical ~11,977 km²; current ~1,500 km²; included; flag at d6 integration',
            'lake_titicaca':'Marginal at 2K (~22 px); verify feather does not suppress',
            'qinghai_lake': 'Marginal at 2K (~15 px); verify feather does not suppress',
            'taihu_lake':   'Sub-threshold (~8 px); may be suppressed by feather',
            'qiandao_lake': 'Sub-threshold (~2 px); suppressed from inland_water hard mask at 2K',
            'dongting_lake':'Sub-threshold (~2 px); soft presence only',
            'poyang_lake':  'Absent in h/L2 positive-area; subsumed into Yangtze river-lake zone',
        },
    }

    return {
        'lake_mask_from_GSHHG_L2': feather(lake_hard.astype(np.float32),         1.0),
        'lake_island_mask':        feather(island_hard.astype(np.float32),        1.0),
        'inland_water_mask':       feather(inland_water_hard.astype(np.float32),  1.0),
        'large_lake_mask':         feather(large_lake_hard.astype(np.float32),    1.0),
        '_inland_water_hard':      inland_water_hard,   # internal — used by terrain masks
    }, stats


# ---------------------------------------------------------------------------
# Terrain / relief proxy masks (B-6.2G-2B)
# ---------------------------------------------------------------------------
# Thresholds (documented for metadata)
_TERRAIN_THRESHOLDS = {
    'high_mountain_mask': {
        'elev_min_m':   2500,
        'elev_max_m':   None,
        'method':       'ETOPO1 z > 2500 m AND land AND NOT inland_water; feather sigma=1; '
                        'post-feather: soft-multiply land_mask, hard-exclude inland_water_hard (B-6.2G-2B-P)',
        'rationale':    'Strict high-mountain threshold; captures Himalaya, Andes, Alps, '
                        'Karakoram, Caucasus, Rockies, Atlas; excludes Ethiopian Highlands core (~1800-2500m)',
    },
    'plateau_refined_mask': {
        'elev_smooth_sigma': 5,
        'elev_min_m':   800,
        'elev_max_m':   4500,
        'method':       'gaussian_filter(z, sigma=5) in [800, 4500] m AND land AND NOT inland_water; feather sigma=1; '
                        'post-feather: soft-multiply land_mask, hard-exclude inland_water_hard (B-6.2G-2B-P)',
        'rationale':    'Broad-elevation smoothing (sigma=5 ≈ 100 km) removes isolated peaks; '
                        'retains spatially coherent plateaus: Tibetan Plateau, Altiplano, '
                        'Ethiopian Highlands, Iranian/Anatolian Plateau, Deccan Plateau; '
                        'more selective than raw plateau_mask (500-1500m band)',
    },
    'lowland_or_basin_proxy': {
        'elev_min_m':   None,
        'elev_max_m':   300,
        'method':       'ETOPO1 z <= 300 m AND land AND NOT inland_water; feather sigma=1; '
                        'post-feather: soft-multiply land_mask, hard-exclude inland_water_hard (B-6.2G-2B-P)',
        'rationale':    'Low-elevation land proxy; captures Amazon Basin, North China Plain, '
                        'European Plain, Indo-Gangetic Plain, West Siberian Plain, river deltas; '
                        'Congo Basin (~300-500m) partially missed; proxy only — not a hydrological dataset',
    },
    'hill_or_relief_proxy': {
        'elev_min_m':   300,
        'elev_max_m':   1500,
        'method':       'ETOPO1 z in (300, 1500] m AND land AND NOT inland_water; feather sigma=1; '
                        'post-feather: soft-multiply land_mask, hard-exclude inland_water_hard (B-6.2G-2B-P)',
        'rationale':    'Transitional elevation band proxy for hilly terrain; captures SE Asia hills, '
                        'Central European uplands, Eastern African foothills, Brazilian Highlands margins; '
                        'NOT a true slope/ruggedness measure — elevation-band proxy only; '
                        'overlaps with plateau_refined in 800-1500m zone by design',
    },
}


def apply_terrain_domain(mask: np.ndarray, land_mask: np.ndarray,
                          inland_water_exclude: np.ndarray) -> np.ndarray:
    """
    Post-feather domain clipping for terrain / river proxy masks.

    Clipping policy:
      land:          soft multiply by float land_mask [0,1].
                     Guarantees mask at any ocean pixel (land_mask < 0.5) → result < 0.5.
      inland_water:  hard binary exclusion using bool inland_water_exclude.
                     Pass (inland_water_mask > 0.5) — the feathered threshold — rather than
                     the raw pre-feather binary, to guarantee zero hard-pixel overlap even
                     across feather halos. Zeroes mask wherever inland_water_exclude=True.
    """
    mask = np.clip(mask, 0.0, 1.0)
    mask = mask * land_mask                                    # soft land domain
    mask = mask * (~inland_water_exclude).astype(np.float32)  # hard inland-water exclusion
    return np.clip(mask, 0.0, 1.0)


def make_terrain_masks(z: np.ndarray, land_mask: np.ndarray,
                       inland_water_hard: np.ndarray, w: int, h: int) -> tuple:
    """
    Generate 4 terrain / relief proxy masks (B-6.2G-2B / patched B-6.2G-2B-P).

    All masks:
      - Restricted to land semantics (AND land_hard before feather)
      - Exclude inland_water_mask (AND NOT inland_water_hard before feather)
      - Post-feather: apply_terrain_domain() — soft land clip + hard inland_water exclusion
      - shape (h, w), float32, range [0, 1], no NaN/Inf
      - Feather sigma=1

    Returns (masks_dict, stats_dict).
    """
    print("[TERRAIN] Generating terrain / relief proxy masks (B-6.2G-2B-P)...")
    t0 = time.time()

    land_hard = land_mask > 0.5

    thr = _TERRAIN_THRESHOLDS

    # 1. high_mountain_mask: z > 2500m, land, not inland_water
    hm_elev_min = thr['high_mountain_mask']['elev_min_m']
    hm_raw  = (z > hm_elev_min) & land_hard & ~inland_water_hard
    high_mountain_mask = apply_terrain_domain(
        feather(hm_raw.astype(np.float32), 1.0), land_mask, inland_water_hard)

    # 2. plateau_refined_mask: smooth elevation in [800, 4500]m, land, not inland_water
    sigma_smooth  = thr['plateau_refined_mask']['elev_smooth_sigma']
    elev_smooth   = gaussian_filter(z.astype(np.float64), sigma=sigma_smooth).astype(np.float32)
    pr_elev_min   = thr['plateau_refined_mask']['elev_min_m']
    pr_elev_max   = thr['plateau_refined_mask']['elev_max_m']
    pr_raw = ((elev_smooth >= pr_elev_min) & (elev_smooth <= pr_elev_max)
              & land_hard & ~inland_water_hard)
    plateau_refined_mask = apply_terrain_domain(
        feather(pr_raw.astype(np.float32), 1.0), land_mask, inland_water_hard)

    # 3. lowland_or_basin_proxy: z <= 300m, land, not inland_water
    lb_elev_max  = thr['lowland_or_basin_proxy']['elev_max_m']
    lb_raw = (z <= lb_elev_max) & land_hard & ~inland_water_hard
    lowland_or_basin_proxy = apply_terrain_domain(
        feather(lb_raw.astype(np.float32), 1.0), land_mask, inland_water_hard)

    # 4. hill_or_relief_proxy: 300 < z <= 1500m, land, not inland_water
    hr_elev_min = thr['hill_or_relief_proxy']['elev_min_m']
    hr_elev_max = thr['hill_or_relief_proxy']['elev_max_m']
    hr_raw = ((z > hr_elev_min) & (z <= hr_elev_max)
              & land_hard & ~inland_water_hard)
    hill_or_relief_proxy = apply_terrain_domain(
        feather(hr_raw.astype(np.float32), 1.0), land_mask, inland_water_hard)

    elapsed = time.time() - t0

    # Pre-feather hard px (for record); post-feather px reported in compute_metrics
    px_hm_pre = int(hm_raw.sum())
    px_pr_pre = int(pr_raw.sum())
    px_lb_pre = int(lb_raw.sum())
    px_hr_pre = int(hr_raw.sum())

    # Post-domain-clip hard px
    ocean_hard = ~land_hard
    px_hm = int((high_mountain_mask      > 0.5).sum())
    px_pr = int((plateau_refined_mask    > 0.5).sum())
    px_lb = int((lowland_or_basin_proxy  > 0.5).sum())
    px_hr = int((hill_or_relief_proxy    > 0.5).sum())

    # Domain integrity check
    hm_ocean  = int(((high_mountain_mask      > 0.5) & ocean_hard).sum())
    pr_ocean  = int(((plateau_refined_mask    > 0.5) & ocean_hard).sum())
    lb_ocean  = int(((lowland_or_basin_proxy  > 0.5) & ocean_hard).sum())
    hr_ocean  = int(((hill_or_relief_proxy    > 0.5) & ocean_hard).sum())
    hm_iw     = int(((high_mountain_mask      > 0.5) & inland_water_hard).sum())
    pr_iw     = int(((plateau_refined_mask    > 0.5) & inland_water_hard).sum())
    lb_iw     = int(((lowland_or_basin_proxy  > 0.5) & inland_water_hard).sum())
    hr_iw     = int(((hill_or_relief_proxy    > 0.5) & inland_water_hard).sum())

    print(f"[TERRAIN] {'Mask':<34} {'pre-feather':>11} {'post-clip':>9}  ocean∩  iw∩")
    print(f"[TERRAIN] {'high_mountain_mask':<34} {px_hm_pre:>11,} {px_hm:>9,}  {hm_ocean:>5}  {hm_iw:>4}")
    print(f"[TERRAIN] {'plateau_refined_mask':<34} {px_pr_pre:>11,} {px_pr:>9,}  {pr_ocean:>5}  {pr_iw:>4}")
    print(f"[TERRAIN] {'lowland_or_basin_proxy':<34} {px_lb_pre:>11,} {px_lb:>9,}  {lb_ocean:>5}  {lb_iw:>4}")
    print(f"[TERRAIN] {'hill_or_relief_proxy':<34} {px_hr_pre:>11,} {px_hr:>9,}  {hr_ocean:>5}  {hr_iw:>4}")
    print(f"[TERRAIN] Domain patch: B-6.2G-2B-P  ({elapsed:.1f}s)")
    if any(v > 0 for v in [hm_ocean, pr_ocean, lb_ocean, hr_ocean,
                            hm_iw, pr_iw, lb_iw, hr_iw]):
        print("[TERRAIN] WARNING: domain clip did not fully zero overlap — inspect immediately")
    else:
        print("[TERRAIN] Domain integrity: all terrain ∩ ocean = 0, all terrain ∩ inland_water = 0  PASS")

    stats = {
        'pre_feather_hard_px': {
            'high_mountain_mask_px':     px_hm_pre,
            'plateau_refined_mask_px':   px_pr_pre,
            'lowland_or_basin_proxy_px': px_lb_pre,
            'hill_or_relief_proxy_px':   px_hr_pre,
        },
        'post_clip_hard_px': {
            'high_mountain_mask_px':     px_hm,
            'plateau_refined_mask_px':   px_pr,
            'lowland_or_basin_proxy_px': px_lb,
            'hill_or_relief_proxy_px':   px_hr,
        },
        # top-level aliases kept for compute_metrics compat
        'high_mountain_mask_px':     px_hm,
        'plateau_refined_mask_px':   px_pr,
        'lowland_or_basin_proxy_px': px_lb,
        'hill_or_relief_proxy_px':   px_hr,
        'domain_overlap_px': {
            'high_mountain_mask_ocean':         hm_ocean,
            'plateau_refined_mask_ocean':       pr_ocean,
            'lowland_or_basin_proxy_ocean':     lb_ocean,
            'hill_or_relief_proxy_ocean':       hr_ocean,
            'high_mountain_mask_inland_water':  hm_iw,
            'plateau_refined_mask_inland_water': pr_iw,
            'lowland_or_basin_proxy_inland_water': lb_iw,
            'hill_or_relief_proxy_inland_water': hr_iw,
        },
        'thresholds':               {k: {kk: vv for kk, vv in v.items() if kk != 'rationale'}
                                     for k, v in _TERRAIN_THRESHOLDS.items()},
        'land_only':                True,
        'land_only_after_feather':  True,
        'inland_water_excluded':    True,
        'inland_water_excluded_after_feather': True,
        'domain_clip_policy': {
            'land':          'soft multiply by float land_mask after feather',
            'inland_water':  'hard binary exclusion using inland_water_hard (bool) after feather',
            'patch':         'B-6.2G-2B-P',
        },
        'known_limitations': [
            'All masks are elevation-band proxies derived from ETOPO1; not geomorphological classes',
            'high_mountain_mask: Ethiopian Highlands (~1800-2500m) partially excluded by 2500m threshold',
            'plateau_refined_mask: uses broad Gaussian smoothing (sigma=5 ≈ 100km); '
            'thin plateau edges may be under-represented; proxy, not true plateau dataset',
            'lowland_or_basin_proxy: Congo Basin (~300-500m) partially missed by z<=300m threshold; '
            'lowland proxy only, not true basin dataset',
            'hill_or_relief_proxy: elevation-band only; NOT a slope or ruggedness measure; '
            'overlaps plateau_refined in 800-1500m zone',
            '2K resolution (1px ≈ 19km): sub-pixel mountain ranges and narrow valleys lost',
        ],
    }

    return {
        'high_mountain_mask':     high_mountain_mask,
        'plateau_refined_mask':   plateau_refined_mask,
        'lowland_or_basin_proxy': lowland_or_basin_proxy,
        'hill_or_relief_proxy':   hill_or_relief_proxy,
    }, stats


# ---------------------------------------------------------------------------
# Major river proxy masks (B-6.2G-3B / B-6.2G-3B-R)
# ---------------------------------------------------------------------------
# Buffer configuration (documented for metadata)
_RIVER_BUFFER_RADIUS_PX   = 1          # binary_dilation steps
_RIVER_BUFFER_STRUCTURE   = np.ones((3, 3), dtype=bool)   # 3×3 square (8-connected)
_RIVER_BUFFER_WIDTH_LABEL = '3px raw (~60 km at equator); ~5px visible after feather'

# Regional density check bboxes (lon_w, lat_s, lon_e, lat_n)
_RIVER_DENSITY_REGIONS = {
    'Europe':      (-10,  35,  40,  72),
    'China':       ( 95,  18, 135,  55),
    'India':       ( 65,   5,  95,  35),
    'N_America':   (-130, 20, -55,  75),
    'S_America':   ( -85,-60, -30,  15),
    'Africa':      ( -20,-40,  55,  40),
    'SE_Asia':     (  95, -5, 145,  30),
    'Siberia':     (  55, 45, 180,  75),
}
_RIVER_DENSITY_WARN_THRESHOLD = 0.30   # buffer px / land px in region


def _rasterize_wdbii_level(path: Path, w: int, h: int) -> tuple:
    """Load a WDBII river polyline shp, draw onto 1px canvas. Returns (img_array, n_shapes, n_pts)."""
    sf   = shapefile.Reader(str(path))
    img  = Image.new('L', (w, h), 0)
    draw = ImageDraw.Draw(img)
    n_shapes = n_pts = 0
    for sr in sf.iterShapeRecords():
        n_shapes += 1
        n_pts    += len(sr.shape.points)
        _draw_polyline(draw, sr.shape, w, h, fill=255, width=1)
    sf.close()
    return np.array(img, dtype=np.float32) / 255.0, n_shapes, n_pts


def make_river_masks(wdbii_base: Path, tier: str, land_mask: np.ndarray,
                     inland_water_hard: np.ndarray, w: int, h: int) -> tuple:
    """
    Generate 4 river corridor proxy masks (B-6.2G-3B + B-6.2G-3B-R).

    L01 baseline (B-6.2G-3B):
      major_river_proxy      — 1px L01 raster; feather + domain clip
      river_buffer_proxy     — L01 dilated 3px; feather + domain clip

    L01+L02 variant (B-6.2G-3B-R — fixes Nile / Mississippi / Danube gaps):
      major_river_proxy_l01_l02  — 1px L01+L02 raster; feather + domain clip
      river_buffer_proxy_l01_l02 — L01+L02 dilated 3px; feather + domain clip

    All masks: land-only, inland_water excluded, NOT merged into inland_water_mask,
    corridor proxy only (NOT true river width), feather sigma=1.

    Returns (masks_dict, stats_dict).
    """
    l01_path = wdbii_base / tier / f"WDBII_river_{tier}_L01.shp"
    l02_path = wdbii_base / tier / f"WDBII_river_{tier}_L02.shp"
    if not l01_path.exists(): sys.exit(f"[ABORT] WDBII L01 not found: {l01_path}")
    if not l02_path.exists(): sys.exit(f"[ABORT] WDBII L02 not found: {l02_path}")

    # --- L01 rasterization ---
    t0 = time.time()
    print(f"[RIVER] Loading WDBII {tier}/L01: {l01_path}")
    raw_l01, n_l01_shapes, n_l01_pts = _rasterize_wdbii_level(l01_path, w, h)
    print(f"[RIVER] L01: {n_l01_shapes} shapes | {n_l01_pts:,} points  ({time.time()-t0:.1f}s)")

    # --- L02 rasterization (drawn onto L01 canvas) ---
    t1 = time.time()
    print(f"[RIVER] Loading WDBII {tier}/L02: {l02_path}")
    raw_l02_only, n_l02_shapes, n_l02_pts = _rasterize_wdbii_level(l02_path, w, h)
    print(f"[RIVER] L02: {n_l02_shapes} shapes | {n_l02_pts:,} points  ({time.time()-t1:.1f}s)")

    # L01+L02 combined = pixel-wise max
    raw_combined = np.maximum(raw_l01, raw_l02_only)

    ocean_hard = ~(land_mask > 0.5)

    def _make_pair(raw_float, label):
        """Build (major, buffer) mask pair from a raw float raster."""
        raw_bool  = raw_float > 0.5
        major     = apply_terrain_domain(
            feather(raw_bool.astype(np.float32), 1.0), land_mask, inland_water_hard)
        dilated   = binary_dilation(raw_bool, structure=_RIVER_BUFFER_STRUCTURE,
                                    iterations=_RIVER_BUFFER_RADIUS_PX)
        buf       = apply_terrain_domain(
            feather(dilated.astype(np.float32), 1.0), land_mask, inland_water_hard)
        # counts
        px_raw     = int(raw_bool.sum())
        px_dilated = int(dilated.sum())
        px_major   = int((major > 0.5).sum())
        px_buf     = int((buf   > 0.5).sum())
        m_oc  = int(((major > 0.5) & ocean_hard).sum())
        b_oc  = int(((buf   > 0.5) & ocean_hard).sum())
        m_iw  = int(((major > 0.5) & inland_water_hard).sum())
        b_iw  = int(((buf   > 0.5) & inland_water_hard).sum())
        dom_ok = not any(v > 0 for v in [m_oc, b_oc, m_iw, b_iw])
        print(f"[RIVER] {label:<14} major raw={px_raw:,} post={px_major:,}  "
              f"buf raw={px_dilated:,} post={px_buf:,}  "
              f"ocean∩={m_oc+b_oc}  iw∩={m_iw+b_iw}  "
              f"{'PASS' if dom_ok else 'FAIL'}")
        return major, buf, {
            'raw_px': px_raw, 'dilated_px': px_dilated,
            'major_px': px_major, 'buf_px': px_buf,
            'major_ocean': m_oc, 'buf_ocean': b_oc,
            'major_iw': m_iw, 'buf_iw': b_iw, 'domain_ok': dom_ok,
        }

    major_l01,     buf_l01,     c01  = _make_pair(raw_l01,      'L01')
    major_l01_l02, buf_l01_l02, c012 = _make_pair(raw_combined, 'L01+L02')

    domain_ok_all = c01['domain_ok'] and c012['domain_ok']
    if domain_ok_all:
        print("[RIVER] Domain integrity PASS: all river masks ∩ ocean=0, ∩ inland_water=0")
    else:
        print("[RIVER] WARNING: domain integrity FAIL — inspect stats")

    # --- Density / noise checks ---
    lat_1d = np.linspace(90.0, -90.0, h)
    lon_1d = np.linspace(-180.0, 180.0, w)
    LAT = lat_1d[:, np.newaxis]
    LON = lon_1d[np.newaxis, :]
    land_hard_bool = land_mask > 0.5
    buf01_hard   = buf_l01     > 0.5
    buf012_hard  = buf_l01_l02 > 0.5

    density = {}
    over_dense_regions = []
    for rname, (lw, ls, le, ln) in _RIVER_DENSITY_REGIONS.items():
        bbox   = (LAT >= ls) & (LAT <= ln) & (LON >= lw) & (LON <= le)
        land_n = int((bbox & land_hard_bool).sum())
        d01    = int((bbox & buf01_hard ).sum())
        d012   = int((bbox & buf012_hard).sum())
        r01    = d01  / max(land_n, 1)
        r012   = d012 / max(land_n, 1)
        flag   = 'OVERDENSE' if r012 > _RIVER_DENSITY_WARN_THRESHOLD else 'ok'
        density[rname] = {
            'land_px': land_n, 'buf_l01_px': d01, 'buf_l01l02_px': d012,
            'density_l01': round(r01, 4), 'density_l01l02': round(r012, 4), 'flag': flag,
        }
        if flag == 'OVERDENSE':
            over_dense_regions.append(rname)
        print(f"[RIVER] density {rname:<12}: L01={r01*100:.1f}%  L01+L02={r012*100:.1f}%  {flag}")

    # Growth ratio
    grow_major  = round(c012['major_px'] / max(c01['major_px'], 1), 2)
    grow_buf    = round(c012['buf_px']   / max(c01['buf_px'],   1), 2)
    l01l02_candidate = 'CANDIDATE — needs further filtering' if over_dense_regions else 'USABLE'
    print(f"[RIVER] L01+L02 vs L01 growth: major ×{grow_major}  buffer ×{grow_buf}")
    print(f"[RIVER] L01+L02 assessment: {l01l02_candidate}"
          + (f"  (over-dense: {', '.join(over_dense_regions)})" if over_dense_regions else ""))

    stats = {
        'wdbii_tier':          tier,
        'l01_shape_count':     n_l01_shapes,
        'l01_total_points':    n_l01_pts,
        'l02_shape_count':     n_l02_shapes,
        'l02_total_points':    n_l02_pts,
        'rasterization_method':'PIL ImageDraw.line width=1 (1px polyline)',
        'buffer_radius_px':    _RIVER_BUFFER_RADIUS_PX,
        'buffer_structure':    '3x3 square binary_dilation (8-connected, 1 iteration)',
        'buffer_width_label':  _RIVER_BUFFER_WIDTH_LABEL,
        'l01_baseline': {
            'levels_used':           ['L01'],
            'l02_used':              False,
            'raw_rasterized_px':     c01['raw_px'],
            'raw_dilated_px':        c01['dilated_px'],
            'major_river_proxy_px':  c01['major_px'],
            'river_buffer_proxy_px': c01['buf_px'],
            'domain_overlap_px': {
                'major_ocean': c01['major_ocean'], 'buf_ocean': c01['buf_ocean'],
                'major_iw':    c01['major_iw'],    'buf_iw':    c01['buf_iw'],
            },
            'domain_ok': c01['domain_ok'],
        },
        'l01_l02_variant': {
            'levels_used':                ['L01', 'L02'],
            'l02_role':                   'coverage supplement (Nile/Mississippi/Danube not in L01)',
            'l02_is_proof_of_hierarchy':  False,
            'raw_rasterized_px':          c012['raw_px'],
            'raw_dilated_px':             c012['dilated_px'],
            'major_river_proxy_l01_l02_px': c012['major_px'],
            'river_buffer_proxy_l01_l02_px':c012['buf_px'],
            'growth_vs_l01': {'major': grow_major, 'buffer': grow_buf},
            'domain_overlap_px': {
                'major_ocean': c012['major_ocean'], 'buf_ocean': c012['buf_ocean'],
                'major_iw':    c012['major_iw'],    'buf_iw':    c012['buf_iw'],
            },
            'domain_ok':        c012['domain_ok'],
            'assessment':       l01l02_candidate,
            'over_dense_regions': over_dense_regions,
        },
        'density_check':         density,
        'density_warn_threshold': _RIVER_DENSITY_WARN_THRESHOLD,
        'land_only_after_feather':             True,
        'inland_water_excluded_after_feather': True,
        'domain_clip_policy': {
            'land':         'soft multiply by float land_mask after feather',
            'inland_water': 'hard binary exclusion using (inland_water_mask > 0.5) after feather',
        },
        'proxy_note':     'NOT true river width; NOT merged into inland_water_mask; '
                          'corridor geographic reference proxy only',
        'priority_note':  'inland_water_mask takes priority over river proxy in d6 color application',
        'wdbii_no_name_field':  True,
        'selection_method':     'level-based (L01/L02); NOT name-based',
        'l01_failed_regions':   ['Nile', 'Mississippi', 'Danube'],
        'l01_l02_fixes':        ['Nile (L02: 90 shapes)', 'Mississippi (L02: 81 shapes)',
                                 'Danube (L02: 100 shapes)'],
        'validation_note': 'WDBII has no name field; validation by bbox/geographic spot-check only',
        'known_limitations': [
            'WDBII has no name field; river identification by bbox/geographic corridor only',
            'L01 missing Nile / Mississippi / Danube — fixed in L01+L02 variant',
            '1px polyline at 2K: each px ≈ 19km; thin tributaries may have sampling gaps',
            'buffer corridor (~3px raw ≈ 60km) is NOT proportional to real river width',
            'River mouths / estuaries: estuary handling deferred to B-6.2G-3C-R or later',
            'L03-L11 not used; low-level lines could cause global line network over-density',
            'inland_water_mask priority: corridor pixels near large lakes are zeroed by domain clip',
            'L01+L02 variant is a coverage supplement; L02 level is NOT proof of true hierarchy',
        ],
    }

    return {
        'major_river_proxy':           major_l01,
        'river_buffer_proxy':          buf_l01,
        'major_river_proxy_l01_l02':   major_l01_l02,
        'river_buffer_proxy_l01_l02':  buf_l01_l02,
    }, stats


# ---------------------------------------------------------------------------
# Special sea water-only masks
# ---------------------------------------------------------------------------
def make_special_sea_masks(ocean_mask: np.ndarray, z: np.ndarray,
                            lat_1d: np.ndarray, lon_1d: np.ndarray) -> dict:
    LAT   = lat_1d[:, np.newaxis]
    LON   = lon_1d[np.newaxis, :]
    ocean = ocean_mask > 0.5
    result = {}
    for (name, lat_s, lat_n, lon_w, lon_e, z_floor, _, _note) in _SPECIAL_SEA_CONFIGS:
        bbox = (LAT >= lat_s) & (LAT <= lat_n) & (LON >= lon_w) & (LON <= lon_e)
        sel  = ocean & bbox
        if z_floor is not None:
            sel = sel & (z >= z_floor)
        result[name] = sel.astype(np.float32)
    return result


# ---------------------------------------------------------------------------
# Mask generation (base masks)
# ---------------------------------------------------------------------------
def generate_masks(z: np.ndarray, land_gshhg: np.ndarray, w: int, h: int) -> dict:
    lat_1d = np.linspace(90.0, -90.0, h)
    lon_1d = np.linspace(-180.0, 180.0, w)
    LAT = lat_1d[:, np.newaxis]
    LON = lon_1d[np.newaxis, :]

    land_gshhg_hard = (land_gshhg > 0.5).astype(np.float32)
    land_etopo1     = (z > 0).astype(np.float32)

    antarctica_ice_mask = ((LAT < -60.0) & (z > 0)).astype(np.float32)
    greenland_ice_mask  = (
        (LAT > 59.5) & (LAT < 84.5) & (LON > -74.0) & (LON < -11.0) & (z > 0)
    ).astype(np.float32)
    polar_land_ice_mask = np.maximum(antarctica_ice_mask, greenland_ice_mask)

    land_mask  = np.maximum(land_gshhg_hard, polar_land_ice_mask)
    ocean_mask = (1.0 - land_mask).astype(np.float32)
    ocean_hard = ocean_mask > 0.5

    print(f"[POLAR]  Antarctica supplement: {int((antarctica_ice_mask > 0.5).sum()):,} px")
    print(f"[POLAR]  Greenland  supplement: {int((greenland_ice_mask  > 0.5).sum()):,} px")
    polar_added = int(((land_mask > 0.5) & (land_gshhg_hard < 0.5)).sum())
    print(f"[POLAR]  Polar-only additions:  {polar_added:,} px")

    deep_ocean_raw  = ((z < -3500)                & ocean_hard).astype(np.float32)
    mid_ocean_raw   = ((z >= -3500) & (z < -1000) & ocean_hard).astype(np.float32)
    cont_shelf_raw  = ((z >= -1000) & (z < -200)  & ocean_hard).astype(np.float32)
    shallow_sea_raw = ((z >= -200)  & (z < 0)     & ocean_hard).astype(np.float32)

    deep_ocean_mask  = np.clip(feather(deep_ocean_raw,  1.0) * ocean_mask, 0, 1)
    mid_ocean_mask   = np.clip(feather(mid_ocean_raw,   1.0) * ocean_mask, 0, 1)
    cont_shelf_mask  = np.clip(feather(cont_shelf_raw,  1.0) * ocean_mask, 0, 1)
    shallow_sea_mask = np.clip(feather(shallow_sea_raw, 1.0) * ocean_mask, 0, 1)

    dist_px = distance_transform_edt(ocean_hard).astype(np.float32)
    max_dist = float(dist_px.max())
    coastline_dist_norm = (dist_px / max_dist) if max_dist > 0 else dist_px

    land_hard    = land_mask > 0.5
    mountain_raw = ((z > 1500)             & land_hard).astype(np.float32)
    plateau_raw  = ((z > 500) & (z <= 1500) & land_hard).astype(np.float32)
    mountain_mask = np.clip(feather(mountain_raw, 1.0) * land_mask, 0, 1)
    plateau_mask  = np.clip(feather(plateau_raw,  1.0) * land_mask, 0, 1)

    special_sea = make_special_sea_masks(ocean_mask, z, lat_1d, lon_1d)
    print(f"[SPECIAL_SEA] {len(special_sea)} water-only masks generated")

    base = {
        'land_mask':               land_mask,
        'ocean_mask':              ocean_mask,
        'deep_ocean_mask':         deep_ocean_mask,
        'mid_ocean_mask':          mid_ocean_mask,
        'continental_shelf_mask':  cont_shelf_mask,
        'shallow_sea_mask':        shallow_sea_mask,
        'coastline_distance_mask': coastline_dist_norm.astype(np.float32),
        'mountain_mask':           mountain_mask,
        'plateau_mask':            plateau_mask,
        'antarctica_ice_mask':     antarctica_ice_mask,
        'greenland_ice_mask':      greenland_ice_mask,
        'polar_land_ice_mask':     polar_land_ice_mask,
        '_land_etopo1':            land_etopo1,
        '_land_gshhg_raw':         land_gshhg_hard,
        '_dist_px':                dist_px,
    }
    base.update(special_sea)
    return base


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def compute_metrics(masks: dict, w: int, h: int,
                    lake_stats: dict = None, terrain_stats: dict = None,
                    river_stats: dict = None) -> dict:
    total = w * h

    def stats(key, thresh=0.5):
        m = masks[key]
        px = int((m > thresh).sum())
        return {
            'pixel_count':    px,
            'coverage_ratio': round(float(px / total), 6),
            'min':   round(float(m.min()), 5),
            'max':   round(float(m.max()), 5),
            'mean':  round(float(m.mean()), 5),
        }

    land  = masks['land_mask']
    ocean = masks['ocean_mask']
    deep  = masks['deep_ocean_mask']
    mid   = masks['mid_ocean_mask']
    shelf = masks['continental_shelf_mask']
    shsea = masks['shallow_sea_mask']
    letop = masks['_land_etopo1']
    gshhg = masks['_land_gshhg_raw']
    dpx   = masks['_dist_px']
    ant   = masks['antarctica_ice_mask']

    depth_sum = ((deep > 0.5).astype(int) + (mid > 0.5).astype(int)
                 + (shelf > 0.5).astype(int) + (shsea > 0.5).astype(int))
    depth_overlap_px   = int((depth_sum > 1).sum())
    ocean_px           = int((ocean > 0.5).sum())
    depth_covered_px   = int((depth_sum >= 1).sum())
    depth_uncovered_px = max(0, ocean_px - depth_covered_px)

    disagree_after  = int(((land > 0.5) != (letop > 0.5)).sum())
    disagree_before = int(((gshhg > 0.5) != (letop > 0.5)).sum())

    land_hard = land > 0.5
    any_depth = depth_sum >= 1
    depth_on_land = int((any_depth & land_hard).sum())
    ant_depth     = int((any_depth & (ant > 0.5)).sum())

    check_points = [
        ('Antarctica_interior', -80,   0),
        ('Greenland',            72, -42),
        ('Antarctic_coast',     -70,   0),
        ('Southern_Ocean',      -55,   0),
    ]
    sanity = {}
    for name, lat, lon in check_points:
        r, c = px_for_latlon(lat, lon, w, h)
        entry = {
            'lat': lat, 'lon': lon, 'row': r, 'col': c,
            'land':           round(float(masks['land_mask'][r, c]),  3),
            'ocean':          round(float(masks['ocean_mask'][r, c]), 3),
            'antarctica_ice': round(float(ant[r, c]),                 3),
            'deep_ocean':     round(float(deep[r, c]),                3),
            'mid_ocean':      round(float(mid[r, c]),                 3),
            'shelf':          round(float(shelf[r, c]),               3),
            'shallow':        round(float(shsea[r, c]),               3),
        }
        if name == 'Antarctica_interior':
            ok = entry['land'] > 0.5 and entry['ocean'] < 0.5 and entry['antarctica_ice'] > 0.5
        elif name == 'Greenland':
            ok = entry['land'] > 0.5
        elif name == 'Antarctic_coast':
            ok = entry['land'] > 0.5 or entry['ocean'] > 0.5
        elif name == 'Southern_Ocean':
            ok = entry['ocean'] > 0.5
        else:
            ok = True
        entry['judgment'] = 'PASS' if ok else 'FAIL'
        sanity[name] = entry

    ss_names = [cfg[0] for cfg in _SPECIAL_SEA_CONFIGS]
    ss_metrics = {}
    for name in ss_names:
        if name not in masks:
            continue
        m = masks[name]
        px = m > 0.5
        n_px      = int(px.sum())
        land_leak = int((px & land_hard).sum())
        cfg = next(c for c in _SPECIAL_SEA_CONFIGS if c[0] == name)
        _, lat_s, lat_n, lon_w, lon_e, z_floor, bbox_str, note = cfg
        ss_metrics[name] = {
            'pixel_count':      n_px,
            'coverage_ratio':   round(float(n_px / total), 6),
            'land_leak_pixels': land_leak,
            'bbox':             bbox_str,
            'depth_gate':       f'z >= {z_floor}' if z_floor is not None else 'none',
            'note':             note,
        }

    lake_metrics = {}
    for key in ['lake_mask_from_GSHHG_L2', 'lake_island_mask',
                'inland_water_mask', 'large_lake_mask']:
        if key in masks:
            lake_metrics[key] = stats(key)

    ocean_hard_m = ocean > 0.5
    iw_hard_m    = masks['inland_water_mask'] > 0.5 if 'inland_water_mask' in masks else None
    terrain_metrics = {}
    for key in ['high_mountain_mask', 'plateau_refined_mask',
                'lowland_or_basin_proxy', 'hill_or_relief_proxy']:
        if key not in masks:
            continue
        entry = stats(key)
        m_hard = masks[key] > 0.5
        entry['ocean_overlap_pixels']         = int((m_hard & ocean_hard_m).sum())
        entry['inland_water_overlap_pixels']  = int((m_hard & iw_hard_m).sum()) if iw_hard_m is not None else 'n/a'
        entry['land_only_after_feather']      = True
        entry['inland_water_excluded_after_feather'] = True
        terrain_metrics[key] = entry

    result = {
        'resolution':              f'{w}x{h}',
        'total_pixels':            total,
        'land_mask':               stats('land_mask'),
        'ocean_mask':              stats('ocean_mask'),
        'deep_ocean_mask':         stats('deep_ocean_mask'),
        'mid_ocean_mask':          stats('mid_ocean_mask'),
        'continental_shelf_mask':  stats('continental_shelf_mask'),
        'shallow_sea_mask':        stats('shallow_sea_mask'),
        'coastline_distance_mask': stats('coastline_distance_mask'),
        'mountain_mask':           stats('mountain_mask'),
        'plateau_mask':            stats('plateau_mask'),
        'antarctica_ice_mask':     stats('antarctica_ice_mask'),
        'greenland_ice_mask':      stats('greenland_ice_mask'),
        'polar_land_ice_mask':     stats('polar_land_ice_mask'),
        'checks': {
            'land_plus_ocean_mean':                  round(float((land + ocean).mean()), 6),
            'land_plus_ocean_expected':              '1.0',
            'depth_mask_overlap_pixels':             depth_overlap_px,
            'ocean_px_covered_by_depth_masks':       depth_covered_px,
            'ocean_px_uncovered_by_depth_masks':     depth_uncovered_px,
            'depth_on_land_pixels':                  depth_on_land,
            'antarctica_depth_mask_pixels':          ant_depth,
            'etopo1_vs_gshhg_disagree_before_ratio': round(float(disagree_before / total), 5),
            'etopo1_vs_land_disagree_after_ratio':   round(float(disagree_after / total), 5),
            'disagree_reduction_px':                 disagree_before - disagree_after,
        },
        'polar_sanity_checks':     sanity,
        'special_sea_water_masks': ss_metrics,
        'coastline_distance_px_raw': {
            'min':  round(float(dpx.min()), 2),
            'max':  round(float(dpx.max()), 2),
            'mean': round(float(dpx.mean()), 2),
            'note': 'pixel units only; km calibration deferred to B-6.3',
        },
        'land_coverage': {
            'gshhg_only_ratio':       round(float((gshhg > 0.5).mean()), 5),
            'final_land_ratio':       round(float((land > 0.5).mean()), 5),
            'polar_supplement_ratio': round(float((masks['polar_land_ice_mask'] > 0.5).mean()), 5),
            'etopo1_ratio':           round(float((letop > 0.5).mean()), 5),
        },
    }

    if lake_metrics:
        result['inland_water_masks'] = lake_metrics
    if lake_stats:
        result['inland_water_source_stats'] = {
            k: lake_stats[k] for k in [
                'l2_total_shapes', 'l2_positive_area_shapes', 'l2_negative_area_excluded',
                'l3_total_shapes', 'l3_with_valid_parent_id', 'large_lake_threshold_km2',
                'lake_mask_px', 'lake_island_mask_px', 'inland_water_mask_px', 'large_lake_mask_px',
            ]
        }

    river_metrics = {}
    for key in ['major_river_proxy', 'river_buffer_proxy',
                'major_river_proxy_l01_l02', 'river_buffer_proxy_l01_l02']:
        if key not in masks:
            continue
        entry = stats(key)
        m_hard = masks[key] > 0.5
        entry['ocean_overlap_pixels']                = int((m_hard & ocean_hard_m).sum())
        entry['inland_water_overlap_pixels']         = int((m_hard & iw_hard_m).sum()) if iw_hard_m is not None else 'n/a'
        entry['land_only_after_feather']             = True
        entry['inland_water_excluded_after_feather'] = True
        entry['proxy_note'] = 'polyline corridor proxy; NOT true river width'
        if 'l01_l02' in key:
            entry['variant'] = 'L01+L02 (B-6.2G-3B-R coverage supplement)'
        else:
            entry['variant'] = 'L01 baseline (B-6.2G-3B)'
        river_metrics[key] = entry

    if terrain_metrics:
        result['terrain_masks'] = terrain_metrics
    if terrain_stats:
        result['terrain_source_stats'] = {
            'post_clip_hard_px':              terrain_stats.get('post_clip_hard_px', {}),
            'pre_feather_hard_px':            terrain_stats.get('pre_feather_hard_px', {}),
            'domain_overlap_px':              terrain_stats.get('domain_overlap_px', {}),
            'land_only':                      terrain_stats['land_only'],
            'land_only_after_feather':        terrain_stats.get('land_only_after_feather', True),
            'inland_water_excluded':          terrain_stats['inland_water_excluded'],
            'inland_water_excluded_after_feather': terrain_stats.get('inland_water_excluded_after_feather', True),
            'domain_clip_policy':             terrain_stats.get('domain_clip_policy', {}),
            'thresholds':                     terrain_stats['thresholds'],
        }

    if river_metrics:
        result['river_masks'] = river_metrics
    if river_stats:
        result['river_source_stats'] = {
            'wdbii_tier':              river_stats['wdbii_tier'],
            'l01_shape_count':         river_stats['l01_shape_count'],
            'l01_total_points':        river_stats['l01_total_points'],
            'l02_shape_count':         river_stats.get('l02_shape_count', 'n/a'),
            'l02_total_points':        river_stats.get('l02_total_points', 'n/a'),
            'rasterization_method':    river_stats['rasterization_method'],
            'buffer_radius_px':        river_stats['buffer_radius_px'],
            'buffer_structure':        river_stats['buffer_structure'],
            'l01_baseline':            river_stats.get('l01_baseline', {}),
            'l01_l02_variant':         river_stats.get('l01_l02_variant', {}),
            'density_check':           river_stats.get('density_check', {}),
            'land_only_after_feather': river_stats['land_only_after_feather'],
            'inland_water_excluded_after_feather': river_stats['inland_water_excluded_after_feather'],
            'l01_failed_regions':      river_stats.get('l01_failed_regions', []),
            'l01_l02_fixes':           river_stats.get('l01_l02_fixes', []),
            'selection_method':        river_stats.get('selection_method', ''),
        }

    return result


# ---------------------------------------------------------------------------
# Previews
# ---------------------------------------------------------------------------
def save_previews(masks: dict, out_dir: Path, w: int, h: int) -> list:
    prev_dir = out_dir / 'previews'
    prev_dir.mkdir(parents=True, exist_ok=True)

    def to_u8(m):
        return np.clip(m * 255, 0, 255).astype(np.uint8)

    paths = []

    # 1. Land/ocean
    land = to_u8(masks['land_mask'])
    sea  = to_u8(masks['ocean_mask'])
    p = prev_dir / 'land_ocean_preview.jpg'
    Image.fromarray(np.stack([land, np.zeros_like(land), sea], axis=-1)).save(str(p), quality=87)
    paths.append(str(p))

    # 2. Bathymetry classes + polar ice
    bc = np.zeros((h, w, 3), dtype=np.uint8)
    bc[(masks['deep_ocean_mask']        > 0.5)] = [12,  38, 120]
    bc[(masks['mid_ocean_mask']         > 0.5)] = [35,  90, 190]
    bc[(masks['continental_shelf_mask'] > 0.5)] = [55, 165, 175]
    bc[(masks['shallow_sea_mask']       > 0.5)] = [120, 210, 220]
    bc[(masks['land_mask']              > 0.5)] = [110, 135,  75]
    bc[(masks['plateau_mask']           > 0.5)] = [170, 150,  95]
    bc[(masks['mountain_mask']          > 0.5)] = [210, 210, 210]
    bc[(masks['polar_land_ice_mask']    > 0.5)] = [240, 248, 255]
    p = prev_dir / 'bathymetry_classes_preview.jpg'
    Image.fromarray(bc).save(str(p), quality=87)
    paths.append(str(p))

    # 3. Coastline distance
    p = prev_dir / 'coastline_distance_preview.jpg'
    Image.fromarray(to_u8(masks['coastline_distance_mask'])).save(str(p), quality=87)
    paths.append(str(p))

    # 4. Shallow sea
    p = prev_dir / 'shallow_sea_preview.jpg'
    Image.fromarray(to_u8(masks['shallow_sea_mask'])).save(str(p), quality=87)
    paths.append(str(p))

    # 5. Polar ice supplement
    pol = np.zeros((h, w, 3), dtype=np.uint8)
    pol[(masks['antarctica_ice_mask'] > 0.5)] = [180, 220, 255]
    pol[(masks['greenland_ice_mask']  > 0.5)] = [255, 200, 180]
    p = prev_dir / 'polar_ice_supplement_preview.jpg'
    Image.fromarray(pol).save(str(p), quality=87)
    paths.append(str(p))

    # 6. Special seas
    sc = np.zeros((h, w, 3), dtype=np.uint8)
    for name, colour in _SEA_PREVIEW_COLOURS.items():
        if name in masks:
            sc[(masks[name] > 0.5)] = colour
    p = prev_dir / 'special_seas_preview.jpg'
    Image.fromarray(sc).save(str(p), quality=87)
    paths.append(str(p))

    # 7. Inland water
    lake_keys = ['lake_mask_from_GSHHG_L2', 'lake_island_mask',
                 'inland_water_mask', 'large_lake_mask']
    if any(k in masks for k in lake_keys):
        lk = np.zeros((h, w, 3), dtype=np.uint8)
        lk[(masks['land_mask'] > 0.5)] = [60, 60, 60]
        if 'lake_mask_from_GSHHG_L2' in masks:
            lk[(masks['lake_mask_from_GSHHG_L2'] > 0.5)] = [80, 140, 220]
        if 'inland_water_mask' in masks:
            lk[(masks['inland_water_mask'] > 0.5)] = [100, 180, 255]
        if 'large_lake_mask' in masks:
            lk[(masks['large_lake_mask'] > 0.5)] = [60, 230, 220]
        if 'lake_island_mask' in masks:
            lk[(masks['lake_island_mask'] > 0.5)] = [230, 140, 40]
        p = prev_dir / 'inland_water_overview_preview.jpg'
        Image.fromarray(lk).save(str(p), quality=87)
        paths.append(str(p))

    # 8. Terrain overview (B-6.2G-2B)
    terrain_keys = ['high_mountain_mask', 'plateau_refined_mask',
                    'lowland_or_basin_proxy', 'hill_or_relief_proxy']
    if any(k in masks for k in terrain_keys):
        tc = np.zeros((h, w, 3), dtype=np.uint8)
        # base: ocean dark blue, land dark grey
        tc[(masks['ocean_mask']  > 0.5)] = [20,  40,  80]
        tc[(masks['land_mask']   > 0.5)] = [70,  65,  55]
        # lowland: muted green
        if 'lowland_or_basin_proxy' in masks:
            tc[(masks['lowland_or_basin_proxy'] > 0.5)] = [90, 130,  75]
        # hill: olive
        if 'hill_or_relief_proxy' in masks:
            tc[(masks['hill_or_relief_proxy']   > 0.5)] = [150, 140,  80]
        # plateau: tan / sandy
        if 'plateau_refined_mask' in masks:
            tc[(masks['plateau_refined_mask']   > 0.5)] = [190, 165, 100]
        # high mountain: near-white grey
        if 'high_mountain_mask' in masks:
            tc[(masks['high_mountain_mask']     > 0.5)] = [220, 218, 215]
        # inland water on top: blue
        if 'inland_water_mask' in masks:
            tc[(masks['inland_water_mask']      > 0.5)] = [80, 160, 240]
        p = prev_dir / 'terrain_overview_preview.jpg'
        Image.fromarray(tc).save(str(p), quality=87)
        paths.append(str(p))
        print(f"[PREVIEW] terrain_overview_preview.jpg written")

    # 9. River proxy overview — distinguishes L01 baseline vs L01+L02 variant (B-6.2G-3B-R)
    river_keys = ['major_river_proxy', 'river_buffer_proxy',
                  'major_river_proxy_l01_l02', 'river_buffer_proxy_l01_l02']
    if any(k in masks for k in river_keys):
        rc = np.zeros((h, w, 3), dtype=np.uint8)
        rc[(masks['ocean_mask'] > 0.5)] = [20,  40,  80]
        rc[(masks['land_mask']  > 0.5)] = [60,  55,  45]
        if 'inland_water_mask' in masks:
            rc[(masks['inland_water_mask'] > 0.5)] = [70, 130, 200]
        # L01+L02 buffer: muted blue-green (drawn first, lower priority)
        if 'river_buffer_proxy_l01_l02' in masks:
            rc[(masks['river_buffer_proxy_l01_l02'] > 0.5)] = [50, 180, 200]
        # L01+L02 major: cyan
        if 'major_river_proxy_l01_l02' in masks:
            rc[(masks['major_river_proxy_l01_l02']  > 0.5)] = [80, 230, 230]
        # L01 buffer: warm orange (drawn on top to distinguish baseline)
        if 'river_buffer_proxy' in masks:
            rc[(masks['river_buffer_proxy'] > 0.5)] = [220, 160,  50]
        # L01 major: bright yellow
        if 'major_river_proxy' in masks:
            rc[(masks['major_river_proxy']  > 0.5)] = [255, 250, 100]
        p = prev_dir / 'river_proxy_overview_preview.jpg'
        Image.fromarray(rc).save(str(p), quality=87)
        paths.append(str(p))
        print(f"[PREVIEW] river_proxy_overview_preview.jpg written  "
              f"(yellow=L01, cyan=L01+L02, orange=L01-buf, blue-green=L01+L02-buf)")

    print(f"[PREVIEW] {len(paths)} previews → {prev_dir}")
    return paths


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------
def build_metadata(args, w, h, etopo1_md5, gshhg_shp, etopo1_W, etopo1_H,
                   lake_stats: dict = None, terrain_stats: dict = None,
                   river_stats: dict = None) -> dict:
    ss_meta = {}
    for (name, lat_s, lat_n, lon_w, lon_e, z_floor, bbox_str, note) in _SPECIAL_SEA_CONFIGS:
        ss_meta[name] = {
            'type':               'structure_selector',
            'visual_effect':      'none',
            'd6_integration':     'forbidden_until_B6_4_or_later',
            'method':             'ocean_mask * bbox_mask' + (f' * (z >= {z_floor})' if z_floor else ''),
            'bbox':               bbox_str,
            'depth_gate':         f'z >= {z_floor}' if z_floor else 'none',
            'water_only':         True,
            'land_leak_expected': 0,
            'limitations':        note,
            'feather_required_in_d6': True,
        }

    lake_meta = {}
    if lake_stats:
        lake_meta = {
            'lake_mask_from_GSHHG_L2': {
                'type': 'inland_water_structure_selector',
                'source': f'GSHHG {args.gshhg_tier}/L2 positive-area polygons',
                'filter': 'area > 0; 56 negative-area river-lake zones excluded',
                'd6_integration': 'forbidden_until_B6_4_or_later',
            },
            'lake_island_mask': {
                'type': 'inland_water_structure_selector',
                'source': f'GSHHG {args.gshhg_tier}/L3 lake-island polygons',
                'parent_id_note': 'real L3 parent_id -> L2 id linkage; parent_id=0 not assumed',
                'd6_integration': 'forbidden_until_B6_4_or_later',
            },
            'inland_water_mask': {
                'type': 'inland_water_structure_selector',
                'method': 'lake_hard & ~island_hard; feather sigma=1',
                'd6_integration': 'forbidden_until_B6_4_or_later',
            },
            'large_lake_mask': {
                'type': 'inland_water_structure_selector',
                'method': f'L2 area >= {lake_stats["large_lake_threshold_km2"]:.0f} km² & ~island; feather sigma=1',
                'd6_integration': 'forbidden_until_B6_4_or_later',
            },
        }

    terrain_meta = {}
    if terrain_stats:
        for mask_name, thr in _TERRAIN_THRESHOLDS.items():
            terrain_meta[mask_name] = {
                'type':           'terrain_structure_selector',
                'visual_effect':  'none',
                'd6_integration': 'forbidden_until_B6_4_or_later',
                'method':         thr['method'],
                'rationale':      thr['rationale'],
                'land_only':                       True,
                'land_only_after_feather':         True,
                'inland_water_excluded':           True,
                'inland_water_excluded_after_feather': True,
                'domain_clip_policy': {
                    'land':         'soft multiply by float land_mask after feather',
                    'inland_water': 'hard binary exclusion using (inland_water_mask > 0.5) after feather; '
                                    'feathered threshold used to prevent halo overlap',
                    'patch':        'B-6.2G-2B-P / B-6.2G-3B',
                },
                'proxy_note':     'elevation-band proxy derived from ETOPO1; not a geomorphological classification',
                'priority_note':  'inland_water_mask takes priority over terrain masks in d6 color application',
            }

    deferred = [
        'reef_atoll_proxy_mask (B-6.2S-3)',
        'island_proximity_mask (B-6.2S-3)',
        'bahamas_bank_mask (B-6.2S-2)',
        'river_mouth_proxy (B-6.2G-3C — estuary/mouth handling, post-3B)',
        'river_delta_proxy (B-6.2G-3D or later)',
        'wetland_mask (B-6.2G-4)',
        'desert_arid_mask (B-6.2G-4)',
        'vegetation_biome_mask (B-6.2G-5)',
        'cryosphere_glacier_mask (B-6.2G-6)',
        'reef_island_bank_mask (B-6.2G-7)',
        'bay_strait_gulf_mask (B-6.2G-8)',
        'human_modified_mask (B-6.2G-9)',
        'true_geomorphon_classes (requires DEM derivatives)',
        'true_slope_aspect_masks (requires DEM derivatives)',
        'true_basin_dataset (requires hydrological data)',
    ]

    preview_list = [
        'previews/land_ocean_preview.jpg',
        'previews/bathymetry_classes_preview.jpg',
        'previews/coastline_distance_preview.jpg',
        'previews/shallow_sea_preview.jpg',
        'previews/polar_ice_supplement_preview.jpg',
        'previews/special_seas_preview.jpg',
        'previews/inland_water_overview_preview.jpg',
        'previews/terrain_overview_preview.jpg',
        'previews/river_proxy_overview_preview.jpg',
    ]

    return {
        'generation_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'phase':           'B-6.2G-3B-R (L01+L02 Coverage Supplement)',
        'script':          'scripts/generate_b6_structure_masks.py',
        'resolution':      {'width': w, 'height': h},
        'projection':      'equirectangular / EPSG:4326 (assumed)',
        'dtype':           'float32',
        'sources': {
            'etopo1': {
                'path':     str(ETOPO1_PATH),
                'md5':      etopo1_md5,
                'src_dims': {'width': etopo1_W, 'height': etopo1_H},
                'variable': 'z', 'format': 'GMT NetCDF4 (gdal variant)',
                'variant':  'Ice Surface',
                'note':     'flat z array; reshape(H,W); row 0 = lat +90',
            },
            'gshhg_l1': {
                'tier': args.gshhg_tier, 'path': str(gshhg_shp),
                'version': '2.3.7', 'layer': 'L1 (land polygons)',
            },
            'gshhg_l2': {
                'tier': args.gshhg_tier,
                'path': str(GSHHG_BASE / args.gshhg_tier / f"GSHHS_{args.gshhg_tier}_L2.shp"),
                'version': '2.3.7', 'layer': 'L2 (lake polygons)',
                'filter': 'area > 0 only',
            },
            'gshhg_l3': {
                'tier': args.gshhg_tier,
                'path': str(GSHHG_BASE / args.gshhg_tier / f"GSHHS_{args.gshhg_tier}_L3.shp"),
                'version': '2.3.7', 'layer': 'L3 (islands-in-lakes)',
                'parent_id_note': 'real parent_id -> L2 id mapping',
            },
            'wdbii_l01': {
                'tier':         args.gshhg_tier,
                'path':         str(WDBII_BASE / args.gshhg_tier / f"WDBII_river_{args.gshhg_tier}_L01.shp"),
                'version':      '2.3.7',
                'layer':        'L01 (major rivers)',
                'shape_type':   'Polyline (shapeType=3) — NOT Polygon',
                'fields':       ['id', 'level'],
                'name_field':   'none — WDBII has no river name field',
                'l02_used':     True,
                'l02_note':     'L02 used for L01+L02 variant only; L01 baseline still kept separately',
            },
            'wdbii_l02': {
                'tier':         args.gshhg_tier,
                'path':         str(WDBII_BASE / args.gshhg_tier / f"WDBII_river_{args.gshhg_tier}_L02.shp"),
                'version':      '2.3.7',
                'layer':        'L02 (secondary rivers)',
                'shape_type':   'Polyline (shapeType=3) — NOT Polygon',
                'fields':       ['id', 'level'],
                'purpose':      'coverage supplement for B-6.2G-3C gaps: Nile / Mississippi / Danube absent in L01',
                'b6_2g_3c_failure': 'B-6.2G-3C validation found Nile=0, Mississippi=0, Danube=0 in L01 baseline; '
                                    'L02 fills: Nile~90 shapes, Mississippi~81 shapes, Danube~100 shapes',
            },
        },
        'polar_handling': {
            'antarctica_source': 'ETOPO1 Ice z > 0 where lat < -60',
            'greenland_source':  'ETOPO1 Ice z > 0 where lat 59.5–84.5, lon -74 to -11',
            'method':            'land_mask = max(GSHHG_rasterized, polar_land_ice_supplement)',
        },
        'special_sea_water_masks': ss_meta,
        'inland_water_masks':      lake_meta,
        'terrain_masks':           terrain_meta,
        'river_masks':             {
            'major_river_proxy': {
                'type':      'river_corridor_proxy',
                'variant':   'L01 baseline (B-6.2G-3B)',
                'source':    'WDBII h/L01 (55 shapes)',
                'coverage_gap': 'Nile / Mississippi / Danube NOT covered (see l01_failed_regions)',
                'd6_integration': 'forbidden_until_B6_4_or_later',
                'method':    'PIL ImageDraw.line width=1; post-feather: soft land clip + hard inland_water exclude',
                'proxy_note':'NOT true river width; NOT filled water polygon; corridor reference only',
                'land_only_after_feather': True, 'inland_water_excluded_after_feather': True,
            },
            'river_buffer_proxy': {
                'type':      'river_corridor_proxy',
                'variant':   'L01 baseline (B-6.2G-3B)',
                'source':    'WDBII h/L01 (55 shapes) — dilated',
                'coverage_gap': 'Nile / Mississippi / Danube NOT covered (see l01_failed_regions)',
                'd6_integration': 'forbidden_until_B6_4_or_later',
                'method':    f'binary_dilation(3x3 square, {_RIVER_BUFFER_RADIUS_PX} iter); '
                             f'corridor {_RIVER_BUFFER_WIDTH_LABEL}; '
                             'post-feather: soft land clip + hard inland_water exclude',
                'proxy_note':'buffered corridor proxy; NOT proportional to real river width',
                'land_only_after_feather': True, 'inland_water_excluded_after_feather': True,
            },
            'major_river_proxy_l01_l02': {
                'type':      'river_corridor_proxy',
                'variant':   'L01+L02 variant (B-6.2G-3B-R — coverage supplement)',
                'source':    'WDBII h/L01 + h/L02 (55+2371 shapes)',
                'l02_role':  'coverage supplement for Nile / Mississippi / Danube; NOT a proof of true hierarchy',
                'd6_integration': 'forbidden_until_B6_4_or_later',
                'method':    'PIL ImageDraw.line width=1; L01+L02 pixel-wise max; '
                             'post-feather: soft land clip + hard inland_water exclude',
                'proxy_note':'NOT true river width; NOT filled water polygon',
                'land_only_after_feather': True, 'inland_water_excluded_after_feather': True,
            },
            'river_buffer_proxy_l01_l02': {
                'type':      'river_corridor_proxy',
                'variant':   'L01+L02 variant (B-6.2G-3B-R — coverage supplement)',
                'source':    'WDBII h/L01+L02 — dilated',
                'l02_role':  'coverage supplement; assessment subject to density check',
                'd6_integration': 'forbidden_until_B6_4_or_later',
                'method':    f'binary_dilation(3x3 square, {_RIVER_BUFFER_RADIUS_PX} iter); '
                             f'corridor {_RIVER_BUFFER_WIDTH_LABEL}; '
                             'post-feather: soft land clip + hard inland_water exclude',
                'proxy_note':'buffered corridor proxy; see density_check for over-density assessment',
                'land_only_after_feather': True, 'inland_water_excluded_after_feather': True,
            },
        } if river_stats else {},
        'thresholds': {
            'land_mask':               'max(GSHHG L1, polar_land_ice_supplement)',
            'ocean_mask':              '1 - land_mask',
            'deep_ocean_mask':         'z < -3500 AND ocean',
            'mid_ocean_mask':          '-3500 <= z < -1000 AND ocean',
            'continental_shelf_mask':  '-1000 <= z < -200 AND ocean',
            'shallow_sea_mask':        '-200 <= z < 0 AND ocean',
            'mountain_mask':           'z > 1500 AND land (legacy P1)',
            'plateau_mask':            '500 < z <= 1500 AND land (legacy P1)',
            'high_mountain_mask':      'z > 2500 AND land AND NOT inland_water; post-feather: land clip + inland_water hard-exclude (B-6.2G-2B-P)',
            'plateau_refined_mask':    'gaussian_filter(z, σ=5) in [800,4500] AND land AND NOT inland_water; post-feather: land clip + inland_water hard-exclude (B-6.2G-2B-P)',
            'lowland_or_basin_proxy':  'z <= 300 AND land AND NOT inland_water; post-feather: land clip + inland_water hard-exclude (B-6.2G-2B-P)',
            'hill_or_relief_proxy':    '300 < z <= 1500 AND land AND NOT inland_water; post-feather: land clip + inland_water hard-exclude (B-6.2G-2B-P)',
            'major_river_proxy':           'WDBII h/L01 (55 shapes) polyline raster 1px; post-feather land clip + hard inland_water exclude',
            'river_buffer_proxy':          'WDBII h/L01 (55 shapes) polyline raster + binary_dilation 3x3 1 iter (~3px); post-feather land clip + hard inland_water exclude',
            'major_river_proxy_l01_l02':   'WDBII h/L01+L02 (55+2371 shapes) pixel-wise max raster 1px; post-feather land clip + hard inland_water exclude',
            'river_buffer_proxy_l01_l02':  'WDBII h/L01+L02 pixel-wise max + binary_dilation 3x3 1 iter (~3px); post-feather land clip + hard inland_water exclude',
        },
        'deferred_masks':    deferred,
        'known_limitations': [
            'All terrain masks are ETOPO1 elevation-band proxies; not geomorphological classifications',
            'high_mountain: Ethiopian Highlands (~1800-2500m) partially below 2500m threshold',
            'plateau_refined: broad Gaussian smoothing (σ=5 ≈ 100km); thin edges may be clipped; proxy, not true plateau dataset',
            'lowland_or_basin_proxy: Congo Basin (~300-500m) partially missed; lowland proxy, not true basin dataset',
            'hill_or_relief_proxy: elevation band only; NOT a slope or ruggedness measure; overlaps plateau_refined in 800-1500m zone',
            'ETOPO1 Ice: z reflects ice surface elevation, not bedrock',
            '2K: 1px ≈ 19km — sub-pixel mountain ranges and narrow valleys lost',
            'Aral Sea / Lake Chad: historical GSHHG extent in inland_water_mask',
            'terrain masks must not be used in d6 before B-6.4 API design',
            'inland_water_mask takes semantic priority over terrain masks',
            'B-6.2G-2B-P: post-feather domain clip applied; all terrain masks land-only and inland-water-free after patch',
            'B-6.2G-3B: major_river_proxy and river_buffer_proxy are WDBII L01 baseline (55 shapes); '
            'L01 coverage gaps: Nile / Mississippi / Danube absent (confirmed B-6.2G-3C)',
            'B-6.2G-3B-R: major_river_proxy_l01_l02 and river_buffer_proxy_l01_l02 add L02 (2371 shapes) '
            'as coverage supplement; L01+L02 variant marked CANDIDATE pending density audit; '
            'river proxies NOT merged into inland_water_mask; NOT used in d6 before B-6.4 API design',
        ],
        'output_files': {
            'npz':      'structure_masks_2048x1024.npz',
            'metadata': 'structure_mask_metadata.json',
            'metrics':  'structure_mask_metrics.json',
            'previews': preview_list,
        },
        'safety_assertions': {
            'pwa_assets_not_modified':   True,
            'production_not_written':    True,
            'candidates_not_written':    True,
            'd6_generator_not_modified': True,
            'earth3js_not_modified':     True,
            'no_git_operations':                          True,
            'wdbii_l01_used_for_l01_baseline':            True,
            'wdbii_l02_used_for_l01_l02_coverage_variant':True,
            'wdbii_l03_and_above_not_used':               True,
            'river_proxy_not_merged_into_inland_water':   True,
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='B-6.2G-3B-R Structure Mask Generator')
    parser.add_argument('--resolution', default='2048x1024',
                        help='Output resolution WxH (default: 2048x1024)')
    parser.add_argument('--gshhg-tier', default='h',
                        choices=['c', 'l', 'i', 'h', 'f'],
                        help='GSHHG resolution tier (default: h)')
    args = parser.parse_args()

    W, H = [int(x) for x in args.resolution.lower().split('x')]
    if W > 4096 or H > 2048:
        sys.exit(f"[ABORT] Resolution {W}×{H} exceeds allowed max 4096×2048.")

    print("=" * 70)
    print("B-6.2G-3B-R Structure Mask Generator (L01+L02 Coverage Supplement)")
    print(f"Resolution:  {W} × {H}")
    print(f"GSHHG tier:  {args.gshhg_tier}")
    print(f"Output dir:  {OUTPUT_DIR}")
    print("=" * 70)

    assert_output_safety(OUTPUT_DIR)
    print("[SAFETY] Output path check: PASS")

    if not ETOPO1_PATH.exists():
        sys.exit(f"[ABORT] ETOPO1 not found: {ETOPO1_PATH}")
    gshhg_shp  = GSHHG_BASE / args.gshhg_tier / f"GSHHS_{args.gshhg_tier}_L1.shp"
    wdbii_l01  = WDBII_BASE  / args.gshhg_tier / f"WDBII_river_{args.gshhg_tier}_L01.shp"
    wdbii_l02  = WDBII_BASE  / args.gshhg_tier / f"WDBII_river_{args.gshhg_tier}_L02.shp"
    if not gshhg_shp.exists():
        sys.exit(f"[ABORT] GSHHG not found: {gshhg_shp}")
    if not wdbii_l01.exists():
        sys.exit(f"[ABORT] WDBII L01 not found: {wdbii_l01}")
    if not wdbii_l02.exists():
        sys.exit(f"[ABORT] WDBII L02 not found: {wdbii_l02}")

    print(f"[INPUT] ETOPO1:    {ETOPO1_PATH}  OK")
    print(f"[INPUT] GSHHG:     {gshhg_shp}  OK")
    print(f"[INPUT] WDBII L01: {wdbii_l01}  OK")
    print(f"[INPUT] WDBII L02: {wdbii_l02}  OK")
    print("[INPUT] Computing ETOPO1 MD5...")
    etopo1_md5 = md5_file(ETOPO1_PATH)
    print(f"[INPUT] ETOPO1 MD5: {etopo1_md5}")

    t_total = time.time()

    z, etopo1_W, etopo1_H = load_etopo1(ETOPO1_PATH, H, W)
    land_gshhg = rasterize_gshhg_land(gshhg_shp, W, H)

    print("[MASKS] Generating base structure masks...")
    masks = generate_masks(z, land_gshhg, W, H)

    print("[MASKS] Generating inland water / lake masks (B-6.2G-1B)...")
    lake_masks, lake_stats = make_lake_masks(GSHHG_BASE, args.gshhg_tier, W, H)
    masks.update(lake_masks)
    # derive exclusion mask from feathered inland_water (covers feather halo too)
    _ = masks.pop('_inland_water_hard')
    inland_water_exclude = masks['inland_water_mask'] > 0.5

    print("[MASKS] Generating terrain / relief proxy masks (B-6.2G-2B)...")
    terrain_masks, terrain_stats = make_terrain_masks(
        z, masks['land_mask'], inland_water_exclude, W, H)
    masks.update(terrain_masks)

    print("[MASKS] Generating major river proxy masks (B-6.2G-3B-R): L01 + L01+L02 variants...")
    river_masks, river_stats = make_river_masks(
        WDBII_BASE, args.gshhg_tier, masks['land_mask'], inland_water_exclude, W, H)
    masks.update(river_masks)

    public_keys = [k for k in masks if not k.startswith('_')]
    print(f"[MASKS] Total public masks: {len(public_keys)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    npz_path = OUTPUT_DIR / 'structure_masks_2048x1024.npz'
    np.savez_compressed(str(npz_path), **{k: masks[k] for k in public_keys})
    npz_kb = npz_path.stat().st_size // 1024
    print(f"[OUTPUT] NPZ: {npz_path.name}  ({npz_kb} KB, {len(public_keys)} masks)")

    metrics = compute_metrics(masks, W, H, lake_stats=lake_stats,
                              terrain_stats=terrain_stats, river_stats=river_stats)
    metrics_path = OUTPUT_DIR / 'structure_mask_metrics.json'
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"[OUTPUT] Metrics: {metrics_path.name}")

    metadata = build_metadata(args, W, H, etopo1_md5, gshhg_shp, etopo1_W, etopo1_H,
                              lake_stats=lake_stats, terrain_stats=terrain_stats,
                              river_stats=river_stats)
    meta_path = OUTPUT_DIR / 'structure_mask_metadata.json'
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"[OUTPUT] Metadata: {meta_path.name}")

    save_previews(masks, OUTPUT_DIR, W, H)

    print()
    print("=== SAFETY CONFIRMATIONS ===")
    print("Confirm: d6_noon_air_earth_generator.py NOT modified.")
    print("Confirm: pwa/assets/earth/candidates/   NOT written.")
    print("Confirm: pwa/assets/earth/production/   NOT written.")
    print("Confirm: WDBII L01 used for baseline; L02 used for L01+L02 variant only.")
    print("Confirm: WDBII L03+ NOT used.")
    print("Confirm: river proxy NOT merged into inland_water_mask.")
    print("Confirm: No git operations performed.")

    print()
    print("=== B-6.2G-3B-R COMPLETE ===")
    print(f"Total masks in NPZ: {len(public_keys)}")
    print(f"NPZ size: {npz_kb} KB    Total time: {time.time()-t_total:.1f}s")

    chk = metrics['checks']
    print()
    print("--- Structural integrity ---")
    print(f"  land+ocean mean:  {chk['land_plus_ocean_mean']:.6f}  (expected 1.0)")
    print(f"  depth overlap px: {chk['depth_mask_overlap_pixels']}")
    print(f"  depth_on_land px: {chk['depth_on_land_pixels']}")

    print()
    print("--- Polar sanity checks ---")
    print(f"  {'Point':<28} {'land':>5} {'ocean':>5} {'ant':>5}  Judgment")
    for name, entry in metrics['polar_sanity_checks'].items():
        print(f"  {name:<28} {entry['land']:>5.3f} {entry['ocean']:>5.3f} "
              f"{entry['antarctica_ice']:>5.3f}  {entry['judgment']}")

    print()
    print("--- Lake / inland water masks ---")
    src = metrics.get('inland_water_source_stats', {})
    print(f"  L2 positive shapes: {src.get('l2_positive_area_shapes','?')} / "
          f"total {src.get('l2_total_shapes','?')} "
          f"(excluded {src.get('l2_negative_area_excluded','?')} river-lake zones)")
    print(f"  L3 shapes: {src.get('l3_total_shapes','?')} total, "
          f"{src.get('l3_with_valid_parent_id','?')} parent_id verified")
    print(f"  {'Mask':<34} {'px':>8}  cov%")
    for key in ['lake_mask_from_GSHHG_L2', 'lake_island_mask',
                'inland_water_mask', 'large_lake_mask']:
        st = metrics.get('inland_water_masks', {}).get(key, {})
        if st:
            print(f"  {key:<34} {st['pixel_count']:>8,}  {st['coverage_ratio']*100:.3f}%")

    print()
    print("--- Terrain / relief masks (B-6.2G-2B-P post-feather domain clip) ---")
    print(f"  {'Mask':<34} {'px':>8}  cov%   ocean∩  iw∩")
    all_terrain_ok = True
    for key in ['high_mountain_mask', 'plateau_refined_mask',
                'lowland_or_basin_proxy', 'hill_or_relief_proxy']:
        st = metrics.get('terrain_masks', {}).get(key, {})
        if st:
            thr_str = ''
            if key in _TERRAIN_THRESHOLDS:
                t = _TERRAIN_THRESHOLDS[key]
                lo = t.get('elev_min_m')
                hi = t.get('elev_max_m')
                if lo and hi:
                    thr_str = f'  [{lo}–{hi}m]'
                elif lo:
                    thr_str = f'  [>{lo}m]'
                elif hi:
                    thr_str = f'  [<={hi}m]'
            oc = st.get('ocean_overlap_pixels', '?')
            iw = st.get('inland_water_overlap_pixels', '?')
            if isinstance(oc, int) and oc > 0:
                all_terrain_ok = False
            if isinstance(iw, int) and iw > 0:
                all_terrain_ok = False
            print(f"  {key:<34} {st['pixel_count']:>8,}  {st['coverage_ratio']*100:.3f}%"
                  f"  {str(oc):>6}  {str(iw):>4}{thr_str}")
    verdict = "PASS" if all_terrain_ok else "FAIL — inspect domain_overlap_px"
    print(f"  terrain ∩ ocean = 0 AND terrain ∩ inland_water = 0: {verdict}")

    print()
    print("--- Major river proxy masks (B-6.2G-3B-R) ---")
    rs = metrics.get('river_source_stats', {})
    print(f"  WDBII tier: {rs.get('wdbii_tier','?')}  L01 baseline + L01+L02 variant")
    print(f"  L01: {rs.get('l01_shape_count','?')} shapes / {rs.get('l01_total_points','?')} pts  "
          f"|  L02: {rs.get('l02_shape_count','?')} shapes / {rs.get('l02_total_points','?')} pts")
    print(f"  Buffer: {rs.get('buffer_structure','?')}  radius={rs.get('buffer_radius_px','?')}px")

    print(f"  {'Mask':<38} {'raw px':>8}  {'post-clip':>9}  ocean∩  iw∩  variant")
    all_river_ok = True
    l01_base = rs.get('l01_baseline', {})
    l012_var  = rs.get('l01_l02_variant', {})
    for key in ['major_river_proxy', 'river_buffer_proxy',
                'major_river_proxy_l01_l02', 'river_buffer_proxy_l01_l02']:
        st = metrics.get('river_masks', {}).get(key, {})
        if st:
            if 'l01_l02' not in key:
                raw_px = l01_base.get('raw_rasterized_px' if 'buffer' not in key
                                      else 'raw_dilated_px', '?')
            else:
                raw_px = l012_var.get('raw_rasterized_px' if 'buffer' not in key
                                      else 'raw_dilated_px', '?')
            oc  = st.get('ocean_overlap_pixels', '?')
            iw  = st.get('inland_water_overlap_pixels', '?')
            var = 'L01' if 'l01_l02' not in key else 'L01+L02'
            if isinstance(oc, int) and oc > 0: all_river_ok = False
            if isinstance(iw, int) and iw > 0: all_river_ok = False
            print(f"  {key:<38} {str(raw_px):>8}  {st['pixel_count']:>9,}  {str(oc):>6}  {str(iw):>4}  {var}")

    verdict = "PASS" if all_river_ok else "FAIL — inspect domain_overlap_px"
    print(f"  river ∩ ocean = 0 AND river ∩ inland_water = 0: {verdict}")

    # Growth ratios (L01+L02 vs L01 baseline)
    l01v  = metrics.get('river_source_stats', {}).get('l01_baseline', {})
    l012v = metrics.get('river_source_stats', {}).get('l01_l02_variant', {})
    if l01v and l012v:
        maj01   = l01v.get('major_river_proxy_px', 1)
        maj012  = l012v.get('major_river_proxy_l01_l02_px', 1)
        buf01   = l01v.get('river_buffer_proxy_px', 1)
        buf012  = l012v.get('river_buffer_proxy_l01_l02_px', 1)
        print(f"  Growth (L01→L01+L02): major ×{maj012/max(maj01,1):.2f}  "
              f"buffer ×{buf012/max(buf01,1):.2f}")

    # Density checks per region
    density = rs.get('density_check', {})
    if density:
        print()
        print("  --- Density check (river_buffer px / land px per region) ---")
        print(f"  {'Region':<14} {'L01':>8} {'L01+L02':>10}  flag")
        for region, d in density.items():
            flag = d.get('flag', '')
            r01  = d.get('density_l01',   0.0)
            r012 = d.get('density_l01l02', 0.0)
            marker = ' <<< OVERDENSE' if flag == 'OVERDENSE' else ''
            print(f"  {region:<14} {r01:>7.1%} {r012:>10.1%}{marker}")

    print()
    print("Next step: B-6.2G-3C-R — validate L01+L02 variant coverage "
          "(Nile / Mississippi / Danube) and density.")


if __name__ == '__main__':
    main()
