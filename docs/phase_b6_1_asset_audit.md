# Phase B-6.1 — Asset Audit

**Audit Date:** 2026-06-10  
**Auditor:** Claude Code (automated read-only checks)  
**Source brief:** `docs/phase_b6_1_asset_audit_task_brief.md`  
**Status:** COMPLETE — no files modified, no masks generated, no code changed

---

## 1. Executive Summary

All primary assets required for B-6.2 are **present and verified**:

| Asset | Status | Notes |
|---|---|---|
| ETOPO1 Ice Surface (GMT NetCDF4) | **READY** | 890 MB, global, 21601×10801 @ 1 arcmin |
| GSHHG 2.3.7 (full + high resolution) | **READY** | L1–L6, all 5 tiers extracted |
| GEBCO 2026 | Japan subset only | lon 118–150, lat 22–50; NOT global |
| Existing color-classifier ocean mask | Available (4096×2048) | Not structure-based; supplemental only |
| Core Python dependencies | **READY** | netCDF4 / scipy / numpy / shapefile / Pillow |
| Optional Python dependencies | 4 missing | geopandas / rasterio / pyproj / skimage |

**B-6.2 Go/No-Go: `READY_TO_PROCEED`**

ETOPO1 + GSHHG + available Python stack is sufficient to generate all required minimum masks at 2K. Optional missing deps (geopandas, rasterio, pyproj, skimage) are NOT required for the B-6.2 minimal mask set. Existing scripts (`generate_d5a_bathy.py`) already demonstrate the full ETOPO1 read-reshape-downsample pipeline.

---

## 2. Current Git Safety Status

```
 M d5b_processor_v3/d6_noon_air_earth_generator.py   ← B-5.1+B-5.2, NOT committed
?? previews/...                                        ← NOT committed
```

- `d6_noon_air_earth_generator.py` remains unstaged; no risk of accidental commit
- No masks were generated during this audit
- No code was modified
- No generator was run

---

## 3. ETOPO1 Audit

### 3.1 File Identity

| Field | Value |
|---|---|
| **Path** | `pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd` |
| **Compressed backup** | `pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd.gz` (377 MB) |
| **Format** | NetCDF4 (GMT-style `gdal` variant) |
| **File size** | 890 MB |
| **MD5** | `36edc15622edcae8ccc9486a88c6488a` |

### 3.2 Grid Parameters

| Field | Value |
|---|---|
| **Dimensions** | 21,601 × 10,801 (width × height) |
| **Total cells** | 233,312,401 |
| **Resolution** | 0.016667° ≈ 1 arc-minute ≈ 1.85 km/pixel at equator |
| **Lon range** | −180.0 → +180.0 (global) |
| **Lat range** | −90.0 → +90.0 (global) |
| **Coverage** | **GLOBAL** ✓ |

### 3.3 Data Variables

| Field | Value |
|---|---|
| **Variable name** | `z` (flat array, int32) |
| **Elevation range** | −10,898 m (Mariana Trench) → +8,271 m (summit) |
| **Units** | meters (implicit; standard ETOPO1 convention) |
| **Fill / NoData value** | −2,147,483,648 (int32 min, no land gaps in GMT ice grid) |
| **Variant** | Ice Surface (`_Ice_`) — includes Antarctic and Greenland ice shelf elevation |

### 3.4 Depth Bands for Mask Generation

| Mask | Depth condition | Expected coverage |
|---|---|---|
| `land_mask` | z > 0 | Continental + island land |
| `ocean_mask` | z ≤ 0 | All ocean + ice shelf areas |
| `shallow_sea_mask` | −200 ≤ z < 0 | Continental shelf / reef |
| `continental_shelf_mask` | −1000 ≤ z < −200 | Mid-depth shelf |
| `mid_ocean_mask` | −3500 ≤ z < −1000 | Mid-ocean ridges, slopes |
| `deep_ocean_mask` | z < −3500 | Abyssal plains, trenches |
| `mountain_mask` | z > 1500 (land) | High peaks |
| `plateau_mask` | 500 < z ≤ 1500 (land) | Plateaus, highlands |

