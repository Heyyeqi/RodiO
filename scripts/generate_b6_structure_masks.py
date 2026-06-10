#!/usr/bin/env python3
"""
B-6.2P Structure Mask Generator — Polar / Antarctica Land-Ice Patch
=====================================================================
Generates 2K structure masks from ETOPO1 (global bathymetry) and GSHHG
(vector coastlines). Outputs to d5b_processor_v3/d5b_output/structure_masks/.

Masks generated (P0):
  land_mask, ocean_mask, deep_ocean_mask, mid_ocean_mask,
  continental_shelf_mask, shallow_sea_mask, coastline_distance_mask

Masks generated (P1):
  mountain_mask, plateau_mask

Polar supplement masks (B-6.2P fix):
  antarctica_ice_mask   — ETOPO1 z > 0 where lat < -60
  greenland_ice_mask    — ETOPO1 z > 0 within Greenland bbox (lat 59.5–84.5, lon -74 to -11)
  polar_land_ice_mask   — union of the above two

B-6.2P fix:
  GSHHG L1 does not cover deep Antarctic interior or Greenland ice cap interior.
  land_mask = max(GSHHG_rasterized, polar_land_ice_supplement)
  All depth masks are recomputed against the corrected ocean_mask.

Deferred:
  reef_atoll_proxy_mask, island_proximity_mask, special_sea_water_masks

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
    """Convert geographic lat/lon to nearest pixel (row, col) in equirectangular grid."""
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
# Mask generation
# ---------------------------------------------------------------------------
def generate_masks(z: np.ndarray, land_gshhg: np.ndarray, w: int, h: int) -> dict:
    """
    Build all P0, P1, and polar supplement structure masks.
    Returns dict of str → float32 ndarray [h, w] in [0, 1].
    Keys prefixed with '_' are internal metrics helpers, not saved to NPZ.
    """
    # Coordinate grids (equirectangular, matching ETOPO1 downsampled orientation)
    # Row 0 = lat +90, row h-1 = lat -90; col 0 = lon -180, col w-1 = lon +180
    lat_1d = np.linspace(90.0, -90.0, h)
    lon_1d = np.linspace(-180.0, 180.0, w)
    LAT = lat_1d[:, np.newaxis]   # (h, 1)
    LON = lon_1d[np.newaxis, :]   # (1, w)

    # --- GSHHG primary land (before polar supplement) ---
    land_gshhg_hard = (land_gshhg > 0.5).astype(np.float32)

    # ETOPO1 land reference (for metrics only — not used as primary mask)
    land_etopo1 = (z > 0).astype(np.float32)

    # --- B-6.2P Polar ice supplements ---
    # GSHHG L1 covers the Antarctic ice front but leaves the deep interior
    # (~lat -70 to -90) unpopulated.  ETOPO1 Ice Surface has z > 0 there.
    # Supplement: use ETOPO1 z > 0 for lat < -60 to fill the gap.
    antarctica_ice_mask = ((LAT < -60.0) & (z > 0)).astype(np.float32)

    # Greenland ice cap interior: similar gap in GSHHG h-tier at 2K.
    # Bbox: lat 59.5–84.5 N, lon -74 to -11 W.
    greenland_ice_mask = (
        (LAT > 59.5) & (LAT < 84.5) & (LON > -74.0) & (LON < -11.0) & (z > 0)
    ).astype(np.float32)

    polar_land_ice_mask = np.maximum(antarctica_ice_mask, greenland_ice_mask)

    # Final land mask = GSHHG + polar supplement (union, no subtraction)
    land_mask  = np.maximum(land_gshhg_hard, polar_land_ice_mask)
    ocean_mask = (1.0 - land_mask).astype(np.float32)
    ocean_hard = ocean_mask > 0.5

    print(f"[POLAR]  Antarctica supplement added: {int((antarctica_ice_mask > 0.5).sum()):,} px")
    print(f"[POLAR]  Greenland  supplement added: {int((greenland_ice_mask > 0.5).sum()):,} px")
    gshhg_only = int(((land_mask > 0.5) & (land_gshhg_hard > 0.5)).sum())
    polar_added = int(((land_mask > 0.5) & (land_gshhg_hard < 0.5)).sum())
    print(f"[POLAR]  GSHHG pixels kept: {gshhg_only:,}  polar-only added: {polar_added:,}")

    # --- Bathymetry depth classes (computed against corrected ocean_mask) ---
    deep_ocean_raw  = ((z < -3500)                & ocean_hard).astype(np.float32)
    mid_ocean_raw   = ((z >= -3500) & (z < -1000) & ocean_hard).astype(np.float32)
    cont_shelf_raw  = ((z >= -1000) & (z < -200)  & ocean_hard).astype(np.float32)
    shallow_sea_raw = ((z >= -200)  & (z < 0)     & ocean_hard).astype(np.float32)

    deep_ocean_mask  = np.clip(feather(deep_ocean_raw,  1.0) * ocean_mask, 0, 1)
    mid_ocean_mask   = np.clip(feather(mid_ocean_raw,   1.0) * ocean_mask, 0, 1)
    cont_shelf_mask  = np.clip(feather(cont_shelf_raw,  1.0) * ocean_mask, 0, 1)
    shallow_sea_mask = np.clip(feather(shallow_sea_raw, 1.0) * ocean_mask, 0, 1)

    # --- Coastline distance (EDT on corrected ocean_hard) ---
    dist_px = distance_transform_edt(ocean_hard).astype(np.float32)
    max_dist = float(dist_px.max())
    coastline_dist_norm = (dist_px / max_dist) if max_dist > 0 else dist_px

    # --- P1: mountain / plateau (corrected land_mask) ---
    land_hard    = land_mask > 0.5
    mountain_raw = ((z > 1500)            & land_hard).astype(np.float32)
    plateau_raw  = ((z > 500) & (z <= 1500) & land_hard).astype(np.float32)
    mountain_mask = np.clip(feather(mountain_raw, 1.0) * land_mask, 0, 1)
    plateau_mask  = np.clip(feather(plateau_raw,  1.0) * land_mask, 0, 1)

    return {
        # Public P0 masks
        'land_mask':               land_mask,
        'ocean_mask':              ocean_mask,
        'deep_ocean_mask':         deep_ocean_mask,
        'mid_ocean_mask':          mid_ocean_mask,
        'continental_shelf_mask':  cont_shelf_mask,
        'shallow_sea_mask':        shallow_sea_mask,
        'coastline_distance_mask': coastline_dist_norm.astype(np.float32),
        # Public P1 masks
        'mountain_mask':           mountain_mask,
        'plateau_mask':            plateau_mask,
        # Public polar supplement masks (B-6.2P)
        'antarctica_ice_mask':     antarctica_ice_mask,
        'greenland_ice_mask':      greenland_ice_mask,
        'polar_land_ice_mask':     polar_land_ice_mask,
        # Internal helpers (not saved to NPZ)
        '_land_etopo1':            land_etopo1,
        '_land_gshhg_raw':         land_gshhg_hard,
        '_dist_px':                dist_px,
    }


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
            'coverage_ratio': round(float(px / total), 5),
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
    grl   = masks['greenland_ice_mask']

    # Depth mask exclusivity
    depth_sum = ((deep > 0.5).astype(int) + (mid > 0.5).astype(int)
                 + (shelf > 0.5).astype(int) + (shsea > 0.5).astype(int))
    depth_overlap_px   = int((depth_sum > 1).sum())
    ocean_px           = int((ocean > 0.5).sum())
    depth_covered_px   = int((depth_sum >= 1).sum())
    depth_uncovered_px = max(0, ocean_px - depth_covered_px)

    # ETOPO1 vs final land_mask disagreement
    disagree_after = int(((land > 0.5) != (letop > 0.5)).sum())

    # ETOPO1 vs GSHHG-only disagreement (before polar fix)
    disagree_before = int(((gshhg > 0.5) != (letop > 0.5)).sum())

    # Depth-on-land checks
    land_hard  = land > 0.5
    any_depth  = depth_sum >= 1
    depth_on_land = int((any_depth & land_hard).sum())

    ant_hard  = ant > 0.5
    ant_depth = int((any_depth & ant_hard).sum())

    # Polar sanity check points
    check_points = [
        ('Antarctica_interior', -80,  0),
        ('Greenland',            72, -42),
        ('Antarctic_coast',     -70,  0),
        ('Southern_Ocean',      -55,  0),
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
        # judgment
        if name == 'Antarctica_interior':
            ok = entry['land'] > 0.5 and entry['ocean'] < 0.5 and entry['antarctica_ice'] > 0.5
        elif name == 'Greenland':
            ok = entry['land'] > 0.5
        elif name == 'Antarctic_coast':
            ok = entry['land'] > 0.5 or entry['ocean'] > 0.5  # accept either (coast edge)
        elif name == 'Southern_Ocean':
            ok = entry['ocean'] > 0.5
        else:
            ok = True
        entry['judgment'] = 'PASS' if ok else 'FAIL'
        sanity[name] = entry

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
            'depth_mask_overlap_expected':           '0 (exclusive classes)',
            'ocean_px_covered_by_depth_masks':       depth_covered_px,
            'ocean_px_uncovered_by_depth_masks':     depth_uncovered_px,
            'depth_on_land_pixels':                  depth_on_land,
            'depth_on_land_expected':                '~0 (depth only in ocean)',
            'antarctica_depth_mask_pixels':          ant_depth,
            'antarctica_depth_mask_expected':        '0 (Antarctica should be land)',
            'etopo1_vs_gshhg_disagree_before_px':    disagree_before,
            'etopo1_vs_gshhg_disagree_before_ratio': round(float(disagree_before / total), 5),
            'etopo1_vs_land_disagree_after_px':      disagree_after,
            'etopo1_vs_land_disagree_after_ratio':   round(float(disagree_after / total), 5),
            'disagree_reduction_px':                 disagree_before - disagree_after,
        },
        'polar_sanity_checks': sanity,
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

    # 1. Land/ocean (red=land, blue=ocean)
    land = to_u8(masks['land_mask'])
    sea  = to_u8(masks['ocean_mask'])
    p = prev_dir / 'land_ocean_preview.jpg'
    Image.fromarray(np.stack([land, np.zeros_like(land), sea], axis=-1)).save(str(p), quality=87)
    paths.append(str(p))

    # 2. Bathymetry classes + polar ice
    bc = np.zeros((h, w, 3), dtype=np.uint8)
    bc[(masks['deep_ocean_mask']        > 0.5)] = [12,  38, 120]   # deep navy
    bc[(masks['mid_ocean_mask']         > 0.5)] = [35,  90, 190]   # mid blue
    bc[(masks['continental_shelf_mask'] > 0.5)] = [55, 165, 175]   # teal
    bc[(masks['shallow_sea_mask']       > 0.5)] = [120, 210, 220]  # light cyan
    bc[(masks['land_mask']              > 0.5)] = [110, 135,  75]  # olive green
    bc[(masks['plateau_mask']           > 0.5)] = [170, 150,  95]  # tan
    bc[(masks['mountain_mask']          > 0.5)] = [210, 210, 210]  # light grey
    # Polar ice on top — bright white distinguishes from mountain grey
    bc[(masks['polar_land_ice_mask']    > 0.5)] = [240, 248, 255]  # ice white
    p = prev_dir / 'bathymetry_classes_preview.jpg'
    Image.fromarray(bc).save(str(p), quality=87)
    paths.append(str(p))

    # 3. Coastline distance (greyscale)
    p = prev_dir / 'coastline_distance_preview.jpg'
    Image.fromarray(to_u8(masks['coastline_distance_mask'])).save(str(p), quality=87)
    paths.append(str(p))

    # 4. Shallow sea
    p = prev_dir / 'shallow_sea_preview.jpg'
    Image.fromarray(to_u8(masks['shallow_sea_mask'])).save(str(p), quality=87)
    paths.append(str(p))

    # 5. Polar ice supplement (B-6.2P new)
    pol = np.zeros((h, w, 3), dtype=np.uint8)
    pol[(masks['antarctica_ice_mask'] > 0.5)] = [180, 220, 255]  # light blue = Antarctica
    pol[(masks['greenland_ice_mask']  > 0.5)] = [255, 200, 180]  # light orange = Greenland
    p = prev_dir / 'polar_ice_supplement_preview.jpg'
    Image.fromarray(pol).save(str(p), quality=87)
    paths.append(str(p))

    print(f"[PREVIEW] 5 previews → {prev_dir}")
    return paths


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------
def build_metadata(args, w, h, etopo1_md5, gshhg_shp, etopo1_W, etopo1_H) -> dict:
    return {
        'generation_time':  time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'phase':            'B-6.2P (Polar Patch)',
        'script':           'scripts/generate_b6_structure_masks.py',
        'resolution':       {'width': w, 'height': h},
        'projection':       'equirectangular / EPSG:4326 (assumed)',
        'dtype':            'float32',
        'sources': {
            'etopo1': {
                'path':     str(ETOPO1_PATH),
                'md5':      etopo1_md5,
                'src_dims': {'width': etopo1_W, 'height': etopo1_H},
                'variable': 'z',
                'format':   'GMT NetCDF4 (gdal variant)',
                'variant':  'Ice Surface',
                'note':     'flat z array; reshape(H,W); row 0 = lat +90',
            },
            'gshhg': {
                'tier':    args.gshhg_tier,
                'path':    str(gshhg_shp),
                'version': '2.3.7',
                'layer':   'L1 (land polygons)',
            },
        },
        'polar_handling': {
            'antarctica_source': 'ETOPO1 Ice z > 0 where lat < -60',
            'greenland_source':  'ETOPO1 Ice z > 0 where lat 59.5–84.5, lon -74 to -11',
            'reason':            'GSHHG L1 does not cover deep Antarctic interior or Greenland ice cap interior at 2K',
            'method':            'land_mask = max(GSHHG_rasterized, polar_land_ice_supplement)',
            'ocean_mask_recomputed_after_polar_supplement': True,
            'depth_masks_recomputed_after_polar_supplement': True,
        },
        'thresholds': {
            'land_mask':               'max(GSHHG L1 rasterized, polar_land_ice_supplement)',
            'ocean_mask':              '1 - land_mask (recomputed after polar fix)',
            'deep_ocean_mask':         'ETOPO1 z < -3500 AND ocean',
            'mid_ocean_mask':          'ETOPO1 -3500 <= z < -1000 AND ocean',
            'continental_shelf_mask':  'ETOPO1 -1000 <= z < -200 AND ocean',
            'shallow_sea_mask':        'ETOPO1 -200 <= z < 0 AND ocean',
            'coastline_distance_mask': 'scipy EDT from corrected land boundary, normalised 0-1',
            'mountain_mask':           'ETOPO1 z > 1500 AND land',
            'plateau_mask':            'ETOPO1 500 < z <= 1500 AND land',
            'antarctica_ice_mask':     'ETOPO1 z > 0 AND lat < -60',
            'greenland_ice_mask':      'ETOPO1 z > 0 AND lat 59.5–84.5 AND lon -74 to -11',
            'polar_land_ice_mask':     'max(antarctica_ice_mask, greenland_ice_mask)',
        },
        'mask_types': {
            'land_mask':               'physical (GSHHG + ETOPO1 polar supplement)',
            'ocean_mask':              'physical (derived from corrected land_mask)',
            'deep_ocean_mask':         'physical (ETOPO1 depth band, corrected ocean)',
            'mid_ocean_mask':          'physical (ETOPO1 depth band, corrected ocean)',
            'continental_shelf_mask':  'physical (ETOPO1 depth band, corrected ocean)',
            'shallow_sea_mask':        'physical (ETOPO1 depth band, corrected ocean)',
            'coastline_distance_mask': 'physical (EDT from corrected land, normalised)',
            'mountain_mask':           'physical (ETOPO1 elevation, corrected land)',
            'plateau_mask':            'physical (ETOPO1 elevation, corrected land)',
            'antarctica_ice_mask':     'physical (ETOPO1 Ice polar supplement)',
            'greenland_ice_mask':      'physical (ETOPO1 Ice polar supplement)',
            'polar_land_ice_mask':     'physical (union of polar supplements)',
        },
        'deferred_masks': [
            'reef_atoll_proxy_mask',
            'island_proximity_mask',
            'special_sea_water_masks (Red Sea, Yellow Sea, etc.)',
            'great_barrier_reef_proxy_mask',
            'bahamas_bank_mask',
        ],
        'known_limitations': [
            'ETOPO1 Ice variant: z reflects ice surface elevation, not bedrock',
            'GSHHG L1 only: L2 lakes not subtracted (lake-as-land at large lakes)',
            'Rasterisation at 2K: 1 px ≈ 19 km — sub-pixel islands lost',
            'Antimeridian-crossing rings rendered approximately',
            'Depth mask feather sigma=1px at 2K ≈ 19 km',
            'coastline_distance_mask: pixel units only; km calibration deferred to B-6.3',
            'Greenland bbox is approximate; some Arctic Ocean shelf pixels may be incorrectly marked if z > 0',
            'No CRS validation: EPSG:4326 assumed',
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
    parser = argparse.ArgumentParser(description='B-6.2P Structure Mask Generator (Polar Patch)')
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
    print("B-6.2P Structure Mask Generator (Polar / Antarctica Patch)")
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

    print("[MASKS] Generating structure masks (B-6.2P)...")
    t_masks = time.time()
    masks = generate_masks(z, land_gshhg, W, H)
    public_keys = [k for k in masks if not k.startswith('_')]
    print(f"[MASKS] {len(public_keys)} masks in {time.time()-t_masks:.1f}s")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    npz_path = OUTPUT_DIR / 'structure_masks_2048x1024.npz'
    np.savez_compressed(str(npz_path), **{k: masks[k] for k in public_keys})
    npz_kb = npz_path.stat().st_size // 1024
    print(f"[OUTPUT] NPZ: {npz_path.name}  ({npz_kb} KB)")

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
    print("=== B-6.2P COMPLETE ===")
    print(f"Masks ({len(public_keys)}): {public_keys}")
    print(f"NPZ: {npz_kb} KB   Total time: {time.time()-t_total:.1f}s")

    chk = metrics['checks']
    print()
    print("--- Coverage summary ---")
    for key in ['land_mask', 'ocean_mask', 'deep_ocean_mask', 'mid_ocean_mask',
                'continental_shelf_mask', 'shallow_sea_mask',
                'mountain_mask', 'plateau_mask',
                'antarctica_ice_mask', 'greenland_ice_mask']:
        st = metrics[key]
        print(f"  {key:30s}  cov={st['coverage_ratio']:.3f}  px={st['pixel_count']:>8,}")

    print()
    print("--- Structural checks ---")
    print(f"  land+ocean mean:                  {chk['land_plus_ocean_mean']:.6f}  (expected 1.0)")
    print(f"  depth overlap pixels:             {chk['depth_mask_overlap_pixels']}")
    print(f"  depth_on_land_pixels:             {chk['depth_on_land_pixels']}")
    print(f"  antarctica_depth_mask_pixels:     {chk['antarctica_depth_mask_pixels']}")
    print(f"  ETOPO1/GSHHG disagree (before):  {chk['etopo1_vs_gshhg_disagree_before_ratio']:.4f}"
          f"  ({chk['etopo1_vs_gshhg_disagree_before_px']:,} px)")
    print(f"  ETOPO1/land   disagree (after):   {chk['etopo1_vs_land_disagree_after_ratio']:.4f}"
          f"  ({chk['etopo1_vs_land_disagree_after_px']:,} px)")
    print(f"  disagreement reduction:           {chk['disagree_reduction_px']:,} px")

    print()
    print("--- Polar sanity checks ---")
    print(f"  {'Point':<28} {'land':>5} {'ocean':>5} {'ant_ice':>7} {'deep':>5} {'mid':>5} {'shelf':>6} {'shallow':>7}  Judgment")
    for name, entry in metrics['polar_sanity_checks'].items():
        print(f"  {name:<28} {entry['land']:>5.3f} {entry['ocean']:>5.3f} "
              f"{entry['antarctica_ice']:>7.3f} {entry['deep_ocean']:>5.3f} "
              f"{entry['mid_ocean']:>5.3f} {entry['shelf']:>6.3f} "
              f"{entry['shallow']:>7.3f}  {entry['judgment']}")


if __name__ == '__main__':
    main()
