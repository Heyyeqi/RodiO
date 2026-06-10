# Phase B-6.2S-1A Special Sea Water-Only Mask Validation Audit

Date: 2026-06-10

Scope: independent read-only validation of the B-6.2S-1 special sea water-only masks. This audit did not modify code, did not rerun `scripts/generate_b6_structure_masks.py`, did not run d6, did not generate masks or previews, and did not write to `pwa`, `production`, or `candidates`.

Audited files:

- `scripts/generate_b6_structure_masks.py`
- `d5b_processor_v3/d5b_output/structure_masks/structure_masks_2048x1024.npz`
- `d5b_processor_v3/d5b_output/structure_masks/structure_mask_metadata.json`
- `d5b_processor_v3/d5b_output/structure_masks/structure_mask_metrics.json`
- `d5b_processor_v3/d5b_output/structure_masks/previews/special_seas_preview.jpg`

## 1. Static Code Audit

| Check | Result | Pass? |
| ----- | ------ | ----- |
| `_SPECIAL_SEA_CONFIGS` defines 11 masks | Red Sea, Yellow Sea, East China Sea, Japan Sea, Mediterranean, Aegean, Caribbean, Persian Gulf, North Sea, Baltic Sea, South China Sea. | Yes |
| `_SEA_PREVIEW_COLOURS` covers the 11 masks | Each special sea mask has a preview color. | Yes |
| `make_special_sea_masks()` formula | Uses `ocean_mask > 0.5`, lat/lon bbox, and optional `z >= z_floor`. Output is `float32`. | Yes |
| Water-only construction | All special sea masks are ANDed with `ocean_mask`. | Yes |
| Depth gate source | Depth gates use ETOPO1 `z` values. | Yes |
| Image/texture mutation | No image texture modification logic exists in special sea generation. | Yes |
| d6 mutation/integration | No d6 file modification or runtime integration logic. Metadata says `d6_integration: forbidden_until_B6_4_or_later`. | Yes |
| Forbidden output paths | Output remains under `d5b_processor_v3/d5b_output/structure_masks`; safety assertions still list pwa/production/candidates as not written. | Yes |
| `land_leak_pixels` metric | Computed as `(special_mask > 0.5) & land_mask`. This correctly checks hard leakage into final land. | Yes |
| Metadata semantics | Each special sea mask is marked `type: structure_selector`, `visual_effect: none`, `water_only: true`, `land_leak_expected: 0`. | Yes |
| Preview path | `special_seas_preview.jpg` is written only under `d5b_output/structure_masks/previews/`. | Yes |

Static verdict: B-6.2S-1 is structure-selector only. It does not grade textures and does not touch d6 or frontend assets.

## 2. Output Numerical Audit

The `.npz` contains 23 masks:

```text
land_mask
ocean_mask
deep_ocean_mask
mid_ocean_mask
continental_shelf_mask
shallow_sea_mask
coastline_distance_mask
mountain_mask
plateau_mask
antarctica_ice_mask
greenland_ice_mask
polar_land_ice_mask
red_sea_water_mask
yellow_sea_water_mask
east_china_sea_water_mask
japan_sea_water_mask
mediterranean_water_mask
aegean_sea_water_mask
caribbean_water_mask
persian_gulf_water_mask
north_sea_water_mask
baltic_sea_water_mask
south_china_sea_water_mask
```

All special sea masks are non-empty, `float32`, shape `(1024, 2048)`, bounded in `[0,1]`, and have zero land leakage.

| Mask | Shape | Dtype | Min | Max | Mean | Pixel Count | Coverage | Land Leak Pixels | NaN? | Inf? |
| ---- | ----- | ----- | --: | --: | ---: | ----------: | -------: | ---------------: | ---- | ---- |
| `red_sea_water_mask` | `(1024, 2048)` | float32 | 0.0000 | 1.0000 | 0.00042868 | 899 | 0.000429 | 0 | No | No |
| `yellow_sea_water_mask` | `(1024, 2048)` | float32 | 0.0000 | 1.0000 | 0.00073910 | 1550 | 0.000739 | 0 | No | No |
| `east_china_sea_water_mask` | `(1024, 2048)` | float32 | 0.0000 | 1.0000 | 0.00147533 | 3094 | 0.001475 | 0 | No | No |
| `japan_sea_water_mask` | `(1024, 2048)` | float32 | 0.0000 | 1.0000 | 0.00177622 | 3725 | 0.001776 | 0 | No | No |
| `mediterranean_water_mask` | `(1024, 2048)` | float32 | 0.0000 | 1.0000 | 0.00409269 | 8583 | 0.004093 | 0 | No | No |
| `aegean_sea_water_mask` | `(1024, 2048)` | float32 | 0.0000 | 1.0000 | 0.00014353 | 301 | 0.000144 | 0 | No | No |
| `caribbean_water_mask` | `(1024, 2048)` | float32 | 0.0000 | 1.0000 | 0.00576258 | 12085 | 0.005763 | 0 | No | No |
| `persian_gulf_water_mask` | `(1024, 2048)` | float32 | 0.0000 | 1.0000 | 0.00025368 | 532 | 0.000254 | 0 | No | No |
| `north_sea_water_mask` | `(1024, 2048)` | float32 | 0.0000 | 1.0000 | 0.00110197 | 2311 | 0.001102 | 0 | No | No |
| `baltic_sea_water_mask` | `(1024, 2048)` | float32 | 0.0000 | 1.0000 | 0.00073242 | 1536 | 0.000732 | 0 | No | No |
| `south_china_sea_water_mask` | `(1024, 2048)` | float32 | 0.0000 | 1.0000 | 0.00473833 | 9937 | 0.004738 | 0 | No | No |

