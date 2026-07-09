# B-6.2X-C1-X2 — GEBCO Canonical DEM Interface Layer

Stage: B-6.2X-C1-X2  
Type: Canonical DEM abstraction layer  
Status: **PASS**  
Date: 2026-06-24  
Tools: Python 3 + tifffile + numpy  

---

## 1. Scope

This task creates a unified Python DEM abstraction layer for existing GEBCO, ETOPO1, and Copernicus DEM sources.

Boundary followed:

- No raster resampling.
- No masks generated.
- No generator / d6 execution.
- No downloads.
- No existing processed_8k file modifications.
- No source_cache moves/deletes.
- No full GEBCO merge or 8K DEM generation.
- No commit or push.

---

## 2. Adapter Architecture

Created module:

```text
core/dem/
    __init__.py
    dem_interface.py
    gebco_adapter.py
    etopo_adapter.py
    copernicus_adapter.py
```

Core classes:

| Class | Role |
|---|---|
| `DEMInterface` | Shared interface: `get_value`, `get_window`, `get_stats`, `get_crs`, `validate_alignment` |
| `GeoTiffDEMAdapter` | Shared north-up EPSG:4326 GeoTIFF coordinate mapping and lazy array loading |
| `GEBCOAdapter` | Native GEBCO tile directory access; no global merge |
| `ETOPO1Adapter` | Global fallback truth |
| `CopernicusDEMAdapter` | Land refinement layer |
| `DEMRegistry` | Priority glue layer |

`DEMRegistry.from_source_cache(root)` builds the canonical RodiO registry from the existing local source cache.

---

## 3. DEM Priority Logic

Canonical rule:

```text
GEBCO is NOT primary DEM
ETOPO1 is global fallback truth
Copernicus is land refinement
```

Registry query priority:

1. Try Copernicus first when it returns a valid land-like value.
2. Try GEBCO when it returns a valid negative bathymetry value.
3. Fall back to ETOPO1.

No land/ocean mask is created. Routing is based only on native-source validity and value sign:

- Copernicus `nodata=-32768` means no land-refinement value.
- GEBCO negative values are treated as ocean bathymetry.
- ETOPO1 remains the always-available fallback.

---

## 4. GEBCO Tile Mapping Strategy

Source path:

```text
d5b_processor_v3/source_cache/gee_global/external_raw/gebco/gebco_2026_sub_ice_topo_geotiff/
```

Detected source type:

```text
tiles
```

Tile mapping:

- Tile bounds are parsed from filenames such as `gebco_2026_sub_ice_n90.0_s0.0_w-180.0_e-90.0_geotiff.tif`.
- `lon` is normalized into `[-180, 180)`.
- `lat` is clamped into the addressable raster range.
- The adapter chooses the single tile whose native bounds contain the coordinate.
- Pixel row/column is computed from that tile's native GeoTIFF tiepoint and pixel scale.
- The tile array is opened lazily via `tifffile.memmap()` when possible.

GEBCO `get_window(bbox)` returns native windows per intersecting tile. It does not stitch windows into a merged global raster.

---

## 5. Fallback Logic

Example registry construction:

```python
from core.dem import DEMRegistry

registry = DEMRegistry.from_source_cache(
    "d5b_processor_v3/source_cache/gee_global"
)
value = registry.query(lon, lat)
```

Sample query behavior:

| Coordinate | GEBCO | ETOPO1 | Copernicus | Registry result |
|---|---:|---:|---:|---:|
| -150, 30 | -6320 | -6068 | nodata | -6320 |
| 86.925, 27.988 | 8627 | 7295 | 7021 | 7021 |
| 0, 0 | -4936 | -4934 | nodata | -4936 |

---

## 6. Validation Results

### 6.1 Tile Coverage Check

| Check | Result |
|---|---|
| GEBCO source type | `tiles` |
| Tile count | 8 |
| Missing tiles | none |
| Extra tiles | none |
| Coverage | `(-180.0, -90.0, 180.0, 90.0)` |
| CRS | EPSG:4326 for all tiles |
| Tile shape | 21600 x 21600 for all tiles |
| dtype | int16 for all tiles |
| nodata | -32767 |
| Result | PASS |

### 6.2 Consistency Check

No raster deviation file was generated. The deviation check was performed as an in-memory 5 degree global sample grid.

| Comparison | Samples | Mean abs deviation | Median abs deviation | P95 abs deviation | Max abs deviation |
|---|---:|---:|---:|---:|---:|
| GEBCO vs ETOPO1 | 2,592 | 93.41 m | 38.00 m | 371.45 m | 1,627.00 m |
| Copernicus vs ETOPO1 land-valid sample | 1,057 | 703.92 m | 50.00 m | 3,055.80 m | 5,281.00 m |

Interpretation:

- GEBCO and ETOPO1 are broadly consistent as global bathymetry/topography sources; higher deviations are expected from resolution/source differences.
- Copernicus vs ETOPO1 has a low median but high tail because Copernicus resolves steep land relief and polar/high-mountain terrain differently from ETOPO1.
- No critical DEM inconsistency was found.

### 6.3 Alignment Check

| Adapter | Alignment result | Notes |
|---|---|---|
| ETOPO1 | PASS | 8192 x 4096, EPSG:4326, origin (-180, 90), pixel scale 0.0439453125 deg |
| Copernicus DEM | PASS | 8192 x 4096, EPSG:4326, origin (-180, 90), pixel scale 0.0439453125 deg, nodata -32768 |
| GEBCO | PASS | Native 15 arc-second 8-tile grid, EPSG:4326, complete global coverage, tile origins match tile bounds |

No origin/coverage drift was detected. GEBCO is intentionally a native 15 arc-second tile grid, not an 8K grid; this interface preserves native resolution and does not attempt pixel-grid resampling.

---

## 7. Risks / Limitations

- `get_window()` for GEBCO returns one window per intersecting native tile; consumers must handle multi-tile windows explicitly.
- ETOPO1 and Copernicus 8K GeoTIFFs are LZW-compressed; native window reads may require tifffile decompression internally. Loading remains lazy at adapter initialization time.
- Registry land/ocean routing uses source validity and value sign only. It does not create or depend on a land/ocean mask.
- GEBCO ZIP and NetCDF support is detection-level only in this layer. Tile directory mode is the validated implementation path.
- Copernicus is used as land refinement, not as global truth; ocean nodata must fall back to GEBCO/ETOPO1.

---

## 8. Verdict

```text
pass
```

The canonical DEM interface layer is created and validated. GEBCO tile source detection works, all 8 tiles cover the globe with consistent CRS and metadata, the DEM registry is established, and no critical DEM inconsistency or alignment drift was found under this no-resampling/no-merge interface scope.

---

*Audit executed: 2026-06-24*  
*No 8K DEM generated. No GEBCO tiles merged. No masks generated. No generator/d6 run.*
