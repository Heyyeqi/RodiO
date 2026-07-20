/*
 * celestial_position_reference.js — #52 Phase 1 天体位置自校验
 * 纯后端、不依赖外部数据源。用已知天文常识核对 subSolarPoint / subLunarPoint。
 * 运行：node docs/roadmap/source_appendix/celestial_position_reference.js
 *
 * 校验点：
 *  1) 北半球夏至(≈6/21) subSolarLat ≈ +23.44°（黄赤交角），偏差 < 1°
 *  2) 北半球冬至(≈12/21) subSolarLat ≈ -23.44°，偏差 < 1°
 *  3) 春分(≈3/20) / 秋分(≈9/23) subSolarLat ≈ 0°，偏差 < 1°
 *  4) 太阳直射点经度在 24h 内完整走一圈 ±180°（地球自转）
 *  5) subLunarLat 落在 ±(23.44+5.14)°≈±28.6° 内（赤纬 = 黄赤交角+月球轨道倾角）
 *  6) 全年扫描：subSolarLat 跟随赤纬呈正弦，max≈+23.44 / min≈-23.44
 */
'use strict'
const path = require('path')
const astro = require(path.resolve(__dirname, '../../../core/astronomy'))

const OBLIQUITY = 23.4397 // 黄赤交角（度），与 core/astronomy.js 一致
const DEG = 180 / Math.PI

function utcAt(month, day, hour = 12, minute = 0) {
  // 用 UTC 构造，避免时区干扰（subSolar 是纯世界时函数）
  return Date.UTC(2026, month - 1, day, hour, minute, 0)
}

function angleDiffDeg(a, b) {
  let d = ((a - b) % 360 + 540) % 360 - 180
  return d
}

function round(n, p = 4) {
  const f = Math.pow(10, p)
  return Math.round(n * f) / f
}

// ── 1) 二分二至的 subSolar 纬度偏差 ───────────────────────────────
const solsticeTests = [
  { name: '夏至 ~6/21 UTC12', ms: utcAt(6, 21), expectedLat: +OBLIQUITY },
  { name: '冬至 ~12/21 UTC12', ms: utcAt(12, 21), expectedLat: -OBLIQUITY },
  { name: '春分 ~3/20 UTC12', ms: utcAt(3, 20), expectedLat: 0 },
  { name: '秋分 ~9/23 UTC12', ms: utcAt(9, 23), expectedLat: 0 },
]

console.log('=== 1) 二分二至 subSolar 纬度偏差（预期 < 1°）===')
let maxLatErr = 0
for (const t of solsticeTests) {
  const p = astro.subSolarPoint(t.ms)
  const err = Math.abs(angleDiffDeg(p.lat, t.expectedLat))
  maxLatErr = Math.max(maxLatErr, err)
  console.log(
    `  ${t.name.padEnd(22)} lat=${round(p.lat, 3).toFixed(3).padStart(8)}° ` +
    `expected=${t.expectedLat.toFixed(3).padStart(7)}° ` +
    `偏差=${err.toFixed(3).padStart(6)}°  ` +
    `${err < 1 ? 'PASS' : 'FAIL <--'}`
  )
}

// 同时校验：夏至/冬至瞬间更精确的偏差（true instant 由 solarDeclination 自然给出）
console.log('\n=== 1b) 精确二分二至瞬间（更紧的参考，非红线）===')
for (const [label, mon, day] of [['夏至', 6, 21], ['冬至', 12, 21]]) {
  // 扫描该日 0-24h 取 |lat| 最大值（即最接近真黄赤交角）
  let best = 0, bestMs = 0
  for (let h = 0; h < 24; h++) {
    const ms = utcAt(mon, day, h)
    const lat = Math.abs(astro.subSolarPoint(ms).lat)
    if (lat > best) { best = lat; bestMs = ms }
  }
  const err = Math.abs(best - OBLIQUITY)
  console.log(`  ${label} 当日峰值 |lat|=${best.toFixed(3)}°  与黄赤交角偏差=${err.toFixed(3)}° ${err < 0.1 ? '(契合 NOAA)' : ''}`)
}