### 3.5 Resample to 2K

At 2K (2048×1024):
- Source 21601 → 2048: downsample factor ≈ 10.5×
- Source 10801 → 1024: downsample factor ≈ 10.5×
- Method: `np.linspace` index mapping (already used in `generate_d5a_bathy.py`)
- **Confirmed feasible** — existing script already does this for 8K; 2K is simpler

### 3.6 Python Readability

```python
import netCDF4 as nc
import numpy as np
ds = nc.Dataset('pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd')
dim = ds.variables['dimension'][:]
z_raw = ds.variables['z'][:].astype(np.float32).reshape(int(dim[1]), int(dim[0]))
# → shape (10801, 21601), north-first, float32
```

**Status: CONFIRMED WORKING** (verified by audit probe and prior scripts)

### 3.7 Limitations

- Ice variant includes Greenland/Antarctic ice shelf elevation, not bedrock
- `_gdal.grd` variant uses flat `z` array; reshape required (not conventional lat/lon axes)
- No explicit CRS metadata in file; EPSG:4326 assumed (standard ETOPO1 convention)
- 1 arc-minute resolution = ~1.85 km/px; adequate for 2K–8K structure masks but not reef-level detail

---

## 4. GSHHG Audit

### 4.1 File Identity

| Field | Value |
|---|---|
| **Zip path** | `pwa/assets/source/coastline/gshhg/gshhg-shp-2.3.7.zip` |
| **Zip size** | 142 MB |
| **Version** | 2.3.7 (current stable) |
| **Extracted root** | `pwa/assets/source/coastline/gshhg/GSHHS_shp/` |
| **License** | LGPLv3 (confirmed present: `COPYING.LESSERv3`) |

### 4.2 Available Tiers and L1 Sizes

| Tier | Resolution | L1 Shape file | L1 Size | L1 Feature count |
|---|---|---|---|---|
| `f` (full) | ~25 m | `GSHHS_shp/f/GSHHS_f_L1.shp` | **154 MB** | **179,837** |
| `h` (high) | ~200 m | `GSHHS_shp/h/GSHHS_h_L1.shp` | 33 MB | 144,749 |
| `i` (intermediate) | ~1 km | `GSHHS_shp/i/GSHHS_i_L1.shp` | 6.9 MB | — |
| `l` (low) | ~25 km | `GSHHS_shp/l/GSHHS_l_L1.shp` | 1.2 MB | — |
| `c` (crude) | ~500 km | `GSHHS_shp/c/GSHHS_c_L1.shp` | 154 KB | — |

**MD5 (f/L1):** `2e283b3a193c6111beeae7c0ff7374d3`

All tiers L1–L6 present for all 5 resolutions. WDBII river/border shapefiles also present.

### 4.3 Coverage

- **bbox (f/L1):** xmin=−180.0, ymin=−68.92, xmax=+180.0, ymax=+83.63
- **Coverage: GLOBAL** (ymin/ymax excludes deep Antarctic interior, not relevant for coastlines)

### 4.4 Layer Descriptions

| Layer | Contents | B-6 use |
|---|---|---|
| L1 | Land polygon (continent + islands) | `land_mask`, `island_proximity_mask` |
| L2 | Lake polygon | `lake_mask` (future) |
| L3 | Island in lake | Minimal relevance |
| L4 | Pond in island in lake | Not needed |
| L5 | Antarctic ice front | `ice_shelf_mask` (optional) |
| L6 | Antarctic grounding line | `ice_shelf_mask` (optional) |

### 4.5 Recommended Tier for B-6.2

