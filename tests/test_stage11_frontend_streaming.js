'use strict'

// Stage 11 frontend streaming binding tests.
// These checks keep earth3d.js on the tile-streaming path and prevent silent
// regression to single full-earth texture loading.

const fs = require('fs')
const path = require('path')
const assert = require('assert')

const EARTH3D_PATH = path.join(__dirname, '../pwa/earth3d.js')
const source = fs.readFileSync(EARTH3D_PATH, 'utf8')

let passed = 0
let failed = 0

function test(label, fn) {
  try {
    fn()
    console.log('  PASS:', label)
    passed++
  } catch (err) {
    console.error('  FAIL:', label)
    console.error('       ', err.message)
    failed++
  }
}

function extractFunction(name) {
  const start = source.indexOf(`function ${name}(`)
  assert.ok(start >= 0, `${name} not found`)
  const nextFunction = source.indexOf('\n      function ', start + 1)
  const nextClass = source.indexOf('\n      class ', start + 1)
  const candidates = [nextFunction, nextClass].filter((idx) => idx > start)
  const end = candidates.length ? Math.min(...candidates) : source.length
  return source.slice(start, end)
}

function extractClass(name) {
  const start = source.indexOf(`class ${name}`)
  assert.ok(start >= 0, `${name} not found`)
  const end = source.indexOf('\n\n      function ', start)
  assert.ok(end > start, `${name} end boundary not found`)
  return source.slice(start, end)
}

console.log('\nearth3d.js - Stage 11 frontend streaming tests\n')

test('full-earth day texture load path is removed', () => {
  assert.ok(!source.includes('getDayTexturePaths'), 'legacy day texture path resolver remains')
  assert.ok(!source.includes('d5z_b'), 'legacy d5z_b path remains')
  assert.ok(!source.includes('/assets/bluemarble.jpg'), 'static Blue Marble fallback remains')
  assert.ok(!source.includes('/assets/earth_day_8k.jpg'), 'single day texture fallback remains')
  assert.ok(!source.includes('bmng21k_lod'), 'old full-image BMNG LOD variant remains')
})

test('frontend tile streaming manager owns active and cached tiles', () => {
  const klass = extractClass('FrontendTileStreamingManager')
  assert.ok(klass.includes('this.activeTiles = new Map()'), 'activeTiles map missing')
  assert.ok(klass.includes('this.tileCache = new Map()'), 'tileCache map missing')
  assert.ok(klass.includes('this.loadingTiles = new Set()'), 'loading tile set missing')
  assert.ok(klass.includes('requestVisibleTiles(cameraState)'), 'requestVisibleTiles missing')
  assert.ok(klass.includes('loadTileAsync(tile)'), 'async tile loader missing')
})

test('visible tile requests are generated from camera state', () => {
  const fn = extractFunction('computeVisibleTileSet')
  assert.ok(fn.includes('cameraState.lon'), 'longitude not used')
  assert.ok(fn.includes('cameraState.lat'), 'latitude not used')
  assert.ok(fn.includes('cameraState.fovDegrees'), 'field of view not used')
  assert.ok(fn.includes('return { lod: _lod, x: Number(x), y: Number(y) }'), 'tile ids not returned')
})

test('LOD resolution adapts to camera distance and GPU max texture size', () => {
  const fn = extractFunction('resolveEarthTextureLOD')
  assert.ok(fn.includes('maxTextureSize'), 'GPU maxTextureSize not consulted')
  assert.ok(fn.includes('distance'), 'camera distance not consulted')
  assert.ok(fn.includes("lod = '16k'"), '16k LOD config missing')
  assert.ok(fn.includes("lod = '8k'"), '8k LOD config missing')
  assert.ok(fn.includes("lod = '4k'"), '4k LOD config missing')
})

test('GPU texture swapping uses a CanvasTexture atlas without per-frame full re-upload', () => {
  const klass = extractClass('FrontendTileStreamingManager')
  assert.ok(klass.includes('new THREE.CanvasTexture(this.atlasCanvas)'), 'CanvasTexture atlas missing')
  assert.ok(klass.includes('this.atlasContext.drawImage'), 'tile draw into atlas missing')
  assert.ok(klass.includes('this.atlasTexture.needsUpdate = true'), 'dynamic atlas update missing')
  assert.ok(source.includes('dayTexture = tileManager.atlasTexture'), 'material day texture is not atlas-backed')
})

test('16k atlas keeps source resolution and can use sharp filtering', () => {
  const lodFn = extractFunction('resolveEarthTextureLOD')
  assert.ok(lodFn.includes("atlasTileSize: lod === '16k' ? 4096"), '16k atlas should keep 4096 tile size')
  assert.ok(source.includes('function configureAtlasTexture(texture, lod)'), 'atlas-specific texture configuration missing')
  assert.ok(source.includes("atlasFilterMode === 'sharp' && lod === '16k'"), 'sharp mode should be scoped to 16k atlas')
  assert.ok(source.includes('texture.generateMipmaps = false'), 'sharp atlas should disable mipmaps')
  assert.ok(source.includes('this.atlasContext.imageSmoothingEnabled = false'), 'atlas canvas smoothing should be disabled')
})