## 3. Geographic Sanity Check

| Sea | Test Point Lon | Test Point Lat | Expected Mask | Actual Value | Judgment |
| --- | -------------: | -------------: | ------------- | -----------: | -------- |
| Red Sea | 38 | 20 | `red_sea_water_mask = 1` | 1.0000 | Pass |
| Yellow Sea | 123 | 36 | `yellow_sea_water_mask = 1` or near 1 | 1.0000 | Pass |
| East China Sea | 125 | 29 | `east_china_sea_water_mask = 1` | 1.0000 | Pass |
| Japan Sea | 135 | 40 | `japan_sea_water_mask = 1` | 1.0000 | Pass |
| Mediterranean | 18 | 36 | `mediterranean_water_mask = 1` | 1.0000 | Pass |
| Aegean | 25 | 38 | `aegean_sea_water_mask = 1` | 0.0000 | Caution: this exact 2K pixel is land/island. Nearby water points such as `(24.5, 38.5)`, `(26, 39)`, and `(24, 37)` are `aegean=1`. |
| Caribbean | -75 | 16 | `caribbean_water_mask = 1` | 1.0000 | Pass |
| Persian Gulf | 52 | 26 | `persian_gulf_water_mask = 1` | 1.0000 | Pass |
| North Sea | 3 | 56 | `north_sea_water_mask = 1` | 1.0000 | Pass |
| Baltic Sea | 18 | 58 | `baltic_sea_water_mask = 1` | 1.0000 | Pass |
| South China Sea | 113 | 12 | `south_china_sea_water_mask = 1` | 1.0000 | Pass |

Negative samples:

| Negative Point | Expected | Actual | Judgment |
| -------------- | -------- | ------ | -------- |
| Sahara land `(20, 23)` | All special sea masks = 0 | Max special sea value 0.0000 | Pass |
| Pacific deep ocean `(-150, 0)` | All special sea masks = 0 | Max special sea value 0.0000 | Pass |
| Antarctica interior `(0, -80)` | All special sea masks = 0 | Max special sea value 0.0000 | Pass |
| Japan land `(138, 37)` | `japan_sea_water_mask = 0` | 0.0000 | Pass |
| Egypt land near Red Sea `(33, 27)` | `red_sea_water_mask = 0` | 0.0000 | Pass |
| Saudi land near Red Sea `(40, 23)` | `red_sea_water_mask = 0` | 0.0000 | Pass |
| Saudi land near Red Sea `(42, 25)` | `red_sea_water_mask = 0` | 0.0000 | Pass |

Note: `(35, 27)` is classified as ocean in the current land/ocean mask and therefore enters `red_sea_water_mask`; it should not be used as a land-negative sample.

Geographic verdict: 10 of 11 requested center points pass exactly. The Aegean requested point fails because it resolves to land in the base mask, while nearby Aegean water pixels pass. This is a representative-point caveat, not a critical mask failure.

## 4. Depth Gate Validation

| Mask | Depth Gate | Pixel Count With Gate | Estimated Count Without Gate | Gate Removed % | Judgment |
| ---- | ---------- | --------------------: | ---------------------------: | -------------: | -------- |
| `yellow_sea_water_mask` | `z >= -100` | 1550 | 1606 | 3.49% | Pass; gate is not over-filtering. |
| `persian_gulf_water_mask` | `z >= -100` | 532 | 547 | 2.74% | Pass; gate is not over-filtering. |
| `north_sea_water_mask` | `z >= -200` | 2311 | 2738 | 15.60% | Pass with caution; removal is meaningful but aligned with excluding deeper Atlantic/Skagerrak-adjacent pixels. |

Depth gate verdict: no mandatory B-6.2S-1B change is needed. Retain the current gates for API design, but keep `north_sea_water_mask` on the visual review list because its gate removes a larger fraction than Yellow Sea and Persian Gulf.

