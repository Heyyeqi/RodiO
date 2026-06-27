# B-6.2X-D3-S-EXT-C1-X — Cross-Layer Consistency Audit

Stage: B-6.2X-D3-S-EXT-C1-X  
Type: Semantic cross-layer validation  
Status: **CONDITIONAL_PASS**  
Date: 2026-06-24  
Tools: tifffile 2026.6.1 + imagecodecs + numpy 2.5.0  

---

## 1. Scope

This audit validates the completed Köppen-Geiger 1991-2020 8K climate layer against existing 8K land-cover, elevation, and surface-water evidence.

Boundary followed:

- No masks generated.
- No resampling performed.
- No GeoTIFFs modified.
- No generator or d6 scripts run.
- No production, pwa, candidates, or source_cache writes.
- No downloads, moves, deletes, commits, or pushes.

Only the report file was generated from read-only raster statistics.

---

## 2. Input Layers

| Layer | Resolved input path | Shape | dtype | Metadata notes |
|---|---|---:|---|---|
| Köppen-Geiger 1991-2020 | `d5b_processor_v3/source_cache/gee_global/external_processed_8k/koppen_geiger_1991_2020_8192x4096.tif` | 4096 x 8192 | uint8 | LZW, origin (-180, 90), scale 0.0439453125 deg, no explicit nodata; class 0 treated as ocean/unclassified |
| ESA WorldCover 2021 v200 | `d5b_processor_v3/source_cache/gee_global/exported_8k/esa_worldcover_2021_v200_map_8192x4096.tif` | 4096 x 8192 | uint8 | LZW, origin (-180, 90), scale 0.0439453125 deg |
| MERIT DEM v1.0.3 elevation | `d5b_processor_v3/source_cache/gee_global/supplemental_8k/merit_dem_v1_0_3_elevation_8192x4096.tif` | 4096 x 8192 | int16 | LZW, nodata -32768, origin (-180, 89.999), Y scale 0.04394482421875 deg |
| JRC GSW occurrence | `d5b_processor_v3/source_cache/gee_global/exported_8k/jrc_gsw_occurrence_8192x4096.tif` | 4096 x 8192 | uint8 | LZW, origin (-180, 90), scale 0.0439453125 deg |
| JRC GSW max extent | `d5b_processor_v3/source_cache/gee_global/exported_8k/jrc_gsw_max_extent_8192x4096.tif` | 4096 x 8192 | uint8 | LZW, origin (-180, 90), scale 0.0439453125 deg |

The requested relative `external_processed_8k/...` file was resolved under the existing local source cache. No file was copied or moved.

---

## 3. Method

Arrays were read directly with `tifffile.imread()`. All statistics are full-raster statistics over the existing 8192 x 4096 pixels.

WorldCover analysis denominator:

- Köppen class > 0.
- ESA class > 0 and ESA class != 80.

WorldCover mismatch rules:

- `desert_vs_vegetation`: Köppen BWh/BWk (`4,5`) overlapping ESA tree, wetland, mangrove, or moss/lichen (`10,90,95,100`).
- `tropical_forest_vs_climate`: Köppen Af/Am (`1,2`) not overlapping ESA tree, mangrove, or wetland (`10,95,90`).
- `cropland_vs_arid`: ESA cropland (`40`) overlapping Köppen BWh/BWk (`4,5`).

DEM analysis denominator:

- Köppen class > 0.
- ESA land class, excluding ESA water.
- DEM finite and between -500 m and 9000 m.

DEM anomaly rules:

- `high_altitude_tropical`: Köppen Af/Am/Aw (`1,2,3`) at elevation >= 3000 m.
- `polar_elevation_sanity`: EF low non-snow/non-moss pixels below 500 m, plus ET low tree/cropland/built pixels below 500 m.
- `alpine_boundary`: elevation >= 3500 m outside the cold/polar/alpine-adjacent climate set (`7,16,17,18,22,23,24,25,26,27,28,29,30`).

Water analysis:

- ESA class `0` is treated as ocean/no-data proxy only with caveat. Because global ESA 0 includes Antarctic and high-latitude no-data/ice regions, the primary ocean sanity check uses ESA 0 with latitude > -60.
- JRC GSW is used as surface-water corroboration, not as an ocean mask.

Top inconsistent regions are reported as 5 degree latitude/longitude bins ranked by inconsistent pixel count.

---

## 4. Köppen vs WorldCover

| Metric | Value |
|---|---:|
| Analysis land pixels | 7,751,962 |
| Union mismatch pixels | 84,777 |
| Mismatch ratio | **1.094%** |
| desert_vs_vegetation pixels | 4,758 |
| tropical_forest_vs_climate pixels | 44,745 |
| cropland_vs_arid pixels | 35,274 |

Top 10 inconsistent 5 degree regions:

| Rank | Lat range | Lon range | Mismatch pixels | Region ratio | Dominant check |
|---:|---|---|---:|---:|---|
| 1 | 25 to 30 | 70 to 75 | 5,518 | 41.797% | cropland_vs_arid |
| 2 | 0 to 5 | -75 to -70 | 3,610 | 27.543% | tropical_forest_vs_climate |
| 3 | 5 to 10 | -75 to -70 | 3,594 | 28.246% | tropical_forest_vs_climate |
| 4 | 30 to 35 | 70 to 75 | 3,098 | 23.570% | cropland_vs_arid |
| 5 | 25 to 30 | 65 to 70 | 2,961 | 23.407% | cropland_vs_arid |
| 6 | -25 to -20 | -55 to -50 | 2,622 | 20.512% | tropical_forest_vs_climate |
| 7 | 10 to 15 | 30 to 35 | 2,109 | 16.049% | cropland_vs_arid |
| 8 | -5 to 0 | -50 to -45 | 2,063 | 19.235% | tropical_forest_vs_climate |
| 9 | 5 to 10 | -70 to -65 | 1,855 | 14.275% | tropical_forest_vs_climate |
| 10 | 30 to 35 | 45 to 50 | 1,835 | 14.375% | cropland_vs_arid |

Interpretation:

- Global mismatch is low at 1.094%.
- The largest arid/cropland bins are geographically plausible irrigated or transitional dryland agriculture regions rather than obvious global-layer failure.
- Tropical mismatch bins cluster around Amazon/Andean edge regions where 8K nearest-class climate, land-cover year, and mountain/forest transitions can legitimately diverge.

---

## 5. Köppen vs DEM

| Metric | Value |
|---|---:|
| Analysis land pixels | 7,751,772 |
| Union anomaly pixels | 19,570 |
| DEM mismatch/anomaly ratio | **0.252%** |
| high_altitude_tropical pixels | 0 |
| polar_elevation_sanity pixels | 2,622 |
| alpine_boundary pixels | 16,948 |

Elevation-class sample statistics:

| Köppen class | Pixels | Mean elevation | Median elevation | P90 | P99 |
|---:|---:|---:|---:|---:|---:|
| 1 Af | 280,831 | 268 m | 141 m | 726 m | 1,400 m |
| 3 Aw | 753,789 | 467 m | 390 m | 1,043 m | 1,556 m |
| 4 BWh | 990,269 | 477 m | 404 m | 968 m | 1,541 m |
| 5 BWk | 271,876 | 1,177 m | 1,097 m | 2,574 m | 4,577 m |
| 7 BSk | 400,003 | 1,064 m | 930 m | 2,070 m | 4,453 m |
| 27 Dfc | 1,296,419 | 380 m | 271 m | 813 m | 2,237 m |
| 29 ET | 623,466 | 1,308 m | 455 m | 4,661 m | 5,437 m |
| 30 EF | 278,524 | 2,069 m | 2,125 m | 2,904 m | 3,200 m |

Top DEM anomaly zones:

| Rank | Lat range | Lon range | Anomaly pixels | Region ratio | Dominant check |
|---:|---|---|---:|---:|---|
| 1 | -25 to -20 | -70 to -65 | 5,780 | 44.520% | alpine_boundary |
| 2 | -30 to -25 | -70 to -65 | 3,019 | 23.049% | alpine_boundary |
| 3 | -20 to -15 | -70 to -65 | 1,884 | 14.797% | alpine_boundary |
| 4 | 30 to 35 | 80 to 85 | 1,827 | 14.173% | alpine_boundary |
| 5 | -55 to -50 | -75 to -70 | 896 | 12.048% | polar_elevation_sanity |
| 6 | 35 to 40 | 70 to 75 | 753 | 5.718% | alpine_boundary |
| 7 | 35 to 40 | 90 to 95 | 696 | 5.397% | alpine_boundary |
| 8 | -55 to -50 | -70 to -65 | 683 | 16.200% | polar_elevation_sanity |
| 9 | 30 to 35 | 75 to 80 | 606 | 4.609% | alpine_boundary |
| 10 | 35 to 40 | 75 to 80 | 535 | 4.059% | alpine_boundary |

Interpretation:

- No high-altitude tropical mismatch was detected under the >= 3000 m rule.
- Alpine-boundary anomalies are concentrated in Andes/Himalaya-style high-relief transition zones and are small globally.
- DEM metadata is not perfectly identical to the Köppen/ESA grid: MERIT DEM reports origin Y 89.999 and Y scale 0.04394482421875. Since no resampling is allowed in this audit, statistics are array-index aligned and this metadata offset remains a condition.

---

## 6. Köppen vs Water

| Metric | Value |
|---|---:|
| ESA 0 ocean/no-data proxy pixels with latitude > -60 | 18,812,490 |
| Köppen land-class pixels on bounded ocean proxy | 9,048 |
| Ocean misclassification ratio | **0.048%** |
| ESA water class 80 pixels | 1,361,700 |
| ESA water class 80 also present in JRC water evidence | 982,501 |
| ESA water/JRC overlap share of ESA water | 72.153% |
| ESA water class 80 with Köppen land climate | 226,574 |

Interpretation:

- No material ocean misclassification was detected with the bounded ESA0 ocean proxy.
- ESA 0 cannot be used globally as a pure ocean mask because it includes Antarctic/high-latitude no-data or ice-edge regions; a global unbounded ESA0 check would incorrectly flag Antarctic EF land as ocean inconsistency.
- JRC GSW exists and corroborates most ESA water class 80 pixels, but it is not a clean ocean mask and was not used to invalidate climate classes over open ocean.

---

## 7. Global Consistency Score

Weighted score:

```
100 - (0.45 * WorldCover mismatch %)
    - (0.35 * DEM anomaly %)
    - (0.20 * bounded ocean misclassification %)
```

| Component | Ratio |
|---|---:|
| Köppen vs WorldCover | 1.094% |
| Köppen vs DEM | 0.252% |
| Köppen vs bounded ocean proxy | 0.048% |
| Global consistency score | **99.410 / 100** |

---

## 8. Critical Issues (if any)

No critical semantic inconsistency was found.

Non-critical conditions:

- MERIT DEM metadata is slightly offset from the Köppen/ESA grid even though array shapes match.
- Ocean detection is proxy-based because no dedicated ocean mask was provided; ESA 0 needs latitude guarding to avoid Antarctic false positives.
- Top mismatch bins should be treated as review targets if future semantic masks depend on strict arid/tropical/alpine boundaries, but they do not indicate that the Köppen layer is globally invalid.

---

## 9. Verdict

```
conditional_pass
```

The Köppen-Geiger 8K layer is semantically consistent enough to proceed as a source layer for later review-gated derivation work. The verdict is conditional, not fail, because global mismatch rates are low and no critical cross-layer inconsistency was found. The condition is that future work must account for the MERIT DEM metadata offset and must not treat ESA 0 or JRC GSW as a perfect ocean mask without an explicit ocean-layer decision.

---

*Audit executed: 2026-06-24*  
*No masks generated. No rasters modified. No generator/d6 run. No source_cache writes.*
