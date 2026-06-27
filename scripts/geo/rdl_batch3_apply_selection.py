#!/usr/bin/env python3.11
"""
rdl_batch3_apply_selection.py — Apply Batch 3 landforms selection decisions

For each "keep" region: promotes tile_noon_air_mapbox_m3m4_dem_landforms.jpg
to tile_noon_air_mapbox.jpg (backing up the previous version as _pre_landforms.jpg).

For "revert" regions: no-op (leaves tile_noon_air_mapbox.jpg untouched).

Usage:
  python3.11 scripts/geo/rdl_batch3_apply_selection.py [--dry-run]

  --dry-run   Print what would happen without writing any files.
"""

import shutil
import argparse
from pathlib import Path

TILES_DIR = Path(__file__).parent.parent.parent / (
    "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions"
)

# Batch 3 selection results (2026-06-27, 63 keep / 21 revert)
KEEP = [
    "sea_of_japan", "great_barrier_reef", "mediterranean_west", "adriatic_sea",
    "french_guiana", "norway_fjords", "bay_of_biscay", "indonesia_west",
    "hainan_island", "sri_lanka", "taiwan_strait", "singapore_malacca",
    "madagascar", "borneo", "rio_southeast_brazil", "arabian_sea",
    "papua_new_guinea", "bay_of_bengal", "british_isles", "gulf_mexico_yucatan",
    "abc_venezuela", "alaska", "central_america_pacific", "indonesia_east",
    "philippines_central", "korea_yellow_sea", "japan", "brazil_coast",
    "east_china_sea", "caribbean_bahamas", "iceland", "taiwan",
    "andaman_sea", "kuril_southern", "new_zealand", "puerto_rico_vi",
    "falkland_islands", "nansha_spratly", "faroe_islands", "bashi_channel",
    "south_china_sea", "new_caledonia", "solomon_islands", "galapagos",
    "canary_madeira", "hawaii", "fiji_vanuatu", "eastern_caribbean",
    # manual review — accepted as-is
    "south_africa", "caspian_sea", "red_sea", "rio_de_la_plata",
    "black_sea", "baltic_sea", "gulf_of_thailand", "bohai_sea",
    "mozambique_channel", "east_africa_coast", "persian_gulf",
    "patagonia", "mediterranean_east", "peru_chile_coast", "california_coast",
]

REVERT = [
    "cape_verde", "south_georgia", "french_polynesia", "samoa", "azores",
    "ryukyu", "guam_marianas", "christmas_island", "palau", "marshall_islands",
    "tonga", "maldives", "easter_island", "seychelles", "kiribati_gilbert",
    "ogasawara", "micronesia", "xisha_paracel", "dongsha_pratas",
    "bermuda", "svalbard",
]

SRC_NAME  = "tile_noon_air_mapbox_m3m4_dem_landforms.jpg"
DEST_NAME = "tile_noon_air_mapbox.jpg"
BACKUP_NAME = "tile_noon_air_mapbox_pre_landforms.jpg"


def apply(dry_run: bool) -> None:
    tag = "[dry-run] " if dry_run else ""
    applied = []
    skipped_missing = []

    for region in KEEP:
        region_dir = TILES_DIR / region
        src  = region_dir / SRC_NAME
        dest = region_dir / DEST_NAME
        backup = region_dir / BACKUP_NAME

        if not src.exists():
            skipped_missing.append(region)
            print(f"  SKIP  {region} — {SRC_NAME} not found")
            continue

        if not dry_run:
            if dest.exists() and not backup.exists():
                shutil.copy2(dest, backup)
            shutil.copy2(src, dest)

        applied.append(region)
        print(f"  {tag}APPLY {region}")

    print()
    print(f"Keep:   {len(KEEP)} regions → applied {len(applied)}, skipped {len(skipped_missing)}")
    print(f"Revert: {len(REVERT)} regions — no changes")
    if skipped_missing:
        print(f"Missing src: {skipped_missing}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    mode = "DRY RUN" if args.dry_run else "APPLY"
    print(f"=== Batch 3 landforms selection apply — {mode} ===")
    print(f"Tiles dir: {TILES_DIR}\n")
    apply(args.dry_run)
