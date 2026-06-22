# scripts/gee_export — GEE Export Script Draft

Stage: B-6.2X-D2
Date: 2026-06-15
Status: Script draft only. No exports have been executed. No data has been downloaded.

This directory contains Google Earth Engine (GEE) export script drafts for the
B-6.2X global source cache phase.

---

## Purpose

These scripts are intended to be copy-pasted into the GEE Code Editor at
https://code.earthengine.google.com and run manually by RW. They are NOT
executed automatically and do NOT call any external service during normal
development.

---

## Scripts

| File | Resolution | Purpose |
|---|---|---|
| `export_phase1_8k.js` | 8192×4096 | Phase 1 core sources — primary import/validation tier |
| `export_phase1_21600.js` | 21600×10800 | Phase 1 core sources — master cache tier (reference draft, not yet executed) |

---

## How to Execute (Manual, RW Only — Requires Explicit Authorization)

**D2 scripts are inert drafts. Do not click Run for export submission.**
Actual export requires RW approval and an explicit uncomment of the function
call at the bottom of each script (`definePhase1Exports()` for 8K,
`definePhase1Exports21600()` for 21.6K). Pasting the script into the GEE
Code Editor and clicking Run without uncommenting the function call will
submit no tasks and produce no output.

Steps (to be followed only after RW authorization):

1. Open https://code.earthengine.google.com in a browser.
2. Sign in with the Google account that has GEE access.
3. Open a new script in the Code Editor.
4. Copy the contents of `export_phase1_8k.js` and paste into the editor.
5. Review the Drive folder name at the top of the script.
   - Default Drive folder: `RodiO_GEE_Cache_Phase1`
   - Ensure this folder exists in your Google Drive before proceeding.
6. After RW authorization: uncomment `// definePhase1Exports();` at the
   bottom of the script to register export tasks.
7. Click **Run** in the Code Editor (this registers tasks but does not start them).
8. Switch to the **Tasks** tab in the GEE Code Editor.
9. Click **RUN** next to each listed task only after reviewing task names and
   confirming they match expected filenames (GEE does not auto-start batch tasks).
10. Wait for tasks to complete (typically 10–60 minutes per export at 8K).
11. Open Google Drive → `RodiO_GEE_Cache_Phase1` and download each `.tif` file.
12. Place downloaded files into:
    `d5b_processor_v3/source_cache/gee_global/exported_8k/`

---

## Drive Folder

Default: `RodiO_GEE_Cache_Phase1`

This folder must be created manually in Google Drive before running exports.
Do not commit Drive contents to the repo.

---

## Google Drive Quota Notes

Phase 1 exports include approximately 10 separate tasks (4 JRC GSW bands,
3 Copernicus DEM bands, 2 ETOPO1 bands, 1 ESA WorldCover band).

Approximate file sizes at 8K (estimated, uncompressed GeoTIFF):

| Source | Approx Size |
|---|---|
| ESA WorldCover 8K | ~32 MB (uint8 single band) |
| JRC GSW occurrence 8K | ~32 MB (uint8) |
| JRC GSW seasonality 8K | ~32 MB (uint8) |
| JRC GSW recurrence 8K | ~32 MB (uint8) |
| JRC GSW max_extent 8K | ~32 MB (uint8) |
| Copernicus DEM elevation 8K | ~128 MB (float32) |
| Copernicus DEM slope 8K | ~128 MB (float32) |
| Copernicus DEM relief 8K | ~128 MB (float32) |
| ETOPO1 bedrock 8K | ~64 MB (int16) |
| ETOPO1 ice_surface 8K | ~64 MB (int16) |

Total: approximately 672 MB uncompressed. GeoTIFF compression (LZW or DEFLATE)
will reduce this. Ensure sufficient Drive quota before starting.

---

## GEBCO (Phase 3 — Not in These Scripts)

GEBCO is not available in the GEE Data Catalog. It must be downloaded separately:

- Source: https://www.gebco.net (GEBCO 2023 or latest grid)
- Format: GeoTIFF global grid (15 arc-second)
- Estimated size: ~8 GB (raw)
- Local target path (pre-reserved):
  `d5b_processor_v3/source_cache/gee_global/exported_8k/gebco_2023_global_bathymetry_8192x4096.tif`
- License: GEBCO Open Data License
- Attribution: `GEBCO Compilation Group (2023) GEBCO 2023 Grid, doi:10.5285/...`
- Commercial clearance: pending_review (RW must verify before production use)

Do not acquire GEBCO until Phase 3 is explicitly authorized.

---

## After Export — Local Placement

```
d5b_processor_v3/source_cache/gee_global/
  exported_8k/      ← place 8K .tif files here
  exported_21600/   ← place 21.6K .tif files here
  manifests/        ← fill manifest JSON per file after successful import
  diagnostics/      ← written by D3 import validation scripts
```

All files in `source_cache/` are gitignored. Do not commit them.

---

## License Notes (Preliminary — pending_review)

All license and commercial clearance fields in manifest files must be set to
`pending_review` or `needs_source_verification` until RW formally verifies
each source's terms for RodiO's specific production and commercial context.
Do not write `approved`, `cleared`, or `commercial_ok` in any manifest field
until RW signs off after D3 import validation.