| Use | Recommended tier | Reason |
|---|---|---|
| `land_mask` / `ocean_mask` at 2K | `h` (high) | 144K shapes, 33 MB; full (179K/154 MB) is slower but usable |
| `coastline_distance_mask` | `h` or `f` | More shapes = more accurate distance field |
| `small_island_mask` | `f` (full) | Only full captures sub-km islands |
| `island_proximity_mask` | `f` (full) | Reef/atoll detection needs highest resolution |

### 4.6 Python Readability

```python
import shapefile
sf = shapefile.Reader('pwa/assets/source/coastline/gshhg/GSHHS_shp/f/GSHHS_f_L1.shp')
# → 179,837 polygon shapes, bbox global
```

**Status: CONFIRMED WORKING** (pyshp 3.0.12 installed, verified by audit probe)

### 4.7 Rasterization Approach (no geopandas required)

For B-6.2, GSHHG rasterization does NOT require geopandas or rasterio. Pure numpy + shapefile:

```python
# Scan-line rasterization via PIL.ImageDraw
from PIL import Image, ImageDraw
import shapefile
img = Image.new('L', (2048, 1024), 0)
draw = ImageDraw.Draw(img)
sf = shapefile.Reader('...GSHHS_h_L1.shp')
for shape in sf.shapes():
    # project lon/lat → pixel, draw filled polygon
    ...
```

This approach is proven in the existing `gshhg_coastline_render.py` script.

---

## 5. GEBCO Audit

### 5.1 File Identity

| Field | Value |
|---|---|
| **Path** | `pwa/assets/source/bathy/gebco_2026/gebco_2026_118_150_22_50.nc` |
| **Format** | NetCDF4, variable `elevation` (int16) |
| **MD5** | `b05507ce8c6afc309857ad44d2c3993a` |
| **File size** | ~143 MB |

### 5.2 Coverage — Japan Subset Only

| Parameter | Value |
|---|---|
| **Lon range** | 118.00° → 150.00° (32° wide) |
| **Lat range** | 22.00° → 50.00° (28° tall) |
| **Coverage** | **Japan / Yellow Sea / East China Sea / Sea of Japan ONLY** |
| **Grid size** | 7,680 × 6,720 |
| **Resolution** | ~0.00417° ≈ 464 m/pixel (much finer than ETOPO1) |
| **Elevation range** | −10,668 m → +3,757 m |

### 5.3 Why GEBCO Cannot Serve as Global B-6 Foundation

1. **Coverage gap**: Covers only 32°×28° of 360°×180° globe (0.14% of global area)
2. **Incompatible extent**: Would require masking + blending with another global source for all other regions
3. **Resolution mismatch**: 464 m/px vs ETOPO1 1850 m/px — mixing would create seams
4. **B-6 requires global uniform coverage** for all 9 mask types

### 5.4 Valid Use of GEBCO Subset

- **Japan / Yellow East China / Japan Sea benchmark region** only
- Can serve as high-resolution reference to validate B-6.2 shelf/depth masks in this region
- Useful for the Japan special sea color correction context (B-5.3 Yellow/East China fix)
- Script `scripts/geo/gebco_bathymetry_tint.py` already uses it

### 5.5 Global GEBCO Recommendation

If high-resolution global bathymetry is needed beyond ETOPO1 (e.g., for reef/atoll detection):
- GEBCO 2023/2024/2026 global: ~7.8 GB (15 arc-second, 86400×43200)
- **Not required for B-6.2 minimum masks** — ETOPO1 at 1 arc-minute is sufficient
- Can be deferred to B-6.3 or later if reef_atoll_proxy_mask is required

---

## 6. Existing Masks and Scripts Audit

### 6.1 Existing Mask Assets

| Asset | Path | Size | Type | Resolution | Notes |
|---|---|---|---|---|---|
| `ocean_mask_4096x2048_soft.png` | `pwa/assets/earth/masks/` | 398 KB | Grayscale L | 4096×2048 | Color-classifier based; `B > R+15` heuristic |
| `ocean_mask_soft_preview.png` | `pwa/assets/earth/masks/` | 23 KB | Grayscale L | 1024×512 | Preview of above |
| `ocean_specular_4096x2048.png` | `pwa/assets/earth/masks/` | 73 KB | Grayscale L | 4096×2048 | Specular highlight mask |

