# Phase B-6.2G-1A — Inland Water Asset Feasibility Audit

**Phase:** B-6.2G-1A (revised: B-6.2G-1A-R)
**Date:** 2026-06-10
**Status:** READ-ONLY AUDIT — no code changes, no mask generation
**Scope:** Confirm GSHHG L2 / L3 sufficiency for inland water / lake masks; WDBII river check
**Next phase:** B-6.2G-1B (implementation, separate authorization required)

---

## 1. GSHHG L2 — Lake Polygon Audit

### 1.1 File Presence (All 5 Tiers)

| Tier | Path | Shape count | File size |
|------|------|:-----------:|----------:|
| c (crude) | `GSHHS_shp/c/GSHHS_c_L2.shp` | 994 | ~52 KB |
| l (low) | `GSHHS_shp/l/GSHHS_l_L2.shp` | 4,367 | ~348 KB |
| i (intermediate) | `GSHHS_shp/i/GSHHS_i_L2.shp` | 6,559 | ~1.5 MB |
| h (high) | `GSHHS_shp/h/GSHHS_h_L2.shp` | 6,601 | ~4.1 MB |
| f (full) | `GSHHS_shp/f/GSHHS_f_L2.shp` | 6,660 | ~13 MB |

All tiers present and readable. **Verdict: PRESENT.**

### 1.2 Fields

```
['id', 'level', 'source', 'parent_id', 'sibling_id', 'area']
```

- `id`: string (not int — use `str`, not `%d` format specifier)
- `level`: int, always 2 for L2
- `area`: float, km². **Negative values = river-lake widening zones** (not true lakes — see §1.4)
- `parent_id`, `sibling_id`: cross-reference to containing / sibling L1/L3 polygons
- `source`: CIA WDBII (0) or WVS (1)

### 1.3 Area Distribution (h tier, 6,601 shapes total)

| Area threshold | Polygon count | Notes |
|----------------|:-------------:|-------|
| ≥ 500,000 km² | 0 | Caspian (397K) is largest |
| ≥ 100,000 km² | 2 | Caspian + Great Lakes system |
| ≥ 50,000 km² | 4 | + Victoria, Aral Sea |
| ≥ 10,000 km² | 17 | Major world lakes |
| ≥ 5,000 km² | 31 | Regional large lakes |
| ≥ 1,000 km² | 156 | Minimum "large lake" class |
| ≥ 500 km² | 301 | Marginal at 2K (≤ 1–2 px) |
| ≥ 100 km² | 1,400 | Sub-threshold at 2K |
| ≥ 50 km² | 2,297 | Sub-pixel at 2K |
| ≥ 10 km² | 4,667 | Invisible at 2K |

Of the 6,601 total shapes: **6,545 have positive area** (true lakes); **56 have negative area** (river-lake widening zones, see §1.4).

**At 2048×1024 resolution**, 1 pixel ≈ 380–382 km² at the equator (area diminishes with cos(lat)). Minimum useful mask area ≈ 5 px ≈ 1,900 km². Only **~156 polygons** (area ≥ 1,000 km²) are reliably visible as distinct shapes. **B-6.2G-1B must filter to `area > 0` before rasterization.**

### 1.4 River-Lake Widening Zones (Negative Area)

GSHHG L2 contains **56 shapes with negative `area` values**. Per GSHHG 2.3.7 documentation: "Shapefile polygons of level = 2 and with a negative area are river-lakes" — these represent the fat, braided sections of major rivers, not discrete lake bodies.

Top river-lake widening zones identified:

| Rank | area (km²) | Bbox | Likely river |
|------|------------|------|--------------|
| 1 | −28,218 | [−73.0,−4.5,−52.7,−0.2] | Amazon lower basin |
| 2 | −12,740 | [112.4,59.2,135.9,71.4] | Lena / Siberia complex |
| 3 | −11,872 | [16.1,−3.1,24.6,2.4] | Congo River |
| 4 | −7,897 | [65.0,56.3,84.5,66.8] | Ob River (W. Siberia) |
| 5 | −7,469 | [−60.8,−33.3,−55.8,−27.2] | Paraná / Río de la Plata |
| 6 | −6,107 | [103.1,10.0,106.4,18.4] | Mekong River |
| 7 | −5,754 | [130.3,46.8,140.8,53.2] | Amur River |
| 8 | −5,615 | [84.0,62.4,92.0,69.8] | Yenisei lower basin |
| 9 | **−4,916** | **[114.3,28.8,119.6,32.3]** | **Yangtze / middle section** |
| 10 | −4,908 | [−67.5,6.2,−61.7,9.8] | Orinoco River |

