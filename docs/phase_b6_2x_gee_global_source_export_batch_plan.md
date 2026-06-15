# Phase B-6.2X — GEE Global Source Export Batch Plan

Stage: B-6.2X  
Type: Google Earth Engine global source export batch planning  
Date: 2026-06-10  
Status: Planning only; no export, no mask generation, no d6 integration

This phase reframes B-6 from incremental mask patching to a unified global source-cache route:

```text
GEE global source cache
→ local import / alignment
→ semantic mask derivation
→ validation
→ API / priority design
→ d6 / visual color application
```

This document does not download data, execute GEE exports, generate masks, run the structure mask generator, run d6, write to `pwa/`, `production/`, or `candidates/`, generate Noon Air images, commit, or push.

## 1. Strategic Reframe

The previous B-6.2G route improved rigor but remained fragmented:

- lake, river, terrain, desert, and reef were audited one by one;
- each feature class required separate asset discovery;
- source quality varied across masks;
- validation often had to prove both source availability and semantic correctness at the same time.

The new route is to first build a coherent Google Earth Engine source cache:

- export global base rasters in consistent equirectangular grids;
- keep external source rasters out of git;
- derive semantic masks locally from a common source inventory;
- validate masks after source import, not during ad hoc source hunting;
- only after validation, design API priority and d6 integration.

GEE solves source acquisition and preprocessing convenience. It does not replace:

- semantic design;
- mask priority / parent-child rules;
- proxy vs data-derived labeling;
- local import validation;
- geographic validation;
- API design;
- d6 refactor;
- visual color calibration.

## 2. Export Resolution Policy

RodiO current runtime day texture target is `8192x4096`. Long-term structure and texture work needs a `21600x10800` master / intermediate route.

Export policy:

| Tier | Role | Use Now? | Notes |
| ---- | ---- | -------- | ----- |
| 8K `8192x4096` | active import test, prototype, runtime-aligned source | yes | main near-term validation tier |
| 21.6K `21600x10800` | master source cache / later activation | yes, as registration target | do not process heavily until explicitly gated |
| 2K `2048x1024` | low-res diagnostics only | no as primary | insufficient for current RodiO precision target |
| full raw 10m global tiles | original source truth | no for this phase | too large; do not download into repo |

Source resolution categories:

| Category | Meaning | Examples | Policy |
| -------- | ------- | -------- | ------ |
| true high-res source | native source is detailed enough to support 21.6K output | ESA WorldCover, Dynamic World, Copernicus DEM GLO-30 | export 8K first; 21.6K where cost is acceptable |
| master-aligned source | native source is coarser; 21.6K export adds alignment, not real detail | ETOPO1, MODIS, Köppen, Global Aridity | 8K first; 21.6K only for grid consistency |
| vector-derived source | source is vector and must be rasterized | GLIMS, GSHHG, reef vectors | define rasterization scale and topology rules |

## 3. Candidate GEE Source List

### A. ESA WorldCover 2021 v200

Official GEE dataset: `ESA/WorldCover/v200`  
Band: `Map`  
Resolution: 10 m  
License: CC-BY-4.0  
Role: primary global land-cover source.

ESA WorldCover 2021 provides a global 10 m land-cover map with 11 classes and CC-BY-4.0 terms. Official class values:

| Value | Class |
| ----: | ----- |
| 10 | Tree cover |
| 20 | Shrubland |
| 30 | Grassland |
| 40 | Cropland |
| 50 | Built-up |
| 60 | Bare / sparse vegetation |
| 70 | Snow and ice |
| 80 | Permanent water bodies |
| 90 | Herbaceous wetland |
| 95 | Mangroves |
| 100 | Moss and lichen |

Downstream masks:

- `forest_mask`
- `shrubland_mask`
- `grassland_mask`
- `cropland_mask`
- `builtup_mask`
- `bare_sparse_land_mask`
- `snow_ice_mask`
- `permanent_water_mask`
- `wetland_mask`
- `mangrove_mask`
- `moss_lichen_mask`

