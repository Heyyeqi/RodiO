# Phase B-6.3H Structure Mask Human / Geographic Validation

Date: 2026-06-10

Scope: human-readable geographic validation of the already-generated B-6.2P 2K structure masks. This pass only read existing `.npz`, metadata, metrics, and preview files. It did not rerun the generator, did not run d6, did not generate masks or images, and did not write to `pwa`, `production`, or `candidates`.

Validated outputs:

- `d5b_processor_v3/d5b_output/structure_masks/structure_masks_2048x1024.npz`
- `d5b_processor_v3/d5b_output/structure_masks/structure_mask_metadata.json`
- `d5b_processor_v3/d5b_output/structure_masks/structure_mask_metrics.json`
- `d5b_processor_v3/d5b_output/structure_masks/previews/`

## 1. Output Identity

The metadata identifies the current output as `B-6.2P (Polar Patch)` at `2048x1024`, generated at `2026-06-10T06:49:06Z`.

Existing preview files:

| Preview | Exists | Dimensions | Size |
| ------- | ------ | ---------- | ---: |
| `land_ocean_preview.jpg` | Yes | 2048x1024 | 186K |
| `bathymetry_classes_preview.jpg` | Yes | 2048x1024 | 378K |
| `coastline_distance_preview.jpg` | Yes | 2048x1024 | 101K |
| `shallow_sea_preview.jpg` | Yes | 2048x1024 | 148K |
| `polar_ice_supplement_preview.jpg` | Yes | 2048x1024 | 59K |

## 2. Global Preview Validation

| Check | Observation | Judgment |
| ----- | ----------- | -------- |
| Upside-down latitude flip | Continents, Antarctica, Greenland, Arctic regions, and Southern Ocean appear in expected north/south positions. | Pass |
| Longitude offset / 180-degree shift | Americas, Europe/Africa, Asia, and Pacific layout are in normal equirectangular positions. | Pass |
| Land/ocean reversal | Land appears as land and oceans as ocean in `land_ocean_preview.jpg`. | Pass |
| Antarctica land/ice | Antarctica is included as land/ice after B-6.2P, not ocean. | Pass |
| Greenland land/ice | Greenland is included as land/ice after B-6.2P. | Pass |
| Pacific / Atlantic / Indian Ocean | All three major oceans are correctly ocean in global preview and point samples. | Pass |
| Continental shelf placement | Shelf/shallow classes primarily track continental margins and enclosed shallow seas. | Pass |
| Shallow sea placement | Strong shallow signal appears around Yellow Sea, East China Sea, North Sea, Persian Gulf, Southeast Asia, Arctic shelves, Bahamas/Caribbean margins, and other expected shelves. | Pass |
| Coastline distance continuity | `coastline_distance_preview.jpg` increases away from land along ocean basins and is continuous around coasts. Voronoi-like basin ridges are expected for distance transforms. | Pass |

Preview-level caveats:

- `coastline_distance_mask` is normalized pixel distance, not kilometers. It is usable as a proximity field but not as a geodesic metric.
- Fine reefs and island chains are not visually reliable in 2K P0 masks. They require dedicated reef/atoll/island proximity work.
- Some point samples in very narrow seas or island regions can hit a land pixel instead of adjacent water; this is expected at 2K but important for later water-only masks.

## 3. Global Key Point Sampling

