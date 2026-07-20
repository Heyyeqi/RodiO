/*
 * celestial_frontend_crosscheck.js — #52 重新设计版 Step 1 交叉验证
 *
 * 目的：验证 earth3d.js 前端的 _computeSubsolarPoint / _computeSublunarPoint
 * 与后端 core/astronomy.js 的 subSolarPoint / subLunarPoint 在"同一时刻"下
 * 给出的经纬度偏差在 1° 以内。
 *
 * 前端公式逐字移植自 pwa/earth3d.js（J2000 角度风格）；后端取自 core/astronomy.js。
 * 采样：以固定基准日的 UTC 0 点起，每 30 分钟一个点，共 48 点覆盖 24 小时。
 *
 * 用法：node celestial_frontend_crosscheck.js
 */
'use strict'
const path = require('path')
const astro = require(path.join(__dirname, '..', '..', '..', 'core', 'astronomy.js'))

const DEG = Math.PI / 180
function normalizeLon(lon) {
  let v = lon
  while (v < -180) v += 360
  while (v > 180) v -= 360
  return v
}
// 经度环形差（考虑 ±180 环绕）
function lonDiff(a, b) {
  let d = Math.abs(((a - b + 540) % 360) - 180)
  return d
}

// ── 前端移植：_computeSubsolarPoint（与 earth3d.js 逐字对应）──
function frontendSubSolar(nowMs) {
  const now = new Date(nowMs)
  const JD = now.getTime() / 86400000 + 2440587.5
  const n = JD - 2451545.0
  const L = (280.46646 + 0.9856474 * n) % 360
  const M = (((357.52911 + 0.98560028 * n) % 360) + 360) % 360
  const Mr = M * DEG
  const C = 1.914602 * Math.sin(Mr) + 0.019993 * Math.sin(2 * Mr) + 0.000289 * Math.sin(3 * Mr)
  const sunLon = L + C
  const omega = 125.04 - 1934.136 * n / 36525
  const lambda = sunLon - 0.00569 - 0.00478 * Math.sin(omega * DEG)
  const lamr = lambda * DEG
  const epsr = (23.439291 - 0.013004 * n / 36525) * DEG
  const decl = Math.asin(Math.sin(epsr) * Math.sin(lamr))
  const ra = Math.atan2(Math.cos(epsr) * Math.sin(lamr), Math.cos(lamr))
  const GMST = ((280.46061837 + 360.98564736629 * n) % 360 + 360) % 360
  const eot = -0.000319 * Math.sin(omega * DEG) - 0.000024 * Math.sin(2 * lamr)
  const GAST = GMST + eot * 180 / Math.PI
  const GHA = ((GAST - ra * 180 / Math.PI) % 360 + 360) % 360
  let subLon = -GHA
  if (subLon < -180) subLon += 360
  else if (subLon > 180) subLon -= 360
  return { lat: decl * 180 / Math.PI, lon: subLon }
}

// ── 前端移植：_computeSublunarPoint（与 earth3d.js 逐字对应，全程弧度）──
function frontendSubLunar(nowMs) {
  const now = new Date(nowMs)
  const JD = now.getTime() / 86400000 + 2440587.5
  const n = JD - 2451545.0
  const d = JD - 2451543.5
  const _2pi = Math.PI * 2
  const norm2pi = (a) => ((a % _2pi) + _2pi) % _2pi
  const node = norm2pi((125.1228 - 0.0529538083 * d) * DEG)
  const incl = 5.1454 * DEG
  const w = norm2pi((318.0634 + 0.1643573223 * d) * DEG)
  const a = 60.2666
  const e = 0.0549
  const M = norm2pi((115.3654 + 13.0649929509 * d) * DEG)
  const eAnomaly = M + e * Math.sin(M) * (1 + e * Math.cos(M))
  const xv = a * (Math.cos(eAnomaly) - e)
  const yv = a * (Math.sqrt(1 - e * e) * Math.sin(eAnomaly))
  const v = Math.atan2(yv, xv)
  const r = Math.sqrt(xv * xv + yv * yv)
  const xh = r * (Math.cos(node) * Math.cos(v + w) - Math.sin(node) * Math.sin(v + w) * Math.cos(incl))
  const yh = r * (Math.sin(node) * Math.cos(v + w) + Math.cos(node) * Math.sin(v + w) * Math.cos(incl))
  const zh = r * Math.sin(v + w) * Math.sin(incl)
  const lonEcl = Math.atan2(yh, xh)
  const latEcl = Math.atan2(zh, Math.sqrt(xh * xh + yh * yh))
  const eps = (23.439291 - 0.013004 * n / 36525) * DEG
  const ra = Math.atan2(
    Math.sin(lonEcl) * Math.cos(eps) - Math.tan(latEcl) * Math.sin(eps),
    Math.cos(lonEcl)
  )
  const dec = Math.asin(
    Math.sin(latEcl) * Math.cos(eps) + Math.cos(latEcl) * Math.sin(eps) * Math.sin(lonEcl)
  )
  const t = n / 36525
  const theta = 280.46061837 + 360.98564736629 * n + 0.000387933 * t * t - (t * t * t) / 38710000
  const gst = norm2pi(theta * DEG)
  const lon = (ra - gst) * 180 / Math.PI
  return { lat: dec * 180 / Math.PI, lon: normalizeLon(lon) }
}

