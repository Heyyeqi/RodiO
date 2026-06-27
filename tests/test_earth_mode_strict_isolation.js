'use strict'

const fs = require('fs')
const path = require('path')
const assert = require('assert')

const earth3d = fs.readFileSync(path.join(__dirname, '../pwa/earth3d.js'), 'utf8')
const earthModes = fs.readFileSync(path.join(__dirname, '../pwa/earth_modes.js'), 'utf8')
const sw = fs.readFileSync(path.join(__dirname, '../pwa/sw.js'), 'utf8')

let passed = 0
let failed = 0

function test(label, fn) {
  try {
    fn()
    console.log('  PASS:', label)
    passed++
  } catch (error) {
    console.error('  FAIL:', label)
    console.error('       ', error.message)
    failed++
  }
}

console.log('\nearth mode strict isolation tests\n')

test('RAW mode resolves only to the raw topo_bathy tile directory', () => {
  assert.ok(
    earthModes.includes("tileSource: '/assets/earth/bmng21k/topo_bathy/tiles/'"),
    'RAW tileSource is not the raw tile directory'
  )
  assert.ok(
    earth3d.includes("if (mode === 'RAW' && url.includes('tiles_noon_air'))"),
    'RAW guard does not reject noon_air URLs'
  )
})

test('NOON_AIR mode resolves only to tiles_noon_air, not raw /tiles/', () => {
  assert.ok(
    earthModes.includes("tileSource: '/assets/earth/bmng21k/topo_bathy/tiles_noon_air/'"),
    'NOON_AIR tileSource is not tiles_noon_air'
  )
  assert.ok(
    earth3d.includes("url.includes('bmng21k/topo_bathy/tiles') && !url.includes('tiles_noon_air')"),
    'NOON_AIR guard does not reject raw topo_bathy tiles'
  )
})

test('all streaming requests pass through EARTH_MODE-bound getTileUrl', () => {
  assert.ok(earth3d.includes('function getTileUrl(lod, x, y)'), 'getTileUrl missing')
  assert.ok(
    earth3d.includes('return resolveTileUrl(EARTH_MODE, lod, x, y)'),
    'getTileUrl does not bind to EARTH_MODE'
  )
  assert.ok(
    earth3d.includes('return getTileUrl(tile.lod, tile.x, tile.y)'),
    'StreamingManager bypasses getTileUrl'
  )
})

test('no frontend tile fallback path exists in streaming manager', () => {
  assert.ok(!earth3d.includes('tileUrlCandidates'), 'tileUrlCandidates fallback remains')
  assert.ok(!earth3d.includes('mapTileToLod'), '8k fallback mapper remains')
  assert.ok(!earth3d.includes('loadTextureWithFallback(\n        _dayPrimary'), 'legacy day fallback load remains')
  assert.ok(!earth3d.includes('[tile-stream] tile fallback'), 'tile fallback log remains')
})

test('cache keys and stale callbacks are mode-isolated', () => {
  assert.ok(
    earth3d.includes('return `${mode.cachePrefix}_${tile.lod}_${tile.x}_${tile.y}`'),
    'cache key does not include mode prefix'
  )
  assert.ok(earth3d.includes('const modeAtRequest = EARTH_MODE'), 'request mode snapshot missing')
  assert.ok(earth3d.includes('modeAtRequest !== EARTH_MODE'), 'stale cross-mode callback guard missing')
})

test('mode switching clears cache, pending requests, visible atlas, and reloads visible tiles', () => {
  assert.ok(earth3d.includes('tileManager.clearCache()'), 'setEarthMode does not clear cache')
  assert.ok(earth3d.includes('tileManager.resetStreaming()'), 'setEarthMode does not reset streaming')
  assert.ok(earth3d.includes('this.loadingTiles.clear()'), 'pending tile set is not cleared')
  assert.ok(earth3d.includes('this.activeTiles.clear()'), 'visible tile set is not cleared')
  assert.ok(earth3d.includes('requestRenderUpdate()'), 'setEarthMode does not request a render update')
})

test('runtime diagnostics expose actual tile source instead of fixed bmng21k label', () => {
  assert.ok(earth3d.includes("console.log('[tile-request]', modeAtRequest, url)"), 'actual tile URL log missing')
  assert.ok(earth3d.includes('tileSource: currentMode.tileSource'), 'tile-stream source diagnostic missing')
  assert.ok(!earth3d.includes("'bmng21k tile stream'"), 'fixed bmng21k stream label remains')
})

test('service worker static shell is versioned and network-first', () => {
  assert.ok(sw.includes("const CACHE = 'claudio-v2'"), 'service worker cache version not bumped')
  assert.ok(sw.includes('fetch(e.request)'), 'static shell is not network-first')
})

console.log(`\nResults: ${passed} passed, ${failed} failed\n`)
process.exit(failed > 0 ? 1 : 0)
