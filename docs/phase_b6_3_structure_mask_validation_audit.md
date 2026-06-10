# Phase B-6.3 — Structure Mask Validation Audit

> Created: 2026-06-10
> Auditor: Codex independent review
> Scope: static code audit + read-only output validation
> Non-execution: did not rerun B-6.2 generator, did not run d6, did not generate masks/images/textures, did not commit or push

## Executive Verdict

B-6.2 is a useful 2K non-polar structure-mask prototype, but it is not yet a complete global structure layer.

The script is filesystem-safe for the audited output path, and the `.npz` masks are numerically well-formed: all masks are `(1024, 2048)`, `float32`, finite, and in `[0,1]`. Land/ocean complement exactly, depth hard classes do not overlap, and generated files are ignored by git.

Critical issue: GSHHG L1 high-tier land mask does not cover Antarctica interior. The point `(0, -80)` is classified as `ocean=1`, `land=0`. That is unacceptable for a global reusable structure layer and must be fixed before d6 uses these masks as authoritative global `land_mask` / `ocean_mask`.

Recommendation: proceed to B-6.3 human validation with this issue explicitly called out, but do not freeze B-6.4 API and do not integrate d6 until B-6.2 is patched for polar land/ice handling.

## 1. Static Code Audit

Audited file: `scripts/generate_b6_structure_masks.py`

### 1.1 Path Safety

Findings:

- Reads ETOPO1 from `pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd`.
- Reads GSHHG from `pwa/assets/source/coastline/gshhg/GSHHS_shp`.
- Writes to fixed `OUTPUT_DIR = d5b_processor_v3/d5b_output/structure_masks`.
- `FORBIDDEN_WRITE_PATHS` includes:
  - `pwa/assets/earth/candidates`
  - `pwa/assets/earth/production`
  - `pwa`
- `assert_output_safety()` aborts if output path is inside any forbidden path.
- No logic modifies d6, frontend, `DAY_TEXTURE_VARIANT`, git, production, or candidates.
- Preview paths are under `OUTPUT_DIR / previews`.

Risk notes:

- Output filename is hardcoded as `structure_masks_2048x1024.npz` even though `--resolution` accepts other values up to 4096x2048. This is not a problem for the audited 2K run, but it is a future naming/API bug.
- The script imports `warnings` but does not use it; harmless.

Verdict: path safety passes for audited B-6.2 output.

### 1.2 Input Reading

ETOPO1:

- Reads NetCDF variable `dimension`.
- Treats `dimension[0]` as width and `dimension[1]` as height.
- Reads flat `z`, casts to `float32`, reshapes as `(H_src, W_src)`.
- Downsamples with nearest-neighbor index mapping using `np.linspace` over rows and columns.
- Existing geographic point checks show no obvious north/south flip or 180-degree longitude offset for Sahara, Amazon, Himalaya/Tibet, Yellow Sea, Atlantic, and Pacific.

GSHHG:

- Reads tier selected by `--gshhg-tier`, default `h`.
- Uses `GSHHS_h_L1.shp` for audited output.
- Converts lon/lat to pixel with:
  - `x = (lon + 180) / 360 * w`
  - `y = (90 - lat) / 180 * h`
- Emits a warning count for antimeridian-crossing rings, but renders them approximately.

Risks:

- Antimeridian polygons are not geometrically split/repaired.
- The rasterizer assumes the first ring of a shape is exterior and subsequent rings are holes. This is acceptable for a prototype, but B-6.3 should validate complex multipolygon regions.
- GSHHG L1 high-tier does not include Antarctica interior as land in the generated mask; this is the main critical issue.

### 1.3 Mask Generation Logic

Confirmed:

- `land_mask` and `ocean_mask` come from GSHHG.
- ETOPO1 land/ocean is kept only as `_land_etopo1` for disagreement metrics.
- Depth masks are based on ETOPO1 `z`.
- Depth masks are multiplied by `ocean_mask`.
- Hard depth classes are mutually exclusive at `>0.5`.
- `coastline_distance_mask` comes from distance transform of GSHHG-derived ocean/land.
- `mountain_mask` and `plateau_mask` are multiplied by `land_mask`.

Important nuance:

- Depth masks are feathered with Gaussian sigma 1.0. Therefore hard-class overlap is zero at threshold `>0.5`, but soft masks overlap at nonzero values around class boundaries. This is expected for soft masks but must be documented in the API. Consumers should not assume `deep + mid + shelf + shallow` are strictly one-hot soft classes.

### 1.4 Output Logic

Confirmed:

- `.npz` public mask keys are stable for the B-6.2 output:
  - `land_mask`
  - `ocean_mask`
  - `deep_ocean_mask`
  - `mid_ocean_mask`
  - `continental_shelf_mask`
  - `shallow_sea_mask`
  - `coastline_distance_mask`
  - `mountain_mask`
  - `plateau_mask`
- All arrays are saved as `float32`.
- Metadata records source path, ETOPO1 MD5, GSHHG tier/path, thresholds, resolution, projection assumption, deferred masks, limitations, and safety assertions.
- Metrics record coverage, depth overlap, depth uncovered ocean, raw coastline distance stats, and ETOPO1/GSHHG disagreement.
- Previews are only under `d5b_processor_v3/d5b_output/structure_masks/previews/`.

Missing / should improve:

- GSHHG shapefile MD5 is not recorded in metadata.
- Metrics do not spatially break down ETOPO1/GSHHG disagreement by latitude/region.
- Metrics do not include geographic point sanity checks.
- Metrics do not include Antarctica/Greenland-specific checks.
- Metadata notes no CRS validation, which is honest but should become a B-6.3 validation item.

## 2. Output Numerical Audit

Audited file: `d5b_processor_v3/d5b_output/structure_masks/structure_masks_2048x1024.npz`

Read-only note: system `/usr/bin/python3` had no numpy. The project `.venv/bin/python` had numpy and was used to load the existing `.npz`. That environment did not have `netCDF4`, `scipy`, or `shapefile`, so this audit did not re-read ETOPO1 or re-run any generation logic.

### 2.1 Basic Mask Table

| Mask | Shape | Dtype | Min | Max | Mean | Nonzero Ratio | NaN? | Inf? |
|---|---|---|---:|---:|---:|---:|---|---|
| `land_mask` | `(1024, 2048)` | float32 | 0.00000000 | 1.00000000 | 0.25278759 | 0.25278759 | no | no |
| `ocean_mask` | `(1024, 2048)` | float32 | 0.00000000 | 1.00000000 | 0.74721241 | 0.74721241 | no | no |
| `deep_ocean_mask` | `(1024, 2048)` | float32 | 0.00000000 | 1.00000000 | 0.39750591 | 0.49349833 | no | no |
| `mid_ocean_mask` | `(1024, 2048)` | float32 | 0.00000000 | 1.00000000 | 0.15835153 | 0.35896540 | no | no |
| `continental_shelf_mask` | `(1024, 2048)` | float32 | 0.00000000 | 1.00000000 | 0.03992841 | 0.13644552 | no | no |
| `shallow_sea_mask` | `(1024, 2048)` | float32 | 0.00000000 | 1.00000000 | 0.04328373 | 0.10681868 | no | no |
| `coastline_distance_mask` | `(1024, 2048)` | float32 | 0.00000000 | 1.00000000 | 0.14652981 | 0.74721241 | no | no |
| `mountain_mask` | `(1024, 2048)` | float32 | 0.00000000 | 1.00000000 | 0.02594098 | 0.06603956 | no | no |
| `plateau_mask` | `(1024, 2048)` | float32 | 0.00000000 | 1.00000000 | 0.06729501 | 0.15191603 | no | no |

Basic validation:

- All shapes are exactly `(1024, 2048)`.
- No NaN.
- No Inf.
- Values are in `[0,1]`.

### 2.2 Land / Ocean Checks

| Check | Result |
|---|---:|
| `(land_mask + ocean_mask).min()` | 1.0 |
| `(land_mask + ocean_mask).max()` | 1.0 |
| `(land_mask + ocean_mask).mean()` | 1.0 |
| land/ocean overlap pixels, threshold `>0.5` | 0 |
| land/ocean gap pixels, threshold `<=0.5` both | 0 |
| land coverage | 25.28% |
| ocean coverage | 74.72% |

Coverage is within the requested approximate range: land 25%-32%, ocean 68%-75%.

Critical caveat: the global aggregate hides polar failure. Antarctica interior is currently ocean in GSHHG-derived `land_mask`.

### 2.3 Depth Band Checks

| Check | Result |
|---|---:|
| `depth_band_sum_coverage` hard, `>=1` band at `>0.5` | 0.636123 |
| `unclassified_ocean_coverage` as total image ratio | 0.111089 |
| `unclassified_ocean_coverage` within ocean only | 0.148672 |
| `depth_band_overlap_pixels` hard threshold `>0.5` | 0 |
| `depth_on_land_pixels` hard threshold `>0.5` | 0 |
| soft depth sum min | 0.0 |
| soft depth sum max | 1.000000119 |
| soft depth sum mean | 0.639069 |
| soft overlap pixels at `>1e-6` across multiple bands | 694,122 |
| soft depth sum `>1.000001` pixels | 0 |
| soft depth on land `>1e-6` pixels | 0 |

