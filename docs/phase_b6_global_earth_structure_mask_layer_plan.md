# Phase B-6 — Global Earth Structure Mask Layer Plan

> Created: 2026-06-10
> Status: Planning document only
> Scope: architecture, asset audit, mask design, integration plan
> Strict non-execution: no code changes, no generator run, no calibration, no full-res, no image/mask generation, no commit, no push

## 0. Why B-6 Exists

### 0.1 Current Stable State

The current online Day Earth texture is `d5z_b`.

- Production texture must remain unchanged.
- `DAY_TEXTURE_VARIANT` must remain unchanged.
- B-6 is not a launch or frontend replacement phase.
- B-6 must not write to `pwa/assets/earth/production/`.
- B-6 must not copy anything to `pwa/assets/earth/candidates/`.
- B-6 must not touch `pwa/earth3d.js`.

B-6 is a structure-layer planning phase. It is not a Noon Air color tuning phase.

### 0.2 B-4 / B-5 Failure Chain

#### B-4

Observed failures:

- Black seas.
- Rectangular patch artifacts.
- French Polynesia horizontal hard cut.
- Shallow shelf and island halo results were covered by later logic.

Root causes:

- `final_harmony_guard` participated in image mutation, blending protected rectangles back toward `d5z_b`.
- Source-derived generation and `d5z_b` baseline guard semantics were mismatched.
- Ocean system had a cascading darkening risk because deep-ocean classification was recomputed from already-mutated pixels.
- There was no reliable shallow / reef / shelf structure recognition.

#### B-5.1

Observed failures:

- Black seas were partially relieved.
- Large blue rectangular patches appeared.

Root causes:

- `_TROPICAL_FLOOR_ZONES` used broad geographic bboxes.
- Tropical floor lifted whole rectangular tropical ocean regions rather than real shallow-water structures.
- This violated the Noon Air spec rule against large bright-blue blocks.

#### B-5.2

Observed failures:

- Rectangular patches disappeared.
- Maldives, French Polynesia, Pacific Islands, Hawaii, and Caribbean became too dark again.
- Red Sea and Yellow / East China remained unresolved.

Root causes:

- Removing tropical floor removed the only strong local brightness rescue.
- Existing island halo and shallow proxy logic were too weak.
- Global floor can prevent near-black water, but cannot build shallow sea hierarchy.
- Small islands and atolls are too small at 2K for RGB/luminance proxy plus crop mean metrics.
- The generator lacks real reef / shelf / coastline / bathymetry structure layers.

#### B-5.3A Codex Deep Audit

Conclusion:

- The root cause is not a single color parameter.
- The current source-derived pipeline lacks stable bathymetry / coastline / reef / shelf structure masks.
- B-5.3 circle masks are temporary proxies, not a root-cause solution.
- The project should enter a Global Earth Structure Mask Layer phase before continuing local color patches.

## 1. B-6 Goal Definition

### 1.1 Goal

B-6 establishes a reusable, cacheable, auditable Global Earth Structure Mask Layer for the RodiO Earth visual system.

The goal is not to tune Noon Air colors. The goal is to stop every theme generator from guessing physical structure using mutable RGB/luminance heuristics.

The structure layer should serve:

- Noon Air.
- Morning.
- Afternoon.
- Evening.
- Deep Night.
- Weather.
- Seven-day / planetary transitions.
- Music-linked visual changes.
- Future 8K and 21.6K Earth texture upgrades.

### 1.2 Planned Outputs

Future B-6 deliverables should include at least:

```text
d5b_processor_v3/earth_structure_masks/
d5b_processor_v3/earth_structure_masks/generate_structure_masks.py
d5b_processor_v3/earth_structure_masks/config.py
d5b_processor_v3/earth_structure_masks/README.md
d5b_processor_v3/earth_structure_masks/output/structure_masks_2048x1024.npz
d5b_processor_v3/earth_structure_masks/output/structure_masks_8192x4096.npz
d5b_processor_v3/earth_structure_masks/output/structure_mask_metadata.json
d5b_processor_v3/earth_structure_masks/previews/
docs/phase_b6_global_earth_structure_mask_layer_plan.md
docs/phase_b6_1_asset_audit.md
docs/phase_b6_2_structure_mask_prototype_plan.md
```

This document only plans those outputs. It does not create code, masks, previews, or images.

### 1.3 Relationship To d6 Noon Air Generator

B-6 must be independent of `d6_noon_air_earth_generator.py`.

Future integration model:

- B-6 generates `.npz` structure masks.
- d6 reads B-6 masks.
- d6 no longer guesses shallow sea / reef / shelf using RGB/luminance proxy.
- d6 applies Noon Air aesthetic decisions to physically meaningful masks.
- Future theme generators reuse the same structure layer.

## 2. Read-Only Asset Audit

### 2.1 Scan Commands Executed

Read-only scans were performed with:

