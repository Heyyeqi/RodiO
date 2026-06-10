# Phase B-6.2G-2A Terrain / Relief Feasibility Audit

Date: 2026-06-10

Scope: asset and feasibility audit only. This document does not modify code, does not regenerate masks, does not run `scripts/generate_b6_structure_masks.py`, does not run d6, does not write to `pwa`, `production`, or `candidates`, and does not commit or push.

## 1. Current Terrain Capability

Current terrain-related masks:

- `mountain_mask`
- `plateau_mask`

Current implementation in `scripts/generate_b6_structure_masks.py`:

```text
mountain_mask = ETOPO1 z > 1500 AND land
plateau_mask  = ETOPO1 500 < z <= 1500 AND land
```

Current metrics from generated B-6 output:

| Mask | Pixel Count | Coverage | Mean |
| ---- | ----------: | -------: | ---: |
| `mountain_mask` | 207,180 | 0.098791 | 0.10034 |
| `plateau_mask` | 166,241 | 0.079270 | 0.08080 |

Assessment:

- `mountain_mask` is a coarse high-elevation selector, not a mountain morphology mask.
- `plateau_mask` is a mid-elevation band selector, not a refined plateau semantic mask.
- Neither mask uses slope, local relief, curvature, basin context, relative elevation, landform shape, island context, or regional landform metadata.
- These masks are useful as early structure selectors for broad Noon Air land color protection, but they are not enough for future map generation where mountains, plateaus, basins, plains, hills, volcanic islands, and rift valleys should be treated differently.

Current limitations:

- High plateaus above 1500m can be classified as mountain instead of plateau.
- Low but rugged mountains can be missed.
- Elevated deserts and basins can be misread as plateau.
- Plains, basins, valleys, hills, escarpments, and volcanic islands are not represented.
- No terrain mask currently excludes inland water; terrain masks should not drive lake coloring.

## 2. Terrain / Relief / Landform Gap Audit

| Proposed Mask | ETOPO1 Support | Needs Slope / Relief / Curvature? | Needs Higher DEM? | Proxy Only? | Suitable for B-6.2G-2B? | Notes |
| ------------- | -------------- | ---------------------------------- | ----------------- | ----------- | ------------------------ | ----- |
| `high_mountain_mask` | Yes | Optional for refinement | No for 2K prototype | No, if clearly elevation-thresholded | Yes | Draft threshold: `z > 3000m AND land`, excluding lakes. |
| `refined_mountain_mask` | Partial | Yes | Better with higher DEM | Yes at 2K | Conditional | Combine elevation > 1500m with local relief. |
| `plateau_refined_mask` | Partial | Yes, low local relief needed | Better with higher DEM | Yes | Yes, as proxy | Must separate Tibet/Iran/Anatolia from rugged mountain ranges. |
| `hill_mask` | Partial | Yes | Better with higher DEM | Yes | Conditional | Local relief band, not raw elevation. |
| `basin_mask` | Partial | Yes | Better with hydrology/DEM | Yes | Yes, as `lowland_or_basin_proxy` | Needs low relief + inland depression / surrounding highlands. |
| `lowland_plain_mask` | Partial | Yes | No for coarse prototype | Yes | Yes, as part of lowland proxy | Elevation < 300/500m + low relief + land. |
| `valley_or_lowland_mask` | Partial | Yes | Better with drainage data | Yes | Deferred | Hard to separate valley vs plain with ETOPO1 alone. |
| `coastal_plain_mask` | Partial | Yes | Better with coast distance | Yes | Deferred | Needs coastline distance + low elevation + low relief. |
| `escarpment_proxy` | Partial | Yes, gradient essential | Better with higher DEM | Yes | Deferred | Slope edge detection at 2K can be noisy. |
| `rift_valley_proxy` | Partial | Yes, named region likely needed | Yes for robust | Yes | Deferred | Great Rift Valley should not be inferred by threshold only. |
| `volcanic_island_mask` | Partial | Yes + island components | Better with island data | Yes | Deferred | Requires small island / island relief stage. |
| `island_relief_mask` | Partial | Yes + GSHHG components | Better with higher DEM | Yes | Deferred | Belongs with island/reef/bank phase or later terrain+island fusion. |
| `dry_basin_proxy` | Partial | Yes + aridity data | Better with land cover/aridity | Yes | Deferred | Do not mix with desert/arid phase yet. |

Feasibility conclusion:

- ETOPO1 can support a minimal 2K terrain prototype.
- ETOPO1 alone cannot support full geomorphology.
- B-6.2G-2B should be explicitly labeled as coarse terrain proxy, not final landform truth.

## 3. Key Region Audit