**Critical finding:** Bbox [114.3,28.8,119.6,32.3] is the Yangtze river-lake zone covering the Dongting–Poyang region. This explains why Poyang Lake does not appear as a standalone positive-area lake in h/L2: it is subsumed into the WDBII river-lake polygon of the Yangtze. In f/L2, Poyang appears fragmented into 3 small shapes (188+130+36 km²) — all well below the 2K threshold. Qiandao Lake (581.7 km²) is nearby (bbox [118.6,29.4,119.2,29.8]) but lies just outside this river-lake zone and is present as a distinct positive-area polygon.

**Requirement:** B-6.2G-1B must filter to **`area > 0`** before rasterizing lake masks. River-lake zones may be included as a separate optional `river_lake_zone_mask` for delta texturing — do not merge with lake masks.

---

## 2. GSHHG L3 — Lake Island Polygon Audit

### 2.1 File Presence

| Tier | Shape count | File size |
|------|:-----------:|----------:|
| c | 24 | ~3 KB |
| l | 506 | ~63 KB |
| i | 1,408 | ~372 KB |
| h | 1,434 | ~400 KB |
| f | 1,437 | ~951 KB |

All tiers present. **Verdict: PRESENT.**

### 2.2 Fields

Identical to L2: `['id', 'level', 'source', 'parent_id', 'sibling_id', 'area']`.

The `parent_id` field in L3 holds the actual `id` value of the containing L2 lake polygon. This linkage is the correct basis for island hole-punching: build a dict `{l2_id → [l3_shapes]}` using the real `parent_id` values, then for each L2 polygon rasterize its corresponding L3 islands as fill=0 overlays. **Do not assume `parent_id = 0`.**

### 2.3 Coverage Ratio

h tier: 1,434 L3 islands for 6,601 L2 shapes. In practice, islands are concentrated in the largest lakes (Great Lakes, Baikal). Most small lakes have no L3 children.

### 2.4 Rasterization Strategy

The PIL rasterization approach used in `generate_b6_structure_masks.py` (exterior ring fill=255, hole ring fill=0) is directly applicable to L2+L3. Correct sequence:
1. Rasterize all L2 positive-area polygons as fill=255.
2. Build linkage: `l3_by_parent = {sr.record['parent_id']: [...]} for sr in L3`.
3. For each L2 polygon, look up `l3_by_parent[l2_id]` and rasterize matching L3 islands as fill=0.
4. Use h/L3 with h/L2 exclusively; do not mix tiers.

---

## 3. Key Region Coverage Spot Check

Resolution reference: 2048×1024, 1 px ≈ 0.1758° lon × 0.1758° lat. Pixel area at latitude φ ≈ 382 × cos(φ) km².

### Table A — Required 12-Region Checklist