```bash
find pwa/assets pwa/assets/source pwa/assets/earth d5b_processor_v3 d5b_processor_v3/data d5b_processor_v3/d5b_output d5b_processor_v3/scripts docs previews -maxdepth 3 -type f -print
du -sh pwa/assets pwa/assets/source pwa/assets/earth d5b_processor_v3 d5b_processor_v3/data d5b_processor_v3/d5b_output d5b_processor_v3/scripts docs previews
find pwa/assets/source pwa/assets/earth/masks scripts/geo previews/rdl_v2_p0_gebco_gshhg_japan_benchmark previews/rdl_v2_japan_visual_tile_prototype previews/regional_detail_mvp_japan_eastsea_v2_audit -maxdepth 4 -type f \( -iname '*etopo*' -o -iname '*gebco*' -o -iname '*gshhg*' -o -iname '*coast*' -o -iname '*bathy*' -o -iname '*mask*' -o -iname '*dem*' -o -iname '*elevation*' -o -iname '*topo*' -o -iname '*shelf*' -o -iname '*distance*' \) -print
file pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd.gz pwa/assets/source/bathy/gebco_2026/gebco_2026_118_150_22_50.nc pwa/assets/source/coastline/gshhg/gshhg-shp-2.3.7.zip pwa/assets/earth/masks/ocean_mask_4096x2048_soft.png pwa/assets/earth/masks/ocean_specular_4096x2048.png
rg -n -i "ETOPO|ETOPO1|GEBCO|GSHHG|NaturalEarth|Natural Earth|DEM|bathymetry|coastline|coast|shore|land_mask|ocean_mask|sea_mask|shelf|reef|atoll|island|RDL|VIIRS|OSM|GLOBE|elevation|topography|relief|japan|yellow sea|red sea|maldives|bahamas" pwa/assets d5b_processor_v3 docs previews
```

Directory findings:

- `pwa/assets/`: exists, about 2.0G.
- `pwa/assets/source/`: exists, about 1.8G.
- `pwa/assets/earth/`: exists, about 103M.
- `d5b_processor_v3/`: exists, about 117M.
- `d5b_processor_v3/data/`: does not exist.
- `d5b_processor_v3/d5b_output/`: exists, about 116M.
- `d5b_processor_v3/scripts/`: does not exist.
- `docs/`: exists, about 560K.
- `previews/`: exists, about 299M.
- Additional relevant directory: `scripts/geo/` exists and contains GEBCO/GSHHG/RDL scripts.

### 2.2 Asset Table

| Asset | Path | Type | Scope | Resolution | Format | Size | Used By Current Pipeline? | Can Use For B-6? | Confidence |
|---|---|---|---|---|---|---:|---|---|---|
| ETOPO1 Ice Surface Grid | `pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd` | bathymetry + topography | global | 21601x10801 / 1 arc-min | NetCDF `.grd` | 890M | used by bathy/RDL scripts, not d6 | yes | high |
| ETOPO1 compressed source | `pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd.gz` | source archive | global | 21601x10801 | gzip NetCDF | 377M | no | backup only | high |
| GEBCO 2026 Japan subset | `pwa/assets/source/bathy/gebco_2026/gebco_2026_118_150_22_50.nc` | bathymetry/topography | Japan region | 6720x7680 per docs | HDF5 NetCDF | 46M | RDL Japan scripts/previews | partial | high |
| GSHHG full-res package | `pwa/assets/source/coastline/gshhg/gshhg-shp-2.3.7.zip` | coastline archive | global | vector | zip/shp | 142M | RDL scripts | yes | high |
| GSHHG full-res land polygons | `pwa/assets/source/coastline/gshhg/GSHHS_shp/f/GSHHS_f_L1.shp` | coastline/land polygons | global | vector, full-res | shp | 154M | RDL Japan script | yes | high |
| GSHHG lower tiers | `pwa/assets/source/coastline/gshhg/GSHHS_shp/{c,l,i,h}/...` | coastline/land polygons | global | vector tiers | shp/dbf/shx | varied | not d6 | yes, fallback/perf | high |
| WDBII rivers/borders | `pwa/assets/source/coastline/gshhg/WDBII_shp/...` | rivers/borders | global | vector tiers | shp | varied | not d6 | partial | medium |
| Earth day source | `pwa/assets/source/earth_day_source_21600x10800.jpg` | source image | global | 21600x10800 | jpg | 20M | d6 input | partial, texture reference only | high |
| D5z production texture | `pwa/assets/earth/production/d5z_b_8192x4096.jpg` | production texture | global | 8192x4096 | jpg | unknown in scan table | production runtime | no for mask generation; yes for comparison | high |
| D5z candidate copy | `pwa/assets/earth/candidates/d5z_b_8192x4096.jpg` | baseline texture | global | 8192x4096 | jpg | d6 guard/reference | no for masks; yes reference | high |
| Existing soft ocean mask | `pwa/assets/earth/masks/ocean_mask_4096x2048_soft.png` | mask | global | 4096x2048 | 8-bit grayscale PNG | 398K | earth runtime/specular assets | partial | medium |
| Existing ocean specular | `pwa/assets/earth/masks/ocean_specular_4096x2048.png` | mask/specular | global | 4096x2048 | 8-bit grayscale PNG | 73K | earth runtime | partial | medium |
| Existing 2K ocean specular | `pwa/assets/earth/masks/ocean_specular_2048x1024.png` | mask/specular | global | 2048x1024 | PNG | 29K | earth runtime | partial | medium |
| GSHHG coastline renderer | `scripts/geo/gshhg_coastline_render.py` | script | region-capable | configurable | py | 14K | RDL Japan workflow | yes, adapt | high |
| GEBCO bathy renderer | `scripts/geo/gebco_bathymetry_tint.py` | script | region-capable | configurable | py | 8.9K | RDL Japan workflow | yes, adapt | high |
| RDL retuning script | `scripts/geo/rdl_retuning.py` | script | Japan prototype | regional | py | 22K | RDL Japan workflow | partial | medium |
| RDL tile compositor | `scripts/geo/rdl_tile_compositor.py` | script | Japan tile | regional | py/html | 32K | RDL Japan workflow | partial | medium |
| Japan GSHHG mask preview | `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/gshhg_coastline_mask.png` | output/preview | Japan | 4096x3584 per docs | png | preview | no for d6 | reference only | high |
| Japan GSHHG distance field | `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/gshhg_distance_field.png` | output/preview | Japan | 4096x3584 per docs | png | preview | no for d6 | reference only | high |
| Japan GEBCO tint | `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/gebco_bathymetry_tint.png` | output/preview | Japan | 6720x7680 source-derived | png | preview | no for d6 | reference only | high |
| ETOPO audit outputs | `previews/regional_detail_mvp_japan_eastsea_v2_audit/etopo1_*.png` | output/preview | Japan | regional | png/npy | preview | no for d6 | reference only | high |
| RDL global data audit docs | `previews/rdl_v2_global_data_source_upgrade_audit/*.md` | doc | global planning | n/a | md | small | no | yes, planning | high |
| Bathy validation doc | `docs/devlog_bathy_1_etopo_validation.md` | doc | global ETOPO1 | n/a | md | small | no | yes, reference | high |
| Global color/RDL plan | `docs/global_color_grading_bmng_rdl_phase_plan.md` | doc | global | n/a | md | small | no | yes, architecture | high |
| Current d6 generator | `d5b_processor_v3/d6_noon_air_earth_generator.py` | script | global | 2K/8K | py | n/a | yes | integration target only | high |
| Legacy masks helper | `d5b_processor_v3/masks.py` | script | image-derived | image input | py | n/a | D5 pipeline | partial, not authoritative | medium |

