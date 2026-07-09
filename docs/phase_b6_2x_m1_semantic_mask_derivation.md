# M1 — Semantic Mask Derivation
**Phase B6-2x | Status: Implemented & Tested**
*Generated: 2026-06-24*

---

## 1. Overview

M1 is the tile-based semantic mask generation system. It consumes the outputs of SAL (semantic truth decisions) and the D6 Binding Layer (visual representation) and produces structured numpy mask arrays for each geographic tile.

```
SAL ArbitrationResult
D6RenderInput
        ↓
  M1 Pipeline (core/m1/)
        ↓
  SemanticMaskTile:
    ocean_mask       bool[H, W]
    land_mask        bool[H, W]
    biome_mask       uint8[H, W]
    uncertainty_mask float32[H, W]
    confidence_mask  float32[H, W]
    ocean_prob_mask  float32[H, W]
```

M1 produces **numpy arrays only** — no RGB images, no raster files, no GPU ops.

---

## 2. Module Structure

```
core/m1/
    mask_types.py              — TileBBox, SemanticMaskTile, biome codes, types
    tile_segmenter.py          — grid decomposition and mask stitching
    semantic_field_builder.py  — SAL + D6 → per-point scalar fields
    real_signal_provider.py    — M0 SpatialRuntime → SAL signal kwargs
    mask_generator.py          — iterates tile grid, calls full pipeline per point
    m1_pipeline.py             — run_tile() / run_global() orchestration layer
    __init__.py
    _test_m1.py
    _test_real_signal_provider.py
```

---

## 3. Mask Architecture

### 3.1 Per-Point Computation

For each (lon, lat) grid point within a tile, M1 runs:

```
SignalProvider(lon, lat)
        ↓ SAL signal dict
SemanticArbitrator.resolve()
        ↓ ArbitrationResult { final_class, confidence_score, entropy,
                               probability_map, conflict_detected }
SALD6Bridge.convert()
        ↓ D6RenderInput { uncertainty, base_color, ... }
SemanticFieldBuilder.build()
        ↓ { ocean_field, climate_field, uncertainty_field, biome_code, confidence }
SemanticFieldBuilder.fields_to_point_masks()
        ↓
  ocean_mask[row, col]       = final_class == "ocean"
  land_mask[row, col]        = final_class in land-family
  biome_mask[row, col]       = BIOME_* integer code
  uncertainty_mask[row, col] = D6RenderInput.uncertainty  # winner-margin based
  confidence_mask[row, col]  = SAL confidence_score
  ocean_prob_mask[row, col]  = probability_map["ocean"]
```

### 3.2 Signal Provider Pattern

`MaskGenerator` is decoupled from data sources via a `SignalProvider` callable:

```python
SignalProvider = Callable[[float, float], Dict]   # (lon, lat) → SAL signal kwargs
```

This allows the same pipeline to be driven by:
- Test synthetic functions
- `RealSignalProvider`, backed by M0 `SpatialRuntime`
- Cached pre-processed signal grids (future)

### 3.3 RealSignalProvider

`RealSignalProvider` translates live `SpatialRuntime.query_point(lon, lat)` output into SAL's four signal slots:

| SAL input | Runtime source |
|---|---|
| `dem_signal` | elevation sign (`<0 → ocean`, otherwise land) |
| `climate_signal` | Köppen class present → land anchor |
| `ocean_signal` | runtime ocean truth after Köppen veto |
| `landcover_signal` | ocean / desert / forest / ice / land proxy from climate + elevation |

`M1Pipeline(runtime=runtime)` now auto-installs `RealSignalProvider` when no explicit `signal_provider` is passed. This keeps synthetic tests possible while allowing the same M1 entry point to run against real DEM + Köppen + GEBCO runtime data.

---

## 4. Tile Segmentation Strategy

### 4.1 Global Grid

Default: 8192 × 4096 pixels covering −180→180 lon, −90→90 lat.

```
Tile size:   1024 × 1024 px
Grid layout: 8 cols × 4 rows = 32 tiles
Tile order:  row-major, top-left origin (lat 90 → −90, lon −180 → 180)
```

### 4.2 TileBBox

Each tile carries its geographic bounds and grid position:

```python
@dataclass
class TileBBox:
    lon_min, lon_max: float   # degrees
    lat_min, lat_max: float
    col_idx, row_idx: int     # grid position
```

### 4.3 Coordinate Sampling

Within a tile, points are sampled on a regular grid:

