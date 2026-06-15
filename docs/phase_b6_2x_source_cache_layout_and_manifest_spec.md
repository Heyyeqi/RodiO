# Phase B-6.2X — Source Cache Layout and Manifest Specification

Stage: B-6.2X-D2
Date: 2026-06-15
Status: Specification only. No data has been downloaded or generated.

This document defines the local source cache directory layout, file naming
conventions, and manifest JSON schema for the B-6.2X GEE global source cache.

---

## 1. Source Cache Root

```
d5b_processor_v3/source_cache/gee_global/
```

This entire directory tree is gitignored. Nothing in it is committed to the repo.

---

## 2. Directory Layout

```
d5b_processor_v3/source_cache/gee_global/
│
├── exported_8k/
│   └── {source}_{version}_{band}_8192x4096.tif
│
├── exported_21600/
│   └── {source}_{version}_{band}_21600x10800.tif
│
├── manifests/
│   ├── manifest.template.json          (do not fill directly — copy and rename)
│   └── {filename}.manifest.json        (one per .tif file, filled after D3 import)
│
└── diagnostics/
    └── {source}_{band}_{resolution}_import_stats.json   (written by D3 scripts)
```

---

## 3. File Naming Convention

Pattern: `{source_name}_{version}_{band}_{width}x{height}.tif`

Rules:
- All lowercase
- Underscores as separators, no spaces or hyphens
- Version included when the dataset has a versioned release (e.g., `v200`, `v1_4`)
- Width and height always explicit as integers (not `8k`, not `8K`)
- Band name matches the GEE band name exactly when single-band export
- For derived bands (slope, relief), use descriptive name (`slope`, `relief`)

### Phase 1 Canonical Filenames

| File | Tier | Source |
|---|---|---|
| `esa_worldcover_2021_v200_map_8192x4096.tif` | 8K | ESA WorldCover v200 |
| `jrc_gsw_occurrence_8192x4096.tif` | 8K | JRC GSW v1.4 |
| `jrc_gsw_seasonality_8192x4096.tif` | 8K | JRC GSW v1.4 |
| `jrc_gsw_recurrence_8192x4096.tif` | 8K | JRC GSW v1.4 |
| `jrc_gsw_max_extent_8192x4096.tif` | 8K | JRC GSW v1.4 |
| `copernicus_dem_glo30_elevation_8192x4096.tif` | 8K | Copernicus DEM GLO-30 |
| `copernicus_dem_glo30_slope_8192x4096.tif` | 8K | Copernicus DEM GLO-30 derived |
| `copernicus_dem_glo30_relief_8192x4096.tif` | 8K | Copernicus DEM GLO-30 derived |
| `etopo1_bedrock_8192x4096.tif` | 8K | ETOPO1 |
| `etopo1_ice_surface_8192x4096.tif` | 8K | ETOPO1 |
| `esa_worldcover_2021_v200_map_21600x10800.tif` | 21.6K | ESA WorldCover v200 |
| `copernicus_dem_glo30_elevation_21600x10800.tif` | 21.6K | Copernicus DEM GLO-30 |
| `copernicus_dem_glo30_slope_21600x10800.tif` | 21.6K | Copernicus DEM GLO-30 derived |
| `etopo1_bedrock_21600x10800.tif` | 21.6K | ETOPO1 |
| `etopo1_ice_surface_21600x10800.tif` | 21.6K | ETOPO1 |

### Phase 3 Pre-reserved Filenames (not yet acquired)

| File | Tier | Source |
|---|---|---|
| `gebco_2023_global_bathymetry_8192x4096.tif` | 8K | GEBCO (external) |
| `gebco_2023_global_bathymetry_21600x10800.tif` | 21.6K | GEBCO (external) |
| `glims_glacier_mask_8192x4096.tif` | 8K | GLIMS (GEE vector rasterized) |
| `dynamic_world_2021_label_8192x4096.tif` | 8K | Dynamic World V1 |

---

## 4. Manifest JSON Schema

Every `.tif` file in `exported_8k/` or `exported_21600/` must have a
corresponding manifest file in `manifests/` before it is used in mask
derivation. The manifest schema extends the template at
`manifests/manifest.template.json`.

### Required Fields