| # | Region | Found in h/L2? | GSHHG area (km²) | Approx px at 2K | Bbox (lon_W, lat_S, lon_E, lat_N) | Judgment |
|---|--------|:--------------:|:----------------:|:---------------:|-----------------------------------|----------|
| 1 | Caspian Sea | ✓ | 397,052 | ~1,420 | 46.68, 36.58, 54.77, 47.11 | **PASS** — dominant feature |
| 2 | Great Lakes | ✓ | 208,200 | ~770 | −92.11, 41.62, −79.66, 49.02 | **PASS** — single polygon in h/L2; sub-lakes individually identifiable only in f/L2 |
| 3 | Lake Baikal | ✓ | 32,266 | ~139 | 103.71, 51.46, 109.97, 55.79 | **PASS** |
| 4 | Lake Victoria | ✓ | 69,057 | ~181 | 31.61, −3.01, 34.85, 0.49 | **PASS** |
| 5 | Lake Tanganyika | ✓ | 32,733 | ~86 | 29.04, −8.80, 31.20, −3.34 | **PASS** |
| 6 | Lake Titicaca | ✓ | 8,117 | ~22 | −70.04, −16.60, −68.58, −15.24 | **MARGINAL** — present, ~5×4 px blob; sigma=1 feather risk; watchlist |
| 7 | Aral Sea | ✓ (historical) | 67,543 | ~248 | 58.18, 43.39, 61.97, 46.87 | **CAUTION** — visually large at 2K but data is historical (~67K km²); current area ~2,500 km²; watchlist |
| 8 | Qinghai Lake | ✓ | 4,450 | ~15 | (h/L2, top-400 by area) | **MARGINAL** — ~3×5 px at 2K; borderline threshold; watchlist |
| 9 | Dongting Lake | ✓ (positive area, 778 km²) | 778 | ~2 | (h/L2 positive, Yangtze region) | **SUB-THRESHOLD** — ~2 px; vanishes in sigma=1 feather; watchlist |
| 10 | Poyang Lake | absent as standalone | 188+130+36 (f/L2 only) | <1 | fragmented in f/L2 only | **ABSENT** — subsumed into Yangtze river-lake zone in h/L2; not recoverable at 2K; watchlist |
| 11 | Taihu Lake | ✓ | 2,519 | ~8 | (116°E region, lat ~31°N) | **SUB-THRESHOLD** — ~3×3 px; feather will suppress; watchlist |
| 12 | Qiandao Lake | ✓ (single polygon) | 581.7 | ~2 | 118.63, 29.40, 119.20, 29.81 | **SUB-THRESHOLD** — ~2 px at 2K; not suitable as B-6.2G-1B core validation point; 8K / high-res watchlist |

**Summary (Table A, 12 regions):**

| Result | Count | Regions |
|--------|:-----:|---------|
| PASS | 5 | Caspian, Great Lakes, Baikal, Victoria, Tanganyika |
| CAUTION (data anachronism) | 1 | Aral Sea |
| MARGINAL (present, borderline threshold) | 2 | Titicaca, Qinghai |
| SUB-THRESHOLD (present but ≤ 10 px) | 3 | Taihu, Dongting, Qiandao |
| ABSENT (not recoverable at 2K) | 1 | Poyang |
| **Total** | **12** | |

Note: all 7 non-PASS regions from Table A (Aral Sea, Titicaca, Qinghai, Dongting, Poyang, Taihu, Qiandao) enter the validation watchlist (§3.3). Lake Chad is added from Table B, for a total of 8 watchlist regions.

### Table B — Additional Reference Regions (Watchlist / Context)

| Region | Found in h/L2? | GSHHG area (km²) | Approx px at 2K | Bbox | Judgment |
|--------|:--------------:|:----------------:|:---------------:|------|----------|
| Lake Malawi (Nyasa) | ✓ | 28,943 | ~81 | 33.89, −14.41, 35.29, −9.48 | PASS — clear reference lake |
| Lake Chad | ✓ (historical) | 11,977 | ~30 | 13.22, 12.45, 15.21, 13.99 | CAUTION — historical peak extent; current area ~1,500 km²; watchlist |
| Great Slave Lake | ✓ | 29,587 | ~153 | −117.68, 60.83, −108.90, 62.95 | PASS |
| Great Bear Lake | ✓ | 31,034 | ~155 | −125.12, 64.80, −117.46, 67.05 | PASS |
| Lake Balkhash | ✓ | 17,616 | ~58 | 73.42, 44.96, 79.25, 46.84 | PASS |
| Lake Ladoga | ✓ | 17,868 | ~63 | 29.80, 59.90, 32.96, 61.78 | PASS |

### 3.3 Validation Watchlist

The following 8 regions require explicit per-pixel validation at B-6.2G-1B implementation time: 7 non-PASS regions from Table A, plus Lake Chad from Table B.

