# RDL M2 Coral Atlas Reef Proof — 2026-06-26

Minimal proof for Allen Coral Atlas reef extent rasterization.

No geopandas, rasterio, fiona, pyproj, shapely, or GDAL was used.
The pipeline is `zip/gpkg -> sqlite3 -> GeoPackageBinary/WKB parser -> Pillow mask/preview`.

## Outputs

### maldives

- Package: `Central-Indian-Ocean-20230310001123.zip`
- Features in region bbox: 6541
- Polygons rasterized: 6541
- Reef pixel ratio: 0.020874
- Contact sheet: `docs/preview_archives/rdl_m2_coral_atlas_proof_20260626/maldives_aca_reef_contact_sheet.jpg`
- Preview: `docs/preview_archives/rdl_m2_coral_atlas_proof_20260626/maldives_aca_reef_overlay_preview.jpg`
- Mask: `docs/preview_archives/rdl_m2_coral_atlas_proof_20260626/maldives_aca_reef_mask.png`

### hawaii

- Package: `Hawaiian-Islands-20230309235255.zip`
- Features in region bbox: 1153
- Polygons rasterized: 1153
- Reef pixel ratio: 0.002481
- Contact sheet: `docs/preview_archives/rdl_m2_coral_atlas_proof_20260626/hawaii_aca_reef_contact_sheet.jpg`
- Preview: `docs/preview_archives/rdl_m2_coral_atlas_proof_20260626/hawaii_aca_reef_overlay_preview.jpg`
- Mask: `docs/preview_archives/rdl_m2_coral_atlas_proof_20260626/hawaii_aca_reef_mask.png`

## Notes

- This proof uses reef extent only. Benthic and geomorphic classes are intentionally deferred because their GeoPackages are much larger.
- Reef extent should be treated as a shallow-water detail mask, not as a full color replacement layer.
- The next production step is to feed this mask into the RDL compositor with depth-gated, feathered color treatment.
