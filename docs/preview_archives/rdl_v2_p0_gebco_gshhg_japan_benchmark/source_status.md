# RDL v2 P0 — Source Data Status

**Date:** 2026-06-08
**Region:** 118_150_22_50 (lon 118–150°E, lat 22–50°N)
**Phase:** P0 Japan benchmark — natural geography layer only
(City roads and lights deferred to Layer 6: Vector / Light Overlay)

---

## Layer 4: Coastline Data (GSHHG)

| Item | Status | Detail |
|---|---|---|
| **GSHHG full resolution** | ✅ downloaded + extracted | `pwa/assets/source/coastline/gshhg/GSHHS_shp/f/GSHHS_f_L1.shp` (161 MB) |
| NaturalEarth 10m coastline | ✅ downloaded (interim backup) | `/tmp/ne_10m_coastline/ne_10m_coastline.shp` |

**Current pipeline source for gshhg_coastline_mask.png:**
→ Land mask: GSHHG L1 full resolution polygons (7,820 polygons in Japan region, rendered at 4096×3584)
→ Coastline edge: morphological edge detection from GSHHG mask (160,000+ coastline pixels)
→ Result: Land=30.4%, Sea=68.5%, Coast=1.09%

---

## Layer 3: Bathymetry (GEBCO)

| Item | Status | Detail |
|---|---|---|
| **GEBCO 2026 Japan subset** | ✅ downloaded + verified | `pwa/assets/source/bathy/gebco_2026/gebco_2026_118_150_22_50.nc` (46MB, 6720×7680, z -8378m to +3757m, 0 NoData) |
| **ETOPO1** (fallback) | ✅ available | `pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd` (890 MB, 1.85 km/px) |

**Current pipeline source for etopo1_bathymetry_tint.png:**
→ ETOPO1, subset shape: 1681 × 1921 px native, 5-level depth tint applied
→ z-range in Japan region: -6792m to +2105m ✅

**GEBCO pipeline (completed):**
→ `gebco_bathymetry_tint.py --bounds 118 150 22 50 --nc <path>` → `gebco_bathymetry_tint.png` ✅
→ GEBCO vs ETOPO1 comparison → `etopo_vs_gebco_compare.png` ✅
→ Confirmed: 6720×7680 (15 arc-sec), 4× better than ETOPO1, land ratio 30.6% matches GSHHG 30.4%

---

## Layer 5: Elevation / DEM (Copernicus GLO-30)

| Item | Status | Detail |
|---|---|---|
| Copernicus DEM GLO-30 | DEFERRED | Not downloaded this phase (per scope constraint) |
| ETOPO1 (land elevation) | ✅ available as fallback | Same file as bathy |

---

## Processed Output Status

| Output File | Status | Source |
|---|---|---|
| `etopo1_bathymetry_tint.png` | ✅ complete | ETOPO1, 5-level depth |
| `gshhg_coastline_mask.png` | ✅ **FINAL** | GSHHG L1 full-res (7820 polys, 4096×3584, 160K coast px) |
| `gshhg_distance_field.png` | ✅ **FINAL** | computed from GSHHG L1 mask |
| `key_crops_contact_sheet.png` | ✅ **FINAL** | 5 key regions, GSHHG L1 polygons |
| `combined_etopo1_gshhg_preview.png` | ✅ reference (ETOPO1+GSHHG) — renamed from old misleading name | ETOPO1 tint + GSHHG L1 coast |
| `combined_gebco_gshhg_preview.png` | ✅ **FINAL** (GEBCO+GSHHG combined) | GEBCO 2026 tint + GSHHG L1 coast |
| `gebco_download_check.md` | ✅ complete | Manual research |
| `gebco_bathymetry_tint.png` | ✅ **FINAL** | GEBCO 2026, 6720×7680, 5-level depth |
| `etopo_vs_gebco_compare.png` | ✅ **FINAL** | ETOPO1 vs GEBCO 2026 side-by-side |

---

## Next Actions to Complete P0

**P0 is COMPLETE.** All blockers resolved. Pipeline output:
- GSHHG L1 land mask / SDF / key crops (Phase 1) ✅
- GEBCO 2026 bathymetry tint + ETOPO1 comparison (Phase 2) ✅
- GEBCO+GSHHG combined 4-panel preview (Phase 3) ✅
- README_P0_RESULT.md Q1-Q6 all answered ✅

~~Phase 1 GSHHG: COMPLETE~~ ✅

---

## Script Inventory (scripts/geo/)

| Script | Purpose | Reusable? |
|---|---|---|
| `lon_lat_to_uv.js` | Geo → Three.js UV converter | ✅ any region via `--bounds` |
| `gshhg_coastline_render.py` | Land mask + distance field + key crops | ✅ any region via `--bounds` |
| `gebco_bathymetry_tint.py` | 5-level bathy tint (GEBCO or ETOPO1) | ✅ any region via `--bounds` |
| `rdl_composite_preview.py` | 4-panel composite preview | ✅ any region via `--bounds` |