| Region | Reason for watchlist |
|--------|---------------------|
| Aral Sea | Historical extent mismatch; must be flagged or excluded in metadata |
| Lake Chad | Historical extent mismatch; data_epoch: pre-1990 |
| Lake Titicaca | Marginal at 2K (~22 px); verify feather does not suppress |
| Qinghai Lake | Marginal at 2K (~15 px); verify feather does not suppress |
| Taihu Lake | Sub-threshold (~8 px); verify presence survives sigma=1 feather |
| Qiandao Lake | Sub-threshold (~2 px); not a 2K core validation point; defer to 8K |
| Dongting Lake | Sub-threshold (~2 px); expected absent in output; verify no false positive |
| Poyang Lake | Absent in h/L2; expected absent in output; verify no false positive |

---

## 4. Inland Water Mask Design Proposal

All masks generated from h/L2 positive-area shapes only. L3 used for island hole-punching via real `parent_id` linkage.

### 4.1 `lake_mask_from_GSHHG_L2` (Base)

- **Source:** h/L2, positive-area shapes only (`area > 0`), 6,545 polygons
- **Method:** PIL rasterize: exterior ring fill=255; islands from h/L3 via real `parent_id`→L2 `id` mapping (fill=0 overlay). Do not assume `parent_id = 0` — use actual L3 `parent_id` values to build `{l2_id: [l3_shapes]}` lookup before rasterization.
- **Resolution:** 2048×1024
- **Note:** Includes all positive-area lakes regardless of size. Sub-1000 km² shapes appear as 1–2 px noise. Recommend area-threshold pre-filter (`area ≥ 1,000 km²`) or post-process morphological opening at 3-px threshold.
- **Expected coverage ratio:** ~1.2–1.8% of total pixels

### 4.2 `large_lake_mask`

- **Source:** h/L2, positive-area, area ≥ 10,000 km² (17 polygons)
- **Method:** Same rasterization + feather σ=1
- **Expected coverage ratio:** ~0.5–0.7%
- **Use case:** High-confidence water selector; no seasonal ambiguity; cleanest signal for d6

### 4.3 `inland_water_mask` (Composite)

- **Source:** h/L2 positive-area, area ≥ 1,000 km² (156 polygons)
- **Method:** Rasterize + feather σ=1 + AND with `land_mask` to prevent ocean bleed
- **Expected coverage ratio:** ~0.9–1.1%
- **Includes:** Caspian, Great Lakes, African great lakes, Central Asian lakes, Finnish/Russian lake district
- **Excludes by construction:** Aral Sea (flagged — see §6 Risk R2; exclude via bbox gate 58–62°E, 43–47°N), Poyang, Dongting (sub-threshold or absent in h/L2)

### 4.4 `lake_island_mask` (Hole Geometry)

- **Source:** h/L3, area ≥ 100 km² (~60 polygons)
- **Method:** Rasterize as filled land using `parent_id`→L2 `id` linkage
- **Note:** Only meaningful when overlaid on `large_lake_mask`. Restricts to islands whose real `parent_id` matches a large-lake L2 `id`.

### 4.5 `inland_water_distance_mask`

- **Source:** Derived from `inland_water_mask`
- **Method:** `distance_transform_edt(1 - inland_water_hard)`, normalize 0-1 over 50 px range
- **Semantics:** 0 = inland water; 1 = ≥50 px from inland water
- **Use case:** Gradient falloff for freshwater proximity; vegetation density modulation in d6
- **Note:** Same EDT approach as `coastline_distance_mask` in current script

### 4.6 River-Lake Zone Mask (Optional, Deferred)

- **Source:** h/L2, negative-area shapes only (56 polygons)
- **Use case:** Yangtze / Amazon / Congo delta texture differentiation
- **Deferred to:** B-6.2G-2 or later; requires separate validation

---

## 5. River / Delta Boundary — WDBII Check

### 5.1 File Presence

Path: `pwa/assets/source/coastline/gshhg/WDBII_shp/`
Tiers: c, l, i, h, f — **all present**.
River levels per tier: **L01–L11** (11 levels each).

| Tier | L01 (major) | L01 file size |
|------|:-----------:|--------------|
| c | 55 shapes | 11 KB |
| l | 55 shapes | 38 KB |
| i | 55 shapes | 128 KB |
| h | 55 shapes | 361 KB |
| f | 55 shapes | 1,826 KB |

