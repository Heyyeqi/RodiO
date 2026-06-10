#!/usr/bin/env python3
"""
B-6.2 Structure Mask Prototype Generator
=========================================
Generates 2K structure masks from ETOPO1 (global bathymetry) and GSHHG
(vector coastlines). Outputs to d5b_processor_v3/d5b_output/structure_masks/.

Masks generated (P0):
  land_mask, ocean_mask, deep_ocean_mask, mid_ocean_mask,
  continental_shelf_mask, shallow_sea_mask, coastline_distance_mask

Masks generated (P1, low-cost):
  mountain_mask, plateau_mask

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
import os
import sys
import time
import warnings
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

# Paths that must never be written to
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
            pass  # not a sub-path, OK


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


# ---------------------------------------------------------------------------
# ETOPO1 load
# ---------------------------------------------------------------------------
def load_etopo1(path: Path, target_h: int, target_w: int):
    """
    Load ETOPO1 GMT NetCDF4 (gdal variant) and downsample to target resolution.
    Returns (z: float32 ndarray [H,W], src_W, src_H).
    Negative z = ocean, positive z = land/ice. Units: meters.
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

    # Nearest-neighbour downsample via index mapping
    ri = np.round(np.linspace(0, H_src - 1, target_h)).astype(int)
    ci = np.round(np.linspace(0, W_src - 1, target_w)).astype(int)
    z = z_raw[np.ix_(ri, ci)]
    del z_raw  # free ~880 MB
    print(f"[ETOPO1] Downsampled to {target_w}×{target_h}, z=[{z.min():.0f}, {z.max():.0f}] m")
    return z, W_src, H_src


# ---------------------------------------------------------------------------
# GSHHG rasterize
# ---------------------------------------------------------------------------
def rasterize_gshhg_land(shp_path: Path, w: int, h: int) -> np.ndarray:
    """
    Rasterize GSHHG L1 land polygons to a float32 binary land mask [0,1].
    Uses PIL.ImageDraw fill (exterior ring) then erases holes (inner rings).
    Antimeridian-crossing rings emit a warning but are rendered approximately.
    Returns ndarray shape (h, w) float32, 1=land, 0=ocean.
    """
    print(f"[GSHHG] Loading: {shp_path}")
    t0 = time.time()
    sf = shapefile.Reader(str(shp_path))

    img  = Image.new('L', (w, h), 0)  # start: all ocean
    draw = ImageDraw.Draw(img)

    def ring_to_pixels(ring):
        return [(float((lon + 180.0) / 360.0 * w),
                 float((90.0 - lat) / 180.0 * h))
                for lon, lat in ring]

    antimeridian_warnings = 0
    n_shapes = 0
    n_rings  = 0

    for shape in sf.iterShapes():
        pts   = shape.points
        parts = list(shape.parts) + [len(pts)]
        n_shapes += 1

        # First ring = exterior (fill white = land)
        # Subsequent rings = holes (erase = ocean within land body)
        for ring_idx in range(len(parts) - 1):
            ring = pts[parts[ring_idx]:parts[ring_idx + 1]]
            if len(ring) < 3:
                continue
            n_rings += 1

            # Check for antimeridian crossing (consecutive lon diff > 180°)
            lons = [p[0] for p in ring]
            crossing = any(abs(lons[i+1] - lons[i]) > 180 for i in range(len(lons) - 1))
            if crossing:
                antimeridian_warnings += 1

            px = ring_to_pixels(ring)
            if ring_idx == 0:
                draw.polygon(px, fill=255)      # exterior → land
            else:
                draw.polygon(px, fill=0)        # hole → ocean (lake inside landmass)

    sf.close()
    elapsed = time.time() - t0
    print(f"[GSHHG] {n_shapes} shapes, {n_rings} rings rendered in {elapsed:.1f}s")
    if antimeridian_warnings > 0:
        print(f"[GSHHG] WARNING: {antimeridian_warnings} antimeridian-crossing ring(s) "
              f"— approximate rendering near ±180° (documented limitation)")

    land = np.array(img, dtype=np.float32) / 255.0
    land_px = int((land > 0.5).sum())
    print(f"[GSHHG] Land coverage: {land.mean()*100:.1f}%  ({land_px:,} / {w*h:,} px)")
    return land


