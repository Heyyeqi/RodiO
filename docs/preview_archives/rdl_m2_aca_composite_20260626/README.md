# RDL M2 ACA Reef Composite Candidate — 2026-06-26

This is the first natural-composite candidate using Allen Coral Atlas reef extent.

## Region

- Region: `maldives`
- Source package: `Central-Indian-Ocean-20230310001123.zip`
- Features in bbox: 6,541
- Polygons rasterized: 6,541
- Parse errors: 0
- Reef pixel ratio: 0.020874

## Outputs

- Candidate tile: `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/maldives/tile_noon_air_mapbox_aca_reef.jpg`
- Mask: `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/maldives/aca_reef_mask.png`
- Contact sheet: `docs/preview_archives/rdl_m2_aca_composite_20260626/maldives_m2_aca_reef_candidate_contact_sheet.jpg`
- Summary JSON: `docs/preview_archives/rdl_m2_aca_composite_20260626/maldives_m2_aca_reef_candidate_summary.json`

## Method

No geopandas, rasterio, fiona, pyproj, shapely, or GDAL was used. The path is `sqlite3 + GeoPackageBinary/WKB parser + Pillow`.

This candidate uses a feathered reef-mask blend. Because the active `.venv` is intentionally minimal and has no `tifffile`, this run did not use GEBCO depth gating. A future refinement can add depth gating without changing the Coral Atlas reader.

## Status

Review candidate only. Not wired into `earth3d.js`, not deployed, and not a replacement for the accepted M0/M1 tile.
