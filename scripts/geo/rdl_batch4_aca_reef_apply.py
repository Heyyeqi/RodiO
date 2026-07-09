#!/usr/bin/env python3.11
"""
rdl_batch4_aca_reef_apply.py — Apply ACA reef layer to batch3 production tiles

For each region that has aca_reef_mask.png, applies the reef colorization
on top of the current tile_noon_air_mapbox.jpg (batch3 result).

Saves result as tile_noon_air_mapbox_aca_reef_b4.jpg so it can be reviewed
before promotion. Does NOT overwrite production tile directly.

Usage:
  python3.11 scripts/geo/rdl_batch4_aca_reef_apply.py [--dry-run] [--region japan]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

TILES_DIR = Path(__file__).parents[2] / (
    "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions"
)
ELEV_PATH = Path(__file__).parents[2] / (
    "d5b_processor_v3/source_cache/gee_global/exported_8k/copernicus_dem_glo30_elevation_8192x4096.tif"
)

_elev_cache: np.ndarray | None = None

def _load_elev() -> np.ndarray | None:
    global _elev_cache
    if _elev_cache is not None:
        return _elev_cache
    if not ELEV_PATH.exists():
        return None
    try:
        import tifffile
        _elev_cache = tifffile.imread(str(ELEV_PATH)).astype(np.float32)
        print(f"  [elev] loaded {ELEV_PATH.name} {_elev_cache.shape}")
        return _elev_cache
    except Exception as e:
        print(f"  [elev] failed to load: {e}")
        return None

def _crop_elev(elev: np.ndarray, lon_w: float, lon_e: float,
               lat_s: float, lat_n: float, out_w: int, out_h: int) -> np.ndarray | None:
    h, w = elev.shape
    x0 = max(0, math.floor((lon_w + 180.0) / 360.0 * w))
    x1 = min(w, math.ceil((lon_e + 180.0) / 360.0 * w))
    y0 = max(0, math.floor((90.0 - lat_n) / 180.0 * h))
    y1 = min(h, math.ceil((90.0 - lat_s) / 180.0 * h))
    crop = elev[y0:y1, x0:x1]
    if crop.size == 0:
        return None
    return np.array(
        Image.fromarray(crop, mode="F").resize((out_w, out_h), Image.BILINEAR)
    )

def apply_aca_reef(base_arr: np.ndarray, mask_img: Image.Image,
                   elev: np.ndarray | None = None) -> np.ndarray:
    """Verbatim from rdl_mapbox_poc.apply_m2_aca_reef."""
    base = base_arr.astype(np.float32)
    mask_core = np.array(mask_img, dtype=np.float32) / 255.0
    mask_feather = np.array(
        mask_img.filter(ImageFilter.GaussianBlur(radius=2.2)), dtype=np.float32
    ) / 255.0
    if elev is not None:
        depth = np.maximum(-elev.astype(np.float32), 0.0)
        shallow = np.clip(1.0 - (depth - 5.0) / 115.0, 0.0, 1.0)
        gate = np.where(elev < 8.0, 0.35 + 0.65 * shallow, 0.0)
    else:
        gate = np.ones(mask_core.shape, dtype=np.float32) * 0.75
    alpha = np.clip(mask_feather * gate * 0.34, 0.0, 0.34)
    core = np.clip(mask_core * gate, 0.0, 1.0)
    reef_rgb = np.array([88, 190, 184], dtype=np.float32)
    sand_rgb = np.array([205, 214, 184], dtype=np.float32)
    target = base * 0.72 + reef_rgb[None, None, :] * 0.20 + sand_rgb[None, None, :] * 0.08
    result = base * (1.0 - alpha[:, :, None]) + target * alpha[:, :, None]
    lift = (core * 11.0)[:, :, None]
    result = result + lift * np.array([0.45, 0.95, 0.85], dtype=np.float32)[None, None, :]
    return np.clip(result, 0, 255).astype(np.uint8)

def process_region(region_dir: Path, elev_global: np.ndarray | None,
                   dry_run: bool) -> str:
    mask_path = region_dir / "aca_reef_mask.png"
    src_path  = region_dir / "tile_noon_air_mapbox.jpg"
    dest_path = region_dir / "tile_noon_air_mapbox_aca_reef_b4.jpg"
    meta_path = region_dir / "mapbox_meta.json"

    if not mask_path.exists():
        return "skip:no_mask"
    if not src_path.exists():
        return "skip:no_production_tile"
    if dry_run:
        return "dry_run:ok"

    # Load bounds for elevation crop
    elev_crop = None
    if elev_global is not None and meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            b = meta["bounds"]
            base_img = Image.open(src_path)
            w, h = base_img.size
            elev_crop = _crop_elev(elev_global, b["lon_w"], b["lon_e"],
                                   b["lat_s"], b["lat_n"], w, h)
        except Exception:
            elev_crop = None

    base_img = Image.open(src_path).convert("RGB")
    mask_img = Image.open(mask_path).convert("L")
    if mask_img.size != base_img.size:
        mask_img = mask_img.resize(base_img.size, Image.LANCZOS)

    base_arr = np.array(base_img)
    result_arr = apply_aca_reef(base_arr, mask_img, elev_crop)

    result_img = Image.fromarray(result_arr)
    result_img.save(str(dest_path), "JPEG", quality=92, optimize=True)
    return "applied"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--region", default=None, help="Process single region only")
    args = parser.parse_args()

    tag = "[DRY RUN] " if args.dry_run else ""
    print(f"=== Batch 4 ACA reef apply — {tag or 'APPLY'} ===")

    elev_global = None if args.dry_run else _load_elev()

    region_dirs = (
        [TILES_DIR / args.region] if args.region
        else sorted(TILES_DIR.iterdir())
    )

    results: dict[str, list[str]] = {"applied": [], "dry_run:ok": [],
                                     "skip:no_mask": [], "skip:no_production_tile": []}
    t0 = time.time()
    for region_dir in region_dirs:
        if not region_dir.is_dir():
            continue
        status = process_region(region_dir, elev_global, args.dry_run)
        results.setdefault(status, []).append(region_dir.name)
        sym = {"applied": "✓", "dry_run:ok": "~", "skip:no_mask": "–",
               "skip:no_production_tile": "!"}.get(status, "?")
        print(f"  {sym} {region_dir.name} ({status})")

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")
    print(f"  Applied:          {len(results.get('applied', []))}")
    print(f"  Dry-run eligible: {len(results.get('dry_run:ok', []))}")
    print(f"  No mask:          {len(results.get('skip:no_mask', []))}")
    print(f"  No prod tile:     {len(results.get('skip:no_production_tile', []))}")
    if not args.dry_run:
        print("\nOutput: tile_noon_air_mapbox_aca_reef_b4.jpg (not yet in production)")
        print("Review with a contact sheet before promoting to tile_noon_air_mapbox.jpg")


if __name__ == "__main__":
    main()
