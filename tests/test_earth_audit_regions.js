'use strict'

const fs = require('fs')
const path = require('path')
const assert = require('assert')

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

console.log('\nearth audit region switcher tests\n')

test('audit control is present near earth mode controls', () => {
  assert.ok(index.includes('id="earth-audit-control"'), 'earth audit control missing')
  assert.ok(index.includes('id="earth-audit-prev"'), 'earth audit prev button missing')
  assert.ok(index.includes('id="earth-audit-next"'), 'earth audit next button missing')
  assert.ok(index.includes('id="earth-audit-label"'), 'earth audit label missing')
  assert.ok(index.includes('data-audit-move="left"'), 'left audit move missing')
  assert.ok(index.includes('data-audit-move="right"'), 'right audit move missing')
  assert.ok(index.includes('data-audit-move="up"'), 'up audit move missing')
  assert.ok(index.includes('data-audit-move="down"'), 'down audit move missing')
  assert.ok(index.includes('data-audit-angle="oblique"'), '45 degree audit angle missing')
  assert.ok(index.includes('id="rdl-tile-view"'), 'RDL tile view button missing')
  assert.ok(index.includes('id="rdl-tile-preview"'), 'RDL tile preview panel missing')
})

test('first-pass audit sequence contains the requested 12 regions', () => {
  const required = [
    '中国华东 / 长三角',
    '台湾',
    '日本本州',
    '冲绳 / 琉球',
    '菲律宾',
    '南海',
    '喜马拉雅',
    '青藏高原',
    '马尔代夫',
    '撒哈拉',
    '亚马逊',
    '格陵兰',
  ]
  for (const label of required) {
    assert.ok(index.includes(`label: '${label}'`), `${label} missing`)
  }
})

test('audit sequence preserves representative coordinates', () => {
  assert.ok(index.includes("{ label: '中国华东 / 长三角', lat: 31.2, lon: 121.5 }"), 'Changjiang delta coordinate mismatch')
  assert.ok(index.includes("label: '菲律宾', lat: 12.9, lon: 122.0"), 'Philippines coordinate mismatch')
  assert.ok(index.includes("{ label: '喜马拉雅', lat: 28.0, lon: 86.9 }"), 'Himalaya coordinate mismatch')
  assert.ok(index.includes("{ label: '格陵兰', lat: 72.0, lon: -40.0 }"), 'Greenland coordinate mismatch')
})

test('region switch updates app state, global visual state, and earth3d location', () => {
  assert.ok(index.includes('state.lat = region.lat'), 'state latitude is not updated')
  assert.ok(index.includes('state.lon = region.lon'), 'state longitude is not updated')
  assert.ok(index.includes('window.__rodioVisualState = {'), 'visual state update missing')
  assert.ok(index.includes('window.earth3d.setDebugLocation(region.lon, region.lat, { center: true })'), 'earth3d centered debug location binding missing')
  assert.ok(index.includes('window.earth3d.setRDLInspectRegion(region.rdlId || null)'), 'RDL inspect binding missing')
})

test('prev and next buttons cycle through regions in order', () => {
  assert.ok(index.includes('let currentEarthAuditIndex = -1'), 'initial audit index should start before first region')
  assert.ok(index.includes('setEarthAuditRegion(currentEarthAuditIndex + 1)'), 'next button does not advance sequence')
  assert.ok(index.includes('setEarthAuditRegion(currentEarthAuditIndex - 1)'), 'prev button does not reverse sequence')
  assert.ok(index.includes('currentEarthAuditIndex = ((index % count) + count) % count'), 'audit sequence does not wrap')
})

test('directional controls nudge the current audit view', () => {
  assert.ok(index.includes('function nudgeAuditView(direction)'), 'audit nudge function missing')
  assert.ok(index.includes("up: [lat + step, lon]"), 'up nudge missing')
  assert.ok(index.includes("left: [lat, lon - step]"), 'left nudge missing')
  assert.ok(index.includes('bindHoldButton(button, () => nudgeAuditView(button.dataset.auditMove))'), 'move buttons are not wired for hold-repeat')
  assert.ok(index.includes('repeatTimer = setInterval(action, 90)'), 'hold repeat interval missing')
})