### 2.3 Asset Conclusions

1. Current project has global bathymetry/topography data: yes, ETOPO1 exists at `pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd`.
2. Current project has global coastline data: yes, GSHHG exists and is extracted under `pwa/assets/source/coastline/gshhg/`.
3. Current project has a global land/ocean mask: partially. There is a 4096x2048 soft ocean mask under `pwa/assets/earth/masks/`, and GSHHG can generate a proper one. There is no canonical B-6 `.npz` land/ocean mask yet.
4. GEBCO in the project is Japan-only, not global: `gebco_2026_118_150_22_50.nc`.
5. ETOPO1 is suitable as the B-6 early global structure foundation for 2K and 8K class masks. It is 1 arc-min, matching the 21.6K source grid family, but it is not enough for coral reef detail.
6. GSHHG is suitable for coastline / land-ocean / small-island foundation.
7. Real global reef/atoll data is missing.
8. New data is not needed for B-6.1 asset audit or a B-6.2 2K prototype based on ETOPO1 + GSHHG. New global GEBCO and reef datasets are needed later for higher precision.
9. Immediately usable for 2K prototype: ETOPO1, GSHHG, existing `scripts/geo` logic, existing ocean mask as comparison only.
10. Delay to Phase C / B-7: global GEBCO download, real coral reef/atoll datasets, Copernicus/ALOS DEM, OSM, VIIRS.

## 3. Structure Mask Capability Design

### 3.1 Mask Inventory