# ---------------------------------------------------------------------------
# Mask generation
# ---------------------------------------------------------------------------
def generate_masks(z: np.ndarray, land_gshhg: np.ndarray, w: int, h: int) -> dict:
    """
    Build all P0 and P1 structure masks.
    Returns dict of str → float32 ndarray [h, w] in [0, 1].
    Keys prefixed with '_' are internal metrics helpers, not public outputs.
    """
    # --- land / ocean (GSHHG primary, ETOPO1 for reference) ---
    land_mask  = (land_gshhg > 0.5).astype(np.float32)
    ocean_mask = 1.0 - land_mask

    land_etopo1  = (z > 0).astype(np.float32)  # reference only
    ocean_etopo1 = 1.0 - land_etopo1

    # --- bathymetry depth classes (ETOPO1 z, applied only within ocean_mask) ---
    ocean_hard = ocean_mask > 0.5

    deep_ocean_raw  = ((z < -3500)              & ocean_hard).astype(np.float32)
    mid_ocean_raw   = ((z >= -3500) & (z < -1000) & ocean_hard).astype(np.float32)
    cont_shelf_raw  = ((z >= -1000) & (z < -200)  & ocean_hard).astype(np.float32)
    shallow_sea_raw = ((z >= -200)  & (z < 0)     & ocean_hard).astype(np.float32)

    # Gentle 1px Gaussian feather; re-clamp to ocean to prevent land bleed
    deep_ocean_mask  = np.clip(feather(deep_ocean_raw,  1.0) * ocean_mask, 0, 1)
    mid_ocean_mask   = np.clip(feather(mid_ocean_raw,   1.0) * ocean_mask, 0, 1)
    cont_shelf_mask  = np.clip(feather(cont_shelf_raw,  1.0) * ocean_mask, 0, 1)
    shallow_sea_mask = np.clip(feather(shallow_sea_raw, 1.0) * ocean_mask, 0, 1)

    # --- coastline distance (EDT from GSHHG land, ocean pixels only) ---
    # distance_transform_edt: each foreground (non-zero) pixel gets its distance
    # to nearest background (zero) pixel.  With ocean_hard as input:
    #   ocean px (1) → distance to nearest land px (0) = coastline distance [px]
    #   land px  (0) → 0
    dist_px = distance_transform_edt(ocean_hard).astype(np.float32)
    max_dist = float(dist_px.max())
    coastline_dist_norm = (dist_px / max_dist) if max_dist > 0 else dist_px

    # --- P1: mountain / plateau (ETOPO1 elevation, land only) ---
    land_hard   = land_mask > 0.5
    mountain_raw = ((z > 1500)           & land_hard).astype(np.float32)
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
        # Internal metrics helpers (not saved to NPZ)
        '_land_etopo1':            land_etopo1,
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
    cdist = masks['coastline_distance_mask']
    mtn   = masks['mountain_mask']
    plt   = masks['plateau_mask']
    letop = masks['_land_etopo1']
    dpx   = masks['_dist_px']

    # Overlap: depth mask exclusivity
    depth_sum = ((deep > 0.5).astype(int) + (mid > 0.5).astype(int)
                 + (shelf > 0.5).astype(int) + (shsea > 0.5).astype(int))
    depth_overlap_px  = int((depth_sum > 1).sum())
    ocean_px          = int((ocean > 0.5).sum())
    depth_covered_px  = int((depth_sum >= 1).sum())
    depth_uncovered_px = max(0, ocean_px - depth_covered_px)

    # ETOPO1 vs GSHHG land disagreement
    disagree = int(((land > 0.5) != (letop > 0.5)).sum())

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
        'checks': {
            'land_plus_ocean_mean':             round(float((land + ocean).mean()), 6),
            'land_plus_ocean_expected':         '1.0',
            'depth_mask_overlap_pixels':        depth_overlap_px,
            'depth_mask_overlap_expected':      '0 (exclusive classes)',
            'ocean_px_covered_by_depth_masks':  depth_covered_px,
            'ocean_px_uncovered_by_depth_masks': depth_uncovered_px,
            'etopo1_vs_gshhg_land_disagree_px': disagree,
            'etopo1_vs_gshhg_land_disagree_ratio': round(float(disagree / total), 5),
        },
        'coastline_distance_px_raw': {
            'min':  round(float(dpx.min()), 2),
            'max':  round(float(dpx.max()), 2),
            'mean': round(float(dpx.mean()), 2),
            'note': 'pixel units only; km calibration deferred to B-6.3',
        },
        'land_coverage': {
            'gshhg_ratio':  round(float((land > 0.5).mean()), 5),
            'etopo1_ratio': round(float((letop > 0.5).mean()), 5),
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

    # 1. Land/ocean overview: red=land, blue=ocean
    land  = to_u8(masks['land_mask'])
    sea   = to_u8(masks['ocean_mask'])
    lo_rgb = np.stack([land, np.zeros_like(land), sea], axis=-1)
    p = prev_dir / 'land_ocean_preview.jpg'
    Image.fromarray(lo_rgb).save(str(p), quality=87)
    paths.append(str(p))

    # 2. Bathymetry classes (colour-coded)
    bc = np.zeros((h, w, 3), dtype=np.uint8)
    bc[(masks['deep_ocean_mask']         > 0.5)] = [12,  38, 120]   # deep: dark navy
    bc[(masks['mid_ocean_mask']          > 0.5)] = [35,  90, 190]   # mid: medium blue
    bc[(masks['continental_shelf_mask']  > 0.5)] = [55, 165, 175]   # shelf: teal
    bc[(masks['shallow_sea_mask']        > 0.5)] = [120, 210, 220]  # shallow: light cyan
    bc[(masks['land_mask']               > 0.5)] = [110, 135, 75]   # land: olive green
    bc[(masks['plateau_mask']            > 0.5)] = [170, 150, 95]   # plateau: tan
    bc[(masks['mountain_mask']           > 0.5)] = [230, 225, 215]  # mountain: near-white
    p = prev_dir / 'bathymetry_classes_preview.jpg'
    Image.fromarray(bc).save(str(p), quality=87)
    paths.append(str(p))

    # 3. Coastline distance (greyscale)
    p = prev_dir / 'coastline_distance_preview.jpg'
    Image.fromarray(to_u8(masks['coastline_distance_mask'])).save(str(p), quality=87)
    paths.append(str(p))

    # 4. Shallow sea highlight
    p = prev_dir / 'shallow_sea_preview.jpg'
    Image.fromarray(to_u8(masks['shallow_sea_mask'])).save(str(p), quality=87)
    paths.append(str(p))

    print(f"[PREVIEW] 4 previews → {prev_dir}")
    return paths


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------
def build_metadata(args, w, h, etopo1_md5, gshhg_shp, etopo1_W, etopo1_H) -> dict:
    return {
        'generation_time':  time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'phase':            'B-6.2',
        'script':           'scripts/generate_b6_structure_masks.py',
        'resolution':       {'width': w, 'height': h},
        'projection':       'equirectangular / EPSG:4326 (assumed)',
        'dtype':            'float32',
        'sources': {
            'etopo1': {
                'path':       str(ETOPO1_PATH),
                'md5':        etopo1_md5,
                'src_dims':   {'width': etopo1_W, 'height': etopo1_H},
                'variable':   'z',
                'format':     'GMT NetCDF4 (gdal variant)',
                'variant':    'Ice Surface',
                'note':       'flat z array; reshape(H,W) required',
            },
            'gshhg': {
                'tier':    args.gshhg_tier,
                'path':    str(gshhg_shp),
                'version': '2.3.7',
                'layer':   'L1 (land polygons)',
            },
        },
        'thresholds': {
            'land_mask':               'GSHHG L1 rasterized polygons (PIL fill, exterior+holes)',
            'ocean_mask':              '1 - land_mask',
            'deep_ocean_mask':         'ETOPO1 z < -3500 AND ocean',
            'mid_ocean_mask':          'ETOPO1 -3500 <= z < -1000 AND ocean',
            'continental_shelf_mask':  'ETOPO1 -1000 <= z < -200 AND ocean',
            'shallow_sea_mask':        'ETOPO1 -200 <= z < 0 AND ocean',
            'coastline_distance_mask': 'scipy EDT from GSHHG land boundary, normalized 0-1',
            'mountain_mask':           'ETOPO1 z > 1500 AND land',
            'plateau_mask':            'ETOPO1 500 < z <= 1500 AND land',
        },
        'mask_types': {
            'land_mask':               'physical (GSHHG rasterized)',
            'ocean_mask':              'physical (GSHHG derived)',
            'deep_ocean_mask':         'physical (ETOPO1 depth band)',
            'mid_ocean_mask':          'physical (ETOPO1 depth band)',
            'continental_shelf_mask':  'physical (ETOPO1 depth band)',
            'shallow_sea_mask':        'physical (ETOPO1 depth band)',
            'coastline_distance_mask': 'physical (GSHHG EDT, normalized)',
            'mountain_mask':           'physical (ETOPO1 elevation, land)',
            'plateau_mask':            'physical (ETOPO1 elevation, land)',
        },
        'deferred_masks': [
            'reef_atoll_proxy_mask',
            'island_proximity_mask',
            'special_sea_water_masks (Red Sea, Yellow Sea, etc.)',
            'great_barrier_reef_proxy_mask',
            'bahamas_bank_mask',
        ],
        'known_limitations': [
            'ETOPO1 Ice variant: Antarctic/Greenland z reflects ice surface, not bedrock',
            'GSHHG L1 only: L2 lakes not subtracted (lake-as-land artifact at small lakes)',
            'Rasterization at 2K: 1 px ≈ 19 km — sub-pixel islands are lost',
            'Antimeridian-crossing rings rendered approximately (GSHHG typically pre-split)',
            'Depth mask feather sigma=1px at 2K ≈ 19 km; fine structure lost',
            'coastline_distance_mask: pixel-space distance only; km calibration deferred to B-6.3',
            'No CRS validation: EPSG:4326 assumed from ETOPO1/GSHHG standard convention',
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
    parser = argparse.ArgumentParser(description='B-6.2 Structure Mask Prototype Generator')
    parser.add_argument('--resolution', default='2048x1024',
                        help='Output resolution WxH (default: 2048x1024)')
    parser.add_argument('--gshhg-tier', default='h',
                        choices=['c', 'l', 'i', 'h', 'f'],
                        help='GSHHG resolution tier (default: h = high)')
    args = parser.parse_args()

    W, H = [int(x) for x in args.resolution.lower().split('x')]
    if W > 4096 or H > 2048:
        sys.exit(f"[ABORT] Resolution {W}×{H} exceeds allowed maximum 4096×2048 for this script.")

    print("=" * 70)
    print("B-6.2 Structure Mask Prototype Generator")
    print(f"Resolution:  {W} × {H}")
    print(f"GSHHG tier:  {args.gshhg_tier}")
    print(f"Output dir:  {OUTPUT_DIR}")
    print("=" * 70)

    # Safety check
    assert_output_safety(OUTPUT_DIR)
    print("[SAFETY] Output path check: PASS")

    # Verify inputs
    if not ETOPO1_PATH.exists():
        sys.exit(f"[ABORT] ETOPO1 not found: {ETOPO1_PATH}")
    gshhg_shp = GSHHG_BASE / args.gshhg_tier / f"GSHHS_{args.gshhg_tier}_L1.shp"
    if not gshhg_shp.exists():
        sys.exit(f"[ABORT] GSHHG shapefile not found: {gshhg_shp}")

    print(f"[INPUT] ETOPO1:  {ETOPO1_PATH}  OK")
    print(f"[INPUT] GSHHG:   {gshhg_shp}  OK")

    # MD5 for metadata (runs in parallel with mental model — fast enough at startup)
    print("[INPUT] Computing ETOPO1 MD5...")
    etopo1_md5 = md5_file(ETOPO1_PATH)
    print(f"[INPUT] ETOPO1 MD5: {etopo1_md5}")

    t_total = time.time()

    # --- Load ETOPO1 ---
    z, etopo1_W, etopo1_H = load_etopo1(ETOPO1_PATH, H, W)

    # --- Rasterize GSHHG ---
    land_gshhg = rasterize_gshhg_land(gshhg_shp, W, H)

    # --- Generate masks ---
    print("[MASKS] Generating structure masks...")
    t_masks = time.time()
    masks = generate_masks(z, land_gshhg, W, H)
    public_keys = [k for k in masks if not k.startswith('_')]
    print(f"[MASKS] {len(public_keys)} masks generated in {time.time()-t_masks:.1f}s")

    # --- Prepare output ---
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # NPZ (public masks only)
    npz_path = OUTPUT_DIR / 'structure_masks_2048x1024.npz'
    np.savez_compressed(str(npz_path), **{k: masks[k] for k in public_keys})
    npz_kb = npz_path.stat().st_size // 1024
    print(f"[OUTPUT] NPZ: {npz_path.name}  ({npz_kb} KB)")

    # Metrics
    metrics = compute_metrics(masks, W, H)
    metrics_path = OUTPUT_DIR / 'structure_mask_metrics.json'
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"[OUTPUT] Metrics: {metrics_path.name}")

    # Metadata
    metadata = build_metadata(args, W, H, etopo1_md5, gshhg_shp, etopo1_W, etopo1_H)
    meta_path = OUTPUT_DIR / 'structure_mask_metadata.json'
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"[OUTPUT] Metadata: {meta_path.name}")

    # Previews
    preview_paths = save_previews(masks, OUTPUT_DIR, W, H)

    # Safety print summary
    print()
    print("=== SAFETY CONFIRMATIONS ===")
    print("Confirm: earth3d.js                  NOT modified.")
    print("Confirm: DAY_TEXTURE_VARIANT          NOT modified.")
    print("Confirm: pwa/assets/earth/candidates/ NOT written.")
    print("Confirm: pwa/assets/earth/production/ NOT written.")
    print("Confirm: d6_noon_air_earth_generator.py NOT modified.")
    print("Confirm: No git operations performed.")

    print()
    print("=== B-6.2 COMPLETE ===")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Masks:    {public_keys}")
    print(f"NPZ size: {npz_kb} KB")
    print(f"Total time: {time.time()-t_total:.1f}s")

    # Print key metrics inline
    chk = metrics['checks']
    print()
    print("--- Metrics summary ---")
    for key in ['land_mask', 'ocean_mask', 'deep_ocean_mask', 'mid_ocean_mask',
                'continental_shelf_mask', 'shallow_sea_mask', 'coastline_distance_mask',
                'mountain_mask', 'plateau_mask']:
        st = metrics[key]
        print(f"  {key:30s}  cov={st['coverage_ratio']:.3f}  px={st['pixel_count']:>8,}")
    print(f"  land+ocean mean: {chk['land_plus_ocean_mean']:.6f}  (expected 1.0)")
    print(f"  depth overlap px: {chk['depth_mask_overlap_pixels']}")
    print(f"  ETOPO1/GSHHG land disagree: {chk['etopo1_vs_gshhg_land_disagree_ratio']:.3f}")


if __name__ == '__main__':
    main()