test('far and near controls set stable distance presets', () => {
  assert.ok(index.includes('function setAuditDistance(level)'), 'stable distance setter missing')
  assert.ok(index.includes("rdlZoomIn.addEventListener('click', () => setAuditDistance(1))"), 'near button should set a fixed near preset')
  assert.ok(index.includes("rdlZoomOut.addEventListener('click', () => setAuditDistance(0.35))"), 'far button should set a fixed far preset')
  const distanceFn = index.slice(index.indexOf('function setAuditDistance(level)'), index.indexOf("rdlZoomIn.addEventListener('click'"))
  assert.ok(!distanceFn.includes('setDebugLocation'), 'distance preset should not recenter the audit region')
})

test('audit angle controls do not recenter the selected region', () => {
  const angleFn = index.slice(index.indexOf('function setAuditAngle(angle)'), index.indexOf('auditAngleButtons.forEach'))
  assert.ok(angleFn.includes('window.earth3d?.setAuditViewAngle?.(angle)'), 'angle setter should call earth3d angle API')
  assert.ok(!angleFn.includes('setDebugLocation'), 'angle preset should not recenter the audit region')
})

test('flat RDL tile preview uses Mapbox POC for Hawaii', () => {
  assert.ok(index.includes('function getRDLTileUrl(rdlId)'), 'RDL tile URL resolver missing')
  assert.ok(index.includes("rdlId === 'hawaii' ? 'tile_noon_air_mapbox.jpg' : 'tile_noon_air.jpg'"), 'Hawaii flat preview should use Mapbox tile')
  assert.ok(index.includes('function updateRDLTilePreview()'), 'RDL tile preview updater missing')
  assert.ok(index.includes("rdlTileViewBtn?.addEventListener('click'"), 'RDL tile preview toggle missing')
})

test('RDL audit regions automatically switch to island-ready mode', () => {
  assert.ok(index.includes("window.earth3d?.setEarthMode?.('NOON_AIR_V2_ISLANDS')"), 'RDL audit mode switch missing')
  assert.ok(index.includes("currentEarthMode = 'NOON_AIR_V2_ISLANDS'"), 'RDL audit UI mode state missing')
})

test('pure view hides atmosphere UI for clarity inspection', () => {
  assert.ok(index.includes('#app.earth-pure-inspection #weather-canvas'), 'pure view should hide weather canvas')
  assert.ok(index.includes('#app.earth-pure-inspection .hero-center'), 'pure view should hide hero title')
  assert.ok(index.includes('#app.earth-pure-inspection .earth-audit-control'), 'pure view should hide audit controls')
  assert.ok(index.includes('#app.earth-pure-inspection .rdl-zoom-label'), 'pure view should keep minimal position label styled')
  assert.ok(index.includes('transform: translateX(-50%)'), 'pure view exit control should be centered, not left-floating')
  assert.ok(index.includes("app.classList.add('earth-pure-inspection')"), 'pure view class activation missing')
  assert.ok(index.includes("app.classList.remove('earth-pure-inspection')"), 'pure view class restore missing')
  assert.ok(index.includes("window.earth3d?.setAtlasFilterMode?.('sharp')"), 'pure view should enable sharp atlas mode')
  assert.ok(index.includes("window.earth3d?.setDebugLocation?.(inspectLon, inspectLat, { center: true })"), 'pure view should recenter current inspection target')
  assert.ok(index.includes('window.earth3d?.setAuditLightingMode?.(true)'), 'pure/audit view should force neutral audit lighting')
})

console.log(`\nResults: ${passed} passed, ${failed} failed\n`)
process.exit(failed > 0 ? 1 : 0)
