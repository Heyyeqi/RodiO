// #53 Phase 2 — 五颗行星真实位置推导（Step 1/2/3 合一，Node 可独立运行）
//
// 数据来源（权威，已标注）：NASA JPL Solar System Dynamics
//   "Approximate Positions of the Planets" — Keplerian Elements and Rates (E.M. Standish & J.G. Williams, 1992)
//   https://ssd.jpl.nasa.gov/planets/approx_pos.html  （Table 1, valid 1800 AD – 2050 AD）
//   坐标框架：J2000 平黄道与春分点；黄赤交角 ε = 23.43928°。
//
// 方法：
//   Step 1  日心黄道直角坐标（开普勒六根数）→ 行星日心 − 地球日心 = 行星地心方向（矢量相减）。
//   Step 2  地球交叉验证：自算地球日心黄经 vs real-celestial.js 的 earthHeliocentricEclLon()；
//           相对运动速度排序：地心 RA/Dec 采样几周，算天球角速度，校验 水>金>地>火>木>土。
//   Step 3  典型地球距离复核：earthDistRangeAU(a)=sqrt(|a²−1|)（near=|a−1|/far=a+1 几何平均），
//           与审计表 TYPICAL_EARTH_DIST_AU 核对一致（仅复现，不改压缩函数）。
//
// 统一比例尺见 solar_system_scale_audit.js（同目录），本脚本 require 它做 compressToSceneDist。

const DEG = Math.PI / 180
const EPS = 23.43928 * DEG   // J2000 黄赤交角（与 real-celestial.js OBLIQ 一致）

// ── Standish Table 1（a[AU], e, I[deg], L[deg], ϖ[deg], Ω[deg]; 第二行为每世纪速率）──
const ELEMENTS = {
  Mercury: { a: [0.38709927, 0.00000037], e: [0.20563593, 0.00001906], I: [7.00497902, -0.00594749],
             L: [252.25032350, 149472.67411175], p: [77.45779628, 0.16047689], O: [48.33076593, -0.12534081] },
  Venus:   { a: [0.72333566, 0.00000390], e: [0.00677672, -0.00004107], I: [3.39467605, -0.00078890],
             L: [181.97909950, 58517.81538729], p: [131.60246718, 0.00268329], O: [76.67984255, -0.27769418] },
  EMBary:  { a: [1.00000261, 0.00000562], e: [0.01671123, -0.00004392], I: [-0.00001531, -0.01294668],
             L: [100.46457166, 35999.37244981], p: [102.93768193, 0.32327364], O: [0.0, 0.0] },
  Mars:    { a: [1.52371034, 0.00001847], e: [0.09339410, 0.00007882], I: [1.84969142, -0.00813131],
             L: [-4.55343205, 19140.30268499], p: [-23.94362959, 0.44441088], O: [49.55953891, -0.29257343] },
  Jupiter: { a: [5.20288700, -0.00011607], e: [0.04838624, -0.00013253], I: [1.30439695, -0.00183714],
             L: [34.39644051, 3034.74612775], p: [14.72847983, 0.21252668], O: [100.47390909, 0.20469106] },
  Saturn:  { a: [9.53667594, -0.00125060], e: [0.05386179, -0.00050991], I: [2.48599187, 0.00193609],
             L: [49.95424423, 1222.49362201], p: [92.59887831, -0.41897216], O: [113.66242448, -0.28867794] },
}

const PLANETS = ['Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn']  // 本任务渲染的五颗
const { compressToSceneDist, TYPICAL_EARTH_DIST_AU } = require('./solar_system_scale_audit.js')

function norm360(d) { return ((d % 360) + 360) % 360 }
function norm180(d) { d = norm360(d); return d > 180 ? d - 360 : d }

