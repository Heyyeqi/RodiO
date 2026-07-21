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
 *  ── 距离分档可见性（按"相机到地心的实际直线距离"，不按构图名字，各天体独立）：
 *       MOON_VISIBLE_DIST = 35, MOON_HIDE_DIST = 65
 *         → 相机距 ∈ [35,65) 显示月亮（moonView 48 / lunarHalo 58 在内，farOrbit 25.15 与 deepSpace 80 越过隐藏）
 *       SUN_VISIBLE_DIST  = 50  → 相机距 ≥50 显示太阳（覆盖 sunView 67.5 / lunarHalo 58 / deepSpace 80，高于 farOrbit 25.15）
 *       五颗行星（#53 天体专属远景角度）各自独立阈值，按 compressToSceneDist 场景放置距离排序，
 *       不再共用一个 PLANETS_VISIBLE_DIST：Venus 70 / Mercury 72 / Mars 74 / Jupiter 76 / Saturn 78；
 *       外三行星（#54 完整太阳系）继续延伸：Uranus 81 / Neptune 83 / Pluto 85。
 *       每颗行星有自己的专属构图（venusView 70.5 … saturnView 78.5；uranusView 81.5 / neptuneView 83.5 /
 *       plutoView 85.5）；内行星落在"自己阈值已过、下一颗还没到"的窗口内，天然只显示这一颗；
 *       外行星因阈值密集采用"越远越叠加"设计语言（与 moonView→lunarHalo 一致）：uranusView 起内行星已在框。
 *       deepSpace(80) ≥ 内五行星全部阈值、< Uranus(81)，故 deepSpace 仍只显示内五行星（全景效果不变）。
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

  // ── C1: realCelestial 全局隐藏 2D 叠加层（weather-canvas）──
  // 避免 2D 绘制内容（天空渐变/地球贴图/Waiting 背景等）覆盖在 WebGL 场景之上，
  // 造成左下角白块泄漏、背景不纯黑等问题。HTML UI（.panel-layer, z-index:3）不受影响。
  ;(function hide2DOverlay () {
    const c = document.getElementById('weather-canvas')
    if (c) { c.style.display = 'none' }
  })()

  // ── 命名常量（不散落魔法数字）──
  // 三档拆分可见性（按"相机到地心的实际直线距离"，不按构图名字）。
  // 阈值命名遵循可扩展模式 XXX_VISIBLE_DIST / XXX_HIDE_DIST：未来新增构图或新天体
  // 只需加一对常量 + 一行判断，无需重设计。当前各档边界（场景单位，相机距地心）：
  //   月亮 : [MOON_VISIBLE_DIST(35), MOON_HIDE_DIST(65))   → moonView 48 / lunarHalo 58 可见，farOrbit 25.15 与 deepSpace 80 越过隐藏
  //   太阳 : [SUN_VISIBLE_DIST(50),  ∞)                     → 不变（覆盖 deepSpace 80）
  //   行星 : 每颗独立阈值（按 compressToSceneDist 场景放置距离排序，越远相机距越大），
  //          不再共用 PLANETS_VISIBLE_DIST；deepSpace(80) 仅内五行星，Uranus(81) 起为外行星专属窗口。
  const MOON_VISIBLE_DIST = 35   // 相机距地心 ≥ 此值 → 月亮可见（moonView 48 / lunarHalo 58 在内；farOrbit 25.15 与 deepSpace 80 越过 → 隐藏）
  const MOON_HIDE_DIST = 65      // 相机距地心 ≥ 此值 → 月亮隐藏（deepSpace 80 越过，避免与太阳/行星拥挤）
  const SUN_VISIBLE_DIST = 50    // 相机距地心 ≥ 此值 → 太阳可见（覆盖 deepSpace 80，高于 farOrbit 25.15）
  // 每行星独立可见性阈值（相机距地心 ≥ 此值 → 该行星可见）。命名遵循 XXX_VISIBLE_DIST 模式。
  // 内五行星：Venus 70 / Mercury 72 / Mars 74 / Jupiter 76 / Saturn 78（间隔 2，专属构图落在单体内）。
  // 外三行星：Uranus 81 / Neptune 83 / Pluto 85（deepSpace=80 不触发，专属构图 uranusView 81.5 起）。
  const PLANET_VISIBLE_DIST = {
    Venus: 70, Mercury: 72, Mars: 74, Jupiter: 76, Saturn: 78,
    Uranus: 81, Neptune: 83, Pluto: 85,
  }

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

  // ── 天体贴图 Sprite 工厂（太阳/8行星/5卫星真实贴图专用）──
  // 这些贴图都是探测器拍的"全圆盘照片"（近似正方形），不是月球贴图那种等距柱状全球展开图，
  // 不能贴 SphereGeometry（会拉伸畸变+黑背景缠绕到球面各处）。
  // 改用 Sprite（恒朝向相机）直接显示原图，AdditiveBlending 让黑色背景自然消失于深空背景。
  function createBodyTexSprite(colorTint) {
    const mat = new T.SpriteMaterial({
      map: null,
      color: colorTint || 0xffffff,
      transparent: true,
      blending: T.AdditiveBlending,
      depthWrite: false,
      depthTest: false,
    })
    const sprite = new T.Sprite(mat)
    sprite.frustumCulled = false
    sprite.visible = false
    return sprite
  }
  function loadSpriteTexture(sprite, path) {
    new T.TextureLoader().load(path, function (tex) {
      if (T.sRGBEncoding !== undefined) tex.encoding = T.sRGBEncoding
      sprite.material.map = tex
      sprite.material.needsUpdate = true
      // Bug 2 修复：记录原始长宽比，供 tick() 缩放时使用（避免非正方形贴图被拉伸成椭圆）
      // aspect = imgW/imgH；>1 更宽，<1 更高
      if (tex.image && tex.image.width && tex.image.height) {
        sprite.userData.aspect = tex.image.width / tex.image.height
      }
    }, undefined, function (e) { console.error('[realCelestial] 贴图加载失败:', path, e) })
  }
  // Bug 2 修复：按贴图原始长宽比设置 Sprite 缩放（长边对齐视觉直径 d，短边按比例，圆盘不被拉伸）
  function applyAspectScale(sprite, d) {
    const aspect = sprite.userData.aspect || 1   // imgW/imgH
    const sx = aspect >= 1 ? d : d * aspect
    const sy = aspect >= 1 ? d / aspect : d
    sprite.scale.set(sx, sy, 1)
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
    Mercury: { typicalAU: 0.9220797145583455, rgb: [132, 129, 129], mag: -0.2, ang: 1.2, texture: '/assets/textures/planets/mercury_messenger_truecolor.jpg' },
    Venus:   { typicalAU: 0.6908797145583455, rgb: [208, 206, 204], mag: -4.6, ang: 1.8, texture: '/assets/textures/planets/venus_mariner10_truecolor.jpg' },
    Mars:    { typicalAU: 1.1500330430035477,  rgb: [138, 105, 75],  mag: -1.0, ang: 1.5, texture: '/assets/textures/planets/mars_truecolor.jpg' },
    Jupiter: { typicalAU: 5.105997356051019,  rgb: [172, 121, 68],  mag: -2.0, ang: 2.6, texture: '/assets/textures/planets/jupiter_pia01369.jpg' }
,
    Saturn:  { typicalAU: 9.484427710726674,  rgb: [119, 111, 82],  mag: 0.5,  ang: 2.4, texture: '/assets/textures/planets/saturn_truecolor.jpg' }
,
    // #54 外三行星（典型距离取 SCALE_TYPICAL_AU，与压缩比例尺一致；rgb=NASA 实测近似色，mag=视星等用于亮度分级）
    Uranus:  { typicalAU: 19.16492841103248,   rgb: [143, 196, 209], mag: 5.5,  ang: 1.9, texture: '/assets/textures/planets/uranus_pia18182.jpg' },
    Neptune: { typicalAU: 30.052366978326347,  rgb: [80, 120, 210],  mag: 7.8,  ang: 1.8, texture: '/assets/textures/planets/neptune_pia01492.jpg' }
,
    Pluto:   { typicalAU: 39.4693339695516,    rgb: [200, 178, 155], mag: 13.5, ang: 1.0, texture: '/assets/textures/planets/pluto_pia19708.jpg' },
  }
  const PLANET_NAMES = ['Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']
  // 亮度分级：视星等 → 相对流量 flux=10^(-0.4·mag) → 4次方根压缩（金星最亮=1.0，避免外行星过暗看不见）
  function planetBrightness(mag) {
    const fVenus = Math.pow(10, -0.4 * (-4.6))
    const f = Math.pow(10, -0.4 * mag)
    return Math.pow(f / fVenus, 0.25)
  }

  // #54 代表性卫星（illustrative，非星历精确）：木星伽利略4卫星 + 土卫六。圆轨道、共面于黄道，
  // 真实公转周期；相位 angle = 2π·(daysSinceJ2000/period + phase0)。仅当母行星可见时显示。
  // sceneRadius 为风格化轨道半径（场景单位，贴近母行星）。这是"代表性"示意，不声称轨道力学精确。
  const SATELLITE_DEFS = {
    Jupiter: [
      { name: 'Io',       periodDays: 1.769,  sceneRadius: 0.55, ang: 0.55, texture: '/assets/textures/planets/io_truecolor.jpg', rgb: [210, 205, 190], phase0: 0.10 },
      { name: 'Europa',   periodDays: 3.551,  sceneRadius: 0.85, ang: 0.48, texture: '/assets/textures/planets/europa_pia19048.jpg', rgb: [205, 195, 175], phase0: 0.42 },
      { name: 'Ganymede', periodDays: 7.155,  sceneRadius: 1.20, ang: 0.60, texture: '/assets/textures/planets/ganymede_pia00716.jpg', rgb: [180, 172, 160], phase0: 0.71 },
      { name: 'Callisto', periodDays: 16.689, sceneRadius: 1.60, ang: 0.55, texture: '/assets/textures/planets/callisto_pia03456.jpg', rgb: [150, 142, 130], phase0: 0.20 },
    ],
    Saturn: [
      { name: 'Titan',    periodDays: 15.945, sceneRadius: 1.35, ang: 0.65, texture: '/assets/textures/planets/titan_pia06230.jpg', rgb: [212, 182, 140], phase0: 0.55 },
    ],
  }

  // ── Step 1 Hero 肖像：真实等距柱状全球贴图球（与轨道 Sprite 分离，独照模式）──
  // 贴图来自 planets_equirect/（Solar System Scope 2:1 等距柱状），与行星圆盘照片 planets/ 分开存放。
  // 先以 Mars + Saturn 验证整条管线（球体 + 月面光照着色器 + 土星环 + 专用构图），再推广到其余行星。
  const HERO_DEFS = {
    mars: {
      radius: 1.0,
      pos: new T.Vector3(0, 60, 0),
      texture: '/assets/textures/planets_equirect/mars.jpg',
      ambient: 0.05, tint: [1.0, 1.0, 1.0], spin: 0.0016,
    },
    saturn: {
      radius: 1.4,
      pos: new T.Vector3(0, 60, 0),
      texture: '/assets/textures/planets_equirect/saturn.jpg',
      ambient: 0.06, tint: [1.0, 0.98, 0.92], spin: 0.0014,
      tiltDeg: 26.7,
      ring: {
        inner: 1.4 * 1.25,
        outer: 1.4 * 2.30,
        alphaTex: '/assets/textures/planets_equirect/saturn_ring_alpha.png',
      },
    },
  }

  // Standish Table 1 轨道根数 [a, e, I(deg), L(deg), ϖ(deg), Ω(deg)]；[0]=J2000值 [1]=每世纪速率
  const PLANET_ELEMENTS = {
    Mercury: { a: [0.38709927, 0.00000037], e: [0.20563593, 0.00001906], I: [7.00497902, -0.00594749], L: [252.25032350, 149472.67411175], p: [77.45779628, 0.16047689], O: [48.33076593, -0.12534081] },
    Venus:   { a: [0.72333566, 0.00000390], e: [0.00677672, -0.00004107], I: [3.39467605, -0.00078890], L: [181.97909950, 58517.81538729], p: [131.60246718, 0.00268329], O: [76.67984255, -0.27769418] },
    EMBary:  { a: [1.00000261, 0.00000562], e: [0.01671123, -0.00004392], I: [-0.00001531, -0.01294668], L: [100.46457166, 35999.37244981], p: [102.93768193, 0.32327364], O: [0.0, 0.0] },
    Mars:    { a: [1.52371034, 0.00001847], e: [0.09339410, 0.00007882], I: [1.84969142, -0.00813131], L: [-4.55343205, 19140.30268499], p: [-23.94362959, 0.44441088], O: [49.55953891, -0.29257343] },
    Jupiter: { a: [5.20288700, -0.00011607], e: [0.04838624, -0.00013253], I: [1.30439695, -0.00183714], L: [34.39644051, 3034.74612775], p: [14.72847983, 0.21252668], O: [100.47390909, 0.20469106] },
    Saturn:  { a: [9.53667594, -0.00125060], e: [0.05386179, -0.00050991], I: [2.48599187, 0.00193609], L: [49.95424423, 1222.49362201], p: [92.59887831, -0.41897216], O: [113.66242448, -0.28867794] },
    // #54 外三行星（Standish Table 1 同族根数；Uranus/Neptune 经 JPL 官方核对；Pluto 用同期权威均值根数，
    //   L 速率 = 360°/周期·世纪 ≈ +145.2，与内行星同款 Kepler 求解）。e/I/ϖ/Ω 速率极小，本历元误差可忽略。
    Uranus:  { a: [19.18916464, -0.00196176], e: [0.04725744, -0.00004397], I: [0.77263783, -0.00242939], L: [313.23810451, 428.48202785], p: [170.95427630, 0.40805281], O: [74.01692503, 0.04240589] },
    Neptune: { a: [30.06992276, 0.00026291], e: [0.00859048, 0.00005105], I: [1.77004347, 0.00035372], L: [-55.12002969, 218.45945325], p: [44.96476227, -0.32241464], O: [131.78422574, -0.00508664] },
    Pluto:   { a: [39.48211675, -0.00031586], e: [0.24882730, 0.00005170], I: [17.14001206, -0.00032692], L: [238.92903833, 145.23], p: [224.06891629, -0.44018123], O: [110.30393684, -0.38632021] },
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

    // ── 太阳：光晕（保留原有渐变光斑）+ 真实贴图核心盘（新增）──
    // sunHalo: 原有径向渐变光斑，作为外围光晕层（renderOrder 18，先画）
    const sunHaloMat = new T.SpriteMaterial({
      map: makeSunGlowTexture(),
      color: 0xffffff,
      transparent: true,
      blending: T.AdditiveBlending,
      depthWrite: false,
      depthTest: false,
    })
    const sunHalo = new T.Sprite(sunHaloMat)
    sunHalo.renderOrder = 18
    sunHalo.frustumCulled = false
    sunHalo.visible = false   // Bug 1 修复：默认隐藏，只有 showSun 时才显示（否则默认近景也会出现发光球）
    scene.add(sunHalo)

    // sun: 真实 SDO/HMI 贴图核心盘（renderOrder 20，叠在光晕上层），暖白色调
    const sun = createBodyTexSprite(0xfff0cc)
    sun.renderOrder = 20
    scene.add(sun)
    loadSpriteTexture(sun, '/assets/textures/sun/sun_sdo_hmi_luminance.jpg')

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
      // 亮度分级地板：外行星物理上远暗于金星，但场景需可见，故贴图亮度下限 0.22（不影响内行星，其 bright 已 >0.22）。
      // 真实 NASA 探测器全圆盘贴图 Sprite（AdditiveBlending 黑背景自然消失于深空）
      const sp = createBodyTexSprite(0xffffff)
      loadSpriteTexture(sp, def.texture)
      sp.renderOrder = 18
      sp.visible = false
      scene.add(sp)
      planets[name] = {
        sprite: sp,
        dist: compressToSceneDist(def.typicalAU),
        ang: def.ang,
        texture: def.texture,
        bright: bright, rgb: def.rgb,
        ndc: [0, 0], visible: false,
      }
    }

    // ── #54 代表性卫星 Sprite（母行星可见时才显示）──
    const satellites = {}   // satellites[parentName] = [{ sprite, def, ndc:[x,y], visible }]
    const heroSpheres = {}  // Hero 肖像球体：name -> { group, mesh, mat, ringMesh, radius, spin }
    let _heroMode = null    // null=轨道视图；'mars'/'saturn'=独照视图（由 earth3d 切换）
    const _heroSunDir = new T.Vector3(0, 0, 1)  // 行星→太阳 世界方向（每帧更新，供 Hero 相机/光照共用）
    for (const parentName in SATELLITE_DEFS) {
      satellites[parentName] = []
      for (const def of SATELLITE_DEFS[parentName]) {
        // 真实贴图 Sprite（同行星做法）
        const sSprite = createBodyTexSprite(0xffffff)
        loadSpriteTexture(sSprite, def.texture)
        sSprite.renderOrder = 17
        sSprite.visible = false
        scene.add(sSprite)
        satellites[parentName].push({ sprite: sSprite, def: def, texture: def.texture, ndc: [0, 0], visible: false })
      }
    }

    // ── Step 1 Hero 肖像球体（真实 SphereGeometry + 复用 MOON_VERT/MOON_FRAG 月面光照）──
    // 与轨道 Sprite 完全分离：这是"独照"模式，earth3d 用专用构图把相机直接对准行星。
    // 球体用等距柱状全球贴图（planets_equirect/），光照用世界空间太阳方向 uSunDir（与月球同款柔化 terminator）。
    for (const name in HERO_DEFS) {
      const def = HERO_DEFS[name]
      const geo = new T.SphereGeometry(def.radius, 64, 48)
      const tex = new T.TextureLoader().load(def.texture, function (t) { if (T.sRGBEncoding !== undefined) t.encoding = T.sRGBEncoding })
      const mat = new T.ShaderMaterial({
        uniforms: {
          uTex: { value: tex },
          uSunDir: { value: new T.Vector3(0, 1, 0) },   // 行星→太阳 世界方向，每帧由 tick 更新
          uAmbient: { value: def.ambient },
          uTint: { value: new T.Color(def.tint[0], def.tint[1], def.tint[2]) },
        },
        vertexShader: MOON_VERT,
        fragmentShader: MOON_FRAG,
      })
      const mesh = new T.Mesh(geo, mat)
      mesh.frustumCulled = false
      const group = new T.Group()
      group.position.copy(def.pos)
      if (def.tiltDeg) group.rotation.z = def.tiltDeg * DEG   // 轴倾角（土星 26.7°）
      group.add(mesh)
      let ringMesh = null
      if (def.ring) {
        const rg = new T.RingGeometry(def.ring.inner, def.ring.outer, 256, 1)
        const ringTex = new T.TextureLoader().load(def.ring.alphaTex, function (t) { if (T.sRGBEncoding !== undefined) t.encoding = T.sRGBEncoding })
        const ringMat = new T.ShaderMaterial({
          uniforms: {
            uRingAlpha: { value: ringTex },
            uInner: { value: def.ring.inner },
            uOuter: { value: def.ring.outer },
          },
          vertexShader: `
            varying vec2 vLocal;
            void main() {
              vLocal = position.xy;   // 圆环在局部 XY 平面
              gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            }
          `,
          fragmentShader: `
            precision highp float;
            varying vec2 vLocal;
            uniform sampler2D uRingAlpha;
            uniform float uInner;
            uniform float uOuter;
            void main() {
              float r = length(vLocal);
              float rn = clamp((r - uInner) / (uOuter - uInner), 0.0, 1.0);  // 0=内缘 1=外缘
              // B3: 环透明度 = 贴图band结构 × 软边消隐（内外缘柔化，避免生硬圆环）
              float band = texture2D(uRingAlpha, vec2(rn, 0.5)).r;
              float edge = smoothstep(0.0, 0.05, rn) * smoothstep(1.0, 0.93, rn);
              // Cassini 缝：rn≈0.62 处一道暗缝
              float cassini = smoothstep(0.015, 0.05, abs(rn - 0.62));
              float a = band * edge * cassini;
              // B3: 金黄→琥珀色径向渐变（内C环暗淡、外A环明亮），贴近 Apple 天文壁纸
              vec3 colC = vec3(0.62, 0.50, 0.34);   // 内缘 C 环：暗淡棕黄
              vec3 colB = vec3(0.92, 0.76, 0.48);   // B 环：饱满金棕
              vec3 colA = vec3(0.98, 0.86, 0.62);   // 外缘 A 环：明亮浅金
              vec3 tint = mix(colC, colB, smoothstep(0.0, 0.5, rn));
              tint = mix(tint, colA, smoothstep(0.66, 1.0, rn));
              if (a < 0.01) discard;
              gl_FragColor = vec4(tint, a * 0.95);
            }
          `,
          transparent: true,
          side: T.DoubleSide,
          depthWrite: false,
          blending: T.NormalBlending,
        })
        ringMesh = new T.Mesh(rg, ringMat)
        ringMesh.rotation.x = Math.PI / 2   // 平躺到 XZ 平面（行星赤道面），随 group 轴倾角一起倾斜
        ringMesh.frustumCulled = false
        group.add(ringMesh)
      }
      group.visible = false
      scene.add(group)
      heroSpheres[name] = { group: group, mesh: mesh, mat: mat, ringMesh: ringMesh, radius: def.radius, spin: def.spin, def: def }
    }

    // ════════════════════════════════════════════════════════════════════
    // 太阳系示意图视图（celestial_solar_system_diagram_v1.md §1）
    // 独立 Group + 日心坐标俯视，与轨道视图 / Hero 独照互斥。进入时隐藏轨道视图天体。
    // ════════════════════════════════════════════════════════════════════
    let _diagramMode = null   // null=关闭；true=太阳系示意图激活
    const DIAGRAM_SCALE_MIN = 2.0    // 水星（最内圈）目标场景半径
    const DIAGRAM_SCALE_MAX = 14.0   // 冥王星（最外圈）目标场景半径（艺术化压缩，非等比例）
    const _diagLogMin = Math.log10(0.387)   // 水星 a (AU)
    const _diagLogMax = Math.log10(39.48)   // 冥王星 a (AU)
    function diagramCompress(aAU) {
      const t = (Math.log10(aAU) - _diagLogMin) / (_diagLogMax - _diagLogMin)
      return DIAGRAM_SCALE_MIN + t * (DIAGRAM_SCALE_MAX - DIAGRAM_SCALE_MIN)
    }
    // 取日心轨道根数（a, e, 近日点黄经 w 弧度），用于画真实椭圆轨道环
    function keplerElems(name, nowMsD) {
      const el = PLANET_ELEMENTS[name]
      const Tc = pCenturies(nowMsD)
      const a = el.a[0] + el.a[1] * Tc
      const e = el.e[0] + el.e[1] * Tc
      const w = pNorm360(el.p[0] + el.p[1] * Tc) * DEG
      return { a, e, w }
    }
    const diagramGroup = new T.Group()
    diagramGroup.visible = false
    scene.add(diagramGroup)
    // 10 天体：太阳(原点) + 8大行星 + 地球(EMBary) + 冥王星
    const DIAGRAM_BODY_DEFS = {
      Sun:     { tex: '/assets/textures/sun/sun_sdo_hmi_luminance.jpg', size: 4.0 },
      Mercury: { tex: PLANET_DEFS.Mercury.texture, size: 1.0 },
      Venus:   { tex: PLANET_DEFS.Venus.texture,   size: 1.4 },
      Earth:   { tex: '/assets/textures/earth/blue_marble_4k.jpg', size: 1.4 },
      Mars:    { tex: PLANET_DEFS.Mars.texture,    size: 1.2 },
      Jupiter: { tex: PLANET_DEFS.Jupiter.texture, size: 2.5 },
      Saturn:  { tex: PLANET_DEFS.Saturn.texture,  size: 2.3 },
      Uranus:  { tex: PLANET_DEFS.Uranus.texture,  size: 1.6 },
      Neptune: { tex: PLANET_DEFS.Neptune.texture, size: 1.55 },
      Pluto:   { tex: PLANET_DEFS.Pluto.texture,   size: 0.85 },
    }
    const DIAGRAM_BODY_ORDER = ['Sun', 'Mercury', 'Venus', 'Earth', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']
    const DIAGRAM_HELIO_NAME = { Sun: null, Mercury: 'Mercury', Venus: 'Venus', Earth: 'EMBary', Mars: 'Mars', Jupiter: 'Jupiter', Saturn: 'Saturn', Uranus: 'Uranus', Neptune: 'Neptune', Pluto: 'Pluto' }
    const diagramBodies = {}
    const diagramRings = []
    for (const name of DIAGRAM_BODY_ORDER) {
      const def = DIAGRAM_BODY_DEFS[name]
      const sp = createBodyTexSprite(0xffffff)
      loadSpriteTexture(sp, def.tex)
      sp.renderOrder = 20
      sp.visible = false
      diagramGroup.add(sp)
      diagramBodies[name] = { sprite: sp, size: def.size, helio: DIAGRAM_HELIO_NAME[name] }
    }
    // 9 条真实椭圆轨道环：8大行星(含地球) + 冥王星；共面黄道(I=0)，冥王星保留真实倾角(~17°)
    const DIAGRAM_RING_NAMES = ['Mercury', 'Venus', 'Earth', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']
    const _diagramRingUniforms = { uColor: { value: new T.Color(0.55, 0.72, 1.0) } }
    const diagramRingVert = `
      attribute float radial;
      varying float vR;
      void main() {
        vR = radial;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `
    const diagramRingFrag = `
      precision highp float;
      uniform vec3 uColor;
      varying float vR;
      void main() {
        float edge = smoothstep(0.0, 0.5, vR) * smoothstep(1.0, 0.5, vR);  // 带宽柔边（中间亮、内外缘消隐）
        gl_FragColor = vec4(uColor, edge * 0.55);
      }
    `
    function makeDiagramRingGeometry(a, e, wRad, ratio, width, N) {
      const b = a * Math.sqrt(1 - e * e) * ratio
      const ar = a * ratio
      const cw = Math.cos(wRad), sw = Math.sin(wRad)
      const center = []
      for (let i = 0; i <= N; i++) {
        const E = 2 * Math.PI * i / N
        const x1 = ar * (Math.cos(E) - e)
        const y1 = b * Math.sin(E)
        const x = x1 * cw - y1 * sw
        const y = x1 * sw + y1 * cw
        center.push(new T.Vector2(x, y))
      }
      const positions = [], radials = [], indices = []
      for (let i = 0; i <= N; i++) {
        const p = center[i]
        const len = Math.hypot(p.x, p.y) || 1
        const dx = p.x / len, dy = p.y / len
        positions.push(p.x - dx * width / 2, p.y - dy * width / 2, 0, p.x + dx * width / 2, p.y + dy * width / 2, 0)
        radials.push(0, 1)
      }
      for (let i = 0; i < N; i++) {
        const o = i * 2
        indices.push(o, o + 1, o + 2, o + 1, o + 3, o + 2)
      }
      const geo = new T.BufferGeometry()
      geo.setAttribute('position', new T.Float32BufferAttribute(positions, 3))
      geo.setAttribute('radial', new T.Float32BufferAttribute(radials, 1))
      geo.setIndex(indices)
      return geo
    }
    for (const name of DIAGRAM_RING_NAMES) {
      const helio = DIAGRAM_HELIO_NAME[name] || name   // Earth→EMBary（PLANET_ELEMENTS 以 EMBary 为键）
      const el = keplerElems(helio, Date.now())
      const ratio = diagramCompress(el.a) / el.a
      const width = el.a * ratio * 0.05
      const geo = makeDiagramRingGeometry(el.a, el.e, el.w, ratio, width, 256)
      const mat = new T.ShaderMaterial({
        uniforms: _diagramRingUniforms,
        vertexShader: diagramRingVert,
        fragmentShader: diagramRingFrag,
        transparent: true, blending: T.AdditiveBlending, depthWrite: false, side: T.DoubleSide,
      })
      const ring = new T.Mesh(geo, mat)
      if (name === 'Pluto') ring.rotation.x = PLANET_ELEMENTS.Pluto.I[0] * DEG  // 保留真实轨道倾角
      ring.renderOrder = 15
      ring.frustumCulled = false
      ring.visible = false
      diagramGroup.add(ring)
      diagramRings.push(ring)
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
      // 行星可见性改为每体阈值查表（见下方循环）；state.planetsVisible 在循环后汇总
      state.moonVisible = showMoon
      state.sunVisible = showSun

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
      moon.visible = showMoon && !_heroMode && !_diagramMode
      sun.visible = showSun && !_heroMode && !_diagramMode
      sunHalo.visible = showSun && !_heroMode && !_diagramMode   // Bug 1 修复 + Hero 模式隐藏

      // ── #53/#54 行星更新：每体独立可见性档(PLANET_VISIBLE_DIST) ──
      for (const name of PLANET_NAMES) {
        const P = planets[name]
        const visible = camDistEarth >= PLANET_VISIBLE_DIST[name]
        P.visible = visible
        P.sprite.visible = visible && !_heroMode && !_diagramMode
        if (visible) {
          const dir = planetGeoDir(name, nowMs)        // 真实地心方向（日心−地球日心）
          const pos = earthCenter.clone().add(new T.Vector3(dir.x, dir.y, dir.z).multiplyScalar(P.dist))
          P.sprite.position.copy(pos)
          P.worldPos = pos
          const camToP = camera.position.distanceTo(pos)
          const d = 2 * camToP * Math.tan((P.ang * DEG) / 2)  // 恒定角直径（风格化）
          applyAspectScale(P.sprite, d)   // Bug 2 修复：按贴图长宽比缩放，避免非正方形被拉伸
          const ndc = pos.clone().project(camera)
          P.ndc = [round(ndc.x, 4), round(ndc.y, 4)]
        } else {
          P.worldPos = null
        }
      }
      state.planetsVisible = PLANET_NAMES.some(function (n) { return planets[n].visible })

      // ── #54 代表性卫星：仅母行星可见时显示，圆轨道共面黄道（illustrative）──
      const daysJ2000 = pJulian(nowMs) - 2451545.0
      for (const parentName in satellites) {
        const parent = planets[parentName]
        const parentVisible = parent && parent.visible && parent.worldPos
        for (const s of satellites[parentName]) {
          if (!parentVisible) { s.visible = false; s.sprite.visible = false; continue }
          const ang = 2 * Math.PI * (daysJ2000 / s.def.periodDays + s.def.phase0)
          const ox = Math.cos(ang) * s.def.sceneRadius
          const oy = Math.sin(ang) * s.def.sceneRadius
          // 黄道平面偏移 → 赤道系（绕 X 转 +ε），与行星方向同源
          const ex = ox
          const ey = oy * Math.cos(EPS)
          const ez = oy * Math.sin(EPS)
          const sp = parent.worldPos.clone().add(new T.Vector3(ex, ey, ez))
          s.sprite.position.copy(sp)
          const camToS = camera.position.distanceTo(sp)
          const sd = 2 * camToS * Math.tan((s.def.ang * DEG) / 2)
          applyAspectScale(s.sprite, sd)   // Bug 2 修复
          s.sprite.visible = !_heroMode
          s.visible = true
          const sndc = sp.clone().project(camera)
          s.ndc = [round(sndc.x, 4), round(sndc.y, 4)]
        }
      }

      // 公转轨道环 + 地球标记：仅 deepSpace（与太阳晕同阈值 SUN_VISIBLE_DIST）。
      // 与 near-field 太阳晕独立；标记角度 = 真实地球日心黄道经度（随日期变化）。
      const showOrbit = camDistEarth >= SUN_VISIBLE_DIST
      state.orbitVisible = showOrbit
      orbitRing.visible = showOrbit && !_heroMode && !_diagramMode
      earthMarker.visible = showOrbit && !_heroMode && !_diagramMode
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
        sun.scale.set(d * pulse, d * pulse, 1)       // 真实贴图核心盘（含呼吸）
        sunHalo.scale.set(d * 1.7 * pulse, d * 1.7 * pulse, 1) // 光晕稍大，柔和溢出
        sunHalo.position.copy(sunPos)               // 光晕跟着太阳走
        state.sunWorldDiameter = round(d, 4)
        state.sunAngDiamDeg = round(SUN_ANG_DIAM, 4)
      }

      // 月相：世界坐标 (太阳 − 月亮) 方向
      moonUniforms.uSunDir.value.copy(sunPos).sub(moonPos).normalize()

      // ── Hero 肖像：独照模式，更新球体光照 + 缓慢自转（展示等距柱状全球贴图）──
      if (_heroMode && heroSpheres[_heroMode]) {
        const h = heroSpheres[_heroMode]
        // 行星→太阳 世界方向：hero 星球远离地球中心，必须用真实太阳世界位置重算（不能复用 sunDir）
        _heroSunDir.copy(sunPos).sub(h.group.position)
        if (_heroSunDir.lengthSq() < 1e-6) _heroSunDir.set(0, 0, 1)
        _heroSunDir.normalize()
        h.mat.uniforms.uSunDir.value.copy(_heroSunDir)   // 点亮朝阳半球
        h.mesh.rotation.y += h.spin
      }

      // ── 太阳系示意图：更新 10 天体位置（日心坐标 × 统一压缩比例），每帧用真实时刻 ──
      if (_diagramMode) {
        const nowD = Date.now()
        for (const name of DIAGRAM_BODY_ORDER) {
          const b = diagramBodies[name]
          if (b.helio) {
            const h = keplerHelioEcl(b.helio, nowD)
            const ratio = diagramCompress(h.a) / h.a
            b.sprite.position.set(h.x * ratio, h.y * ratio, h.z * ratio)
          } else {
            b.sprite.position.set(0, 0, 0)  // 太阳固定在示意图原点
          }
          applyAspectScale(b.sprite, b.size)
        }
      }

// 太阳呼吸缩放已合入 showSun 分支（含光晕）

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
          sunHaloVisible: sunHalo.visible,  // Bug 1 调试字段：光晕是否被 showSun 门控
          heroMode: _heroMode,              // Step 1 调试字段：当前是否处于某行星独照视图
          hero: {
            mode: _heroMode,
            marsGroupVisible: !!(heroSpheres.mars && heroSpheres.mars.group.visible),
            saturnGroupVisible: !!(heroSpheres.saturn && heroSpheres.saturn.group.visible),
            pose: _heroMode ? window.realCelestial.getHeroPose(_heroMode) : null,
          },
          diagramMode: _diagramMode,        // §1 调试字段：太阳系示意图是否激活
          diagram: {
            mode: _diagramMode,
            groupVisible: diagramGroup.visible,
            bodyCount: DIAGRAM_BODY_ORDER.length,
            ringCount: diagramRings.length,
          },
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
              ang: P.ang, bright: round(P.bright, 3), rgb: P.rgb,
              texture: P.texture || null, ndc: P.ndc,
              texAspect: round(P.sprite.userData.aspect || 1, 4),  // Bug 2 调试字段：贴图原始长宽比
            }
          }),
          satellites: Object.keys(satellites).reduce(function (acc, parentName) {
            acc[parentName] = satellites[parentName].map(function (s) {
              return { name: s.def.name, visible: s.visible, ndc: s.ndc, parent: parentName }
            })
            return acc
          }, {}),
        }
      },
      // ── Step 1 Hero 独照 API（供 earth3d 专用构图调用）──
      setHeroMode: function (name) {
        _heroMode = (name && heroSpheres[name]) ? name : null
        // 与示意图视图互斥：进入 Hero 时退出示意图
        if (_heroMode && _diagramMode) {
          _diagramMode = null
          diagramGroup.visible = false
          for (const k in diagramBodies) diagramBodies[k].sprite.visible = false
          for (const r of diagramRings) r.visible = false
        }
        // 切换可见性：仅当前 hero 球体可见，其余全部隐藏；非 hero 模式时全部隐藏
        for (const k in heroSpheres) heroSpheres[k].group.visible = (k === _heroMode)
        return _heroMode
      },
      // ── 太阳系示意图 API（供 earth3d 专用构图调用）──
      setDiagramMode: function (on) {
        _diagramMode = !!on
        // 与 Hero 独照互斥：进入示意图时退出 Hero
        if (_diagramMode && _heroMode) {
          _heroMode = null
          for (const k in heroSpheres) heroSpheres[k].group.visible = false
        }
        diagramGroup.visible = _diagramMode
        for (const name in diagramBodies) diagramBodies[name].sprite.visible = _diagramMode
        for (const r of diagramRings) r.visible = _diagramMode
        return _diagramMode
      },
      getDiagramPose: function () {
        if (!_diagramMode) return null
        const center = diagramGroup.position   // 太阳在示意图原点 (0,0,0)
        const elev = 30 * DEG   // 俯视仰角（参考图：斜上方俯视整个盘面）
        const R = 60            // 相机距离：容纳冥王星环（外半径 14）+ 留白
        const camPos = [
          center.x + R * Math.cos(elev) * Math.sin(0),
          center.y + R * Math.sin(elev),
          center.z + R * Math.cos(elev) * Math.cos(0),
        ]
        return {
          target: [center.x, center.y, center.z],
          camera: camPos,
          fov: 35,
        }
      },
      // 临时调试：返回示意图天体状态（验证用，可后续移除）
      _debugDiagramBodies: function () {
        return Object.keys(diagramBodies).map(function (name) {
          const sp = diagramBodies[name].sprite
          return { name: name, mapLoaded: !!(sp.material.map && sp.material.map.image), vis: sp.visible, pos: [+sp.position.x.toFixed(2), +sp.position.y.toFixed(2)], scale: [+sp.scale.x.toFixed(2), +sp.scale.y.toFixed(2)] }
        })
      },
      _debugDiagramRings: function () {
        return diagramRings.map(function (r, i) { return { idx: i, vis: r.visible } })
      },
      _debugSetBodyScale: function (name, sx, sy) {
        if (diagramBodies[name]) diagramBodies[name].sprite.scale.set(sx || 8, sy || 8, 1)
      },
      // 持久缩放覆盖（tick 中 applyAspectScale 会检查此值）
      _debugOverrideScales: null,   // { Sun: [sx,sy], ... } 或 null=不覆盖
      _debugSetAllBlending: function (modeStr) {
        const bm = { normal: T.NormalBlending, additive: T.AdditiveBlending }[modeStr]
        if (!bm) return
        for (const k in diagramBodies) diagramBodies[k].sprite.material.blending = bm
      },
      getHeroPose: function (name) {
        const key = name || _heroMode
        if (!key || !heroSpheres[key]) return null
        const h = heroSpheres[key]
        const planetPos = h.group.position
        const fov = 28
        const vHalf = Math.tan((fov * DEG) / 2)            // 垂直半视角 (tan)
        const aspect = (camera && camera.aspect) ? camera.aspect : 1
        const hHalf = vHalf * aspect                        // 水平半视角 (tan)；竖屏 aspect<1 时更小
        const minHalf = Math.min(vHalf, hHalf)              // 取较短边对应的半视角
        // 有环行星（土星）：以环外径为基准取景，让环系统约占短边 80%、球体约 35%，四周留白
        // 无环行星（火星）：球体直径占短边 40%
        const hasRing = !!(h.def && h.def.ring)
        const refRadius = hasRing ? h.def.ring.outer : h.radius
        const fill = hasRing ? 0.70 : 0.40
        const d = refRadius / (fill * minHalf)
        // 相机方向：默认沿"行星→太阳"方向（朝阳侧，永远看到被照亮半球）
        const litDir = _heroSunDir.clone().normalize()
        let camDir = litDir.clone()
        // B2: 有轴倾角的行星（土星 26.7°）→ 俯视斜角相机（参考 Apple 天文壁纸）：
        //     相机放在行星上方（Y > planetY），略偏朝阳侧。
        //     这样看到完整球体 + 环从斜上方展开（非 edge-on），且亮半球仍占主导面。
        if (h.def && h.def.tiltDeg) {
          // 环法线（世界空间）：group 仅设了 rotation.z = tiltDeg，所以
          //   ringNormal = (sin(tiltDeg), cos(tiltDeg), 0)
          const tRad = h.def.tiltDeg * DEG
          const ringNormal = new T.Vector3(Math.sin(tRad), Math.cos(tRad), 0).normalize()
          // 俯仰角：从环法线向朝阳方向偏移 ~28°（相机在"环上方但略偏太阳"）
          const elevAxis = new T.Vector3().crossVectors(ringNormal, litDir)
          if (elevAxis.lengthSq() > 1e-6) {
            elevAxis.normalize()
            camDir = ringNormal.clone().applyAxisAngle(elevAxis, -18 * DEG)
          }
        }
        const camPos = planetPos.clone().add(camDir.multiplyScalar(d))
        return {
          target: [planetPos.x, planetPos.y, planetPos.z],
          camera: [camPos.x, camPos.y, camPos.z],
          fov: fov,
          radius: h.radius,
          sunDir: [_heroSunDir.x, _heroSunDir.y, _heroSunDir.z],
        }
      },
    }
  }
})()
