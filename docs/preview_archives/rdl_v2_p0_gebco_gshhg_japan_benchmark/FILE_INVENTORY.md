# P0 File Inventory — rdl_v2_p0_gebco_gshhg_japan_benchmark

**Date:** 2026-06-08  
**Region:** 118_150_22_50 (lon 118–150°E, lat 22–50°N)  
**Status:** P0 complete; no commit pending

---

## Source Data (pwa/assets/source/)

| File | Size | Format | Role |
|---|---|---|---|
| `bathy/gebco_2026/gebco_2026_118_150_22_50.nc` | 46MB | NetCDF4, int16, zlib4 | **Main bathy source** (6720×7680, 15 arc-sec, z −8378m to +3757m) |
| `coastline/gshhg/GSHHS_shp/f/GSHHS_f_L1.shp` | 154MB | ESRI Shapefile | **Main coastline source** (GSHHG L1 land, ~25m accuracy) |
| `bathy/ETOPO1_Ice_g_gdal.grd` | 890MB | GMT grd | Fallback/comparison bathy (1 arc-min, 1.85km/px) |

---

## Preview Outputs (previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/)

### Documentation

| File | Size | Role |
|---|---|---|
| `README_P0_RESULT.md` | ~12KB | P0 validation results (Q1–Q6), evidence chain, HTTP Range risk note, layer stack |
| `source_status.md` | 3.7KB | Per-layer data source status table |
| `gebco_download_check.md` | 2.6KB | GEBCO 2026 version confirmation, download params, size estimates |
| `FILE_INVENTORY.md` | (this file) | Canonical file listing with sizes, formats, generation commands, roles |
| `NEXT_JAPAN_V2_TILE_PLAN.md` | — | Japan v2 2048/4096 regional detail tile composite plan |

### Phase 1 — GSHHG Coastline (FINAL)

| File | Size | Generation Command | Role |
|---|---|---|---|
| `gshhg_coastline_mask.png` | 161KB | `python3 scripts/geo/gshhg_coastline_render.py --bounds 118 150 22 50 --shp pwa/assets/source/coastline/gshhg/GSHHS_shp/f/GSHHS_f_L1.shp` | Binary land mask + coastline edge at 4096×3584 |
| `gshhg_distance_field.png` | 1.4MB | same command | Signed distance-to-coast field (grayscale) at 4096×3584 |
| `key_crops_contact_sheet.png` | 189KB | same command | 5-panel crop contact sheet (Tokyo Bay, Osaka Bay, Okinawa Arc, Tsugaru Strait, Kyushu W) |

**GSHHG stats:** 7820 L1 polygons in Japan region; land 30.4%, sea 68.5%, coastline edge 1.09% (160K+ px)

### Phase 2 — Bathymetry (FINAL)

| File | Size | Generation Command | Role |
|---|---|---|---|
| `gebco_bathymetry_tint.png` | 892KB | `python3 scripts/geo/gebco_bathymetry_tint.py --bounds 118 150 22 50 --nc pwa/assets/source/bathy/gebco_2026/gebco_2026_118_150_22_50.nc` | **GEBCO 2026** 5-level depth tint at native 6720×7680 |
| `etopo1_bathymetry_tint.png` | 81KB | same script with `--etopo` | ETOPO1 5-level depth tint at native 1921×1681 (comparison only) |
| `etopo_vs_gebco_compare.png` | 1.4MB | same script with `--compare` | Side-by-side: ETOPO1 (left) vs GEBCO 2026 (right) |

**GEBCO 2026 stats:** 6720×7680, 15 arc-sec, z −8378m (Japan Trench) to +3757m (≈Mt. Fuji), land 30.6%, 0 NoData

### Phase 3 — Composite Previews

| File | Size | Generation Command | Role |
|---|---|---|---|
| `combined_gebco_gshhg_preview.png` | 3.0MB | `python3 scripts/geo/rdl_composite_preview.py --bounds 118 150 22 50` | **FINAL** 4-panel composite: base gray / GEBCO 2026 tint / GSHHG L1 coast / combined |
| `combined_etopo1_gshhg_preview.png` | 2.9MB | (historic — do not re-run with this name) | Reference: interim 4-panel with ETOPO1 tint (renamed from misleading `combined_gebco_gshhg_preview.png`) |

**Note:** `combined_etopo1_gshhg_preview.png` was the original file generated before GEBCO was downloaded. It was renamed when the correct GEBCO-based file replaced it. Kept for comparison.

---

## Scripts (scripts/geo/)

| Script | Language | Purpose | Key CLI Flags |
|---|---|---|---|
| `lon_lat_to_uv.js` | Node.js | Geo → Three.js r128 UV bounds + GLSL snippet | `--bounds lon_w lon_e lat_s lat_n` |
| `gshhg_coastline_render.py` | Python 3 | Land mask + SDF + key region crops | `--bounds`, `--shp <shapefile>`, `--out <dir>` |
| `gebco_bathymetry_tint.py` | Python 3 | 5-level depth tint (GEBCO or ETOPO1) | `--bounds`, `--nc <netcdf>`, `--etopo`, `--compare` |
| `rdl_composite_preview.py` | Python 3 | 4-panel composite preview | `--bounds`, `--out <dir>` |

All scripts use `--bounds lon_w lon_e lat_s lat_n`; no place names hardcoded.

---

## Scratch Files (not part of P0 deliverables)

| File | Location | Status |
|---|---|---|
| `gebco_row_slices.py` | `/tmp/` | Working GEBCO download script (column-slice method, 50 workers) — keep for reference |
| `gebco_range_download.py` | `/tmp/` | Earlier GEBCO download script (full-row method, abandoned — too slow) |

---

## Not Downloaded / Out of Scope for P0

| Source | Reason |
|---|---|
| Copernicus DEM GLO-30 | Deferred per scope constraint; planned for Japan v2 tile phase |
| OSM road/building data | Layer 6 scope (Vector / Light Overlay) |
| VIIRS Night Lights | Layer 6 scope |