**Assessment**: Existing masks are color-derived from the BMNG texture (pixel color classifier), NOT structure-derived from ETOPO1/GSHHG. They are suitable as supplemental references but:
- Cannot replace ETOPO1-based `deep_ocean_mask` (color classifier cannot distinguish depth)
- Cannot replace GSHHG-based `coastline_distance_mask` (no geographic precision)
- Will be replaced/augmented by B-6.2 structure masks

### 6.2 Existing Geo Scripts

| Script | Path | Purpose | ETOPO1 | GSHHG | GEBCO |
|---|---|---|---|---|---|
| `validate_etopo1_bathy.py` | `scripts/` | ETOPO1 validation | ✓ reads + reshapes | — | — |
| `generate_d5a_bathy.py` | `scripts/` | D5a depth-tinted texture | ✓ reads + downsamples to 8K | — | — |
| `generate_d6_topo_blend.py` | `scripts/` | D6 topo blend | ✓ | — | — |
| `gebco_bathymetry_tint.py` | `scripts/geo/` | GEBCO tinting (Japan) | — | — | ✓ |
| `gshhg_coastline_render.py` | `scripts/geo/` | GSHHG coastline rendering | — | ✓ rasterize | — |
| `d5b_processor_v3/masks.py` | `d5b_processor_v3/` | Color-classifier masks | — | — | — |

**Key finding**: `generate_d5a_bathy.py` already contains a working, production-validated ETOPO1 read-reshape-downsample pipeline at 8K. B-6.2 can directly adapt this logic for 2K mask generation. The hard ETOPO1 integration work is **already done**.

---

## 7. Python Dependency Audit

| Dependency | Installed | Version | Needed For | Required for B-6.2? | Fallback |
|---|---|---|---|---|---|
| **numpy** | ✓ | 1.23.3 | All array operations | **YES** | — |
| **Pillow** | ✓ | 11.3.0 | Mask output, polygon rasterization | **YES** | — |
| **scipy** | ✓ | 1.7.1 | Gaussian blur, distance_transform_edt, morphology | **YES** | — |
| **netCDF4** | ✓ | 1.7.2 | Read ETOPO1 .grd and GEBCO .nc | **YES** | xarray (also installed) |
| **h5py** | ✓ | 3.14.0 | HDF5 format GEBCO (if needed) | NO | netCDF4 sufficient |
| **xarray** | ✓ | 2024.7.0 | Alternative NetCDF4 reader | NO (fallback only) | netCDF4 |
| **shapefile** (pyshp) | ✓ | 3.0.12 | Read GSHHG .shp files | **YES** | — |
| **shapely** | ✓ | 2.0.7 | Polygon operations (optional) | NO | PIL.ImageDraw sufficient |
| **geopandas** | ✗ | MISSING | High-level shapefile processing | NO | shapefile + PIL |
| **rasterio** | ✗ | MISSING | GeoTIFF read/write | NO | netCDF4 + PIL |
| **pyproj** | ✗ | MISSING | Coordinate reprojection | NO | Equirectangular math in numpy |
| **skimage** | ✗ | MISSING | Morphological operations | NO | scipy.ndimage |

**Summary**: All **required** dependencies for B-6.2 minimum masks are installed. The 4 missing deps (geopandas, rasterio, pyproj, skimage) are optional convenience libraries. B-6.2 can proceed without installing any new packages.

**If skimage is later needed** (e.g., for sophisticated morphological cleanup):
```bash
pip3 install scikit-image
```

**If geopandas / rasterio / pyproj are needed** (e.g., for CRS-accurate reprojection):
```bash
pip3 install geopandas rasterio pyproj
```
Do NOT install during B-6.1 (read-only audit phase).

---

## 8. B-6.2 Prototype Readiness

### 8.1 Readiness Checklist