| Region | Should Be Recognized? | Current Mountain / Plateau Coverage | Needs Refined Terrain? | B-6.2G-2C Validation Use |
| ------ | --------------------- | ----------------------------------- | ---------------------- | ------------------------ |
| Himalaya | Yes, high mountain | Covered by `mountain_mask`, but not separated as high mountain/glacier terrain | Yes | Hard validation for `high_mountain_mask`. |
| Tibetan Plateau | Yes, high plateau | Mostly `mountain_mask` due elevation >1500m; plateau semantics weak | Yes | Hard validation for `plateau_refined_mask`. |
| Andes | Yes, mountain chain + plateau segments | Broadly mountain | Yes | Hard validation for mountain continuity and high plateau edges. |
| Rockies | Yes, rugged mountain | Broadly mountain | Yes | Mountain validation; ensure plains not over-included. |
| Alps | Yes, mountain | Covered but small at 2K | Yes | Small-region mountain validation. |
| Ethiopian Highlands | Yes, highland/plateau | Likely mountain/plateau mix | Yes | Plateau/highland validation. |
| East African Rift | Yes, rift/valley | Not reliably represented | Yes, but defer true rift | Soft validation for basin/relief proxy only. |
| Iranian Plateau | Yes, plateau/dry highland | Mix of mountain/plateau | Yes | Plateau_refined validation. |
| Anatolian Plateau | Yes, plateau | Mix of mountain/plateau | Yes | Plateau_refined validation. |
| Deccan Plateau | Yes, plateau | May be plateau/lowland depending threshold | Yes | Plateau_refined watchlist. |
| Great Rift Valley | Yes, rift valley | Not represented as rift | Yes, deferred | Validation later, not B-6.2G-2B hard target. |
| Hawaii / volcanic island chains | Yes, volcanic islands | Not reliable at 2K/Etopo coarse | Yes, deferred | Requires island component stage. |
| Japan mountain arcs | Yes, mountain arcs | Partially covered | Yes | Regional validation with Japan GEBCO/terrain benchmark if useful. |
| Indonesia volcanic arcs | Yes, volcanic island arcs | Not reliable globally | Yes, deferred | Island + relief fusion later. |
| New Zealand Alps | Yes, mountain | Likely covered but small/narrow | Yes | Mountain watchlist. |
| Central Asian basins | Yes, basin/lowland | Not represented | Yes | Basin/lowland validation. |
| Amazon Basin | Yes, lowland basin | Mostly neither mountain nor plateau | Yes | Lowland/basin proxy validation. |
| Congo Basin | Yes, lowland basin | Mostly lowland, may be unclassified | Yes | Lowland/basin proxy validation. |
| North China Plain | Yes, lowland plain | Mostly unclassified lowland | Yes | Lowland plain validation. |
| European Plain | Yes, lowland plain | Mostly unclassified lowland | Yes | Lowland plain validation. |
| Mississippi Basin | Yes, basin/plain | Mostly unclassified lowland | Yes | Lowland/basin proxy validation. |
| Sichuan Basin | Yes, enclosed basin | Not represented as basin | Yes | Basin proxy validation. |
| Tarim Basin | Yes, dry basin | Not represented as basin; may be plateau/lowland mix | Yes | Basin proxy + later arid phase validation. |

Key-region conclusion:

- Current masks are sufficient to identify many highlands in a broad sense.
- They are not sufficient to distinguish terrain forms.
- B-6.2G-2C should use both hard high-mountain/plateau validation regions and soft basin/lowland watchlist regions.

## 4. Data Source Capability Audit

| Data Source | Available? | Supports | Cannot Support | Suitable Phase | Risk |
| ----------- | ---------- | -------- | -------------- | -------------- | ---- |
| ETOPO1 Ice Surface | Yes: `pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd` | 2K coarse elevation, high mountain, elevation bands, lowland proxy, local relief if computed from downsampled grid | Fine landforms, reliable volcanic islands, cliffs, detailed slope/aspect, glacier truth | B-6.2G-2B | 1 arc-min source but 2K output smooths relief; ice surface not bedrock. |
| Existing `mountain_mask` logic | Yes | Coarse high elevation selector | Terrain morphology | Current baseline / B-6.2G-2 comparison | Threshold-only. |
| Existing `plateau_mask` logic | Yes | Coarse mid-elevation selector | True plateau semantics | Current baseline / B-6.2G-2 comparison | Misclassifies elevated plains, misses high plateaus. |
| GEBCO Japan subset | Yes: `pwa/assets/source/bathy/gebco_2026/gebco_2026_118_150_22_50.nc` | Regional Japan benchmark, coastal/mountain context around Japan | Global terrain foundation | Regional validation only | Not global. |
| `dem/copernicus_glo30` directory | Present but empty | Nothing currently | High-resolution DEM, detailed slope, landform classes | Deferred | Placeholder only. |
| Current day texture color | Yes | Visual review and sanity comparison | Terrain semantic truth | Review only | Color confounds terrain with biome/desert/snow/cloud. |
| RDL / bathy preview assets | Present | Regional reference and existing processing patterns | Global terrain data | Reference only | Outputs/previews are not source datasets. |

