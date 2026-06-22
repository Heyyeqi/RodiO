// B-6.2X-D2 — GEE Export Script Draft: Phase 1 Core Sources @ 21600x10800
// Stage: B-6.2X-D2
// Date: 2026-06-15
// Status: REFERENCE DRAFT — not to be executed until Phase 2 is authorized.
//         This script has NOT been executed. No exports have been submitted.
//         Do not run without explicit RW authorization after D3 8K import
//         validation passes.
//
// HOW TO USE:
//   1. Copy into GEE Code Editor ONLY after D3 8K validation passes and
//      RW explicitly authorizes 21.6K exports.
//   2. Review all Export.image.toDrive() calls inside definePhase1Exports21600().
//   3. Uncomment the call to definePhase1Exports21600() at the bottom of this
//      file after RW authorization.
//   4. Go to the Tasks tab and click RUN on each listed task.
//   5. Do NOT call task.start() programmatically.
//
// Purpose: Master source cache at 21600x10800 for future high-resolution
//          structure mask work. This tier adds real detail for sources with
//          native resolution finer than ~1855 m (ESA WorldCover, Copernicus DEM).
//          ETOPO1 21.6K is master-aligned only — no additional true detail.
//
// Pixel dimensions are controlled by the 'dimensions' parameter (not 'scale').
// SCALE_21600 is kept below as a reference comment only.

// ---------------------------------------------------------------------------
// CONFIGURATION
// ---------------------------------------------------------------------------

var DRIVE_FOLDER = 'RodiO_GEE_Cache_Phase1';
var CRS = 'EPSG:4326';
var REGION = ee.Geometry.Rectangle([-180, -90, 180, 90], 'EPSG:4326', false);
var DIMENSIONS_21600 = '21600x10800';
var MAX_PIXELS_21600 = 1e11;
var FORMAT = 'GeoTIFF';

// Reference scale (informational only — not used in Export calls):
// At the equator, 21600x10800 in EPSG:4326 ≈ 1855 m/px.
// var SCALE_21600 = 1855;  // reference only

// ---------------------------------------------------------------------------
// PHASE 1 21.6K EXPORT DEFINITIONS
// All Export.image.toDrive() calls are wrapped in definePhase1Exports21600().
// This function is NOT called automatically. Call it only after RW authorization
// AND after D3 8K import validation passes.
// ---------------------------------------------------------------------------