| Mask | Purpose | Primary Data Source | Fallback Source | Generation Method | Resolution Target | Output Type | Cache Format | Reusable For Themes? | Risk |
|---|---|---|---|---|---|---|---|---|---|
| `land_mask` | stable land selection | GSHHG L1 polygons | ETOPO1 elevation >= 0m | rasterize global polygons to target grid | 2K, 8K, optional 21.6K | hard + soft edge | uint8 or float32 in npz | yes | GSHHG rasterization complexity |
| `ocean_mask` | stable water selection | inverse GSHHG land | ETOPO1 elevation < 0m | inverse land, resolve lakes if needed | 2K/8K | hard + soft edge | uint8/float32 | yes | inland water semantics |
| `coastline_mask` | coast edge | GSHHG land boundary | morphology from ETOPO1 land | edge detect land/ocean boundary | 2K/8K | soft edge | float32 | yes | too sharp/GIS if used visually |
| `coastline_distance_mask` | coastal influence field | GSHHG land/ocean boundary | ETOPO1 boundary | distance transform, km scaled by latitude | 2K/8K | float32 0..1 | float32 | yes | equirectangular distance distortion |
| `deep_ocean_mask` | deep basin selection | ETOPO1/GEBCO depth | source RGB only for review | depth < -3000m draft | 2K/8K | hard/soft class | float32 | yes | ETOPO1 coarse, trenches generalized |
| `mid_ocean_mask` | mid-depth water | ETOPO1 | none | -3000m <= depth < -1000m draft | 2K/8K | class | float32 | yes | class boundaries need feather |
| `continental_shelf_mask` | broad shelf | ETOPO1, later GEBCO | GSHHG coast distance | -1000m <= depth < -200m draft; feather | 2K/8K | soft | float32 | yes | ETOPO1 may over/under-classify shelves |
| `shallow_sea_mask` | shallow water | ETOPO1, later GEBCO | coastline distance + source brightness | -200m <= depth < -30m draft | 2K/8K | soft | float32 | yes | ETOPO1 insufficient for reefs |
| `nearshore_shallow_mask` | coastal shallow band | ETOPO1 + coastline distance | GSHHG distance | -30m <= depth < 0m plus coast distance < draft 50km | 2K/8K | soft | float32 | yes | coast distance can overreach cliffs/deep coasts |
| `reef_or_atoll_proxy_mask` | reef/atoll enhancement control | requires new reef data | ETOPO1 shallow anomaly + island proximity + anchors | proxy acceptable for B-6 prototype; draft: shallow water near small islands in tropics | 2K/8K | soft | float32 | yes | proxy weak for Maldives/Bahamas/Tuamotu/GBR |
| `island_proximity_mask` | island halo/control | GSHHG small islands | manual anchors fallback | connected components; distance transform around island polygons | 2K/8K | soft distance | float32 | yes | global component processing cost |
| `small_island_mask` | small island pixels | GSHHG polygon area | existing island centers | component area threshold draft < 10,000 km2 | 2K/8K | hard/soft | uint8/float32 | yes | area in projected grid needs geodesic correction |
| `tropical_island_group_mask` | tropical archipelago zones | GSHHG + lat band + anchors | manual island groups | island proximity within lat -30..30 plus known groups | 2K/8K | soft | float32 | yes | manual grouping still needed |
| `high_latitude_island_mask` | cold island handling | GSHHG + lat band | anchors | island proximity above |lat| > 50 | 2K/8K | soft | float32 | yes | ice/land ambiguity |
| `polar_ice_mask` | polar ice treatment | ETOPO1 Ice grid + source brightness | RGB snow proxy | lat + high elevation/ice surface + brightness | 2K/8K | soft | float32 | yes | ETOPO1 Ice includes ice surface not modern sea ice |
| `greenland_ice_mask` | Greenland ice | GSHHG/ETOPO1 region + brightness | region bbox + RGB | Greenland polygon/elevation/brightness | 2K/8K | soft | float32 | yes | seasonal texture mismatch |
| `antarctica_ice_mask` | Antarctica ice | GSHHG/ETOPO1 + lat | lat <= -60 | Antarctica land + brightness | 2K/8K | soft | float32 | yes | coast/shelf ice complexity |
| `sea_ice_proxy_mask` | possible sea ice zones | source brightness + polar water | lat + RGB | polar ocean, bright/low saturation, draft | 2K/8K | soft | float32 | yes | requires temporal/seasonal data for accuracy |
| `polar_coastal_water_mask` | polar coast water | GSHHG coast distance + ocean | ETOPO1 shallow | polar ocean within coast band | 2K/8K | soft | float32 | yes | ice/water ambiguity |
| `desert_mask` | desert color control | source color + regional biome config | arid region bboxes | RGB warm land + known desert regions | 2K/8K | soft | float32 | yes | requires biome data for true global |
| `arid_land_mask` | dryland control | source color + ETOPO1 | region config | low vegetation proxy from source; optional lat regions | 2K/8K | soft | float32 | yes | color proxy still needed without land cover |
| `vegetation_mask` | green land control | source color + land mask | RGB/HSL proxy | green hue on GSHHG land | 2K/8K | soft | float32 | yes | acceptable as aesthetic, not physical |
| `rainforest_mask` | tropical dense green | future land cover | region config + RGB | Amazon/Congo/SEA bbox clipped to vegetation | 2K/8K | soft | float32 | yes | bbox coarse |
| `grassland_mask` | grass/savanna | future land cover | region config + RGB | biome bboxes clipped to land | 2K/8K | soft | float32 | yes | requires new landcover for robust |
| `mountain_mask` | mountain treatment | ETOPO1 elevation | source relief | elevation >1500m draft, slope/local relief | 2K/8K | soft | float32 | yes | ETOPO1 coarse |
| `plateau_mask` | plateau treatment | ETOPO1 elevation + low relief | region config | elevation >2500m and low local relief draft | 2K/8K | soft | float32 | yes | threshold needs tuning |
| `snow_mountain_mask` | snow/ice mountains | ETOPO1 + source brightness | RGB snow proxy | high elevation + bright low-sat pixels | 2K/8K | soft | float32 | yes | clouds/salt lakes false positives |

### 3.2 Special Sea Water-Only Masks

| Mask | Purpose | Primary Data Source | Fallback Source | Generation Method | Resolution Target | Output Type | Cache Format | Reusable For Themes? | Risk |
|---|---|---|---|---|---|---|---|---|---|
| `red_sea_water_mask` | narrow Red Sea water only | GSHHG ocean + bbox | ETOPO1 ocean | bbox clipped by ocean, optionally depth and coast distance | 2K/8K | soft | float32 | yes | 2K narrow width |
| `yellow_sea_water_mask` | turbid shelf water | GSHHG ocean + ETOPO1 shelf + bbox | bbox ocean | bbox clipped by ocean and -200..0m depth | 2K/8K | soft | float32 | yes | turbid land/river ambiguity |
| `east_china_sea_water_mask` | East China shelf | ETOPO1 shelf + ocean + bbox | bbox ocean | water-only bbox, shelf class | 2K/8K | soft | float32 | yes | overlaps Japan/Ryukyu zones |
| `japan_sea_water_mask` | Japan Sea water | ocean + bbox + depth | bbox ocean | water-only bbox | 2K/8K | soft | float32 | yes | coast/depth gradients |
| `mediterranean_water_mask` | Mediterranean water | GSHHG ocean + bbox | bbox ocean | water-only bbox with subregion optional | 2K/8K | soft | float32 | yes | complex islands/coasts |
| `aegean_sea_water_mask` | Aegean island water | GSHHG ocean + island proximity | bbox ocean | water-only bbox + island proximity | 2K/8K | soft | float32 | yes | many small islands |
| `caribbean_water_mask` | Caribbean water | GSHHG ocean + bbox | bbox ocean | water-only bbox + shelf classes | 2K/8K | soft | float32 | yes | broad and diverse |
| `bahamas_bank_mask` | Bahamas banks | ETOPO1/GEBCO shallow + GSHHG | island proximity + bbox | shallow water near Bahamas; requires GEBCO/reef for quality | 2K/8K | soft | float32 | yes | ETOPO1 may miss banks |
| `persian_gulf_water_mask` | Persian Gulf | GSHHG ocean + bbox | bbox ocean | water-only bbox + shallow class | 2K/8K | soft | float32 | yes | turbid shallow water |
| `north_sea_water_mask` | North Sea | ocean + bbox + depth | bbox ocean | shelf water mask | 2K/8K | soft | float32 | yes | land/sea complexity |
| `baltic_sea_water_mask` | Baltic Sea | ocean/inland water + bbox | bbox water | water-only with GSHHG levels | 2K/8K | soft | float32 | yes | GSHHG inland water semantics |
| `south_china_sea_water_mask` | South China Sea | ocean + bbox + shelf | bbox ocean | water-only bbox | 2K/8K | soft | float32 | yes | reef/island detail |
| `coral_sea_water_mask` | Coral Sea | ocean + bbox + shelf/reef proxy | bbox ocean | water-only + shallow classes | 2K/8K | soft | float32 | yes | reef data missing |
| `great_barrier_reef_proxy_mask` | GBR reef proxy | requires reef data or GEBCO | island/coast/shallow proxy | shallow anomalies near Queensland coast | 2K/8K | soft | float32 | yes | ETOPO1 not enough for ribbon reefs |