Answers:

- ETOPO1 is sufficient for a 2K coarse terrain prototype.
- ETOPO1 can support high mountain, coarse plateau, lowland/basin proxies, and local relief estimates.
- ETOPO1 can compute slope/local relief/elevation range at 2K, but results must be labeled proxy.
- The repository currently lacks a usable global high-resolution DEM.
- `dem/copernicus_glo30` is empty and not usable.
- GEBCO Japan subset is regional, not global.
- Current day texture color must not be used as terrain semantic truth.

## 5. Proposed B-6.2G-2B Minimal Terrain Prototype Scope

Recommended allowed masks:

1. `high_mountain_mask`
   - Method: `ETOPO1 z > 3000m AND land AND NOT inland_water`.
   - Rationale: stable, simple, useful for Himalaya/Tibet/Andes/Rockies.

2. `plateau_refined_mask`
   - Method: high elevation plus low local relief; draft thresholds must be documented.
   - Rationale: separates true broad elevated regions from rugged high mountains.

3. `lowland_or_basin_proxy`
   - Method: low elevation + low local relief + land, optionally excluding coastline band.
   - Rationale: supports Amazon/Congo/North China/European/Mississippi basins and plains as a proxy.

4. `hill_or_relief_proxy`
   - Method: moderate elevation/local relief band.
   - Rationale: fills the semantic gap between lowland and mountains.

Temporarily forbidden in B-6.2G-2B:

- full geomorphon classification
- true volcanic island mask
- true rift valley mask
- true escarpment mask
- detailed slope/aspect layer
- biome / desert / glacier / reef / river masks

Reason:

- These require either better DEM, named-region validation, island components, hydrology, land cover, or specialized terrain classifiers.
- Hard-coding them now would pollute the structure layer with overconfident proxies.

## 6. Interaction With Lake Masks

Rules for future terrain masks:

- Terrain masks should not cover inland water as final terrain color selectors.
- Lake masks should have higher priority than terrain masks for color application.
- `high_mountain_mask`, `plateau_refined_mask`, `hill_or_relief_proxy`, and `lowland_or_basin_proxy` should exclude `inland_water_mask`.
- Basin/lowland masks may coexist with lake proximity as context, but not overwrite lake water.
- API must support mask groups and priority:
  - `water.inland` overrides `terrain.*` for visual color.
  - `terrain.*` may provide surrounding context around lakes.
  - `landform.proxy` must be marked as proxy, not physical truth.

## 7. API / d6 Boundary

- B-6.2G-2A is feasibility audit only.
- d6 integration remains forbidden.
- visual rebuild remains forbidden.
- B-6.4 API can continue as draft, but must not freeze.
- terrain masks must pass B-6.2G-2C validation before d6 discussion.
- color grading / 上色 must not start.

## 8. Final Recommendation

| Question | Answer |
| -------- | ------ |
| Is current terrain / relief layer sufficient? | No |
| Can ETOPO1 support minimal terrain prototype? | Yes, conditionally, as a coarse 2K proxy |
| Should B-6.2G-2B start after this audit? | Yes, conditional on strict minimal scope |
| Recommended masks for B-6.2G-2B | `high_mountain_mask`, `plateau_refined_mask`, `lowland_or_basin_proxy`, `hill_or_relief_proxy` |
| Masks that must be deferred | true volcanic island, rift valley, escarpment, geomorphon, detailed slope/aspect, biome, desert, glacier, reef, river masks |
| Required validation regions for B-6.2G-2C | Himalaya, Tibetan Plateau, Andes, Rockies, Alps, Ethiopian Highlands, Iranian Plateau, Anatolian Plateau, Deccan Plateau, Amazon Basin, Congo Basin, North China Plain, European Plain, Mississippi Basin, Sichuan Basin, Tarim Basin, Japan mountain arcs, New Zealand Alps |
| Can d6 be touched? | No |
| Can visual rebuild / 上色 start? | No |
| Is git state safe? | Conditional: existing d6/devlog/generator changes must remain isolated and reviewed separately |

## 9. Next Step

Proceed to B-6.2G-2B only as a minimal terrain prototype, with no d6, no pwa, no production/candidates, no visual rebuild, and no generated output commits. Follow immediately with B-6.2G-2C terrain validation.
