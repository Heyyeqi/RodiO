# Phase B-6.2G-4D-2P-R Desert / Arid 8K + 21.6K Resource Acquisition Setup

Stage: B-6.2G-4D-2P-R  
Type: Resource Acquisition Setup  
Date: 2026-06-10  
Scope: gitignore, source-cache layout, manifest template, and export instructions only

This stage does not download full-resolution 10m raw global tiles, generate formal structure masks, run the structure mask generator, run d6, write to `pwa/`, `production/`, or `candidates/`, generate Noon Air imagery, commit, or push.

## 1. Why This Replaces the 2K-only Plan

B-6.2G-4D-2 originally framed the import test around low-res / 2K source exports. That is insufficient for RodiO's current and long-term Earth texture goals:

- current runtime day texture is 8192x4096;
- structure layer testing should therefore support an 8K active test path;
- long-term source-derived work needs a 21600x10800 master-aligned intermediate;
- if 21.6K is not planned now, the project risks optimizing around temporary 2K data and forgetting the master route.

This stage prepares two export tiers:

- **8K**: active import test and prototype input;
- **21.6K**: master-aligned source cache for later validation and future high-resolution structure layers.

2K is excluded from this setup because it is no longer the correct planning target for desert / arid source acquisition. 2K may still be used for quick diagnostics later, but it is not the resource acquisition target.

## 2. Why Full 10m Raw Global Data Is Still Excluded

ESA WorldCover 10m is appropriate as source truth, but downloading full global raw 10m tiles is not appropriate for this stage:

- global 10m data is too large for casual local handling;
- current local tooling lacks GDAL/rasterio;
- raw tiles increase accidental git/runtime coupling risk;
- the immediate need is master-aligned equirectangular exports, not raw source tiling.

The correct near-term path is Earth Engine or equivalent controlled export to:

- 8192x4096 for active testing;
- 21600x10800 for master source cache.

Raw full-resolution global tiles remain forbidden unless separately authorized.

## 3. Gitignore / Source Cache Policy

`.gitignore` now includes:

```gitignore
# External source cache for manually downloaded/exported datasets
d5b_processor_v3/source_cache/
```

This means the following must not appear in git status and must not be committed:

```text
d5b_processor_v3/source_cache/desert_arid/raw/
d5b_processor_v3/source_cache/desert_arid/exported_8k/
d5b_processor_v3/source_cache/desert_arid/exported_21600/
d5b_processor_v3/source_cache/desert_arid/diagnostics/
```

Because the whole `source_cache` tree is ignored, cache-local `README.md` and `manifest.template.json` are also ignored. This document therefore records the canonical template and instructions in a tracked location.

## 4. Source Cache Layout

Created / expected local layout:

```text
d5b_processor_v3/source_cache/desert_arid/
  README.md
  manifest.template.json
  raw/
  exported_8k/
  exported_21600/
  diagnostics/
```

Directory purpose:

- `raw/`: manually downloaded raw external files, if later authorized;
- `exported_8k/`: active 8192x4096 source exports for import tests and prototypes;
- `exported_21600/`: 21600x10800 master-aligned source exports, saved and checksummed only for now;
- `diagnostics/`: diagnostic previews/stats from import tests, never production outputs.

## 5. Required Export Files

### 8K Active Test Files

```text
d5b_processor_v3/source_cache/desert_arid/exported_8k/esa_worldcover_2021_v200_map_8192x4096.tif
d5b_processor_v3/source_cache/desert_arid/exported_8k/global_aridity_index_8192x4096.tif
```

Acceptable Global Aridity alternative:

```text
d5b_processor_v3/source_cache/desert_arid/exported_8k/global_aridity_index_8192x4096.nc
```

### 21.6K Master Source Files

```text
d5b_processor_v3/source_cache/desert_arid/exported_21600/esa_worldcover_2021_v200_map_21600x10800.tif
d5b_processor_v3/source_cache/desert_arid/exported_21600/global_aridity_index_21600x10800.tif
```

Acceptable Global Aridity alternative:

```text
d5b_processor_v3/source_cache/desert_arid/exported_21600/global_aridity_index_21600x10800.nc
```

## 6. ESA WorldCover Export Instructions

Dataset:

```text
ESA/WorldCover/v200
```

Band:

```text
Map
```

Export 1:

```text
target_grid: equirectangular_8192x4096
crs: EPSG:4326
global_extent: [-180, -90, 180, 90]
filename: esa_worldcover_2021_v200_map_8192x4096.tif
destination: d5b_processor_v3/source_cache/desert_arid/exported_8k/
```

Export 2:

```text
target_grid: equirectangular_21600x10800
crs: EPSG:4326
global_extent: [-180, -90, 180, 90]
filename: esa_worldcover_2021_v200_map_21600x10800.tif
destination: d5b_processor_v3/source_cache/desert_arid/exported_21600/
```

Class mapping:

```text
10 Tree cover
20 Shrubland
30 Grassland
40 Cropland
50 Built-up
60 Bare / sparse vegetation
70 Snow and ice
80 Permanent water bodies
90 Herbaceous wetland
95 Mangroves
100 Moss and lichen
```

ESA metadata:

```text
license: CC-BY-4.0
commercial_clearance: true
research_only: false
attribution: ESA WorldCover 10 m 2021 v200
```

## 7. Global Aridity Export / Download Instructions

Global Aridity must be prepared in the same two target grids:

```text
8192x4096
21600x10800
```

Important semantic note:

Global Aridity source resolution is much coarser than 21.6K. A 21600x10800 aridity export is a **master-aligned raster**, not true higher-resolution aridity information.

Required metadata:

```text
research_only: true
commercial_clearance: false
commercial_clearance_status: pending
replacement_required_before_commercial: true
usage_scope: research_noncommercial_prototype
redistribution_allowed: false_without_permission
```

8K file target:

```text
d5b_processor_v3/source_cache/desert_arid/exported_8k/global_aridity_index_8192x4096.tif
```

or:

```text
d5b_processor_v3/source_cache/desert_arid/exported_8k/global_aridity_index_8192x4096.nc
```

21.6K file target:

```text
d5b_processor_v3/source_cache/desert_arid/exported_21600/global_aridity_index_21600x10800.tif
```

or:

```text
d5b_processor_v3/source_cache/desert_arid/exported_21600/global_aridity_index_21600x10800.nc
```

## 8. Manifest Template

Canonical manifest template:

```json
{
  "dataset": "",
  "dataset_version": "",
  "source_url": "",
  "earth_engine_dataset_id": "",
  "license": "",
  "attribution": "",
  "commercial_clearance": "",
  "research_only": false,
  "replacement_required_before_commercial": false,
  "export_method": "",
  "export_date": "",
  "resolutions": {
    "8k": {
      "target_grid": "equirectangular_8192x4096",
      "file_path": "",
      "checksum": "",
      "status": ""
    },
    "21600": {
      "target_grid": "equirectangular_21600x10800",
      "file_path": "",
      "checksum": "",
      "status": ""
    }
  },
  "file_format": "",
  "nodata": "",
  "class_mapping": {},
  "notes": ""
}
```

Checksum policy:

- record SHA-256 for every exported file once present;
- do not process 21.6K files until checksum and manifest entries exist;
- record `status: missing | present | verified | failed`.

## 9. Processing Policy

8K:

- may enter B-6.2G-4D-2-R8K import test;
- can be used for diagnostic import, orientation, class histogram, and candidate array checks;
- still must not generate formal structure mask `.npz` in this setup stage.

21.6K:

- existence / checksum / manifest registration only;
- no formal mask generation;
- no d6;
- no pwa;
- no production;
- no candidates;
- later phase: B-6.2G-4M master validation.

## 10. Next Stage Recommendation

Proceed to **B-6.2G-4D-2-R8K** only after at least the ESA 8K export is manually provided under:

```text
d5b_processor_v3/source_cache/desert_arid/exported_8k/esa_worldcover_2021_v200_map_8192x4096.tif
```

Global Aridity can remain blocked until the research-only 8K file is provided.

B-6.2G-4B must not start until 8K import validation passes.

## 11. Completion Notes

- `.gitignore` updated to ignore `d5b_processor_v3/source_cache/`.
- Source cache directory skeleton created.
- Cache-local README and manifest template created, but ignored by git.
- This tracked document records the canonical template and export instructions.
- No external data was downloaded.
- No 8K sample was obtained.
- No 21.6K sample was obtained.
- No formal masks were generated.
- No generator or d6 run occurred.