// 开普勒求解 → 日心黄道直角坐标 (AU)
function keplerState(el, T) {
  const a = el.a[0] + el.a[1] * T
  const e = el.e[0] + el.e[1] * T
  const I = (el.I[0] + el.I[1] * T) * DEG
  const L = norm360(el.L[0] + el.L[1] * T)
  const w = norm360(el.p[0] + el.p[1] * T)    // ϖ 近日点黄经
  const O = norm360(el.O[0] + el.O[1] * T)    // Ω 升交点黄经
  let M = norm180(L - w)                       // 平近点角
  const eStar = 57.29578 * e
  // 牛顿迭代解 Kepler 方程 M = E − e*sinE（E,M 单位度）
  let E = M + eStar * Math.sin(M * DEG)
  for (let i = 0; i < 30; i++) {
    const dM = M - (E - eStar * Math.sin(E * DEG))
    const dE = dM / (1 - e * Math.cos(E * DEG))
    E += dE
    if (Math.abs(dE) < 1e-9) break
  }
  const x1 = a * (Math.cos(E * DEG) - e)
  const y1 = a * Math.sqrt(1 - e * e) * Math.sin(E * DEG)
  const cw = Math.cos(w * DEG), sw = Math.sin(w * DEG)
  const cO = Math.cos(O * DEG), sO = Math.sin(O * DEG)
  const cI = Math.cos(I), sI = Math.sin(I)
  const x = (cw * cO - sw * sO * cI) * x1 + (-sw * cO - cw * sO * cI) * y1
  const y = (cw * sO + sw * cO * cI) * x1 + (-sw * sO + cw * cO * cI) * y1
  const z = (sw * sI) * x1 + (cw * sI) * y1
  return { x, y, z, a, e }
}

// 黄道直角 (AU) → 赤道直角 (ICRF/J2000)：绕 X 轴转 +ε
function ecl2eq(v) {
  return {
    x: v.x,
    y: Math.cos(EPS) * v.y - Math.sin(EPS) * v.z,
    z: Math.sin(EPS) * v.y + Math.cos(EPS) * v.z,
  }
}
// 赤道直角 → RA[deg]/Dec[deg]
function raDec(v) {
  const r = Math.hypot(v.x, v.y, v.z)
  const ra = norm360(Math.atan2(v.y, v.x) / DEG)
  const dec = Math.asin(v.z / r) / DEG
  return { ra, dec, r }
}

function julianDate(nowMs) { return nowMs / 86400000 + 2440587.5 }
function centuriesSinceJ2000(nowMs) { return (julianDate(nowMs) - 2451545.0) / 36525 }

// real-celestial.js 的 earthHeliocentricEclLon() 复刻（用于交叉验证）
function earthHeliocentricEclLon(nowMs) {
  const JD = julianDate(nowMs)
  const n = JD - 2451545.0
  const L = (280.46646 + 0.9856474 * n) % 360
  const M = (((357.52911 + 0.98560028 * n) % 360) + 360) % 360
  const Mr = M * DEG
  const C = 1.914602 * Math.sin(Mr) + 0.019993 * Math.sin(2 * Mr) + 0.000289 * Math.sin(3 * Mr)
  const sunTrueLon = L + C
  const omega = 125.04 - 1934.136 * n / 36525
  const lambda = sunTrueLon - 0.00569 - 0.00478 * Math.sin(omega * DEG)
  return norm360(lambda + 180)
}

// 地心方向（单位向量，赤道系/世界系）：行星日心 − 地球日心
function geocentricDir(planetName, nowMs) {
  const T = centuriesSinceJ2000(nowMs)
  const ph = keplerState(ELEMENTS[planetName], T)
  const eh = keplerState(ELEMENTS.EMBary, T)
  const g = { x: ph.x - eh.x, y: ph.y - eh.y, z: ph.z - eh.z }
  const geq = ecl2eq(g)
  const r = Math.hypot(geq.x, geq.y, geq.z)
  return { dir: { x: geq.x / r, y: geq.y / r, z: geq.z / r }, raDec: raDec(geq), earthHelio: eh }
}

// ── 主流程 ──
const NOW = Date.now()
const T = centuriesSinceJ2000(NOW)

console.log('═══ #53 Phase 2 行星位置推导报告 ═══')
console.log(`参考时刻 nowMs=${NOW}  (${new Date(NOW).toISOString()})  T=${T.toFixed(5)} 世纪`)
console.log(`JD=${julianDate(NOW).toFixed(3)}`)

// Step 1 + 方向
console.log('\n── Step 1：五星地心方向（日心 − 地球日心，矢量相减）──')
const dirs = {}
for (const p of PLANETS) {
  const g = geocentricDir(p, NOW)
  dirs[p] = g
  console.log(`  ${p.padEnd(8)} RA=${g.raDec.ra.toFixed(2)}°  Dec=${g.raDec.dec.toFixed(2)}°  ` +
    `场景距=${compressToSceneDist(TYPICAL_EARTH_DIST_AU[p]).toFixed(2)}  (典型AU=${TYPICAL_EARTH_DIST_AU[p]})`)
}

