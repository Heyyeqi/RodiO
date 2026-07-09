'use strict'

// Tests for BMNG frontend texture unification in earth3d.js.
// Stage 11 moves the day texture from full-image LOD loading to BMNG tile
// streaming, so these assertions guard the source contract without reviving the
// legacy single-texture path.

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

console.log('\nearth3d.js - texture unification tests\n')

test('DAY_TEXTURE_VARIANT points to BMNG tile streaming', () => {
  const match = source.match(/const DAY_TEXTURE_VARIANT\s*=\s*'([^']+)'/)
  assert.ok(match, 'DAY_TEXTURE_VARIANT not found')
  assert.strictEqual(match[1], 'bmng21k_stream', `Expected 'bmng21k_stream', got '${match[1]}'`)
})

test('legacy d5z_b and static fallback day textures are absent', () => {
  assert.ok(!source.includes('d5z_b'), 'd5z_b path should not remain in frontend source')
  assert.ok(!source.includes('/assets/bluemarble.jpg'), 'Blue Marble static fallback should not remain')
  assert.ok(!source.includes('/assets/earth_day_8k.jpg'), 'single day texture fallback should not remain')
})

test('render mode resolver is the day source contract', () => {
  assert.ok(source.includes('function resolveTileUrl(modeName, lod, x, y)'), 'explicit mode-bound tile resolver missing')
  assert.ok(source.includes('function getTileUrl(lod, x, y)'), 'single tile URL entry point missing')
  assert.ok(source.includes('return resolveTileUrl(EARTH_MODE, lod, x, y)'), 'getTileUrl does not bind to earth mode')
  assert.ok(source.includes('return getTileUrl(tile.lod, tile.x, tile.y)'), 'tile manager bypasses resolver')
  assert.ok(source.includes('getEarthModeConfig(modeName)'), 'resolver does not use explicit earth mode config')
})

test('resolveEarthTextureLOD function is defined for streaming LOD selection', () => {
  assert.ok(source.includes('function resolveEarthTextureLOD('), 'resolveEarthTextureLOD not found')
  assert.ok(source.includes("lod = '16k'"), '16k streaming LOD missing')
  assert.ok(source.includes("lod = '8k'"), '8k streaming LOD missing')
  assert.ok(source.includes("lod = '4k'"), '4k streaming LOD missing')
})

test('FrontendTileStreamingManager is registered and atlas-backed', () => {
  assert.ok(source.includes('class FrontendTileStreamingManager'), 'tile streaming manager missing')
  assert.ok(source.includes('new THREE.CanvasTexture(this.atlasCanvas)'), 'atlas texture missing')
  assert.ok(source.includes('dayTexture = tileManager.atlasTexture'), 'day texture is not atlas-backed')
})

test('[earth] texture source log is present', () => {
  assert.ok(source.includes("console.log('[earth] texture source:'"), '[earth] texture source log missing')
})

test('[tile-stream] debug log is present', () => {
  assert.ok(source.includes("console.log('[tile-stream]'"), '[tile-stream] log missing')
})

console.log(`\nResults: ${passed} passed, ${failed} failed\n`)
process.exit(failed > 0 ? 1 : 0)
