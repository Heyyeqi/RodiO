/**
 * lon_lat_to_uv.js — Three.js r128 SphereGeometry UV converter
 *
 * Three.js r128 UV convention (INVERSE of equirectangular map standard):
 *   uv.x = (lon + 180) / 360           [0=180°W → 1=180°E]
 *   uv.y = 1 - (90 - lat) / 180        [0=90°S  → 1=90°N] ← north=1, not north=0
 *
 * Equirectangular map convention (e.g., NASA Blue Marble, ETOPO1 image):
 *   px.x = (lon + 180) / 360 * width
 *   px.y = (90 - lat) / 180 * height   ← north=0 (top of image)
 *
 * The vUv.y flip is the critical invariant for all RDL region definitions.
 * NEVER define region bounds in raw image coordinates without converting first.
 */

/**
 * Convert geographic bounds to Three.js r128 SphereGeometry UV bounds.
 * @param {number} lonW  West longitude (degrees, e.g. 118)
 * @param {number} lonE  East longitude (degrees, e.g. 150)
 * @param {number} latS  South latitude (degrees, e.g. 22)
 * @param {number} latN  North latitude (degrees, e.g. 50)
 * @returns {{ uMin, uMax, vMin, vMax }}  UV bounds in Three.js r128 space
 */
function boundsToUV(lonW, lonE, latS, latN) {
  return {
    uMin: (lonW + 180) / 360,
    uMax: (lonE + 180) / 360,
    vMin: (90 + latS) / 180,   // south boundary → smaller v
    vMax: (90 + latN) / 180,   // north boundary → larger v
  };
}

/**
 * Convert a single lon/lat point to Three.js r128 UV.
 * @param {number} lon  Longitude in degrees
 * @param {number} lat  Latitude in degrees
 * @returns {{ u, v }}
 */
function lonLatToUV(lon, lat) {
  return {
    u: (lon + 180) / 360,
    v: (90 + lat) / 180,
  };
}

/**
 * Convert Three.js r128 UV back to geographic coordinates.
 * @param {number} u
 * @param {number} v
 * @returns {{ lon, lat }}
 */
function uvToLonLat(u, v) {
  return {
    lon: u * 360 - 180,
    lat: v * 180 - 90,
  };
}

// CLI usage: node lon_lat_to_uv.js --bounds lon_w lon_e lat_s lat_n
if (typeof require !== 'undefined' && require.main === module) {
  const args = process.argv.slice(2);
  const boundsIdx = args.indexOf('--bounds');
  if (boundsIdx !== -1 && args.length >= boundsIdx + 5) {
    const [lonW, lonE, latS, latN] = args.slice(boundsIdx + 1, boundsIdx + 5).map(Number);
    const uv = boundsToUV(lonW, lonE, latS, latN);
    console.log(`Region: ${lonW}_${lonE}_${latS}_${latN}`);
    console.log(`uMin=${uv.uMin.toFixed(4)} uMax=${uv.uMax.toFixed(4)}`);
    console.log(`vMin=${uv.vMin.toFixed(4)} vMax=${uv.vMax.toFixed(4)}`);
    console.log('');
    console.log('GLSL snippet:');
    console.log(`  float uMin = ${uv.uMin.toFixed(4)};`);
    console.log(`  float uMax = ${uv.uMax.toFixed(4)};`);
    console.log(`  float vMin = ${uv.vMin.toFixed(4)};`);
    console.log(`  float vMax = ${uv.vMax.toFixed(4)};`);
  } else {
    console.log('Usage: node lon_lat_to_uv.js --bounds lon_w lon_e lat_s lat_n');
    console.log('Example (Japan): node lon_lat_to_uv.js --bounds 118 150 22 50');
  }
}

module.exports = { boundsToUV, lonLatToUV, uvToLonLat };