```python
lons = linspace(bbox.lon_min, bbox.lon_max, tile_px_w)
lats = linspace(bbox.lat_max, bbox.lat_min, tile_px_h)   # top-down
```

At 1024 px resolution this gives ~0.044° per sample (~4.9 km at equator).

### 4.4 Stitching

`TileSegmenter.stitch_tiles()` recombines tiles into a single global array:

```python
global_array = segmenter.stitch_tiles(tiles, field="biome_mask")
# Returns np.ndarray (global_h, global_w) — no image, no RGB
```

Gaps are filled with `BIOME_UNKNOWN` (uint8) or `NaN` (float fields).

---

## 5. SAL → Mask Mapping

### 5.1 Binary Masks

| Mask | Derivation |
|---|---|
| `ocean_mask` | `final_class == "ocean"` |
| `land_mask` | `final_class in {"land", "desert", "forest", "wetland", "urban", "ice"}` |

Binary masks are derived from SAL's categorical decision. For smooth boundaries, downstream consumers should use `ocean_prob_mask` (raw probability) as a soft-boundary signal.

### 5.2 Biome Codes (uint8)

| Code | Class | Code | Class |
|---|---|---|---|
| 0 | ocean | 4 | forest |
| 1 | shallow_water | 5 | wetland |
| 2 | land (generic) | 6 | ice |
| 3 | desert | 7 | urban |
| 255 | unknown | — | — |

Biome code is taken from `SAL.final_class`. When the D6 Binding Layer has applied a climate-zone override (e.g., land → desert), that override is visible in the D6 visual output but the biome code in M1 still reflects the SAL canonical class (no side-effects on truth layer).

### 5.3 Probabilistic Ocean Mask

`ocean_prob_mask` stores `probability_map["ocean"]` from SAL before thresholding. Range from test cases:

- Pure ocean: ~0.169
- Conflicted (Dead Sea / Caspian): ~0.136
- Coastal mixed: 0.103 – 0.169 (gradient spans 0.066)

This continuous field is the primary signal for D6 transition-gradient rendering at boundaries.

---

## 6. Uncertainty Encoding

```
winner_margin = p(top_1_class) − p(top_2_class)
uncertainty   = clamp(1 − winner_margin / 0.08)
```

M1 takes this value from `D6RenderInput.uncertainty`, so Binding remains the single translation layer for uncertainty semantics.

| Scenario | Winner margin | Uncertainty |
|---|---|---|
| Dead Sea | 0.012 | 0.8465 |
| Pacific Ocean | 0.065 | 0.1814 |
| Coastal (mixed) | variable | 0.4293 avg |

Entropy remains available in SAL as a diagnostic, but it is no longer the primary uncertainty driver. The margin-derived field separates clean ocean from ambiguous land/ocean races despite low absolute softmax confidence.

### Spatial Uncertainty Variation

The coastal tile shows meaningful spatial variation:
- `std(uncertainty_mask) = 0.235224` — spatial structure is present
- `ocean_prob range = [0.103, 0.169]` — 0.066 span, usable gradient

---

## 7. Integration with D6 Binding Layer

M1 consumes D6RenderInput indirectly via `SemanticFieldBuilder`, which takes both `sal_state` and `d6_input` as inputs. Currently, M1 uses the D6 input to anchor the pipeline (ensuring SAL and D6 agree on the same point state) but does not propagate visual fields (base_color, adjusted_color) into the mask arrays.

Future integration path:
- Add `color_hint_r/g/b` float32 fields to `SemanticMaskTile` from D6 adjusted_color
- Add `light_factor` and `seasonal_modifier` pass-through for per-tile light map
- These fields become the D6 per-tile uniform upload payload

---

## 8. Test Case Results

### Test 1: Dead Sea Tile (8×8 = 64 points)

| Metric | Value |
|---|---|
| ocean_fraction | 0.000 ✓ |
| land_fraction | 1.000 ✓ |
| biome_codes | `[2]` (land) |
| mean_confidence | 0.1486 |
| mean_uncertainty | 0.8465 |

All 64 points uniformly classified as `land`. De-correlation correctly resolved negative-elevation endorheic basin.

### Test 2: Open Ocean Tile (8×8 = 64 points)

| Metric | Value |
|---|---|
| ocean_fraction | 1.000 ✓ |
| land_fraction | 0.000 ✓ |
| biome_codes | `[0]` (ocean) |
| mean_confidence | 0.1693 |
| mean_uncertainty | 0.1814 |