## 5. Overlap / Conflict Audit

Nonzero overlaps:

| Pair | Overlap Pixels | Judgment |
| ---- | -------------: | -------- |
| `yellow_sea_water_mask` vs `east_china_sea_water_mask` | 611 | Acceptable; expected boundary/transition overlap. API should define priority or allow composite use. |
| `east_china_sea_water_mask` vs `japan_sea_water_mask` | 65 | Small; acceptable near Korea Strait / regional boundary. |
| `east_china_sea_water_mask` vs `south_china_sea_water_mask` | 38 | Small; acceptable boundary overlap. |
| `mediterranean_water_mask` vs `aegean_sea_water_mask` | 301 | Expected nested relationship; Aegean is fully inside Mediterranean. |
| `north_sea_water_mask` vs `baltic_sea_water_mask` | 9 | Tiny boundary overlap; acceptable. |

Overlap verdict:

- Nested masks should be retained.
- Metadata should eventually include explicit `parent`, `child`, and `priority` fields, especially `mediterranean_water_mask -> aegean_sea_water_mask`.
- d6/API consumers must define a priority policy before visual color application. Recommended priority: child/specific masks override parent/general masks.

## 6. Preview Audit

| Check | Result | Pass? |
| ----- | ------ | ----- |
| `special_seas_preview.jpg` exists | Present at `d5b_processor_v3/d5b_output/structure_masks/previews/special_seas_preview.jpg`. | Yes |
| Dimensions | 2048x1024 RGB JPEG. | Yes |
| Output location | Only under `d5b_output/structure_masks/previews/`. | Yes |
| Root `previews/` write | No evidence of B-6.2S-1 output written to root `previews/`. | Yes |
| `pwa` write | No newer files found under `pwa` from this output timestamp check. | Yes |
| Visual geography | 11 colored regions are visible in the expected broad locations. | Yes |
| Longitude/latitude offset | No obvious global offset. | Yes |
| Land/ocean reversal | No; colors appear only on water-selected pixels. | Yes |

Preview caveat: several masks are large geographic selectors. Caribbean, Mediterranean, and South China Sea should not be treated as feathered visual effects directly; they are water-only selectors that require downstream feathering and priority rules.

## 7. Git Safety Audit

`git check-ignore -v` confirms all generated B-6.2S-1 outputs are ignored by `.gitignore:12:d5b_processor_v3/d5b_output/`:

```text
d5b_processor_v3/d5b_output/structure_masks/structure_masks_2048x1024.npz
d5b_processor_v3/d5b_output/structure_masks/structure_mask_metadata.json
d5b_processor_v3/d5b_output/structure_masks/structure_mask_metrics.json
d5b_processor_v3/d5b_output/structure_masks/previews/special_seas_preview.jpg
```

Current `git status --short` does not show generated structure mask outputs. It does show unrelated existing local changes, including `d5b_processor_v3/d6_noon_air_earth_generator.py`, `devlog.md`, and root `previews/` directories. This audit did not modify those files.

## 8. Readiness Verdict

1. Do B-6.2S-1 special sea masks pass validation?
   Answer: Yes. All 11 masks are present, non-empty, water-only, numerically valid, and geographically coherent.

2. Is there any critical issue?
   Answer: No critical issue was found.

3. Is B-6.2S-1B required?
   Answer: No mandatory fix is required. Optional improvements: add explicit parent/child/priority metadata and note that the requested Aegean point `(25,38)` lands on a 2K land/island pixel.

4. Can the project enter B-6.2S-2 shelf / bank masks?
   Answer: Yes, after this audit is reviewed. Do not enter B-6.2S-2 in this turn.

5. Can B-6.4 API draft proceed in parallel?
   Answer: Yes, as a design-only draft. It must include mask priority, child-over-parent behavior, feathering expectations, and failure behavior.

6. Is d6 integration still forbidden?
   Answer: Yes. These masks are selectors only and are not ready for runtime visual application.

7. Is returning to B-5.3 still forbidden?
   Answer: Yes. Continue structure-layer validation rather than local visual patching.

8. Should this audit document be committed?
   Answer: Yes, it is safe to commit this markdown audit document when the user chooses to commit docs.

9. Should generated masks / previews be committed?
   Answer: No. `.npz`, metadata, metrics, and preview outputs should remain ignored and uncommitted.

## Final Recommendation

- B-6.2S-1 verdict: Pass.
- Critical issue: None.
- Required B-6.2S-1B patch: No.
- Optional B-6.2S-1B/API metadata improvement: parent/child/priority fields for nested and overlapping masks.
- Proceed to B-6.2S-2: Yes, after review; not in this turn.
- Proceed to B-6.4 API draft: Yes, design-only; not runtime integration.
- Connect to d6: No.
- Resume B-5.3: No.
- Commit generated outputs: No.
