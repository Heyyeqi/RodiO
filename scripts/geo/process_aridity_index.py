#!/usr/bin/env python3.11
"""
process_aridity_index.py — CGIAR Global Aridity Index v3.1 → 8K GeoTIFF

Extracts ai_v31_yr.tif from the annual zip, resamples to 8192×4096
(full-globe -90/+90 lat extent) using area-average (PIL BOX filter),
pads south of -60° with nodata=0, and writes a properly tagged GeoTIFF:
  external_processed_8k/global_aridity_index_8192x4096.tif

The output includes ModelPixelScaleTag, ModelTiepointTag, GeoKeyDirectoryTag
(EPSG:4326 / WGS-84), and GDAL_NODATA so GIS tools can read the extent.
A tracking manifest is also written to docs/data_sources/ (git-tracked).

Scale convention (unchanged from source):
    stored uint16 value = AI * 10000
    AI < 0.05   (value <  500)  → hyperarid
    AI 0.05–0.20 (500–2000)     → arid
    AI 0.20–0.50 (2000–5000)    → semi-arid
    AI 0.50–0.65 (5000–6500)    → sub-humid
    AI ≥ 0.65   (≥ 6500)        → humid
    value = 0                   → nodata (ocean / south of -60° / masked pixel)

License: CGIAR-CSI, non-commercial / research only.
         See docs/data_sources/global_aridity_pet_manifest.json.

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

# Tracked manifest location (committed to git)
MANIFEST_TRACKED = REPO_ROOT / "docs/data_sources/global_aridity_pet_manifest.json"
# Source-cache copy (gitignored, for proximity to data)
MANIFEST_CACHE   = (
    REPO_ROOT
    / "d5b_processor_v3/source_cache/gee_global/external_manifests"
    / "global_aridity_pet_manifest.json"
)

# Source raster geometry (native 30-arcsec grid)
SRC_W  = 43200
SRC_H  = 18000
SRC_LAT_N =  90.0
SRC_LAT_S = -60.0       # coverage stops here

# Target 8K geometry (full globe)
OUT_W  = 8192
OUT_H  = 4096
OUT_LAT_N =  90.0
OUT_LAT_S = -90.0

NODATA = 0  # uint16


def _data_rows_in_output() -> int:
    """Output rows that map to actual source data (lat > -60°)."""
    return round((OUT_LAT_N - SRC_LAT_S) / (OUT_LAT_N - OUT_LAT_S) * OUT_H)  # 3413


def load_source(dry_run: bool) -> np.ndarray | None:
    if not ZIP_PATH.exists():
        print(f"ERROR: zip not found: {ZIP_PATH}", file=sys.stderr)
        return None
    if dry_run:
        print(f"  [dry-run] would extract {ZIP_ENTRY}")
        return None

    print(f"  Extracting {ZIP_ENTRY} …", flush=True)
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
        print(f"ERROR: expected 2D array, got {arr.shape}", file=sys.stderr)
        return None
    print(f"  Source: {arr.shape} {arr.dtype}  "
          f"value range [{int(arr.min())}, {int(arr.max())}]", flush=True)
    return arr


def resample(arr: np.ndarray, data_rows: int) -> np.ndarray:
    """
    Downsample source array to (data_rows, OUT_W) using PIL BOX filter.

    BOX = area-average resampling — each output pixel is the mean of the
    corresponding input patch.  Correct for continuous climate fields;
    avoids LANCZOS ringing near sharp dry/humid boundaries.
    """
    print(f"  Resampling {arr.shape} → ({data_rows}, {OUT_W}) [BOX / area-average] …",
          flush=True)
    t0 = time.time()
    img = Image.fromarray(arr.astype(np.float32), mode="F")
    img_resized = img.resize((OUT_W, data_rows), Image.BOX)
    result = np.clip(np.round(np.array(img_resized, dtype=np.float32)), 0, 65535).astype(np.uint16)
    print(f"  Resampled in {time.time()-t0:.1f}s  "
          f"value range [{int(result.min())}, {int(result.max())}]", flush=True)
    return result


def _geotiff_extratags() -> list:
    """
    Build tifffile extratags list for a WGS-84 geographic GeoTIFF.

    Tags:
        33550  ModelPixelScaleTag  — pixel size in degrees
        33922  ModelTiepointTag    — (0,0) → (-180, +90)
        34735  GeoKeyDirectoryTag  — EPSG:4326 keys
        42113  GDAL_NODATA         — nodata as ASCII string
    """
    x_scale = 360.0 / OUT_W   # ≈ 0.04394531°/px
    y_scale = 180.0 / OUT_H   # ≈ 0.04394531°/px

    geo_key_dir = [
        1, 1, 0, 3,          # KeyDirVersion=1, KeyRevision=1, Minor=0, NKeys=3
        1024, 0, 1, 2,       # GTModelTypeGeoKey = ModelTypeGeographic
        1025, 0, 1, 1,       # GTRasterTypeGeoKey = RasterPixelIsArea
        2048, 0, 1, 4326,    # GeographicTypeGeoKey = GCS_WGS_84
    ]

    return [
        (33550, "d", 3, [x_scale, y_scale, 0.0]),
        (33922, "d", 6, [0.0, 0.0, 0.0, -180.0, 90.0, 0.0]),
        (34735, "H", len(geo_key_dir), geo_key_dir),
        (42113, "s", None, "0\x00"),
    ]


def save_output(resampled: np.ndarray, data_rows: int) -> None:
    """Build full-globe 4096×8192 raster and save as tagged GeoTIFF."""
    try:
        import tifffile
    except ImportError:
        print("ERROR: tifffile not available", file=sys.stderr)
        return

    output = np.zeros((OUT_H, OUT_W), dtype=np.uint16)
    output[:data_rows, :] = resampled

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Saving → {OUT_FILE} …", flush=True)
    t0 = time.time()
    tifffile.imwrite(
        str(OUT_FILE),
        output,
        photometric="minisblack",
        compression="lzw",
        extratags=_geotiff_extratags(),
    )
    size_mb = OUT_FILE.stat().st_size / 1e6
    print(f"  Saved {size_mb:.1f} MB in {time.time()-t0:.1f}s", flush=True)


def _base_manifest() -> dict:
    """Return the canonical manifest dict (same content as the original)."""
    return {
        "source_name": "Global Aridity Index and Potential Evapotranspiration (ET0) Climate Database v3.1",
        "source_version": "v3.1 (figshare version 4)",
        "provider": "CGIAR-CSI / Trabucco & Zomer",
        "official_url": "https://cgiarcsi.community/data/global-aridity-and-pet-database/",
        "download_url": "https://doi.org/10.6084/m9.figshare.7504448.v4",
        "download_date": "2026-06-24",
        "raw_file_path": "d5b_processor_v3/source_cache/gee_global/external_raw/global_aridity_pet/",
        "processed_8k_file_path": str(OUT_FILE.relative_to(REPO_ROOT)),
        "spatial_metadata": {
            "crs": "EPSG:4326 (WGS84)",
            "pixel_size_deg": 0.0083333333,
            "pixel_size_arcsec": 30,
            "native_width_px": SRC_W,
            "native_height_px": SRC_H,
            "coverage_west": -180.0,
            "coverage_east": 180.0,
            "coverage_north": 90.0,
            "coverage_south": -60.0,
            "note_coverage": "Does NOT cover south of -60 deg",
        },
        "processed_8k_metadata": {
            "crs": "EPSG:4326 (WGS84)",
            "width_px": OUT_W,
            "height_px": OUT_H,
            "resampling": "PIL BOX (area-average)",
            "geotiff_tags": ["ModelPixelScaleTag (33550)", "ModelTiepointTag (33922)",
                             "GeoKeyDirectoryTag (34735) EPSG:4326", "GDAL_NODATA (42113) = 0"],
            "nodata_value": 0,
            "nodata_rows_south": OUT_H - _data_rows_in_output(),
            "coverage_south_padded": -90.0,
            "scale": "uint16 = AI * 10000",
        },
        "license": "non-commercial use only; attribution required",
        "attribution_required": True,
        "attribution_text": (
            "CGIAR-CSI Global-Aridity and Global-PET Database; "
            "Trabucco, Antonio; Zomer, Robert (2019). "
            "Global Aridity Index and Potential Evapotranspiration (ET0) Climate Database v3. "
            "figshare. doi:10.6084/m9.figshare.7504448.v4"
        ),
        "commercial_clearance": False,
        "research_only": True,
        "replacement_required_before_commercial": True,
        "processing_readiness": "processed_8k_available",
        "use_in_rodio": (
            "M1 desert/arid zone mask derivation (research phase only). "
            "Replace with CC-licensed aridity source before commercial release."
        ),
        "classification_thresholds_unep": {
            "hyperarid":  "AI < 0.05  (value < 500)",
            "arid":       "AI 0.05–0.20  (500–2000)",
            "semi_arid":  "AI 0.20–0.50  (2000–5000)",
            "sub_humid":  "AI 0.50–0.65  (5000–6500)",
            "humid":      "AI ≥ 0.65  (≥ 6500)",
        },
    }


def write_manifests(manifest: dict) -> None:
    """Write manifest to both tracked (docs/) and cache locations."""
    body = json.dumps(manifest, indent=2)

    # Tracked copy (committed to git)
    MANIFEST_TRACKED.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_TRACKED.write_text(body)
    print(f"  Manifest (tracked) → {MANIFEST_TRACKED.relative_to(REPO_ROOT)}")

    # Cache copy (gitignored, proximity to raw data)
    MANIFEST_CACHE.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_CACHE.write_text(body)
    print(f"  Manifest (cache)   → {MANIFEST_CACHE.relative_to(REPO_ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tag = "[DRY RUN] " if args.dry_run else ""
    print(f"=== Global Aridity Index processing — {tag or 'APPLY'} ===")
    data_rows = _data_rows_in_output()
    print(f"  Output geometry: {OUT_W}×{OUT_H}  "
          f"(data rows: {data_rows}, nodata rows: {OUT_H - data_rows})")
    print()

    if args.dry_run:
        load_source(dry_run=True)
        print("  [dry-run] would resample (BOX) → save GeoTIFF → write manifests")
        return

    t_total = time.time()
    arr = load_source(dry_run=False)
    if arr is None:
        sys.exit(1)

    resampled = resample(arr, data_rows)
    del arr

    save_output(resampled, data_rows)
    write_manifests(_base_manifest())

    print(f"\nDone in {time.time()-t_total:.1f}s")
    print(f"Output : {OUT_FILE}")
    print(f"Tracked: {MANIFEST_TRACKED.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
