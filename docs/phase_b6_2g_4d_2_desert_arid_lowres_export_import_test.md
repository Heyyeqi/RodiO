# Phase B-6.2G-4D-2 Desert / Arid Low-res Export / Import Test

Stage: B-6.2G-4D-2  
Type: Low-res Export / Import Test  
Date: 2026-06-10  
Scope: feasibility test planning and current sample availability audit

This stage is not formal mask implementation. It does not generate structure mask `.npz` files, does not modify `scripts/generate_b6_structure_masks.py`, does not run d6, does not write to `pwa/`, `production/`, or `candidates/`, and does not generate Noon Air imagery.

## 1. Input Strategy

### Current Sample Availability

Read-only scan found no existing low-res / 2K desert-arid source samples in:

- `d5b_processor_v3/source_cache/desert_arid/`
- `d5b_processor_v3/`
- `pwa/assets/source/`

No files matching WorldCover, aridity, PET, Koppen, MODIS, MCD12Q1, or bare-land sample names were found.

Current result:

```text
blocked: no sample available
```

Because no sample exists and this stage forbids downloading full-resolution data, no import test was executed.

### ESA WorldCover 2021 v200

Target strategy:

- Use Google Earth Engine to export a global 2048x1024 or near-2K class raster.
- Dataset ID: `ESA/WorldCover/v200`
- Band: `Map`
- Required class of interest: class `60` bare / sparse vegetation.
- Export only a class raster or a precomputed diagnostic class-60 binary raster.
- Do not download global 10m raw tiles.
- Place exported file under a gitignored source cache path after user-provided export.

Recommended initial export:

```text
d5b_processor_v3/source_cache/desert_arid/exported_2k/esa_worldcover_2021_v200_map_2048x1024.tif
```

Alternative lower-friction export:

```text
d5b_processor_v3/source_cache/desert_arid/exported_2k/esa_worldcover_2021_v200_class60_2048x1024_uint8.tif
```

The second option is smaller and easier to test, but loses the full class histogram.

### Global Aridity Index / PET

Target strategy:

- Use a low-res / 2K aridity raster, not a full raw archive.
- Mark as research-only:
  - `commercial_clearance: false`
  - `commercial_clearance_status: pending`
  - `usage_scope: research_noncommercial_prototype`
  - `replacement_required_before_commercial: true`
- If the source is not available as an already downsampled raster, D-2 remains blocked until a manually provided sample exists.

Current result:

```text
blocked: no Global Aridity sample available
```

No commercial clearance was attempted or granted in this phase.

## 2. Recommended Source Cache Layout

Recommended path:

```text
d5b_processor_v3/source_cache/desert_arid/
  README.md
  manifest.json
  raw/
  exported_2k/
  diagnostics/
```

Current `.gitignore` scan found:

```text
d5b_processor_v3/d5b_output/
```

It did not find an ignore rule for `d5b_processor_v3/source_cache/` or `d5b_processor_v3/source_cache/desert_arid/`.

Decision in this phase:

- Do not create `source_cache/desert_arid/` yet, because it is not currently confirmed gitignored.
- Before any sample is placed there, add or confirm a gitignore rule for:

```text
d5b_processor_v3/source_cache/
```

Policy:

- Raw external data: not committed.
- Exported 2K external rasters: not committed.
- Diagnostics: not committed.
- Source cache `manifest.json`: may remain untracked inside gitignored cache, or a sanitized tracked manifest template may be created later by explicit decision.
- README: can be tracked only if it contains instructions and no data paths that imply committed raw files.

Minimum manifest fields:

- `dataset`
- `version`
- `license`
- `source_url`
- `dataset_id`
- `export_method`
- `export_date`
- `resolution`
- `file_path`
- `checksum`
- `commercial_clearance`
- `research_only`
- `attribution`
- `caveats`

## 3. Import Test

No import test was run because no sample file is present.

Required manual export steps for ESA WorldCover:

1. Use Earth Engine dataset `ESA/WorldCover/v200`.
2. Select band `Map`.
3. Export global equirectangular extent:
   - lon: `-180` to `180`
   - lat: `-90` to `90`
4. Target dimensions:
   - preferred D-2: `2048x1024`
   - optional later intermediate: `21600x10800`, separately authorized
5. Recommended format:
   - GeoTIFF for full class raster;
   - or uint8 GeoTIFF/PNG/TIFF for class-60 diagnostic binary.
6. Expected file path after user provides export:

```text
d5b_processor_v3/source_cache/desert_arid/exported_2k/esa_worldcover_2021_v200_map_2048x1024.tif
```

Required manual sample path for Global Aridity:

```text
d5b_processor_v3/source_cache/desert_arid/exported_2k/global_aridity_index_2048x1024.tif
```

or, if NetCDF / grid format is used:

```text
d5b_processor_v3/source_cache/desert_arid/exported_2k/global_aridity_index_2048x1024.nc
```

When a sample is available, D-2-R should test:

- file readable;
- dimensions;
- projection / geographic extent;
- lon/lat orientation;
- y-axis flip requirement;
- equirectangular alignment with RodiO `(1024, 2048)` convention;
- nodata handling;
- class/value validity;
- no unexpected NaN / Inf;
- resampling to `2048x1024`;
- conversion to diagnostic arrays only.

## 4. Diagnostic Mapping Test

No diagnostic arrays, previews, or stats were generated in this phase because no sample exists.

Planned ESA WorldCover diagnostic checks:

- class histogram;
- class `60` bare / sparse vegetation pixel count;
- water / snow / built-up / cropland / tree cover counts;
- diagnostic `bare_sparse_candidate` array;
- no formal mask output.

Planned Global Aridity diagnostic checks:

- value range;
- nodata count;
- encoding / scale factor check;
- draft hyper-arid / arid / semi-arid threshold counts;
- diagnostic `arid_candidate` array;
- no formal mask output.

Diagnostic arrays are not structure masks. They must not enter d6, production, candidates, or API freeze.

## 5. Key Region Diagnostic Spot Check

No bbox stats were computed because no sample exists.

Future validation checklist:

| Region | ESA bare/sparse response | Aridity response | Diagnostic Verdict | Notes |
| ------ | ------------------------ | ---------------- | ------------------ | ----- |
| Sahara | pending sample | pending sample | blocked | hard region |
| Arabian Desert | pending sample | pending sample | blocked | hard region |
| Namib | pending sample | pending sample | blocked | hard region |
| Atacama | pending sample | pending sample | blocked | hard region |
| Australian deserts | pending sample | pending sample | blocked | hard region |
| Taklamakan | pending sample | pending sample | blocked | hard region |
| Sahel | pending sample | pending sample | blocked | transition watchlist |
| Gobi | pending sample | pending sample | blocked | cold/arid watchlist |
| Kalahari | pending sample | pending sample | blocked | semi-arid watchlist |
| Great Basin | pending sample | pending sample | blocked | dry basin watchlist |
| Altiplano dry regions | pending sample | pending sample | blocked | high cold arid watchlist |

## 6. Tooling / Environment Notes

Current local environment:

- `rasterio`: missing
- `osgeo` / GDAL Python bindings: missing
- `gdalinfo`: not found
- `ogrinfo`: not checked in this phase, previously not found
- `xarray`: available
- `netCDF4`: available
- `PIL`: available
- `numpy`: available
- `scipy`: available, with existing NumPy/SciPy version warning

Implications:

- Earth Engine export remains the preferred path.
- Do not process full global GeoTIFF/COG tiles locally in this phase.
- Do not install GDAL/rasterio inside this phase.
- A NetCDF or simple array sample may be easier to test than GeoTIFF with current tooling.
- A future B-6.2G-4D-2P tooling patch may be needed if GeoTIFF import becomes mandatory.

## 7. Decision Gate

| Gate | Result | Reason |
| ---- | ------ | ------ |
| ESA 2K export/import | blocked | no sample available |
| Global Aridity import | blocked | no sample available |
| Can enter B-6.2G-4B | no | D-2 import validation has not passed |
| Need B-6.2G-4D-2-R | yes | repeat after sample is provided |
| Need manual export/download | yes | Earth Engine ESA export and Global Aridity sample needed |
| Need higher-res intermediate export | not now | 2K sample should pass first |
| Need 21.6K export later | later only | requires separate authorization |

## 8. Final Recommendation

- Can ESA WorldCover proceed to prototype? **Blocked until 2K export sample exists and passes D-2-R.**
- Can Global Aridity proceed to prototype? **Blocked until research-only sample exists and passes D-2-R.**
- Can B-6.2G-4B start now? **No.**
- What files are required next?
  - `d5b_processor_v3/source_cache/desert_arid/exported_2k/esa_worldcover_2021_v200_map_2048x1024.tif`
  - `d5b_processor_v3/source_cache/desert_arid/exported_2k/global_aridity_index_2048x1024.tif` or `.nc`
  - `d5b_processor_v3/source_cache/desert_arid/manifest.json`
- What manual export/download steps are required?
  - Earth Engine export for ESA WorldCover `ESA/WorldCover/v200` band `Map`.
  - Provide or export a low-res Global Aridity sample under research-only terms.
  - Confirm `source_cache/` is gitignored before placing files.
- Should full-res raw download start now? **No.**
- Should Earth Engine export be used? **Yes.**
- Can d6 be touched? **No.**
- Can visual rebuild / 上色 start? **No.**

## 9. Completion Notes

- Code modified: no
- Data downloaded: no
- Source cache created: no
- Sample read: no
- Diagnostic outputs generated: no
- Formal masks generated: no
- Structure mask generator run: no
- d6 run: no
- pwa / production / candidates written: no
- Commit / push: no
- Critical issue: no sample available and `source_cache/` is not currently confirmed gitignored

