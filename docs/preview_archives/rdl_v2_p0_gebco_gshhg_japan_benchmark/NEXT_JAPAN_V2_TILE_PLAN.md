# Japan v2 Visual Tile — Composite Plan

**Date:** 2026-06-08  
**Goal:** Produce a Japan regional detail tile (2048 or 4096px) using d5b_v3.2.1 base + GEBCO 2026 tint + GSHHG L1 coastline edge, for potential use in Three.js earth globe.

**Hard constraints:** No Copernicus DEM; no OSM; no city lights; no earth3d.js changes; no replacement of formal pwa/assets/earth/ resources; no commit.

---

## Output Specification

| Parameter | Value |
|---|---|
| Region | lon 118–150°E, lat 22–50°N (Japan benchmark region) |
| Output name | `japan_v2_detail_tile_4096x3584.png` |
| Output resolution | 4096 × 3584 px (128 px/degree; 4096 for 32°lon × 3584 for 28°lat) |
| Aspect ratio | 32/28 = 1.143 |
| UV bounds (Three.js r128) | uMin=0.8278, uMax=0.9167, vMin=0.6222, vMax=0.7778 |
| Format | PNG (lossless; JPEG optional at q=95 for size) |

**Why 4096×3584?** GSHHG output is already at this resolution. GEBCO at native 6720×7680 slightly exceeds it (7680/4096=1.875× downscale, information preserved). d5b 8K crop will be upscaled ~5.6× — acceptable because GEBCO and GSHHG provide the high-frequency detail that d5b lacks at this scale.

**2048 variant:** `japan_v2_detail_tile_2048x1792.png` — half resolution, for mobile/fallback.

---

## Layer Stack

| Layer | Source | Operation | Notes |
|---|---|---|---|
| L1: Base color | d5b_design_v3_2_1_8192x4096.jpg | Crop Japan → resize to 4096×3584 | Provides land+ocean style/color from v3.2.1 |
| L2: GEBCO tint | gebco_bathymetry_tint.png (6720×7680) | Resize 7680×6720 → 4096×3584; apply to ocean pixels only | 5-level depth palette replaces d5b ocean |
| L3: GSHHG mask | gshhg_coastline_mask.png (4096×3584) | Use as alpha: ocean=1, land=0 | Controls where GEBCO tint is applied |
| L4: Coastline edge | gshhg_coastline_mask.png edge channel | Overlay as white/cyan glow (additive) | Sharpens coast; replaces blurry d5b coastline |

**Blend logic per pixel:**
```
ocean_mask = (gshhg_mask == sea)
output[ocean_mask] = blend(base[ocean_mask], gebco_tint[ocean_mask], alpha=0.85)
output[land] = base[land]
output[coast_edge] = additive_mix(output[coast_edge], (180,220,255), strength=0.4)
```

---

## Input Files

| File | Path | Size | Notes |
|---|---|---|---|
| d5b base | `pwa/assets/earth/candidates/d5b_design_v3_2_1_8192x4096.jpg` | ~8MB | Formal 8K candidate; read-only |
| GEBCO tint | `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/gebco_bathymetry_tint.png` | 892KB | Pre-generated, 6720×7680 |
| GSHHG mask | `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/gshhg_coastline_mask.png` | 161KB | Pre-generated, 4096×3584, white=land |

---

## Crop Computation

**d5b base (8192×4096, equirectangular, north=top):**

```
col_w = round((118 + 180) / 360 * 8192) = 6784
col_e = round((150 + 180) / 360 * 8192) = 7509
row_n = round((1 - (90 + 50) / 180) * 4096) = round(0.2222 * 4096) = 910
row_s = round((1 - (90 + 22) / 180) * 4096) = round(0.3778 * 4096) = 1547

Crop box: (col_w=6784, row_n=910, col_e=7509, row_s=1547)
Crop size: 725 × 637 px (from 8192×4096 source)
Resize to: 4096 × 3584 (upscale ×5.65 — JPEG artifacts present; GEBCO/GSHHG supply detail)
```

**GEBCO tint (6720×7680, covers 118–150°E / 22–50°N exactly):**
- Resize 7680×6720 → 4096×3584 (bicubic or lanczos downscale, no information loss)
- Note: GEBCO array orientation is lat S→N (row 0 = lat 22°N), so no flip needed before PIL use after the `flipud` in load_gebco_nc()

