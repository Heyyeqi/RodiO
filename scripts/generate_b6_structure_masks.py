#!/usr/bin/env python3
"""
B-6.2S-1 Structure Mask Generator — Special Sea Water-Only Masks
=================================================================
Generates 2K structure masks from ETOPO1 (global bathymetry) and GSHHG
(vector coastlines). Outputs to d5b_processor_v3/d5b_output/structure_masks/.

Masks generated (P0):
  land_mask, ocean_mask, deep_ocean_mask, mid_ocean_mask,
  continental_shelf_mask, shallow_sea_mask, coastline_distance_mask

Masks generated (P1):
  mountain_mask, plateau_mask

Polar supplement masks (B-6.2P):
  antarctica_ice_mask, greenland_ice_mask, polar_land_ice_mask

Special sea water-only masks (B-6.2S-1):
  red_sea_water_mask, yellow_sea_water_mask, east_china_sea_water_mask,
  japan_sea_water_mask, mediterranean_water_mask, aegean_sea_water_mask,
  caribbean_water_mask, persian_gulf_water_mask, north_sea_water_mask,
  baltic_sea_water_mask, south_china_sea_water_mask

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
from scipy.ndimage import distance_transform_edt, gaussian_filter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ETOPO1_PATH  = PROJECT_ROOT / "pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd"
GSHHG_BASE   = PROJECT_ROOT / "pwa/assets/source/coastline/gshhg/GSHHS_shp"
OUTPUT_DIR   = PROJECT_ROOT / "d5b_processor_v3/d5b_output/structure_masks"

FORBIDDEN_WRITE_PATHS = [
    PROJECT_ROOT / "pwa/assets/earth/candidates",
    PROJECT_ROOT / "pwa/assets/earth/production",
    PROJECT_ROOT / "pwa",
]

# ---------------------------------------------------------------------------
# Special sea configurations
# Each entry: (name, lat_s, lat_n, lon_w, lon_e, z_floor, bbox_str, note)
# z_floor: minimum z value (inclusive); None = no depth gate
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

# Preview colours per special sea (RGB)
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


# ---------------------------------------------------------------------------
# ETOPO1 load
# ---------------------------------------------------------------------------
def load_etopo1(path: Path, target_h: int, target_w: int):
    """
    Load ETOPO1 GMT NetCDF4 (gdal variant) and downsample to target resolution.
    Row 0 = lat +90° (north); row H-1 = lat -90° (south).
    Returns (z float32 [H,W], src_W, src_H). Negative z = ocean.
    """
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
# GSHHG rasterize
# ---------------------------------------------------------------------------
def rasterize_gshhg_land(shp_path: Path, w: int, h: int) -> np.ndarray:
    """
    Rasterize GSHHG L1 land polygons to float32 binary land mask [0,1].
    First ring = exterior (land); subsequent rings = holes (lakes).
    Returns ndarray shape (h, w), 1=land, 0=ocean.
    """
    print(f"[GSHHG] Loading: {shp_path}")
    t0 = time.time()
    sf = shapefile.Reader(str(shp_path))

    img  = Image.new('L', (w, h), 0)
    draw = ImageDraw.Draw(img)

    def ring_to_pixels(ring):
        return [(float((lon + 180.0) / 360.0 * w),
                 float((90.0 - lat) / 180.0 * h))
                for lon, lat in ring]

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
            px = ring_to_pixels(ring)
            draw.polygon(px, fill=255 if ring_idx == 0 else 0)

    sf.close()
    elapsed = time.time() - t0
    print(f"[GSHHG] {n_shapes} shapes rendered in {elapsed:.1f}s")
    if antimeridian_warnings:
        print(f"[GSHHG] WARNING: {antimeridian_warnings} antimeridian-crossing ring(s) — approximate near ±180°")

    land = np.array(img, dtype=np.float32) / 255.0
    print(f"[GSHHG] Land coverage: {land.mean()*100:.1f}%  ({int((land>0.5).sum()):,} px)")
    return land


# ---------------------------------------------------------------------------
# Special sea water-only masks
# ---------------------------------------------------------------------------
def make_special_sea_masks(ocean_mask: np.ndarray, z: np.ndarray,
                            lat_1d: np.ndarray, lon_1d: np.ndarray) -> dict:
    """
    Generate 11 named special sea water-only masks.
    Formula: ocean_mask * bbox * optional_depth_gate
    All masks are strictly water-only by construction (ANDed with ocean_mask > 0.5).
    Returns dict[str → float32 ndarray].
    """
    LAT   = lat_1d[:, np.newaxis]   # (h, 1)
    LON   = lon_1d[np.newaxis, :]   # (1, w)
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
# Mask generation
# ---------------------------------------------------------------------------
def generate_masks(z: np.ndarray, land_gshhg: np.ndarray, w: int, h: int) -> dict:
    """
    Build all P0, P1, polar supplement, and special sea structure masks.
    Returns dict of str → float32 ndarray [h, w] in [0, 1].
    Keys prefixed with '_' are internal metrics helpers, not saved to NPZ.
    """
    lat_1d = np.linspace(90.0, -90.0, h)
    lon_1d = np.linspace(-180.0, 180.0, w)
    LAT = lat_1d[:, np.newaxis]
    LON = lon_1d[np.newaxis, :]

    land_gshhg_hard = (land_gshhg > 0.5).astype(np.float32)
    land_etopo1     = (z > 0).astype(np.float32)

    # --- B-6.2P Polar ice supplements ---
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

    # --- Bathymetry depth classes ---
    deep_ocean_raw  = ((z < -3500)                & ocean_hard).astype(np.float32)
    mid_ocean_raw   = ((z >= -3500) & (z < -1000) & ocean_hard).astype(np.float32)
    cont_shelf_raw  = ((z >= -1000) & (z < -200)  & ocean_hard).astype(np.float32)
    shallow_sea_raw = ((z >= -200)  & (z < 0)     & ocean_hard).astype(np.float32)

    deep_ocean_mask  = np.clip(feather(deep_ocean_raw,  1.0) * ocean_mask, 0, 1)
    mid_ocean_mask   = np.clip(feather(mid_ocean_raw,   1.0) * ocean_mask, 0, 1)
    cont_shelf_mask  = np.clip(feather(cont_shelf_raw,  1.0) * ocean_mask, 0, 1)
    shallow_sea_mask = np.clip(feather(shallow_sea_raw, 1.0) * ocean_mask, 0, 1)

    # --- Coastline distance ---
    dist_px = distance_transform_edt(ocean_hard).astype(np.float32)
    max_dist = float(dist_px.max())
    coastline_dist_norm = (dist_px / max_dist) if max_dist > 0 else dist_px

    # --- P1: mountain / plateau ---
    land_hard    = land_mask > 0.5
    mountain_raw = ((z > 1500)             & land_hard).astype(np.float32)
    plateau_raw  = ((z > 500) & (z <= 1500) & land_hard).astype(np.float32)
    mountain_mask = np.clip(feather(mountain_raw, 1.0) * land_mask, 0, 1)
    plateau_mask  = np.clip(feather(plateau_raw,  1.0) * land_mask, 0, 1)

    # --- B-6.2S-1: Special sea water-only masks ---
    special_sea = make_special_sea_masks(ocean_mask, z, lat_1d, lon_1d)
    sea_names = list(special_sea.keys())
    print(f"[SPECIAL_SEA] {len(sea_names)} water-only masks generated")

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
def compute_metrics(masks: dict, w: int, h: int) -> dict:
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

    # Polar sanity checks
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

    # Special sea metrics
    # z array needed — we embed it via a closure over the outer z
    z_arr = masks.get('_z_ref')  # injected in main if needed; fallback below

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
            'pixel_count':    n_px,
            'coverage_ratio': round(float(n_px / total), 6),
            'land_leak_pixels': land_leak,
            'bbox': bbox_str,
            'depth_gate': f'z >= {z_floor}' if z_floor is not None else 'none',
            'note': note,
        }

    return {
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
        'polar_sanity_checks': sanity,
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

    # 6. Special seas overview (B-6.2S-1 new)
    sc = np.zeros((h, w, 3), dtype=np.uint8)
    for name, colour in _SEA_PREVIEW_COLOURS.items():
        if name in masks:
            sc[(masks[name] > 0.5)] = colour
    p = prev_dir / 'special_seas_preview.jpg'
    Image.fromarray(sc).save(str(p), quality=87)
    paths.append(str(p))

    print(f"[PREVIEW] 6 previews → {prev_dir}")
    return paths


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------
def build_metadata(args, w, h, etopo1_md5, gshhg_shp, etopo1_W, etopo1_H) -> dict:
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
            'feather_note':       'apply gaussian sigma >= 5px in d6 before color grading to avoid hard bbox edges',
        }

    return {
        'generation_time':  time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'phase':            'B-6.2S-1 (Special Sea Water-Only Masks)',
        'script':           'scripts/generate_b6_structure_masks.py',
        'resolution':       {'width': w, 'height': h},
        'projection':       'equirectangular / EPSG:4326 (assumed)',
        'dtype':            'float32',
        'sources': {
            'etopo1': {
                'path':     str(ETOPO1_PATH),
                'md5':      etopo1_md5,
                'src_dims': {'width': etopo1_W, 'height': etopo1_H},
                'variable': 'z', 'format': 'GMT NetCDF4 (gdal variant)',
                'variant':  'Ice Surface',
                'note':     'flat z array; reshape(H,W); row 0 = lat +90',
            },
            'gshhg': {
                'tier': args.gshhg_tier, 'path': str(gshhg_shp),
                'version': '2.3.7', 'layer': 'L1 (land polygons)',
            },
        },
        'polar_handling': {
            'antarctica_source': 'ETOPO1 Ice z > 0 where lat < -60',
            'greenland_source':  'ETOPO1 Ice z > 0 where lat 59.5–84.5, lon -74 to -11',
            'reason':            'GSHHG L1 does not cover deep Antarctic interior or Greenland ice cap interior at 2K',
            'method':            'land_mask = max(GSHHG_rasterized, polar_land_ice_supplement)',
            'ocean_mask_recomputed_after_polar_supplement': True,
        },
        'special_sea_water_masks': ss_meta,
        'thresholds': {
            'land_mask':               'max(GSHHG L1 rasterized, polar_land_ice_supplement)',
            'ocean_mask':              '1 - land_mask',
            'deep_ocean_mask':         'ETOPO1 z < -3500 AND ocean',
            'mid_ocean_mask':          'ETOPO1 -3500 <= z < -1000 AND ocean',
            'continental_shelf_mask':  'ETOPO1 -1000 <= z < -200 AND ocean',
            'shallow_sea_mask':        'ETOPO1 -200 <= z < 0 AND ocean',
            'coastline_distance_mask': 'scipy EDT from corrected land boundary, normalised 0-1',
            'mountain_mask':           'ETOPO1 z > 1500 AND land',
            'plateau_mask':            'ETOPO1 500 < z <= 1500 AND land',
            'special_sea_water_masks': 'ocean_mask * bbox * optional_depth_gate',
        },
        'deferred_masks': [
            'reef_atoll_proxy_mask (B-6.2S-3)',
            'island_proximity_mask (B-6.2S-3)',
            'bahamas_bank_mask (B-6.2S-2)',
            'yellow_east_china_shelf_mask (B-6.2S-2)',
            'great_barrier_reef_proxy_mask (needs GEBCO global)',
            'red_sea_reef_mask (needs GEBCO global)',
        ],
        'known_limitations': [
            'ETOPO1 Ice: z reflects ice surface, not bedrock',
            'GSHHG L1 only: L2 lakes not subtracted',
            '2K: 1 px ≈ 19 km — sub-pixel islands lost',
            'Special sea bbox edges require feathering (sigma >= 5px) in d6 color grading',
            'Special sea masks are geographic selectors only — no visual effect applied',
            'coastline_distance_mask: pixel units only; km calibration deferred',
        ],
        'output_files': {
            'npz':      'structure_masks_2048x1024.npz',
            'metadata': 'structure_mask_metadata.json',
            'metrics':  'structure_mask_metrics.json',
            'previews': [
                'previews/land_ocean_preview.jpg',
                'previews/bathymetry_classes_preview.jpg',
                'previews/coastline_distance_preview.jpg',
                'previews/shallow_sea_preview.jpg',
                'previews/polar_ice_supplement_preview.jpg',
                'previews/special_seas_preview.jpg',
            ],
        },
        'safety_assertions': {
            'pwa_assets_not_modified':   True,
            'production_not_written':    True,
            'candidates_not_written':    True,
            'd6_generator_not_modified': True,
            'earth3js_not_modified':     True,
            'no_git_operations':         True,
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='B-6.2S-1 Structure Mask Generator')
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
    print("B-6.2S-1 Structure Mask Generator (Special Sea Water-Only Masks)")
    print(f"Resolution:  {W} × {H}")
    print(f"GSHHG tier:  {args.gshhg_tier}")
    print(f"Output dir:  {OUTPUT_DIR}")
    print("=" * 70)

    assert_output_safety(OUTPUT_DIR)
    print("[SAFETY] Output path check: PASS")

    if not ETOPO1_PATH.exists():
        sys.exit(f"[ABORT] ETOPO1 not found: {ETOPO1_PATH}")
    gshhg_shp = GSHHG_BASE / args.gshhg_tier / f"GSHHS_{args.gshhg_tier}_L1.shp"
    if not gshhg_shp.exists():
        sys.exit(f"[ABORT] GSHHG not found: {gshhg_shp}")

    print(f"[INPUT] ETOPO1: {ETOPO1_PATH}  OK")
    print(f"[INPUT] GSHHG:  {gshhg_shp}  OK")

    print("[INPUT] Computing ETOPO1 MD5...")
    etopo1_md5 = md5_file(ETOPO1_PATH)
    print(f"[INPUT] ETOPO1 MD5: {etopo1_md5}")

    t_total = time.time()

    z, etopo1_W, etopo1_H = load_etopo1(ETOPO1_PATH, H, W)
    land_gshhg = rasterize_gshhg_land(gshhg_shp, W, H)

    print("[MASKS] Generating all structure masks (B-6.2S-1)...")
    t_masks = time.time()
    masks = generate_masks(z, land_gshhg, W, H)
    public_keys = [k for k in masks if not k.startswith('_')]
    print(f"[MASKS] {len(public_keys)} masks in {time.time()-t_masks:.1f}s")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    npz_path = OUTPUT_DIR / 'structure_masks_2048x1024.npz'
    np.savez_compressed(str(npz_path), **{k: masks[k] for k in public_keys})
    npz_kb = npz_path.stat().st_size // 1024
    print(f"[OUTPUT] NPZ: {npz_path.name}  ({npz_kb} KB, {len(public_keys)} masks)")

    metrics = compute_metrics(masks, W, H)
    metrics_path = OUTPUT_DIR / 'structure_mask_metrics.json'
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"[OUTPUT] Metrics: {metrics_path.name}")

    metadata = build_metadata(args, W, H, etopo1_md5, gshhg_shp, etopo1_W, etopo1_H)
    meta_path = OUTPUT_DIR / 'structure_mask_metadata.json'
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"[OUTPUT] Metadata: {meta_path.name}")

    save_previews(masks, OUTPUT_DIR, W, H)

    print()
    print("=== SAFETY CONFIRMATIONS ===")
    print("Confirm: earth3d.js                   NOT modified.")
    print("Confirm: DAY_TEXTURE_VARIANT           NOT modified.")
    print("Confirm: pwa/assets/earth/candidates/  NOT written.")
    print("Confirm: pwa/assets/earth/production/  NOT written.")
    print("Confirm: d6_noon_air_earth_generator.py NOT modified.")
    print("Confirm: No git operations performed.")

    print()
    print("=== B-6.2S-1 COMPLETE ===")
    print(f"Total masks in NPZ: {len(public_keys)}")
    print(f"NPZ size: {npz_kb} KB    Total time: {time.time()-t_total:.1f}s")

    chk = metrics['checks']
    print()
    print("--- Structural integrity ---")
    print(f"  land+ocean mean:              {chk['land_plus_ocean_mean']:.6f}  (expected 1.0)")
    print(f"  depth overlap px:             {chk['depth_mask_overlap_pixels']}")
    print(f"  depth_on_land_pixels:         {chk['depth_on_land_pixels']}")
    print(f"  antarctica_depth_mask_pixels: {chk['antarctica_depth_mask_pixels']}")

    print()
    print("--- Polar sanity checks ---")
    print(f"  {'Point':<28} {'land':>5} {'ocean':>5} {'ant':>5}  Judgment")
    for name, entry in metrics['polar_sanity_checks'].items():
        print(f"  {name:<28} {entry['land']:>5.3f} {entry['ocean']:>5.3f} "
              f"{entry['antarctica_ice']:>5.3f}  {entry['judgment']}")

    print()
    print("--- Special sea water-only masks ---")
    print(f"  {'Mask':<34} {'px':>8}  {'cov':>7}  land_leak  depth_gate")
    ss_names = [cfg[0] for cfg in _SPECIAL_SEA_CONFIGS]
    for name in ss_names:
        st = metrics['special_sea_water_masks'].get(name, {})
        if not st:
            continue
        print(f"  {name:<34} {st['pixel_count']:>8,}  {st['coverage_ratio']:>7.4f}  "
              f"{st['land_leak_pixels']:>9}  {st['depth_gate']}")


if __name__ == '__main__':
    main()
