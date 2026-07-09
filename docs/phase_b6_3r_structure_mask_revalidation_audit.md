# Phase B-6.3R Structure Mask Re-validation Audit

Date: 2026-06-10

Scope: independent read-only audit of the B-6.2P 2K structure mask outputs and generator code safety. This audit did not rerun `scripts/generate_b6_structure_masks.py`, did not run d6, did not generate masks or textures, and did not write to `pwa`, `production`, or `candidates`.

Audited files:

- `scripts/generate_b6_structure_masks.py`
- `d5b_processor_v3/d5b_output/structure_masks/structure_masks_2048x1024.npz`
- `d5b_processor_v3/d5b_output/structure_masks/structure_mask_metadata.json`
- `d5b_processor_v3/d5b_output/structure_masks/structure_mask_metrics.json`
- `d5b_processor_v3/d5b_output/structure_masks/previews/`
- `docs/phase_b6_3_structure_mask_validation_audit.md`
- `docs/phase_b6_1_asset_audit.md`

## 1. B-6.2P Fix Review

The B-6.2P output metadata reports `phase: B-6.2P (Polar Patch)` and records explicit polar handling:

- Antarctica supplement: ETOPO1 Ice `z > 0` where latitude `< -60`.
- Greenland supplement: ETOPO1 Ice `z > 0` inside approximate Greenland bbox `lat 59.5..84.5`, `lon -74..-11`.
- Final land mask: `max(GSHHG_rasterized, polar_land_ice_supplement)`.
- Ocean mask: recomputed as `1 - land_mask`.
- Depth masks: recomputed after polar supplement.

| Check | Result | Pass? |
| ----- | ------ | ----- |
| `antarctica_ice_mask` exists | Present in `.npz`, `float32[1024,2048]`, coverage 10.22%. | Yes |
| `greenland_ice_mask` exists | Present in `.npz`, `float32[1024,2048]`, coverage 1.23%. | Yes |
| `polar_land_ice_mask` exists | Present in `.npz`, `float32[1024,2048]`, coverage 11.45%. | Yes |
| `land_mask` merges polar supplement | Metadata says `land_mask = max(GSHHG_rasterized, polar_land_ice_supplement)`. Metrics show final land 35.51% vs GSHHG-only 25.28%. | Yes |
| `ocean_mask` recomputed after supplement | Metadata flag `ocean_mask_recomputed_after_polar_supplement: true`; land+ocean sum is exactly 1.0. | Yes |
| Depth masks recomputed from new ocean | Metadata flag `depth_masks_recomputed_after_polar_supplement: true`; `depth_on_land_pixels = 0`. | Yes |
| Antarctica interior excluded from ocean/depth | At `(0,-80)`: `land=1`, `ocean=0`, `antarctica_ice=1`, all depth masks 0. | Yes |

Verdict: B-6.2P directly fixes the critical Antarctica land/ocean failure found in B-6.3.

## 2. NPZ Numerical Integrity

All 12 masks are present, have shape `(1024, 2048)`, contain no NaN/Inf, and remain within `[0,1]`.