test('streaming cache is bounded and evicts least-recent tiles', () => {
  const klass = extractClass('FrontendTileStreamingManager')
  assert.ok(klass.includes('this.touchCacheKey(key)'), 'cache recency tracking missing')
  assert.ok(klass.includes('while (this.cacheOrder.length > this.lodConfig.maxCachedTiles)'), 'cache cap missing')
  assert.ok(klass.includes('this.tileCache.delete(evictKey)'), 'tile eviction missing')
  assert.ok(klass.includes('evicted?.dispose'), 'evicted GPU texture disposal missing')
})

test('render loop is camera-driven and emits tile debug overlay logs', () => {
  assert.ok(source.includes('function updateStreaming(camera)'), 'updateStreaming(camera) missing')
  assert.ok(source.includes('tileManager.updateStreaming(getStreamingCameraState(camera))'), 'camera state not passed to tile manager')
  assert.ok(
    source.includes('updateStreaming(camera)\n          updateRDLOverlays()\n\n          renderer.render(scene, camera)') ||
    source.includes('updateStreaming(camera)\n        updateRDLOverlays()\n        renderer.render(scene, camera)') ||
    (source.includes('updateStreaming(camera)') && source.includes('updateRDLOverlays()') && source.includes('renderer.render(scene, camera)')),
    'render loop does not update streaming and RDL overlays before render'
  )
  assert.ok(source.includes("console.log('[tile-stream]'"), 'tile stream debug log missing')
})

test('tile URLs are resolved through the render mode contract', () => {
  const klass = extractClass('FrontendTileStreamingManager')
  assert.ok(source.includes('function resolveTileUrl(modeName, lod, x, y)'), 'explicit mode-bound tile resolver missing')
  assert.ok(source.includes('function getTileUrl(lod, x, y)'), 'single tile URL entry point missing')
  assert.ok(source.includes('return resolveTileUrl(EARTH_MODE, lod, x, y)'), 'getTileUrl is not bound to EARTH_MODE')
  assert.ok(klass.includes('return getTileUrl(tile.lod, tile.x, tile.y)'), 'manager bypasses mode resolver')
  assert.ok(!klass.includes('tileUrlCandidates'), 'candidate fallback resolver remains')
  assert.ok(!klass.includes('tile fallback'), 'raw fallback chain remains')
})

test('RDL regions use Mapbox satellite tiles', () => {
  assert.ok(source.includes("id: 'hawaii'"), 'hawaii RDL region missing')
  assert.ok(source.includes("tile_noon_air_mapbox.jpg"), 'RDL regions do not point to Mapbox POC tiles')
})

test('RDL overlays are opt-in to avoid stray resolution patches', () => {
  assert.ok(source.includes('let   _rdlInspectRegion = null'), 'RDL inspect region state missing')
  assert.ok(source.includes('const opacity = inspectThisRegion ? 0.92 : 0.0'), 'non-inspected RDL overlays should be hidden')
})

test('debug region jumps refresh RDL overlays immediately', () => {
  assert.ok(
    source.includes('updateStreaming(camera)\n          updateRDLOverlays()\n          renderer.render(scene, camera)'),
    'setDebugLocation does not refresh RDL overlays before rendering'
  )
})

test('RDL inspect mode can force the active audit region visible', () => {
  assert.ok(source.includes('let   _rdlInspectRegion = null'), 'RDL inspect region state missing')
  assert.ok(source.includes('const inspectThisRegion = _rdlInspectRegion && entry.region.id === _rdlInspectRegion'), 'RDL inspect region visibility gate missing')
  assert.ok(source.includes('setRDLInspectRegion(regionId)'), 'RDL inspect public API missing')
  const inspectFn = source.slice(source.indexOf('setRDLInspectRegion(regionId)'), source.indexOf('setAuditViewAngle(angle)'))
  assert.ok(!inspectFn.includes('_rdlZoomLevel = 1'), 'RDL inspect should not force zoom distance')
})

test('RDL regional textures avoid mipmap softening', () => {
  assert.ok(source.includes('tex.generateMipmaps = false'), 'RDL texture mipmap disabling missing')
  assert.ok(source.includes('tex.anisotropy = Math.min(16, renderer.capabilities.getMaxAnisotropy())'), 'RDL texture anisotropy missing')
})

test('main globe geometry is high enough for close-up review', () => {
  assert.ok(source.includes('earthGeometry = new THREE.SphereGeometry(2, 128, 128)'), 'main earth sphere should use 128 segments')
  assert.ok(source.includes('new THREE.SphereGeometry(2.07, 128, 128)'), 'atmosphere sphere should use 128 segments')
})

test('audit camera angle presets are exposed for region review', () => {
  assert.ok(source.includes('const _AUDIT_VIEW_ANGLES = {'), 'audit camera angle presets missing')
  assert.ok(source.includes('oblique: { y:'), '45 degree audit angle missing')
  assert.ok(source.includes('setAuditViewAngle(angle)'), 'audit camera angle API missing')
  assert.ok(source.includes('setAuditLightingMode(enabled)'), 'audit lighting API missing')
  assert.ok(source.includes('const AUDIT_LIGHTING_CONFIG = {'), 'neutral audit lighting config missing')
  assert.ok(source.includes('let useAuditCenterTarget = false'), 'persistent audit center state missing')
  assert.ok(source.includes('getTargetOrientation(useAuditCenterTarget ? auditCenterDir : null)'), 'render loop does not preserve centered audit target')
})

console.log(`\nResults: ${passed} passed, ${failed} failed\n`)
process.exit(failed > 0 ? 1 : 0)