Required files:

```text
esa_worldcover_2021_v200_map_8192x4096.tif
esa_worldcover_2021_v200_map_21600x10800.tif
```

Source note: ESA WorldCover should be treated as land-cover truth, not as final RodiO color. It must be domain-clipped by land/ocean masks during semantic derivation.

### B. Dynamic World V1

Official GEE dataset: `GOOGLE/DYNAMICWORLD/V1`  
Bands: `water`, `trees`, `grass`, `flooded_vegetation`, `crops`, `shrub_and_scrub`, `built`, `bare`, `snow_and_ice`, `label`  
Resolution: 10 m  
License: CC-BY 4.0 with attribution.

Dynamic World provides class probabilities and labels. It is useful as confidence / cross-check rather than a first-pass truth replacement.

Recommended export design:

- defer full probability stack until Phase 2;
- export 2021 annual composite to match ESA WorldCover 2021;
- start with selected probability bands:
  - `bare`
  - `water`
  - `trees`
  - `grass`
  - `flooded_vegetation`
  - `snow_and_ice`
- optionally export `label` after probability composite behavior is validated.

Candidate files:

```text
dynamic_world_2021_label_8192x4096.tif
dynamic_world_2021_bare_probability_8192x4096.tif
dynamic_world_2021_water_probability_8192x4096.tif
dynamic_world_2021_trees_probability_8192x4096.tif
dynamic_world_2021_flooded_vegetation_probability_8192x4096.tif
```

Caveat: Dynamic World probabilities are model outputs and must be thresholded. They are excellent for confidence, but should not silently override ESA classes without validation.

### C. Copernicus DEM GLO-30

Official GEE dataset: `COPERNICUS/DEM/GLO30`  
Primary band: `DEM`  
Resolution: 30 m  
License: free worldwide license with noted country exceptions in the official catalog.

Copernicus DEM GLO-30 is a Digital Surface Model, not a bare-earth DEM. It represents surface elevation including buildings, infrastructure, and vegetation. It is still much better than ETOPO1 for macro land terrain structure.

Downstream masks:

- `high_mountain_mask`
- `mountain_mask`
- `plateau_refined_mask`
- `slope_relief_mask`
- `lowland_plain_mask`
- `basin_context_proxy`
- `hill_or_relief_proxy`

Recommended exports:

```text
copernicus_dem_glo30_elevation_8192x4096.tif
copernicus_dem_glo30_slope_8192x4096.tif
copernicus_dem_glo30_relief_8192x4096.tif

copernicus_dem_glo30_elevation_21600x10800.tif
copernicus_dem_glo30_slope_21600x10800.tif
```

21.6K caveat: GLO-30 has native 30 m detail, so 21.6K is meaningful for global texture-scale terrain, but export cost and Drive file size should be tested after 8K import passes.

### D. ETOPO1

Official GEE dataset: `NOAA/NGDC/ETOPO1`  
Bands: `bedrock`, `ice_surface`  
Resolution: 1 arc-minute / approximately 1855 m  
License: public-domain NOAA product; cite NCEI.

ETOPO1 remains the right global low-cost bathymetry / polar context source:

- `bedrock` for ocean bathymetry and bedrock under ice sheets;
- `ice_surface` for ice-sheet surface context.

Downstream masks:

- `deep_ocean_mask`
- `mid_ocean_mask`
- `continental_shelf_mask`
- `shallow_sea_mask`
- `polar_ice_context_mask`
- `antarctica_bedrock_context`
- `greenland_bedrock_context`

Recommended files:

```text
etopo1_bedrock_8192x4096.tif
etopo1_ice_surface_8192x4096.tif
etopo1_bedrock_21600x10800.tif
etopo1_ice_surface_21600x10800.tif
```