| Region | Lon | Lat | land | ocean | deep | mid | shelf | shallow | coastline_distance | antarctica_ice | greenland_ice | mountain | plateau | Judgment |
| ------ | --: | --: | ---: | ----: | ---: | --: | ----: | ------: | -----------------: | -------------: | ------------: | -------: | ------: | -------- |
| Pacific deep ocean | -150 | 0 | 0.0000 | 1.0000 | 0.6477 | 0.3523 | 0.0000 | 0.0000 | 0.2569 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass; ocean with deep/mid blend. |
| Atlantic deep ocean | -30 | 0 | 0.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1781 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass; deep ocean. |
| Indian Ocean | 80 | -20 | 0.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.5822 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass; ocean. |
| Sahara | 20 | 23 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | Pass for land; plateau proxy should not be treated as ecology. |
| Amazon | -60 | -5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass. |
| Tibet | 86 | 30 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | Pass for high terrain. |
| Himalaya | 86 | 28 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.9364 | 0.0636 | Pass; mountain-dominant. |
| Antarctica interior | 0 | -80 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | Pass; B-6.2 critical issue fixed. |
| Southern Ocean | 0 | -55 | 0.0000 | 1.0000 | 0.0206 | 0.9664 | 0.0131 | 0.0000 | 0.1288 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass; ocean outside polar supplement. |
| Greenland | -42 | 72 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 0.0000 | Pass; Greenland ice supplement active. |
| Yellow Sea | 123 | 36 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0412 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass; shallow captured. |
| East China Sea | 125 | 29 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.0920 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass; shallow captured. |
| Red Sea | 38 | 20 | 0.0000 | 1.0000 | 0.0000 | 0.1165 | 0.8820 | 0.0014 | 0.0282 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass for ocean; needs named water mask for color work. |
| Mediterranean | 18 | 36 | 0.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.1098 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass for ocean; local shelf varies by subregion. |
| Japan Sea | 135 | 40 | 0.0000 | 1.0000 | 0.0000 | 0.8528 | 0.1472 | 0.0000 | 0.1149 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass; mid/shelf mix. |
| Caribbean | -75 | 16 | 0.0000 | 1.0000 | 0.1554 | 0.8446 | 0.0000 | 0.0000 | 0.0706 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass for ocean; shallow reef/bank detail incomplete. |
| Bahamas | -76.5 | 24.5 | 0.0000 | 1.0000 | 0.0003 | 0.5131 | 0.0162 | 0.0084 | 0.0071 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Partial; ocean correct but Bahamas Bank is weak at this point. |
| Maldives | 73.5 | 3.5 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Caution; point falls on tiny island/land pixel at 2K. Reef/atoll proxy still required. |
| Persian Gulf | 52 | 26 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.9569 | 0.0141 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass; shallow captured. |
| North Sea | 3 | 56 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | 0.1313 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Pass; shallow captured. |

Additional targeted samples:

| Region | Lon | Lat | land | ocean | deep | mid | shelf | shallow | Judgment |
| ------ | --: | --: | ---: | ----: | ---: | --: | ----: | ------: | -------- |
| South China Sea | 115 | 12 | 0.0000 | 1.0000 | 0.9417 | 0.0569 | 0.0014 | 0.0000 | Pass for ocean; point is deep basin, not shelf. |
| Tuamotu | -145 | -16 | 0.0000 | 1.0000 | 0.0002 | 0.4431 | 0.1632 | 0.0000 | Partial; no reliable reef/atoll structure. |
| Hawaii | -157 | 20 | 0.0000 | 1.0000 | 0.9283 | 0.0674 | 0.0029 | 0.0000 | Pass for surrounding ocean; island halo/refringent shelf not represented. |
| Baltic Sea | 20 | 58 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0004 | 0.9978 | Pass; shallow enclosed sea captured. |
| Aegean Sea | 25 | 38 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Caution; point lands on island/land pixel. Needs named water-only mask. |
| Great Barrier Reef | 147 | -18 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Caution; point lands on coast/land pixel. Requires GBR-specific proxy or better data. |

## 4. Regional Structure Assessment

### East Asia

| Region | Assessment | Enough For Next Phase? |
| ------ | ---------- | ---------------------- |
| Yellow Sea | Correctly ocean and strongly shallow at sampled point. Preview also shows expected shallow shelf in the Yellow/East China shelf system. | Yes |
| East China Sea | Correctly ocean and shallow at sampled point. | Yes |
| Japan Sea | Correctly ocean, mostly mid with shelf contribution. | Yes |
| South China Sea | Correctly ocean. The central sample is deep basin, while coastal shelves appear in preview around Southeast Asia. | Yes for P0; special/coastal refinements later. |

East Asia verdict: P0 masks are geographically coherent enough to support B-6.2S-1 and B-6.4 planning. Yellow/East China color work still needs named water-only masks and color metrics, not just global shallow masks.

### Tropical Island Regions