| Mask | Shape | Dtype | Min | Max | Mean | Nonzero Ratio | NaN? | Inf? |
| ---- | ----- | ----- | --: | --: | ---: | ------------: | ---- | ---- |
| `land_mask` | `(1024, 2048)` | float32 | 0.000000 | 1.000000 | 0.355096 | 0.355096 | No | No |
| `ocean_mask` | `(1024, 2048)` | float32 | 0.000000 | 1.000000 | 0.644904 | 0.644904 | No | No |
| `deep_ocean_mask` | `(1024, 2048)` | float32 | 0.000000 | 1.000000 | 0.397506 | 0.493464 | No | No |
| `mid_ocean_mask` | `(1024, 2048)` | float32 | 0.000000 | 1.000000 | 0.158334 | 0.357826 | No | No |
| `continental_shelf_mask` | `(1024, 2048)` | float32 | 0.000000 | 1.000000 | 0.039639 | 0.131596 | No | No |
| `shallow_sea_mask` | `(1024, 2048)` | float32 | 0.000000 | 1.000000 | 0.043002 | 0.101521 | No | No |
| `coastline_distance_mask` | `(1024, 2048)` | float32 | 0.000000 | 1.000000 | 0.162854 | 0.644904 | No | No |
| `mountain_mask` | `(1024, 2048)` | float32 | 0.000000 | 1.000000 | 0.100345 | 0.148690 | No | No |
| `plateau_mask` | `(1024, 2048)` | float32 | 0.000000 | 1.000000 | 0.080799 | 0.179196 | No | No |
| `antarctica_ice_mask` | `(1024, 2048)` | float32 | 0.000000 | 1.000000 | 0.102248 | 0.102248 | No | No |
| `greenland_ice_mask` | `(1024, 2048)` | float32 | 0.000000 | 1.000000 | 0.012267 | 0.012267 | No | No |
| `polar_land_ice_mask` | `(1024, 2048)` | float32 | 0.000000 | 1.000000 | 0.114515 | 0.114515 | No | No |

Additional integrity checks:

```text
land_ocean_sum_min = 1.0
land_ocean_sum_max = 1.0
land_ocean_sum_mean = 1.0
land_ocean_overlap_px = 0
land_ocean_gap_px = 0
depth_band_overlap_pixels_hard = 0
depth_on_land_pixels_hard = 0
antarctica_depth_mask_pixels_hard = 0
soft_depth_sum_max = 1.0000001192092896
soft_depth_sum_gt1_pixels = 0
antarctica_nonpolar_nonzero = 0
greenland_nonpolar_nonzero = 0
polar_nonpolar_nonzero = 0
```

The high `soft_depth_overlap_pixels_gt_1e-6 = 685932` is expected from feathered float bands. It is not a hard overlap problem because the soft depth sum never exceeds 1 beyond float tolerance.

## 3. Land / Ocean Coverage

```text
land_coverage = 0.35509586
ocean_coverage = 0.64490414
land_plus_ocean_mean = 1.0
land_plus_ocean_min = 1.0
land_plus_ocean_max = 1.0
```

Assessment:

- B-6.2 GSHHG-only land coverage was 25.28%, which omitted deep Antarctica and Greenland ice interiors at 2K.
- B-6.2P final land coverage is 35.51% after adding polar land/ice supplement.
- This is higher than the common equal-area Earth land fraction, but this grid is equirectangular pixel coverage, not equal-area surface coverage. Polar rows are overrepresented in pixel space, so Antarctica and Greenland materially raise the pixel ratio.
- The result is reasonable for a 2K equirectangular structure mask whose immediate job is to keep polar land ice out of ocean and depth processing.
- Possible over-expansion remains: ETOPO1 Ice `z > 0` in polar regions may include ice-shelf or marginal polar features, and the Greenland bbox is approximate. This is acceptable for B-6.4 API design but requires B-6.3 visual validation before d6 use.

## 4. Depth Integrity

```text
depth_band_sum_coverage_hard = 0.63608027
unclassified_ocean_pixels = 18505
unclassified_ocean_ratio_within_ocean = 0.01368245
depth_band_overlap_pixels_hard = 0
depth_on_land_pixels_hard = 0
antarctica_depth_mask_pixels_hard = 0
```

Assessment:

- `depth_on_land_pixels = 0`: depth masks are correctly constrained to ocean after the polar supplement.
- `antarctica_depth_mask_pixels = 0`: Antarctica is no longer included in deep/mid/shelf/shallow ocean masks.
- Hard depth bands are mutually exclusive.
- Unclassified ocean is 18,505 pixels, about 1.37% of ocean pixels. This is small enough for B-6.4 planning and likely comes from threshold edges, feathering, coastline rasterization, or source disagreement.
- Southern Ocean sample `(0,-55)` remains ocean and is classified mainly as mid-ocean with small deep/shelf blend, which is consistent with the expected behavior outside the Antarctic land-ice supplement.