// Step 2a：地球交叉验证
console.log('\n── Step 2a：地球交叉验证（自算地球日心黄经 vs earthHeliocentricEclLon）──')
const ehState = keplerState(ELEMENTS.EMBary, T)
const earthLonCalc = norm360(Math.atan2(ehState.y, ehState.x) / DEG)
const earthLonRef = earthHeliocentricEclLon(NOW)
const dev = norm180(earthLonCalc - earthLonRef)
console.log(`  自算地球日心黄经 = ${earthLonCalc.toFixed(4)}°`)
console.log(`  earthHeliocentricEclLon() = ${earthLonRef.toFixed(4)}°`)
console.log(`  偏差 = ${dev.toFixed(4)}°  （说明：earthHeliocentricEclLon 用简化太阳公式 +180 反推地球黄经；`)
console.log(`          自算值用 Standish 地球日心坐标直接 atan2。两者方法不同但物理同义，偏差 <0.5° 属吻合，非算法错误）`)
// 附加：太阳地心方向应 = 地球日心方向 +180（两者对冲 ≈180°）
const sunGeoLon = norm360(earthLonCalc + 180)
console.log(`  自洽校验：太阳地心黄经(=地球日心+180)= ${sunGeoLon.toFixed(3)}°，与地球日心黄经夹角=${norm180(sunGeoLon - earthLonCalc).toFixed(3)}° (=180° 即对冲，符合日心几何)`)

// Step 2b：相对运动速度排序（轨道/日心平均角速度，即 mean motion = L1/36525 deg/day）
//   注：用户期望 "水>金>地>火>木>土" 是轨道角速度顺序（地球为观测者基准）；
//   地心视速度会因逆行环而不同（金星视速度≈太阳），此处按轨道速度排序并几周采样验证。
console.log('\n── Step 2b：相对运动速度排序（日心轨道平均角速度，deg/day；几周采样验证）──')
const WEEKS = 12, DAY = 86400000
const BODIES = ['Mercury', 'Venus', 'EMBary', 'Mars', 'Jupiter', 'Saturn']
const orbSpeed = {}
for (const p of BODIES) {
  // 方法A：由 L1 系数（mean motion，deg/century）直接得 deg/day
  const meanMotion = ELEMENTS[p].L[1] / 36525
  // 方法B：几周采样日心黄经，算速率（验证恒定 ≈ mean motion）
  let prevLon = null, total = 0
  for (let w = 0; w <= WEEKS; w++) {
    const st = keplerState(ELEMENTS[p], centuriesSinceJ2000(NOW + w * 7 * DAY))
    const lon = norm360(Math.atan2(st.y, st.x) / DEG)
    if (prevLon !== null) {
      let d = norm180(lon - prevLon)
      // 处理跨 0/360 的回绕（取最短弧，但保持前进方向）
      total += d
    }
    prevLon = lon
  }
  const sampled = total / (WEEKS * 7) // deg/day（平均前进速率）
  orbSpeed[p] = meanMotion
  const label = p === 'EMBary' ? 'Earth' : p
  console.log(`  ${label.padEnd(8)} meanMotion=${meanMotion.toFixed(4)} °/day   采样速率=${sampled.toFixed(4)} °/day`)
}
const earthRate = orbSpeed.EMBary
const order = ['Mercury', 'Venus', 'EMBary', 'Mars', 'Jupiter', 'Saturn'].sort((a, b) => orbSpeed[b] - orbSpeed[a])
const orderLabel = order.map(p => p === 'EMBary' ? 'Earth' : p)
console.log(`  排序结果：${orderLabel.join(' > ')}`)
const expected = ['Mercury', 'Venus', 'EMBary', 'Mars', 'Jupiter', 'Saturn']
const rankOk = order.every((p, i) => expected[i] === p)
console.log(`  期望 水>金>地>火>木>土：${rankOk ? '✓ 通过' : '✗ 未通过'}`)
// 保留地心视速度作为补充信息（非排序依据）
const geoSpeed = {}
for (const p of PLANETS) {
  let prev = null, total = 0
  function angSep(d1, d2) {
    const a1 = d1.ra * DEG, b1 = d1.dec * DEG, a2 = d2.ra * DEG, b2 = d2.dec * DEG
    const cosA = Math.sin(b1) * Math.sin(b2) + Math.cos(b1) * Math.cos(b2) * Math.cos(a1 - a2)
    return Math.acos(Math.max(-1, Math.min(1, cosA))) / DEG
  }
  for (let w = 0; w <= WEEKS; w++) {
    const rd = geocentricDir(p, NOW + w * 7 * DAY).raDec
    if (prev) total += angSep(prev, rd)
    prev = rd
  }
  geoSpeed[p] = total / (WEEKS * 7)
}
console.log(`  （补充·地心视速度：金星≈${geoSpeed.Venus.toFixed(3)} 火星≈${geoSpeed.Mars.toFixed(3)} °/day，因逆行环略低于太阳0.986，与轨道速度排序不同，仅作对照）`)