## 4. Data Source Route Design

### 4.1 ETOPO1

Status:

- Exists at `pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd`.
- Global.
- NetCDF Data Format.
- Documented as 21601x10801, 1 arc-min.
- Good enough for 2K and 8K class global structure masks.
- Not enough for precise coral reefs, small atolls, or narrow coastal detail.

Can generate:

- `land_mask` fallback.
- `ocean_mask` fallback.
- `deep_ocean_mask`.
- `mid_ocean_mask`.
- `continental_shelf_mask`.
- `shallow_sea_mask`.
- `nearshore_shallow_mask`.
- `mountain_mask`.
- `high_mountain_mask`.
- `plateau_mask` draft.
- polar terrain/ice proxy, with caution.

Draft thresholds:

| Class | Draft Threshold | Audit Judgment |
|---|---|---|
| deep_ocean | depth < -3000m | reasonable for basins; may miss trenches as separate class |
| mid_ocean | -3000m <= depth < -1000m | reasonable |
| continental_shelf | -1000m <= depth < -200m | too broad for "shelf"; useful as slope/transition |
| shallow_sea | -200m <= depth < -30m | reasonable first pass |
| nearshore_shallow | -30m <= depth < 0m | reasonable but ETOPO1 coarse |
| land | elevation >= 0m | usable fallback; GSHHG better |
| mountain | elevation > 1500m | reasonable |
| high_mountain | elevation > 3000m | reasonable |
| plateau | elevation > 2500m with low local relief | good concept; local relief threshold must be tuned |

Recommended refinement:

- Use soft bands around thresholds, not hard binary cutoffs.
- Add `depth_gradient` or local slope for shelf/coast transition.
- Use GSHHG for land/ocean boundary, ETOPO1 for depth/elevation classes.

### 4.2 GEBCO

Status:

- Project has GEBCO 2026 Japan subset only: `pwa/assets/source/bathy/gebco_2026/gebco_2026_118_150_22_50.nc`.
- It is not global.
- Existing docs report 6720x7680, 15 arc-sec, 4x better than ETOPO1 for the Japan benchmark.

Use:

- Cannot directly power global B-6.
- Very valuable for Japan / Yellow-East China / Ryukyu prototype validation.
- Global GEBCO would improve Bahamas, Maldives, Red Sea, Yellow Sea, East China Sea, South China Sea, Great Barrier Reef, and all continental shelves.

Cost:

- Global GEBCO will be large and processing-heavy.
- Recommended cache strategy: do not load global high-res GEBCO into d6. Preprocess to 2K/8K `.npz` masks and store metadata/hash.

Recommendation:

- Use ETOPO1 for B-6.2 2K prototype.
- Use Japan GEBCO as validation/control.
- Plan global GEBCO as B-7 or Phase C after B-6 API stabilizes.

### 4.3 GSHHG

Status:

- Exists globally under `pwa/assets/source/coastline/gshhg/`.
- Full-res GSHHS L1 polygons are available.
- Existing `scripts/geo/gshhg_coastline_render.py` can generate land mask + coastline edge + distance field for arbitrary `--bounds`.

Can generate:

- `land_mask`.
- `ocean_mask`.
- `coastline_mask`.
- `coastline_distance_mask`.
- `small_island_mask`.
- `island_proximity_mask`.
- special-sea water-only masks when clipped by bbox.

Processing steps:

1. Load GSHHG L1 polygons at selected tier.
2. Rasterize to equirectangular target grid.
3. Derive ocean as inverse land, with policy for lakes/inland water.
4. Derive coastline edge by morphology.
5. Compute distance transform in approximate km with latitude correction.
6. Run connected-component labeling for islands and island area classes.

Dependency risks:

- Existing scripts likely use geospatial/Python stack such as shapefile/rasterization and image operations. B-6.1 must lock exact dependencies before implementation.
- Full-res global rasterization at 8K may be slow; cache output.

### 4.4 Natural Earth / OSM

Status:

- Natural Earth is referenced in docs and was reportedly downloaded to `/tmp` as interim backup, but no repo-local Natural Earth shapefile was found.
- OSM is referenced in docs as future vector detail; no repo-local OSM data was found.

Suitability:

- Natural Earth is acceptable fallback for coarse coastline/land context, but too coarse for small islands and coastline precision.
- OSM is not appropriate for B-6 global texture masks unless a later vector overlay/urban/road system is planned.
- Neither should be the primary B-6 coastline source while GSHHG is available.