Fields: `['id', 'level']`. **No name field.** Shape type: **3 = Polyline** (not polygon).

### 5.2 Level Structure

| Level | Count (f tier) | Approximate significance |
|-------|:--------------:|--------------------------|
| L01 | 55 | Major world rivers (Amazon, Nile, Congo, Yangtze, Mississippi, Ob, Lena, Amur, Mekong, ...) |
| L02 | 2,381 | Large secondary rivers |
| L03 | 4,438 | Medium rivers |
| L04 | 7,553 | Small rivers |
| L05–L11 | 8,985–242 | Minor streams and tributaries |

### 5.3 Suitability as `major_river_proxy`

| Criterion | Assessment |
|-----------|------------|
| Readable via `pyshp` | ✓ Yes |
| Polygon (rasterizable directly) | ✗ No — Polyline (type 3); requires buffer/dilation |
| Name field | ✗ Absent — only `id` and `level` |
| L01 covers major world rivers | ✓ Yes — 55 shapes covers all globally significant rivers |
| Visual footprint at 2K without buffering | ~1–3 px wide corridor |
| Buffer approach feasibility | Feasible via `binary_dilation` or EDT; N=3 px corridor at 2K |
| Risk of land-ocean bleed | Low for L01; higher near river mouths |

### 5.4 Decision

WDBII rivers are **NOT** suitable for merging into lake masks. Polyline drainage networks are conceptually and geometrically distinct from polygon water bodies.

**Verdict: PRESENT and READABLE. Must remain deferred. Do not merge with B-6.2G-1B lake masks.**

If a `major_river_corridor_mask` is needed in a future phase (B-6.2G-2 or later): rasterize WDBII L01+L02 polylines → 1-px binary raster → `binary_dilation(radius=N)` → AND with `land_mask`.

---

## 6. Risk Audit

### R1 — Small lake noise at 2K

- **Risk:** Sub-threshold lakes (area < 1,000 km²) rasterize as isolated 1–2 px artifacts; sigma=1 feather will not cleanly suppress them.
- **Mitigation:** Pre-filter to area ≥ 1,000 km²; OR morphological opening at ~3-px threshold post-rasterization.
- **Severity:** LOW — cosmetic only

### R2 — Aral Sea historical extent mismatch

- **Risk:** GSHHG 2.3.7 shows Aral Sea at historical ~67,543 km². Current extent (2026) is ~2,500 km². The mask will show a large Central Asian "lake" that no longer exists at that scale.
- **Mitigation:** Exclude via bbox gate (58–62°E, 43–47°N) from `inland_water_mask`; set `aral_sea_excluded: true` in metadata. Alternative: ETOPO1 z > 0 depth gate (Aral basin is below sea level).
- **Severity:** MEDIUM — geographically incorrect; visible in previews; risk of d6 misuse

### R3 — Lake Chad historical extent mismatch

- **Risk:** Lake Chad at 11,977 km² reflects its 1960s peak. Current area ~1,500 km². Mask will show a mostly-dried lake.
- **Mitigation:** Note `data_epoch: pre-1990` in metadata. For d6 structural texture, historical shape may be acceptable.
- **Severity:** LOW — historical use acceptable in visual context

### R4 — Poyang / Dongting seasonal absence

- **Risk:** Both lakes absent in h/L2 as standalone positive-area polygons; merged into Yangtze river-lake zone. Will not appear in any lake mask using h/L2 `area > 0` filter.
- **Mitigation:** Accept absence; note in metadata. River-lake zone mask (§4.6, deferred) may partially cover this region.
- **Severity:** LOW — geographically notable but sub-threshold at 2K

### R5 — Great Lakes as single h/L2 polygon

- **Risk:** All 5 Great Lakes (Superior, Huron, Michigan, Erie, Ontario) are stored as one 208,200 km² polygon in h/L2. Individual lake identities require f/L2.
- **Mitigation:** Unified blob is visually acceptable at 2K. Upgrade to f/L2 only if individual lake selection is required.
- **Severity:** LOW at 2K

### R6 — Antimeridian polygon splits

