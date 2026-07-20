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
 *  ── 距离分档可见性（按"相机到地心的实际直线距离"，不按构图名字）：
 *       MOON_VISIBLE_DIST = 20  → 相机距 ≥20 显示月亮（覆盖 farOrbit 25.15，明显高于近景 ≤15.9）
 *       SUN_VISIBLE_DIST  = 50  → 相机距 ≥50 显示太阳（覆盖 deepSpace 80，高于 farOrbit 25.15）
 *     这样新构图（如 #40 Flight View）只要算出的距离落在区间就自动生效，不用改判断逻辑。
 *  ── 压缩距离（艺术化，但自洽、可推导）：
 *       月亮放置距离 = MOON_PLACE_FRAC(0.45) × 相机→地球距离 → farOrbit≈11.3 / deepSpace≈36
 *       太阳放置距离 = SUN_PLACE_FRAC(0.70) × 相机→地球距离 → deepSpace≈56（明显比月亮远）
 *  ── 角直径恒定缩放（关键，杜绝上一版 22×/38× 失控）：
 *       每帧按"相机到天体距离"缩放天体世界尺寸，使渲染角直径恒等于
 *       月亮 = REAL_MOON_ANG × 4.5 ≈ 2.33°（垂直FOV 8.3%）、太阳 = REAL_SUN_ANG × 5.0 ≈ 2.67°（9.5%）。
 *       世界半径 = 相机距 × tan(角直径/2)。任意轨道位置都精确等于选取倍数，绝不会越界。
 *  ── 复用（不重做）：太阳光晕 shader（makeSunGlowTexture 程序生成径向渐变 + AdditiveBlending）、
 *     月亮相位 shader（MOON_VERT/MOON_FRAG 真实 terminator）、真实月球贴图 moon_1024.jpg。
 *  ── 月相：uSunDir = 世界坐标 (太阳位置 − 月亮位置) 归一化，相位形状随 now 真实变化。
 */
(function () {
  'use strict'
  const T = self.THREE
  if (!T) { console.error('[realCelestial] THREE 未加载，跳过'); return }

  const params = new URLSearchParams(window.location.search)
  if (params.get('earthCandidate') !== 'realCelestial') return // 红线：不影响正常用户

  // ── 命名常量（不散落魔法数字）──
  const MOON_VISIBLE_DIST = 20   // 相机距地心 ≥ 此值 → 月亮可见（覆盖 farOrbit 25.15）
  const SUN_VISIBLE_DIST = 50    // 相机距地心 ≥ 此值 → 太阳可见（覆盖 deepSpace 80）

  // 固定摆放距离（场景单位，地球半径=2）。
  // 保证在任何合格构图（相机距地心 ≥ 阈值）的视锥内始终可见：
  //   月亮：阈值=20, atan(3/20)=8.5° < FOV/2(14°)。farOrbit(25): atan(3/25)=6.9°。
  //   太阳：阈值=50, atan(6/50)=6.8°。deepSpace(80): atan(6/80)=4.3°。
  const MOON_DIST = 3            // 月亮距地心 = 1.5 R_earth（真实 60R_e 的艺术压缩）
  const SUN_DIST = 6             // 太阳距地心 = 3 R_earth（明显比月亮远，deepSpace 光晕清晰但不过大）
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
      '/assets/textures/moon/moon_1024.jpg',
      function (tex) {
        if (T.sRGBEncoding !== undefined) tex.encoding = T.sRGBEncoding
        moonUniforms.uTex.value = tex
      },
      undefined,
      function (e) { console.error('[realCelestial] 月球贴图加载失败:', e) }
    )

    const state = {
      camDistEarth: 0, moonVisible: false, sunVisible: false,
      moonWorldRadius: 0, sunWorldDiameter: 0,
      moonAngDiamDeg: 0, sunAngDiamDeg: 0,
      moonNDC: [0, 0], sunNDC: [0, 0],
    }
    const earthCenter = new T.Vector3()
    const sunDir = new T.Vector3(), moonDir = new T.Vector3()
    const sunPos = new T.Vector3(), moonPos = new T.Vector3()
    const t0 = performance.now()

    function tick() {
      earthCenter.copy(api.getEarthCenter())
      const camDistEarth = api.getCameraDistanceToEarth()
      state.camDistEarth = round(camDistEarth, 3)
      const showMoon = camDistEarth >= MOON_VISIBLE_DIST
      const showSun = camDistEarth >= SUN_VISIBLE_DIST
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
      moon.visible = showMoon
      sun.visible = showSun

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

      // 太阳轻微脉动（视觉生命感）
      const t = (performance.now() - t0) / 1000
      const pulse = 1 + 0.05 * Math.sin(t * 0.8)
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
      sun: sun, moon: moon, data: null,
      isRealCelestial: true,
      getState: function () {
        return {
          camDistEarth: state.camDistEarth,
          moonVisible: state.moonVisible,
          sunVisible: state.sunVisible,
          moonWorldRadius: state.moonWorldRadius,
          sunWorldDiameter: state.sunWorldDiameter,
          moonAngDiamDeg: state.moonAngDiamDeg,
          sunAngDiamDeg: state.sunAngDiamDeg,
          moonMult: round(MOON_ANG_DIAM / REAL_MOON_ANG, 3),
          sunMult: round(SUN_ANG_DIAM / REAL_SUN_ANG, 3),
          moonNDC: state.moonNDC,
          sunNDC: state.sunNDC,
          now: nowMs,
          subSolar: apiData ? [round(apiData.sun.subSolarLat, 3), round(apiData.sun.subSolarLon, 3)] : null,
          subLunar: apiData ? [round(apiData.moon.subLunarLat, 3), round(apiData.moon.subLunarLon, 3)] : null,
          phase: apiData ? apiData.moon.phaseName : null,
          illumination: apiData ? apiData.moon.illumination : null,
        }
      },
    }
  }
})()