### 4.5 Reef / Atoll Data

Status:

- No true global reef/atoll dataset was found in the project.

Short-term proxy options:

- Bathymetry shallow anomalies.
- Island proximity from GSHHG small islands.
- Known island group anchors.
- Source texture brightness, only as a weak review signal.

Proxy limitations:

- Maldives: linear atoll chain, too fine for circular proxy.
- Bahamas: broad shallow bank, not island-centered.
- Tuamotu: dispersed atoll field.
- Great Barrier Reef: ribbon reef structure not captured by ETOPO1.
- Red Sea reefs: narrow coastal reefs need high-res bathymetry or reef data.

Recommendation:

- B-6 prototype may include `reef_or_atoll_proxy_mask`, clearly labeled proxy.
- Production-quality reef behavior requires a real reef/atoll dataset or GEBCO-class shallow bathymetry plus manual validation.

## 5. Structure Mask Generation Pipeline Design

### 5.1 Directory Structure

```text
d5b_processor_v3/earth_structure_masks/
  README.md
  config.py
  generate_structure_masks.py
  data/
  output/
  previews/
  metrics/
```

Policy:

- `data/` stores lightweight local config or copied metadata only. Large source datasets should remain in `pwa/assets/source/`.
- `output/` stores `.npz` masks and metadata.
- `previews/` stores review-only images.
- `metrics/` stores mask validation summaries.

### 5.2 Recommended Function Structure

| Function | Input | Output | External Data? | Resolution Adaptive? | Cacheable? | Failure Policy | Fallback |
|---|---|---|---:|---:|---:|---|---|
| `load_topography_source()` | ETOPO1 path, optional GEBCO paths | elevation/depth arrays + metadata | yes | yes | source cache | abort if no ETOPO1 | no for B-6.2 |
| `load_coastline_source()` | GSHHG path/tier | polygon source + metadata | yes | yes | source cache | abort if no GSHHG | ETOPO1 land fallback only for prototype |
| `build_land_ocean_masks()` | GSHHG polygons, target grid | land/ocean masks | yes | yes | yes | abort if rasterization fails | ETOPO1 elevation >=0 |
| `build_bathymetry_masks()` | ETOPO1/GEBCO elevation | depth class masks | yes | yes | yes | abort if dimensions invalid | no |
| `build_coastline_distance_mask()` | land/ocean mask | distance km + normalized bands | no after land mask | yes | yes | abort if transform unavailable | simple pixel distance for prototype |
| `build_island_proximity_mask()` | GSHHG land components | island masks/proximity | yes | yes | yes | warn if component stats fail | manual anchors |
| `build_special_sea_masks()` | ocean mask, bbox config, depth masks | named water-only masks | no after masks | yes | yes | abort if named mask empty | bbox clipped by ocean |
| `build_land_ecology_proxy_masks()` | source texture, land, ETOPO1, config | desert/vegetation/etc. | source image optional | yes | yes | warn, not abort | region config |
| `validate_structure_masks()` | all masks | metrics/errors | no | yes | yes | abort on critical alignment errors | no |
| `save_structure_masks_npz()` | mask dict | `.npz` | no | yes | n/a | abort on write failure | no |
| `save_structure_mask_previews()` | mask dict | preview JPG/PNG | no | yes | n/a | optional; warn | no |
| `write_structure_mask_metadata()` | config, source hashes, metrics | JSON | no | yes | n/a | abort if missing provenance | no |

### 5.3 `.npz` Output Format

Planned structure:

```python
{
  "land_mask": float32[H,W],
  "ocean_mask": float32[H,W],
  "coastline_mask": float32[H,W],
  "coastline_distance_km": float32[H,W],
  "deep_ocean_mask": float32[H,W],
  "mid_ocean_mask": float32[H,W],
  "continental_shelf_mask": float32[H,W],
  "shallow_sea_mask": float32[H,W],
  "nearshore_shallow_mask": float32[H,W],
  "reef_or_atoll_proxy_mask": float32[H,W],
  "island_proximity_mask": float32[H,W],
  "small_island_mask": float32[H,W],
  "tropical_island_group_mask": float32[H,W],
  "high_latitude_island_mask": float32[H,W],
  "polar_ice_mask": float32[H,W],
  "greenland_ice_mask": float32[H,W],
  "antarctica_ice_mask": float32[H,W],
  "sea_ice_proxy_mask": float32[H,W],
  "polar_coastal_water_mask": float32[H,W],
  "desert_mask": float32[H,W],
  "arid_land_mask": float32[H,W],
  "vegetation_mask": float32[H,W],
  "rainforest_mask": float32[H,W],
  "grassland_mask": float32[H,W],
  "mountain_mask": float32[H,W],
  "plateau_mask": float32[H,W],
  "snow_mountain_mask": float32[H,W],
  "red_sea_water_mask": float32[H,W],
  "yellow_sea_water_mask": float32[H,W],
  "east_china_sea_water_mask": float32[H,W],
  "japan_sea_water_mask": float32[H,W],
  "mediterranean_water_mask": float32[H,W],
  "aegean_sea_water_mask": float32[H,W],
  "caribbean_water_mask": float32[H,W],
  "bahamas_bank_mask": float32[H,W],
  "persian_gulf_water_mask": float32[H,W],
  "north_sea_water_mask": float32[H,W],
  "baltic_sea_water_mask": float32[H,W],
  "south_china_sea_water_mask": float32[H,W],
  "coral_sea_water_mask": float32[H,W],
  "great_barrier_reef_proxy_mask": float32[H,W],
}
```

Storage rules:

- Hard masks may be stored as `uint8` if they are strictly 0/1.
- Soft masks should be `float32` in `[0,1]`.
- Distance masks should be `float32`, unit kilometers, with metadata documenting approximation.
- Use compressed `.npz` for 2K; evaluate compressed vs uncompressed for 8K loading speed.
- 2K rough size: 2048x1024x4 bytes is about 8MB per float32 mask before compression. 40 masks uncompressed would be about 320MB; compression and uint8 hard masks should reduce this substantially.
- 8K rough size: 8192x4096x4 bytes is about 128MB per float32 mask before compression. Full 40-mask float32 package is too large; B-6 must store critical 8K masks only or use uint8/float16/tiling.
- Metadata JSON is required.

Metadata must include:

- source file paths;
- source file sizes and hashes if feasible;
- generation resolution;
- mask names and dtypes;
- threshold values;
- coordinate convention;
- projection;
- date;
- generator version;
- warnings and fallback use.

### 5.4 Preview Outputs

Planned review previews:

```text
previews/structure_masks/land_ocean_preview.jpg
previews/structure_masks/bathymetry_classes_preview.jpg
previews/structure_masks/coastline_distance_preview.jpg
previews/structure_masks/shallow_sea_preview.jpg
previews/structure_masks/reef_proxy_preview.jpg
previews/structure_masks/special_seas_preview.jpg
```

Rules:

- Preview images are for human review only.
- Preview images do not enter production.
- Preview images do not affect d6.
- Preview generation belongs to B-6.2/B-6.3, not this planning turn.

## 6. d6 Noon Air Integration Route

### 6.1 Current Logic To Replace

| Current Logic | Replace With | Reason |
|---|---|---|
| `ocean_px(f32)` | B-6 `ocean_mask` | RGB blue dominance is not a stable ocean classifier |
| `deep_ocean_px(f32)` | B-6 `deep_ocean_mask` | depth should come from topography/bathymetry, not current pixels |
| shallow proxy using luminance threshold | B-6 `continental_shelf_mask`, `shallow_sea_mask`, `nearshore_shallow_mask` | brightness is not depth |
| manual tropical bbox floor | B-6 reef/island/shelf masks | broad rectangles caused B-5.1 patches |
| partial island halo center logic | B-6 `island_proximity_mask`, `small_island_mask`, `reef_or_atoll_proxy_mask` | center circles are not island/reef geometry |
| special sea bbox water detection | B-6 named water-only masks | avoids land-dominated or coast-wrong metrics |
| Red Sea crop metrics | `red_sea_water_mask` metrics | whole crop is desert-dominated |
| Yellow Sea color detection | `yellow_sea_water_mask` + `B_over_G` / `B_minus_G` | channel-ratio should be water-only |
| land/ocean distinction in land modules | B-6 `land_mask`, `ocean_mask` | current land/ocean thresholds are inconsistent |

### 6.2 Current Logic To Preserve

Preserve:

- final harmony guard diagnostic-only semantics;
- calibration safety metadata;
- output path safety;
- metrics JSON writing;
- visual review crops;
- atmosphere overlay, with possible mask-aware exclusions later;
- aesthetic color modules after replacing their masks;
- `--calibration` and `--full-res` separation.

### 6.3 New d6 Pipeline Concept

```text
load source texture
load structure masks
global base aesthetic
deep ocean adjustment using deep_ocean_mask
mid ocean adjustment using mid_ocean_mask
continental shelf adjustment using shelf_mask
shallow sea adjustment using shallow_sea_mask
reef / atoll adjustment using reef_proxy_mask
island proximity halo using island_proximity_mask
special sea water-only adjustment
land / desert / vegetation / polar using structure masks
atmosphere overlay
diagnostics
output calibration
```

Differences from current d6:

- classifiers are loaded, not recomputed from mutated `out`;
- physical structure and aesthetic color are separated;
- special seas are water-only by construction;
- reef/shelf/island changes can be measured by structure masks;
- metrics can report affected pixels per physical structure;
- d6 becomes a theme renderer, not a geography classifier.

## 7. B-6 Execution Plan

| Phase | Goal | Inputs | Outputs | Actions Allowed | Actions Forbidden | Acceptance Criteria |
|---|---|---|---|---|---|---|
| B-6.1 Asset Audit | produce detailed inventory and source decision | existing files/docs/scripts | `docs/phase_b6_1_asset_audit.md` | read files, inspect metadata, no generation | no code change, no masks, no images | clear source table and go/no-go for prototype |
| B-6.2 2K Structure Mask Prototype | generate 2K `.npz` masks only | ETOPO1, GSHHG, config | 2K mask `.npz`, metadata, previews | create new B-6 scripts/output only | no texture generation, no d6 changes | masks align globally; special sea masks non-empty |
| B-6.3 Structure Mask Validation | validate visual/numeric quality | B-6.2 outputs | metrics and review doc | inspect previews, compute mask stats | no d6 calibration | land/ocean, coast distance, shelf, special seas pass review |
| B-6.4 Structure Layer API Design | define stable read API | B-6.2/6.3 outputs | API spec doc | write docs, maybe plan interfaces | no d6 refactor yet | d6 integration contract stable |
| B-6.5 d6 Refactor Plan | plan mask-based d6 changes | API spec, current d6 | refactor plan doc | docs only | no image generation | module-by-module replacement plan approved |
| B-6.6 Noon Air 2K Rebuild | regenerate 2K calibration using masks | refactored d6 + masks | 2K calibration outputs | run calibration only after approval | no full-res, no candidates, no production | no black sea/patch artifacts; metrics improve |
| B-6.7 8K Candidate Gate | decide 8K eligibility | approved 2K result | 8K go/no-go doc | run 8K only after explicit approval | no production promotion | 2K pass + structure masks validated |