21.6K caveat: this is master-aligned, not higher true detail. ETOPO1 cannot solve reef, atoll, or fine shelf morphology.

### E. JRC Global Surface Water

Official GEE dataset: `JRC/GSW1_4/GlobalSurfaceWater`  
Resolution: 30 m  
Key bands: `occurrence`, `seasonality`, `recurrence`, `transition`, `max_extent`.

JRC GSW maps global surface water distribution from 1984 to 2021. It is useful for inland water, seasonal water, reservoirs, river-water support, and wetland-water context.

Phase 1 bands:

```text
jrc_gsw_occurrence_8192x4096.tif
jrc_gsw_seasonality_8192x4096.tif
jrc_gsw_recurrence_8192x4096.tif
jrc_gsw_max_extent_8192x4096.tif
```

Downstream masks:

- `permanent_water_mask`
- `seasonal_water_mask`
- `lake_water_crosscheck`
- `river_water_crosscheck`
- `reservoir_or_managed_water_proxy`
- `wetland_water_support`

Caveat: JRC GSW gives water history, not lake hierarchy. GSHHG L2/L3 still matters for lake topology and lake islands.

### F. GLIMS Glacier Inventory

Official GEE dataset: `GLIMS/current`  
Type: FeatureCollection  
Role: global glacier vector inventory.

GLIMS is a vector source and should not be exported as a raw table for d6 use. It needs a rasterization policy:

- filter to glacier boundary records where appropriate;
- rasterize to 8K global grid in GEE or locally;
- preserve attribution and snapshot date;
- avoid conflating glacier polygons with seasonal snow.

Recommended files:

```text
glims_glacier_mask_8192x4096.tif
glims_glacier_mask_21600x10800.tif
```

Downstream masks:

- `glacier_mask`
- `mountain_glacier_mask`
- `icefield_mask`
- `cryosphere_validation_mask`

Caveat: GLIMS does not replace Antarctica / Greenland ice-sheet handling. It complements polar land ice with mountain and regional glaciers.

### G. Optional / Deferred Sources

| Source | Status | Role | Recommendation |
| ------ | ------ | ---- | -------------- |
| Copernicus CGLS-LC100 bare-coverfraction | optional | bare fraction / soft mask | Phase 3 or cross-check |
| MODIS MCD12Q1 | optional | coarse land-cover cross-check | Phase 3 |
| Köppen-Geiger | may require external source | climate context | defer; not land-cover truth |
| Global Aridity Index / PET | external / licensing caveat | aridity truth | continue as desert/arid supplement; research-only until commercial gate |
| GEBCO | external or separate source | high-quality bathymetry | required for reef/shelf improvement; not replaced by ETOPO1 |
| reef / coral datasets | external | coral reef / atoll truth | required for Maldives, Tuamotu, Bahamas, GBR |
| GSHHG | local vector source | coastline, islands, lake hierarchy | keep local; not replaced by GEE rasters |

## 4. Proposed File List

Recommended source cache layout:

```text
d5b_processor_v3/source_cache/gee_global/
  exported_8k/
  exported_21600/
  manifests/
  diagnostics/
```

Phase 1 required files:

```text
exported_8k/esa_worldcover_2021_v200_map_8192x4096.tif
exported_21600/esa_worldcover_2021_v200_map_21600x10800.tif

exported_8k/copernicus_dem_glo30_elevation_8192x4096.tif
exported_8k/copernicus_dem_glo30_slope_8192x4096.tif

exported_8k/etopo1_bedrock_8192x4096.tif
exported_8k/etopo1_ice_surface_8192x4096.tif

exported_8k/jrc_gsw_occurrence_8192x4096.tif
exported_8k/jrc_gsw_seasonality_8192x4096.tif
exported_8k/jrc_gsw_recurrence_8192x4096.tif
exported_8k/jrc_gsw_max_extent_8192x4096.tif
```

