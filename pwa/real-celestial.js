/*
 * real-celestial.js — #52 Phase 1（重新设计版 第一批）天体系统：太阳 + 月亮可见化
 *
 * 激活：仅当 URL 含 ?earthCandidate=realCelestial（跟 horizon-lab.js 同一个门控模式）。
 * 红线：不修改 earth3d.js 任何现有 mesh/theme/sunDirection 逻辑（仅新增只读 getter + 算法函数）。
 *
 * 设计要点（相对上版的彻底重做）：
 *  ── 摆放参照系：以"地球中心（世界坐标）"为参照，位置 = earthCenter + 真实方向 × 压缩后距离。
 *     不再使用上一版的"相机位置 + 固定深度"HUD 写法（那种以相机为参照、clamp+反投影的做法已废弃）。
 *  ── 真实方向来源：太阳用 earth3d 的 _computeSubsolarPoint()（前端权威来源，与后端 core/astronomy.js
 *     的 subSolarPoint() 经交叉验证偏差 <1°）；月亮用同风格移植的 _computeSublunarPoint()。
 *     方向换算 world 单位向量时，复用 earth3d 内部 updateSunPosition 的同一公式（不乘 earth.quaternion），
 *     保证太阳天光晕正好落在受光半球正上方（与现有 FAR_VIEW 光照一致）。
 *  ── 距离分档可见性（按"相机到地心的实际直线距离"，不按构图名字，三档独立）：
 *       MOON_VISIBLE_DIST = 35, MOON_HIDE_DIST = 65
 *         → 相机距 ∈ [35,65) 显示月亮（moonView 48 / lunarHalo 58 在内，farOrbit 25.15 与 deepSpace 80 越过隐藏）
 *       SUN_VISIBLE_DIST  = 50  → 相机距 ≥50 显示太阳（覆盖 deepSpace 80，高于 farOrbit 25.15）
 *       PLANETS_VISIBLE_DIST = 70 → 相机距 ≥70 显示行星（独立于太阳，仅 deepSpace）
 *     阈值命名遵循可扩展模式 XXX_VISIBLE_DIST / XXX_HIDE_DIST：新构图/新天体只需加一对常量。
 *     这样新构图（如 #40 Flight View）只要算出的距离落在对应区间就自动生效，不用改判断逻辑。
 *  ── 压缩距离（艺术化，但自洽、可推导）：
 *       月亮放置距离 = MOON_PLACE_FRAC(0.45) × 相机→地球距离 → farOrbit≈11.3 / deepSpace≈36
 *       太阳放置距离 = SUN_PLACE_FRAC(0.70) × 相机→地球距离 → deepSpace≈56（明显比月亮远）
 *  ── 角直径恒定缩放（关键，杜绝上一版 22×/38× 失控）：
 *       每帧按"相机到天体距离"缩放天体世界尺寸，使渲染角直径恒等于
 *       月亮 = REAL_MOON_ANG × 4.5 ≈ 2.33°（垂直FOV 8.3%）、太阳 = REAL_SUN_ANG × 5.0 ≈ 2.67°（9.5%）。
 *       世界半径 = 相机距 × tan(角直径/2)。任意轨道位置都精确等于选取倍数，绝不会越界。
 *  ── 复用（不重做）：太阳光晕 shader（makeSunGlowTexture 程序生成径向渐变 + AdditiveBlending）、
 *     月亮相位 shader（MOON_VERT/MOON_FRAG 真实 terminator）、真实月球贴图 moon_lroc_color_2k.jpg（LROC WAC 2k 自然色，2025 CGI Moon Kit）。
 *  ── 月相：uSunDir = 世界坐标 (太阳位置 − 月亮位置) 归一化，相位形状随 now 真实变化。
 */