Commit policy:

- B-6.1 docs can be committed after review.
- B-6.2 scripts can be committed if they only generate structure masks and do not touch production.
- Generated 2K masks may be committed only if size and repo policy allow; otherwise store under ignored output with metadata committed.
- 8K masks likely should not be committed without explicit storage policy.

## 8. Current B-5 Workspace Recommendation

Current relevant status:

```text
M d5b_processor_v3/d6_noon_air_earth_generator.py
?? docs/phase_b5_3_noon_air_island_reef_shelf_recovery_plan.md
?? docs/phase_b5_3a_codex_noon_air_generator_deep_architecture_audit.md
```

Recommendations:

1. Commit B-5.3A audit docs: yes, after review. It documents why B-6 is needed.
2. Commit B-5.3 plan doc: optional, but if committed, label as superseded/deferred by B-6.
3. Do not commit d6 generator as visual progress. If committed at all, commit only as "calibration safety checkpoint" and explicitly note it is not visually accepted.
4. Preserve B-5.1/B-5.2 modifications as reference until B-6 plan is accepted; do not delete them.
5. Consider a backup branch before any revert or refactor.
6. Do not clean previews in this phase.
7. Pause B-5.3 implementation.

Suggested commands, not executed:

```bash
git add docs/phase_b5_3a_codex_noon_air_generator_deep_architecture_audit.md docs/phase_b6_global_earth_structure_mask_layer_plan.md
git commit -m "docs: plan global earth structure mask layer"
```

Optional if preserving the B-5.3 plan as historical context:

```bash
git add docs/phase_b5_3_noon_air_island_reef_shelf_recovery_plan.md
git commit -m "docs: record deferred noon air reef recovery plan"
```

Do not execute without explicit authorization:

```bash
git add d5b_processor_v3/d6_noon_air_earth_generator.py
```

## 9. Risk Register

| Risk | Impact | Likelihood | Mitigation |
|---|---|---:|---|
| Data files too large | slow processing, repo bloat | high | cache only derived masks; avoid committing large 8K masks by default |
| Coordinate/projection alignment errors | masks shift vs texture | medium | validate with known coast points and previews |
| ETOPO1 resolution insufficient | reefs/small islands remain weak | high | label reef masks proxy; use GSHHG and later GEBCO/reef data |
| Global GEBCO processing cost high | delays Phase C/B-7 | high | start with ETOPO1; subset GEBCO for benchmarks |
| GSHHG coastline complexity | slow rasterization, polygon bugs | medium | tier fallback, cache outputs, validate by region |
| Reef data missing | atoll/GBR/Bahamas remain approximate | high | proxy only in B-6; plan real dataset search |
| Mask/source texture misalignment | artifacts at coasts | medium | metadata coordinate convention, pixel tests, coast preview |
| 2K mask passes but 8K fails | false confidence | medium | require 8K mask validation before 8K candidate |
| Structure layer over-engineered | slow progress | medium | B-6.2 minimal 2K prototype first |
| Short-term no visual output | stakeholder impatience | medium | explain B-6 as prerequisite to stable visuals |
| d6 refactor cost high | delayed Noon Air rebuild | high | API spec first; replace masks incrementally |
| Existing ocean mask conflicts with GSHHG | inconsistent water semantics | medium | treat existing mask as comparison, not authority |
| Soft distance in equirectangular grid inaccurate | latitude artifacts | medium | latitude-aware km conversion or geodesic approximation |
| Inland lakes semantics ambiguous | special masks include/exclude lakes incorrectly | low-medium | define policy in config metadata |

## Final Recommendation

1. Should we pause B-5.3 implementation?
   Answer: Yes. B-5.3 should remain paused until B-6.1/B-6.2 establishes structure masks and metrics.

2. Should we build Global Structure Mask Layer?
   Answer: Yes. It is the correct root-cause response to repeated RGB/luminance/bbox/circle failures.

3. Should B-6 start with asset audit or prototype?
   Answer: Start with B-6.1 asset audit, then B-6.2 2K prototype. This document includes an initial audit, but B-6.1 should formalize source hashes, dependencies, and exact implementation constraints.

4. Can current d6 generator continue as-is?
   Answer: Only as a historical calibration prototype. It should not be the basis for further local B-5.3 patching or production decisions.

5. Should current d6 modifications be committed?
   Answer: Not as visual progress. Commit only if the team wants a labeled calibration-safety checkpoint; otherwise leave uncommitted until B-6 direction is settled.

6. Should B-5.3 / B-5.3A docs be committed?
   Answer: B-5.3A should be committed as the deep audit rationale. B-5.3 may be committed as deferred historical context, but it should not authorize implementation.

7. What is the next smallest safe action?
   Answer: Commit this B-6 plan and the B-5.3A audit doc only, after review. Do not commit generator changes.

8. What is the first implementation phase after this document?
   Answer: B-6.1 Asset Audit, focused on exact source inventory, dependency audit, metadata/hash capture, and prototype go/no-go.

9. What must remain forbidden?
   Answer: No generator run, no calibration, no full-res, no new texture, no mask/image generation in this planning turn, no candidates/production writes, no frontend changes, no commit/push without explicit authorization, no preview cleanup, and no file deletion.

## Non-Execution Confirmation

- Code modified: no.
- JSON modified: no.
- Images modified/generated: no.
- Generator run: no.
- Calibration/full-res run: no.
- Commit/push: no.
- Production/candidates/frontend touched: no.