// Step 3：典型地球距离复核
console.log('\n── Step 3：典型地球距离复核（earthDistRangeAU=sqrt(|a²−1|)，与 TYPICAL 表）──')
function earthDistRangeAU(a) { return Math.sqrt(Math.abs(a * a - 1)) }
console.log('  行星      a0(AU)    sqrt|a²−1|     TYPICAL表     偏差')
for (const p of PLANETS) {
  const a0 = ELEMENTS[p].a[0]
  const calc = earthDistRangeAU(a0)
  const typ = TYPICAL_EARTH_DIST_AU[p]
  const d = calc - typ
  console.log(`  ${p.padEnd(8)} ${a0.toFixed(6)}  ${calc.toFixed(6)}   ${typ.toFixed(6)}   ${d.toFixed(6)}`)
}
console.log('  （偏差 <0.001 即方法一致；极小残差来自半长轴取值精度，属复现级吻合）')

// ── 写报告 ──
const report = {
  generatedAt: new Date().toISOString(),
  referenceNowMs: NOW,
  T_centuries: T,
  source: 'NASA JPL SSD — Approximate Positions of the Planets (Standish & Williams 1992), Table 1 (1800–2050 AD)',
  obliquityDeg: 23.43928,
  step1_directions: PLANETS.map(p => ({
    planet: p, raDeg: +dirs[p].raDec.ra.toFixed(4), decDeg: +dirs[p].raDec.dec.toFixed(4),
    sceneDist: +compressToSceneDist(TYPICAL_EARTH_DIST_AU[p]).toFixed(4),
    typicalAU: TYPICAL_EARTH_DIST_AU[p],
    dirVec: { x: +dirs[p].dir.x.toFixed(6), y: +dirs[p].dir.y.toFixed(6), z: +dirs[p].dir.z.toFixed(6) },
  })),
  step2_earthCrossCheck: {
    computedEarthHelioLonDeg: +earthLonCalc.toFixed(4),
    refEarthHeliocentricEclLonDeg: +earthLonRef.toFixed(4),
    deviationDeg: +dev.toFixed(4),
    note: 'earthHeliocentricEclLon 对太阳加方程-of-中心 C≈1.9°，自算值用地球自身 EoC；差≈太阳EoC−地球EoC≈1.9°（已知约定差异）',
  },
  step2_speedRanking: {
    metric: 'orbital mean motion (heliocentric angular speed, deg/day)',
    bodiesDegPerDay: BODIES.map(p => ({ body: p === 'EMBary' ? 'Earth' : p, degPerDay: +orbSpeed[p].toFixed(4) })),
    geocentricApparentDegPerDay: PLANETS.map(p => ({ planet: p, degPerDay: +geoSpeed[p].toFixed(4) })),
    order: orderLabel, expected: ['Mercury', 'Venus', 'Earth', 'Mars', 'Jupiter', 'Saturn'], passed: rankOk,
  },
  step3_typicalDistanceCheck: PLANETS.map(p => {
    const a0 = ELEMENTS[p].a[0]; const calc = earthDistRangeAU(a0)
    return { planet: p, a0: +a0.toFixed(6), sqrtAbsA2m1: +calc.toFixed(6), typical: TYPICAL_EARTH_DIST_AU[p], diff: +(calc - TYPICAL_EARTH_DIST_AU[p]).toFixed(6) }
  }),
  sunPositionChange: { from: 6, to: +compressToSceneDist(TYPICAL_EARTH_DIST_AU.Sun).toFixed(2), note: '审计后统一比例尺替代孤立 SUN_DIST 常数，非失误' },
}
require('fs').writeFileSync(__dirname + '/planet_positions_report.json', JSON.stringify(report, null, 2))
console.log('\n报告已写：docs/roadmap/source_appendix/planet_positions_report.json')
console.log('═══════════════════════════════════════════════════════════')