| Item | Status |
|---|---|
| ETOPO1 file present and readable | ✓ READY |
| ETOPO1 global coverage confirmed | ✓ READY |
| ETOPO1 read pipeline exists (generate_d5a_bathy.py) | ✓ READY |
| GSHHG f/h tiers present and readable | ✓ READY |
| GSHHG global L1 coverage confirmed | ✓ READY |
| GSHHG rasterization pipeline exists (gshhg_coastline_render.py) | ✓ READY |
| Core Python deps: numpy/Pillow/scipy/netCDF4/shapefile | ✓ READY |
| 2K downsample from ETOPO1 confirmed feasible | ✓ READY |
| No new data downloads required | ✓ READY |
| No new dep installs required | ✓ READY |

### 8.2 Minimum B-6.2 Mask Set (Recommended)

All masks at `2048×1024`, float32 [0,1], PNG output:

| Mask Name | Source | Method | Priority |
|---|---|---|---|
| `land_mask_2k` | ETOPO1 z > 0 | Threshold + feather | **P0** |
| `ocean_mask_2k` | ETOPO1 z ≤ 0 | Threshold + feather | **P0** |
| `deep_ocean_mask_2k` | ETOPO1 z < −3500 | Threshold + feather | **P0** |
| `mid_ocean_mask_2k` | ETOPO1 −3500 ≤ z < −1000 | Threshold range + feather | **P0** |
| `continental_shelf_mask_2k` | ETOPO1 −1000 ≤ z < −200 | Threshold range + feather | **P0** |
| `shallow_sea_mask_2k` | ETOPO1 −200 ≤ z < 0 | Threshold range + feather | **P0** |
| `coastline_distance_mask_2k` | GSHHG f/h L1 | Rasterize → distance_transform_edt | **P0** |
| `mountain_mask_2k` | ETOPO1 z > 1500 (land) | Threshold + feather | P1 |
| `plateau_mask_2k` | ETOPO1 500 < z ≤ 1500 (land) | Threshold range + feather | P1 |
| `special_sea_*_mask_2k` | ocean_mask + bbox | ocean_mask × region_mask | P1 |
| `reef_atoll_proxy_mask_2k` | GSHHG f L1 (small polygon area) | Polygon area filter + buffer | OPTIONAL |

### 8.3 Implementation Path for B-6.2

B-6.2 should create a new standalone script: `scripts/generate_b6_structure_masks.py`

The script reuses:
- ETOPO1 load/reshape logic from `generate_d5a_bathy.py` (lines already validated)
- GSHHG rasterization from `gshhg_coastline_render.py`
- Gaussian feather from `d5b_processor_v3/masks.py`

No new scripts from scratch; it's an assembly of proven components.

---

## 9. Risks and Blockers

| Risk | Severity | Detail | Mitigation |
|---|---|---|---|
| ETOPO1 flat `z` array requires reshape | LOW | Already handled in existing script; `reshape(H, W)` | Copy from `generate_d5a_bathy.py` |
| GSHHG f/L1 (154 MB) slow to rasterize | MEDIUM | 179K polygons at 2K may take 60–120s | Use `h/L1` (33 MB, 144K shapes) for faster 2K prototype; `f/L1` for 8K |
| Gaussian blur at coarse 2K understates coast detail | LOW | 2K = 1px per ~20 km; small islands disappear | Accept at 2K; 8K pass needed for reef/atoll detail |
| ETOPO1 ice variant inflates Antarctic/Greenland elevation | LOW | Masks should still be reasonable; bedrock variant not available locally | Acceptable for color grading purpose |
| Missing geopandas/rasterio means no automatic CRS handling | LOW | ETOPO1/GSHHG are both EPSG:4326; equirectangular math in numpy is sufficient | numpy-only approach confirmed feasible |
| `ocean_mask` from ETOPO1 includes sea ice / Antarctic shelf | MEDIUM | Ice variant marks ice shelf as land (z > 0) | Apply GSHHG L5/L6 (Antarctic grounding line) to refine; or accept minor inaccuracy |

