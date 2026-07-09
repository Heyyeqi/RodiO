# File Inventory — rdl_v2_japan_visual_tile_prototype

**Date:** 2026-06-08
**Region:** 118_150_22_50
**Generator:** `scripts/geo/rdl_tile_compositor.py v1.0.0`

---

## 01_layers/ — Layer images

| File | Size | Description |
|---|---|---|
| `layer0_baseline_d5b_crop.png` | 8.0MB | d5b 8K crop 728×637 → 4096×3584 (Lanczos). Upsampled ×5.6. Comparison baseline only. |
| `layer1_visual_texture_matched.png` | 8.0MB | 21.6K source crop 1920×1680 → 4096×3584, histogram-matched to L0. Upsampled ×2.1. Not true 4096 land detail. |
| `layer2_gebco_bathymetry_tint_035.png` | 2.0MB | GEBCO 2026 5-level depth tint, 7680×6720 → 4096×3584. Ocean only in final composite. |
| `layer3_gshhg_clarity_10km_015.png` | 8.0MB | Composite with coastal zone highlighted (blue tint = 10km zone, 6.86% of pixels). |
| `layer_stack_contact_sheet.png` | 4.0MB | 5-panel contact sheet: L0→L1→L2→L3_zone→composite |

## 02_tiles/ — Final tiles and comparison images

| File | Size | Description |
|---|---|---|
| `v2_gebco_gshhg_tile_4096.png` | 10MB | **Main output.** 4096×3584, GEBCO blend=0.35, GSHHG zone=10km, str=0.15, visual=0.30. |
| `v2_gebco_gshhg_tile_2048.png` | 4.0MB | 2048×1792, same parameters. Generated from scratch (not downscaled from 4096). |
| `baseline_d5b_crop_4096.png` | 8.0MB | Pure d5b baseline at 4096×3584. For demo and comparison. |
| `baseline_d5b_crop_2048.png` | 3.0MB | Pure d5b baseline at 2048×1792. |
| `etopo_reference_4096.png` | 9.0MB | d5b + ETOPO1 tint + GSHHG clarity at 4096×3584. Reference for v1-style comparison. |
| `etopo_reference_2048.png` | 4.0MB | Same at 2048×1792. For demo. |
| `baseline_vs_etopo_vs_v2_compare.png` | 4.0MB | 4-panel: baseline \| etopo_reference \| v2_2048 \| v2_4096 (at 1024px per panel) |
| `tile_2048_vs_4096_compare.png` | 7.0MB | Side-by-side: v2_2048 \| v2_4096 (displayed at 2048px each) |
| `gebco_blend_contact_sheet.png` | 3.0MB | 3-panel: GEBCO blend 0.25 / 0.35 / 0.40 |
| `gshhg_zone_contact_sheet.png` | 2.0MB | 3-panel: GSHHG zone 5km / 10km / 20km |
| `gshhg_strength_contact_sheet.png` | 2.0MB | 3-panel: GSHHG strength 0.10 / 0.15 / 0.20 |

## 03_demo/ — Standalone demo

| File | Size | Description |
|---|---|---|
| `demo_japan_v2_tile.html` | 8.0KB | Standalone Three.js r128 globe (CDN). UV region shader blend. Baseline/etopo_ref/v2_2048/v2_4096 toggle. Blend slider, distance buttons, FPS. No earth3d.js modification. |
| `demo_uv_bounds_outline.png` | 4.0MB | UV bounds verification: red rectangle drawn on d5b 8K, rescaled to 2160px wide. Confirms Japan/Japan Sea/East China Sea coverage. |

## 04_crops/ — Key region crop comparisons

All crops show 4 panels: `baseline | etopo_reference | v2_2048 | v2_4096`

| File | Size | Region | Crop px (per panel) |
|---|---|---|---|
| `crop_01_japan_sea_basin_compare.png` | 708KB | Japan Sea Basin (130–140°E, 37–43°N) | 1280×768 |
| `crop_02_japan_trench_compare.png` | 580KB | Japan Trench (141–149°E, 33–40°N) | 1024×896 |
| `crop_03_east_china_shelf_compare.png` | 772KB | East China Shelf (119–128°E, 25–32°N) | 1152×896 |
| `crop_04_okinawa_trough_ryukyu_compare.png` | 772KB | Okinawa Trough / Ryukyu (122–132°E, 23–29°N) | 1280×768 |
| `crop_05_tokyo_bay_compare.png` | 324KB | Tokyo Bay (138.5–141°E, 34.5–36.5°N) | 320×256 |
| `crop_06_osaka_seto_compare.png` | 772KB | Osaka Bay / Seto Inland Sea (132–137°E, 33–36°N) | 640×384 |
| `crop_07_ise_bay_compare.png` | 324KB | Ise Bay (135.5–138.5°E, 33.5–35.5°N) | 384×256 |
| `crop_08_ryukyu_islands_compare.png` | 644KB | Ryukyu Islands (123–131°E, 24–28°N) | 1024×512 |
| `crop_09_kyushu_west_compare.png` | 708KB | Kyushu West (127–132°E, 30–34°N) | 640×512 |

## 05_reports/ — Documentation

| File | Description |
|---|---|
| `README_PROTOTYPE.md` | Phase positioning, layer definitions, parameter summary, verdict table |
| `FILE_INVENTORY.md` | This file |
| `NEXT_STEP_RECOMMENDATION.md` | Decision tree for post-prototype next steps |
| `metadata.json` | Machine-readable record: bounds, UV, sources, blends, commands, timestamps |

---

## Source Files Used (not in this directory)

| File | Size | Role |
|---|---|---|
| `pwa/assets/earth/candidates/d5b_design_v3_2_1_8192x4096.jpg` | 8.0MB | Base texture (read-only, not modified) |
| `pwa/assets/source/earth_day_source_21600x10800.jpg` | 20MB | 21.6K visual source (read-only, not modified) |
| `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/gebco_bathymetry_tint.png` | 892KB | GEBCO 2026 5-level depth tint from P0 |
| `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/etopo1_bathymetry_tint.png` | 81KB | ETOPO1 depth tint from P0 (reference only) |
| `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/gshhg_coastline_mask.png` | 161KB | GSHHG L1 mask from P0 (sea/land/edge RGB) |
| `pwa/assets/source/bathy/gebco_2026/gebco_2026_118_150_22_50.nc` | 46MB | GEBCO 2026 NetCDF (used in P0, not directly here) |
| `pwa/assets/source/coastline/gshhg/GSHHS_shp/f/GSHHS_f_L1.shp` | 154MB | GSHHG full-res source (used in P0, not directly here) |
