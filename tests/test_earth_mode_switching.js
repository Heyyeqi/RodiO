'use strict'

const fs = require('fs')
const path = require('path')
const assert = require('assert')

const earth3d = fs.readFileSync(path.join(__dirname, '../pwa/earth3d.js'), 'utf8')
const earthModes = fs.readFileSync(path.join(__dirname, '../pwa/earth_modes.js'), 'utf8')
const index = fs.readFileSync(path.join(__dirname, '../pwa/index.html'), 'utf8')

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

console.log('\nearth rendering mode contract tests\n')

test('RAW mode never requests tiles_noon_air', () => {
  assert.ok(earthModes.includes('RAW'), 'RAW mode missing')
  assert.ok(earthModes.includes("pipeline: 'raw'"), 'RAW pipeline label missing')
  assert.ok(
    earthModes.includes("tileSource: '/assets/earth/bmng21k/topo_bathy/tiles/'"),
    'RAW tile source mismatch'
  )
})

test('NOON_AIR mode never requests raw tiles', () => {
  assert.ok(earthModes.includes('NOON_AIR'), 'NOON_AIR mode missing')
  assert.ok(earthModes.includes("pipeline: 'noon_air_full'"), 'NOON_AIR pipeline label missing')
  assert.ok(
    earthModes.includes("tileSource: '/assets/earth/bmng21k/topo_bathy/tiles_noon_air/'"),
    'NOON_AIR tile source mismatch'
  )
})

test('single resolver is mode-bound and has no raw fallback candidates', () => {
  assert.ok(earth3d.includes('function resolveTileUrl(modeName, lod, x, y)'), 'explicit resolveTileUrl missing')
  assert.ok(earth3d.includes('function getTileUrl(lod, x, y)'), 'single tile URL entry point missing')
  assert.ok(
    earth3d.includes('return resolveTileUrl(EARTH_MODE, lod, x, y)'),
    'getTileUrl does not bind requests to EARTH_MODE'
  )
  assert.ok(!earth3d.includes('tileUrlCandidates'), 'candidate fallback resolver still exists')
  assert.ok(!earth3d.includes('mapTileToLod'), '8k fallback tile mapper still exists')
  assert.ok(!earth3d.includes('tile fallback'), 'tile fallback logging still exists')
})

test('runtime mismatch guard blocks cross-mode leakage', () => {
  assert.ok(
    earth3d.includes('[FATAL MODE MISMATCH] RAW tile detected in NOON_AIR mode'),
    'NOON_AIR raw guard missing'
  )
  assert.ok(
    earth3d.includes('[FATAL MODE MISMATCH] NOON_AIR tile detected in RAW mode'),
    'RAW noon_air guard missing'
  )
  assert.ok(
    earth3d.includes('[FATAL MODE MISMATCH] V2 tile detected in RAW mode'),
    'V2 in RAW guard missing'
  )
  assert.ok(
    earth3d.includes('[FATAL MODE MISMATCH] Non-V2 tile detected in V2_ENHANCED mode'),
    'non-V2 in V2_ENHANCED guard missing'
  )
  assert.ok(
    earth3d.includes('[FATAL MODE MISMATCH] Non-NOON_AIR_V2 tile detected in NOON_AIR_V2 mode'),
    'non-NAV2 in NOON_AIR_V2 guard missing'
  )
  assert.ok(
    earth3d.includes('[FATAL MODE MISMATCH] Non-NOON_AIR_V2_ISLANDS tile detected in NOON_AIR_V2_ISLANDS mode'),
    'non-NAV2I in NOON_AIR_V2_ISLANDS guard missing'
  )
})

test('cache keys are isolated by render mode', () => {
  assert.ok(
    earth3d.includes('return `${mode.cachePrefix}_${tile.lod}_${tile.x}_${tile.y}`'),
    'mode-prefixed cache key missing'
  )
  assert.ok(earthModes.includes("cachePrefix: 'raw'"), 'raw cache prefix missing')
  assert.ok(earthModes.includes("cachePrefix: 'noon_air'"), 'noon_air cache prefix missing')
  assert.ok(earthModes.includes("cachePrefix: 'v2'"), 'v2 cache prefix missing')
  assert.ok(earthModes.includes("cachePrefix: 'nav2'"), 'nav2 cache prefix missing')
  assert.ok(earthModes.includes("cachePrefix: 'nav2i'"), 'nav2i cache prefix missing')
})

test('switching mode clears old tiles and pending loads', () => {
  assert.ok(earth3d.includes('function setEarthMode(mode)'), 'setEarthMode missing')
  assert.ok(earth3d.includes('tileManager.clearCache()'), 'mode switch does not clear cache')
  assert.ok(earth3d.includes('tileManager.resetStreaming()'), 'mode switch does not reset streaming')
  assert.ok(earth3d.includes('this.loadGeneration += 1'), 'pending load generation reset missing')
  assert.ok(earth3d.includes('modeAtRequest !== EARTH_MODE'), 'stale mode callback guard missing')
})

test('UI toggle fully controls earth mode', () => {
  assert.ok(index.includes('/earth_modes.js?v=rdl-overlay-gate-v1'), 'earth_modes.js not loaded before earth3d')
  assert.ok(index.includes('/earth3d.js?v=rdl-overlay-gate-v1'), 'earth3d.js cache-busting version missing')
  assert.ok(index.includes('data-earth-mode="RAW"'), 'RAW UI button missing')
  assert.ok(index.includes('data-earth-mode="NOON_AIR"'), 'NOON_AIR UI button missing')
  assert.ok(index.includes('data-earth-mode="NOON_AIR_V2_ISLANDS"'), 'NOON_AIR_V2_ISLANDS UI button missing')
  assert.ok(index.includes('window.earth3d.setEarthMode(mode)'), 'UI does not call earth3d.setEarthMode')
})

test('pure view uses island-ready Noon Air mode for RDL review', () => {
  assert.ok(
    index.includes("window.earth3d?.setEarthMode?.('NOON_AIR_V2_ISLANDS')"),
    'PURE VIEW should use NOON_AIR_V2_ISLANDS for island/RDL review'
  )
  assert.ok(
    index.includes("window.earth3d.setDebugLocation(region.lon, region.lat, { center: true })"),
    'audit region should center target instead of using hero composition anchor'
  )
  assert.ok(
    index.includes('window.earth3d.setRDLInspectRegion(region.rdlId || null)'),
    'audit region should enable RDL inspect visibility for regional tiles'
  )
})

test('tile request logging exposes actual mode-bound URLs', () => {
  assert.ok(earth3d.includes("console.log('[tile-request]', modeAtRequest, url)"), 'tile request URL log missing')
  assert.ok(earth3d.includes("console.log('[RodiO] dayTexture source:'"), 'mode source init log missing')
  assert.ok(!earth3d.includes("'bmng21k tile stream'"), 'misleading fixed bmng21k tile stream log remains')
})

console.log(`\nResults: ${passed} passed, ${failed} failed\n`)
process.exit(failed > 0 ? 1 : 0)
