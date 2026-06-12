# RDL v2 Japan Visual Tile Prototype — Results

**Date:** 2026-06-08  
**Region:** 118_150_22_50 (lon 118–150°E, lat 22–50°N)  
**Stage:** Visual Tile Prototype — isolated validation, NOT formal earth3d.js integration

---

## Phase Positioning — Must Read

**This is a prototype validation run, not the final Japan high-quality texture.**

| What this prototype IS | What this prototype is NOT |
|---|---|
| Validation of GEBCO 2026 bathymetry in a Japan tile | Final Japan high-precision regional tile |
| Validation of GSHHG coastline/bay/island detail | Terrain/mountain precision solution (needs DEM) |
| Proof-of-concept for d5b + GEBCO + GSHHG composition | Formal earth3d.js integration |
| Benchmark for 2048 vs 4096 decision | Global texture upgrade |
| Input to decision: proceed to demo-on-globe stage? | RodiO production deployment |

**Land terrain precision (30m DEM) is explicitly out of scope.** Mountain shapes, elevation hillshade, and land terrain fine-detail are pending DEM Phase (Copernicus GLO-30 / ALOS AW3D30). Layer 1 in this prototype only provides limited visual texture compensation at ~2.1× upscale from the 21.6K source — it does not resolve land terrain.

**demo_japan_v2_tile.html** is an isolated prototype demo for visual validation only. It does not represent formal earth3d.js integration, RodiO production deployment, or any modification of the live globe.

---

## 4096 vs 2048 — What Is Actually New

| Resolution | GEBCO bathy detail | GSHHG coast/island detail | Land area |
|---|---|---|---|
| **4096×3584** (v2_4096) | ✅ Real — native 7680×6720, downscaled ×1.875 | ✅ Real — vector rasterized at target res | ⚠ d5b 8K crop upsampled ×5.6 — NOT real 4096 land detail |
| **2048×1792** (v2_2048) | ✅ Real — native data, downscaled ×3.75 | ✅ Real | ⚠ d5b 8K crop upsampled ×2.8 |

**4096 vs 2048 value is primarily in ocean / coastline / island areas, not land areas.** Any apparent land texture difference between 2048 and 4096 is upsampling artifact, not real new information.

---

## Input Data Summary

| Layer | Source | Resolution | Notes |
|---|---|---|---|
| L0: Baseline | d5b_design_v3_2_1_8192x4096.jpg | 8K, crop ~728×637 | ⚠ upsampled 5.6× for 4096 tile |
| L1: Visual texture comp. | earth_day_source_21600x10800.jpg | Crop ~1920×1680 | ⚠ upsampled 2.1× for 4096 tile |
| L2: GEBCO 2026 tint | gebco_bathymetry_tint.png | 7680×6720 (15 arc-sec) | ✅ true 4096 ocean detail |
| L3: GSHHG clarity | gshhg_coastline_mask.png | 4096×3584 native | ✅ true 4096 coastline detail |

**GSHHG L1 clarification:** GSHHG L1 = Level 1 polygon layer (land/sea boundaries), NOT "low resolution". The source file used is `GSHHS_f_L1.shp` where `f` = full resolution (~25m accuracy). 7820 polygons in the Japan region. The GSHHG levels (L1–L6) refer to polygon hierarchy (L1=ocean coastlines, L2=lakes, L3=islands in lakes, etc.), not detail grade.

---

## Composite Parameters (Main Recommendation)

| Parameter | Value | Tested Range |
|---|---|---|
| GEBCO bathymetry blend | **0.35** | 0.25 / 0.35 / 0.40 |
| GSHHG coastal zone | **10km** | 5km / 10km / 20km |
| GSHHG clarity strength | **0.15** | 0.10 / 0.15 / 0.20 |
| Layer 1 visual blend | **0.30** | 0.30 / 0.45 |

Contact sheets for GEBCO blend, GSHHG zone, and GSHHG strength variations are in `02_tiles/`.

---

## Visual Inspection Guide

Open the comparison images to assess:

### Ocean / Bathymetry (GEBCO L2)
- `02_tiles/baseline_vs_etopo_vs_v2_compare.png` — full tile 4-panel comparison
- `04_crops/crop_01_japan_sea_basin_compare.png` — Japan Sea deep basin structure
- `04_crops/crop_02_japan_trench_compare.png` — Japan Trench / outer rise
- `04_crops/crop_03_east_china_shelf_compare.png` — ECS continental shelf gradient
- `04_crops/crop_04_okinawa_trough_ryukyu_compare.png` — Okinawa Trough, Ryukyu Arc
- `02_tiles/gebco_blend_contact_sheet.png` — 0.25 / 0.35 / 0.40 blend comparison