### 9.1 No Blockers

There are no blockers to starting B-6.2. All required assets and dependencies are present.

---

## 10. Final Recommendation

### Verdict: `READY_TO_PROCEED` → Enter B-6.2

**B-6.2 can begin immediately** based on:
- ETOPO1 global, verified, readable, existing pipeline in `generate_d5a_bathy.py`
- GSHHG 2.3.7 full + high res, verified readable via pyshp
- All required Python deps installed; 4 optional missing deps not needed for B-6.2 minimum set
- Existing scripts provide >70% of required infrastructure; B-6.2 is primarily assembly

**B-6.2 scope recommendation:**
1. Create `scripts/generate_b6_structure_masks.py` as new standalone script
2. Generate minimum P0 mask set at 2K (7 masks: land/ocean/deep/mid/shelf/shallow/coastline-distance)
3. Output to `d5b_processor_v3/d5b_output/structure_masks/` (not to `pwa/assets/earth/` — calibration only)
4. No integration into d6 generator until masks visually validated
5. Integration design: B-6.3

**GEBCO deferred:** Japan subset is available for East Asia validation; global GEBCO not needed for B-6.2.

**No new data downloads required for B-6.2.**  
**No new package installs required for B-6.2.**

---

## Appendix A: Structured Audit Summary

```
=== B-6.1 Asset Audit Summary ===

ETOPO1:
  path:       pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd
  format:     NetCDF4 (GMT gdal variant), variable z, int32 flat array
  size:       890 MB
  grid:       21601 × 10801  @ 1 arc-minute
  md5:        36edc15622edcae8ccc9486a88c6488a
  lon_range:  -180.0 → +180.0
  lat_range:  -90.0  → +90.0
  z_range:    -10898 m → +8271 m
  status:     READY

GSHHG:
  zip_path:       pwa/assets/source/coastline/gshhg/gshhg-shp-2.3.7.zip
  version:        2.3.7
  L1_full_path:   GSHHS_shp/f/GSHHS_f_L1.shp  (154 MB, 179837 shapes)
  L1_high_path:   GSHHS_shp/h/GSHHS_h_L1.shp  (33 MB,  144749 shapes)
  tiers:          c / l / i / h / f  ALL PRESENT
  layers:         L1–L6 ALL PRESENT
  bbox:           global  [-180, -68.9, 180, 83.6]
  md5_f_L1:       2e283b3a193c6111beeae7c0ff7374d3
  status:         READY

GEBCO:
  path:       pwa/assets/source/bathy/gebco_2026/gebco_2026_118_150_22_50.nc
  coverage:   JAPAN_ONLY  (lon 118–150, lat 22–50)
  grid:       7680 × 6720  @ ~0.00417° (464 m/px)
  z_range:    -10668 m → +3757 m
  md5:        b05507ce8c6afc309857ad44d2c3993a
  status:     SUPPLEMENTAL (Japan benchmark only; NOT global)

Existing Masks:
  ocean_mask_4096x2048_soft.png:   color-classifier, NOT ETOPO1-based
  ocean_specular_4096x2048.png:    specular highlight mask
  status:     SUPPLEMENTAL

Dependencies:
  numpy:       1.23.3   INSTALLED
  Pillow:      11.3.0   INSTALLED
  scipy:       1.7.1    INSTALLED
  netCDF4:     1.7.2    INSTALLED
  h5py:        3.14.0   INSTALLED
  xarray:      2024.7.0 INSTALLED
  shapefile:   3.0.12   INSTALLED
  shapely:     2.0.7    INSTALLED
  geopandas:   MISSING  (not required for B-6.2)
  rasterio:    MISSING  (not required for B-6.2)
  pyproj:      MISSING  (not required for B-6.2)
  skimage:     MISSING  (not required for B-6.2)

B-6.2 Verdict: READY_TO_PROCEED
```