// ── 采样 24 小时 ──
const base = Date.UTC(2026, 6, 20, 0, 0, 0) // 2026-07-20 UTC
const STEP_MS = 30 * 60 * 1000
const N = 48

function summarize(label, feFn, beFn) {
  let maxLat = 0, maxLon = 0, maxTotal = 0
  const rows = []
  for (let k = 0; k <= N; k++) {
    const t = base + k * STEP_MS
    const fe = feFn(t)
    const be = beFn(t)
    const dLat = Math.abs(fe.lat - be.lat)
    const dLon = lonDiff(fe.lon, be.lon)
    const total = Math.sqrt(dLat * dLat + dLon * dLon)
    maxLat = Math.max(maxLat, dLat)
    maxLon = Math.max(maxLon, dLon)
    maxTotal = Math.max(maxTotal, total)
    if (k % 4 === 0) {
      rows.push({ t: new Date(t).toISOString().slice(11, 16) + 'Z', feLat: fe.lat.toFixed(3), beLat: be.lat.toFixed(3), dLat: dLat.toFixed(4), feLon: fe.lon.toFixed(3), beLon: be.lon.toFixed(3), dLon: dLon.toFixed(4) })
    }
  }
  console.log('\n=== ' + label + ' ===')
  console.log('time   feLat    beLat    dLat     feLon    beLon    dLon')
  for (const r of rows) {
    console.log(`${r.t}  ${r.feLat.padStart(7)} ${r.beLat.padStart(7)} ${r.dLat.padStart(7)}  ${r.feLon.padStart(7)} ${r.beLon.padStart(7)} ${r.dLon.padStart(7)}`)
  }
  const pass = maxTotal < 1.0
  console.log(`\n  max |Δlat| = ${maxLat.toFixed(4)}°`)
  console.log(`  max |Δlon| = ${maxLon.toFixed(4)}°  (环形差)`)
  console.log(`  max 合成偏差 = ${maxTotal.toFixed(4)}°  →  ${pass ? 'PASS (<1°)' : 'FAIL (>=1°)'}`)
  return { maxLat, maxLon, maxTotal, pass }
}

const r1 = summarize('前端 _computeSubsolarPoint  vs 后端 subSolarPoint', frontendSubSolar, astro.subSolarPoint)
const r2 = summarize('前端 _computeSublunarPoint vs 后端 subLunarPoint', frontendSubLunar, astro.subLunarPoint)

console.log('\n──────── 汇总 ────────')
console.log(`太阳: max偏差 ${r1.maxTotal.toFixed(4)}°  ${r1.pass ? 'PASS' : 'FAIL'}`)
console.log(`月亮: max偏差 ${r2.maxTotal.toFixed(4)}°  ${r2.pass ? 'PASS' : 'FAIL'}`)
console.log(r1.pass && r2.pass ? '\n✅ 全部交叉验证通过（偏差 < 1°）' : '\n❌ 存在未通过项')
process.exit(r1.pass && r2.pass ? 0 : 1)
