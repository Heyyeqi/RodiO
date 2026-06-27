#!/usr/bin/env python3.11
"""
process_aridity_index.py — CGIAR Global Aridity Index v3.1 → 8K raster

Extracts ai_v31_yr.tif from the annual zip, resamples to 8192×4096
(full-globe -90/+90 lat extent), pads south of -60° with nodata=0,
and writes external_processed_8k/global_aridity_index_8192x4096.tif.

Scale convention (unchanged from source):
    stored uint16 value = AI * 10000
    AI < 0.05   (value < 500)   → hyperarid
    AI 0.05–0.20 (500–2000)     → arid
    AI 0.20–0.50 (2000–5000)    → semi-arid
    AI 0.50–0.65 (5000–6500)    → sub-humid
    AI ≥ 0.65   (≥ 6500)        → humid
    value = 0                   → nodata (south of -60° or ocean/nodata pixel)

License: CGIAR-CSI, non-commercial / research only.
         See external_manifests/global_aridity_pet_manifest.json.

Usage:
    python3.11 scripts/geo/process_aridity_index.py [--dry-run]
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).parents[2]

ZIP_PATH = (
    REPO_ROOT
    / "d5b_processor_v3/source_cache/gee_global/external_raw/global_aridity_pet"
    / "Global-AI_ET0__annual_v3_1.zip"
)
ZIP_ENTRY = "Global-AI_ET0__annual_v3_1/ai_v31_yr.tif"

OUT_DIR  = REPO_ROOT / "d5b_processor_v3/source_cache/gee_global/external_processed_8k"
OUT_FILE = OUT_DIR / "global_aridity_index_8192x4096.tif"

MANIFEST_PATH = (
    REPO_ROOT
    / "d5b_processor_v3/source_cache/gee_global/external_manifests"
    / "global_aridity_pet_manifest.json"
)

# Source raster geometry (native 30-arcsec grid)
SRC_W  = 43200          # pixels
SRC_H  = 18000          # pixels
SRC_LAT_N =  90.0
SRC_LAT_S = -60.0       # coverage stops here (no Antarctica)

# Target 8K geometry (full globe)
OUT_W  = 8192
OUT_H  = 4096
OUT_LAT_N =  90.0
OUT_LAT_S = -90.0

NODATA = 0  # uint16; hyperarid values start at ~10 (AI=0.001), so 0 is safe nodata


def _data_rows_in_output() -> int:
    """Number of output rows that map to actual source data (lat > -60°)."""
    total_lat = OUT_LAT_N - OUT_LAT_S          # 180°
    covered   = OUT_LAT_N - SRC_LAT_S          # 150°
    return round(covered / total_lat * OUT_H)  # 3413


def load_source(dry_run: bool) -> np.ndarray | None:
    """Read ai_v31_yr.tif from inside the zip. Returns uint16 array (H, W)."""
    if not ZIP_PATH.exists():
        print(f"ERROR: zip not found: {ZIP_PATH}", file=sys.stderr)
        return None

    if dry_run:
        print(f"  [dry-run] would extract {ZIP_ENTRY} ({ZIP_PATH.name})")
        return None

    print(f"  Extracting {ZIP_ENTRY} from {ZIP_PATH.name} …", flush=True)
    t0 = time.time()
    with zipfile.ZipFile(ZIP_PATH) as z:
        raw_bytes = z.read(ZIP_ENTRY)

    print(f"  Read {len(raw_bytes)/1e6:.0f} MB in {time.time()-t0:.1f}s", flush=True)

    try:
        import tifffile
        arr = tifffile.imread(io.BytesIO(raw_bytes))
    except Exception as e:
        print(f"ERROR reading tiff: {e}", file=sys.stderr)
        return None

    if arr.ndim != 2:
        print(f"ERROR: expected 2D array, got shape {arr.shape}", file=sys.stderr)
        return None

    print(f"  Source array: {arr.shape} dtype={arr.dtype} "
          f"min={int(arr.min())} max={int(arr.max())}", flush=True)

    # Validate geometry
    if arr.shape != (SRC_H, SRC_W):
        print(f"  WARNING: expected ({SRC_H},{SRC_W}), got {arr.shape} — adjusting")

    return arr


def resample(arr: np.ndarray, data_rows: int) -> np.ndarray:
    """
    Downsample source array to (data_rows, OUT_W) using PIL LANCZOS.

    PIL mode 'F' (float32) is used so uint16 values are preserved exactly.
    """
    print(f"  Resampling {arr.shape} → ({data_rows}, {OUT_W}) …", flush=True)
    t0 = time.time()

    img = Image.fromarray(arr.astype(np.float32), mode="F")
    img_resized = img.resize((OUT_W, data_rows), Image.LANCZOS)
    resampled = np.array(img_resized, dtype=np.float32)

    # Round back to uint16, preserving nodata=0
    result = np.clip(np.round(resampled), 0, 65535).astype(np.uint16)
    print(f"  Resampled in {time.time()-t0:.1f}s  "
          f"value range [{int(result.min())}, {int(result.max())}]", flush=True)
    return result


def save_output(resampled: np.ndarray, data_rows: int) -> None:
    """Build full-globe 4096×8192 raster and save as uint16 GeoTIFF."""
    try:
        import tifffile
    except ImportError:
        print("ERROR: tifffile not available", file=sys.stderr)
        return

    output = np.zeros((OUT_H, OUT_W), dtype=np.uint16)  # nodata=0 pre-filled
    output[:data_rows, :] = resampled

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Saving → {OUT_FILE} …", flush=True)
    t0 = time.time()

    # Minimal GeoTIFF metadata via tifffile (no GDAL dependency)
    # Resolution in degrees per pixel (approximate)
    x_res = 360.0 / OUT_W   # deg/px
    y_res = 180.0 / OUT_H   # deg/px
    tifffile.imwrite(
        str(OUT_FILE),
        output,
        photometric="minisblack",
        compression="lzw",
        metadata={
            "source":     "CGIAR Global Aridity Index v3.1, annual",
            "license":    "non-commercial / research only",
            "scale":      "uint16 = AI * 10000",
            "nodata":     "0",
            "coverage":   "-90 to +90 lat (south of -60 padded with nodata=0)",
            "x_res_deg":  x_res,
            "y_res_deg":  y_res,
        },
    )
    size_mb = OUT_FILE.stat().st_size / 1e6
    print(f"  Saved {size_mb:.1f} MB in {time.time()-t0:.1f}s", flush=True)


def update_manifest(processed_path: Path) -> None:
    """Write processed_8k_file_path into the existing manifest JSON."""
    if not MANIFEST_PATH.exists():
        return
    manifest = json.loads(MANIFEST_PATH.read_text())
    manifest["processed_8k_file_path"] = str(
        processed_path.relative_to(REPO_ROOT)
    )
    manifest["processing_notes_8k"] = (
        f"Resampled from {SRC_W}×{SRC_H} (30 arcsec native, lat -60 to +90) "
        f"to {OUT_W}×{OUT_H} (full globe -90 to +90) using PIL LANCZOS. "
        f"Rows south of -60° padded with nodata=0. "
        f"Scale unchanged: stored uint16 = AI × 10000."
    )
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    print(f"  Manifest updated: {MANIFEST_PATH.name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without writing files")
    args = parser.parse_args()

    tag = "[DRY RUN] " if args.dry_run else ""
    print(f"=== Global Aridity Index processing — {tag or 'APPLY'} ===")
    print(f"  Source zip : {ZIP_PATH.name}")
    print(f"  Output     : {OUT_FILE}")
    print()

    data_rows = _data_rows_in_output()
    print(f"  Output geometry : {OUT_W}×{OUT_H}  (data rows: {data_rows}, "
          f"nodata rows: {OUT_H - data_rows})")
    print()

    if args.dry_run:
        load_source(dry_run=True)
        print("  [dry-run] would resample → save → update manifest")
        return

    t_total = time.time()

    arr = load_source(dry_run=False)
    if arr is None:
        sys.exit(1)

    resampled = resample(arr, data_rows)
    del arr  # free ~400MB

    save_output(resampled, data_rows)
    update_manifest(OUT_FILE)

    print(f"\nDone in {time.time()-t_total:.1f}s total")
    print(f"Output: {OUT_FILE}")


if __name__ == "__main__":
    main()
