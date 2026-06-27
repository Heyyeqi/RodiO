# RDL M3/M4 Region Sampler — 2026-06-26

## Scope

This report samples existing 8K categorical rasters for all RDL regions:

- M3 ESA WorldCover land-cover classes
- M4 Koppen-Geiger 1991-2020 climate classes

No texture, mask, source raster, runtime code, git staging, or deployment was changed.

Full outputs:

- `m3_m4_region_histograms.json`
- `m3_m4_region_summary.csv`
- `m3_m4_visual_hints.json`

## High-Priority Region Snapshot

| Region | WorldCover top land | WC family | Water % | Koppen top | Climate family | Climate land % |
|---|---|---|---:|---|---|---:|
| caribbean_bahamas | 10 Tree cover | vegetated | 29.19 | 3 Aw - Tropical savannah | tropical | 13.36 |
| great_barrier_reef | 10 Tree cover | vegetated | 15.25 | 6 BSh - Arid steppe hot | arid | 37.88 |
| hawaii | 10 Tree cover | vegetated | 14.30 | 15 Cfb | temperate | 3.78 |
| indonesia_east | 10 Tree cover | vegetated | 38.57 | 1 Af - Tropical rainforest | tropical | 17.27 |
| maldives | - None | None | 30.74 | 1 Af - Tropical rainforest | tropical | 0.08 |
| philippines_central | 10 Tree cover | vegetated | 31.84 | 1 Af - Tropical rainforest | tropical | 19.87 |
| ryukyu | 10 Tree cover | vegetated | 14.80 | 14 Cfa | temperate | 0.53 |
| south_china_sea | 10 Tree cover | vegetated | 13.96 | 3 Aw - Tropical savannah | tropical | 7.51 |

## Family Counts

Koppen top-family counts:

- `arid`: 10
- `cold`: 8
- `none`: 1
- `polar`: 3
- `temperate`: 18
- `tropical`: 44

WorldCover top-land-family counts:

- `bare`: 4
- `ice`: 2
- `none`: 6
- `vegetated`: 72

## Interpretation

- M3 can now use the WorldCover histogram to bias land-only visual treatment per region.
- M4 can now use the Koppen histogram to choose region-level Noon Air baseline parameters.
- These summaries are review inputs only; they do not yet change compositing behavior.
- `m3_m4_visual_hints.json` is a conservative parameter sketch, not an applied config.