### Coastline / Bays / Islands (GSHHG L3)
- `04_crops/crop_05_tokyo_bay_compare.png` — Tokyo Bay inner detail
- `04_crops/crop_06_osaka_seto_compare.png` — Osaka Bay / Seto Inland Sea
- `04_crops/crop_07_ise_bay_compare.png` — Ise Bay
- `04_crops/crop_08_ryukyu_islands_compare.png` — Ryukyu island chain
- `04_crops/crop_09_kyushu_west_compare.png` — Kyushu West coast
- `02_tiles/gshhg_zone_contact_sheet.png` — 5km / 10km / 20km zone comparison
- `02_tiles/gshhg_strength_contact_sheet.png` — 0.10 / 0.15 / 0.20 strength comparison

### Demo
- `03_demo/demo_japan_v2_tile.html` — open in browser; toggle baseline/etopo_reference/v2_2048/v2_4096, adjust blend, test distances 1.50/1.35/1.25
- `03_demo/demo_uv_bounds_outline.png` — UV bounds verification (red rectangle on d5b 8K globe texture)

---

## Verification Checklist

Before recording the verdicts below, verify:
- [ ] UV bounds outline shows Japan / Japan Sea / East China Sea region correctly
- [ ] demo_japan_v2_tile.html loads in browser without errors
- [ ] v2_4096 ocean areas show clearly different depth zones vs baseline
- [ ] v2_4096 coastal areas show detail improvement in Tokyo Bay / Seto / Ryukyu
- [ ] No visible GIS-style contour lines, political borders, or map edge artifacts
- [ ] No coastline displacement, dirty edges, or black border artifacts

---

## Verdict Table

*Fill in after visual inspection. Use Yes / No / Partial only.*

| Verification Item | Verdict | Notes |
|---|---|---|
| GEBCO ocean depth clearly better than ETOPO1 | — | Compare panels 2→4 in baseline_vs_etopo_vs_v2_compare.png |
| GSHHG coastline clearly improves bays/islands | — | Check crop_05 through crop_09 |
| v2_gebco_gshhg_tile clearly better than baseline | — | — |
| 2048 sufficient (no significant 4096 ocean/coast gain) | — | Compare tile_2048_vs_4096_compare.png |
| 4096 worth it (visible ocean/coast gain over 2048) | — | Same |
| GIS / map-style feel detected | — | Contour lines, edge artifacts, cold scientific tone |
| Proceed to independent demo on-globe verification | — | — |
| Proceed to formal earth3d.js integration | — | Should be No at this stage |
| Next step: DEM Phase (Copernicus/ALOS for land terrain) | — | — |
| Continue deferring Layer 6 (city roads / city lights) | — | — |

---

## Technical Notes

### Baseline upsampling
Layer 0 baseline is a d5b 8K local crop of ~728×637 pixels, upsampled 5.6× to 4096×3584. At 4096 output, land areas have no additional information versus 2048. This is used purely as a color/style baseline — not as a high-detail land source.

### Layer 1 limitation
21.6K source effective crop is ~1920×1680 pixels, upsampled 2.1× to reach 4096×3584. While this is better than the d5b 8K crop, it still does not provide 4096-grade land terrain detail. Any improvement in land areas comes from this 2.1× upscale plus histogram matching to d5b color, not from genuine sub-km terrain resolution.

### GSHHG coastal zone implementation
Coastal zone is computed as all pixels within `zone_km` of the land/sea boundary (both ocean side and land side), using `scipy.ndimage.distance_transform_edt`. At 4096×3584 for 32°×28° region, pixel density ≈ 1.43 px/km. 10km zone ≈ 14.3 pixels. The clarity enhancement (unsharp mask at strength 0.15) is applied only within this zone to improve visual sharpness without drawing visible lines.

### HTTP Range / GEBCO note
GEBCO tint was derived from the Japan subset downloaded via HTTP Range byte-offset from CEDA (`DATA_OFFSET=1,058,396`, specific to GEBCO 2026). See P0 README for risk details.

### Demo boundary
`demo_japan_v2_tile.html` is an isolated prototype. The UV region shader blends the Japan tile onto the d5b globe within `[uMin=0.8278, uMax=0.9167] × [vMin=0.6222, vMax=0.7778]` with 2-pixel smoothstep feathering. No earth3d.js code was modified.

---

## What Comes Next (Pending Verdicts)

If verdicts are positive:

1. **Immediate next step**: independent on-globe demo (separate HTML, verified bounds, camera/lighting matching production globe)
2. **Medium term**: DEM Phase — Copernicus GLO-30 or ALOS AW3D30 for land terrain hillshade
3. **After DEM stable**: formal earth3d.js integration planning
4. **Deferred**: Layer 6 (OSM road glow, VIIRS city lights) — separate phase after natural geography stable
5. **Global pipeline**: abstract Japan workflow into `rdl_tile_compositor.py --bounds` for all regions (script already supports this)