| Field | Type | Description |
|---|---|---|
| `dataset` | string | Human-readable dataset name |
| `version` | string | Dataset version (e.g., `v200`, `v1.4`) |
| `gee_asset_id` | string | GEE Data Catalog ID (e.g., `ESA/WorldCover/v200`) |
| `export_method` | string | Always `"GEE batch export to Drive"` for GEE sources |
| `bands_exported` | array | List of GEE band names exported |
| `resolution_px` | string | Pixel dimensions as `{W}x{H}` string |
| `scale_m` | number | GEE export scale in meters per pixel |
| `crs` | string | Always `"EPSG:4326"` for Phase 1 exports |
| `region` | string | Export region description |
| `drive_folder` | string | Google Drive folder name used during export |
| `filename` | string | Exact filename of the .tif file |
| `local_path` | string | Relative path from repo root to the .tif file |
| `export_date` | string | ISO 8601 date when GEE export was submitted (fill after export) |
| `checksum_sha256` | string | SHA-256 of the downloaded .tif (fill after download) |
| `import_verified` | boolean | Set to `true` only after D3 import validation passes |
| `import_date` | string | ISO 8601 date of D3 import validation |
| `nodata_value` | string | Nodata handling (documented per source) |
| `dtype` | string | GeoTIFF data type (e.g., `uint8`, `float32`, `int16`) |
| `value_range` | string | Description of valid value range |
| `license` | string | SPDX license identifier or descriptive string |
| `attribution` | string | Full attribution string required by license |
| `commercial_clearance` | string | See policy below — must be `pending_review` until RW sign-off |
| `license_url` | string | URL to license text |
| `notes` | string | Any caveats, exceptions, or processing notes |

### commercial_clearance Field Policy

The `commercial_clearance` field MUST be set to one of the following values
until RW formally reviews and approves each source for RodiO's production
and commercial context:

- `pending_review` — default for all D2 manifest entries
- `needs_source_verification` — when the license text requires additional
  clarification before production use can be confirmed

Do NOT write any of the following values in this field:
- `approved`
- `cleared`
- `commercial_ok`
- `ok`
- Any string that implies final authorization

Only RW can change this field to an approved status after formal review.

---

## 5. Per-Source License Notes (Preliminary)

These notes are informational only. All `commercial_clearance` entries remain
`pending_review` until RW verification.

| Source | License | Attribution Required | Commercial Clearance |
|---|---|---|---|
| ESA WorldCover v200 | CC-BY-4.0 | Yes (ESA) | pending_review |
| JRC Global Surface Water v1.4 | CC-BY-4.0 | Yes (JRC / Pekel et al.) | pending_review |
| Copernicus DEM GLO-30 | Copernicus Open Access Hub Terms | Yes (ESA / Copernicus) | pending_review — country exceptions apply; see GEE catalog |
| ETOPO1 | NOAA public domain | Yes (NOAA NCEI / Amante & Eakins 2009) | pending_review |
| GEBCO (Phase 3) | GEBCO Open Data License | Yes (GEBCO Compilation Group) | pending_review |
| Dynamic World V1 (Phase 2) | CC-BY-4.0 | Yes (Google / Brown et al.) | pending_review |
| GLIMS (Phase 2) | Varies by contributor | Yes (NSIDC / GLIMS) | needs_source_verification |

---

## 6. Manifest Lifecycle

```
D2: manifest template and example exist in repo (scripts/gee_export/manifest.example.json)
    → no real manifest instances yet

D3: after each 8K file is imported and validated:
    → copy manifest.template.json to manifests/{filename}.manifest.json
    → fill all fields except commercial_clearance (remains pending_review)
    → set import_verified: true after validation passes

D4: after 21.6K files are verified:
    → same process for exported_21600/ files

Post-D4: RW reviews commercial_clearance fields
    → only RW may update commercial_clearance from pending_review
```

---

## 7. What Is and Is Not Committed to the Repo

| Path | Committed? |
|---|---|
| `scripts/gee_export/*.js` | Yes (script drafts) |
| `scripts/gee_export/README.md` | Yes |
| `scripts/gee_export/manifest.example.json` | Yes (example only) |
| `docs/phase_b6_2x_source_cache_layout_and_manifest_spec.md` | Yes (this file) |
| `d5b_processor_v3/source_cache/` (entire tree) | No — gitignored |
| Any `.tif` or `.npz` file | No — gitignored |
| `manifests/*.manifest.json` (real instances) | No — gitignored |
| `diagnostics/` (D3 outputs) | No — gitignored |

---

## 8. D3 Entry Criteria

Before entering B-6.2X-D3 (8K Import Test):

- At least one Phase 1 8K file must be manually downloaded from Google Drive
  and placed in `exported_8k/`
- The corresponding manifest template must be filled (import_verified: false)
- D3 scripts will then validate shape, dtype, values, nodata, and class
  histograms and set `import_verified: true` on pass

Do not enter D3 without at least one downloaded file to validate.
