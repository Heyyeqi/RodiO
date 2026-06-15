// B-6.2X-D2 — GEE Export Script Draft: Phase 1 Core Sources @ 8192x4096
// Stage: B-6.2X-D2
// Date: 2026-06-15
// Status: DRAFT — review only. Do not run without RW authorization.
//         This script has NOT been executed. No exports have been submitted.
//
// HOW TO USE:
//   1. Copy this file into the GEE Code Editor at https://code.earthengine.google.com
//   2. Read all comments and review each Export.image.toDrive() call.
//   3. To submit a task, UNCOMMENT the call to definePhase1Exports() at the
//      bottom of this file ONLY after RW authorization.
//   4. After running, go to the Tasks tab and click RUN on each listed task.
//   5. Do NOT call task.start() programmatically — start tasks manually only.
//
// Expected output resolution: 8192 x 4096 pixels, EPSG:4326 equirectangular.
// Pixel dimensions are controlled by the 'dimensions' parameter (not 'scale').
// SCALE_8K is kept below as a reference comment only — it is not used as the
// primary size-control field in any Export call.

// ---------------------------------------------------------------------------
// CONFIGURATION
// ---------------------------------------------------------------------------

var DRIVE_FOLDER = 'RodiO_GEE_Cache_Phase1';
var CRS = 'EPSG:4326';
var REGION = ee.Geometry.Rectangle([-180, -90, 180, 90], 'EPSG:4326', false);
var DIMENSIONS_8K = '8192x4096';
var MAX_PIXELS_8K = 1e10;
var FORMAT = 'GeoTIFF';

// Reference scale (informational only — not used in Export calls):
// At the equator, 8192x4096 in EPSG:4326 ≈ 4891 m/px.
// var SCALE_8K = 4891;  // reference only

// ---------------------------------------------------------------------------
// PHASE 1 EXPORT DEFINITIONS
// All Export.image.toDrive() calls are wrapped in definePhase1Exports().
// This function is NOT called automatically. Call it only after RW authorization.
// ---------------------------------------------------------------------------

