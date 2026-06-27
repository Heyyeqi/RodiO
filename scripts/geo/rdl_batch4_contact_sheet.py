#!/usr/bin/env python3.11
"""
rdl_batch4_contact_sheet.py — Generate batch4 ACA reef diff contact sheet

Creates a side-by-side contact sheet: before (batch3) vs after (batch4 ACA reef)
for all 47 regions that have tile_noon_air_mapbox_aca_reef_b4.jpg.

Usage:
  python3.11 scripts/geo/rdl_batch4_contact_sheet.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

TILES_DIR = Path(__file__).parents[2] / (
    "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions"
)
OUT_DIR = Path(__file__).parents[2] / "docs/preview_archives/rdl_batch4_aca_reef_20260627"
OUT_DIR.mkdir(parents=True, exist_ok=True)

THUMB = 256  # thumbnail size per tile
COLS  = 6

def make_thumb(path: Path, size: int) -> Image.Image:
    img = Image.open(path).convert("RGB")
    img.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new("RGB", (size, size), (20, 20, 20))
    x = (size - img.width) // 2
    y = (size - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas

def mean_abs_diff(a: Path, b: Path) -> float:
    arr_a = np.array(Image.open(a).convert("RGB"), dtype=np.float32)
    arr_b = np.array(Image.open(b).convert("RGB"), dtype=np.float32)
    if arr_a.shape != arr_b.shape:
        img_b = Image.open(b).convert("RGB").resize(
            (arr_a.shape[1], arr_a.shape[0]), Image.LANCZOS
        )
        arr_b = np.array(img_b, dtype=np.float32)
    return float(np.mean(np.abs(arr_a - arr_b)))


def main() -> None:
    regions = sorted(p.name for p in TILES_DIR.iterdir()
                     if p.is_dir() and (p / "tile_noon_air_mapbox_aca_reef_b4.jpg").exists())

    print(f"Generating contact sheet for {len(regions)} regions ...")

    diffs: list[tuple[str, float]] = []
    for r in regions:
        before = TILES_DIR / r / "tile_noon_air_mapbox.jpg"
        after  = TILES_DIR / r / "tile_noon_air_mapbox_aca_reef_b4.jpg"
        diff = mean_abs_diff(before, after)
        diffs.append((r, diff))
        print(f"  {r}: mean_abs_diff={diff:.4f}")

    diffs.sort(key=lambda x: -x[1])

    # Save diff stats
    (OUT_DIR / "batch4_diff_stats.json").write_text(
        json.dumps([{"region": r, "mean_abs_diff_rgb": round(d, 4)} for r, d in diffs], indent=2)
    )

    # Build contact sheet: 2 rows per region (before / after), COLS wide
    rows = math.ceil(len(diffs) / COLS)
    sheet_w = COLS * THUMB
    sheet_h = rows * THUMB * 2 + rows * 20  # 20px label row per pair-row

    sheet = Image.new("RGB", (sheet_w, sheet_h), (15, 15, 15))
    draw = ImageDraw.Draw(sheet)

    for idx, (region, diff) in enumerate(diffs):
        col = idx % COLS
        row = idx // COLS
        x = col * THUMB
        y_label = row * (THUMB * 2 + 20)
        y_before = y_label + 20
        y_after  = y_before + THUMB

        before_path = TILES_DIR / region / "tile_noon_air_mapbox.jpg"
        after_path  = TILES_DIR / region / "tile_noon_air_mapbox_aca_reef_b4.jpg"

        sheet.paste(make_thumb(before_path, THUMB), (x, y_before))
        sheet.paste(make_thumb(after_path,  THUMB), (x, y_after))

        label = f"{region[:18]}  Δ{diff:.2f}"
        draw.rectangle([x, y_label, x + THUMB, y_label + 20], fill=(30, 30, 30))
        draw.text((x + 4, y_label + 3), label, fill=(200, 200, 200))

    out_path = OUT_DIR / "batch4_contact_sheet.jpg"
    sheet.save(str(out_path), "JPEG", quality=88)
    print(f"\nContact sheet: {out_path}")
    print(f"Diff stats:    {OUT_DIR / 'batch4_diff_stats.json'}")
    print(f"\nTop 5 by diff:")
    for r, d in diffs[:5]:
        print(f"  {r}: {d:.4f}")


if __name__ == "__main__":
    main()