**GSHHG mask (4096×3584, already at target resolution):**
- Direct use; white=land (pixel ≥ 128), black=sea (pixel < 128)

---

## Proposed Script

**File:** `scripts/geo/japan_v2_tile_composite.py`

```bash
python3 scripts/geo/japan_v2_tile_composite.py \
  --bounds 118 150 22 50 \
  --base pwa/assets/earth/candidates/d5b_design_v3_2_1_8192x4096.jpg \
  --tint previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/gebco_bathymetry_tint.png \
  --mask previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/gshhg_coastline_mask.png \
  --out previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/ \
  --res 4096
```

**Key steps in script:**

```python
# 1. Load and crop d5b base
base = Image.open(args.base)  # 8192×4096 JPEG
crop = base.crop((col_w, row_n, col_e, row_s))  # 725×637
base_resized = crop.resize((4096, 3584), Image.LANCZOS)

# 2. Load GEBCO tint (already 6720×7680, north=top after flipud in tint script)
tint = Image.open(args.tint)  # 7680×6720 (W×H in PIL)
tint_resized = tint.resize((4096, 3584), Image.LANCZOS)

# 3. Load GSHHG mask
mask = Image.open(args.mask).convert('L')  # 4096×3584

# 4. Build ocean alpha (sea pixels)
mask_arr = np.array(mask)
ocean = mask_arr < 128  # True = sea

# 5. Blend GEBCO tint onto ocean pixels
base_arr = np.array(base_resized, dtype=np.float32)
tint_arr = np.array(tint_resized, dtype=np.float32)
TINT_ALPHA = 0.85
result = base_arr.copy()
result[ocean] = base_arr[ocean] * (1 - TINT_ALPHA) + tint_arr[ocean] * TINT_ALPHA

# 6. Coastline edge glow (morphological edge = pixels where mask transitions)
from scipy.ndimage import binary_dilation
edge = binary_dilation(ocean, iterations=2) & ~ocean  # 2-px coast fringe
COAST_COLOR = np.array([180, 220, 255], dtype=np.float32)
COAST_STRENGTH = 0.4
result[edge] = np.clip(result[edge] * (1 - COAST_STRENGTH) + COAST_COLOR * COAST_STRENGTH, 0, 255)

# 7. Save
Image.fromarray(result.astype(np.uint8)).save(out_path_4096, compress_level=6)
```

---

## Output Files

| File | Size (est.) | Location |
|---|---|---|
| `japan_v2_detail_tile_4096x3584.png` | ~6–9MB | `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/` |
| `japan_v2_detail_tile_2048x1792.png` | ~2–3MB | same dir (optional half-res) |

---

## Three.js Integration Notes

**This tile is NOT for direct globe replacement.** It is a reference composite for visual validation and future GLSL shader integration.

For use in globe:
- UV bounds: `uMin=0.8278, uMax=0.9167, vMin=0.6222, vMax=0.7778`
- Must be blended via GLSL shader `mix()` in the Japan UV region only
- `earth3d.js` must NOT be modified during this P0/audit phase

Future integration path (separate task, separate PR):
1. Write GLSL snippet that masks to Japan UV bounds
2. Load tile as `THREE.Texture`
3. Mix with base day texture in fragment shader using smoothstep feathering at borders
4. Validate on globe before any formal texture replacement

---

## What This Plan Does NOT Include

| Excluded | Why |
|---|---|
| Copernicus DEM GLO-30 | Out of P0 scope; deferred |
| OSM roads / buildings | Layer 6 (Vector overlay) — separate phase |
| City lights (VIIRS) | Layer 6 — separate phase |
| Hillshading | No DEM yet; would add after Copernicus download |
| Actual globe deployment | No earth3d.js changes; no pwa/assets/earth/ writes |
| Commit | Per standing constraint |

---

## Prerequisites Checklist

- [x] `gebco_2026_118_150_22_50.nc` downloaded and verified
- [x] `gebco_bathymetry_tint.png` generated (6720×7680)
- [x] `gshhg_coastline_mask.png` generated (4096×3584)
- [x] `d5b_design_v3_2_1_8192x4096.jpg` available at `pwa/assets/earth/candidates/`
- [ ] `japan_v2_tile_composite.py` written and tested
- [ ] 4096×3584 tile generated and reviewed
- [ ] UV crop math verified against `lon_lat_to_uv.js` output