Phase 2 optional / supplement files:

```text
exported_8k/dynamic_world_2021_label_8192x4096.tif
exported_8k/dynamic_world_2021_bare_probability_8192x4096.tif
exported_8k/dynamic_world_2021_water_probability_8192x4096.tif
exported_8k/dynamic_world_2021_trees_probability_8192x4096.tif
exported_8k/dynamic_world_2021_flooded_vegetation_probability_8192x4096.tif

exported_8k/glims_glacier_mask_8192x4096.tif
exported_21600/glims_glacier_mask_21600x10800.tif

exported_21600/copernicus_dem_glo30_elevation_21600x10800.tif
exported_21600/copernicus_dem_glo30_slope_21600x10800.tif
exported_21600/etopo1_bedrock_21600x10800.tif
exported_21600/etopo1_ice_surface_21600x10800.tif
```

Phase 3 deferred / external:

```text
gebco_global_bathymetry_8192x4096.tif
gebco_global_bathymetry_21600x10800.tif
global_aridity_index_8192x4096.tif
koppen_geiger_classes_8192x4096.tif
reef_coral_global_mask_8192x4096.tif
```

## 5. Source-to-Mask Mapping

| Source | Bands / Layers | Derived Masks | Confidence | Caveats |
| ------ | -------------- | ------------- | ---------- | ------- |
| ESA WorldCover | `Map` classes 10-100 | `forest_mask`, `shrubland_mask`, `grassland_mask`, `cropland_mask`, `builtup_mask`, `bare_sparse_land_mask`, `wetland_mask`, `mangrove_mask`, `snow_ice_mask`, `permanent_water_mask` | high for broad land cover | class `60` is bare/sparse land, not desert truth |
| Dynamic World | label + probability bands | confidence overlays for `trees`, `grass`, `bare`, `water`, `flooded_vegetation`, `snow_ice` | medium/high as cross-check | probabilities require thresholding and annual composite design |
| Copernicus DEM GLO-30 | `DEM`, derived slope/relief | `high_mountain_mask`, `plateau_mask`, `slope_relief_mask`, `lowland_plain_mask`, `basin_context_proxy` | high for macro terrain | DSM, not bare-earth DEM; not true geomorphology |
| ETOPO1 | `bedrock`, `ice_surface` | `continental_shelf_mask`, `shallow_sea_mask`, `deep_ocean_mask`, `polar_ice_context_mask` | medium for global ocean bands | too coarse for reef, banks, atolls |
| JRC GSW | `occurrence`, `seasonality`, `recurrence`, `max_extent` | `permanent_water_mask`, `seasonal_water_mask`, `lake_water_crosscheck`, `river_water_crosscheck` | high for observed surface water | not topology; historical water may not match current visual target |
| GLIMS | glacier polygons | `glacier_mask`, `icefield_mask`, `mountain_glacier_mask` | medium/high after filtering | vector rasterization required; not seasonal snow |
| GSHHG local | L1-L6 vectors | coastline, islands, lake hierarchy, lake islands | high for topology | keep local, not GEE raster replacement |
| GEBCO external | bathymetry | refined shelf, shallow bank, reef-adjacent bathymetry | high if acquired | external acquisition needed |
| Reef / coral external | reef polygons / rasters | `reef_or_atoll_mask`, `coral_sea_proxy`, atoll structure | high if acquired | likely needed for Maldives/Tuamotu/Bahamas/GBR |

## 6. What GEE Cannot Fully Solve

GEE source exports are a major acceleration, but several RodiO-critical structures still need specialized data or topology:

- coral reef;
- atoll morphology;
- Bahamas Bank;
- Maldives / Tuamotu / Pacific atolls;
- fine small-island coastline;
- true shallow reef morphology;
- high-quality bathymetry beyond ETOPO1;
- lake island hierarchy;
- coastline topology.

Required non-GEE or local sources remain:

- GSHHG for coastline / islands / lake hierarchy;
- GEBCO for higher-quality bathymetry;
- reef / coral datasets for true reef and atoll masks;
- manual geographic validation for island, coast, and shallow-water artifacts.

## 7. Export Priority

### Phase 1 — Core Global Sources

Export first:

- ESA WorldCover 8K / 21.6K;
- Copernicus DEM GLO-30 elevation / slope 8K;
- ETOPO1 bedrock / ice_surface 8K;
- JRC Global Surface Water occurrence / seasonality / recurrence / max_extent 8K.

Rationale:

- gives land cover, terrain, ocean bathymetry, polar context, and surface water;
- enough to derive first coherent land/ocean/water/terrain/vegetation/bare/snow masks;
- provides immediate 8K runtime-aligned data.

### Phase 2 — Confidence / Supplement

Export after Phase 1 import validation:

- Dynamic World 2021 selected composite bands;
- GLIMS glacier raster;
- Copernicus DEM 21.6K;
- ETOPO1 21.6K;
- JRC 21.6K only if import/storage is justified.

### Phase 3 — Specialized / External

Acquire or plan separately:

- GEBCO;
- reef / coral;
- Global Aridity / Köppen;
- MODIS / CGLS-LC100.

These should not block Phase 1, but they are still required before declaring the global semantic layer visually complete.

## 8. Import Gate

### B-6.2X-D1 — Source Cache Setup / Gitignore Audit

Allowed:

- create `d5b_processor_v3/source_cache/gee_global/`;
- create gitignored subdirectories;
- write README / manifest template;
- verify `.gitignore`.

Forbidden:

- download / export data;
- generate masks;
- run d6;
- write pwa / production / candidates.

Exit criteria:

- cache path exists;
- generated rasters are ignored;
- manifest schema records dataset, version, license, attribution, resolution, checksum, export method, and commercial clearance.

### B-6.2X-D2 — GEE Export Script Draft

Allowed:

- create export instruction document;
- optionally create a non-runtime export script draft;
- define exact Drive folder and filenames.

Forbidden:

- execute exports unless separately authorized;
- modify structure mask generator;
- run d6.

Exit criteria:

- Phase 1 export tasks are copy-paste ready;
- resolution, CRS, region, file format, and maxPixels are explicit.

### B-6.2X-D3 — 8K Import Test

Allowed:

- read manually exported 8K rasters from gitignored cache;
- compute diagnostic stats / previews;
- validate shape, dtype, values, nodata, orientation, and class histograms.

Forbidden:

- generate formal structure mask `.npz`;
- run structure mask generator;
- run d6;
- write pwa / production / candidates.

Exit criteria:

- every Phase 1 8K source has import verdict;
- invalid or missing sources are tracked.

### B-6.2X-D4 — 21.6K Existence / Master Registration

Allowed:

- check file existence and size;
- compute checksum if cheap;
- record manifest.

Forbidden:

- full 21.6K processing unless explicitly gated;
- mask generation;
- d6 integration.

Exit criteria:

- master files registered or explicitly deferred.

### B-6.2X-M1 — Semantic Mask Derivation Prototype

Allowed:

- derive prototype masks from validated source cache;
- write generated outputs only to `d5b_output`;
- emit metadata / metrics / diagnostic previews.

Forbidden:

- d6 integration;
- visual rebuild;
- production writes.

Exit criteria:

- source-to-mask derivation is traceable;
- proxy vs data-derived masks are labeled.

### B-6.2X-M2 — Validation Audit

Allowed:

- read generated masks;
- perform numeric and geographic validation;
- write validation docs.

Forbidden:

- patch visual color or d6;
- commit generated rasters / masks.

Exit criteria:

- masks pass or are marked conditional / failed with exact blockers.

### B-6.2X-API — Structure Semantic API Draft

Allowed:

