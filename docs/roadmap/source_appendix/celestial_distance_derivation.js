// #52 Phase 1 (redesign batch 1) — 距离/角直径推导（最终版）
const DEG = Math.PI / 180

// ── 真实天文角直径 ──
const R_MOON_KM = 1737.4, D_MOON_KM = 384400
const R_SUN_KM = 696340, D_SUN_KM = 149597870
const REAL_MOON_ANG = 2 * Math.atan(R_MOON_KM / D_MOON_KM) / DEG   // 0.5179°
const REAL_SUN_ANG = 2 * Math.atan(R_SUN_KM / D_SUN_KM) / DEG      // 0.5334°

// ── 渲染倍数（3~6 倍带内）──
const MOON_MULT = 4.5, SUN_MULT = 5.0
const MOON_ANG = MOON_MULT * REAL_MOON_ANG    // 2.3307° (8.3% FOV)
const SUN_ANG = SUN_MULT * REAL_SUN_ANG       // 2.6670° (9.5% FOV)

// ── 固定摆放距离（场景单位，地球半径 R_e=2）──
const R_EARTH = 2
const MOON_DIST = 3    // 月亮距地心 = 1.5 R_earth（真实 60R_e 的艺术压缩）
const SUN_DIST = 6     // 太阳距地心 = 3 R_earth（明显比月亮远）

const FOV_V = 28, HALF_FOV = FOV_V / 2

console.log('═══ #52 天体系统 距离/角直径 推导报告 ═══')
console.log(`真实角直径: 月亮 ${REAL_MOON_ANG.toFixed(4)}°  太阳 ${REAL_SUN_ANG.toFixed(4)}°`)
console.log(`渲染倍数: 月亮 ${MOON_MULT}× → ${MOON_ANG.toFixed(4)}° (${(MOON_ANG/FOV_V*100).toFixed(1)}% 垂直FOV)`)
console.log(`渲染倍数: 太阳 ${SUN_MULT}× → ${SUN_ANG.toFixed(4)}° (${(SUN_ANG/FOV_V*100).toFixed(1)}% 垂直FOV)`)
console.log(`摆放距离: 月亮 ${MOON_DIST} 单位 (${MOON_DIST/R_EARTH} R_e)  太阳 ${SUN_DIST} 单位 (${SUN_DIST/R_EARTH} R_e)`)

// ── 视锥可见性保证 ──
console.log('\n视锥可见性 (max 角偏移 = atan(DIST/camDist) < half-FOV=14°?):')
const comps = [
  ['near (阈值边界)', 20],
  ['farOrbit', 25.15],
  ['deepSpace', 80.01],
]
for (const [name, cd] of comps) {
  const mOff = Math.atan(MOON_DIST / cd) / DEG
  const sOff = Math.atan(SUN_DIST / cd) / DEG
  console.log(`  ${name.padEnd(18)} camDist=${cd.toFixed(2)}  moon偏移${mOff.toFixed(1)}°${mOff<=HALF_FOV?'✓':'✗'}  sun偏移${sOff.toFixed(1)}°${sOff<=HALF_FOV?'✓':'✗'}`)
}

// ── 恒定角直径缩放：世界尺寸随相机距离自适应（每帧实时计算）──
console.log('\n恒定角直径 → 标称世界尺寸:')
for (const [name, cd] of comps) {
  const mCam = cd - MOON_DIST, sCam = cd - SUN_DIST
  const mR = mCam * Math.tan(MOON_ANG * DEG / 2)
  const sD = 2 * sCam * Math.tan(SUN_ANG * DEG / 2)
  console.log(`  ${name.padEnd(18)} moon_r≈${mR.toFixed(3)}  sun_d≈${sD.toFixed(3)}  (cam→body: moon≈${mCam.toFixed(1)} sun≈${sCam.toFixed(1)})`)
}

console.log('\n═══════════════════════════════════════════════════════════')