function definePhase1Exports() {

  // -------------------------------------------------------------------------
  // BATCH 1 — ESA WorldCover 2021 v200
  // dataset: ESA/WorldCover/v200
  // band:    Map (uint8, 11 land-cover classes)
  // license: CC-BY-4.0 (commercial_clearance: pending_review)
  // -------------------------------------------------------------------------

  var esaWC = ee.ImageCollection('ESA/WorldCover/v200').mosaic().select('Map');

  Export.image.toDrive({
    image: esaWC,
    description: 'esa_worldcover_2021_v200_map_8192x4096',
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'esa_worldcover_2021_v200_map_8192x4096',
    dimensions: DIMENSIONS_8K,
    crs: CRS,
    region: REGION,
    maxPixels: MAX_PIXELS_8K,
    fileFormat: FORMAT
  });
  // Expected local path: exported_8k/esa_worldcover_2021_v200_map_8192x4096.tif
  // Downstream masks: forest, shrubland, grassland, cropland, builtup,
  //   bare_sparse_land, snow_ice, permanent_water, wetland, mangrove, moss_lichen


  // -------------------------------------------------------------------------
  // BATCH 2 — JRC Global Surface Water v1.4
  // dataset: JRC/GSW1_4/GlobalSurfaceWater
  // bands:   occurrence, seasonality, recurrence, max_extent
  // license: CC-BY-4.0 (commercial_clearance: pending_review)
  // Note:    Each band is a separate Export task.
  // -------------------------------------------------------------------------

  var jrcGSW = ee.Image('JRC/GSW1_4/GlobalSurfaceWater');

  Export.image.toDrive({
    image: jrcGSW.select('occurrence'),
    description: 'jrc_gsw_occurrence_8192x4096',
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'jrc_gsw_occurrence_8192x4096',
    dimensions: DIMENSIONS_8K,
    crs: CRS,
    region: REGION,
    maxPixels: MAX_PIXELS_8K,
    fileFormat: FORMAT
  });
  // Expected local path: exported_8k/jrc_gsw_occurrence_8192x4096.tif
  // Values: 0–100 (percentage of time water present), uint8

  Export.image.toDrive({
    image: jrcGSW.select('seasonality'),
    description: 'jrc_gsw_seasonality_8192x4096',
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'jrc_gsw_seasonality_8192x4096',
    dimensions: DIMENSIONS_8K,
    crs: CRS,
    region: REGION,
    maxPixels: MAX_PIXELS_8K,
    fileFormat: FORMAT
  });
  // Expected local path: exported_8k/jrc_gsw_seasonality_8192x4096.tif
  // Values: 0–12 (months per year water present), uint8

  Export.image.toDrive({
    image: jrcGSW.select('recurrence'),
    description: 'jrc_gsw_recurrence_8192x4096',
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'jrc_gsw_recurrence_8192x4096',
    dimensions: DIMENSIONS_8K,
    crs: CRS,
    region: REGION,
    maxPixels: MAX_PIXELS_8K,
    fileFormat: FORMAT
  });
  // Expected local path: exported_8k/jrc_gsw_recurrence_8192x4096.tif
  // Values: 0–100, uint8

  Export.image.toDrive({
    image: jrcGSW.select('max_extent'),
    description: 'jrc_gsw_max_extent_8192x4096',
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'jrc_gsw_max_extent_8192x4096',
    dimensions: DIMENSIONS_8K,
    crs: CRS,
    region: REGION,
    maxPixels: MAX_PIXELS_8K,
    fileFormat: FORMAT
  });
  // Expected local path: exported_8k/jrc_gsw_max_extent_8192x4096.tif
  // Values: 0/1 binary mask, uint8


  // -------------------------------------------------------------------------
  // BATCH 3 — Copernicus DEM GLO-30
  // dataset: COPERNICUS/DEM/GLO30
  // band:    DEM (float32, meters, DSM — not bare-earth DTM)
  // derived: slope and relief computed in GEE before export
  // license: Copernicus Open Access Hub Terms (commercial_clearance: pending_review;
  //          country exceptions apply — see GEE catalog)
  // -------------------------------------------------------------------------

  var copDEM = ee.ImageCollection('COPERNICUS/DEM/GLO30')
                 .select('DEM')
                 .mosaic();

  // Elevation (raw DSM)
  Export.image.toDrive({
    image: copDEM,
    description: 'copernicus_dem_glo30_elevation_8192x4096',
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'copernicus_dem_glo30_elevation_8192x4096',
    dimensions: DIMENSIONS_8K,
    crs: CRS,
    region: REGION,
    maxPixels: MAX_PIXELS_8K,
    fileFormat: FORMAT
  });
  // Expected local path: exported_8k/copernicus_dem_glo30_elevation_8192x4096.tif
  // Values: float32, meters; nodata likely 0 or -9999 (verify after import)
  // Downstream masks: high_mountain, mountain, plateau_refined, lowland_plain,
  //   basin_context_proxy, hill_or_relief_proxy

  // Slope (degrees, 0–90, derived in GEE)
  var copSlope = ee.Terrain.slope(copDEM);

  Export.image.toDrive({
    image: copSlope,
    description: 'copernicus_dem_glo30_slope_8192x4096',
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'copernicus_dem_glo30_slope_8192x4096',
    dimensions: DIMENSIONS_8K,
    crs: CRS,
    region: REGION,
    maxPixels: MAX_PIXELS_8K,
    fileFormat: FORMAT
  });
  // Expected local path: exported_8k/copernicus_dem_glo30_slope_8192x4096.tif
  // Values: float32, degrees (0–90)

  // Hillshade / relief (0–255, derived in GEE)
  var copRelief = ee.Terrain.hillshade(copDEM);

  Export.image.toDrive({
    image: copRelief,
    description: 'copernicus_dem_glo30_relief_8192x4096',
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'copernicus_dem_glo30_relief_8192x4096',
    dimensions: DIMENSIONS_8K,
    crs: CRS,
    region: REGION,
    maxPixels: MAX_PIXELS_8K,
    fileFormat: FORMAT
  });
  // Expected local path: exported_8k/copernicus_dem_glo30_relief_8192x4096.tif
  // Values: uint8, 0–255 hillshade intensity


  // -------------------------------------------------------------------------
  // BATCH 4 — ETOPO1 Global Relief
  // dataset: NOAA/NGDC/ETOPO1
  // bands:   bedrock, ice_surface
  // license: NOAA public domain (commercial_clearance: pending_review)
  // Note:    ETOPO1 native resolution ~1855 m (1 arc-minute). Exporting at
  //          8192x4096 upsamples; no additional detail is added.
  //          This export is for grid alignment with other Phase 1 sources.
  // -------------------------------------------------------------------------

  var etopo1 = ee.Image('NOAA/NGDC/ETOPO1');

  Export.image.toDrive({
    image: etopo1.select('bedrock'),
    description: 'etopo1_bedrock_8192x4096',
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'etopo1_bedrock_8192x4096',
    dimensions: DIMENSIONS_8K,
    crs: CRS,
    region: REGION,
    maxPixels: MAX_PIXELS_8K,
    fileFormat: FORMAT
  });
  // Expected local path: exported_8k/etopo1_bedrock_8192x4096.tif
  // Values: int16, meters (negative = below sea level)
  // Downstream masks: deep_ocean, mid_ocean, continental_shelf, shallow_sea

  Export.image.toDrive({
    image: etopo1.select('ice_surface'),
    description: 'etopo1_ice_surface_8192x4096',
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'etopo1_ice_surface_8192x4096',
    dimensions: DIMENSIONS_8K,
    crs: CRS,
    region: REGION,
    maxPixels: MAX_PIXELS_8K,
    fileFormat: FORMAT
  });
  // Expected local path: exported_8k/etopo1_ice_surface_8192x4096.tif
  // Values: int16, meters
  // Downstream masks: polar_ice_context, antarctica_bedrock_context,
  //   greenland_bedrock_context

}
// END definePhase1Exports()

// ---------------------------------------------------------------------------
// TO SUBMIT EXPORTS: uncomment the line below ONLY after RW authorization.
// Do NOT uncomment during review or draft stage.
//
// definePhase1Exports();
//
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// TASK SUMMARY (when authorized and function is called)
//
// Total tasks:  10
//   1. esa_worldcover_2021_v200_map_8192x4096
//   2. jrc_gsw_occurrence_8192x4096
//   3. jrc_gsw_seasonality_8192x4096
//   4. jrc_gsw_recurrence_8192x4096
//   5. jrc_gsw_max_extent_8192x4096
//   6. copernicus_dem_glo30_elevation_8192x4096
//   7. copernicus_dem_glo30_slope_8192x4096
//   8. copernicus_dem_glo30_relief_8192x4096
//   9. etopo1_bedrock_8192x4096
//  10. etopo1_ice_surface_8192x4096
//
// After tasks complete in GEE Tasks tab:
//   - Download files from Google Drive: RodiO_GEE_Cache_Phase1
//   - Place in: d5b_processor_v3/source_cache/gee_global/exported_8k/
//   - Fill manifest JSON per file in: source_cache/gee_global/manifests/
//   - Run D3 import validation before using in mask derivation
// ---------------------------------------------------------------------------
