#!/usr/bin/env python3
"""
rdl_m3_m4_region_sampler.py — sample WorldCover and Koppen classes for RDL regions.

This script is read-only with respect to source rasters and generator outputs. It
does not create textures or masks; it writes only summary artifacts for review.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import tifffile


ROOT = Path(__file__).parent.parent.parent
REGION_SOURCE = ROOT / "scripts/geo/rdl_mapbox_poc.py"
WORLDCOVER_TIF = ROOT / (
    "d5b_processor_v3/source_cache/gee_global/exported_8k/"
    "esa_worldcover_2021_v200_map_8192x4096.tif"
)
KOPPEN_TIF = ROOT / (
    "d5b_processor_v3/source_cache/gee_global/external_processed_8k/"
    "koppen_geiger_1991_2020_8192x4096.tif"
)
KOPPEN_MANIFEST = ROOT / (
    "d5b_processor_v3/source_cache/gee_global/external_manifests/"
    "koppen_geiger_manifest.json"
)
DEFAULT_OUT = ROOT / "docs/preview_archives/rdl_m3_m4_region_sampler_20260626"


WORLDCOVER_CLASSES = {
    0: "No data",
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}


def load_regions(path: Path = REGION_SOURCE) -> dict[str, dict[str, Any]]:
    module = ast.parse(path.read_text())
    for node in module.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == "REGIONS":
            return ast.literal_eval(node.value)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if getattr(target, "id", None) == "REGIONS":
                    return ast.literal_eval(node.value)
    raise RuntimeError(f"REGIONS not found in {path}")


def read_koppen_classes(path: Path = KOPPEN_MANIFEST) -> dict[int, str]:
    data = json.loads(path.read_text())
    labels = {0: "Ocean / unclassified"}
    labels.update({int(k): v for k, v in data.get("classes", {}).items()})
    return labels


def crop_for_bounds(
    arr: np.ndarray,
    bounds: tuple[float, float, float, float],
) -> np.ndarray:
    lon_w, lon_e, lat_s, lat_n = bounds
    h, w = arr.shape[:2]
    x0 = math.floor((lon_w + 180.0) / 360.0 * w)
    x1 = math.ceil((lon_e + 180.0) / 360.0 * w)
    y0 = math.floor((90.0 - lat_n) / 180.0 * h)
    y1 = math.ceil((90.0 - lat_s) / 180.0 * h)
    x0 = max(0, min(w - 1, x0))
    x1 = max(x0 + 1, min(w, x1))
    y0 = max(0, min(h - 1, y0))
    y1 = max(y0 + 1, min(h, y1))
    return arr[y0:y1, x0:x1]


def histogram(arr: np.ndarray, labels: dict[int, str]) -> list[dict[str, Any]]:
    values, counts = np.unique(arr, return_counts=True)
    total = int(counts.sum())
    rows: list[dict[str, Any]] = []
    for value, count in zip(values, counts):
        code = int(value)
        pixels = int(count)
        rows.append(
            {
                "code": code,
                "label": labels.get(code, f"Unknown class {code}"),
                "pixels": pixels,
                "pct": round(pixels / total * 100.0, 4) if total else 0.0,
            }
        )
    rows.sort(key=lambda row: row["pixels"], reverse=True)
    return rows


def top_nonzero(rows: list[dict[str, Any]], excluded: set[int] | None = None) -> dict[str, Any] | None:
    excluded = excluded or set()
    for row in rows:
        if row["code"] not in excluded:
            return row
    return None


def koppen_family(code: int | None) -> str | None:
    if code is None or code == 0:
        return None
    if 1 <= code <= 3:
        return "tropical"
    if 4 <= code <= 7:
        return "arid"
    if 8 <= code <= 16:
        return "temperate"
    if 17 <= code <= 28:
        return "cold"
    if 29 <= code <= 30:
        return "polar"
    return "unknown"


def worldcover_family(code: int | None) -> str | None:
    if code is None or code == 0:
        return None
    if code == 80:
        return "water"
    if code in {10, 20, 30, 40, 90, 95, 100}:
        return "vegetated"
    if code == 50:
        return "built"
    if code == 60:
        return "bare"
    if code == 70:
        return "ice"
    return "unknown"


def percent_for_codes(rows: list[dict[str, Any]], codes: set[int]) -> float:
    return round(sum(row["pct"] for row in rows if row["code"] in codes), 4)


def summarize_region(
    region_id: str,
    cfg: dict[str, Any],
    worldcover: np.ndarray,
    koppen: np.ndarray,
    koppen_labels: dict[int, str],
) -> dict[str, Any]:
    bounds = tuple(float(v) for v in cfg["bounds"])
    wc_crop = crop_for_bounds(worldcover, bounds)
    kp_crop = crop_for_bounds(koppen, bounds)
    wc_hist = histogram(wc_crop, WORLDCOVER_CLASSES)
    kp_hist = histogram(kp_crop, koppen_labels)
    wc_top = top_nonzero(wc_hist, excluded={0})
    wc_top_land = top_nonzero(wc_hist, excluded={0, 80})
    kp_top = top_nonzero(kp_hist, excluded={0})
    return {
        "region": region_id,
        "label": cfg.get("label"),
        "bounds": {
            "lon_w": bounds[0],
            "lon_e": bounds[1],
            "lat_s": bounds[2],
            "lat_n": bounds[3],
        },
        "sample_shape": {
            "worldcover": list(wc_crop.shape),
            "koppen": list(kp_crop.shape),
        },
        "worldcover": {
            "top_class": wc_top,
            "top_land_class": wc_top_land,
            "family": worldcover_family(wc_top_land["code"] if wc_top_land else None),
            "water_pct": percent_for_codes(wc_hist, {80}),
            "nodata_pct": percent_for_codes(wc_hist, {0}),
            "vegetated_pct": percent_for_codes(wc_hist, {10, 20, 30, 40, 90, 95, 100}),
            "bare_pct": percent_for_codes(wc_hist, {60}),
            "built_pct": percent_for_codes(wc_hist, {50}),
            "ice_pct": percent_for_codes(wc_hist, {70}),
            "histogram": wc_hist,
        },
        "koppen": {
            "top_class": kp_top,
            "family": koppen_family(kp_top["code"] if kp_top else None),
            "land_climate_pct": round(100.0 - percent_for_codes(kp_hist, {0}), 4),
            "tropical_pct": percent_for_codes(kp_hist, {1, 2, 3}),
            "arid_pct": percent_for_codes(kp_hist, {4, 5, 6, 7}),
            "temperate_pct": percent_for_codes(kp_hist, set(range(8, 17))),
            "cold_pct": percent_for_codes(kp_hist, set(range(17, 29))),
            "polar_pct": percent_for_codes(kp_hist, {29, 30}),
            "histogram": kp_hist,
        },
    }


def visual_hints_for(row: dict[str, Any]) -> dict[str, Any]:
    """
    Convert M3/M4 summaries into conservative review-only hints.

    These values are not applied by any compositor. They are a compact bridge
    from class histograms to the later visual-parameter design pass.
    """
    climate = row["koppen"]["family"] or "none"
    land = row["worldcover"]["family"] or "none"
    climate_presets = {
        "tropical": {
            "temperature_bias": "slightly_warm",
            "saturation_bias": 1.05,
            "contrast_bias": 1.02,
            "noon_air_note": "humid clear-air color, protect cyan shallow water",
        },
        "arid": {
            "temperature_bias": "warm_dry",
            "saturation_bias": 0.98,
            "contrast_bias": 1.04,
            "noon_air_note": "control desert glare, keep water depth separation cool",
        },
        "temperate": {
            "temperature_bias": "neutral",
            "saturation_bias": 1.00,
            "contrast_bias": 1.00,
            "noon_air_note": "neutral baseline, small local land-cover bias only",
        },
        "cold": {
            "temperature_bias": "cool",
            "saturation_bias": 0.96,
            "contrast_bias": 1.03,
            "noon_air_note": "cool atmosphere, preserve snow/forest separation",
        },
        "polar": {
            "temperature_bias": "cold_ice",
            "saturation_bias": 0.92,
            "contrast_bias": 1.01,
            "noon_air_note": "ice highlight protection, avoid blue-black ocean overreach",
        },
        "none": {
            "temperature_bias": "ocean_default",
            "saturation_bias": 1.00,
            "contrast_bias": 1.00,
            "noon_air_note": "mostly ocean bbox; use M0/M1 water behavior first",
        },
    }
    land_presets = {
        "vegetated": {
            "land_tint": "green_ecology_detail",
            "land_strength": 0.12,
            "land_note": "bias land pixels only; keep satellite texture dominant",
        },
        "bare": {
            "land_tint": "sand_rock_warmth",
            "land_strength": 0.10,
            "land_note": "warm bare land softly; cap highlights",
        },
        "ice": {
            "land_tint": "ice_cool_white",
            "land_strength": 0.08,
            "land_note": "protect ice texture and avoid flat white",
        },
        "built": {
            "land_tint": "urban_neutral",
            "land_strength": 0.06,
            "land_note": "small neutral detail lift only",
        },
        "water": {
            "land_tint": "none",
            "land_strength": 0.00,
            "land_note": "water-dominant; let M1 depth and future M2 reef layers lead",
        },
        "none": {
            "land_tint": "none",
            "land_strength": 0.00,
            "land_note": "no meaningful land-cover signal in bbox",
        },
    }
    hint = {
        "region": row["region"],
        "label": row["label"],
        "climate_family": climate,
        "land_family": land,
        "m4_climate_baseline": climate_presets.get(climate, climate_presets["none"]),
        "m3_land_bias": land_presets.get(land, land_presets["none"]),
        "confidence": {
            "koppen_land_climate_pct": row["koppen"]["land_climate_pct"],
            "worldcover_water_pct": row["worldcover"]["water_pct"],
            "worldcover_vegetated_pct": row["worldcover"]["vegetated_pct"],
        },
    }
    water_pct = row["worldcover"]["water_pct"]
    land_climate_pct = row["koppen"]["land_climate_pct"]
    if water_pct >= 70 or land_climate_pct < 1:
        hint["priority_note"] = "water_or_ocean_dominant_region; apply land/climate hints conservatively"
    elif climate in {"tropical", "arid"}:
        hint["priority_note"] = "high_value_visual_baseline_candidate"
    else:
        hint["priority_note"] = "standard_review_candidate"
    return hint


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "region",
        "label",
        "lon_w",
        "lon_e",
        "lat_s",
        "lat_n",
        "worldcover_top_land_code",
        "worldcover_top_land_label",
        "worldcover_family",
        "worldcover_water_pct",
        "worldcover_vegetated_pct",
        "worldcover_bare_pct",
        "worldcover_built_pct",
        "worldcover_ice_pct",
        "koppen_top_code",
        "koppen_top_label",
        "koppen_family",
        "koppen_land_climate_pct",
        "koppen_tropical_pct",
        "koppen_arid_pct",
        "koppen_temperate_pct",
        "koppen_cold_pct",
        "koppen_polar_pct",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            wc_top = row["worldcover"]["top_land_class"] or {}
            kp_top = row["koppen"]["top_class"] or {}
            bounds = row["bounds"]
            writer.writerow(
                {
                    "region": row["region"],
                    "label": row["label"],
                    "lon_w": bounds["lon_w"],
                    "lon_e": bounds["lon_e"],
                    "lat_s": bounds["lat_s"],
                    "lat_n": bounds["lat_n"],
                    "worldcover_top_land_code": wc_top.get("code"),
                    "worldcover_top_land_label": wc_top.get("label"),
                    "worldcover_family": row["worldcover"]["family"],
                    "worldcover_water_pct": row["worldcover"]["water_pct"],
                    "worldcover_vegetated_pct": row["worldcover"]["vegetated_pct"],
                    "worldcover_bare_pct": row["worldcover"]["bare_pct"],
                    "worldcover_built_pct": row["worldcover"]["built_pct"],
                    "worldcover_ice_pct": row["worldcover"]["ice_pct"],
                    "koppen_top_code": kp_top.get("code"),
                    "koppen_top_label": kp_top.get("label"),
                    "koppen_family": row["koppen"]["family"],
                    "koppen_land_climate_pct": row["koppen"]["land_climate_pct"],
                    "koppen_tropical_pct": row["koppen"]["tropical_pct"],
                    "koppen_arid_pct": row["koppen"]["arid_pct"],
                    "koppen_temperate_pct": row["koppen"]["temperate_pct"],
                    "koppen_cold_pct": row["koppen"]["cold_pct"],
                    "koppen_polar_pct": row["koppen"]["polar_pct"],
                }
            )


def write_markdown(rows: list[dict[str, Any]], path: Path) -> None:
    high_coral = {
        "hawaii",
        "maldives",
        "great_barrier_reef",
        "philippines_central",
        "caribbean_bahamas",
        "south_china_sea",
        "ryukyu",
        "indonesia_east",
    }
    selected = [row for row in rows if row["region"] in high_coral]
    lines = [
        "# RDL M3/M4 Region Sampler — 2026-06-26",
        "",
        "## Scope",
        "",
        "This report samples existing 8K categorical rasters for all RDL regions:",
        "",
        "- M3 ESA WorldCover land-cover classes",
        "- M4 Koppen-Geiger 1991-2020 climate classes",
        "",
        "No texture, mask, source raster, runtime code, git staging, or deployment was changed.",
        "",
        "Full outputs:",
        "",
        "- `m3_m4_region_histograms.json`",
        "- `m3_m4_region_summary.csv`",
        "- `m3_m4_visual_hints.json`",
        "",
        "## High-Priority Region Snapshot",
        "",
        "| Region | WorldCover top land | WC family | Water % | Koppen top | Climate family | Climate land % |",
        "|---|---|---|---:|---|---|---:|",
    ]
    for row in selected:
        wc_top = row["worldcover"]["top_land_class"] or {"code": "-", "label": "None"}
        kp_top = row["koppen"]["top_class"] or {"code": "-", "label": "None"}
        lines.append(
            "| {region} | {wc_code} {wc_label} | {wc_family} | {water:.2f} | "
            "{kp_code} {kp_label} | {kp_family} | {land:.2f} |".format(
                region=row["region"],
                wc_code=wc_top.get("code"),
                wc_label=wc_top.get("label"),
                wc_family=row["worldcover"]["family"],
                water=row["worldcover"]["water_pct"],
                kp_code=kp_top.get("code"),
                kp_label=kp_top.get("label"),
                kp_family=row["koppen"]["family"],
                land=row["koppen"]["land_climate_pct"],
            )
        )
    family_counts = Counter(row["koppen"]["family"] or "none" for row in rows)
    wc_counts = Counter(row["worldcover"]["family"] or "none" for row in rows)
    lines.extend(
        [
            "",
            "## Family Counts",
            "",
            "Koppen top-family counts:",
            "",
        ]
    )
    for key, count in sorted(family_counts.items()):
        lines.append(f"- `{key}`: {count}")
    lines.extend(["", "WorldCover top-land-family counts:", ""])
    for key, count in sorted(wc_counts.items()):
        lines.append(f"- `{key}`: {count}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- M3 can now use the WorldCover histogram to bias land-only visual treatment per region.",
            "- M4 can now use the Koppen histogram to choose region-level Noon Air baseline parameters.",
            "- These summaries are review inputs only; they do not yet change compositing behavior.",
            "- `m3_m4_visual_hints.json` is a conservative parameter sketch, not an applied config.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sample M3 WorldCover and M4 Koppen classes for RDL regions.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    for path in [REGION_SOURCE, WORLDCOVER_TIF, KOPPEN_TIF, KOPPEN_MANIFEST]:
        if not path.exists():
            raise FileNotFoundError(path)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    regions = load_regions()
    koppen_labels = read_koppen_classes()
    print(f"[load] WorldCover: {WORLDCOVER_TIF}")
    worldcover = tifffile.imread(WORLDCOVER_TIF)
    print(f"[load] Koppen: {KOPPEN_TIF}")
    koppen = tifffile.imread(KOPPEN_TIF)
    if worldcover.shape != (4096, 8192):
        raise ValueError(f"unexpected WorldCover shape: {worldcover.shape}")
    if koppen.shape != (4096, 8192):
        raise ValueError(f"unexpected Koppen shape: {koppen.shape}")

    rows = [
        summarize_region(region_id, cfg, worldcover, koppen, koppen_labels)
        for region_id, cfg in sorted(regions.items())
    ]
    payload = {
        "generated_at": "2026-06-26",
        "scope": "RDL M3/M4 region categorical raster sampling only",
        "sources": {
            "regions": str(REGION_SOURCE.relative_to(ROOT)),
            "worldcover": str(WORLDCOVER_TIF.relative_to(ROOT)),
            "koppen": str(KOPPEN_TIF.relative_to(ROOT)),
        },
        "region_count": len(rows),
        "regions": rows,
    }
    json_path = args.out_dir / "m3_m4_region_histograms.json"
    csv_path = args.out_dir / "m3_m4_region_summary.csv"
    hints_path = args.out_dir / "m3_m4_visual_hints.json"
    md_path = args.out_dir / "README.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    write_csv(rows, csv_path)
    hints = {
        "generated_at": "2026-06-26",
        "scope": "Review-only M3/M4 visual hints derived from categorical histograms",
        "applied_to_compositor": False,
        "regions": [visual_hints_for(row) for row in rows],
    }
    hints_path.write_text(json.dumps(hints, indent=2, ensure_ascii=False) + "\n")
    write_markdown(rows, md_path)
    print(f"[write] {json_path}")
    print(f"[write] {csv_path}")
    print(f"[write] {hints_path}")
    print(f"[write] {md_path}")
    print(f"[done] regions={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