(function () {
  'use strict'
  const T = self.THREE
  if (!T) { console.error('[realCelestial] THREE 未加载，跳过'); return }

  const params = new URLSearchParams(window.location.search)
  if (params.get('earthCandidate') !== 'realCelestial') return // 红线：不影响正常用户

  // ── 命名常量（不散落魔法数字）──
  // 三档拆分可见性（按"相机到地心的实际直线距离"，不按构图名字）。
  // 阈值命名遵循可扩展模式 XXX_VISIBLE_DIST / XXX_HIDE_DIST：未来新增构图或新天体
  // 只需加一对常量 + 一行判断，无需重设计。当前各档边界（场景单位，相机距地心）：
  //   月亮 : [MOON_VISIBLE_DIST(35), MOON_HIDE_DIST(65))   → moonView 48 / lunarHalo 58 可见，farOrbit 25.15 与 deepSpace 80 越过隐藏
  //   太阳 : [SUN_VISIBLE_DIST(50),  ∞)                     → 不变（覆盖 deepSpace 80）
  //   行星 : [PLANETS_VISIBLE_DIST(70), ∞)                  → 独立于太阳阈值，仅 deepSpace
  const MOON_VISIBLE_DIST = 35   // 相机距地心 ≥ 此值 → 月亮可见（moonView 48 / lunarHalo 58 在内；farOrbit 25.15 与 deepSpace 80 越过 → 隐藏）
  const MOON_HIDE_DIST = 65      // 相机距地心 ≥ 此值 → 月亮隐藏（deepSpace 80 越过，避免与太阳/行星拥挤）
  const SUN_VISIBLE_DIST = 50    // 相机距地心 ≥ 此值 → 太阳可见（覆盖 deepSpace 80，高于 farOrbit 25.15）
  const PLANETS_VISIBLE_DIST = 70 // 相机距地心 ≥ 此值 → 行星可见（不再与太阳共用阈值，仅 deepSpace）

  // 固定摆放距离（场景单位，地球半径=2）。不随相机比例，保证合格构图视锥内可见：
  //   月亮：MOON_DIST=6 → 与地球(半径2)明显分离（不再贴着/穿透）。
  //        moonView(48): 最大角偏移 asin(6/48)=7.2° << FOV/2(14°)，任意方向完整在框。lunarHalo(58): atan(6/58)=5.9° 余量更大。
  //        farOrbit(25.15) 与 deepSpace(80) 下月亮已被隐藏（MOON_VISIBLE_DIST=35 越过），无需考虑。
  //   太阳：SUN_DIST≈12.25（审计后）；deepSpace(80): atan(12.25/80)=8.7° < 14°。
  const MOON_DIST = 6            // 月亮距地心 = 3 R_earth（真实 60R_e 的艺术压缩；原 3 → 6 拉开视觉分离）

  // ── #53 Phase 2 统一距离比例尺（审计锁定，见 solar_system_scale_audit.js）──
  // 约束：deepSpace 相机距地心 80.01，FOV 28°，半 FOV 14°，硬上限 = 80.01*tan14° = 19.95；
  //       安全上限 = 19.95*0.9 = 17.95（留边界）。对数压缩，锚 Moon=3（#52 已验证），
  //       端点 Pluto=17.95。太阳位置由孤立常数 6 改为 compressToSceneDist(1.0)≈12.25 ——
  //       这是审计后统一比例尺的有意调整（替代孤立 SUN_DIST），非失误。
  const SCALE_MOON_DIST = 3
  const SCALE_SAFE_MAX = 17.95
  const SCALE_TYPICAL_AU = {
    Moon: 0.00257, Venus: 0.6908797145583455, Mercury: 0.9220797145583455, Sun: 1.0,
    Mars: 1.1500330430035477, Jupiter: 5.105997356051019, Saturn: 9.484427710726674,
    Uranus: 19.16492841103248, Neptune: 30.052366978326347, Pluto: 39.4693339695516,
  }
  const _scaleLogMoon = Math.log10(SCALE_TYPICAL_AU.Moon)
  const _scaleLogPluto = Math.log10(SCALE_TYPICAL_AU.Pluto)
  const _scaleSlope = (SCALE_SAFE_MAX - SCALE_MOON_DIST) / (_scaleLogPluto - _scaleLogMoon)
  function compressToSceneDist(au) {
    return SCALE_MOON_DIST + _scaleSlope * (Math.log10(au) - _scaleLogMoon)
  }

  const SUN_DIST = compressToSceneDist(SCALE_TYPICAL_AU.Sun) // ≈12.25（审计后；原孤立常数=6）
  const MOON_ANG_DIAM_MULT = 4.5 // 月亮渲染角直径 = 4.5 × 真实
  const SUN_ANG_DIAM_MULT = 5.0  // 太阳渲染角直径 = 5.0 × 真实
  const MOON_TINT = [0.62, 0.585, 0.53] // 自然月色（暖灰，月球实测真色）

  // 真实天文角直径（度）
  const R_MOON_KM = 1737.4, D_MOON_KM = 384400
  const R_SUN_KM = 696340, D_SUN_KM = 149597870
  const REAL_MOON_ANG = 2 * Math.atan(R_MOON_KM / D_MOON_KM) * 180 / Math.PI
  const REAL_SUN_ANG = 2 * Math.atan(R_SUN_KM / D_SUN_KM) * 180 / Math.PI
  const MOON_ANG_DIAM = MOON_ANG_DIAM_MULT * REAL_MOON_ANG
  const SUN_ANG_DIAM = SUN_ANG_DIAM_MULT * REAL_SUN_ANG
  const DEG = Math.PI / 180

  // ── Phase 1 收尾：地球公转可视化（独立视觉语言，仅 deepSpace 可见）──
  // 红线：不触碰上方太阳/月亮任何逻辑（摆放/角直径/月相），此处只新增"轨道环 + 地球标记"。
  // 与 near-field 太阳晕是两套独立语言，允许共存、不必物理一致。
  const ORBIT_RING_DIST = 8        // 轨道环半径（场景单位，地球半径=2；> SUN_DIST=6，环包住太阳晕）
  const ORBIT_RING_WIDTH = 0.18    // 柔边光带半宽（innerR=dist-width, outerR=dist+width）
  const ORBIT_RING_COLOR = 0x7fa8d0 // 环色（克制、不抢戏）
  const MARKER_BASE_SIZE = 0.62    // 地球标记呼吸光点基准世界尺寸
  const OBLIQ = 23.4393 * DEG      // 黄赤交角（低精度，足够示意）

  // 太阳径向渐变光晕贴图（程序生成 CanvasTexture，避免外部依赖）
  function makeSunGlowTexture() {
    const s = 256
    const c = document.createElement('canvas')
    c.width = c.height = s
    const g = c.getContext('2d')
    const grad = g.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2)
    grad.addColorStop(0.00, 'rgba(255,255,255,1.00)')
    grad.addColorStop(0.10, 'rgba(255,250,232,0.96)')
    grad.addColorStop(0.26, 'rgba(255,214,140,0.62)')
    grad.addColorStop(0.50, 'rgba(255,160,70,0.22)')
    grad.addColorStop(0.75, 'rgba(255,130,55,0.06)')
    grad.addColorStop(1.00, 'rgba(255,120,40,0.00)')
    g.fillStyle = grad
    g.fillRect(0, 0, s, s)
    return new T.CanvasTexture(c)
  }

  const MOON_VERT = `
    varying vec2 vUv;
    varying vec3 vWorldNormal;
    void main() {
      vUv = uv;
      // 月亮无自转且作为 scene 子节点（无父旋转），物体空间法线即世界法线
      vWorldNormal = normalize(normalMatrix * normal);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `
  const MOON_FRAG = `
    precision highp float;
    uniform sampler2D uTex;
    uniform vec3 uSunDir;   // 月亮 → 太阳 方向（world-frame）
    uniform float uAmbient; // 地照(earthshine)微弱环境光
    uniform vec3 uTint;
    varying vec2 vUv;
    varying vec3 vWorldNormal;
    void main() {
      vec3 tex = texture2D(uTex, vUv).rgb;
      vec3 base = tex * uTint;                 // 真实月面细节 × 自然月色
      float ndl = dot(normalize(vWorldNormal), normalize(uSunDir));
      // 柔和 terminator：明暗交界用 smoothstep 过渡，避免硬边
      float term = smoothstep(-0.08, 0.18, ndl);
      vec3 col = base * (uAmbient + (1.0 - uAmbient) * term);
      gl_FragColor = vec4(col, 1.0);
    }
  `

  function round(n, p) { const f = Math.pow(10, p || 2); return Math.round(n * f) / f }

  // ════════════════════════════════════════════════════════════════════
  // #53 Phase 2 — 五颗行星（金星/水星/火星/木星/土星）真实方向 + Sprite 渲染
  // 数据：NASA JPL SSD「Approximate Positions of the Planets」(Standish & Williams 1992), Table 1 (1800–2050 AD)
  // 坐标：J2000 平黄道；黄赤交角 ε=23.43928°。方向 = 行星日心 − 地球日心（矢量相减）→ 绕X转ε → 世界方向。
  // ════════════════════════════════════════════════════════════════════
  const EPS = 23.43928 * DEG   // 黄赤交角（与轨道环 eclipticToEquatorialDir 一致）

  // 五颗行星渲染定义：典型地球距离(审计表) / 实测RGB(资源文档) / 平均视星等(亮度分级) / 渲染角直径(风格化)
  const PLANET_DEFS = {
    Mercury: { typicalAU: 0.9220797145583455, rgb: [132, 129, 129], mag: -0.2, ang: 0.9 },
    Venus:   { typicalAU: 0.6908797145583455, rgb: [208, 206, 204], mag: -4.6, ang: 1.3 },
    Mars:    { typicalAU: 1.1500330430035477,  rgb: [138, 105, 75],  mag: -1.0, ang: 1.1 },
    Jupiter: { typicalAU: 5.105997356051019,  rgb: [172, 121, 68],  mag: -2.0, ang: 1.25 },
    Saturn:  { typicalAU: 9.484427710726674,  rgb: [119, 111, 82],  mag: 0.5,  ang: 1.2 },
  }
  const PLANET_NAMES = ['Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn']
  // 亮度分级：视星等 → 相对流量 flux=10^(-0.4·mag) → 4次方根压缩（金星最亮=1.0，避免外行星过暗看不见）
  function planetBrightness(mag) {
    const fVenus = Math.pow(10, -0.4 * (-4.6))
    const f = Math.pow(10, -0.4 * mag)
    return Math.pow(f / fVenus, 0.25)
  }

  // Standish Table 1 轨道根数 [a, e, I(deg), L(deg), ϖ(deg), Ω(deg)]；[0]=J2000值 [1]=每世纪速率
  const PLANET_ELEMENTS = {
    Mercury: { a: [0.38709927, 0.00000037], e: [0.20563593, 0.00001906], I: [7.00497902, -0.00594749], L: [252.25032350, 149472.67411175], p: [77.45779628, 0.16047689], O: [48.33076593, -0.12534081] },
    Venus:   { a: [0.72333566, 0.00000390], e: [0.00677672, -0.00004107], I: [3.39467605, -0.00078890], L: [181.97909950, 58517.81538729], p: [131.60246718, 0.00268329], O: [76.67984255, -0.27769418] },
    EMBary:  { a: [1.00000261, 0.00000562], e: [0.01671123, -0.00004392], I: [-0.00001531, -0.01294668], L: [100.46457166, 35999.37244981], p: [102.93768193, 0.32327364], O: [0.0, 0.0] },
    Mars:    { a: [1.52371034, 0.00001847], e: [0.09339410, 0.00007882], I: [1.84969142, -0.00813131], L: [-4.55343205, 19140.30268499], p: [-23.94362959, 0.44441088], O: [49.55953891, -0.29257343] },
    Jupiter: { a: [5.20288700, -0.00011607], e: [0.04838624, -0.00013253], I: [1.30439695, -0.00183714], L: [34.39644051, 3034.74612775], p: [14.72847983, 0.21252668], O: [100.47390909, 0.20469106] },
    Saturn:  { a: [9.53667594, -0.00125060], e: [0.05386179, -0.00050991], I: [2.48599187, 0.00193609], L: [49.95424423, 1222.49362201], p: [92.59887831, -0.41897216], O: [113.66242448, -0.28867794] },
  }

  function pNorm360(d) { return ((d % 360) + 360) % 360 }
  function pNorm180(d) { d = pNorm360(d); return d > 180 ? d - 360 : d }
  function pJulian(nowMs) { return nowMs / 86400000 + 2440587.5 }
  function pCenturies(nowMs) { return (pJulian(nowMs) - 2451545.0) / 36525 }

  // 开普勒求解 → 日心黄道直角坐标 (AU)
  function keplerHelioEcl(name, nowMs) {
    const el = PLANET_ELEMENTS[name]
    const T = pCenturies(nowMs)
    const a = el.a[0] + el.a[1] * T
    const e = el.e[0] + el.e[1] * T
    const I = (el.I[0] + el.I[1] * T) * DEG
    const L = pNorm360(el.L[0] + el.L[1] * T)
    const w = pNorm360(el.p[0] + el.p[1] * T)   // ϖ 近日点黄经
    const O = pNorm360(el.O[0] + el.O[1] * T)   // Ω 升交点黄经
    const M = pNorm180(L - w)                    // 平近点角
    const eStar = 57.29578 * e
    let E = M + eStar * Math.sin(M * DEG)        // 初值
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
  // 黄道直角 → 赤道直角（绕X转+ε），与轨道环 eclipticToEquatorialDir 同一世界系
  function ecl2eq(v) {
    return { x: v.x, y: Math.cos(EPS) * v.y - Math.sin(EPS) * v.z, z: Math.sin(EPS) * v.y + Math.cos(EPS) * v.z }
  }
  // 行星地心方向（单位向量，世界系）：行星日心 − 地球日心，再转赤道系归一化
  function planetGeoDir(name, nowMs) {
    const ph = keplerHelioEcl(name, nowMs)
    const eh = keplerHelioEcl('EMBary', nowMs)
    const g = { x: ph.x - eh.x, y: ph.y - eh.y, z: ph.z - eh.z }
    const q = ecl2eq(g)
    const r = Math.hypot(q.x, q.y, q.z) || 1
    return { x: q.x / r, y: q.y / r, z: q.z / r }
  }

  // 行星光晕贴图（程序生成径向渐变，AdditiveBlending，同太阳halo做法）；颜色=NASA实测RGB×亮度分级
  function makePlanetGlowTexture(rgb, bright) {
    const s = 128
    const c = document.createElement('canvas')
    c.width = c.height = s
    const g = c.getContext('2d')
    const grad = g.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2)
    const col = `${rgb[0]},${rgb[1]},${rgb[2]}`
    grad.addColorStop(0.00, `rgba(${col},${Math.min(1, 1.0 * bright)})`)
    grad.addColorStop(0.30, `rgba(${col},${0.62 * bright})`)
    grad.addColorStop(0.62, `rgba(${col},${0.16 * bright})`)
    grad.addColorStop(1.00, `rgba(${col},0)`)
    g.fillStyle = grad
    g.fillRect(0, 0, s, s)
    return new T.CanvasTexture(c)
  }

  // 地球日心黄道经度（度，[0,360)）：取太阳地心视黄经（与 earth3d _computeSubsolarPoint
  // 同一权威算法）+ 180°。用于把"地球公转位置标记"摆到轨道环上真实日期对应的角度。
  function earthHeliocentricEclLon(now) {
    const JD = now / 86400000 + 2440587.5
    const n = JD - 2451545.0
    const L = (280.46646 + 0.9856474 * n) % 360
    const M = (((357.52911 + 0.98560028 * n) % 360) + 360) % 360
    const Mr = M * DEG
    const C = 1.914602 * Math.sin(Mr) + 0.019993 * Math.sin(2 * Mr) + 0.000289 * Math.sin(3 * Mr)
    const sunTrueLon = L + C
    const omega = 125.04 - 1934.136 * n / 36525
    const lambda = sunTrueLon - 0.00569 - 0.00478 * Math.sin(omega * DEG)
    return ((lambda + 180) % 360 + 360) % 360
  }
  // 黄道坐标 (cosθ, sinθ, 0) → 赤道系（绕 X 轴转 +ε），返回单位向量
  function eclipticToEquatorialDir(thetaRad) {
    const xe = Math.cos(thetaRad), ye = Math.sin(thetaRad)
    return new T.Vector3(xe, ye * Math.cos(OBLIQ), ye * Math.sin(OBLIQ))
  }

  // 子点(lat,lon) → 世界单位方向。
  // 使用 lonLatToVector3 得到地球局部坐标方向（+y=北极，纹理经纬度一致），
  // 再乘以 earth.quaternion 变换到世界空间。这样太阳/月亮始终在"地球朝向的半球"附近，
  // 保证从任意构图相机都能看到它们（不会跑到视锥外）。数据来源仍是真实天文计算。

  const nowParam = params.get('now')
  const nowMs = nowParam ? Number(nowParam) : Date.now()

  let tries = 0
  const timer = setInterval(function () {
    tries++
    const api = window.earth3d
    const ready = api && api.isReady
    const scene = api && api.getScene && api.getScene()
    const camera = api && api.getCamera && api.getCamera()
    const getEarthCenter = api && api.getEarthCenter
    const getCamDist = api && api.getCameraDistanceToEarth
    const getSubSolar = api && api.getSubsolarPoint
    const getSubLunar = api && api.getSublunarPoint
    if (ready && scene && camera && getEarthCenter && getCamDist && getSubSolar && getSubLunar) {
      clearInterval(timer)
      initCelestial({ api: api, scene: scene, camera: camera, nowMs: nowMs })
    } else if (tries > 240) {
      clearInterval(timer)
      console.error('[realCelestial] earth3d 未在超时内就绪，天体未挂载')
    }
  }, 50)

  function initCelestial(ctx) {
    const { api, scene, camera } = ctx
    const q = nowParam ? ('?now=' + encodeURIComponent(nowParam)) : ''
    // 月相/光照信息来自后端（core/astronomy.js 的 subLunarPoint 等），用于显示与自检；
    // 3D 摆放方向则走前端 _computeSubsolarPoint/_computeSublunarPoint（earth3d 权威来源）。
    let apiData = null
    fetch('/api/celestial-positions' + q)
      .then(function (r) { return r.json() })
      .then(function (data) { apiData = data })
      .catch(function (e) { console.warn('[realCelestial] 取 /api/celestial-positions 失败，仅影响月相显示:', e) })

    // ── 太阳：Sprite 光晕（AdditiveBlending）──
    const sunMat = new T.SpriteMaterial({
      map: makeSunGlowTexture(),
      color: 0xffffff,
      transparent: true,
      blending: T.AdditiveBlending,
      depthWrite: false,
      depthTest: false,            // 天光元素，永远可见（不遮挡判定交给分层）
    })
    const sun = new T.Sprite(sunMat)
    sun.renderOrder = 20
    sun.frustumCulled = false
    scene.add(sun)

    // ── 月亮：Sphere + 真实贴图 + 相位 shader ──
    const moonGeo = new T.SphereGeometry(1, 48, 48) // 基准半径1，运行时按角直径缩放
    const moonUniforms = {
      uTex: { value: null },
      uSunDir: { value: new T.Vector3(1, 0, 0) },
      uAmbient: { value: 0.05 },
      uTint: { value: new T.Vector3(MOON_TINT[0], MOON_TINT[1], MOON_TINT[2]) },
    }
    const moonMat = new T.ShaderMaterial({
      uniforms: moonUniforms,
      vertexShader: MOON_VERT,
      fragmentShader: MOON_FRAG,
      depthTest: false,            // 保证可见（deepSpace/farOrbit 视角下地球极小，遮挡可忽略）
      depthWrite: false,
    })
    const moon = new T.Mesh(moonGeo, moonMat)
    moon.renderOrder = 19
    moon.frustumCulled = false
    scene.add(moon)

    new T.TextureLoader().load(
      '/assets/textures/moon/moon_lroc_color_2k.jpg',
      function (tex) {
        if (T.sRGBEncoding !== undefined) tex.encoding = T.sRGBEncoding
        moonUniforms.uTex.value = tex
      },
      undefined,
      function (e) { console.error('[realCelestial] 月球贴图加载失败:', e) }
    )

    // ── #53 Phase 2 五颗行星（Sprite + 径向渐变，同太阳halo做法）──
    const planets = {}
    for (const name of PLANET_NAMES) {
      const def = PLANET_DEFS[name]
      const bright = planetBrightness(def.mag)
      const mat = new T.SpriteMaterial({
        map: makePlanetGlowTexture(def.rgb, bright),
        color: 0xffffff,
        transparent: true,
        blending: T.AdditiveBlending,
        depthWrite: false,
        depthTest: false,
      })
      const sp = new T.Sprite(mat)
      sp.renderOrder = 18
      sp.frustumCulled = false
      sp.visible = false
      scene.add(sp)
      planets[name] = {
        sprite: sp,
        dist: compressToSceneDist(def.typicalAU),  // 固定场景距离（审计对数压缩）
        ang: def.ang,                               // 渲染角直径（风格化）
        bright: bright, rgb: def.rgb,
        ndc: [0, 0], visible: false,
      }
    }

    // ── 公转轨道环 + 地球位置标记（仅 deepSpace 可见，独立视觉语言）──
    // 环：RingGeometry 细圆环 mesh + ShaderMaterial（柔边光带 + 角度衰减，最亮段跟随地球黄经）
    const ringInner = ORBIT_RING_DIST - ORBIT_RING_WIDTH
    const ringOuter = ORBIT_RING_DIST + ORBIT_RING_WIDTH
    const orbitGeo = new T.RingGeometry(ringInner, ringOuter, 256, 1)
    const orbitUniforms = {
      uEarthAngleRad: { value: 0 },                       // 地球当前黄经（弧度），每帧更新，与 earthMarker 同源
      uTime: { value: 0 },
      uColor: { value: new T.Color(ORBIT_RING_COLOR) },
      uInner: { value: ringInner },
      uOuter: { value: ringOuter },
    }
    const orbitVert = `
      varying float vAngle;
      varying float vRadial;
      uniform float uInner;
      uniform float uOuter;
      void main() {
        // 局部 XY 平面角度（与 eclipticToEquatorialDir 同一经度量，旋转前）
        vAngle = atan(position.y, position.x);
        float r = length(position.xy);
        vRadial = clamp((r - uInner) / (uOuter - uInner), 0.0, 1.0); // 0=内边 1=外边
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `
    const orbitFrag = `
      precision highp float;
      varying float vAngle;
      varying float vRadial;
      uniform float uEarthAngleRad;   // 地球当前黄经（弧度）
      uniform float uTime;
      uniform vec3 uColor;
      const float TAU = 6.28318530718;
      void main() {
        // 径向：中心亮，边缘柔和衰减（非硬边）
        float radial = 1.0 - smoothstep(0.0, 1.0, abs(vRadial - 0.5) * 2.0);
        // 角度：当前像素角度与地球黄经的劣弧距离
        float pa = vAngle;
        if (pa < 0.0) pa += TAU;
        float angDist = abs(pa - uEarthAngleRad);
        angDist = min(angDist, TAU - angDist);
        float angularFade = smoothstep(3.14159, 0.0, angDist);  // 近地球越亮
        float alpha = radial * mix(0.08, 0.5, angularFade);     // 0.08=最暗底限（不完全消失）
        gl_FragColor = vec4(uColor, alpha);
      }
    `
    const orbitMat = new T.ShaderMaterial({
      uniforms: orbitUniforms,
      vertexShader: orbitVert,
      fragmentShader: orbitFrag,
      transparent: true,
      blending: T.AdditiveBlending,
      depthWrite: false,
      depthTest: false,
      side: T.DoubleSide,
    })
    const orbitRing = new T.Mesh(orbitGeo, orbitMat)
    orbitRing.rotation.x = OBLIQ   // 对齐黄道倾角（绕X转+ε，与 eclipticToEquatorialDir 一致）
    orbitRing.renderOrder = 15
    orbitRing.frustumCulled = false
    orbitRing.visible = false
    scene.add(orbitRing)

    // 地球标记：呼吸光点（Sprite + 径向渐变，复用行星光晕生成手法 + 太阳同款 pulse 节奏）
    const markerTex = makePlanetGlowTexture([143, 208, 255], 1.0) // 浅蓝，复用既有生成器
    const markerMat = new T.SpriteMaterial({
      map: markerTex, transparent: true,
      blending: T.AdditiveBlending, depthWrite: false, depthTest: false,
    })
    const earthMarker = new T.Sprite(markerMat)
    earthMarker.renderOrder = 16
    earthMarker.frustumCulled = false
    earthMarker.visible = false
    scene.add(earthMarker)

    const state = {
      camDistEarth: 0, moonVisible: false, sunVisible: false, planetsVisible: false,
      moonWorldRadius: 0, sunWorldDiameter: 0,
      moonAngDiamDeg: 0, sunAngDiamDeg: 0,
      moonNDC: [0, 0], sunNDC: [0, 0],
      orbitVisible: false, earthMarkerEclLonDeg: 0,
      orbitEarthAngleRad: 0, earthMarkerNDC: [0, 0], earthCenterNDC: [0, 0],
    }
    const earthCenter = new T.Vector3()
    const sunDir = new T.Vector3(), moonDir = new T.Vector3()
    const sunPos = new T.Vector3(), moonPos = new T.Vector3()
    const t0 = performance.now()

    function tick() {
      earthCenter.copy(api.getEarthCenter())
      const camDistEarth = api.getCameraDistanceToEarth()
      state.camDistEarth = round(camDistEarth, 3)
      const showMoon = camDistEarth >= MOON_VISIBLE_DIST && camDistEarth < MOON_HIDE_DIST
      const showSun = camDistEarth >= SUN_VISIBLE_DIST
      const showPlanets = camDistEarth >= PLANETS_VISIBLE_DIST
      state.moonVisible = showMoon
      state.sunVisible = showSun
      state.planetsVisible = showPlanets

      // 真实方向（前端权威来源）→ 经地球朝向变换 → 世界方向
      const sp = api.getSubsolarPoint(nowMs)
      const lp = api.getSublunarPoint(nowMs)
      const earthQuat = api.getEarth().quaternion
      sunDir.copy(api.lonLatToVector3(sp.lat, sp.lon, 1)).applyQuaternion(earthQuat)
      moonDir.copy(api.lonLatToVector3(lp.lat, lp.lon, 1)).applyQuaternion(earthQuat)

      // 相对地球的固定距离摆放（不按相机比例，保证始终在视锥内）
      moonPos.copy(earthCenter).add(moonDir.clone().multiplyScalar(MOON_DIST))
      sunPos.copy(earthCenter).add(sunDir.clone().multiplyScalar(SUN_DIST))
      moon.position.copy(moonPos)
      sun.position.copy(sunPos)
      moon.visible = showMoon
      sun.visible = showSun

      // ── #53 Phase 2 行星更新：独立可见性档(PLANETS_VISIBLE_DIST)，仅 deepSpace ──
      for (const name of PLANET_NAMES) {
        const P = planets[name]
        P.visible = showPlanets   // 独立档，不再与太阳共用阈值
        P.sprite.visible = showPlanets
        if (showPlanets) {
          const dir = planetGeoDir(name, nowMs)        // 真实地心方向（日心−地球日心）
          const pos = earthCenter.clone().add(new T.Vector3(dir.x, dir.y, dir.z).multiplyScalar(P.dist))
          P.sprite.position.copy(pos)
          const camToP = camera.position.distanceTo(pos)
          const d = 2 * camToP * Math.tan((P.ang * DEG) / 2)  // 恒定角直径（风格化）
          P.sprite.scale.set(d, d, 1)
          const ndc = pos.clone().project(camera)
          P.ndc = [round(ndc.x, 4), round(ndc.y, 4)]
        }
      }

      // 公转轨道环 + 地球标记：仅 deepSpace（与太阳晕同阈值 SUN_VISIBLE_DIST）。
      // 与 near-field 太阳晕独立；标记角度 = 真实地球日心黄道经度（随日期变化）。
      const showOrbit = camDistEarth >= SUN_VISIBLE_DIST
      state.orbitVisible = showOrbit
      orbitRing.visible = showOrbit
      earthMarker.visible = showOrbit
      // 视觉生命感（呼吸节奏，与太阳 pulse 同款）
      const t = (performance.now() - t0) / 1000
      const pulse = 1 + 0.05 * Math.sin(t * 0.8)
      if (showOrbit) {
        const tNow = nowParam ? nowMs : Date.now()
        const lamE = earthHeliocentricEclLon(tNow) * DEG
        state.earthMarkerEclLonDeg = round(lamE / DEG, 3)
        const dir = eclipticToEquatorialDir(lamE).multiplyScalar(ORBIT_RING_DIST)
        earthMarker.position.copy(earthCenter).add(dir)
        orbitRing.position.copy(earthCenter)
        // 环 shader：最亮段跟随地球黄经（与标记同源，不重算）
        orbitUniforms.uEarthAngleRad.value = lamE
        orbitUniforms.uTime.value = t
        state.orbitEarthAngleRad = round(lamE, 5)
        // 地球标记呼吸光点
        const ms = MARKER_BASE_SIZE * pulse
        earthMarker.scale.set(ms, ms, 1)
        const mndc = earthMarker.position.clone().project(camera)
        state.earthMarkerNDC = [round(mndc.x, 4), round(mndc.y, 4)]
        const ecndc = earthCenter.clone().project(camera)
        state.earthCenterNDC = [round(ecndc.x, 4), round(ecndc.y, 4)]
      }

      // 恒定角直径缩放：世界尺寸 = 相机距 × tan(角直径/2)
      if (showMoon) {
        const camToMoon = camera.position.distanceTo(moonPos)
        const r = camToMoon * Math.tan((MOON_ANG_DIAM * DEG) / 2)
        moon.scale.set(r, r, r)
        state.moonWorldRadius = round(r, 4)
        state.moonAngDiamDeg = round(MOON_ANG_DIAM, 4)
      }
      if (showSun) {
        const camToSun = camera.position.distanceTo(sunPos)
        const d = 2 * camToSun * Math.tan((SUN_ANG_DIAM * DEG) / 2)
        sun.scale.set(d, d, 1)
        state.sunWorldDiameter = round(d, 4)
        state.sunAngDiamDeg = round(SUN_ANG_DIAM, 4)
      }

      // 月相：世界坐标 (太阳 − 月亮) 方向
      moonUniforms.uSunDir.value.copy(sunPos).sub(moonPos).normalize()

      // 太阳轻微脉动（与地球标记同款呼吸节奏，pulse 已在上方定义）
      if (showSun) sun.scale.set(state.sunWorldDiameter * pulse, state.sunWorldDiameter * pulse, 1)

      // 屏幕 NDC（用于验证"随时间在动"）
      const sndc = sunPos.clone().project(camera)
      const mndc = moonPos.clone().project(camera)
      state.sunNDC = [round(sndc.x, 4), round(sndc.y, 4)]
      state.moonNDC = [round(mndc.x, 4), round(mndc.y, 4)]

      requestAnimationFrame(tick)
    }
    tick()

    console.log('[realCelestial] 天体已挂载', {
      camDistEarth: state.camDistEarth,
      moonVisible: state.moonVisible, sunVisible: state.sunVisible,
      REAL_MOON_ANG: round(REAL_MOON_ANG, 4), REAL_SUN_ANG: round(REAL_SUN_ANG, 4),
      MOON_ANG_DIAM: round(MOON_ANG_DIAM, 4), SUN_ANG_DIAM: round(SUN_ANG_DIAM, 4),
      moonMult: MOON_ANG_DIAM_MULT, sunMult: SUN_ANG_DIAM_MULT,
    })

    window.realCelestial = {
      sun: sun, moon: moon, orbitRing: orbitRing, earthMarker: earthMarker, data: null,
      isRealCelestial: true,
      getState: function () {
        return {
          camDistEarth: state.camDistEarth,
          moonVisible: state.moonVisible,
          sunVisible: state.sunVisible,
          planetsVisible: state.planetsVisible,
          moonWorldRadius: state.moonWorldRadius,
          sunWorldDiameter: state.sunWorldDiameter,
          moonAngDiamDeg: state.moonAngDiamDeg,
          sunAngDiamDeg: state.sunAngDiamDeg,
          moonMult: round(MOON_ANG_DIAM / REAL_MOON_ANG, 3),
          sunMult: round(SUN_ANG_DIAM / REAL_SUN_ANG, 3),
          moonNDC: state.moonNDC,
          sunNDC: state.sunNDC,
          sunDistFromEarth: round(sunPos.distanceTo(earthCenter), 3),
          moonDistFromEarth: round(moonPos.distanceTo(earthCenter), 3),
          orbitVisible: state.orbitVisible,
          earthMarkerEclLonDeg: state.earthMarkerEclLonDeg,
          orbitEarthAngleRad: state.orbitEarthAngleRad,
          earthMarkerNDC: state.earthMarkerNDC,
          earthCenterNDC: state.earthCenterNDC,
          now: nowMs,
          subSolar: apiData ? [round(apiData.sun.subSolarLat, 3), round(apiData.sun.subSolarLon, 3)] : null,
          subLunar: apiData ? [round(apiData.moon.subLunarLat, 3), round(apiData.moon.subLunarLon, 3)] : null,
          phase: apiData ? apiData.moon.phaseName : null,
          illumination: apiData ? apiData.moon.illumination : null,
          planets: PLANET_NAMES.map(function (name) {
            const P = planets[name]
            return {
              name: name, visible: P.visible, dist: round(P.dist, 3),
              ang: P.ang, bright: round(P.bright, 3), rgb: P.rgb, ndc: P.ndc,
            }
          }),
        }
      },
    }
  }
})()