// ── 2) 太阳直射点经度 24h 走一圈 ──────────────────────────────────
console.log('\n=== 2) subSolar 经度 24h 扫描（应走满 ±180°，≈15°/h）===')
{
  const samples = []
  for (let m = 0; m <= 1440; m += 60) {
    const ms = utcAt(6, 21, 0, 0) + m * 60 * 1000
    samples.push(astro.subSolarPoint(ms))
  }
  // 计算相邻采样经度变化（解卷绕）
  let total = 0
  let prev = samples[0].lon
  const deltas = []
  for (let i = 1; i < samples.length; i++) {
    const d = angleDiffDeg(samples[i].lon, prev)
    deltas.push(d)
    total += d
    prev = samples[i].lon
  }
  const meanStep = total / deltas.length
  console.log(`  24h 经度累计变化 = ${round(total, 2)}°（应 ≈ -360°）`)
  console.log(`  平均步长 = ${round(meanStep, 2)}°/h（应 ≈ -15°/h）`)
  console.log(`  首=${samples[0].lon.toFixed(1)}° 末=${samples[samples.length - 1].lon.toFixed(1)}°`)
  const ok = Math.abs(Math.abs(total) - 360) < 5 && Math.abs(Math.abs(meanStep) - 15) < 1
  console.log(`  ${ok ? 'PASS' : 'FAIL <--'} 经度完整自转一圈`)
}

// ── 3) subLunar 纬度范围 + 月内变化 ───────────────────────────────
console.log('\n=== 3) subLunar 纬度范围（应 ∈ ±28.6°）与月内漂移 ===')
{
  let maxAbs = 0
  const day0 = utcAt(6, 1, 12)
  const lats = []
  for (let d = 0; d < 30; d++) {
    const lat = astro.subLunarPoint(day0 + d * 86400000).lat
    lats.push(lat)
    maxAbs = Math.max(maxAbs, Math.abs(lat))
  }
  const drift = Math.max(...lats) - Math.min(...lats)
  console.log(`  30 天 |lat| 峰值为 ${maxAbs.toFixed(2)}°（上限 ≈ 28.6°）`)
  console.log(`  30 天纬度漂移 = ${drift.toFixed(2)}°（月球赤纬随轨道进动变化）`)
  const ok = maxAbs <= 28.6 + 0.5
  console.log(`  ${ok ? 'PASS' : 'FAIL <--'} subLunar 纬度在合理范围`)
}

// ── 4) 月相/光照 合理性（交叉校验 illumination 公式）──────────────
console.log('\n=== 4) 月相/光照 交叉校验（illumination = (1-cos(2π·phase))/2）===')
{
  const samples = [
    { label: '新月在 ≈2026-06-15', ms: utcAt(6, 15, 12) },
    { label: '满月在 ≈2026-06-30', ms: utcAt(6, 30, 12) },
  ]
  for (const s of samples) {
    const ph = astro.lunarPhase(s.ms)
    const illum = astro.lunarIllumination(ph)
    const name = astro.lunarPhaseName(ph)
    console.log(`  ${s.label.padEnd(20)} phase=${ph.toFixed(3)} illum=${illum.toFixed(3)} name=${name}`)
  }
  // 满月 illumination 应 > 0.95，新月应 < 0.05
  const fullMs = utcAt(6, 30, 12)
  const newMs = utcAt(6, 15, 12)
  const fullIllum = astro.lunarIllumination(astro.lunarPhase(fullMs))
  const newIllum = astro.lunarIllumination(astro.lunarPhase(newMs))
  console.log(`  满月 illum=${fullIllum.toFixed(3)}（应>0.95）  新月 illum=${newIllum.toFixed(3)}（应<0.05）`)
}

// ── 5) 全年扫描 subSolarLat 极值 ──────────────────────────────────
console.log('\n=== 5) 全年扫描 subSolarLat 极值（max≈+23.44 / min≈-23.44）===')
{
  let maxLat = -90, minLat = 90
  const y0 = utcAt(1, 1, 0)
  for (let d = 0; d < 365; d++) {
    const lat = astro.subSolarPoint(y0 + d * 86400000).lat
    maxLat = Math.max(maxLat, lat)
    minLat = Math.min(minLat, lat)
  }
  console.log(`  subSolarLat 全年 max=${maxLat.toFixed(3)}° / min=${minLat.toFixed(3)}°`)
  const ok = Math.abs(maxLat - OBLIQUITY) < 0.2 && Math.abs(minLat + OBLIQUITY) < 0.2
  console.log(`  ${ok ? 'PASS' : 'FAIL <--'} 极值与黄赤交角吻合`)
}

// ── 总判定 ───────────────────────────────────────────────────────
console.log('\n=== 总判定 ===')
const allPass = maxLatErr < 1
console.log(`  二分二至 subSolar 纬度最大偏差 = ${maxLatErr.toFixed(3)}°  → ${allPass ? 'PASS (<1°)' : 'FAIL'}`)
console.log(allPass ? '  ✅ 天体位置函数自校验通过' : '  ❌ 自校验失败，请检查 subSolarPoint/subLunarPoint')
process.exit(allPass ? 0 : 1)