Stable deep ocean. Highest confidence of the three scenarios (all signals agree, no de-correlation needed).

### Test 3: Coastal Transition Tile (16×16 = 256 points)

| Metric | Value |
|---|---|
| ocean_fraction | 0.500 |
| land_fraction | 0.500 |
| biome_codes | `[0, 2]` (ocean + land) |
| mean_confidence | 0.1592 |
| mean_uncertainty | 0.4293 |
| std(uncertainty) | 0.235224 ✓ spatial gradient present |
| ocean_prob span | 0.0660 ✓ (0.103 → 0.169) |

Correct mixed classification with spatial gradient structure. `conflict_zone=True` flags trigger D6 gradient blend path.

### Test 4: Global Grid Dry-Run

32 tiles enumerated (8 cols × 4 rows), coverage consistent with 8192×4096 / 1024 grid.

**Overall: 4/4 PASS**

---

## 9. Limitations

### 9.1 Real Provider Calibration

`RealSignalProvider` is wired and smoke-tested against the local source cache, but confidence calibration remains heuristic. DEM confidence is distance-from-sea-level based; climate and landcover confidences are fixed anchors. These values should be recalibrated once broader real-tile validation exists.

### 9.2 Per-Point SAL Calls

Each tile point runs an independent SAL resolution. At 8K resolution with 1024×1024 tiles (1M points per tile, 32 tiles = 33M points total), this is not feasible in pure Python. Vectorisation of the SAL pipeline using numpy broadcasting is the required next step before any production run.

### 9.3 Biome Code Reflects SAL Class Only

Climate-zone biome refinement (land → desert, land → forest) is applied in the D6 Binding Layer's visual mapper but not yet written back to `biome_mask`. Adding a `d6_biome_mask` field would expose the refined biome for downstream use without changing the SAL-authoritative `biome_mask`.

### 9.4 Entropy Still Diffuse

SAL entropy values remain close to the 9-class maximum and should be treated as diagnostic. M1's `uncertainty_mask` now uses Binding's winner-margin uncertainty, while `confidence_mask` and `ocean_prob_mask` remain useful companion fields for debugging and boundary gradients.

---

## 10. Future Rasterization Path

When M1 moves toward production-scale output:

```
M1Pipeline.run_global()
        ↓
  32 × SemanticMaskTile (numpy arrays)
        ↓
  TileSegmenter.stitch_tiles(tiles, field="biome_mask")
        ↓
  global_biome: uint8[4096, 8192]    ← in-memory only, or write to:
  → GeoTIFF (GDAL, single band, uint8)     — future optional
  → PNG (palette, no RGB blending)         — future optional
  → Zarr / HDF5 chunk store                — future preferred
```

M1's numpy output is already format-neutral. The rasterization step is a one-call write (e.g., `rasterio.open(..., 'w').write(biome_array)`) that does not require changes to the pipeline.

---

## 11. API Reference

```python
from core.m1 import M1Pipeline, TileBBox
from core.binding import TemporalState
from core.runtime import SpatialRuntime

def my_signals(lon, lat):
    return dict(dem_signal="land", dem_confidence=0.8, ...)

pipeline = M1Pipeline(
    signal_provider=my_signals,
    temporal=TemporalState(month=7, hour=12, lat=31.5, climate_zone="arid"),
    tile_px_size=32,
)

# Single tile
bbox = TileBBox(lon_min=34.5, lon_max=36.5, lat_min=30.5, lat_max=32.5)
tile = pipeline.run_tile(bbox)

print(tile.ocean_fraction())       # 0.0
print(tile.land_fraction())        # 1.0
print(tile.biome_mask)             # uint8 array
print(tile.uncertainty_mask.mean()) # e.g. 0.181 for clear ocean, 0.846 for Dead Sea

# Global dry-run (tile enumeration only)
summary = pipeline.run_global(dry_run=True)
print(summary.total_tiles)         # 32

# Real runtime provider
runtime = SpatialRuntime.from_source_cache("d5b_processor_v3/source_cache/gee_global")
real_pipeline = M1Pipeline(runtime=runtime, tile_px_size=2)
pacific = real_pipeline.run_tile(TileBBox(lon_min=-141, lon_max=-140, lat_min=9, lat_max=10))
deadsea = real_pipeline.run_tile(TileBBox(lon_min=35.2, lon_max=35.8, lat_min=31.2, lat_max=31.8))

print(pacific.ocean_fraction())    # 1.0
print(deadsea.land_fraction())     # 1.0
```