Interpretation:

- Hard classes are exclusive.
- Soft masks overlap heavily because of feathering, but total soft depth sum is effectively capped at 1.0.
- All depth signal remains inside ocean.
- About 14.9% of ocean is unclassified by hard depth bands. This is plausibly caused by GSHHG ocean pixels where ETOPO1 has land/ice/elevation or by coastal/polar disagreement.
- Continental shelf coverage 3.68% and shallow sea coverage 4.30% are plausible for a coarse 2K ETOPO1 prototype, but likely too weak for reef/atoll use.

### 2.4 Coastline Distance Checks

From metrics:

| Metric | Value |
|---|---:|
| raw distance min px | 0.0 |
| raw distance max px | 319.45 |
| raw distance mean px | 46.81 |
| normalized min | 0.0 |
| normalized max | 1.0 |
| normalized mean | 0.14653 |

Interpretation:

- Distance is zero on land and increases into ocean.
- Nonzero ratio equals ocean coverage, confirming it is ocean-side distance only.
- Max 319px is reasonable for the largest open-ocean distance to nearest GSHHG land in a 2048x1024 equirectangular grid.
- It is normalized only; metadata says km calibration is deferred.

Recommendation:

- Keep both `coastline_distance_px` or `coastline_distance_km` and a normalized mask in future outputs. d6/theme consumers will need physical distance thresholds, not only global normalization.

### 2.5 ETOPO1 / GSHHG Disagreement

Existing metrics:

- disagreement pixels: 248,137
- disagreement ratio: 11.832%
- GSHHG land coverage: 25.279%
- ETOPO1 land coverage: 33.913%

Audit judgment:

- The difference is too large to ignore.
- The Antarctica point sample strongly indicates a major portion is polar: GSHHG L1 `h` land mask excludes Antarctica interior while ETOPO1 Ice Surface includes Antarctic ice/elevation.
- This does not look like a global horizontal/vertical flip: Sahara, Amazon, Tibet, Yellow Sea, Red Sea, Mediterranean, Japan Sea, Atlantic, and Greenland sanity points align broadly as expected.
- This does not look like a 180-degree longitude offset: Atlantic/Pacific/Sahara/Amazon samples are geographically sensible.
- It does affect B-6.2 P0 masks because `land_mask` and `ocean_mask` are foundational.
- B-6.3 must add polar-specific handling before this layer can be called global.

Required B-6.2 patch direction:

- Build `antarctica_ice_mask` / Antarctic land from ETOPO1 or GSHHG L5/L6 Antarctic layers.
- Decide whether base `land_mask` should include Antarctica from ETOPO1 below the GSHHG L1 latitude limit.
- Add regional disagreement metrics by latitude bands and named polar regions.

## 3. Geographic Sanity Checks

Sampling used nearest-pixel lon/lat mapping:

- `x = round((lon + 180) / 360 * (W - 1))`
- `y = round((90 - lat) / 180 * (H - 1))`

| Point | Lon | Lat | land | ocean | deep | mid | shelf | shallow | mountain | plateau | Judgment |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Pacific deep ocean | -150 | 0 | 0.0000 | 1.0000 | 0.6477 | 0.3523 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | ocean valid; deep/mid blend plausible from feather/depth boundary |
| Atlantic deep ocean | -30 | 0 | 0.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | valid deep ocean |
| Sahara | 20 | 23 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | land valid; plateau may be too broad semantically |
| Amazon | -60 | -5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | valid land |
| Himalaya / Tibet | 86 | 30 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | valid mountain/highland |
| Yellow Sea | 123 | 36 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | valid shallow water |
| Red Sea | 38 | 20 | 0.0000 | 1.0000 | 0.0000 | 0.1165 | 0.8820 | 0.0014 | 0.0000 | 0.0000 | valid water; shelf/mid blend plausible |
| Mediterranean | 18 | 36 | 0.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | valid water, deep at point plausible |
| Japan Sea | 135 | 40 | 0.0000 | 1.0000 | 0.0000 | 0.8528 | 0.1472 | 0.0000 | 0.0000 | 0.0000 | valid water |
| Maldives | 73.5 | 3.5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | problematic for water sampling; point hits island land at 2K/GSHHG, needs island proximity/reef proxy |
| Bahamas | -76.5 | 24.5 | 0.0000 | 1.0000 | 0.0003 | 0.5131 | 0.0162 | 0.0084 | 0.0000 | 0.0000 | ocean valid, shallow/bank poorly expressed; ETOPO1 too coarse here |
| Antarctica interior | 0 | -80 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | critical failure: Antarctica treated as ocean |
| Greenland | -42 | 72 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | valid land/ice highland proxy |