## 5. ETOPO1 / GSHHG Disagreement

```text
before_disagreement_ratio = 0.11832
after_disagreement_ratio = 0.01601
disagreement_reduction_pixels = 214556
```

Assessment:

- The drop from 11.83% to 1.60% is a material fix and strongly supports that the previous critical disagreement was polar land-ice handling, not a global coordinate flip.
- Geographic samples show no evidence of vertical flip, 180-degree longitude offset, or global land/ocean reversal.
- Residual disagreement is plausible from coastline rasterization, small islands, polar margins, GSHHG/ETOPO1 semantic differences, and 2K resolution loss.
- 1.60% is acceptable for entering B-6.4 API design, with the constraint that d6 integration remains forbidden until visual validation confirms coastlines, shelves, and special regions.

## 6. Geographic Sanity Check

| Point | Lon | Lat | land | ocean | deep | mid | shelf | shallow | antarctica_ice | greenland_ice | mountain | plateau | Judgment |
| ----- | --: | --: | ---: | ----: | ---: | --: | ----: | ------: | -------------: | ------------: | -------: | ------: | -------- |
| Pacific deep ocean | -150 | 0 | 0.0000 | 1.0000 | 0.6477 | 0.3523 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass; ocean and depth-classified. |
| Atlantic deep ocean | -30 | 0 | 0.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass; deep ocean. |
| Sahara | 20 | 23 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | Pass for land; plateau flag may need ecology/topography review later. |
| Amazon | -60 | -5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass. |
| Tibet | 86 | 30 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | Pass for land/mountain; plateau classifier needs separate validation. |
| Yellow Sea | 123 | 36 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass; shallow sea captured. |
| Red Sea | 38 | 20 | 0.0000 | 1.0000 | 0.0000 | 0.1165 | 0.8820 | 0.0014 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass for water-only and shelf/mid mix. |
| Mediterranean | 18 | 36 | 0.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass for ocean; local shelf detail not represented at this point. |
| Japan Sea | 135 | 40 | 0.0000 | 1.0000 | 0.0000 | 0.8528 | 0.1472 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass. |
| Maldives | 73.5 | 3.5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Caution; sample lands on tiny island at 2K. Needs island-proximity/reef proxy, not point-only water validation. |
| Bahamas | -76.5 | 24.5 | 0.0000 | 1.0000 | 0.0003 | 0.5131 | 0.0162 | 0.0084 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Partial; ocean correct, but bank/shallow signal is weak at this exact point. Needs Bahamas bank mask. |
| Antarctica interior | 0 | -80 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | Pass; previous critical issue fixed. |
| Southern Ocean | 0 | -55 | 0.0000 | 1.0000 | 0.0206 | 0.9664 | 0.0131 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass; ocean remains ocean outside polar supplement. |
| Greenland | -42 | 72 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 0.0000 | Pass; Greenland ice supplement active. |

Key interpretation:

- No sign of upside-down latitude mapping.
- No sign of longitude shift or 180-degree wrap failure in these samples.
- No sign of global sea/land inversion.
- Yellow Sea and Red Sea are substantially improved as water-only/depth-aware targets.
- Maldives, Bahamas, Tuamotu, Great Barrier Reef, and similar reef/bank systems still need dedicated reef/atoll/bank masks. The B-6.2P masks should not be treated as a solved reef layer.

## 7. Preview / Git Safety Check

Output remains under `d5b_processor_v3/d5b_output/structure_masks/`. Preview files remain under `d5b_processor_v3/d5b_output/structure_masks/previews/`. No evidence was found of writes to root `previews/`, `pwa`, `production`, or `candidates` during the B-6.2P output timestamp check.