| Region | Assessment | Needed Later |
| ------ | ---------- | ------------ |
| Maldives | The requested point resolves to land at 2K, which is plausible for tiny islands but unusable as a reef/lagoon mask. | B-6.2S-2/S-3 reef/atoll and island proximity proxy; later higher-resolution bathymetry/reef data. |
| Bahamas | Ocean is correct, but shelf/shallow is weak at the sampled bank point. | Dedicated Bahamas Bank mask or higher-quality bathymetry. |
| Caribbean | Ocean is correct, but reef/bank detail is incomplete. | Named water mask plus local shallow/reef proxy. |
| French Polynesia / Tuamotu | Ocean detected, but the reef/atoll structure is not reliable. | Atoll proxy, island group anchors, or reef data. |
| Hawaii | Surrounding ocean detected, but island halo/shelf structure is not represented. | Island proximity and local shelf/halo logic. |

Tropical island verdict: P0 masks are not sufficient for Noon Air island/reef aesthetics. They are adequate to proceed to B-6.2S-1 only because S-1 is named special sea water masks, not final reef/atoll recovery.

### Narrow / Special Seas

| Region | Assessment | Need Named Water-only Mask? |
| ------ | ---------- | --------------------------- |
| Red Sea | Correctly ocean; shelf/mid mix looks plausible. Narrow geometry makes bbox or RGB detection risky. | Yes |
| Persian Gulf | Correctly ocean and shallow. | Yes |
| Baltic Sea | Correctly ocean and shallow. | Yes |
| Mediterranean / Aegean | Mediterranean point is ocean; Aegean point can hit island/land at 2K. | Yes |
| North Sea | Correctly ocean and shallow. | Yes |

Special sea verdict: B-6.2P provides enough base land/ocean/depth structure to start B-6.2S-1. S-1 should create explicit water-only named masks so future color modules do not rely on rectangular bboxes or point sampling.

### Polar

| Region | Assessment | Stability |
| ------ | ---------- | --------- |
| Antarctica | Interior is land/ice and excluded from ocean/depth. Preview shows Antarctica as land/ice. | Stable enough for next phase. |
| Greenland | Greenland is land/ice and excluded from ocean/depth. | Stable enough for next phase, with bbox approximation caveat. |
| Southern Ocean | Remains ocean outside polar supplement and is classified primarily mid/deep/shelf depending on location. | Stable enough for next phase. |

Polar verdict: B-6.2P fixed the B-6.3 Antarctica critical issue. Remaining polar caveats are edge accuracy, ice shelf semantics, and equirectangular pixel-area distortion, none of which block B-6.2S-1.

## 5. Final Validation Answers

1. Do B-6.2P structure masks pass human/geographic validation?
   Answer: Yes, for P0 global land/ocean, broad depth classes, polar land/ice exclusion, and readiness for named water-only mask work.

2. Is there any remaining critical issue?
   Answer: No critical issue was found. The prior Antarctica critical issue is fixed.

3. Can the project enter B-6.2S-1 special sea water-only masks?
   Answer: Yes. The base masks are coherent enough to support special sea water-only mask generation.

4. Can B-6.4 API design be drafted in parallel?
   Answer: Yes. API design can proceed in parallel as long as it remains design-only and does not wire d6 runtime.

5. Is d6 integration still forbidden?
   Answer: Yes. Do not connect these masks to d6 until B-6.2S outputs and B-6.4 API decisions are reviewed.

6. Is B-5.3 visual patch still forbidden?
   Answer: Yes. Do not return to local circle/bbox visual patching while the structure layer is being built.

7. Which regions must remain for B-6.2S-2 / S-3 or later real data?
   Answer: Maldives, Bahamas Bank, Tuamotu/French Polynesia, Caribbean reef/bank systems, Hawaii island halos, Great Barrier Reef, narrow Aegean waters, and any production-grade reef/atoll recovery. Global GEBCO or real reef/coastline-derived datasets remain needed for high-confidence reef and bank masks.

## 6. Recommendation

- B-6.2P status: Human/geographic validation passed.
- Proceed to B-6.2S-1: Yes.
- Draft B-6.4 API in parallel: Yes, design-only.
- Integrate with d6 now: No.
- Resume B-5.3: No.
- Commit generated `.npz`, metadata, metrics, or previews: No.
- Next smallest safe action: design B-6.2S-1 named water-only masks for Red Sea, Yellow Sea, East China Sea, Japan Sea, Mediterranean/Aegean, Persian Gulf, North Sea, Baltic Sea, Caribbean, Bahamas, South China Sea, and related regions using the validated P0 land/ocean structure as a base.