- design API contract;
- define optional masks, missing masks, groups, priority, parent-child rules, proxy flags, versioning.

Forbidden:

- freeze API before mask validation;
- modify d6 runtime;
- start visual rebuild.

Exit criteria:

- API draft supports future masks without forcing B-5.3-style local patches.

## 9. Boundary Rules

This B-6.2X planning stage confirms:

- no d6 run;
- no visual rebuild;
- no color application;
- no production texture replacement;
- no `pwa/`, `production/`, or `candidates/` write;
- no Noon Air images;
- no exported rasters committed;
- no source cache committed;
- no commit;
- no push;
- no edits to `d5b_processor_v3/d6_noon_air_earth_generator.py`;
- root `previews/` remains untouched.

## 10. Final Recommendation

Pause single-point B-6.2G-4D-2-R8K expansion after the current ESA import result is documented. Move to B-6.2X-D1 so the project has one coherent `gee_global` source cache rather than separate per-feature caches.

Recommended immediate next stage:

```text
B-6.2X-D1 — Source Cache Setup / Gitignore Audit
```

Then:

```text
B-6.2X-D2 — GEE Export Script Draft
B-6.2X-D3 — 8K Import Test
```

Do not enter B-6.4 API freeze, d6 refactor, visual rebuild, B-5.3 patching, or production changes until the unified source-derived masks pass validation.

## References

- ESA WorldCover v200 GEE Data Catalog: https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v200
- Dynamic World V1 GEE Data Catalog: https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1
- Copernicus DEM GLO-30 GEE Data Catalog: https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_DEM_GLO30
- ETOPO1 GEE Data Catalog: https://developers.google.com/earth-engine/datasets/catalog/NOAA_NGDC_ETOPO1
- JRC Global Surface Water v1.4 GEE Data Catalog: https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_GlobalSurfaceWater
- GLIMS Current GEE Data Catalog: https://developers.google.com/earth-engine/datasets/catalog/GLIMS_current

---

## 11. B-6.2X-D2 Completion Notes (2026-06-15)

D2 has been executed. The following files were created in the repo:

```
scripts/gee_export/export_phase1_8k.js      Phase 1 8K export script draft (10 tasks)
scripts/gee_export/export_phase1_21600.js   Phase 1 21.6K export script draft (5 tasks, reference)
scripts/gee_export/README.md                Manual execution instructions
scripts/gee_export/manifest.example.json   Example manifest (not a real instance)
docs/phase_b6_2x_source_cache_layout_and_manifest_spec.md   Full spec
```

### D2 Boundary Confirmed

D2 produced script drafts only. The following did not occur:

- No GEE exports were submitted or started.
- No `.tif` or raster files were downloaded.
- No NPZ or mask files were generated.
- No real manifest instances were created in `source_cache/gee_global/manifests/`.
- No changes to `d5b_output`, `production/`, `candidates/`, or `pwa/`.

### Source Cache Layout

Canonical layout (all gitignored):

```
d5b_processor_v3/source_cache/gee_global/
  exported_8k/        Phase 1 8K .tif files (10 files when populated)
  exported_21600/     Phase 1 21.6K .tif files (5 files when populated)
  manifests/          Per-file manifest JSON (filled at D3, not D2)
  diagnostics/        Import validation outputs (written at D3)
```

Full naming convention and manifest schema:
see `docs/phase_b6_2x_source_cache_layout_and_manifest_spec.md`

### License / commercial_clearance Policy

All manifest `commercial_clearance` fields are `pending_review` until RW
formally verifies each source. The values `approved`, `cleared`, and
`commercial_ok` are reserved for post-RW-review use only.

### Next Step: B-6.2X-D3 — 8K Import Test

Entry criteria:
- At least one Phase 1 8K file manually exported from GEE and downloaded.
- File placed in `exported_8k/` and manifest template filled.
- D3 import validation scripts run to verify shape, dtype, values, nodata.