- **Risk:** GSHHG shapefiles split dateline-straddling polygons into east+west parts. Unlikely for inland lakes but possible.
- **Mitigation:** `rasterize_gshhg_land()` already has antimeridian detection; apply same logic to L2 rasterization.
- **Severity:** LOW

### R7 — L3 `parent_id` linkage reliability

- **Risk:** `parent_id` in L3 references the `id` field of the containing L2 polygon. These are real non-zero values. If the tier is mixed (e.g., using f/L3 with h/L2), IDs may not match.
- **Mitigation:** Use h/L3 with h/L2 exclusively. Spatial containment (point-in-polygon) as fallback where needed.
- **Severity:** LOW

---

## 7. Final Recommendation

### 7.1 Verdict After Revision

**READY FOR B-6.2G-1B.** All assets confirmed present. Risks documented. Implementation constraints defined.

### 7.2 Decision Table

| Question | Answer |
|----------|:------:|
| Can GSHHG L2 support `lake_mask_from_GSHHG_L2`? | **YES** |
| Can GSHHG L3 support lake island hole-punching? | **YES** — via real `parent_id`→L2 `id` linkage |
| Must B-6.2G-1B filter L2 to `area > 0`? | **YES** — mandatory; negative-area shapes are river-lake zones |
| Is h tier sufficient for 2K prototype masks? | **YES** — f tier not needed at 2048×1024 |
| Should Aral Sea be excluded from default `inland_water_mask`? | **YES** — historical/anachronistic extent |
| Should river-lake zones (negative area) be kept separate? | **YES** — optional deferred mask; do not merge |
| Should WDBII rivers remain deferred? | **YES** — polyline geometry; different geometry type; defer to B-6.2G-2 |
| Is Poyang Lake recoverable at 2K? | **NO** — absent in h/L2; accept absence |
| Should B-6.2G-1B proceed after this revision? | **YES** |
| Does `d6_noon_air_earth_generator.py` remain untouched? | **YES** |
| Does B-6.4 remain draft-only? | **YES** |

### 7.3 Implementation Priority for B-6.2G-1B

1. `large_lake_mask` — area ≥ 10,000 km², h/L2 positive only (17 polygons). Cleanest, safest.
2. `inland_water_mask` — area ≥ 1,000 km², h/L2 positive only + h/L3 holes via real `parent_id` (156 polygons). Full useful coverage. Exclude Aral Sea via bbox gate.
3. `inland_water_distance_mask` — EDT derived from `inland_water_mask`.
4. Set `aral_sea_excluded: true` in metadata with bbox (58–62°E, 43–47°N).
5. Skip WDBII rivers, river-lake zones, Poyang/Dongting for this phase.
6. Run watchlist validation (§3.3) after generation: confirm Aral absent, confirm Poyang/Dongting absent, confirm Titicaca/Qinghai/Taihu presence or documented absence.

### 7.4 Assets Required at Implementation

| Asset | Path | Size | Status |
|-------|------|------|--------|
| GSHHG h/L2 | `pwa/assets/source/coastline/gshhg/GSHHS_shp/h/GSHHS_h_L2.shp` | 4.1 MB | ✓ Present |
| GSHHG h/L3 | `pwa/assets/source/coastline/gshhg/GSHHS_shp/h/GSHHS_h_L3.shp` | 400 KB | ✓ Present |
| ETOPO1 | `pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd` | 890 MB | ✓ Present |
| WDBII h/L01 (deferred) | `pwa/assets/source/coastline/gshhg/WDBII_shp/h/WDBII_river_h_L01.shp` | 361 KB | ✓ Present (deferred) |

---

## 8. Revision Status (B-6.2G-1A-R)

| Item | Status |
|------|--------|
| Modified `docs/phase_b6_2g_1a_inland_water_asset_feasibility_audit.md` | **YES** — this revision |
| Modified code / `scripts/generate_b6_structure_masks.py` | **NO** |
| Generated masks | **NO** |
| Ran structure mask generator | **NO** |
| Ran d6 | **NO** |
| Wrote to `pwa/` / `production/` / `candidates/` | **NO** |
| Committed | **NO** |
| Pushed | **NO** |

---

*B-6.2G-1A-R — documentation revision only. No code changes. No mask generation. No commit.*