Sanity conclusions:

- No evidence of global north/south flip.
- No evidence of 180-degree longitude offset.
- No evidence of broad sea/land inversion.
- Yellow Sea and Red Sea are represented well enough for B-6.3 inspection.
- Bahamas and Maldives confirm that reef/atoll capability remains insufficient.
- Antarctica is a critical polar land/ocean failure.

## 4. Preview / File Safety Audit

Generated files are all under `d5b_processor_v3/d5b_output/structure_masks/`.

| File | Exists | Size | Gitignored? | Safe? |
|---|---:|---:|---:|---|
| `structure_masks_2048x1024.npz` | yes | 8.5M | yes, `.gitignore:12 d5b_processor_v3/d5b_output/` | yes |
| `structure_mask_metadata.json` | yes | 3.3K | yes | yes |
| `structure_mask_metrics.json` | yes | 1.9K | yes | yes |
| `previews/land_ocean_preview.jpg` | yes | 173K | yes | yes |
| `previews/bathymetry_classes_preview.jpg` | yes | 378K | yes | yes |
| `previews/coastline_distance_preview.jpg` | yes | 70K | yes | yes |
| `previews/shallow_sea_preview.jpg` | yes | 147K | yes | yes |

Preview dimensions:

- All four previews are `2048x1024`.
- Preview paths are not under root `previews/`.
- Preview paths are not under `pwa/`.

Additional safety checks:

- `git status --short` does not show generated structure mask files.
- `git check-ignore -v` confirms `.npz`, metadata, metrics, and previews are ignored via `d5b_processor_v3/d5b_output/`.
- A `find` check for `pwa` files newer than the B-6.2 `.npz` returned no files.

## 5. Readiness Verdict

### 5.1 B-6.2 Pass/Fail

| Question | Verdict |
|---|---|
| Is the B-6.2 script filesystem-safe? | Pass for audited path |
| Are 2K masks numerically valid? | Pass |
| Is there a critical issue? | Yes: Antarctica interior classified as ocean |
| Can this enter B-6.3 human validation? | Yes, specifically to validate and document polar/coast/depth issues |
| Can this enter B-6.4 API design? | Conditional only; API must not freeze until polar fix is planned |
| Can this be connected to d6? | No |

Overall B-6.2 verdict:

Conditionally pass as a non-polar 2K prototype and validation artifact. Fail as a complete global authoritative mask layer until polar land/ice handling is patched.

### 5.2 Should We Return To B-5.3?

No.

- Do not return now to B-5.3 `apply_island_reef_floor`.
- Continue B-6.3 validation and B-6.2 patch planning.
- Current structure masks are already stronger than d6 `ocean_px` / `deep_ocean_px` for non-polar ocean/depth classification.
- They are not yet safe replacements globally because Antarctica is wrong.
- Reef/atoll capability is still deferred and insufficient.
- Maldives, Bahamas, Tuamotu, and Great Barrier Reef still need B-6.x proxy work or real reef / higher-resolution bathymetry data.

### 5.3 Next Step

Recommended next step:

1. Create `docs/phase_b6_3_structure_mask_validation.md` for human visual validation checklist.
2. Patch B-6.2 before API freeze:
   - add Antarctica/polar land/ice handling;
   - add GSHHG shapefile MD5;
   - add latitude-band disagreement metrics;
   - add geographic sanity checks to metrics;
   - preserve raw coastline distance in px and/or km, not only normalized mask.
3. Commit the B-6.2 script only after the polar issue is acknowledged or patched.
4. Commit this B-6.3 audit doc after review.
5. Do not commit generated `.npz`, metadata, metrics, or previews.

## Final Recommendation

- B-6.2 script safety: pass.
- B-6.2 numerical validity: pass.
- B-6.2 global semantic validity: fail until Antarctica/polar masks are fixed.
- Proceed to B-6.3 human validation: yes.
- Proceed to B-6.4 API design: only as draft, no API freeze.
- Integrate with d6: no.
- Return to B-5.3 local reef patching: no.

## Non-Execution Confirmation

- Modified code: no.
- Re-ran B-6.2 generator: no.
- Ran d6 generator: no.
- Ran calibration/full-res: no.
- Generated new masks/images/textures: no.
- Wrote to `pwa/`: no.
- Wrote to production/candidates: no.
- Commit/push: no.
