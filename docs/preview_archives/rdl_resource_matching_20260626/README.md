# RDL Resource Matching Snapshot — 2026-06-26

## Scope

This is a resource matching snapshot for the next RDL regional-detail stages after M0/M1 acceptance.

No generator was run. No ZIP was extracted. No Coral Atlas vector layer was rasterized. No runtime, source data, git staging, or Railway deployment was changed.

## Layer Status

| Layer | Data | Current Format | Current Status | Can Start Now |
|---|---|---|---|---|
| M0 | Mapbox regional base | regional JPG outputs + tile cache | 84/84 local outputs complete | Yes |
| M1 | GEBCO depth | 8 quadrant GeoTIFFs | integrated in `rdl_mapbox_poc.py`; 84/84 enhanced outputs complete | Yes |
| M2 | Allen Coral Atlas | ZIP packages containing `.gpkg` vector layers | raw packages available; only 1 package extracted | No, dependency blocked |
| M3 | ESA WorldCover | global 8192x4096 TIFF | available | Yes, with crop/sampling adapter |
| M4 | Koppen-Geiger | processed global 8192x4096 TIFF + raw ZIPs | available | Yes, with region sampler |
| Supplemental | JRC GSW / MODIS | global 8192x4096 TIFFs | available, lower priority | Later |

Full machine-readable details are in `resource_matching.json`.

## Key Counts

| Item | Count |
|---|---:|
| RDL regions in `rdl_mapbox_poc.py` | 84 |
| M0 `tile_mapbox.jpg` outputs | 84 |
| M1 `tile_noon_air_mapbox.jpg` outputs | 84 |
| Coral Atlas ZIP files | 30 |
| Unique Coral Atlas package prefixes | 29 |
| Extracted Coral Atlas packages | 1 |
| RDL regions with Coral Atlas candidate packages | 34 |
| GEBCO quadrant TIFFs | 8 |

## Current Practical Path

### Next easiest data layers

M3 WorldCover and M4 Koppen are currently easier than M2 Coral Atlas:

- both already have global 8K TIFF products;
- they can be sampled/cropped with `numpy` + `tifffile`, which are already installed;
- they do not require vector GIS dependencies.

Recommended next implementation slice:

1. Build a read-only region sampler for WorldCover and Koppen.
2. Produce per-region class histograms for the 84 RDL regions.
3. Convert the histograms into non-destructive visual hints only:
   - M3 land ecological color bias;
   - M4 region-level Noon Air baseline.

### Coral Atlas remains separate

M2 should stay separate because current local Python is missing:

- `rasterio`
- `fiona`
- `geopandas`
- `shapely`
- `pyproj`

GDAL command-line tools are also not available:

- `ogrinfo`
- `gdalinfo`
- `gdal_rasterize`

So the first M2 task should be dependency/bootstrap plus a tiny one-package rasterization proof, not full production compositing.

## Coral Atlas Candidate Matches

The 34 Coral Atlas matches in `resource_matching.json` are curated candidates, not final validation. They are useful for planning package extraction order, but M2 still needs real vector-layer bbox/class validation before compositing.

High-priority M2 package order:

1. `Hawaiian-Islands`
2. `Central-Indian-Ocean`
3. `Great-Barrier-Reef-and-Torres-Strait`
4. `Philippines`
5. `Northern-Caribbean--Florida---Bahamas`
6. `South-China-Sea`
7. `Northeastern-Asia`
8. `Southeast-Asian-Archipelago`
9. `Timor---Arafura-Seas`

## Deployment Note

This snapshot does not change the deployment conclusion from M0/M1 acceptance:

RDL visual outputs are locally complete, but the source-cache-backed assets are not automatically included by normal git staging. Deployment still needs a deliberate asset strategy before commit/push/Railway.