| File | Exists | Size | Gitignored? | Safe? |
| ---- | ------ | ---: | ----------- | ----- |
| `d5b_processor_v3/d5b_output/structure_masks/structure_masks_2048x1024.npz` | Yes | 8.0M | Yes, ignored by `.gitignore:12:d5b_processor_v3/d5b_output/` | Yes |
| `d5b_processor_v3/d5b_output/structure_masks/structure_mask_metadata.json` | Yes | 4.4K | Yes, ignored by `.gitignore:12:d5b_processor_v3/d5b_output/` | Yes |
| `d5b_processor_v3/d5b_output/structure_masks/structure_mask_metrics.json` | Yes | 3.8K | Yes, ignored by `.gitignore:12:d5b_processor_v3/d5b_output/` | Yes |
| `d5b_processor_v3/d5b_output/structure_masks/previews/land_ocean_preview.jpg` | Yes | 186K | Yes, ignored by `.gitignore:12:d5b_processor_v3/d5b_output/` | Yes |
| `d5b_processor_v3/d5b_output/structure_masks/previews/bathymetry_classes_preview.jpg` | Yes | 378K | Yes, ignored by `.gitignore:12:d5b_processor_v3/d5b_output/` | Yes |
| `d5b_processor_v3/d5b_output/structure_masks/previews/coastline_distance_preview.jpg` | Yes | 101K | Yes, ignored by `.gitignore:12:d5b_processor_v3/d5b_output/` | Yes |
| `d5b_processor_v3/d5b_output/structure_masks/previews/shallow_sea_preview.jpg` | Yes | 148K | Yes, ignored by `.gitignore:12:d5b_processor_v3/d5b_output/` | Yes |
| `d5b_processor_v3/d5b_output/structure_masks/previews/polar_ice_supplement_preview.jpg` | Yes | 59K | Yes, ignored by `.gitignore:12:d5b_processor_v3/d5b_output/` | Yes |

## 8. Readiness Verdict

1. Did B-6.2P fix the Antarctica critical issue found in B-6.3?
   Answer: Yes. Antarctica interior is now land/ice, not ocean, and contributes zero depth-mask pixels.

2. Are there remaining critical issues?
   Answer: No critical blocker was found for B-6.4 API design. Remaining issues are capability gaps and validation risks, not immediate numerical failures.

3. Can B-6.2P masks enter B-6.3 human visual validation?
   Answer: Yes. Visual validation should focus on polar margins, Greenland bbox edges, coastline alignment, Yellow Sea, Red Sea, Bahamas, Maldives, Tuamotu, and Great Barrier Reef.

4. Can B-6.2P masks enter B-6.4 Structure Layer API Design?
   Answer: Yes, for API design and read-only integration planning. The API should preserve mask provenance, version, resolution, and known limitations.

5. Is d6 integration still forbidden?
   Answer: Yes. Do not connect these masks to d6 until B-6.3 visual validation and B-6.4 API design are complete.

6. Is B-5.3 implementation still forbidden?
   Answer: Yes. Do not return to local circle/bbox reef recovery while the structure layer is being validated.

7. Can we start planning how d6 reads these masks?
   Answer: Yes. Planning can start in B-6.4, but no runtime wiring should happen yet.

8. Which capabilities are still insufficient?
   Answer: reef/atoll, Bahamas bank, Maldives/Tuamotu, Great Barrier Reef, high-resolution GEBCO, and special sea water-only masks remain unresolved. ETOPO1 + GSHHG P0 masks are enough for land/ocean, broad bathymetry bands, polar exclusion, and draft API design, but not for final Noon Air reef/island aesthetics.

## Final Recommendation

- B-6.2P verdict: Pass for revalidation and B-6.4 API design readiness.
- Critical issue status: The prior Antarctica critical issue is fixed; no new critical issue was found.
- Proceed to B-6.3 human visual validation: Yes.
- Proceed to B-6.4 Structure Layer API Design: Yes.
- Connect to d6 now: No.
- Resume B-5.3 local patch implementation: No.
- Commit generated `.npz`, metadata, metrics, or previews: No.
- Next smallest safe action: write the B-6.4 API design plan defining mask loading, metadata checks, resolution matching, and failure behavior without modifying d6 runtime.