function definePhase1Exports21600() {

  // -------------------------------------------------------------------------
  // BATCH 1 — ESA WorldCover 2021 v200 @ 21.6K
  // Native 10 m — real additional detail at 21.6K output.
  // license: CC-BY-4.0 (commercial_clearance: pending_review)
  // -------------------------------------------------------------------------

  var esaWC = ee.ImageCollection('ESA/WorldCover/v200').mosaic().select('Map');

  Export.image.toDrive({
    image: esaWC,
    description: 'esa_worldcover_2021_v200_map_21600x10800',
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'esa_worldcover_2021_v200_map_21600x10800',
    dimensions: DIMENSIONS_21600,
    crs: CRS,
    region: REGION,
    maxPixels: MAX_PIXELS_21600,
    fileFormat: FORMAT
  });
  // Expected local path: exported_21600/esa_worldcover_2021_v200_map_21600x10800.tif
  // Estimated size: ~220 MB (uint8 single band, compressed)


  // -------------------------------------------------------------------------
  // BATCH 3 — Copernicus DEM GLO-30 @ 21.6K
  // Native 30 m — real additional detail at 21.6K output.
  // Elevation and slope only; relief deferred (render cost high at this scale).
  // license: Copernicus Open Access Hub Terms (commercial_clearance: pending_review;
  //          country exceptions apply — see GEE catalog)
  // -------------------------------------------------------------------------

  var copDEM = ee.ImageCollection('COPERNICUS/DEM/GLO30')
                 .select('DEM')
                 .mosaic();

  Export.image.toDrive({
    image: copDEM,
    description: 'copernicus_dem_glo30_elevation_21600x10800',
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'copernicus_dem_glo30_elevation_21600x10800',
    dimensions: DIMENSIONS_21600,
    crs: CRS,
    region: REGION,
    maxPixels: MAX_PIXELS_21600,
    fileFormat: FORMAT
  });
  // Expected local path: exported_21600/copernicus_dem_glo30_elevation_21600x10800.tif
  // Estimated size: ~900 MB (float32, compressed)

  var copSlope = ee.Terrain.slope(copDEM);

  Export.image.toDrive({
    image: copSlope,
    description: 'copernicus_dem_glo30_slope_21600x10800',
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'copernicus_dem_glo30_slope_21600x10800',
    dimensions: DIMENSIONS_21600,
    crs: CRS,
    region: REGION,
    maxPixels: MAX_PIXELS_21600,
    fileFormat: FORMAT
  });
  // Expected local path: exported_21600/copernicus_dem_glo30_slope_21600x10800.tif
  // Estimated size: ~900 MB (float32, compressed)


  // -------------------------------------------------------------------------
  // BATCH 4 — ETOPO1 @ 21.6K (master-aligned, no new detail)
  // ETOPO1 native ~1855 m ≈ 21.6K pixel pitch; this export aligns to 21.6K grid.
  // No additional bathymetric detail beyond 8K version.
  // license: NOAA public domain (commercial_clearance: pending_review)
  // -------------------------------------------------------------------------

  var etopo1 = ee.Image('NOAA/NGDC/ETOPO1');

  Export.image.toDrive({
    image: etopo1.select('bedrock'),
    description: 'etopo1_bedrock_21600x10800',
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'etopo1_bedrock_21600x10800',
    dimensions: DIMENSIONS_21600,
    crs: CRS,
    region: REGION,
    maxPixels: MAX_PIXELS_21600,
    fileFormat: FORMAT
  });
  // Expected local path: exported_21600/etopo1_bedrock_21600x10800.tif

  Export.image.toDrive({
    image: etopo1.select('ice_surface'),
    description: 'etopo1_ice_surface_21600x10800',
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'etopo1_ice_surface_21600x10800',
    dimensions: DIMENSIONS_21600,
    crs: CRS,
    region: REGION,
    maxPixels: MAX_PIXELS_21600,
    fileFormat: FORMAT
  });
  // Expected local path: exported_21600/etopo1_ice_surface_21600x10800.tif

  // -------------------------------------------------------------------------
  // DEFERRED — JRC GSW @ 21.6K
  // JRC GSW native 30 m. 21.6K version adds real detail but is lower priority
  // than DEM. Defer to D4 after 8K import validation confirms value.
  // Uncomment only after RW explicitly authorizes D4 21.6K import.
  //
  // var jrcGSW = ee.Image('JRC/GSW1_4/GlobalSurfaceWater');
  // Export.image.toDrive({
  //   image: jrcGSW.select('occurrence'),
  //   description: 'jrc_gsw_occurrence_21600x10800',
  //   folder: DRIVE_FOLDER,
  //   fileNamePrefix: 'jrc_gsw_occurrence_21600x10800',
  //   dimensions: DIMENSIONS_21600, crs: CRS, region: REGION,
  //   maxPixels: MAX_PIXELS_21600, fileFormat: FORMAT
  // });
  // -------------------------------------------------------------------------

}
// END definePhase1Exports21600()

// ---------------------------------------------------------------------------
// TO SUBMIT EXPORTS: uncomment the line below ONLY after:
//   1. D3 8K import validation passes.
//   2. RW explicitly authorizes 21.6K export run.
//
// definePhase1Exports21600();
//
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// TASK SUMMARY (when authorized and function is called)
//
// Total tasks:  5
//   1. esa_worldcover_2021_v200_map_21600x10800
//   2. copernicus_dem_glo30_elevation_21600x10800
//   3. copernicus_dem_glo30_slope_21600x10800
//   4. etopo1_bedrock_21600x10800
//   5. etopo1_ice_surface_21600x10800
//
// After tasks complete in GEE Tasks tab:
//   - Download from Google Drive: RodiO_GEE_Cache_Phase1
//   - Place in: d5b_processor_v3/source_cache/gee_global/exported_21600/
//   - Fill manifest JSON per file in: source_cache/gee_global/manifests/
// ---------------------------------------------------------------------------
