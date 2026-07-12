(function () {
  const TEXTURE_LON_OFFSET = 90
  // Production day texture source: BMNG tile stream only.
  const DAY_TEXTURE_VARIANT = 'bmng21k_stream'
  // [archived] RAW: { tileSource: '/assets/earth/bmng21k/topo_bathy/tiles/', pipeline: 'raw', allowFallback: false, cachePrefix: 'raw' }
  // [archived] NOON_AIR: { tileSource: '/assets/earth/bmng21k/topo_bathy/tiles_noon_air/', pipeline: 'noon_air_full', allowFallback: false, cachePrefix: 'noon_air' }
  // [archived] V2_ENHANCED: { tileSource: '/assets/earth/bmng21k/topo_bathy/tiles_v2_enhanced/', pipeline: 'v2_global_baseline', allowFallback: false, cachePrefix: 'v2' }
  // [archived] NOON_AIR_V2: { tileSource: '/assets/earth/bmng21k/topo_bathy/tiles_noon_air_v2/', pipeline: 'noon_air_v2_final', allowFallback: false, cachePrefix: 'nav2' }
  const EARTH_MODES = window.EARTH_MODES || {
    NOON_AIR_V2_ISLANDS: {
      tileSource: '/assets/earth/bmng21k/topo_bathy/tiles_noon_air_v2_islands/',
      pipeline: 'noon_air_v2_island_pass',
      allowFallback: false,
      cachePrefix: 'nav2i',
    },
  }
  let EARTH_MODE = 'NOON_AIR_V2_ISLANDS'
  const DEBUG_MARKERS_ENABLED = false
  const DEBUG_CITIES = [
    { name: 'Shanghai', lon: 121.4737, lat: 31.2304, color: 0xff3300 },
    { name: 'Tokyo', lon: 139.6917, lat: 35.6895, color: 0xffff00 },
    { name: 'London', lon: 0, lat: 51.5, color: 0x00ff66 },
    { name: 'NewYork', lon: -74, lat: 40.7, color: 0x3399ff },
    { name: 'Sydney', lon: 151.2, lat: -33.9, color: 0xff66ff }
  ]

  // ─── 七曜 (Shichiyou) rimGlow tint ───────────────────────────────────────
  // Per-weekday subtle hue offset applied to deepNight rimGlow colors only.
  // 18% blend keeps the shift restrained while still perceptibly tinting the
  // limb toward the day's planetary color (ref: Japanese day-of-week naming).
  const SHICHIYOU_TINT = [
    { name: '日曜', color: '#F2C879' },  // 0 周日，暖金
    { name: '月曜', color: '#6D8796' },  // 1 周一，冷银蓝
    { name: '火曜', color: '#C97A5A' },  // 2 周二，橙红
    { name: '水曜', color: '#7FADC2' },  // 3 周三，浅青蓝
    { name: '木曜', color: '#8A6D3B' },  // 4 周四，深琥珀
    { name: '金曜', color: '#C9A0A5' },  // 5 周五，暖玫瑰金
    { name: '土曜', color: '#8B7D6B' },  // 6 周六，灰褐
  ]

  // 七曜零点交接仪式的窗口半宽（秒）：23:58:30→00:00:00 隐退 + 00:00:00→00:01:30 浮现。
  // getShichiyouCeremonyBlendFactor 与 _tickCeremony 共用，避免魔法数字不同步。
  const SHICHIYOU_CEREMONY_WINDOW_SECONDS = 90

  // Blend a base rimGlow color toward the weekday tint. Returns a THREE.Color
  // (matching the .value.set() assignment format used by applyRimGlowThemeConfig).
  function applyShichiyouTint(baseHexColor, tintHexColor, blendFactor = 0.18) {
    const base = new THREE.Color(baseHexColor)
    const tint = new THREE.Color(tintHexColor)
    return base.lerp(tint, blendFactor)
  }

  // 七曜零点交接仪式：在 23:58:30→00:00:00 隐退、00:00:00→00:01:30 浮现
  // 两个 90 秒窗口内，把 blend 从常态 BASE 线性降到 0（隐退）再升回 BASE（浮现），
  // 形成 rimGlow 色相偏移的"呼吸式"过渡。窗口外保持常态 BASE。
  function getShichiyouCeremonyBlendFactor(now = new Date()) {
    const BASE = 0.18
    const secondsSinceMidnight = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds()
    const secondsUntilMidnight = 86400 - secondsSinceMidnight
    if (secondsUntilMidnight <= SHICHIYOU_CEREMONY_WINDOW_SECONDS && secondsUntilMidnight > 0) {
      return BASE * (secondsUntilMidnight / SHICHIYOU_CEREMONY_WINDOW_SECONDS) // 隐退：BASE → 0
    }
    if (secondsSinceMidnight < SHICHIYOU_CEREMONY_WINDOW_SECONDS) {
      return BASE * (secondsSinceMidnight / SHICHIYOU_CEREMONY_WINDOW_SECONDS) // 浮现：0 → BASE
    }
    return BASE // 常态
  }

  function lerp(a, b, t) {
    return a + (b - a) * t
  }

  function clamp(v, min, max) {
    return Math.min(max, Math.max(min, v))
  }

  function damp(current, target, factor) {
    return current + (target - current) * factor
  }

  function normalizeLon(lon) {
    let value = Number.isFinite(lon) ? lon : 121.4737
    while (value < -180) value += 360
    while (value > 180) value -= 360
    return value
  }

  function buildStarField(count, radius) {
    const positions = new Float32Array(count * 3)
    const sizes = new Float32Array(count)
    const colors = new Float32Array(count * 3)
    const phases = new Float32Array(count)
    for (let i = 0; i < count; i += 1) {
      const u = Math.random()
      const v = Math.random()
      const theta = 2 * Math.PI * u
      const phi = Math.acos(2 * v - 1)
      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = radius * Math.cos(phi)
      positions[i * 3 + 2] = radius * Math.sin(phi) * Math.sin(theta)
      // Power-law magnitude distribution — real skies are mostly faint stars
      // with a handful of bright ones, not uniform same-size dots.
      const m = Math.pow(Math.random(), 2.8)
      sizes[i] = 0.35 + m * 2.0
      const brightness = 0.35 + m * 0.85
      // Temperature tint: mostly near-white, some cool blue-white, some warm ivory.
      const t = Math.random()
      let r, g, b
      if (t < 0.60)      { r = 1.00; g = 1.00; b = 1.00 }
      else if (t < 0.85) { r = 0.82; g = 0.90; b = 1.00 }
      else               { r = 1.00; g = 0.90; b = 0.76 }
      colors[i * 3]     = r * brightness
      colors[i * 3 + 1] = g * brightness
      colors[i * 3 + 2] = b * brightness
      phases[i] = Math.random() * Math.PI * 2
    }
    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geometry.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1))
    geometry.setAttribute('aColor', new THREE.BufferAttribute(colors, 3))
    geometry.setAttribute('aPhase', new THREE.BufferAttribute(phases, 1))
    return geometry
  }

  function lonLatToVector3(lon, lat, radius = 1) {
    const latRad = THREE.MathUtils.degToRad(lat)
    const lonRad = THREE.MathUtils.degToRad(lon + TEXTURE_LON_OFFSET)

    return new THREE.Vector3(
      Math.cos(latRad) * Math.sin(lonRad),
      Math.sin(latRad),
      Math.cos(latRad) * Math.cos(lonRad)
    ).multiplyScalar(radius)
  }

  function lonLatToNorthTangent(lon, lat) {
    const latRad = THREE.MathUtils.degToRad(lat)
    const lonRad = THREE.MathUtils.degToRad(lon + TEXTURE_LON_OFFSET)

    return new THREE.Vector3(
      -Math.sin(latRad) * Math.sin(lonRad),
      Math.cos(latRad),
      -Math.sin(latRad) * Math.cos(lonRad)
    ).normalize()
  }

  function quaternionFromBasis(sourceNormal, sourceNorth, targetNormal, targetNorth) {
    const sourceEast = new THREE.Vector3()
      .crossVectors(sourceNorth, sourceNormal)
      .normalize()

    const correctedSourceNorth = new THREE.Vector3()
      .crossVectors(sourceNormal, sourceEast)
      .normalize()

    const targetEast = new THREE.Vector3()
      .crossVectors(targetNorth, targetNormal)
      .normalize()

    const correctedTargetNorth = new THREE.Vector3()
      .crossVectors(targetNormal, targetEast)
      .normalize()

    const sourceMatrix = new THREE.Matrix4().makeBasis(
      sourceEast,
      correctedSourceNorth,
      sourceNormal
    )

    const targetMatrix = new THREE.Matrix4().makeBasis(
      targetEast,
      correctedTargetNorth,
      targetNormal
    )

    const sourceQuat = new THREE.Quaternion().setFromRotationMatrix(sourceMatrix)
    const targetQuat = new THREE.Quaternion().setFromRotationMatrix(targetMatrix)

    return targetQuat.multiply(sourceQuat.invert()).normalize()
  }

  function createEarth3D() {
    const appEl = document.getElementById('app')
    const mountEl = document.getElementById('earth3d-layer')
    if (!appEl || !mountEl || !window.THREE) return false

    let renderer = null
    let observer = null
    let skyGeometry = null
    let skyMaterial = null
    let skyMesh = null
    let skyRadius = 300
    let earthGeometry = null
    let atmosphere = null
    let stars = null
    let isDestroyed = false
    let visibilityChangeHandler = null
    let _sunUpdateInterval = null
    let _ceremonyTimer = null   // 七曜零点交接仪式窗口内的 rimGlow 刷新定时器
    let earthMaterial = null
    let earthShaderUniforms = null   // retained from onBeforeCompile for per-theme uniform updates
    let atmosphereMaterial = null
    let atmosphere2Material = null   // thin rim layer (deepNight two-layer atmo)
    let atmosphere2 = null
    let tileManager = null
    let dayTexture = null
    let nightTexture = null
    const nightTextureOverrides = {}
    let oceanSpecularTexture = null
    let oceanSpecularTextureLoadState = 'idle'
    let oceanSpecularTextureWarned = false
    let normalMapTexture = null
    let normalMapTextureLoadState = 'idle'
    let oceanSpecularTexturePath = null
    let oceanMaskTexture = null
    let oceanMaskTextureLoadState = 'idle'
    let oceanTintGeometry = null
    let oceanTintMaterial = null
    let oceanTintMesh = null
    let cloudMesh = null
    let cloudMaterial = null
    let cloudTexture = null
    let starSphere = null
    let starSphereMaterial = null
    let starSphereLoaded = false
    let isReady = false
    let permanentlyUnavailable = false
    let currentDebugMode = null   // tracks active setDebugLayer mode; null = final/normal
    let _animDirty = true
    let _animFrameCount = 0
    let _starAnimStartTime = 0
    let _horizonGlowEl = null      // screen-space outer haze overlay (high blur)
    let _rimGlowEl    = null      // screen-space thin rim overlay (near-zero blur)
    let _horizonGlowCfg = null     // current theme's horizonGlow config
    let bootstrapDayAtlasImage = null
    let bootstrapDayAtlasState = 'idle'
    const earth3dApi = (window.earth3d && typeof window.earth3d === 'object') ? window.earth3d : {}
    window.earth3d = earth3dApi

    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
      renderer.setClearColor(0x000000, 0)
      if (typeof THREE.SRGBColorSpace !== 'undefined') {
        renderer.outputColorSpace = THREE.SRGBColorSpace
      } else if (typeof THREE.sRGBEncoding !== 'undefined') {
        renderer.outputEncoding = THREE.sRGBEncoding
      }
      renderer.domElement.id = 'earth3d-canvas'
      renderer.domElement.style.width = '100%'
      renderer.domElement.style.height = '100%'
      renderer.domElement.style.display = 'block'
      renderer.domElement.style.opacity = '0'
      renderer.domElement.style.transition = 'opacity 240ms ease'
      renderer.domElement.style.willChange = 'opacity'
      mountEl.appendChild(renderer.domElement)

      // Screen-space horizon glow overlays — sit above the WebGL canvas, below UI controls.
      // Two separate divs because rim needs blur≈1px, haze needs blur≈14px.
      _horizonGlowEl = document.createElement('div')
      _horizonGlowEl.id = 'earth-horizon-glow'
      Object.assign(_horizonGlowEl.style, {
        position: 'absolute', pointerEvents: 'none',
        top: '0', left: '0', width: '0', height: '0',
        mixBlendMode: 'screen', zIndex: '2',
        willChange: 'transform, opacity',
      })
      mountEl.appendChild(_horizonGlowEl)

      _rimGlowEl = document.createElement('div')
      _rimGlowEl.id = 'earth-rim-glow'
      Object.assign(_rimGlowEl.style, {
        position: 'absolute', pointerEvents: 'none',
        top: '0', left: '0', width: '0', height: '0',
        mixBlendMode: 'screen', zIndex: '3',
        willChange: 'transform, opacity',
      })
      mountEl.appendChild(_rimGlowEl)

      function markUnavailable() {
        isReady = false
        permanentlyUnavailable = true
        if (renderer) renderer.setAnimationLoop(null)
        if (renderer?.domElement) renderer.domElement.style.opacity = '0'
      }

      renderer.domElement.addEventListener('webglcontextlost', (event) => {
        event.preventDefault()
        markUnavailable()
      })

      const scene = new THREE.Scene()
      const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 1000)
      camera.position.set(0, 0, 4.8)
      camera.lookAt(0, 0, 0)

      // All themes use deep-space background. Daytime themes are slightly lighter than pitch-black
      // to avoid the "sticker on black cardboard" look, while remaining clearly orbital.
      function getSkyThemePreset(themeKey) {
        switch (themeKey) {
          case 'noon':
            return {
              top:     '#1a5080',
              horizon: '#5aa8e0',
              bottom:  '#2a6090',
              opacity: 0.90,
            }
          case 'morning':
            return {
              top:     '#0a3050',
              horizon: '#3a8cc0',
              bottom:  '#1a4a70',
              opacity: 0.94,
            }
          case 'afternoon':
            return {
              top:     '#0e3050',
              horizon: '#4090c0',
              bottom:  '#1e4a70',
              opacity: 0.95,
            }
          case 'evening':
            // Blue-hour sky: visible blue trace — deep navy fading to near-black.
            return {
              top:     '#020914',
              horizon: '#0D2740',
              bottom:  '#07182A',
              opacity: 0.98,
            }
          case 'lateEvening':
            // Late evening: darker than blue-hour, approaching deepNight.
            return {
              top:     '#01060D',
              horizon: '#071525',
              bottom:  '#040C16',
              opacity: 0.98,
            }
          case 'dawn':
            // Pre-dawn sky: black lifting to a thin deep-blue band at the
            // horizon — the first crack of light. Stars still thinning above.
            return {
              top:     '#01060d',
              horizon: '#0a2236',
              bottom:  '#061626',
              opacity: 0.98,
            }
          case 'sunrise':
            // Cold blue morning sky — the global sky sphere stays cool.
            // The previous '#ffb570' horizon painted warm gold across the
            // ENTIRE horizon band, washing the whole screen yellow; the
            // sun's warmth must come only from the localized right-side
            // horizonGlow hotspot, never from this global gradient.
            return {
              top:     '#020812',
              horizon: '#10263A',
              bottom:  '#081522',
              opacity: 0.98,
            }
          case 'goldenApproach':
            // Still full daylight brightness, warm-shifted — a dimmer, warmer
            // cousin of afternoon's sky, not yet approaching dusk darkness.
            return {
              top:     '#123252',
              horizon: '#e8a460',
              bottom:  '#1c3c58',
              opacity: 0.95,
            }
          case 'sunset':
            // Sun low on the horizon (sunDirection -x) — darker top than
            // goldenApproach, saturated orange horizon band, transitioning
            // toward evening's blue-hour palette.
            return {
              top:     '#050e1c',
              horizon: '#ff8a4a',
              bottom:  '#0a1c30',
              opacity: 0.97,
            }
          case 'deepNight':
          case 'night':
            // Near-black star-field sky — the horizon rimGlow supplies all the
            // blue; a bright sky gradient here washes the whole upper canvas
            // and kills the star field (ref: ISS night photo look).
            return {
              top:     '#010409',
              horizon: '#041020',
              bottom:  '#030a14',
              opacity: 0.98,
            }
          default:
            return {
              top:     '#000205',
              horizon: '#020810',
              bottom:  '#071018',
              opacity: 0.98,
            }
        }
      }

      // Themes that render the dedicated earlyMorning sky plane (Plan B) instead
      // of the standard skyMesh sphere. morning/noon/afternoon reuse the same
      // screen-space gradient plane, each with its own 4-stop color set.
      const DAY_SKY_PLANE_THEMES = new Set(['sunrise', 'goldenApproach', 'earlyMorning', 'morning', 'noon', 'afternoon', 'sunset'])

      // 4-stop sky plane gradient colors per theme. The shader maps:
      //   uTopColor     -> top of screen (y 0.68–1.00)
      //   uMidColor     -> middle (y 0.32–0.68)
      //   uLowerColor   -> horizon band (y 0.08–0.32)
      //   uHorizonColor -> bottom of screen, near earth (y 0–0.08)
      const SKY_PLANE_COLORS = {
        sunrise:      { top: '#061423', mid: '#102D46', lower: '#587D93', bottom: '#B5C7C9' },
        goldenApproach: { top: '#061A38', mid: '#0B315D', lower: '#2E5470', bottom: '#C0C3B8' },
        earlyMorning: { top: '#061a3a', mid: '#0b315f', lower: '#235f93', bottom: '#9fd0ed' },
        // morning/noon/afternoon derive from the earlyMorning palette above —
        // same hue family, brightness/temperature ramp only. noon is the
        // brightest sky of the four; afternoon cools the ramp back down and
        // drifts slightly warm-gray at the horizon (not dusk).
        morning:      { top: '#082246', mid: '#0f3d72', lower: '#3072a6', bottom: '#b0dcf4' },
        noon:         { top: '#0d2f5e', mid: '#175089', lower: '#4687b8', bottom: '#cfeafa' },
        afternoon:    { top: '#071c3c', mid: '#0c3462', lower: '#2f6a8e', bottom: '#c3d8dd' },
        sunset:       { top: '#020813', mid: '#081A2D', lower: '#102A3A', bottom: '#071018' },
      }

      function updateEarlyMorningSkyPlane(themeKey) {
        if (!_emSkyPlaneMat || !_emSkyPlaneMat.uniforms) return
        const c = SKY_PLANE_COLORS[themeKey]
        if (!c) return
        _emSkyPlaneMat.uniforms.uTopColor.value.set(c.top)
        _emSkyPlaneMat.uniforms.uMidColor.value.set(c.mid)
        _emSkyPlaneMat.uniforms.uLowerColor.value.set(c.lower)
        _emSkyPlaneMat.uniforms.uHorizonColor.value.set(c.bottom)
      }

      function updateSkyTheme(themeKey) {
        if (!skyMaterial || !skyMaterial.uniforms) return
        const preset = getSkyThemePreset(themeKey)
        skyMaterial.uniforms.uColorTop.value.set(preset.top)
        skyMaterial.uniforms.uColorHorizon.value.set(preset.horizon)
        skyMaterial.uniforms.uColorBottom.value.set(preset.bottom)
        skyMaterial.uniforms.uOpacity.value = preset.opacity
        // earlyMorning + morning/noon/afternoon use the dedicated sky plane;
        // restore skyMesh for all other themes.
        if (!DAY_SKY_PLANE_THEMES.has(themeKey) && skyMesh && !skyMesh.visible) {
          skyMesh.visible = true
        }
        skyMaterial.uniforms.uEnabled.value = DAY_SKY_PLANE_THEMES.has(themeKey) ? 0 : (skyMesh?.visible ? 1 : 0)
      }

      // 白天 tint 仍置 0（A/B 测试阶段，不干扰 dayTexture 判断）。
      // 夜晚主题补充极弱冷深蓝，给海洋添加暗部层次，不影响城市灯光。
      const OCEAN_TINT_BY_THEME = {
        morning:    { color: 0x164556, strength: 0 },
        noon:       { color: 0x1a4f5f, strength: 0 },
        afternoon:  { color: 0x123847, strength: 0 },
        evening:    { color: 0x041827, strength: 0.028 },
        lateEvening:{ color: 0x03131D, strength: 0.025 },
        deepNight:  { color: 0x031018, strength: 0.022 },
        dawn:       { color: 0x05161f, strength: 0.020 },
        night:      { color: 0x061624, strength: 0.09 },
      }

      const loader = new THREE.TextureLoader()
      let atlasFilterMode = window.__rodioAtlasFilterMode === 'normal' ? 'normal' : 'sharp'
      function configureEarthTexture(texture) {
        if ('colorSpace' in texture && THREE.SRGBColorSpace) {
          texture.colorSpace = THREE.SRGBColorSpace
        } else if (THREE.sRGBEncoding) {
          texture.encoding = THREE.sRGBEncoding
        }
        texture.anisotropy = Math.min(16, renderer.capabilities.getMaxAnisotropy())
        texture.minFilter = THREE.LinearMipmapLinearFilter
        texture.magFilter = THREE.LinearFilter
        texture.generateMipmaps = true
        texture.needsUpdate = true
        return texture
      }

      function configureAtlasTexture(texture, lod) {
        configureEarthTexture(texture)
        const useSharpAtlas = atlasFilterMode === 'sharp' && lod === '16k'
        if (useSharpAtlas) {
          texture.minFilter = THREE.LinearFilter
          texture.magFilter = THREE.LinearFilter
          texture.generateMipmaps = false
        }
        texture.needsUpdate = true
        return texture
      }

      function configureRegionalTexture(texture) {
        configureEarthTexture(texture)
        // Regional overlays are frequently inspected at oblique / LOW angles.
        // Keep mipmaps enabled here so anisotropic filtering has stable inputs
        // instead of stretching a single full-res level across the horizon.
        texture.minFilter = THREE.LinearMipmapLinearFilter
        texture.magFilter = THREE.LinearFilter
        texture.generateMipmaps = true
        texture.needsUpdate = true
        return texture
      }

      function applyRegionalTextureSampling(texture, auditProfile = getAuditViewProfile()) {
        if (!texture) return texture
        const inspectSharpenProfile = {
          top: { sharpen: 0.08, useMipmaps: true },
          oblique: { sharpen: 0.18, useMipmaps: false },
          low: { sharpen: 0.28, useMipmaps: false },
          normal: { sharpen: 0.0, useMipmaps: true },
        }
        const profile = inspectSharpenProfile[auditProfile] || inspectSharpenProfile.normal
        texture.anisotropy = Math.min(16, renderer.capabilities.getMaxAnisotropy())
        texture.magFilter = THREE.LinearFilter
        texture.minFilter = profile.useMipmaps
          ? THREE.LinearMipmapLinearFilter
          : THREE.LinearFilter
        texture.generateMipmaps = profile.useMipmaps
        texture.needsUpdate = true
        return profile
      }

      function loadTextureWithFallback(primaryPath, fallbackPath, onLoad) {
        const fallbacks = Array.isArray(fallbackPath)
          ? fallbackPath.filter(Boolean)
          : [fallbackPath].filter(Boolean)
        const paths = [primaryPath, ...fallbacks].filter(Boolean)
        let index = 0
        const tryLoad = () => {
          const path = paths[index]
          loader.load(
            path,
            (texture) => {
              onLoad(configureEarthTexture(texture), path)
            },
            undefined,
            () => {
              const nextPath = paths[index + 1]
              if (nextPath) {
                console.warn('[earth3d] texture fallback:', path, '->', nextPath)
                index += 1
                tryLoad()
              } else {
                console.error('[earth3d] texture load failed:', paths.join(', '))
              }
            }
          )
        }
        tryLoad()
      }

      function loadBootstrapDayAtlasImage() {
        if (bootstrapDayAtlasState !== 'idle') return
        bootstrapDayAtlasState = 'loading'
        const img = new Image()
        img.decoding = 'async'
        img.onload = () => {
          img.decode().then(() => {
            bootstrapDayAtlasImage = img
            bootstrapDayAtlasState = 'ready'
            if (tileManager?.redrawAtlasBaseLayer) {
              tileManager.redrawAtlasBaseLayer()
              requestRenderUpdate()
            }
          }).catch(() => {
            // decode() 失败兜底：按已解码对待，避免永久卡在 loading 态。
            // drawImage 在解码失败的 image 上通常表现为空白，总好过冻结整个管线。
            bootstrapDayAtlasImage = img
            bootstrapDayAtlasState = 'ready'
            if (tileManager?.redrawAtlasBaseLayer) {
              tileManager.redrawAtlasBaseLayer()
              requestRenderUpdate()
            }
          })
        }
        img.onerror = () => {
          bootstrapDayAtlasState = 'missing'
          console.warn('[earth3d] bootstrap day atlas image unavailable; keeping dark atlas placeholder')
        }
        img.src = '/assets/earth_day_8k.jpg'
      }

      function loadTextureWithFallbackLegacy(primaryPath, fallbackPath, onLoad) {
        loader.load(
          primaryPath,
          (texture) => {
            onLoad(configureEarthTexture(texture), primaryPath)
          },
          undefined,
          () => {
            console.warn('[earth3d] texture fallback:', primaryPath, '->', fallbackPath)
            loader.load(
              fallbackPath,
              (texture) => {
                onLoad(configureEarthTexture(texture), fallbackPath)
              },
              undefined,
              () => {
                console.error('[earth3d] texture load failed:', primaryPath, fallbackPath)
              }
            )
          }
        )
      }

      function getGpuMaxTextureSize() {
        try {
          return renderer.capabilities?.maxTextureSize || renderer.getContext()?.getParameter(renderer.getContext().MAX_TEXTURE_SIZE) || 8192
        } catch (_) {
          return 8192
        }
      }

      let _lastTextureSourceKey = null
      function resolveEarthTextureLOD(lodManager, deviceCaps, cameraState = {}) {
        const maxSize = (deviceCaps && deviceCaps.maxTextureSize) || getGpuMaxTextureSize()
        const rawDistance = Number.isFinite(cameraState.distance) ? cameraState.distance : 4.8
        // Zoom compensation: when the camera FOV is narrowed (zoom-in), fewer
        // tiles cover the viewport and each tile subtends a larger screen area,
        // making resolution limits more visible.  Scale the effective distance
        // by the FOV ratio so that zooming in behaves like moving closer —
        // denser LOD on asiaWide / global angles that would otherwise sit just
        // above the 8k threshold at default zoom.
        const distance = Number.isFinite(cameraState.fovDegrees)
          ? rawDistance * (cameraState.fovDegrees / 28)
          : rawDistance
        let lod
        if (maxSize >= 16384 && distance <= 5.6) {
          lod = '16k'
        } else if (maxSize >= 8192 && distance <= 7.2) {
          lod = '8k'
        } else {
          lod = '4k'
        }
        // atlasTileSize drives the canvas draw size per tile (1:1 with source resolution).
        // 16k: GPU maxSize >= 16384 is already verified above, so 4 cols × 4096 = 16384 wide is safe.
        // 8k:  2 cols × 4096 = 8192 wide (full source resolution, safe).
        // 4k:  2 cols × 2048 = 4096 wide (full source resolution, safe).
        const config = {
          lod,
          tileCols: lod === '16k' ? 4 : 2,
          tileRows: lod === '16k' ? 2 : 1,
          tileResolution: lod === '16k' ? 4096 : (lod === '8k' ? 4096 : 2048),
          atlasTileSize: lod === '16k' ? 4096 : (lod === '8k' ? 4096 : 2048),
          maxCachedTiles: lod === '16k' ? 8 : 4,
        }
        const _textureSourceKey = `${EARTH_MODE}:${config.lod}`
        if (_textureSourceKey !== _lastTextureSourceKey) {
          _lastTextureSourceKey = _textureSourceKey
          console.log('[earth] texture source:', `${EARTH_MODE} ${EARTH_MODES[EARTH_MODE].pipeline} tile stream ${config.lod}`)
        }
        return config
      }

      function tileGridForLod(lod) {
        return {
          cols: lod === '16k' ? 4 : 2,
          rows: lod === '16k' ? 2 : 1,
        }
      }

      function getEarthModeConfig(mode = EARTH_MODE) {
        const config = EARTH_MODES[mode]
        if (!config) throw new Error('Invalid EARTH_MODE')
        return config
      }

      function validateTileUrlForMode(url, mode = EARTH_MODE) {
        if (mode === 'NOON_AIR' && url.includes('bmng21k/topo_bathy/tiles') && !url.includes('tiles_noon_air')) {
          throw new Error('[FATAL MODE MISMATCH] RAW tile detected in NOON_AIR mode')
        }
        if (mode === 'RAW' && url.includes('tiles_noon_air')) {
          throw new Error('[FATAL MODE MISMATCH] NOON_AIR tile detected in RAW mode')
        }
        if (mode === 'RAW' && url.includes('tiles_v2_enhanced')) {
          throw new Error('[FATAL MODE MISMATCH] V2 tile detected in RAW mode')
        }
        if (mode === 'V2_ENHANCED' && !url.includes('tiles_v2_enhanced')) {
          throw new Error('[FATAL MODE MISMATCH] Non-V2 tile detected in V2_ENHANCED mode')
        }
        if (mode === 'NOON_AIR_V2' && !url.includes('tiles_noon_air_v2')) {
          throw new Error('[FATAL MODE MISMATCH] Non-NOON_AIR_V2 tile detected in NOON_AIR_V2 mode')
        }
        if (mode === 'NOON_AIR_V2_ISLANDS' && !url.includes('tiles_noon_air_v2_islands')) {
          throw new Error('[FATAL MODE MISMATCH] Non-NOON_AIR_V2_ISLANDS tile detected in NOON_AIR_V2_ISLANDS mode')
        }
        return url
      }

      function resolveTileUrl(modeName, lod, x, y) {
        const mode = getEarthModeConfig(modeName)
        const url = `${mode.tileSource}${lod}/tile_${x}_${y}.jpg`
        return validateTileUrlForMode(url, modeName)
      }

      function getTileUrl(lod, x, y) {
        return resolveTileUrl(EARTH_MODE, lod, x, y)
      }

      function requestRenderUpdate() {
        if (!renderer || !scene || !camera || permanentlyUnavailable) return
        _animDirty = true
        if (isReady && tileManager) {
          tileManager.updateStreaming(getStreamingCameraState(camera))
          updateRDLOverlays()
          renderer.render(scene, camera)
        }
      }

      function setEarthMode(mode) {
        if (!EARTH_MODES[mode]) throw new Error('Invalid EARTH_MODE')
        if (EARTH_MODE === mode) return EARTH_MODE
        EARTH_MODE = mode
        window.__rodioEarthMode = mode
        console.log('[earth] mode switched:', mode)
        if (tileManager) {
          tileManager.clearCache()
          tileManager.resetStreaming()
        }
        requestRenderUpdate()
        return EARTH_MODE
      }

      function computeVisibleTileSet(cameraState) {
        const lod = cameraState.lod || '16k'
        const tileCols = Math.max(1, cameraState.tileCols || 4)
        const tileRows = Math.max(1, cameraState.tileRows || 2)
        const lon = normalizeLon(Number.isFinite(cameraState.lon) ? cameraState.lon : 121.4737)
        const lat = clamp(Number.isFinite(cameraState.lat) ? cameraState.lat : 31.2304, -89.99, 89.99)
        const fov = Math.max(1, Number.isFinite(cameraState.fovDegrees) ? cameraState.fovDegrees : 52)
        const centerX = clamp(Math.floor((lon + 180) / 360 * tileCols), 0, tileCols - 1)
        const centerY = clamp(Math.floor((90 - lat) / 180 * tileRows), 0, tileRows - 1)
        // Polar/high-latitude views expose a lot more longitude near the visible
        // cap than this simple lon/fov heuristic suggests. If we keep a narrow
        // radiusX there, one missing top-row tile can show up as a dark diamond/
        // wedge over the Arctic/Antarctic. Be conservative and load the whole row.
        const polarWideLoad = tileRows > 1 && Math.abs(lat) >= 50
        const radiusX = polarWideLoad
          ? (tileCols - 1)
          : Math.max(0, Math.ceil(fov / (360 / tileCols) / 2))
        const radiusY = Math.max(0, Math.ceil(fov / (180 / tileRows) / 2))
        const keys = new Set()
        for (let dy = -radiusY; dy <= radiusY; dy += 1) {
          const y = centerY + dy
          if (y < 0 || y >= tileRows) continue
          for (let dx = -radiusX; dx <= radiusX; dx += 1) {
            const x = (centerX + dx + tileCols) % tileCols
            keys.add(`${lod}:${x}:${y}`)
          }
        }
        return Array.from(keys).sort().map((key) => {
          const [_lod, x, y] = key.split(':')
          return { lod: _lod, x: Number(x), y: Number(y) }
        })
      }

      class FrontendTileStreamingManager {
        constructor(renderer, lodManager) {
          this.renderer = renderer
          this.lodManager = lodManager
          this.activeTiles = new Map()
          this.tileCache = new Map()
          this.loadingTiles = new Set()
          this.cacheOrder = []
          this.cacheHits = 0
          this.cacheMisses = 0
          this.lastVisibleSignature = ''
          this.lastLod = null
          this.loadGeneration = 0
          this.lodConfig = resolveEarthTextureLOD(lodManager, renderer.capabilities)
          this.atlasCanvas = document.createElement('canvas')
          this.atlasContext = this.atlasCanvas.getContext('2d', { alpha: false })
          this.atlasTexture = new THREE.CanvasTexture(this.atlasCanvas)
          configureAtlasTexture(this.atlasTexture, this.lodConfig.lod)
          this.resetAtlas(this.lodConfig)
          // Tracks retry attempts per tile key — a failed fetch (transient network
          // hiccup) previously left that atlas cell black indefinitely, because
          // updateStreaming() only runs while the camera is animating or _animDirty
          // (see the setAnimationLoop callback); once idle, nothing re-requested
          // the tile until the user rotated the camera again.
          this.tileRetryCount = new Map()
        }

        redrawAtlasBaseLayer() {
          const width = this.atlasCanvas.width
          const height = this.atlasCanvas.height
          if (!width || !height || !this.atlasContext) return
          if (bootstrapDayAtlasImage && bootstrapDayAtlasState === 'ready') {
            this.atlasContext.drawImage(bootstrapDayAtlasImage, 0, 0, width, height)
          } else {
            this.atlasContext.fillStyle = '#020514'
            this.atlasContext.fillRect(0, 0, width, height)
          }
          this.atlasTexture.needsUpdate = true
        }

        requestVisibleTiles(cameraState) {
          const config = resolveEarthTextureLOD(this.lodManager, this.renderer.capabilities, cameraState)
          if (this.lastLod !== config.lod) {
            this.resetAtlas(config)
          }
          const visibleTiles = computeVisibleTileSet({
            ...cameraState,
            lod: config.lod,
            tileCols: config.tileCols,
            tileRows: config.tileRows,
            fovDegrees: cameraState.fovDegrees,
          })
          return visibleTiles
        }

        updateStreaming(cameraState) {
          const visibleTiles = this.requestVisibleTiles(cameraState)
          const signature = visibleTiles.map((tile) => `${tile.lod}:${tile.x}:${tile.y}`).join('|')
          const tilesChanged = signature !== this.lastVisibleSignature
          const stats = { hits: 0, misses: 0, pending: 0 }
          for (const tile of visibleTiles) {
            const key = this.tileKey(tile)
            if (this.tileCache.has(key)) {
              stats.hits += 1
              this.cacheHits += 1
              this.touchCacheKey(key)
              // tile 集合未变时跳过重绘，避免 camera 静止时每帧触发 canvas drawImage 和 GPU 上传
              if (tilesChanged) this.drawTile(tile, this.tileCache.get(key))
              this.activeTiles.set(key, tile)
            } else {
              stats.misses += 1
              this.cacheMisses += 1
              this.loadTileAsync(tile)
            }
            if (this.loadingTiles.has(key)) stats.pending += 1
          }
          if (tilesChanged) {
            const currentMode = getEarthModeConfig()
            console.log('[tile-stream]', {
              mode: EARTH_MODE,
              pipeline: currentMode.pipeline,
              tileSource: currentMode.tileSource,
              lod: this.lodConfig.lod,
              visibleTiles: visibleTiles.map((tile) => `${tile.lod}/${tile.x}/${tile.y}`),
              cacheHits: stats.hits,
              cacheMisses: stats.misses,
              pending: stats.pending,
              cacheSize: this.tileCache.size,
            })
            this.lastVisibleSignature = signature
          }
          return visibleTiles
        }

        loadTileAsync(tile) {
          const key = this.tileKey(tile)
          if (this.loadingTiles.has(key)) return
          this.loadingTiles.add(key)
          const modeAtRequest = EARTH_MODE
          const generation = this.loadGeneration
          const url = this.tileUrl(tile)
          console.log('[tile-request]', modeAtRequest, url)
          loader.load(
            url,
            (texture) => {
              this.loadingTiles.delete(key)
              this.tileRetryCount.delete(key)
              if (generation !== this.loadGeneration || modeAtRequest !== EARTH_MODE || key !== this.tileKey(tile)) {
                texture.dispose()
                return
              }
              configureEarthTexture(texture)
              this.addToCache(key, texture)
              this.drawTile(tile, texture)
              this.activeTiles.set(key, tile)
              if (!permanentlyUnavailable && isReady) {
                renderer.render(scene, camera)
              }
            },
            undefined,
            () => {
              this.loadingTiles.delete(key)
              const attempts = (this.tileRetryCount.get(key) || 0) + 1
              this.tileRetryCount.set(key, attempts)
              const maxRetries = 4
              if (attempts > maxRetries) {
                console.warn('[tile-stream] tile unavailable, giving up after', attempts - 1, 'retries:', key, url)
                return
              }
              const delayMs = 1000 * attempts
              console.warn('[tile-stream] tile unavailable, retry', attempts, 'of', maxRetries, 'in', delayMs + 'ms:', key, url)
              setTimeout(() => {
                // Stale checks: mode/generation may have changed, or the tile may
                // have already loaded via a different path (e.g. camera moved and
                // re-triggered updateStreaming before this retry fired).
                if (generation !== this.loadGeneration || modeAtRequest !== EARTH_MODE) return
                if (this.tileCache.has(key) || this.loadingTiles.has(key)) return
                this.loadTileAsync(tile)
              }, delayMs)
            }
          )
        }

        addToCache(key, texture) {
          if (this.tileCache.has(key)) {
            const previous = this.tileCache.get(key)?.texture || this.tileCache.get(key)
            if (previous !== texture) previous.dispose()
            this.tileCache.delete(key)
          }
          this.tileCache.set(key, { texture, mode: EARTH_MODE })
          this.touchCacheKey(key)
          while (this.cacheOrder.length > this.lodConfig.maxCachedTiles) {
            const evictKey = this.cacheOrder.shift()
            if (!evictKey || !this.tileCache.has(evictKey)) continue
            const evicted = this.tileCache.get(evictKey)?.texture || this.tileCache.get(evictKey)
            this.tileCache.delete(evictKey)
            this.activeTiles.delete(evictKey)
            if (evicted?.dispose) evicted.dispose()
          }
        }

        touchCacheKey(key) {
          this.cacheOrder = this.cacheOrder.filter((item) => item !== key)
          this.cacheOrder.push(key)
        }

        drawTile(tile, textureRecord) {
          const texture = textureRecord?.texture || textureRecord
          const image = texture?.image
          if (!image || !this.atlasContext) return
          const size = this.lodConfig.atlasTileSize
          this.atlasContext.imageSmoothingEnabled = false
          this.atlasContext.drawImage(
            image,
            tile.x * size,
            tile.y * size,
            size,
            size
          )
          this.atlasTexture.needsUpdate = true
        }

        resetAtlas(config) {
          this.lodConfig = config
          this.lastLod = config.lod
          const width = config.tileCols * config.atlasTileSize
          const height = config.tileRows * config.atlasTileSize
          if (this.atlasCanvas.width !== width) this.atlasCanvas.width = width
          if (this.atlasCanvas.height !== height) this.atlasCanvas.height = height
          this.redrawAtlasBaseLayer()
          configureAtlasTexture(this.atlasTexture, config.lod)
          this.activeTiles.clear()
          this.loadingTiles.clear()
          this.atlasTexture.needsUpdate = true
        }

        tileKey(tile) {
          const mode = getEarthModeConfig()
          return `${mode.cachePrefix}_${tile.lod}_${tile.x}_${tile.y}`
        }

        tileUrl(tile) {
          return getTileUrl(tile.lod, tile.x, tile.y)
        }

        clearCache() {
          this.tileCache.forEach((record) => (record?.texture || record)?.dispose?.())
          this.tileCache.clear()
          this.activeTiles.clear()
          this.cacheOrder = []
          this.cacheHits = 0
          this.cacheMisses = 0
        }

        resetStreaming() {
          this.loadGeneration += 1
          this.loadingTiles.clear()
          this.lastVisibleSignature = ''
          this.resetAtlas(this.lodConfig)
        }

        safeRefreshVisibleTiles() {
          // Non-destructive refresh for theme/light changes: keep the existing
          // atlas + cache, but force one visible-set pass so cached tiles redraw
          // immediately and any missing tiles continue loading.
          this.lastVisibleSignature = ''
        }

        dispose() {
          this.clearCache()
          this.loadingTiles.clear()
          if (this.atlasTexture) this.atlasTexture.dispose()
        }
      }

      function isLowSpecularDevice() {
        const smallViewport = Math.min(window.innerWidth || 0, window.innerHeight || 0) <= 820
        const coarsePointer = Boolean(window.matchMedia && window.matchMedia('(pointer: coarse)').matches)
        return smallViewport || coarsePointer
      }

      function getOceanSpecularTexturePaths() {
        const highResPath = '/assets/earth/masks/ocean_specular_4096x2048.png'
        const lowResPath = '/assets/earth/masks/ocean_specular_2048x1024.png'
        return isLowSpecularDevice()
          ? [lowResPath, highResPath]
          : [highResPath, lowResPath]
      }

      function configureOceanSpecularTexture(texture) {
        if ('encoding' in texture && typeof THREE.LinearEncoding !== 'undefined') {
          texture.encoding = THREE.LinearEncoding
        }
        texture.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy())
        texture.minFilter = THREE.LinearMipmapLinearFilter
        texture.magFilter = THREE.LinearFilter
        texture.generateMipmaps = true
        texture.needsUpdate = true
        return texture
      }

      function loadTextureIfExists(path) {
        return fetch(path, { method: 'HEAD' })
          .then((response) => {
            if (!response.ok) return null
            return new Promise((resolve) => {
              loader.load(
                path,
                (texture) => resolve(configureOceanSpecularTexture(texture)),
                undefined,
                () => resolve(null)
              )
            })
          })
          .catch(() => null)
      }

      async function loadOceanSpecularTexture() {
        if (oceanSpecularTextureLoadState !== 'idle') return oceanSpecularTexture
        oceanSpecularTextureLoadState = 'loading'

        const [preferredPath] = getOceanSpecularTexturePaths()
        const texture = await loadTextureIfExists(preferredPath)

        if (texture) {
          oceanSpecularTexture = texture
          oceanSpecularTextureLoadState = 'ready'
          oceanSpecularTexturePath = texture.image?.src || preferredPath

          const themeKey = pendingTheme || currentTheme || 'night'
          if (shouldUseOceanSpecularMap(themeKey)) {
            applyTheme(themeKey, { force: true })
            if (!permanentlyUnavailable && isReady) {
              renderer.render(scene, camera)
            }
          }
          return oceanSpecularTexture
        }

        oceanSpecularTextureLoadState = 'missing'
        if (!oceanSpecularTextureWarned) {
          oceanSpecularTextureWarned = true
          console.warn('[earth3d] ocean specular map unavailable; skipping')
        }
        return null
      }

      async function loadNormalMapTexture() {
        if (normalMapTextureLoadState !== 'idle') return normalMapTexture
        normalMapTextureLoadState = 'loading'
        const path = '/assets/earth_normal_8k.webp'
        const texture = await loadTextureIfExists(path)
        if (texture) {
          texture.colorSpace = THREE.NoColorSpace
          texture.needsUpdate = true
          normalMapTexture = texture
          normalMapTextureLoadState = 'ready'
          if (earthMaterial) {
            earthMaterial.normalMap = normalMapTexture
            earthMaterial.normalScale = new THREE.Vector2(0.15, 0.15)
            earthMaterial.needsUpdate = true
            if (!permanentlyUnavailable && isReady) renderer.render(scene, camera)
          }
          return normalMapTexture
        }
        normalMapTextureLoadState = 'missing'
        console.warn('[earth3d] normal map unavailable; skipping')
        return null
      }

      async function loadOceanMaskTexture() {
        if (oceanMaskTextureLoadState !== 'idle') return oceanMaskTexture
        oceanMaskTextureLoadState = 'loading'

        const path = '/assets/earth/masks/ocean_mask_4096x2048_soft.png'
        const texture = await loadTextureIfExists(path)

        if (isDestroyed) {
          if (texture) texture.dispose()
          return null
        }

        if (texture) {
          oceanMaskTexture = texture
          oceanMaskTextureLoadState = 'ready'

          // Wire ocean mask into the earth shader grade uniforms.
          // Grade strengths (uLandStr etc.) were initialised at 0; enable them now
          // using the current theme's nightGrade config.
          if (cloudMaterial?.uniforms) {
            cloudMaterial.uniforms.uOceanMask.value = oceanMaskTexture
          }
          if (earthShaderUniforms) {
            earthShaderUniforms.uOceanMask.value = oceanMaskTexture
            const _gradeTheme = pendingTheme || currentTheme || 'night'
            const _gradeCfg = THEME_VISUAL_CONFIG[_gradeTheme]?.nightGrade
            if (_gradeCfg) {
              earthShaderUniforms.uOceanLift.value    = _gradeCfg.oceanLift   ?? 0.5
              if (earthShaderUniforms.uOceanLiftTint) {
                const _lt = _gradeCfg.oceanLiftTint
                earthShaderUniforms.uOceanLiftTint.value.set(_lt?.[0] ?? 0.35, _lt?.[1] ?? 0.50, _lt?.[2] ?? 1.0)
              }
              earthShaderUniforms.uOceanTeal.value    = _gradeCfg.oceanTeal   ?? 0
              earthShaderUniforms.uDayOceanGrade.value = _gradeCfg.dayOceanGrade ? 1 : 0
              earthShaderUniforms.uOceanBlendStrength.value = _gradeCfg.oceanBlendStrength ?? 0
              earthShaderUniforms.uOceanDarken.value        = _gradeCfg.oceanDarken ?? 1
              earthShaderUniforms.uOceanContrast.value      = _gradeCfg.oceanContrast ?? 1
              earthShaderUniforms.uOceanSaturation.value    = _gradeCfg.oceanSaturation ?? 1
              earthShaderUniforms.uOceanBlueBias.value      = _gradeCfg.oceanBlueBias ?? 0
              earthShaderUniforms.uOceanRedReduce.value     = _gradeCfg.oceanRedReduce ?? 0
              earthShaderUniforms.uOceanGreenReduce.value   = _gradeCfg.oceanGreenReduce ?? 0
              earthShaderUniforms.uCoastProtection.value    = _gradeCfg.coastProtection ?? 0.75
              if (earthShaderUniforms.uOceanRawMix)      earthShaderUniforms.uOceanRawMix.value      = _gradeCfg.oceanRawMix ?? 0
              if (earthShaderUniforms.uOceanRawExposure) earthShaderUniforms.uOceanRawExposure.value = _gradeCfg.oceanRawExposure ?? 0.025
              if (earthShaderUniforms.uOceanRawBlueKeep) earthShaderUniforms.uOceanRawBlueKeep.value = _gradeCfg.oceanRawBlueKeep ?? 0.2
              earthShaderUniforms.uLandLift.value     = _gradeCfg.landLift    ?? 0.04
              earthShaderUniforms.uLandGamma.value    = _gradeCfg.landGamma   ?? 0.85
              earthShaderUniforms.uLandStr.value      = _gradeCfg.landStr     ?? 0.75
              earthShaderUniforms.uLandRedRed.value   = _gradeCfg.landRedRed  ?? 0.025
              earthShaderUniforms.uLandGreenB.value   = _gradeCfg.landGreenB  ?? 0.045
              earthShaderUniforms.uLandGlowStr.value  = _gradeCfg.landGlowStr ?? 0.10
              earthShaderUniforms.uCityLumLow.value   = _gradeCfg.cityLumLow  ?? 0.008
              earthShaderUniforms.uCityLumHigh.value  = _gradeCfg.cityLumHigh ?? 0.040
            }
            earthMaterial.needsUpdate = true
          }

          if (!oceanTintGeometry) {
            oceanTintGeometry = new THREE.SphereGeometry(2.002, 64, 64)
          }
          if (!oceanTintMaterial) {
            oceanTintMaterial = new THREE.MeshBasicMaterial({
              color: 0x164556,
              alphaMap: oceanMaskTexture,
              transparent: true,
              opacity: 0,
              depthWrite: false,
              depthTest: true,
            })
          }
          if (!oceanTintMesh) {
            oceanTintMesh = new THREE.Mesh(oceanTintGeometry, oceanTintMaterial)
            oceanTintMesh.renderOrder = 1
            oceanTintMesh.frustumCulled = false
            oceanTintMesh.visible = false
            earthGroup.add(oceanTintMesh)
          }

          const themeKey = pendingTheme || currentTheme || 'night'
          applyOceanTint(themeKey)
          if (!permanentlyUnavailable && isReady) {
            renderer.render(scene, camera)
          }
          return oceanMaskTexture
        }

        oceanMaskTextureLoadState = 'missing'
        console.warn('[earth3d] ocean mask unavailable; ocean tint skipped')
        return null
      }

      earthMaterial = new THREE.MeshPhongMaterial({
        color: 0x1a3a5c,
        shininess: 1,
        specular: new THREE.Color(0x05070a),
      })
      // Night-grade shader injection via onBeforeCompile.
      // Three injections:
      //   1. Land/ocean grade  — after #include <map_fragment> (modifies diffuseColor)
      //   2. City light clamp  — Reinhard, after #include <emissivemap_fragment>
      //   3. Land pseudo-emissive — adds day-texture glow to land after city clamp,
      //      bypassing the ambient-light suppression that makes the grade invisible
      // All strengths start at 0; applyTheme enables them after ocean mask is ready.
      const _maskPlaceholder = new THREE.DataTexture(
        new Uint8Array([0, 0, 0, 255]), 1, 1, THREE.RGBAFormat
      )
      _maskPlaceholder.needsUpdate = true
      earthMaterial.onBeforeCompile = (shader) => {
        // On recompile (e.g. when emissiveMap is first assigned, changing USE_EMISSIVEMAP),
        // carry over the previous shader's uniform values so nothing is lost.
        // First compile: earthShaderUniforms is null, so all fallbacks kick in.
        const _prev = earthShaderUniforms
        const _pv = (key, fallback) => _prev ? (_prev[key]?.value ?? fallback) : fallback

        // Ocean mask: use the already-loaded texture immediately so recompile can't reset it.
        shader.uniforms.uOceanMask      = { value: oceanMaskTexture ?? _maskPlaceholder }
        shader.uniforms.uOceanLift      = { value: _pv('uOceanLift', 0) }
        // Hue ratio of the oceanLift floor color (was hardcoded 0.35/0.50/1.0
        // in rodioOceanToneGrade). Default MUST stay (0.35, 0.50, 1.0) —
        // themes that don't set nightGrade.oceanLiftTint keep the exact
        // pre-parameterization color.
        shader.uniforms.uOceanLiftTint  = { value: _prev?.uOceanLiftTint?.value ?? new THREE.Vector3(0.35, 0.50, 1.0) }
        shader.uniforms.uOceanTeal      = { value: _pv('uOceanTeal', 0) }
        shader.uniforms.uOceanBlendStrength = { value: _pv('uOceanBlendStrength', 0) }
        // Gate for the daytime standalone ocean grade (rodioOceanToneGradeStandalone).
        // Default 0 — themes must opt in via nightGrade.dayOceanGrade so the
        // locked earlyMorning (which shares daybaseMode=0) stays pixel-identical.
        shader.uniforms.uDayOceanGrade      = { value: _pv('uDayOceanGrade', 0) }
        shader.uniforms.uOceanDarken        = { value: _pv('uOceanDarken', 1) }
        shader.uniforms.uOceanContrast      = { value: _pv('uOceanContrast', 1) }
        shader.uniforms.uOceanSaturation    = { value: _pv('uOceanSaturation', 1) }
        shader.uniforms.uOceanBlueBias      = { value: _pv('uOceanBlueBias', 0) }
        shader.uniforms.uOceanRedReduce     = { value: _pv('uOceanRedReduce', 0) }
        shader.uniforms.uOceanGreenReduce   = { value: _pv('uOceanGreenReduce', 0) }
        shader.uniforms.uCoastProtection    = { value: _pv('uCoastProtection', 0.75) }
        shader.uniforms.uLandLift       = { value: _pv('uLandLift',  0.04) }
        shader.uniforms.uLandGamma      = { value: _pv('uLandGamma', 0.85) }
        shader.uniforms.uLandStr        = { value: _pv('uLandStr',   0) }
        shader.uniforms.uLandRedRed     = { value: _pv('uLandRedRed', 0.025) }
        shader.uniforms.uLandGreenB     = { value: _pv('uLandGreenB', 0.045) }
        shader.uniforms.uLandGlowStr    = { value: _pv('uLandGlowStr', 0) }
        shader.uniforms.uCityHighlightClamp = { value: _pv('uCityHighlightClamp', 0.88) }
        shader.uniforms.uCityLumLow     = { value: _pv('uCityLumLow',  0.008) }
        shader.uniforms.uCityLumHigh    = { value: _pv('uCityLumHigh', 0.040) }
        // Debug mode always starts at 0 on recompile (preserving would be confusing).
        shader.uniforms.uLandDebugMode  = { value: 0.0 }
        // R5 deepNight black-ocean raw source uniforms
        shader.uniforms.uOceanRawMix      = { value: _pv('uOceanRawMix', 0) }
        shader.uniforms.uOceanRawExposure = { value: _pv('uOceanRawExposure', 0.025) }
        shader.uniforms.uOceanRawBlueKeep = { value: _pv('uOceanRawBlueKeep', 0.2) }
        // v17 daybase-darkened uniforms
        shader.uniforms.uDaybaseMode     = { value: _pv('uDaybaseMode', 0) }
        shader.uniforms.uNightExposure   = { value: _pv('uNightExposure', 0.30) }
        shader.uniforms.uNightSaturation = { value: _pv('uNightSaturation', 0.62) }
        shader.uniforms.uNightGamma      = { value: _pv('uNightGamma', 0.90) }
        shader.uniforms.uNightBlueBias   = { value: _pv('uNightBlueBias', 0.06) }
        shader.uniforms.uNightGreenBias  = { value: _pv('uNightGreenBias', 0.02) }
        shader.uniforms.uNightRedReduce  = { value: _pv('uNightRedReduce', 0.04) }
        shader.uniforms.uTropicalDarken      = { value: _pv('uTropicalDarken', 0) }
        shader.uniforms.uTropicalGreenReduce = { value: _pv('uTropicalGreenReduce', 0) }
        shader.uniforms.uAridDarken          = { value: _pv('uAridDarken', 0) }
        shader.uniforms.uAridWarmReduce      = { value: _pv('uAridWarmReduce', 0) }
        shader.uniforms.uIceNeutralize       = { value: _pv('uIceNeutralize', 0) }
        console.log('[earth3d] onBeforeCompile — recompile#' + ((_prev ? 're' : '1st')),
          '| oceanMaskTexture:', oceanMaskTexture ? 'LOADED' : 'placeholder',
          '| uOceanMask set to:', oceanMaskTexture ? 'real texture' : '_maskPlaceholder')
        earthShaderUniforms = shader.uniforms

        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <common>',
          `#include <common>
          uniform sampler2D uOceanMask;
          uniform float uOceanLift;
          uniform vec3  uOceanLiftTint;
          uniform float uOceanTeal;
          uniform float uOceanBlendStrength;
          uniform float uDayOceanGrade;
          uniform float uOceanDarken;
          uniform float uOceanContrast;
          uniform float uOceanSaturation;
          uniform float uOceanBlueBias;
          uniform float uOceanRedReduce;
          uniform float uOceanGreenReduce;
          uniform float uCoastProtection;
          uniform float uLandLift;
          uniform float uLandGamma;
          uniform float uLandStr;
          uniform float uLandRedRed;
          uniform float uLandGreenB;
          uniform float uLandGlowStr;
          uniform float uCityHighlightClamp;
          uniform float uCityLumLow;
          uniform float uCityLumHigh;
          uniform float uLandDebugMode;
          uniform float uDaybaseMode;
          uniform float uNightExposure;
          uniform float uNightSaturation;
          uniform float uNightGamma;
          uniform float uNightBlueBias;
          uniform float uNightGreenBias;
          uniform float uNightRedReduce;
          uniform float uTropicalDarken;
          uniform float uTropicalGreenReduce;
          uniform float uAridDarken;
          uniform float uAridWarmReduce;
          uniform float uIceNeutralize;
          uniform float uOceanRawMix;
          uniform float uOceanRawExposure;
          uniform float uOceanRawBlueKeep;

          vec3 rodioAdjustSaturation(vec3 color, float saturation) {
            float luma = dot(color, vec3(0.2126, 0.7152, 0.0722));
            return mix(vec3(luma), color, saturation);
          }

          vec3 rodioAdjustContrast(vec3 color, float contrast) {
            return ((color - 0.5) * contrast) + 0.5;
          }

          float rodioOceanToneWeight(float oceanMaskValue, vec3 rawDay) {
            float coastStart = mix(0.12, 0.38, clamp(uCoastProtection, 0.0, 1.0));
            float coastEnd = mix(0.42, 0.82, clamp(uCoastProtection, 0.0, 1.0));
            float coastGuard = smoothstep(coastStart, coastEnd, oceanMaskValue);
            float openOcean = smoothstep(0.30, 0.94, oceanMaskValue);
            float deepOcean = smoothstep(0.62, 0.98, oceanMaskValue);
            float brightness = dot(rawDay, vec3(0.2126, 0.7152, 0.0722));
            float shallowProtection = mix(
              1.0,
              1.0 - 0.55 * smoothstep(0.15, 0.42, brightness),
              clamp(uCoastProtection, 0.0, 1.0)
            );
            return clamp(mix(openOcean, deepOcean, 0.65) * coastGuard * shallowProtection, 0.0, 1.0);
          }

          vec3 rodioNightBaseFromRawEx(vec3 rawDay, float exposure, float saturation) {
            float _rawLuma = dot(rawDay, vec3(0.2126, 0.7152, 0.0722));
            float _rawChroma = length(rawDay - vec3(_rawLuma));
            float _rawWarmBias = rawDay.r - rawDay.b;
            vec3 desat = rodioAdjustSaturation(rawDay, saturation);
            vec3 exposed = desat * exposure;
            vec3 gammaCol = pow(max(exposed, vec3(0.001)), vec3(uNightGamma));
            float _outLuma = dot(gammaCol, vec3(0.2126, 0.7152, 0.0722));
            float _biasScale = 1.0 - smoothstep(0.042, 0.073, _outLuma) * 0.97;
            float _whiteMask = smoothstep(0.35, 0.82, _rawLuma)
                             * smoothstep(0.18, 0.03, _rawChroma);
            _biasScale *= (1.0 - 0.90 * clamp(_whiteMask, 0.0, 1.0));
            float _warmFactor = clamp(_rawWarmBias * 6.0, 0.0, 1.0);
            float _warmOnlyScale = _biasScale + (1.0 - _biasScale) * _warmFactor;
            float _effectiveRedReduce = uNightRedReduce * (1.0 + _warmFactor * 4.5);
            float _effectiveBlueBias  = uNightBlueBias  * (0.15 + _warmFactor * 0.85);
            gammaCol.r *= (1.0 - _effectiveRedReduce  * _warmOnlyScale);
            gammaCol.g *= (1.0 + uNightGreenBias      * _biasScale);
            gammaCol.b *= (1.0 + _effectiveBlueBias   * _warmOnlyScale);
            if (uIceNeutralize > 0.001 && _whiteMask > 0.01) {
              float _wLuma = dot(gammaCol, vec3(0.2126, 0.7152, 0.0722));
              vec3 _whiteOut = vec3(_wLuma * 0.91, _wLuma * 0.96, _wLuma * 1.04);
              gammaCol = mix(gammaCol, _whiteOut, clamp(_whiteMask * uIceNeutralize, 0.0, 1.0));
            }
            return clamp(gammaCol, vec3(0.002), vec3(0.40));
          }

          vec3 rodioNightBaseFromRaw(vec3 rawDay) {
            return rodioNightBaseFromRawEx(rawDay, uNightExposure, uNightSaturation);
          }

          vec3 rodioOceanToneGrade(vec3 rawDay) {
            vec3 color = rodioNightBaseFromRaw(rawDay);
            color *= uOceanDarken;
            color = rodioAdjustContrast(color, uOceanContrast);
            color = rodioAdjustSaturation(color, uOceanSaturation);
            color.r *= (1.0 - uOceanRedReduce);
            color.g *= (1.0 - uOceanGreenReduce);
            color.b *= (1.0 + uOceanBlueBias);
            // Lift floor hue is parameterized (uOceanLiftTint, default
            // 0.35/0.50/1.0 = the former hardcoded ratio) so deepNight can use
            // a colder blue-black floor without affecting other themes.
            color += uOceanLift * uOceanLiftTint;
            return clamp(color, vec3(0.0), vec3(0.40));
          }

          // Same Ocean Tone Grade knobs (darken/contrast/saturation/blueBias/
          // redReduce/greenReduce/lift) as rodioOceanToneGrade(), but applied
          // directly to the raw day ocean color instead of routing through
          // rodioNightBaseFromRaw() first. rodioNightBaseFromRaw() bakes in the
          // v17 night-exposure crush (uNightExposure≈0.03-0.3, clamped to 0.40
          // max) which only makes sense for the deepNight "daybase-darkened"
          // look — reusing it for daytime themes would clamp the ocean to a
          // near-black band regardless of the actual daylight brightness.
          // This standalone variant lets Ocean Tone Grade tint/tone the ocean
          // on any theme (清晨/正午/etc.) without forcing land through night
          // darkening and without crushing ocean brightness to night levels.
          vec3 rodioOceanToneGradeStandalone(vec3 rawDay) {
            vec3 color = rawDay * uOceanDarken;
            color = rodioAdjustContrast(color, uOceanContrast);
            color = rodioAdjustSaturation(color, uOceanSaturation);
            color.r *= (1.0 - uOceanRedReduce);
            color.g *= (1.0 - uOceanGreenReduce);
            color.b *= (1.0 + uOceanBlueBias);
            color += vec3(uOceanLift * 0.35, uOceanLift * 0.50, uOceanLift);
            return clamp(color, vec3(0.0), vec3(1.0));
          }`
        )

        // — Injection 1: map_fragment post-processing —
        // v17 (uDaybaseMode=1): daybase-darkened path — transforms raw day texture to
        //   a natural night base using exposure/saturation/gamma/bias. mapColor=white
        //   so diffuseColor == dayTexture before this block runs.
        // v16 (uDaybaseMode=0): land-only grade on diffuseColor — ocean coloring is
        //   handled in the emissive path because mapColor×tex ≈ near-zero in deepNight.
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <map_fragment>',
          `#include <map_fragment>
          #ifdef USE_MAP
          {
            vec3 _rawDay = diffuseColor.rgb;
            float _oceanMaskValue = texture2D(uOceanMask, vUv).r;
            if (uDaybaseMode > 0.5) {
              vec3 _nightBase = rodioNightBaseFromRaw(_rawDay);
              float _oceanWeight = rodioOceanToneWeight(_oceanMaskValue, _rawDay);

              // ── Land surface-type suppression (tropical green + arid/highland) ──
              float _landMask = 1.0 - clamp(_oceanWeight * 2.0, 0.0, 1.0);
              if (_landMask > 0.001 && (uTropicalDarken > 0.001 || uAridDarken > 0.001)) {
                float _rawLuma = dot(_rawDay, vec3(0.2126, 0.7152, 0.0722));
                float _greenExcess = _rawDay.g - max(_rawDay.r, _rawDay.b) * 0.80;
                float _chroma = length(_rawDay - vec3(_rawLuma));
                // tropical: green-dominant, medium luma (vegetation, not city)
                float _trop = smoothstep(0.02, 0.12, _greenExcess)
                            * smoothstep(0.10, 0.42, _rawLuma)
                            * _landMask;
                // arid: bright luma, low chroma, warm-biased (R > B) — excludes cold ice/snow
                float _warmBias = _rawDay.r - _rawDay.b;
                float _arid = smoothstep(0.35, 0.70, _rawLuma)
                            * smoothstep(0.14, 0.03, _chroma)
                            * smoothstep(0.02, 0.10, _warmBias)
                            * (1.0 - clamp(_trop * 2.0, 0.0, 1.0))
                            * _landMask;
                _nightBase *= (1.0 - uTropicalDarken * _trop);
                _nightBase.g *= (1.0 - uTropicalGreenReduce * _trop);
                _nightBase *= (1.0 - uAridDarken * _arid);
                _nightBase.r *= (1.0 - uAridWarmReduce * _arid);
                float _magentaRaw = min(_rawDay.r, _rawDay.b) - _rawDay.g;
                float _nightMagenta = min(_nightBase.r, _nightBase.b) - _nightBase.g;
                float _deMagenta = smoothstep(0.010, 0.110, _magentaRaw)
                                 * smoothstep(0.004, 0.028, _nightMagenta)
                                 * smoothstep(0.10, 0.75, _rawLuma)
                                 * (1.0 - smoothstep(0.10, 0.42, _warmBias))
                                 * _landMask;
                if (_deMagenta > 0.001) {
                  float _nightLuma = dot(_nightBase, vec3(0.2126, 0.7152, 0.0722));
                  vec3 _neutralCool = vec3(_nightLuma * 0.93, _nightLuma * 0.98, _nightLuma * 1.02);
                  _nightBase = mix(_nightBase, _neutralCool, clamp(_deMagenta * 0.82, 0.0, 0.82));
                }
                // Ice/snow/cold-rock neutralization: pull purple-blue bias back toward gray
                // Targets: high luma + very low chroma + cold or neutral (R not > B)
                if (uIceNeutralize > 0.001) {
                  float _coolBias = _rawDay.b - _rawDay.r;
                  float _coldNeutral = smoothstep(0.16, 0.025, _chroma)
                                     * smoothstep(0.30, 0.80, _rawLuma)
                                     * max(
                                         1.0 - smoothstep(-0.01, 0.10, _warmBias),
                                         smoothstep(0.01, 0.12, _coolBias) * 0.75
                                       )
                                     * _landMask;
                  float _iceGray = dot(_nightBase, vec3(0.2126, 0.7152, 0.0722));
                  _nightBase = mix(
                    _nightBase,
                    vec3(_iceGray),
                    clamp(_coldNeutral * (0.72 + 0.28 * smoothstep(0.48, 0.78, _rawLuma)) * uIceNeutralize, 0.0, 1.0)
                  );
                  float _hardColdWhite = smoothstep(0.44, 0.84, _rawLuma)
                                       * smoothstep(0.10, 0.018, _chroma)
                                       * max(
                                           1.0 - smoothstep(0.00, 0.12, _warmBias),
                                           smoothstep(0.02, 0.16, _coolBias) * 0.9
                                         )
                                       * _landMask;
                  float _hardIceGray = dot(_nightBase, vec3(0.2126, 0.7152, 0.0722));
                  _nightBase = mix(
                    _nightBase,
                    vec3(_hardIceGray),
                    clamp(_hardColdWhite * 0.92 * uIceNeutralize, 0.0, 0.92)
                  );
                }
                _nightBase = clamp(_nightBase, vec3(0.002), vec3(0.40));
              }
              // ─────────────────────────────────────────────────────────────────

              vec3 _oceanTone = rodioOceanToneGrade(_rawDay);
              // r5.3: shallow-sea blend reduction — rawDay luminance lowers
              // effective blendStrength per-pixel so nightBase (carrying
              // day-texture bathymetry) shows through more in shallow seas,
              // breaking the uniform gray-blue mask. Deep ocean unaffected.
              float _rawLuma = dot(_rawDay, vec3(0.2126, 0.7152, 0.0722));
              float _shallowBlendReduce = 1.0 - _rawLuma * 0.55;
              diffuseColor.rgb = mix(
                _nightBase,
                _oceanTone,
                clamp(_oceanWeight * uOceanBlendStrength * _shallowBlendReduce, 0.0, 1.0)
              );
              // R5 deepNight black-ocean raw source — inject near-black cold-tinted ocean
              // after the ocean blend, bypassing nightGrade's exposure+saturation crush.
              // Derived from rawDay (same source as nightBase) but with independent
              // exposure + blue-keep, so the ocean can reach deep blue-black without
              // needing to fight the global nightExposure/nightSaturation settings.
              vec3 _oceanRaw = rodioNightBaseFromRawEx(_rawDay, uOceanRawExposure, uNightSaturation);
              _oceanRaw = _oceanRaw * uOceanRawBlueKeep;
              diffuseColor.rgb = mix(diffuseColor.rgb, _oceanRaw, _oceanWeight * uOceanRawMix * _shallowBlendReduce);
              if (uLandDebugMode > 3.5 && uLandDebugMode < 4.5) {
                diffuseColor.rgb = _oceanTone * clamp(_oceanWeight * 2.2, 0.0, 1.0);
              }
            } else {
              // v16 land-only grade
              float _landW = 1.0 - smoothstep(0.0, 0.008, _oceanMaskValue);
              if (_landW > 0.001 && uLandStr > 0.001) {
                vec3  _col  = diffuseColor.rgb;
                float _lum  = dot(_col, vec3(0.2126, 0.7152, 0.0722));
                float _shd  = 1.0 - smoothstep(0.03, 0.28, _lum);
                vec3  _lifted = clamp(_col + uLandLift * _shd, 0.0, 1.0);
                vec3  _graded = pow(_lifted, vec3(uLandGamma));
                _graded.r = clamp(_graded.r * (1.0 - uLandRedRed * _shd), 0.0, 1.0);
                _graded.g = clamp(_graded.g * (1.0 + uLandGreenB * _shd), 0.0, 1.0);
                diffuseColor.rgb = mix(_col, _graded, _landW * uLandStr);
              }
              // Daytime standalone Ocean Tone Grade — opt-in via uDayOceanGrade
              // (nightGrade.dayOceanGrade). Applies the same darken/contrast/
              // saturation/bias knobs directly on the raw day ocean color so
              // daytime themes can shift the ocean with time of day. Themes
              // that don't opt in (earlyMorning, all night modes) skip this
              // block entirely and render exactly as before.
              if (uDayOceanGrade > 0.5) {
                float _dayOceanW = rodioOceanToneWeight(_oceanMaskValue, _rawDay);
                if (_dayOceanW > 0.001) {
                  vec3 _dayOceanTone = rodioOceanToneGradeStandalone(_rawDay);
                  diffuseColor.rgb = mix(
                    diffuseColor.rgb,
                    _dayOceanTone,
                    clamp(_dayOceanW * uOceanBlendStrength, 0.0, 1.0)
                  );
                }
              }
            }
          }
          #endif`
        )

        // — Injection 2: city recolor + legacy ocean emissive + land glow —
        //
        // CITY RECOLOR:
        //   Three.js default: totalEmissiveRadiance = material.emissive × nightTex.rgb
        //   Problem: nightTex RGB carries raw Black Marble yellow/white → emissiveColor
        //   cannot control hue.
        //   Fix: extract luma from the combined product, apply smooth mask,
        //   replace entirely with (emissive × mask).  emissive = emissiveColor × intensity.
        //
        // OCEAN EMISSIVE:
        //   diffuseColor in deepNight ≈ mapColor × tex ≈ near-zero everywhere.
        //   Ocean tint via diffuse is invisible.  Inject ocean color directly as emissive.
        //   Target: interpolate between deep-navy (#03121F linear) and blue-teal (#08324A linear).
        //
        // LAND GLOW:
        //   Re-sample raw day texture (before mapColor darkening) for actual continent colors.
        //   Desaturate, gamma-lift, inject as low-level emissive on land core.
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <emissivemap_fragment>',
          `#include <emissivemap_fragment>
          {
            // ── City light recolor ─────────────────────────────────────────────
            // Extract luminance from (emissive × nightTex), build smooth mask,
            // then replace totalEmissiveRadiance with pure emissiveColor × mask.
            float _lMask = 0.0;
            vec3  _cityColor = vec3(0.0);
            #ifdef USE_EMISSIVEMAP
            {
              float _nLuma = dot(totalEmissiveRadiance, vec3(0.2126, 0.7152, 0.0722));
              // Power-curve mask: preserves relative luminance so bright metros (Tokyo, NYC)
              // appear visibly brighter than small towns. smoothstep clips all variation
              // above cityLumHigh to the same value — this avoids that flattening.
              float _normCity = max(0.0, _nLuma - uCityLumLow) / max(0.001, uCityLumHigh - uCityLumLow);
              _lMask = pow(clamp(_normCity, 0.0, 2.0), 0.80);
              #ifdef USE_MAP
              vec3 _cityRawDay = mapTexelToLinear(texture2D(map, vUv)).rgb;
              float _cityRawLuma = dot(_cityRawDay, vec3(0.2126, 0.7152, 0.0722));
              float _cityRawChroma = length(_cityRawDay - vec3(_cityRawLuma));
              float _cityWarmBias = _cityRawDay.r - _cityRawDay.b;
              float _cityCoolBias = _cityRawDay.b - _cityRawDay.r;
              float _cityColdWhite = smoothstep(0.28, 0.82, _cityRawLuma)
                                   * smoothstep(0.18, 0.03, _cityRawChroma)
                                   * max(
                                       1.0 - smoothstep(-0.01, 0.10, _cityWarmBias),
                                       smoothstep(0.01, 0.14, _cityCoolBias) * 0.8
                                     );
              // Black Marble can still report weak night luminance over glacier / snow / white rock.
              // Suppress emissive recolor there so warm city lights do not mix into a pink-purple fringe.
              _lMask *= (1.0 - clamp(_cityColdWhite * 0.96 * uIceNeutralize, 0.0, 0.96));
              float _cityHardVeto = smoothstep(0.42, 0.80, _cityRawLuma)
                                  * smoothstep(0.10, 0.018, _cityRawChroma)
                                  * max(
                                      1.0 - smoothstep(0.00, 0.12, _cityWarmBias),
                                      smoothstep(0.02, 0.16, _cityCoolBias) * 0.9
                                    );
              _lMask *= (1.0 - clamp(_cityHardVeto * 1.35 * uIceNeutralize, 0.0, 1.0));
              #endif
              // Three-stop color gradient keyed to city brightness:
              //   dim (small towns)  → amber/bronze  (emissive with green/blue pulled back)
              //   mid (base)         → warm light yellow  (emissive as-is — dominant color)
              //   bright (megacities)→ warm white         (lift all channels toward white)
              float _cb = clamp(_normCity, 0.0, 2.0);
              vec3 _dimHue    = emissive * vec3(0.70, 0.45, 0.25); // amber: less green/blue
              vec3 _brightHue = vec3(0.92, 0.74, 0.42);            // warm gold endpoint (not white)
              vec3 _cityHue = mix(
                mix(_dimHue, emissive, smoothstep(0.0, 0.9, _cb)),
                _brightHue,
                smoothstep(0.9, 1.9, _cb)
              );
              _cityColor = _cityHue * _lMask;
              float _cl = dot(_cityColor, vec3(0.2126, 0.7152, 0.0722));
              if (_cl > 0.001) {
                float _clC = _cl / (1.0 + _cl / uCityHighlightClamp);
                _cityColor *= _clC / _cl;
              }
            }
            #endif

            // ── Shared geometry (sampled once for all modes) ───────────────────
            float _omv = texture2D(uOceanMask, vUv).r;
            // Raised threshold vs map_fragment: only high-confidence open ocean
            float _owv = smoothstep(0.88, 0.95, _omv);
            float _lwv = 1.0 - smoothstep(0.0, 0.008, _omv);

            // ── Mode dispatch ──────────────────────────────────────────────────
            // Debug 3: raw ocean mask value greyscale (pre-threshold, ×2 amplified)
            // Shows actual PNG coverage — if this is black, the mask file didn't load.
            if (uLandDebugMode > 2.5 && uLandDebugMode < 3.5) {
              totalEmissiveRadiance = vec3(_omv) * 2.0;

            // Debug 4: ocean tone grade only — diffuse path already isolated it,
            // so emissive stays off here.
            } else if (uLandDebugMode > 3.5 && uLandDebugMode < 4.5) {
              totalEmissiveRadiance = vec3(0.0);

            // Debug 5: city mask greyscale
            } else if (uLandDebugMode > 4.5 && uLandDebugMode < 5.5) {
              totalEmissiveRadiance = vec3(_lMask) * 2.0;

            // Debug 6: city color only
            } else if (uLandDebugMode > 5.5 && uLandDebugMode < 6.5) {
              totalEmissiveRadiance = _cityColor;

            // Debug 7: daybase only — zero all emissive (v17 diagnosis)
            } else if (uLandDebugMode > 6.5 && uLandDebugMode < 7.5) {
              totalEmissiveRadiance = vec3(0.0);

            // Debug 2: land shadow-weight map greyscale
            } else if (uLandDebugMode > 1.5 && uLandDebugMode < 2.5) {
              #ifdef USE_MAP
              vec3  _rd2 = mapTexelToLinear(texture2D(map, vUv)).rgb;
              float _rl2 = dot(_rd2, vec3(0.2126, 0.7152, 0.0722));
              float _sw2 = smoothstep(0.008, 0.06, _rl2)
                         * (1.0 - smoothstep(0.55, 0.80, _rl2));
              totalEmissiveRadiance = vec3(_sw2 * _lwv) * 3.0;
              #else
              totalEmissiveRadiance = vec3(0.0);
              #endif

            } else {
              // Mode 0 (normal) or mode 1 (kill city+ocean, keep land glow)
              if (uLandDebugMode < 0.5) {
                // Normal: city lights + legacy v16 ocean emissive
                totalEmissiveRadiance = _cityColor;
                if (uDaybaseMode < 0.5 && _owv > 0.001 && uOceanLift > 0.001) {
                  vec3 _ot = mix(vec3(0.00091,0.0193,0.0432), vec3(0.00243,0.0835,0.151),
                                 clamp(uOceanTeal, 0.0, 1.0));
                  totalEmissiveRadiance += _ot * uOceanLift * _owv;
                }
              } else {
                // Debug 1: kill city+ocean (landOnly/landGlowOnly)
                totalEmissiveRadiance = vec3(0.0);
              }

              // Land glow — active in both mode 0 and mode 1
              #ifdef USE_MAP
              if (uLandGlowStr > 0.001 && _lwv > 0.001) {
                vec3  _rd  = mapTexelToLinear(texture2D(map, vUv)).rgb;
                float _rl  = dot(_rd, vec3(0.2126, 0.7152, 0.0722));
                vec3  _lt  = mix(vec3(_rl), _rd, 0.25);
                _lt = pow(clamp(_lt, 0.001, 1.0), vec3(uLandGamma));
                float _sw  = smoothstep(0.008, 0.06, _rl)
                           * (1.0 - smoothstep(0.55, 0.80, _rl));
                totalEmissiveRadiance += _lt * uLandGlowStr * _lwv * _sw;
              }
              #endif
            }
          }`
        )
      }
      loadNormalMapTexture()
      earthGeometry = new THREE.SphereGeometry(2, 128, 128)
      const earth = new THREE.Mesh(earthGeometry, earthMaterial)
      // Fresnel-based atmosphere shader: opacity = pow(1 - |dot(N,V)|, power) * scale
      // Produces a natural limb glow — transparent at center, bright only at the edge.
      // uSunDir (world-space) makes the glow brighter on the sunlit hemisphere and nearly
      // invisible on the dark side, matching real satellite photography of Earth's limb.
      const _atmVert = `
        uniform float uRadius;
        varying vec3 vNormal;
        varying vec3 vViewDir;
        varying vec3 vWorldNormal;
        void main() {
          // Geometry is a unit sphere; uRadius scales it per-theme so one shell can be
          // a tight skin for some themes and a wide halo shell for others without
          // needing a separate mesh (and separate competing silhouette) per theme.
          vNormal = normalize(normalMatrix * normal);
          vWorldNormal = normalize(mat3(modelMatrix) * normal);
          vec4 mvPos = modelViewMatrix * vec4(position * uRadius, 1.0);
          vViewDir = normalize(-mvPos.xyz);
          gl_Position = projectionMatrix * mvPos;
        }
      `
      const _atmFrag = `
        uniform vec3 uColor;
        uniform vec3 uColorOuter;
        uniform float uOpacity;
        uniform float uPower;
        uniform float uPowerOuter;
        uniform float uStrengthOuter;
        uniform vec3  uSunDir;
        uniform float uSunInfluence;
        varying vec3 vNormal;
        varying vec3 vViewDir;
        varying vec3 vWorldNormal;
        void main() {
          // Single silhouette source: both terms read the same N·V, so the bright core
          // and the soft outer wash stay locked to the same edge instead of drifting
          // apart into separate concentric rings (which is what happens if you stack
          // multiple shells of different radii, each with its own N·V=0 silhouette).
          float fresnel = 1.0 - abs(dot(vNormal, vViewDir));
          float core  = pow(fresnel, uPower) * uOpacity;
          float outer = pow(fresnel, uPowerOuter) * uStrengthOuter * uOpacity;
          float total = core + outer;
          // Sun-side modulation: bright limb on the sunlit hemisphere, near-dark on the
          // shadow side (mimics how Earth's atmosphere looks from orbit).
          float sunDot   = dot(vWorldNormal, uSunDir);
          float sunFactor = clamp(sunDot * 0.55 + 0.55, 0.06, 1.0);
          float modFactor = mix(1.0, sunFactor, uSunInfluence);
          total *= modFactor;
          vec3 col = total > 0.0 ? (uColor * core + uColorOuter * outer) / max(core + outer, 0.001) : uColor;
          gl_FragColor = vec4(col, clamp(total, 0.0, 1.0));
        }
      `
      atmosphereMaterial = new THREE.ShaderMaterial({
        vertexShader: _atmVert,
        fragmentShader: _atmFrag,
        uniforms: {
          uColor:         { value: new THREE.Color('#7ab8e6') },
          uColorOuter:    { value: new THREE.Color('#7ab8e6') },
          uOpacity:       { value: 0.7 },
          uPower:         { value: 4.0 },
          uPowerOuter:    { value: 3.2 },
          uStrengthOuter: { value: 0.0 },
          uRadius:        { value: 2.10 },
          uSunDir:        { value: new THREE.Vector3(1, 0, 0) },
          uSunInfluence:  { value: 0.85 },
        },
        transparent: true,
        depthWrite: false,
        depthTest: false,
        blending: THREE.AdditiveBlending,
        // FrontSide: renders the near hemisphere. Fresnel=1 at limb (N·V=0), Fresnel=0 at face
        // (N·V=1). In the zoomed-in app view the limb is at the visible Earth edge — this is
        // where the glow appears. BackSide rendered the far hemisphere whose limb is off-screen
        // in the normal near-camera view and was therefore invisible.
        side: THREE.FrontSide,
      })
      atmosphere = new THREE.Mesh(
        // Unit sphere — actual radius (and therefore how much room the glow has to
        // bleed outward into space vs inward onto the terrain) is set per-theme via
        // the uRadius uniform above.
        new THREE.SphereGeometry(1, 128, 128),
        atmosphereMaterial
      )
      atmosphere.frustumCulled = false
      atmosphere.renderOrder = 1
      atmosphere2Material = new THREE.ShaderMaterial({
        vertexShader: _atmVert,
        fragmentShader: _atmFrag,
        uniforms: {
          uColor:         { value: new THREE.Color('#C8F5FF') },
          uColorOuter:    { value: new THREE.Color('#C8F5FF') },
          uOpacity:       { value: 0.0 },
          uPower:         { value: 5.0 },
          uPowerOuter:    { value: 3.2 },
          uStrengthOuter: { value: 0.0 },
          uRadius:        { value: 2.03 },
          uSunDir:        { value: new THREE.Vector3(1, 0, 0) },
          uSunInfluence:  { value: 0.85 },
        },
        transparent: true,
        depthWrite: false,
        depthTest: false,
        blending: THREE.AdditiveBlending,
        side: THREE.BackSide,
      })
      atmosphere2 = new THREE.Mesh(
        new THREE.SphereGeometry(1, 128, 128),
        atmosphere2Material
      )
      atmosphere2.visible = false

      const earthGroup = new THREE.Group()
      earthGroup.position.set(0, -1.4, 0)
      // earthGroup.rotation.z = THREE.MathUtils.degToRad(23.4)
      earth.add(atmosphere)
      earth.add(atmosphere2)
      earthGroup.add(earth)

      skyGeometry = new THREE.SphereGeometry(skyRadius, 32, 32)
      skyMaterial = new THREE.ShaderMaterial({
        transparent: false,
        side: THREE.BackSide,
        depthWrite: false,
        depthTest: false,
        uniforms: {
          uColorTop: { value: new THREE.Color('#020308') },
          uColorHorizon: { value: new THREE.Color('#0b1220') },
          uColorBottom: { value: new THREE.Color('#060a14') },
          uOpacity: { value: 0.98 },
          uEnabled: { value: 1 },
        },
        vertexShader: `
          varying vec3 vWorldPosition;
          void main() {
            vWorldPosition = (modelMatrix * vec4(position, 1.0)).xyz;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          precision mediump float;

          uniform vec3 uColorTop;
          uniform vec3 uColorHorizon;
          uniform vec3 uColorBottom;
          uniform float uOpacity;
          uniform float uEnabled;
          varying vec3 vWorldPosition;

          void main() {
            if (uEnabled < 0.5) discard;
            vec3 viewDir = normalize(vWorldPosition - cameraPosition);
            float t = clamp(1.0 - viewDir.y, 0.0, 1.0);
            float horizonMix = smoothstep(0.0, 0.72, t);
            float bottomMix = smoothstep(0.72, 1.0, t);
            vec3 color = mix(uColorTop, uColorHorizon, horizonMix);
            color = mix(color, uColorBottom, bottomMix);
            gl_FragColor = vec4(color, uOpacity * uEnabled);
          }
        `,
      })
      skyMesh = new THREE.Mesh(skyGeometry, skyMaterial)
      skyMesh.renderOrder = -1000
      skyMesh.frustumCulled = false
      scene.add(skyMesh)

      // ─── earlyMorning dedicated sky plane (Plan B) ───────────────────────────
      // Separate orthographic scene so vUv.y gives a reliable top-to-bottom
      // screen-space gradient regardless of camera angle.
      let earlyMorningSkyScene = new THREE.Scene()
      let earlyMorningSkyCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1)
      const _emSkyPlaneMat = new THREE.ShaderMaterial({
        depthWrite: false,
        depthTest: false,
        uniforms: {
          // Low-contrast, low-saturation background only — this plane must read as
          // flat sky, not as a light source. The limb glow is the atmosphere shell's
          // job (see atmosphere.radius/opacity below). horizonColor is intentionally
          // capped well below white/pale-blue — a near-white horizon stop is what
          // produced the horizontal band across the full screen width regardless of
          // earth's curvature, since this plane has no notion of earth's silhouette.
          uTopColor:     { value: new THREE.Color('#061a3a') },
          uMidColor:     { value: new THREE.Color('#0b315f') },
          uLowerColor:   { value: new THREE.Color('#235f93') },
          uHorizonColor: { value: new THREE.Color('#9fd0ed') },
          uOpacity:      { value: 1.0 },
          // Screen-space curved limb glow — an ellipse arc (not a horizontal band) so
          // it follows earth's curvature. The main scene's earth mesh renders after
          // this plane and occludes the arc's lower half, which is what makes the
          // remaining upper arc read as "hugging the visible edge" instead of a
          // band drawn across the whole sky.
          // uRimCenter/uRimRadius start as placeholders — updateEarlyMorningRimProjection()
          // overwrites them every earlyMorning frame from the actual camera/earth
          // projection, before this plane renders, so the arc always matches where
          // earth's visible edge actually lands on screen for the current camera.
          // Rim strength kept at 0 here — the sky plane is background-only now.
          // The actual limb glow moved to a post-scene overlay (earlyMorningRimOverlay*
          // below) so it can render after earth and partially cover its upper edge.
          uRimCenter:        { value: new THREE.Vector2(0.5, -0.31) },
          uRimRadius:        { value: new THREE.Vector2(1.08, 1.04) },
          uRimCoreColor:     { value: new THREE.Color('#f6feff') },
          uRimOuterColor:    { value: new THREE.Color('#86c6ef') },
          uRimCoreWidth:     { value: 0.008 },
          uRimOuterWidth:    { value: 0.050 },
          uRimCoreStrength:  { value: 0.0 },
          uRimOuterStrength: { value: 0.0 },
          uRimOffsetY:       { value: 0.010 },
        },
        vertexShader: `
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = vec4(position.xy, 0.0, 1.0);
          }
        `,
        fragmentShader: `
          precision mediump float;
          uniform vec3 uTopColor;
          uniform vec3 uMidColor;
          uniform vec3 uLowerColor;
          uniform vec3 uHorizonColor;
          uniform float uOpacity;
          uniform vec2 uRimCenter;
          uniform vec2 uRimRadius;
          uniform vec3 uRimCoreColor;
          uniform vec3 uRimOuterColor;
          uniform float uRimCoreWidth;
          uniform float uRimOuterWidth;
          uniform float uRimCoreStrength;
          uniform float uRimOuterStrength;
          uniform float uRimOffsetY;
          varying vec2 vUv;
          void main() {
            float y = vUv.y; // 0 bottom, 1 top
            vec3 c = uHorizonColor;
            c = mix(c, uLowerColor, smoothstep(0.08, 0.32, y));
            c = mix(c, uMidColor,   smoothstep(0.32, 0.68, y));
            c = mix(c, uTopColor,   smoothstep(0.68, 1.00, y));

            float nx = (vUv.x - uRimCenter.x) / uRimRadius.x;
            float inside = 1.0 - nx * nx;

            if (inside > 0.0) {
              float arcY = uRimCenter.y + uRimRadius.y * sqrt(inside) + uRimOffsetY;
              float d = abs(vUv.y - arcY);

              float core = exp(-1.0 * pow(d / uRimCoreWidth, 2.0)) * uRimCoreStrength;
              float outer = exp(-1.0 * pow(d / uRimOuterWidth, 2.0)) * uRimOuterStrength;

              float endFade = 1.0 - smoothstep(0.82, 1.0, abs(nx));

              vec3 rim = uRimCoreColor * core + uRimOuterColor * outer;
              c += rim * endFade;
            }

            c = clamp(c, 0.0, 1.0);
            gl_FragColor = vec4(c, uOpacity);
          }
        `,
      })
      earlyMorningSkyScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), _emSkyPlaneMat))
      // ─────────────────────────────────────────────────────────────────────────

      // ─── earlyMorning post-scene curved atmosphere overlay ───────────────────
      // Two SEPARATE materials/meshes, both driven by the same projected rim arc
      // (uRimCenter/uRimRadius, kept in sync in updateEarlyMorningRimProjection):
      //
      //   1. _emRimOverlayMat  (Outer Rim Glow) — sky side only (signedD > 0),
      //      AdditiveBlending. Single power-decay envelope: max(core_part,
      //      tail_part) so core and tail read as one continuous curve, not two
      //      stacked glows. See rimU.* in index.html Theme Tuner for live params.
      //
      //   2. _emInnerVeilMat   (Inner Horizon Veil) — earth-surface side only
      //      (signedD < 0), NormalBlending (alpha/"soft mix", not additive) so
      //      it reads as haze softly lightening the surface near the horizon
      //      rather than a bright line stacked on top of it.
      //
      // Both masks are antialiased independently via fwidth() at their own
      // signedD=0 boundary — outerMask and innerMask do not share a blend zone,
      // so tuning one never leaks into the other.
      //
      // 清晨主题基础值 - 已定版 2026-07-03（3D Fresnel atmosphere 关闭，
      // Rim Overlay + Inner Horizon Veil 接管地平线辉光）：
      //   Sky Background : uTopColor #061a3a / uMidColor #0b315f /
      //                     uLowerColor #235f93 / uHorizonColor #9fd0ed
      //   Rim Overlay    : haloWidth 0.30 / coreFraction 0.43 / corePower 9.4 /
      //                     coreStrength 0.82 / tailPower 1.5 / haloStrength 0.42
      //   Inner Veil     : innerVeilColor #d9f0ff / innerVeilWidth 0.16 /
      //                     innerVeilStrength 0.36 / innerVeilFalloff 1.8
      //   Atmosphere(3D) : opacity 0.0（关闭，见 THEME_VISUAL_CONFIG.earlyMorning）
      // ─────────────────────────────────────────────────────────────────────────
      let earlyMorningRimOverlayScene = new THREE.Scene()
      let earlyMorningRimOverlayCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1)
      const _emRimOverlayMat = new THREE.ShaderMaterial({
        transparent: true,
        depthTest: false,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        uniforms: {
          uRimCenter:           { value: new THREE.Vector2(0.5, 0.0) },
          uRimRadius:           { value: new THREE.Vector2(1.0, 1.0) },
          uRimOffsetY:          { value: 0.004 },
          uSkyHaloColor:       { value: new THREE.Color('#9dd8ff') },
          uSkyHaloColorNear:   { value: new THREE.Color().setRGB(0.95, 0.98, 1.0) },
          uSkyHaloColorFar:    { value: new THREE.Color().setRGB(0.35, 0.55, 0.75) },
          uSkyHaloWidth:       { value: 0.30 },
          uCoreFraction:       { value: 0.43 },
          uCorePower:          { value: 9.4 },
          uCoreStrength:       { value: 0.82 },
          uTailPower:          { value: 1.5 },
          uHaloStrength:       { value: 0.42 },
          uSoftComposite:      { value: 0.0 },
          uOpacity:            { value: 1.0 },
          // ─── directional sun lobe ────────────────────────────────────────
          uSunLobeEnabled:     { value: 0.0 },
          uSunLobeX:           { value: 0.86 },
          uSunLobeY:           { value: 0.35 },
          uSunLobeCoreColor:   { value: new THREE.Color('#FFF8E8') },
          uSunLobeMainColor:   { value: new THREE.Color('#F2B36A') },
          uSunLobeOuterColor:  { value: new THREE.Color('#496F86') },
          uSunLobeStrength:    { value: 0.72 },
          uSunLobeWidth:       { value: 0.18 },
          uSunLobeFalloff:     { value: 2.8 },
          uSunLobeRimBoost:    { value: 0.42 },
          uSunLobeHStretch:    { value: 2.8 },
          uSunLobeVCompress:   { value: 0.50 },
          // ─── arc band ────────────────────────────────────────────────────
          uArcBandEnabled:     { value: 0.0 },
          uArcBandColorNear:   { value: new THREE.Color('#F7E7C6') },
          uArcBandColorMid:    { value: new THREE.Color('#AFCFE0') },
          uArcBandColorFar:    { value: new THREE.Color('#4E6F86') },
          uArcBandStrength:    { value: 0.38 },
          uArcBandWidth:       { value: 0.055 },
          uArcBandSpread:      { value: 0.58 },
          uArcBandDirX:        { value: 0.88 },
          uArcBandDirFalloff:  { value: 1.8 },
        },
        vertexShader: `
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = vec4(position.xy, 0.0, 1.0);
          }
        `,
        fragmentShader: `
          precision mediump float;
          uniform vec2 uRimCenter;
          uniform vec2 uRimRadius;
          uniform float uRimOffsetY;
          uniform vec3  uSkyHaloColor;
          uniform vec3  uSkyHaloColorNear;
          uniform vec3  uSkyHaloColorFar;
          uniform float uSkyHaloWidth;
          uniform float uCoreFraction;
          uniform float uCorePower;
          uniform float uCoreStrength;
          uniform float uTailPower;
          uniform float uHaloStrength;
          uniform float uSoftComposite;
          uniform float uOpacity;
          // ─── directional sun lobe ────────────────────────────────────────
          uniform float uSunLobeEnabled;
          uniform float uSunLobeX;
          uniform float uSunLobeY;
          uniform vec3  uSunLobeCoreColor;
          uniform vec3  uSunLobeMainColor;
          uniform vec3  uSunLobeOuterColor;
          uniform float uSunLobeStrength;
          uniform float uSunLobeWidth;
          uniform float uSunLobeFalloff;
          uniform float uSunLobeRimBoost;
          uniform float uSunLobeHStretch;
          uniform float uSunLobeVCompress;
          // ─── arc band ────────────────────────────────────────────────────
          uniform float uArcBandEnabled;
          uniform vec3  uArcBandColorNear;
          uniform vec3  uArcBandColorMid;
          uniform vec3  uArcBandColorFar;
          uniform float uArcBandStrength;
          uniform float uArcBandWidth;
          uniform float uArcBandSpread;
          uniform float uArcBandDirX;
          uniform float uArcBandDirFalloff;
          varying vec2 vUv;
          void main() {
            float nx = (vUv.x - uRimCenter.x) / uRimRadius.x;
            float inside = 1.0 - nx * nx;

            vec3 color = vec3(0.0);
            float alpha = 0.0;

            float insideAA = fwidth(inside) + 1e-5;
            float insideEdge = smoothstep(-insideAA, insideAA, inside);

            if (insideEdge > 0.0) {
              float arcY = uRimCenter.y + uRimRadius.y * sqrt(max(inside, 0.0)) + uRimOffsetY;
              float signedD = vUv.y - arcY;

              float t = signedD / uSkyHaloWidth;

              float core_part = pow(clamp(1.0 - t / uCoreFraction, 0.0, 1.0), uCorePower);
              float tail_part = pow(clamp(1.0 - t,                  0.0, 1.0), uTailPower);
              float ci = core_part * uCoreStrength;
              float ti = tail_part * uHaloStrength;
              float skyIntensity;
              if (uSoftComposite > 0.5) {
                skyIntensity = 1.0 - (1.0 - ci) * (1.0 - ti);
              } else {
                skyIntensity = max(ci, ti);
              }

              float tC = clamp(t, 0.0, 1.0);
              vec3 skyColor = tC < 0.5
                ? mix(uSkyHaloColorNear, uSkyHaloColor, tC / 0.5)
                : mix(uSkyHaloColor, uSkyHaloColorFar, (tC - 0.5) / 0.5);

              float aa = fwidth(t) + 1e-5;
              float outerMask = smoothstep(-aa, aa, t);

              float intensity = skyIntensity * outerMask;

              // ─── directional sun lobe (arc-following elliptical glow) ───────
              if (uSunLobeEnabled > 0.5 && t > 0.0) {
                float sunArcY = uRimCenter.y + uRimRadius.y * sqrt(max(1.0 - pow((uSunLobeX - uRimCenter.x) / uRimRadius.x, 2.0), 0.0)) + uRimOffsetY;

                // Arc-following: the glow center at any x is the arc itself (arcY),
                // so the glow hugs the limb curve instead of sitting at a fixed y.
                float dx = (vUv.x - uSunLobeX) / (uSunLobeWidth * uSunLobeHStretch);
                float dy = (vUv.y - arcY) / (uSunLobeWidth * uSunLobeVCompress);
                float dist = sqrt(dx * dx + dy * dy);

                // Directional fade: mirror-aware (right-side vs left-side sun)
                float direction;
                if (uSunLobeX >= 0.5) {
                  direction = smoothstep(-0.55, 0.15, dx);
                } else {
                  direction = 1.0 - smoothstep(-0.15, 0.55, dx);
                }

                float lobe = pow(clamp(1.0 - dist, 0.0, 1.0), uSunLobeFalloff);
                lobe *= uSunLobeStrength * direction;

                vec3 lobeColor = dist < 0.08
                  ? uSunLobeCoreColor
                  : dist < 0.35
                    ? mix(uSunLobeCoreColor, uSunLobeMainColor, (dist - 0.08) / 0.27)
                    : mix(uSunLobeMainColor, uSunLobeOuterColor, (dist - 0.35) / 0.65);

                float rimLobe = lobe * uSunLobeRimBoost;
                intensity = max(intensity, lobe);
                skyColor = mix(skyColor, lobeColor, lobe / max(intensity, 1e-6));
                skyColor += lobeColor * rimLobe * outerMask;
              }

              // ─── arc band ────────────────────────────────────────────────
              if (uArcBandEnabled > 0.5 && t > 0.0) {
                // Tight band right above the limb, complementing sunLobe.
                float bandT = abs(t) / uArcBandWidth;
                float bandIntensity = exp(-bandT * bandT * 4.0);

                // Horizontal spread: centered at dirX, extending left/right
                float hDist = (vUv.x - uArcBandDirX) / uArcBandSpread;
                float hFade = exp(-hDist * hDist * uArcBandDirFalloff);

                // Bias mirror-aware: right-side or left-side sun
                float dirBias;
                if (uArcBandDirX >= 0.5) {
                  dirBias = smoothstep(-0.35, 0.25, hDist * uArcBandSpread * 2.0);
                } else {
                  dirBias = 1.0 - smoothstep(-0.25, 0.35, hDist * uArcBandSpread * 2.0);
                }

                float ab = bandIntensity * hFade * dirBias * uArcBandStrength;

                // Color: warm near limb, cooling upward
                float abMix = clamp(abs(t) / 0.12, 0.0, 1.0);
                vec3 abColor = abMix < 0.5
                  ? mix(uArcBandColorNear, uArcBandColorMid, abMix / 0.5)
                  : mix(uArcBandColorMid, uArcBandColorFar, (abMix - 0.5) / 0.5);

                intensity = max(intensity, ab);
                skyColor = mix(skyColor, abColor, ab / max(intensity, 1e-6));
              }

              float endAA = fwidth(nx) + 1e-5;
              float endFade = 1.0 - smoothstep(0.92 - endAA, 0.92 + endAA, abs(nx));

              color = skyColor * intensity * insideEdge * endFade * uOpacity;
              alpha = 1.0;
            }

            gl_FragColor = vec4(color, alpha);
          }
        `,
      })
      const earlyMorningRimOverlayMesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), _emRimOverlayMat)
      earlyMorningRimOverlayScene.add(earlyMorningRimOverlayMesh)
      // ─────────────────────────────────────────────────────────────────────────

      // ─── earlyMorning Inner Horizon Veil ──────────────────────────────────────
      // Separate material/mesh from the outer glow above so it can use standard
      // alpha ("soft mix") compositing instead of additive — additive stacking
      // on top of the earth's own daylight texture reads as a harsh white spike
      // near the horizon; alpha blending instead interpolates the surface color
      // toward a soft blue-white haze, closer to how a thin atmosphere actually
      // looks looking sideways through it near sunrise.
      //   innerMask = rimMask * earthSurfaceArea (signedD < 0, antialiased —
      //   independent of the outer material's own sky-side transition width)
      //   falloff   = pow(1 - clamp(-signedD / innerVeilWidth, 0, 1), innerVeilFalloff)
      //   strongest at the horizon (signedD = 0), fading into the visible disk.
      // ─────────────────────────────────────────────────────────────────────────
      const _emInnerVeilMat = new THREE.ShaderMaterial({
        transparent: true,
        depthTest: false,
        depthWrite: false,
        blending: THREE.NormalBlending,
        uniforms: {
          uRimCenter:          { value: new THREE.Vector2(0.5, 0.0) },
          uRimRadius:          { value: new THREE.Vector2(1.0, 1.0) },
          uRimOffsetY:         { value: 0.004 },
          uInnerVeilColor:     { value: new THREE.Color('#d9f0ff') },
          uInnerVeilWidth:     { value: 0.16 },
          uInnerVeilStrength:  { value: 0.36 },
          uInnerVeilFalloff:   { value: 1.8 },
          uOpacity:            { value: 1.0 },
          // ─── sun lobe surface warmth ─────────────────────────────────────
          uSurfWarmthEnabled:  { value: 0.0 },
          uSurfWarmthX:        { value: 0.90 },
          uSurfWarmthY:        { value: 0.31 },
          uSurfWarmthColor:    { value: new THREE.Color('#F1B46A') },
          uSurfWarmthStrength: { value: 0.08 },
          uSurfWarmthWidth:    { value: 0.22 },
          uSurfWarmthFalloff:  { value: 2.4 },
          uSurfWarmthVCompress:{ value: 0.50 },
        },
        vertexShader: `
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = vec4(position.xy, 0.0, 1.0);
          }
        `,
        fragmentShader: `
          precision mediump float;
          uniform vec2 uRimCenter;
          uniform vec2 uRimRadius;
          uniform float uRimOffsetY;
          uniform vec3  uInnerVeilColor;
          uniform float uInnerVeilWidth;
          uniform float uInnerVeilStrength;
          uniform float uInnerVeilFalloff;
          uniform float uOpacity;
          // ─── sun lobe surface warmth ─────────────────────────────────────
          uniform float uSurfWarmthEnabled;
          uniform float uSurfWarmthX;
          uniform float uSurfWarmthY;
          uniform vec3  uSurfWarmthColor;
          uniform float uSurfWarmthStrength;
          uniform float uSurfWarmthWidth;
          uniform float uSurfWarmthFalloff;
          uniform float uSurfWarmthVCompress;
          varying vec2 vUv;
          void main() {
            float nx = (vUv.x - uRimCenter.x) / uRimRadius.x;
            float inside = 1.0 - nx * nx;

            vec3 color = vec3(0.0);
            float alpha = 0.0;

            float insideAA = fwidth(inside) + 1e-5;
            float insideEdge = smoothstep(-insideAA, insideAA, inside);

            if (insideEdge > 0.0) {
              float arcY = uRimCenter.y + uRimRadius.y * sqrt(max(inside, 0.0)) + uRimOffsetY;
              float signedD = vUv.y - arcY;

              float sideAA = fwidth(signedD) + 1e-5;
              // Extend slightly above the limb (overlap with outer rim) so
              // inner veil and outer glow blend instead of leaving a seam.
              float innerMask = 1.0 - smoothstep(-sideAA, sideAA + 0.004, signedD);

              float innerT = clamp(-signedD / uInnerVeilWidth, 0.0, 1.0);
              float falloff = pow(1.0 - innerT, uInnerVeilFalloff);

              float endAA = fwidth(nx) + 1e-5;
              float endFade = 1.0 - smoothstep(0.92 - endAA, 0.92 + endAA, abs(nx));

              float veilAlpha = falloff * innerMask * insideEdge * endFade * uInnerVeilStrength * uOpacity;

              // ─── sun lobe surface warmth ─────────────────────────────────
              vec3 veilColor = uInnerVeilColor;
              if (uSurfWarmthEnabled > 0.5) {
                float surfArcY = uRimCenter.y + uRimRadius.y * sqrt(max(1.0 - pow((uSurfWarmthX - uRimCenter.x) / uRimRadius.x, 2.0), 0.0)) + uRimOffsetY;
                float sdx = (vUv.x - uSurfWarmthX) / (uSurfWarmthWidth * 2.6);
                float sdy = signedD / (uSurfWarmthWidth * uSurfWarmthVCompress * 0.65);
                float sdist = sqrt(sdx * sdx + sdy * sdy);
                float warmthFalloff = max(uSurfWarmthFalloff, 0.5);
                float warmth = pow(clamp(1.0 - sdist, 0.0, 1.0), warmthFalloff) * uSurfWarmthStrength;
                // Mirror-aware: right-side vs left-side sun
                if (uSurfWarmthX >= 0.5) {
                  warmth *= smoothstep(-0.40, 0.10, sdx);
                } else {
                  warmth *= 1.0 - smoothstep(-0.10, 0.40, sdx);
                }
                veilColor = mix(veilColor, uSurfWarmthColor, clamp(warmth, 0.0, 1.0));
              }

              color = veilColor;
              alpha = clamp(veilAlpha, 0.0, 1.0);
            }

            gl_FragColor = vec4(color, alpha);
          }
        `,
      })
      const earlyMorningInnerVeilMesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), _emInnerVeilMat)
      // Render before the outer glow mesh so the outer additive pass composites
      // on top of the alpha-blended veil rather than the other way around.
      earlyMorningInnerVeilMesh.renderOrder = -1
      earlyMorningRimOverlayScene.add(earlyMorningInnerVeilMesh)
      // ─────────────────────────────────────────────────────────────────────────

      // Applies a theme's `rimGlow` config to the Outer Rim Glow + Inner Horizon
      // Veil materials. Defaults reproduce earlyMorning's baked-in look exactly,
      // so themes that don't define rimGlow (i.e. every theme except earlyMorning
      // and deepNight) are unaffected — same pattern as applyCloudThemeConfig.
      function applyRimGlowThemeConfig(rimGlowCfg, themeName) {
        if (!_emRimOverlayMat?.uniforms || !_emInnerVeilMat?.uniforms) return
        const outer = rimGlowCfg?.outer
        const inner = rimGlowCfg?.inner
        const sunLobe = rimGlowCfg?.sunLobe
        // 七曜 tint: only deepNight gets the per-weekday hue offset (step 1 of
        // the static effect). Other themes keep their authored colors untouched.
        const _tintWeekday = (themeName === 'deepNight')
          ? SHICHIYOU_TINT[new Date().getDay()]
          : null
        const _tintColor = (hex) => _tintWeekday ? applyShichiyouTint(hex, _tintWeekday.color, getShichiyouCeremonyBlendFactor()) : hex
        const ro = _emRimOverlayMat.uniforms
        ro.uSkyHaloColor.value.set(_tintColor(outer?.color ?? '#9dd8ff'))
        ro.uSkyHaloColorNear.value.set(_tintColor(outer?.colorNear ?? '#f2faff'))
        ro.uSkyHaloColorFar.value.set(_tintColor(outer?.colorFar ?? '#598cbf'))
        ro.uSkyHaloWidth.value    = outer?.width        ?? 0.30
        ro.uCoreFraction.value    = outer?.coreFraction  ?? 0.43
        ro.uCorePower.value       = outer?.corePower     ?? 9.4
        ro.uCoreStrength.value    = outer?.coreStrength  ?? 0.82
        ro.uTailPower.value       = outer?.tailPower     ?? 1.5
        ro.uHaloStrength.value    = outer?.haloStrength  ?? 0.42
        ro.uSoftComposite.value   = outer?.softComposite ? 1.0 : 0.0
        ro.uRimOffsetY.value        = outer?.rimOffsetY   ?? 0.004
        const rv = _emInnerVeilMat.uniforms
        rv.uInnerVeilColor.value.set(_tintColor(inner?.color ?? '#d9f0ff'))
        rv.uInnerVeilWidth.value    = inner?.width    ?? 0.16
        rv.uInnerVeilStrength.value = inner?.strength ?? 0.36
        rv.uInnerVeilFalloff.value  = inner?.falloff  ?? 1.8
        // ─── directional sun lobe ──────────────────────────────────────────
        if (sunLobe) {
          ro.uSunLobeEnabled.value     = sunLobe.enabled ? 1.0 : 0.0
          ro.uSunLobeX.value           = sunLobe.x           ?? 0.86
          ro.uSunLobeY.value           = sunLobe.y           ?? 0.35
          ro.uSunLobeCoreColor.value.set(sunLobe.coreColor   ?? '#FFF8E8')
          ro.uSunLobeMainColor.value.set(sunLobe.mainColor   ?? '#F2B36A')
          ro.uSunLobeOuterColor.value.set(sunLobe.outerColor ?? '#496F86')
          ro.uSunLobeStrength.value    = sunLobe.strength    ?? 0.72
          ro.uSunLobeWidth.value       = sunLobe.width       ?? 0.18
          ro.uSunLobeFalloff.value     = sunLobe.falloff     ?? 2.8
          ro.uSunLobeRimBoost.value    = sunLobe.rimBoost    ?? 0.42
          ro.uSunLobeHStretch.value    = sunLobe.hStretch    ?? 2.8
          ro.uSunLobeVCompress.value   = sunLobe.vCompress   ?? 0.50
          // arc band
          const ab = sunLobe.arcBand
          if (ab) {
            ro.uArcBandEnabled.value     = ab.enabled ? 1.0 : 0.0
            ro.uArcBandColorNear.value.set(ab.colorNear  ?? '#F7E7C6')
            ro.uArcBandColorMid.value.set( ab.colorMid   ?? '#AFCFE0')
            ro.uArcBandColorFar.value.set( ab.colorFar   ?? '#4E6F86')
            ro.uArcBandStrength.value    = ab.strength   ?? 0.38
            ro.uArcBandWidth.value       = ab.width      ?? 0.055
            ro.uArcBandSpread.value      = ab.spread     ?? 0.58
            ro.uArcBandDirX.value        = ab.dirX       ?? 0.88
            ro.uArcBandDirFalloff.value  = ab.dirFalloff ?? 1.8
          } else {
            ro.uArcBandEnabled.value     = 0.0
          }
          // surface warmth via inner veil
          const sw = sunLobe.surfaceWarmth
          if (sw) {
            rv.uSurfWarmthEnabled.value  = sw.enabled ? 1.0 : 0.0
            rv.uSurfWarmthX.value        = sw.x        ?? sunLobe.x ?? 0.90
            rv.uSurfWarmthY.value        = sw.y        ?? sunLobe.y ?? 0.31
            rv.uSurfWarmthColor.value.set(sw.color     ?? '#F1B46A')
            rv.uSurfWarmthStrength.value = sw.strength ?? 0.08
            rv.uSurfWarmthWidth.value    = sw.width    ?? 0.22
            rv.uSurfWarmthFalloff.value  = sw.falloff  ?? 2.4
            rv.uSurfWarmthVCompress.value= sw.vCompress ?? 0.50
          } else {
            rv.uSurfWarmthEnabled.value  = 0.0
          }
        } else {
          ro.uSunLobeEnabled.value     = 0.0
          ro.uArcBandEnabled.value     = 0.0
          rv.uSurfWarmthEnabled.value  = 0.0
        }
      }

      // Projects earth's actual on-screen position/size into the rim overlay's
      // (and sky plane's, kept in sync though its rim strength is 0) uniforms
      // every earlyMorning frame, so the curved rim arc tracks wherever earth's
      // visible edge really is for the current camera instead of a hand-guessed
      // fixed ellipse (which drifts out of alignment the moment camera
      // distance/FOV/angle changes).
      const _emRimEarthCenter = new THREE.Vector3()
      const _emRimCameraPos = new THREE.Vector3()
      const _emRimViewDir = new THREE.Vector3()
      const _emRimCameraRight = new THREE.Vector3()
      const _emRimCameraUp = new THREE.Vector3()
      const _emRimScreenRight = new THREE.Vector3()
      const _emRimScreenUp = new THREE.Vector3()
      const _emRimCircleCenter = new THREE.Vector3()
      const _emRimSamplePoint = new THREE.Vector3()
      const _emRimSampleNdc = new THREE.Vector3()
      function updateEarlyMorningRimProjection() {
        if (!earth || !camera || !_emSkyPlaneMat || !_emRimOverlayMat || !_emInnerVeilMat) return

        earth.getWorldPosition(_emRimEarthCenter)
        camera.getWorldPosition(_emRimCameraPos)
        _emRimViewDir.subVectors(_emRimEarthCenter, _emRimCameraPos)

        const earthRadius = 2.0
        const cameraDistance = _emRimViewDir.length()
        if (!Number.isFinite(cameraDistance) || cameraDistance <= earthRadius + 1e-5) return

        _emRimViewDir.divideScalar(cameraDistance)
        _emRimCameraRight.setFromMatrixColumn(camera.matrixWorld, 0).normalize()
        _emRimCameraUp.setFromMatrixColumn(camera.matrixWorld, 1).normalize()

        // Project the true tangent silhouette circle, not the sphere center.
        // Using the sphere center works only for mild views; steeper presets drift
        // because the visible limb is perspective-shifted relative to the sphere's
        // projected center. Here we build the actual tangent circle in 3D camera
        // space and project that circle's center/right/up extremities to screen.
        const circleCenterDistance = cameraDistance - (earthRadius * earthRadius) / cameraDistance
        const circleRadius = earthRadius * Math.sqrt(cameraDistance * cameraDistance - earthRadius * earthRadius) / cameraDistance

        _emRimCircleCenter.copy(_emRimCameraPos).addScaledVector(_emRimViewDir, circleCenterDistance)

        _emRimScreenRight.copy(_emRimCameraRight).addScaledVector(_emRimViewDir, -_emRimCameraRight.dot(_emRimViewDir))
        if (_emRimScreenRight.lengthSq() < 1e-6) {
          _emRimScreenRight.copy(_emRimCameraUp).cross(_emRimViewDir)
        }
        _emRimScreenRight.normalize()

        _emRimScreenUp.copy(_emRimCameraUp).addScaledVector(_emRimViewDir, -_emRimCameraUp.dot(_emRimViewDir))
        if (_emRimScreenUp.lengthSq() < 1e-6) {
          _emRimScreenUp.copy(_emRimViewDir).cross(_emRimScreenRight)
        }
        _emRimScreenUp.normalize()

        let minU = Infinity
        let maxU = -Infinity
        let minV = Infinity
        let maxV = -Infinity
        const sampleCount = 96

        for (let i = 0; i < sampleCount; i++) {
          const theta = (i / sampleCount) * Math.PI * 2
          _emRimSamplePoint.copy(_emRimCircleCenter)
            .addScaledVector(_emRimScreenRight, Math.cos(theta) * circleRadius)
            .addScaledVector(_emRimScreenUp, Math.sin(theta) * circleRadius)

          _emRimSampleNdc.copy(_emRimSamplePoint).project(camera)
          const u = _emRimSampleNdc.x * 0.5 + 0.5
          const v = _emRimSampleNdc.y * 0.5 + 0.5
          if (!Number.isFinite(u) || !Number.isFinite(v)) continue
          if (u < minU) minU = u
          if (u > maxU) maxU = u
          if (v < minV) minV = v
          if (v > maxV) maxV = v
        }

        if (!Number.isFinite(minU) || !Number.isFinite(maxU) ||
            !Number.isFinite(minV) || !Number.isFinite(maxV)) return

        const centerUv = { x: (minU + maxU) * 0.5, y: (minV + maxV) * 0.5 }
        const rimRx = (maxU - minU) * 0.5
        const rimRy = (maxV - minV) * 0.5

        if (!Number.isFinite(centerUv.x) || !Number.isFinite(centerUv.y) ||
            !Number.isFinite(rimRx) || !Number.isFinite(rimRy)) return

        _emSkyPlaneMat.uniforms.uRimCenter.value.set(centerUv.x, centerUv.y)
        _emSkyPlaneMat.uniforms.uRimRadius.value.set(rimRx, rimRy)
        _emRimOverlayMat.uniforms.uRimCenter.value.set(centerUv.x, centerUv.y)
        _emRimOverlayMat.uniforms.uRimRadius.value.set(rimRx, rimRy)
        _emInnerVeilMat.uniforms.uRimCenter.value.set(centerUv.x, centerUv.y)
        _emInnerVeilMat.uniforms.uRimRadius.value.set(rimRx, rimRy)
      }

      const VISUAL_TARGET_NDC = new THREE.Vector2(0.25, -0.24)
      const visualRaycaster = new THREE.Raycaster()
      const visualTargetDir = new THREE.Vector3(0, 0, 1)
      const auditCenterDir = new THREE.Vector3(0, 0, 1)
      let useAuditCenterTarget = false

      function updateVisualTargetDir() {
        const savedQuaternion = earth.quaternion.clone()

        // 用未旋转的 earth 计算“屏幕视觉锚点”对应的球面方向
        earth.quaternion.identity()
        earth.updateMatrixWorld(true)
        earthGroup.updateMatrixWorld(true)
        scene.updateMatrixWorld(true)
        camera.updateMatrixWorld(true)

        const earthCenterWorld = new THREE.Vector3()
        earth.getWorldPosition(earthCenterWorld)

        const sphere = new THREE.Sphere(earthCenterWorld, 2)
        visualRaycaster.setFromCamera(VISUAL_TARGET_NDC, camera)

        const hit = new THREE.Vector3()
        const intersection = visualRaycaster.ray.intersectSphere(sphere, hit)

        if (!intersection) {
          visualTargetDir.set(0, 0, 1)
        } else {
          const localHit = earth.worldToLocal(hit.clone())
          visualTargetDir.copy(localHit.normalize())
        }

        earth.quaternion.copy(savedQuaternion)
        earth.updateMatrixWorld(true)
      }

      const debugCityMarkers = DEBUG_MARKERS_ENABLED
        ? DEBUG_CITIES.map((city) => {
            const marker = new THREE.Mesh(
              new THREE.SphereGeometry(0.045, 16, 16),
              new THREE.MeshBasicMaterial({
                color: city.color,
                depthTest: false,
                depthWrite: false
              })
            )
            marker.name = city.name
            marker.renderOrder = 999
            marker.position.copy(lonLatToVector3(city.lon, city.lat, 2.08))
            earth.add(marker)
            return { city, marker }
          })
        : []

      scene.add(earthGroup)

      earth.rotation.order = 'YXZ'
      atmosphere.rotation.order = 'YXZ'

      // ─── RDL Regional Tile Overlays ────────────────────────────────────────
      // High-res GEBCO regional tiles (~0.1–0.4 km/px) fade in when camera
      // zooms close to key island groups. Fragment shader discards pixels
      // outside each region's sphere-UV window so only the patch shows.
      //
      // Sphere UV mapping (accounts for TEXTURE_LON_OFFSET=90):
      //   u = ((lon + 90 + 720) % 360) / 360
      //   v = (90 - lat) / 180   (0 = north pole, 1 = south pole)
      const _RDL_HIRES_VARIANTS = ['16k', '12k', '8k']
      const _RDL_REGIONS = [
        // ── Original 8 ───────────────────────────────────────────────────────
        { id: 'maldives',            centerLon:  73.0, centerLat:   3.5, sphereUV: { uMin: 0.44861, uMax: 0.45694, vMin: 0.45278, vMax: 0.50833 } },
        { id: 'ryukyu',              centerLon: 127.5, centerLat:  26.8, sphereUV: { uMin: 0.59028, uMax: 0.61806, vMin: 0.33333, vMax: 0.36944 } },
        { id: 'philippines_central', centerLon: 122.0, centerLat:  12.0, sphereUV: { uMin: 0.57500, uMax: 0.60278, vMin: 0.40000, vMax: 0.46667 } },
        { id: 'south_china_sea',     centerLon: 114.0, centerLat:  15.0, sphereUV: { uMin: 0.55000, uMax: 0.58333, vMin: 0.37778, vMax: 0.45556 } },
        { id: 'great_barrier_reef',  centerLon: 148.0, centerLat: -17.5, sphereUV: { uMin: 0.64583, uMax: 0.67639, vMin: 0.55556, vMax: 0.63889 } },
        { id: 'caribbean_bahamas',   centerLon: -77.5, centerLat:  22.2, sphereUV: { uMin: 0.01389, uMax: 0.05556, vMin: 0.34722, vMax: 0.40556 } },
        { id: 'hawaii',              centerLon:-157.8, centerLat:  20.5, sphereUV: { uMin: 0.80139, uMax: 0.82222, vMin: 0.37222, vMax: 0.40000 } },
        { id: 'indonesia_east',      centerLon: 127.5, centerLat:  -4.5, sphereUV: { uMin: 0.58333, uMax: 0.62500, vMin: 0.49444, vMax: 0.55556 } },
        // ── East Asia ─────────────────────────────────────────────────────────
        { id: 'japan',               centerLon: 137.5, centerLat:  38.0, sphereUV: { uMin: 0.85972, uMax: 0.90417, vMin: 0.66944, vMax: 0.75278 } },
        { id: 'korea_yellow_sea',    centerLon: 127.0, centerLat:  34.75, sphereUV: { uMin: 0.83889, uMax: 0.86667, vMin: 0.67222, vMax: 0.71389 } },
        { id: 'taiwan',              centerLon: 121.25, centerLat: 23.75, sphereUV: { uMin: 0.82917, uMax: 0.84444, vMin: 0.61944, vMax: 0.64444 } },
        // ── Europe / Atlantic ─────────────────────────────────────────────────
        { id: 'mediterranean_east',  centerLon:  29.5, centerLat:  37.75, sphereUV: { uMin: 0.56111, uMax: 0.60278, vMin: 0.68889, vMax: 0.73056 } },
        { id: 'mediterranean_west',  centerLon:  14.5, centerLat:  41.25, sphereUV: { uMin: 0.51944, uMax: 0.56111, vMin: 0.69722, vMax: 0.76111 } },
        { id: 'british_isles',       centerLon:  -4.0, centerLat:  55.5,  sphereUV: { uMin: 0.46944, uMax: 0.50833, vMin: 0.77500, vMax: 0.84167 } },
        { id: 'norway_fjords',       centerLon:  11.0, centerLat:  64.25, sphereUV: { uMin: 0.51111, uMax: 0.55000, vMin: 0.81944, vMax: 0.89444 } },
        { id: 'iceland',             centerLon: -18.5, centerLat:  64.75, sphereUV: { uMin: 0.42500, uMax: 0.47222, vMin: 0.84722, vMax: 0.87222 } },
        { id: 'azores',              centerLon: -28.0, centerLat:  38.25, sphereUV: { uMin: 0.41250, uMax: 0.43194, vMin: 0.70278, vMax: 0.72222 } },
        { id: 'canary_madeira',      centerLon: -15.75, centerLat: 30.25, sphereUV: { uMin: 0.44861, uMax: 0.46389, vMin: 0.65000, vMax: 0.68611 } },
        // ── Middle East / Indian Ocean ────────────────────────────────────────
        { id: 'black_sea',           centerLon:  34.75, centerLat: 43.75, sphereUV: { uMin: 0.57639, uMax: 0.61667, vMin: 0.72500, vMax: 0.76111 } },
        { id: 'caspian_sea',         centerLon:  52.0,  centerLat: 42.0,  sphereUV: { uMin: 0.63611, uMax: 0.65278, vMin: 0.70278, vMax: 0.76389 } },
        { id: 'red_sea',             centerLon:  38.0,  centerLat: 21.0,  sphereUV: { uMin: 0.58889, uMax: 0.62222, vMin: 0.56667, vMax: 0.66667 } },
        { id: 'persian_gulf',        centerLon:  55.0,  centerLat: 24.75, sphereUV: { uMin: 0.63889, uMax: 0.66667, vMin: 0.62222, vMax: 0.65278 } },
        { id: 'sri_lanka',           centerLon:  80.5,  centerLat:  8.25, sphereUV: { uMin: 0.71806, uMax: 0.72917, vMin: 0.53056, vMax: 0.56111 } },
        { id: 'andaman_sea',         centerLon:  96.0,  centerLat:  9.75, sphereUV: { uMin: 0.75417, uMax: 0.77917, vMin: 0.52778, vMax: 0.58056 } },
        { id: 'seychelles',          centerLon:  56.0,  centerLat: -5.5,  sphereUV: { uMin: 0.65139, uMax: 0.65972, vMin: 0.45833, vMax: 0.48056 } },
        { id: 'madagascar',          centerLon:  47.0,  centerLat:-19.0,  sphereUV: { uMin: 0.61944, uMax: 0.64167, vMin: 0.35000, vMax: 0.43889 } },
        // ── Africa / Southern ─────────────────────────────────────────────────
        { id: 'south_africa',        centerLon:  24.5,  centerLat:-28.0,  sphereUV: { uMin: 0.54444, uMax: 0.59167, vMin: 0.30556, vMax: 0.38333 } },
        { id: 'cape_verde',          centerLon: -23.75, centerLat: 16.0,  sphereUV: { uMin: 0.42778, uMax: 0.44028, vMin: 0.58056, vMax: 0.59722 } },
        // ── Pacific / Americas ────────────────────────────────────────────────
        { id: 'new_zealand',         centerLon: 172.0,  centerLat:-40.75, sphereUV: { uMin: 0.95972, uMax: 0.99583, vMin: 0.23333, vMax: 0.31389 } },
        { id: 'alaska',              centerLon:-154.5,  centerLat: 58.0,  sphereUV: { uMin: 0.03333, uMax: 0.10833, vMin: 0.80000, vMax: 0.84444 } },
        { id: 'galapagos',           centerLon: -90.5,  centerLat: -0.25, sphereUV: { uMin: 0.24306, uMax: 0.25417, vMin: 0.48611, vMax: 0.51111 } },
        { id: 'gulf_mexico_yucatan', centerLon: -90.5,  centerLat: 24.0,  sphereUV: { uMin: 0.22778, uMax: 0.26944, vMin: 0.59444, vMax: 0.67222 } },
        // ── 东亚补充 ──────────────────────────────────────────────────────────
        { id: 'bohai_sea',           centerLon: 119.75, centerLat: 39.0,  sphereUV: { uMin: 0.82500, uMax: 0.84028, vMin: 0.70556, vMax: 0.72778 } },
        { id: 'east_china_sea',      centerLon: 125.0,  centerLat: 28.5,  sphereUV: { uMin: 0.83056, uMax: 0.86389, vMin: 0.62778, vMax: 0.68889 } },
        { id: 'sea_of_japan',        centerLon: 135.0,  centerLat: 42.5,  sphereUV: { uMin: 0.85556, uMax: 0.89444, vMin: 0.68333, vMax: 0.78889 } },
        { id: 'taiwan_strait',       centerLon: 119.25, centerLat: 24.5,  sphereUV: { uMin: 0.82500, uMax: 0.83750, vMin: 0.62500, vMax: 0.64722 } },
        { id: 'bashi_channel',       centerLon: 120.5,  centerLat: 20.25, sphereUV: { uMin: 0.82778, uMax: 0.84167, vMin: 0.60000, vMax: 0.62500 } },
        // ── 东南亚补充 ────────────────────────────────────────────────────────
        { id: 'singapore_malacca',   centerLon: 102.0,  centerLat:  3.75, sphereUV: { uMin: 0.77222, uMax: 0.79444, vMin: 0.50278, vMax: 0.53889 } },
        { id: 'borneo',              centerLon: 113.75, centerLat:  3.0,  sphereUV: { uMin: 0.80000, uMax: 0.83194, vMin: 0.48889, vMax: 0.54444 } },
        { id: 'indonesia_west',      centerLon: 108.5,  centerLat: -1.5,  sphereUV: { uMin: 0.77500, uMax: 0.82778, vMin: 0.45000, vMax: 0.53333 } },
        { id: 'gulf_of_thailand',    centerLon: 103.5,  centerLat: 11.0,  sphereUV: { uMin: 0.77500, uMax: 0.80000, vMin: 0.52778, vMax: 0.59444 } },
        // ── 南亚补充 ──────────────────────────────────────────────────────────
        { id: 'bay_of_bengal',       centerLon:  90.0,  centerLat: 14.0,  sphereUV: { uMin: 0.72222, uMax: 0.77778, vMin: 0.52778, vMax: 0.62778 } },
        { id: 'arabian_sea',         centerLon:  69.0,  centerLat: 16.5,  sphereUV: { uMin: 0.66667, uMax: 0.71667, vMin: 0.54444, vMax: 0.63889 } },
        // ── 欧洲补充 ──────────────────────────────────────────────────────────
        { id: 'baltic_sea',          centerLon:  19.5,  centerLat: 60.0,  sphereUV: { uMin: 0.52500, uMax: 0.58333, vMin: 0.80000, vMax: 0.86667 } },
        { id: 'adriatic_sea',        centerLon:  16.25, centerLat: 42.0,  sphereUV: { uMin: 0.53333, uMax: 0.55694, vMin: 0.71111, vMax: 0.75556 } },
        { id: 'bay_of_biscay',       centerLon:  -4.0,  centerLat: 45.25, sphereUV: { uMin: 0.47222, uMax: 0.50556, vMin: 0.73333, vMax: 0.76944 } },
        // ── 非洲补充 ──────────────────────────────────────────────────────────
        { id: 'east_africa_coast',   centerLon:  42.0,  centerLat: -4.0,  sphereUV: { uMin: 0.60556, uMax: 0.62778, vMin: 0.43333, vMax: 0.52222 } },
        { id: 'mozambique_channel',  centerLon:  37.5,  centerLat:-17.5,  sphereUV: { uMin: 0.59167, uMax: 0.61667, vMin: 0.36111, vMax: 0.44444 } },
        // ── 太平洋岛屿补充 ────────────────────────────────────────────────────
        { id: 'guam_marianas',       centerLon: 145.0,  centerLat: 14.0,  sphereUV: { uMin: 0.89861, uMax: 0.90694, vMin: 0.56667, vMax: 0.58889 } },
        { id: 'palau',               centerLon: 134.0,  centerLat:  7.0,  sphereUV: { uMin: 0.86806, uMax: 0.87639, vMin: 0.52778, vMax: 0.55000 } },
        { id: 'papua_new_guinea',    centerLon: 146.0,  centerLat: -3.75, sphereUV: { uMin: 0.88889, uMax: 0.92222, vMin: 0.45556, vMax: 0.50278 } },
        { id: 'fiji_vanuatu',        centerLon: 172.5,  centerLat:-17.0,  sphereUV: { uMin: 0.95833, uMax: 1.00000, vMin: 0.37778, vMax: 0.43333 } },
        { id: 'samoa',               centerLon:-171.0,  centerLat:-13.0,  sphereUV: { uMin: 0.01667, uMax: 0.03333, vMin: 0.41667, vMax: 0.43889 } },
        { id: 'french_polynesia',    centerLon:-149.5,  centerLat:-17.0,  sphereUV: { uMin: 0.08056, uMax: 0.08889, vMin: 0.39722, vMax: 0.41389 } },
        { id: 'christmas_island',    centerLon: 105.75, centerLat:-10.25, sphereUV: { uMin: 0.79167, uMax: 0.79583, vMin: 0.43889, vMax: 0.44722 } },
        // ── 美洲补充 ──────────────────────────────────────────────────────────
        { id: 'california_coast',    centerLon:-115.0,  centerLat: 30.0,  sphereUV: { uMin: 0.16389, uMax: 0.19722, vMin: 0.62222, vMax: 0.71111 } },
        { id: 'eastern_caribbean',   centerLon: -61.0,  centerLat: 15.0,  sphereUV: { uMin: 0.32500, uMax: 0.33611, vMin: 0.56111, vMax: 0.60556 } },
        { id: 'brazil_coast',        centerLon: -42.0,  centerLat:  0.5,  sphereUV: { uMin: 0.36111, uMax: 0.40556, vMin: 0.47222, vMax: 0.53333 } },
        { id: 'french_guiana',       centerLon: -52.0,  centerLat:  4.0,  sphereUV: { uMin: 0.35000, uMax: 0.36111, vMin: 0.51111, vMax: 0.53333 } },
        { id: 'patagonia',           centerLon: -70.0,  centerLat:-48.0,  sphereUV: { uMin: 0.28889, uMax: 0.32222, vMin: 0.18889, vMax: 0.27778 } },
        { id: 'falkland_islands',    centerLon: -59.5,  centerLat:-51.5,  sphereUV: { uMin: 0.32778, uMax: 0.34167, vMin: 0.20556, vMax: 0.22222 } },
        // ── 亚太 / 中国近海岛屿（第三批）────────────────────────────────────────
        { id: 'xisha_paracel',       centerLon: 112.0,  centerLat: 16.25, sphereUV: { uMin: 0.80417, uMax: 0.81806, vMin: 0.58056, vMax: 0.60000 } },
        { id: 'nansha_spratly',      centerLon: 113.0,  centerLat:  7.75, sphereUV: { uMin: 0.80000, uMax: 0.82778, vMin: 0.51944, vMax: 0.56667 } },
        { id: 'dongsha_pratas',      centerLon: 116.5,  centerLat: 20.5,  sphereUV: { uMin: 0.82083, uMax: 0.82639, vMin: 0.60833, vMax: 0.61944 } },
        { id: 'ogasawara',           centerLon: 142.0,  centerLat: 25.75, sphereUV: { uMin: 0.89028, uMax: 0.89861, vMin: 0.63056, vMax: 0.65556 } },
        { id: 'micronesia',          centerLon: 151.5,  centerLat:  7.0,  sphereUV: { uMin: 0.88333, uMax: 0.95833, vMin: 0.51944, vMax: 0.55833 } },
        { id: 'marshall_islands',    centerLon: 166.0,  centerLat:  8.0,  sphereUV: { uMin: 0.94444, uMax: 0.97778, vMin: 0.52222, vMax: 0.56667 } },
        { id: 'solomon_islands',     centerLon: 159.0,  centerLat: -8.0,  sphereUV: { uMin: 0.93056, uMax: 0.95278, vMin: 0.43333, vMax: 0.47778 } },
        { id: 'new_caledonia',       centerLon: 165.5,  centerLat:-20.75, sphereUV: { uMin: 0.95139, uMax: 0.96806, vMin: 0.37222, vMax: 0.39722 } },
        { id: 'tonga',               centerLon:-175.0,  centerLat:-19.5,  sphereUV: { uMin: 0.00833, uMax: 0.01944, vMin: 0.36667, vMax: 0.41667 } },
        { id: 'kiribati_gilbert',    centerLon: 174.25, centerLat:  0.25, sphereUV: { uMin: 0.97500, uMax: 0.99306, vMin: 0.48056, vMax: 0.52222 } },
        // ── 美洲补充（第三批）────────────────────────────────────────────────────
        { id: 'puerto_rico_vi',      centerLon: -66.25, centerLat: 18.0,  sphereUV: { uMin: 0.30972, uMax: 0.32222, vMin: 0.59444, vMax: 0.60556 } },
        { id: 'abc_venezuela',       centerLon: -66.25, centerLat: 12.0,  sphereUV: { uMin: 0.29722, uMax: 0.33472, vMin: 0.55556, vMax: 0.57778 } },
        { id: 'easter_island',       centerLon:-109.5,  centerLat:-27.0,  sphereUV: { uMin: 0.19306, uMax: 0.19861, vMin: 0.34444, vMax: 0.35556 } },
        { id: 'rio_southeast_brazil',centerLon: -40.0,  centerLat:-19.5,  sphereUV: { uMin: 0.37222, uMax: 0.40556, vMin: 0.36111, vMax: 0.42222 } },
        { id: 'peru_chile_coast',    centerLon: -76.0,  centerLat:-11.0,  sphereUV: { uMin: 0.27222, uMax: 0.30556, vMin: 0.40000, vMax: 0.47778 } },
        { id: 'rio_de_la_plata',     centerLon: -56.0,  centerLat:-33.5,  sphereUV: { uMin: 0.33333, uMax: 0.35556, vMin: 0.29444, vMax: 0.33333 } },
        { id: 'south_georgia',       centerLon: -37.0,  centerLat:-54.0,  sphereUV: { uMin: 0.38889, uMax: 0.40556, vMin: 0.18889, vMax: 0.21111 } },
        { id: 'bermuda',             centerLon: -65.0,  centerLat: 32.5,  sphereUV: { uMin: 0.31806, uMax: 0.32083, vMin: 0.67778, vMax: 0.68333 } },
        { id: 'central_america_pacific', centerLon:-84.5, centerLat:12.5, sphereUV: { uMin: 0.24444, uMax: 0.28611, vMin: 0.53889, vMax: 0.60000 } },
        // ── 欧洲补充（第三批）────────────────────────────────────────────────────
        { id: 'faroe_islands',       centerLon:  -6.75, centerLat: 62.0,  sphereUV: { uMin: 0.47778, uMax: 0.48472, vMin: 0.84167, vMax: 0.84722 } },
        { id: 'svalbard',            centerLon:  20.0,  centerLat: 79.0,  sphereUV: { uMin: 0.52778, uMax: 0.58333, vMin: 0.92222, vMax: 0.95556 } },
        // ── 补漏（第四批）────────────────────────────────────────────────────────────
        { id: 'hainan_island',       centerLon: 109.75, centerLat: 19.25, sphereUV: { uMin: 0.80000, uMax: 0.80972, vMin: 0.60000, vMax: 0.61389 } },
        { id: 'kuril_southern',      centerLon: 146.0,  centerLat: 45.5,  sphereUV: { uMin: 0.89306, uMax: 0.91806, vMin: 0.73889, vMax: 0.76667 } },
      ].map((r) => ({
        ...r,
        tileUrls: _RDL_HIRES_VARIANTS.map(
          (variant) => `/assets/earth/bmng21k/topo_bathy/tiles_rdl_regions/${r.id}/tile_noon_air_mapbox_${variant}.jpg`
        ).concat([
          `/assets/earth/bmng21k/topo_bathy/tiles_rdl_regions/${r.id}/tile_noon_air_mapbox.jpg`,
        ]),
        tileFallbackUrls: [
          `/assets/earth/bmng21k/topo_bathy/tiles_rdl_regions/${r.id}/tile_noon_air.jpg`,
        ],
      }))

      // Zoom constants kept for FOV control via scroll wheel and audit labels.
      // RDL overlay visibility is intentionally opt-in through _rdlInspectRegion;
      // otherwise regional tiles can appear as hard local-resolution patches while
      // browsing non-RDL audit locations.
      const _RDL_ZOOM_START   = 0.28
      const _RDL_ZOOM_FULL    = 0.60
      // Facing: overlay fades from 0 at the limb (facing=0) to full at facing >= _RDL_FACE_FULL.
      // Depth test handles back-face occlusion; the facing fade only softens the limb transition.
      const _RDL_FACE_THRESH  = -0.1  // start showing just past the back-limb
      const _RDL_FACE_FULL    =  0.25 // full opacity when region is within ~76° of camera center
      let   _rdlZoomLevel     = 0    // 0 = normal FOV, 1 = maximum zoom in
      let   _rdlInspectRegion = null // region id forced visible for audit/inspection mode
      let   _currentAuditViewAngle = 'top'

      const _rdlSphereGeom = new THREE.SphereGeometry(2.003, 128, 128)

      const _rdlVertShader = `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `
      const _rdlFragShader = `
        precision mediump float;
        uniform sampler2D tRegional;
        uniform vec4 uBounds;
        uniform float uOpacity;
        uniform vec2 uTexel;
        uniform float uSharpen;
        varying vec2 vUv;
        void main() {
          float u0 = uBounds.x, u1 = uBounds.y, v0 = uBounds.z, v1 = uBounds.w;
          if (vUv.x < u0 || vUv.x > u1 || vUv.y < v0 || vUv.y > v1) discard;
          float tu = (vUv.x - u0) / (u1 - u0);
          float tv = (vUv.y - v0) / (v1 - v0);
          vec2 uv = vec2(tu, tv);
          vec4 col = texture2D(tRegional, uv);
          if (uSharpen > 0.0) {
            vec3 north = texture2D(tRegional, uv + vec2(0.0, -uTexel.y)).rgb;
            vec3 south = texture2D(tRegional, uv + vec2(0.0,  uTexel.y)).rgb;
            vec3 east  = texture2D(tRegional, uv + vec2( uTexel.x, 0.0)).rgb;
            vec3 west  = texture2D(tRegional, uv + vec2(-uTexel.x, 0.0)).rgb;
            vec3 sharpened = col.rgb * (1.0 + 4.0 * uSharpen) - (north + south + east + west) * uSharpen;
            col.rgb = clamp(mix(col.rgb, sharpened, 0.45), 0.0, 1.0);
          }
          float ex = clamp(min(tu, 1.0 - tu) * 6.0, 0.0, 1.0);
          float ey = clamp(min(tv, 1.0 - tv) * 6.0, 0.0, 1.0);
          gl_FragColor = vec4(col.rgb, uOpacity * min(ex, ey));
        }
      `

      const rdlMeshes = _RDL_REGIONS.map((region) => {
        const mat = new THREE.ShaderMaterial({
          transparent: true,
          depthWrite: false,
          uniforms: {
            tRegional: { value: null },
            uBounds:   { value: new THREE.Vector4(region.sphereUV.uMin, region.sphereUV.uMax, region.sphereUV.vMin, region.sphereUV.vMax) },
            uOpacity:  { value: 0.0 },
            uTexel:    { value: new THREE.Vector2(1 / 4096, 1 / 4096) },
            uSharpen:  { value: 0.0 },
          },
          vertexShader:   _rdlVertShader,
          fragmentShader: _rdlFragShader,
        })
        const mesh = new THREE.Mesh(_rdlSphereGeom, mat)
        mesh.renderOrder = 5
        mesh.visible = false
        earth.add(mesh)
        const entry = { region, mat, mesh, loaded: false, loading: false, texture: null }
        // Pre-load all RDL textures immediately so there's no pop-in when rotating to a region.
        // Prefer 8k regional composites when present, then fall back to default 4k assets.
        const _applyRDLTex = (tex) => {
          entry.texture = configureRegionalTexture(tex)
          mat.uniforms.tRegional.value = entry.texture
          const texWidth = entry.texture?.image?.width || 4096
          const texHeight = entry.texture?.image?.height || texWidth
          mat.uniforms.uTexel.value = new THREE.Vector2(1 / texWidth, 1 / texHeight)
          entry.loaded = true
          entry.loading = false
        }
        const _tileCandidates = [
          ...(Array.isArray(region.tileUrls) ? region.tileUrls : []),
          ...(Array.isArray(region.tileFallbackUrls) ? region.tileFallbackUrls : []),
        ].filter(Boolean)
        const _loadRDLTile = (urlIndex = 0) => {
          const url = _tileCandidates[urlIndex]
          if (!url) {
            entry.loading = false
            console.warn('[earth3d] RDL tile failed:', region.id, '(all candidates exhausted)')
            return
          }
          new THREE.TextureLoader().load(url, (tex) => {
            _applyRDLTex(tex)
            const qualityTag = url.includes('_8k.') ? '(8k)' : (url.includes('tile_noon_air.jpg') ? '(fallback)' : '(mapbox)')
            console.log('[earth3d] RDL tile ready:', region.id, qualityTag)
          }, undefined, () => {
            _loadRDLTile(urlIndex + 1)
          })
        }
        entry.loading = true
        _loadRDLTile(0)
        return entry
      })

      const _rdlEarthWorldPos = new THREE.Vector3()

      function refreshRDLTextureSampling() {
        const auditProfile = getAuditViewProfile()
        rdlMeshes.forEach((entry) => {
          const profile = applyRegionalTextureSampling(entry.texture, auditProfile)
          entry.mat.uniforms.uSharpen.value = _rdlInspectRegion ? profile.sharpen : 0.0
        })
      }

      // Themes that use the screen-space Rim Overlay + Inner Horizon Veil
      // system (outer sky-side line + inner surface-side haze) instead of
      // relying solely on the 3D Fresnel atmosphere shell for limb glow.
      // DeepNight uses the same screen-space Rim Overlay + Inner Horizon Veil
      // stack as earlyMorning; see deepNight.rimGlow in THEME_VISUAL_CONFIG.
      const RIM_OVERLAY_THEMES = new Set(['earlyMorning', 'deepNight', 'evening', 'lateEvening', 'night', 'dawn', 'morning', 'noon', 'afternoon', 'sunrise', 'goldenApproach', 'sunset'])

      function updateEarlyMorningGlowMode() {
        if (!_emRimOverlayMat || !_emInnerVeilMat || !atmosphere || !atmosphereMaterial) return

        const usesRimOverlay = RIM_OVERLAY_THEMES.has(currentTheme)
        const cfg = usesRimOverlay
          ? getThemeVisualConfig(currentTheme)
          : null
        const baseAtmoOpacity = cfg?.atmosphere?.opacity ?? 0
        const baseAtmoPower = cfg?.atmosphere?.power ?? 16.0
        const baseAtmoPowerOuter = cfg?.atmosphere?.powerOuter ?? 5.2
        const baseAtmoStrengthOuter = cfg?.atmosphere?.strengthOuter ?? 0.18
        const baseAtmoRadius = cfg?.atmosphere?.radius ?? 2.04
        // Direction 1: always use the screen-space rim overlay stack for all
        // angles and zoom levels. The downstream guard already protects against
        // non-finite projection, and the zoom-1.0 rim radius (max ~5.52) is
        // visually acceptable — no need for a 3D shell fallback.
        const shouldUseAuditShell = false

        _emRimOverlayMat.uniforms.uOpacity.value = shouldUseAuditShell ? 0.0 : 1.0
        _emInnerVeilMat.uniforms.uOpacity.value = shouldUseAuditShell ? 0.0 : 1.0

        if (shouldUseAuditShell) {
          atmosphere.visible = true
          // Audit mode needs a self-contained 3D glow that is visible enough to
          // read at globe/oblique views, but still stays attached to geometry.
          atmosphereMaterial.uniforms.uOpacity.value = 0.30
          atmosphereMaterial.uniforms.uPower.value = 13.2
          atmosphereMaterial.uniforms.uPowerOuter.value = 4.2
          atmosphereMaterial.uniforms.uStrengthOuter.value = 0.34
          atmosphereMaterial.uniforms.uRadius.value = 2.06
        } else {
          atmosphereMaterial.uniforms.uOpacity.value = baseAtmoOpacity
          atmosphereMaterial.uniforms.uPower.value = baseAtmoPower
          atmosphereMaterial.uniforms.uPowerOuter.value = baseAtmoPowerOuter
          atmosphereMaterial.uniforms.uStrengthOuter.value = baseAtmoStrengthOuter
          atmosphereMaterial.uniforms.uRadius.value = baseAtmoRadius
          atmosphere.visible = baseAtmoOpacity > 0.0001
        }
      }

      // Projects Earth's screen-space center + radius, then positions both CSS glow overlays.
      // Two separate elements are required: the rim needs blur≈1px (sharp), the haze needs blur≈14px.
      function updateHorizonGlow() {
        const hide = !_horizonGlowCfg || !_horizonGlowCfg.enabled
        if (hide) {
          if (_horizonGlowEl) _horizonGlowEl.style.opacity = '0'
          if (_rimGlowEl)     _rimGlowEl.style.opacity = '0'
          return
        }
        const cfg = _horizonGlowCfg
        const w = mountEl.clientWidth  || renderer.domElement.clientWidth  || renderer.domElement.width
        const h = mountEl.clientHeight || renderer.domElement.clientHeight || renderer.domElement.height

        // --- Project Earth center and radius ----
        const _center = new THREE.Vector3(0, 0, 0)
        earth.getWorldPosition(_center)
        const _proj = _center.clone().project(camera)
        const cx = (_proj.x * 0.5 + 0.5) * w
        const cy = (-_proj.y * 0.5 + 0.5) * h

        // Horizontal radius: project a point one Earth-radius (2.0 world units) to camera-right.
        // Previously used 1.0 (half radius), causing the overlay to be smaller than the Earth disk
        // and the glow to paint over the Earth's face instead of surrounding it in space.
        const EARTH_R = 2.0
        const _right = new THREE.Vector3()
        camera.getWorldDirection(_right)
        _right.cross(camera.up).normalize()
        const _edgePt   = _center.clone().add(_right.clone().multiplyScalar(EARTH_R))
        const _edgeProj = _edgePt.clone().project(camera)
        const r_x = Math.sqrt(((_edgeProj.x * 0.5 + 0.5) * w - cx) ** 2 +
                              ((-_edgeProj.y * 0.5 + 0.5) * h - cy) ** 2)

        // Vertical radius: use camera-up direction (accurate for oblique presets) and take MIN of
        // the two projections. When Earth center is off-screen (default view: cy ≈ 881 on 812px
        // screen), max() would pick the off-screen lower offset (~680px) making the inner
        // transparent hole overshoot the actual limb by ~420px. min() gives the closer limb
        // (the part visible on screen), so the glow correctly hugs the Earth's projected edge.
        const _cameraUp = new THREE.Vector3()
        _cameraUp.setFromMatrixColumn(camera.matrixWorld, 1).normalize()
        const _tPt = _center.clone().add(_cameraUp.clone().multiplyScalar(EARTH_R))
        const _bPt = _center.clone().add(_cameraUp.clone().multiplyScalar(-EARTH_R))
        const _tSc = _tPt.clone().project(camera)
        const _bSc = _bPt.clone().project(camera)
        const r_y_up   = Math.abs((-_tSc.y * 0.5 + 0.5) * h - cy)
        const r_y_down = Math.abs((-_bSc.y * 0.5 + 0.5) * h - cy)
        const r_y = Math.min(r_y_up, r_y_down)

        const sc = cfg.scale ?? 1.32
        const rw = r_x * sc
        const rh = r_y * sc

        // --- Layer B: soft outer haze (high blur, starts OUTSIDE Earth edge) ---
        // innerStop × scale > 1.0 → transparent hole covers entire Earth disk.
        // A subtle off-center glow at the top-left breaks the uniform ring feel.
        const c0 = cfg.colorCore  ?? '#e0f0ff'
        const c1 = cfg.colorMain  ?? '#98c8e8'
        const c2 = cfg.colorOuter ?? '#5888a8'
        const s0 = ((cfg.innerStop ?? 0.768) * 100).toFixed(1)
        const s1 = ((cfg.coreStop  ?? 0.800) * 100).toFixed(1)
        const s2 = ((cfg.midStop   ?? 0.875) * 100).toFixed(1)
        const s3 = ((cfg.outerStop ?? 0.960) * 100).toFixed(1)
        const hazeBlur = cfg.blur ?? 16

        // Slight directional variation: shift the gradient center slightly toward the "lit" side.
        // Default offset (47%, 44%) gives upper-left limb a subtly brighter arc,
        // breaking the uniform ring feel without adding a hard spotlight.
        // Config: lightDirX/lightDirY (default 47/44, range 40–60).
        const lDirX = cfg.lightDirX ?? 47
        const lDirY = cfg.lightDirY ?? 44
        _horizonGlowEl.style.cssText = `
          position: absolute; pointer-events: none; mix-blend-mode: screen; z-index: 2;
          filter: blur(${hazeBlur}px);
          opacity: ${cfg.opacity ?? 0.055};
          left: ${cx - rw}px; top: ${cy - rh}px;
          width: ${rw * 2}px; height: ${rh * 2}px;
          border-radius: 50%;
          background: radial-gradient(ellipse at ${lDirX}% ${lDirY}%,
            rgba(0,0,0,0) ${s0}%,
            ${c0}30 ${s1}%,
            ${c1}1e ${s2}%,
            ${c2}0a ${s3}%,
            rgba(0,0,0,0) 100%
          );
        `

        // --- Layer A: thin bright rim (near-zero blur, only at Earth's edge) ---
        // Gradient range is deliberately narrow so filter:blur(2px) keeps it 1-4px visually.
        const rimCfg = cfg.rim
        if (_rimGlowEl && rimCfg) {
          const earthEdgePct = (1 / sc * 100).toFixed(2)          // % where Earth's edge is
          const hw = (rimCfg.halfWidth ?? 0.008) * 100             // half-width in %
          const rimColor = rimCfg.color ?? '#eaf6ff'
          const rimAlpha = Math.round((rimCfg.strength ?? 0.38) * 255).toString(16).padStart(2,'0')
          const rimBlur  = rimCfg.blur ?? 1.8

          const p0 = (parseFloat(earthEdgePct) - hw * 1.8).toFixed(2)
          const p1 = (parseFloat(earthEdgePct) - hw * 0.3).toFixed(2)  // ramp in
          const p2 = earthEdgePct                                        // peak
          const p3 = (parseFloat(earthEdgePct) + hw * 0.5).toFixed(2)  // quick outer drop
          const p4 = (parseFloat(earthEdgePct) + hw * 2.5).toFixed(2)  // fully faded

          _rimGlowEl.style.cssText = `
            position: absolute; pointer-events: none; mix-blend-mode: screen; z-index: 3;
            filter: blur(${rimBlur}px);
            opacity: 1;
            left: ${cx - rw}px; top: ${cy - rh}px;
            width: ${rw * 2}px; height: ${rh * 2}px;
            border-radius: 50%;
            background: radial-gradient(ellipse at center,
              rgba(0,0,0,0) ${p0}%,
              ${rimColor}00 ${p1}%,
              ${rimColor}${rimAlpha} ${p2}%,
              ${rimColor}1a ${p3}%,
              rgba(0,0,0,0) ${p4}%
            );
          `
        } else if (_rimGlowEl) {
          _rimGlowEl.style.opacity = '0'
        }

        if (window.RODIO_DEBUG_HORIZON_GLOW) {
          const hw_px = (cfg.rim?.halfWidth ?? 0.008) * rh
          console.log('[HorizonGlow]', {
            projectedCenterX: cx.toFixed(0),
            projectedCenterY: cy.toFixed(0),
            projectedRadiusX: r_x.toFixed(0),
            projectedRadiusY: r_y.toFixed(0),
            overlayLeft:   (cx - rw).toFixed(0),
            overlayTop:    (cy - rh).toFixed(0),
            overlayWidth:  (rw * 2).toFixed(0),
            overlayHeight: (rh * 2).toFixed(0),
            scale:         sc,
            rim_hw_px:     hw_px.toFixed(1),
            rimCoreOpacity:   cfg.rim?.strength ?? 0,
            outerHazeOpacity: cfg.opacity ?? 0,
            innerIntrusion: ((cfg.innerStop ?? 0.78) * sc - 1.0).toFixed(3),
            containerW: w, containerH: h,
          })
          _horizonGlowEl.style.outline = '1px dashed rgba(0,255,255,0.4)'
          if (_rimGlowEl) _rimGlowEl.style.outline = '1px dashed rgba(255,200,0,0.4)'
        } else {
          _horizonGlowEl.style.outline = ''
          if (_rimGlowEl) _rimGlowEl.style.outline = ''
        }
      }

      function updateRDLOverlays() {
        // RDL overlays use a separate ShaderMaterial with no night processing.
        // Hide them entirely for night themes to prevent raw day-bright tiles showing through.
        const _nightThemes = new Set(['deepNight', 'night', 'lateEvening'])
        if (_nightThemes.has(currentTheme)) {
          rdlMeshes.forEach(({ mesh, mat }) => {
            mesh.visible = false
            mat.uniforms.uOpacity.value = 0
          })
          return
        }
        refreshRDLTextureSampling()
        earth.updateWorldMatrix(true, false)
        earth.getWorldPosition(_rdlEarthWorldPos)
        const camDir = camera.position.clone().sub(_rdlEarthWorldPos).normalize()

        // Score all regions by facing angle
        const scores = rdlMeshes.map((entry) => {
          const regionLocalDir = lonLatToVector3(entry.region.centerLon, entry.region.centerLat, 1).normalize()
          const regionWorldDir = regionLocalDir.clone().transformDirection(earth.matrixWorld).normalize()
          const facing = camDir.dot(regionWorldDir)
          const ft = Math.max(0, Math.min(1, (facing - _RDL_FACE_THRESH) / (_RDL_FACE_FULL - _RDL_FACE_THRESH)))
          const facingOpacity = ft * ft * (3 - 2 * ft)
          return { entry, facingOpacity }
        })

        if (_rdlInspectRegion) {
          // Inspect mode: only the target region, effectively fully opaque so
          // the regional tile is not softened by mixing with the base globe.
          scores.forEach(({ entry }) => {
            // entry.loaded gate: without it, a region can turn visible (facing
            // camera) before its regional texture finishes loading — the shader
            // samples a null tRegional uniform, which reads back as opaque black,
            // producing a hard-edged black wedge over that region's mesh bounds
            // until the async texture load resolves.
            const isTarget = entry.region.id === _rdlInspectRegion && entry.loaded
            entry.mesh.visible = isTarget
            if (isTarget) entry.mat.uniforms.uOpacity.value = 0.995
          })
        } else {
          // Non-inspect mode: keep RDL fully hidden.
          // Regional patches are for explicit audit/inspection only; auto-picking
          // the "best-facing" region causes visible wedges / patch boundaries,
          // especially around polar views and during camera-angle exploration.
          scores.forEach(({ entry }) => {
            entry.mesh.visible = false
            entry.mat.uniforms.uOpacity.value = 0.0
          })
        }
      }
      // ──────────────────────────────────────────────────────────────────────

      // Procedural star sprites: gaussian-falloff glow points (bright core +
      // soft halo) with per-star size/brightness/temperature from
      // buildStarField, plus gentle twinkling. Replaces the old uniform
      // PointsMaterial squares that read as flat artificial dots. Rendered
      // ON TOP of the starmap sphere below — the map provides the dense
      // faint-star/Milky Way background, these provide the bright foreground
      // stars with visible glow gradients.
      const _starPointsMat = new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        uniforms: {
          uOpacity: { value: 0.78 },
          uTime:    { value: 0 },
        },
        vertexShader: `
          attribute float aSize;
          attribute vec3  aColor;
          attribute float aPhase;
          varying vec3  vColor;
          varying float vPhase;
          void main() {
            vColor = aColor;
            vPhase = aPhase;
            vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
            gl_PointSize = aSize * (420.0 / -mvPosition.z);
            gl_Position = projectionMatrix * mvPosition;
          }
        `,
        fragmentShader: `
          precision mediump float;
          uniform float uOpacity;
          uniform float uTime;
          varying vec3  vColor;
          varying float vPhase;
          void main() {
            vec2 c = gl_PointCoord - vec2(0.5);
            float d2 = dot(c, c) * 4.0;           // 0 at center, 1 at sprite edge
            float core = exp(-d2 * 30.0);                   // pin-sharp bright core — gone by d2≈0.15
            float halo = exp(-d2 * 3.5) * 0.22;        // medium-wide glow, soft falloff
            float tw = 0.86 + 0.14 * sin(uTime * 1.1 + vPhase)
                     + 0.05 * sin(uTime * 3.1 + vPhase * 1.7);
            float a = (core + halo) * tw * uOpacity;
            if (a < 0.004) discard;
            gl_FragColor = vec4(vColor * a, a);
          }
        `,
      })
      // Legacy call sites (applyTheme, debug helpers) drive star brightness
      // through material.opacity — proxy that onto the shader uniform so they
      // keep working unchanged.
      Object.defineProperty(_starPointsMat, 'opacity', {
        get() { return this.uniforms.uOpacity.value },
        set(v) { this.uniforms.uOpacity.value = v },
      })
      stars = new THREE.Points(buildStarField(900, 60), _starPointsMat)
      scene.add(stars)

      // Star texture sphere: real star catalog + Milky Way, radius 250 (inside sky sphere at 300).
      // Procedural point cloud stays visible as fallback until texture loads, then hides.
      // Star texture sphere with per-star twinkling via hash(time + position).
      // AdditiveBlending so black background of the texture doesn't occlude the sky gradient.
      starSphereMaterial = new THREE.ShaderMaterial({
        uniforms: {
          uStarTexture: { value: null },
          uOpacity:     { value: 0 },
          uTime:        { value: 0 },
        },
        vertexShader: `
          varying vec3 vWorldPosition;
          void main() {
            vec4 worldPos = modelMatrix * vec4(position, 1.0);
            vWorldPosition = worldPos.xyz;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          precision mediump float;
          uniform sampler2D uStarTexture;
          uniform float     uOpacity;
          uniform float     uTime;
          varying vec3      vWorldPosition;

          // Simple position hash → unique phase per star
          float hash(vec3 p) {
            return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453);
          }

          void main() {
            // Sample the star texture using equirectangular projection from world position
            vec3 dir = normalize(vWorldPosition);
            float u  = 0.5 + atan(dir.z, dir.x) / (2.0 * 3.14159265);
            float v  = 0.5 + asin(clamp(dir.y, -1.0, 1.0)) / 3.14159265;
            vec4 tex = texture2D(uStarTexture, vec2(u, v));

            // Subtle twinkle: each fragment has a unique phase + slow oscillation
            float phase   = hash(vWorldPosition) * 6.2831853;
            float twinkle = 0.85 + 0.15 * sin(uTime * 1.4 + phase);
            // Second harmonic for variety — some stars shimmer faster
            twinkle += 0.06 * sin(uTime * 3.7 + phase * 2.3);

            gl_FragColor = vec4(tex.rgb * twinkle, tex.a) * uOpacity;
          }
        `,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        side: THREE.BackSide,
      })
      starSphere = new THREE.Mesh(
        new THREE.SphereGeometry(250, 64, 64),
        starSphereMaterial
      )
      scene.add(starSphere)
      starSphere.frustumCulled = false
      loader.load('/assets/textures/stars/starmap_2020_8k.jpg',
        (tex) => {
          if ('colorSpace' in tex) {
            tex.colorSpace = THREE.SRGBColorSpace
          } else {
            tex.encoding = THREE.sRGBEncoding
          }
          tex.anisotropy = 1
          starSphereMaterial.uniforms.uStarTexture.value = tex
          starSphereMaterial.uniformsNeedUpdate = true
          starSphereLoaded = true
          starSphereMaterial.uniforms.uOpacity.value = STAR_SPHERE_OPACITY[currentTheme || pendingTheme] ?? 0
          if (stars?.material) {
            stars.material.opacity = PROCEDURAL_STARS_OPACITY[currentTheme || pendingTheme] ?? 0
            stars.material.needsUpdate = true
          }
          requestRenderUpdate()
          console.log('[earth3d] star texture loaded')
        },
        undefined,
        () => {
          console.warn('[earth3d] star texture load failed — procedural stars kept as fallback')
        }
      )

      // Cloud shell — ShaderMaterial to avoid grey-film from linear alphaMap.
      // smoothstep crushes low-luminance areas to zero alpha; power sharpens edges.
      // Radius 2.018 = 1.009× earth (2.0), floating just above surface.
      cloudMaterial = new THREE.ShaderMaterial({
        uniforms: {
          uCloudMap:            { value: null },
          uCloudOpacity:        { value: 0.0 },
          // Per-theme cloud look (defaults below reproduce the original
          // hardcoded pure-white/0.18-0.75/pow1.35 look byte-for-byte, so any
          // theme that doesn't set an object-form `clouds` config is unaffected).
          uCloudColor:          { value: new THREE.Color('#ffffff') },
          uCloudAlphaLow:       { value: 0.18 },
          uCloudAlphaHigh:      { value: 0.75 },
          uCloudAlphaPow:       { value: 1.35 },
          // Separates broad cloud coverage from local cloud structure. The
          // low-frequency sample establishes coverage; the base sample's
          // deviation from it suppresses broad gray film and keeps formations.
          uCloudDetailMix:      { value: 0.0 },
          uCloudDetailContrast: { value: 3.5 },
          // Ocean/deep-ocean suppression — lets a theme dim clouds over water
          // (e.g. earlyMorning) without washing the ocean tone/tint out to a
          // milky white-blue. 1.0 = no suppression (existing behavior).
          uOceanMask:           { value: _maskPlaceholder },
          uOceanSuppress:       { value: 1.0 },
          uDeepOceanSuppress:   { value: 1.0 },
          // 0 = flat color (old behavior); >0 darkens thin/wispy cloud areas
          // toward gray for internal light/shadow volume. See fragment shader.
          uCloudShade:          { value: 0.0 },
          // Directional sunlight on the cloud sphere — creates lit/shadow
          // hemispheres for true volume. (0,1,0) as neutral default → uniform
          // lighting; per-theme sunDirection overrides this via _syncAtmSunDir.
          uSunDir:              { value: new THREE.Vector3(0, 1, 0) },
          // Ambient floor for the dark hemisphere (0=black, 1=full lit).
          uCloudAmbient:        { value: 0.0 },
          // Rim/backlight glow strength on the dark hemisphere (0=off).
          uCloudRim:            { value: 0.0 },
          // Alpha softening: blends edge-alpha with a mip-biased secondary
          // sample (0=off).  Non-zero only when a theme opts in.
          uCloudAlphaSoftness:  { value: 0.0 },
          uCloudMipBias:        { value: 0.0 },
        },
        vertexShader: `
          varying vec2 vUv;
          varying vec3 vWorldNormal;
          varying vec3 vWorldPos;
          void main() {
            vUv = uv;
            vec4 worldPos = modelMatrix * vec4(position, 1.0);
            vWorldPos = worldPos.xyz;
            // Sphere: local position direction IS the normal (unit sphere).
            vWorldNormal = normalize(mat3(modelMatrix) * normalize(position));
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          uniform sampler2D uCloudMap;
          uniform float uCloudOpacity;
          uniform vec3  uCloudColor;
          uniform float uCloudAlphaLow;
          uniform float uCloudAlphaHigh;
          uniform float uCloudAlphaPow;
          uniform float uCloudDetailMix;
          uniform float uCloudDetailContrast;
          uniform float uCloudAlphaSoftness;
          uniform float uCloudMipBias;
          uniform sampler2D uOceanMask;
          uniform float uOceanSuppress;
          uniform float uDeepOceanSuppress;
          uniform float uCloudShade;
          uniform vec3  uSunDir;
          uniform float uCloudAmbient;
          uniform float uCloudRim;
          varying vec2 vUv;
          varying vec3 vWorldNormal;
          varying vec3 vWorldPos;
          void main() {
            vec4 tex = texture2D(uCloudMap, vUv);
            float lum = dot(tex.rgb, vec3(0.299, 0.587, 0.114));
            // Cloud coverage is sampled from a blurred mip level while local
            // structure comes from the full-resolution sample. This prevents
            // the white/gray background of the global cloud-density map from
            // becoming a translucent film over the whole globe.
            vec4 texCoverage = texture2D(uCloudMap, vUv, 2.0);
            float coverageLum = dot(texCoverage.rgb, vec3(0.299, 0.587, 0.114));
            float coverage = smoothstep(uCloudAlphaLow, uCloudAlphaHigh, coverageLum);
            float detailSignal = clamp(abs(lum - coverageLum) * uCloudDetailContrast, 0.0, 1.0);
            float detailMask = mix(1.0, mix(0.24, 1.0, detailSignal), uCloudDetailMix);
            float alpha = coverage * detailMask;
            alpha = pow(alpha, uCloudAlphaPow);

            // Alpha softening: blend edge-alpha with a mip-biased secondary
            // texture sample.  Default-off (uCloudAlphaSoftness == 0); a theme
            // like dawn can opt in to a tiny value (0.15–0.30) to dissolve the
            // hard smoothstep boundary into a natural wispy edge.
            if (uCloudAlphaSoftness > 0.001) {
              vec4 texBias = texture2D(uCloudMap, vUv, uCloudMipBias);
              float lumBias = dot(texBias.rgb, vec3(0.299, 0.587, 0.114));
              float alphaBias = smoothstep(uCloudAlphaLow, uCloudAlphaHigh, lumBias);
              alphaBias = pow(alphaBias, uCloudAlphaPow);
              alpha = mix(alpha, alphaBias, uCloudAlphaSoftness);
            }

            // Ocean / deep-ocean suppression — land (oceanMaskValue low) is
            // unaffected; open ocean fades toward uOceanSuppress; deep ocean
            // (higher oceanMaskValue) fades further toward uDeepOceanSuppress.
            float oceanMaskValue = texture2D(uOceanMask, vUv).r;
            float oceanW = smoothstep(0.15, 0.5, oceanMaskValue);
            float deepW  = smoothstep(0.55, 0.9, oceanMaskValue);
            float suppress = mix(1.0, uOceanSuppress, oceanW);
            suppress = mix(suppress, uDeepOceanSuppress, deepW);
            alpha *= suppress;

            alpha *= uCloudOpacity;

            // Internal texture-based shading — darkens thin/wispy areas.
            float shade = mix(1.0 - uCloudShade, 1.0, smoothstep(uCloudAlphaLow, 0.95, lum));
            vec3 shadedColor = uCloudColor * shade;

            // Directional lighting on the cloud sphere.
            // vWorldNormal points outward from the sphere centre;
            // N·L > 0 → sunlit hemisphere; N·L < 0 → shadow hemisphere.
            float NdotL = dot(normalize(vWorldNormal), normalize(uSunDir));
            float diffuse = smoothstep(-0.35, 0.65, NdotL);
            float dirLight = mix(uCloudAmbient, 1.0, diffuse);

            // Rim / backlight glow — strongest where NdotL is near zero
            // (terminator edge) and the cloud is thin. Simulates the silver-
            // lining effect of sunlight catching wispy cloud edges.
            float rim = (1.0 - abs(NdotL)) * uCloudRim;

            vec3 litColor = shadedColor * dirLight + shadedColor * rim;

            gl_FragColor = vec4(litColor, alpha);
          }
        `,
        transparent: true,
        depthWrite: false,
        blending: THREE.NormalBlending,
        side: THREE.FrontSide,
      })
      cloudMesh = new THREE.Mesh(
        new THREE.SphereGeometry(2.018, 128, 128),
        cloudMaterial
      )
      cloudMesh.renderOrder = 0
      earth.add(cloudMesh)
      // Applies a theme's `clouds` config to cloudMaterial — accepts either the
      // legacy plain-number form (opacity only, all other params stay at the
      // original hardcoded defaults) or an object form for themes that need a
      // distinct cloud look (color/alpha curve/ocean suppression).
      function applyCloudThemeConfig(cloudsCfg) {
        if (!cloudMaterial?.uniforms) return
        const isObj = cloudsCfg && typeof cloudsCfg === 'object'
        // Per-theme cloud texture swap — applied before uniforms so the
        // alpha parameters are evaluated against the correct texture.
        if (isObj && cloudsCfg.texture) { _setCloudTexture(cloudsCfg.texture) }
        const u = cloudMaterial.uniforms
        u.uCloudOpacity.value      = (isObj ? cloudsCfg.opacity : cloudsCfg) ?? 0
        u.uCloudColor.value.set(isObj && cloudsCfg.color ? cloudsCfg.color : '#ffffff')
        u.uCloudAlphaLow.value     = isObj && cloudsCfg.alphaLow          != null ? cloudsCfg.alphaLow          : 0.18
        u.uCloudAlphaHigh.value    = isObj && cloudsCfg.alphaHigh         != null ? cloudsCfg.alphaHigh         : 0.75
        u.uCloudAlphaPow.value     = isObj && cloudsCfg.alphaPow          != null ? cloudsCfg.alphaPow          : 1.35
        u.uCloudDetailMix.value    = isObj && cloudsCfg.detailMix         != null ? cloudsCfg.detailMix         : 0.0
        u.uCloudDetailContrast.value = isObj && cloudsCfg.detailContrast  != null ? cloudsCfg.detailContrast  : 3.5
        u.uCloudAlphaSoftness.value= isObj && cloudsCfg.alphaSoftness     != null ? cloudsCfg.alphaSoftness     : 0.0
        console.log('[cloud] apply cfg:', JSON.stringify({ texture: isObj ? cloudsCfg.texture : 'none', opacity: u.uCloudOpacity.value, alphaLow: u.uCloudAlphaLow.value, alphaHigh: u.uCloudAlphaHigh.value, detailMix: u.uCloudDetailMix.value }))
        u.uCloudMipBias.value      = isObj && cloudsCfg.mipBias           != null ? cloudsCfg.mipBias           : 0.0
        u.uOceanSuppress.value     = isObj && cloudsCfg.oceanSuppress     != null ? cloudsCfg.oceanSuppress     : 1.0
        u.uDeepOceanSuppress.value = isObj && cloudsCfg.deepOceanSuppress != null ? cloudsCfg.deepOceanSuppress : 1.0
        u.uCloudShade.value        = isObj && cloudsCfg.shade             != null ? cloudsCfg.shade             : 0.0
        u.uCloudAmbient.value      = isObj && cloudsCfg.ambient           != null ? cloudsCfg.ambient           : 0.0
        u.uCloudRim.value          = isObj && cloudsCfg.rim               != null ? cloudsCfg.rim               : 0.0
        // Cloud-sphere radius scale — lifts the cloud layer slightly above
        // the surface to reduce the "pasted-on" feel.  Default 1.0 (2.018).
        if (cloudMesh) {
          const rs = isObj && cloudsCfg.radiusScale != null ? cloudsCfg.radiusScale : 1.0
          cloudMesh.scale.setScalar(rs)
        }
      }
      // ── Per-theme cloud texture system ──────────────────────────
      // Each theme can specify its own cloud map via `clouds.texture`.
      // Textures are pre-loaded into a cache; applyCloudThemeConfig
      // swaps the active texture when the theme changes.
      const CLOUD_TEXTURE_BASE = '/assets/textures/clouds/'
      const CLOUD_TEXTURE_DEFAULT = 'fair_clouds_8k.jpg'
      const cloudTextureCache = {} // name → THREE.Texture

      function _setupCloudTex(tex) {
        if ('colorSpace' in tex) {
          tex.colorSpace = THREE.SRGBColorSpace
        } else {
          tex.encoding = THREE.sRGBEncoding
        }
        tex.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy())
        return tex
      }

      function _resolveCloudTextureName(theme) {
        const cfg = getThemeVisualConfig(theme)
        return (cfg?.clouds?.texture) || CLOUD_TEXTURE_DEFAULT
      }

      function _setCloudTexture(name) {
        const tex = cloudTextureCache[name]
        if (tex && cloudMaterial) {
          cloudMaterial.uniforms.uCloudMap.value = tex
          console.log('[cloud] _setCloudTexture:', name, tex?.image?.src || tex?.source?.data ? 'loaded' : 'no-img')
        }
      }

      // All cloud textures used by the themes — static list to avoid
      // accessing THEME_VISUAL_CONFIG before its const declaration.
      const _neededCloudTex = new Set([
        'fair_clouds_8k.jpg',
        'fair_clouds_soft_8k.jpg',
        'africa_clouds_8k.jpg',
        'n_amer_clouds_8k.jpg',
        'se_asia_clouds_8k.jpg',
        'australia_clouds_8k.jpg',
        'storm_clouds_crisp_8k.jpg',
        'storm_clouds_8k.jpg',
        'europe_clouds_8k.jpg',
        's_amer_clouds_8k.jpg',
        'africa_clouds_wispy_8k.jpg',
        'clouds_live_8k.jpg',
      ])
      let _cloudTexPending = _neededCloudTex.size
      for (const name of _neededCloudTex) {
        loader.load(CLOUD_TEXTURE_BASE + name, (tex) => {
          cloudTextureCache[name] = _setupCloudTex(tex)
          _cloudTexPending--
          if (_cloudTexPending === 0) {
            // All textures ready — activate the initial theme's texture.
            const initialName = _resolveCloudTextureName(currentTheme || pendingTheme)
            cloudTexture = cloudTextureCache[initialName]
            _setCloudTexture(initialName)
            applyCloudThemeConfig(getThemeVisualConfig(currentTheme || pendingTheme).clouds)
            requestRenderUpdate()
            console.log('[earth3d] cloud textures loaded:', Object.keys(cloudTextureCache).length)
          }
        })
      }

      const ambientLight = new THREE.AmbientLight(0xffffff, 0.018)
      scene.add(ambientLight)

      const sunLight = new THREE.DirectionalLight(0xfff5e0, 1.25)
      scene.add(sunLight)

      // Transitional bridge toward the future 9-segment time system:
      // dawn, sunrise, earlyMorning, morning, noon, afternoon,
      // sunset, evening, deepNight.
      //
      // Current button compatibility is preserved:
      // sunrise -> sunrise
      // morning -> morning
      // noon -> noon
      // sunset -> sunset
      // night -> night (compatible with deepNight)
      //
      // Visual responsibility notes:
      // dawn: pre-sunrise / night-dawn transition
      // sunrise: sunrise / lock-screen reference primary direction
      // earlyMorning: post-sunrise cool morning transition
      // morning: morning
      // noon: noon
      // afternoon: softer post-noon daylight
      // sunset: sunset / low-angle evening transition
      // evening: early night with visible city lights
      // deepNight: pure deep-night mode
      //
      // Reference lock-screen styling should ultimately live in dawn/sunrise,
      // not in pure night.
      // STAR_SPHERE_OPACITY: values migrated into THEME_VISUAL_CONFIG.starSphereOpacity.
      // Kept as fallback for the `night` legacy key and any future theme without an
      // inline starSphereOpacity entry. Do not use as the primary source.
      const STAR_SPHERE_OPACITY = {
        dawn:                      0.03,
        sunrise:                   0.02,
        earlyMorning:              0.02,
        morning:                   0.02,
        noon:                      0.00,
        afternoon:                 0.00,
        goldenApproach:            0.04,
        sunset:                    0.04,
        evening:                   0.10,
        lateEvening:               0.18,
        deepNight:                 0.32,
        night:                     0.22,
      }

      // Procedural sprite-star overlay opacity per theme.
      // These foreground glow-dots now coexist with the texture starmap
      // (rather than being zeroed on load), so values are tuned lower than
      // the historical config.lighting.stars to keep them as subtle bright accents
      // on top of the dense background starfield.
      // Read via PROCEDURAL_STARS_OPACITY[theme] with a daytime-safe fallback.
      const PROCEDURAL_STARS_OPACITY = {
        dawn:                      0.12,
        sunrise:                   0.02,
        earlyMorning:              0,
        morning:                   0,
        noon:                      0,
        afternoon:                 0,
        goldenApproach:            0.01,
        sunset:                    0.05,
        evening:                   0.12,
        lateEvening:               0.20,
        deepNight:                 0.28,
        night:                     0.24,
      }

      const THEME_VISUAL_CONFIG = {
        dawn: {
          // V4-2B: pre-sunrise / night-dawn transition. Sits visually between
          // deepNight (22.5h, pure night) and earlyMorning (7.4h, cool morning).
          // Dawn signature: sky just beginning to lift from black to deep blue,
          // a thin warm-cool horizon micro-glow, ocean starting to read blue
          // (not pitch black), city lights dimmed but not yet extinguished,
          // stars still present but thinning.
          themeHour: 5.0,
          texture: {
            map: 'day',
            emissiveMap: 'night',
            // Cool blue-grey day base — the first hint of pre-dawn light lifting
            // the land out of pure night, but far from earlyMorning's full white.
            mapColor: 0x8a98a4,
            // Warm amber filament, dimmer than deepNight's gold — cities fading
            // as the sky brightens, but still a recognizable network.
            emissiveColor: 0xffb066,
            emissiveIntensity: 0.18,
            nightBaseIntensity: 0.16,
          },
          material: {
            specular: 0x000102,
            shininess: 0.10,
          },
          // Thin blue limb glow just waking up — less than earlyMorning's bright
          // core, more present than deepNight's disabled shell. Disabled by
          // default (Rim Overlay owns the limb job, same as earlyMorning).
          atmosphere: {
            color: '#9fc4e0',
            colorOuter: '#5d86a8',
            radius: 2.04,
            opacity: 0.0,
            power: 15.0,
            powerOuter: 5.0,
            strengthOuter: 0.16,
          },
          // Screen-space Rim Overlay + Inner Horizon Veil — dawn-tinted electric
          // blue arc: cooler and a touch softer than deepNight's saturated blue,
          // with a faint warm core hint at the limb (first pre-sun warmth).
          rimGlow: {
            outer: {
              color: '#8FA9C0', colorNear: '#cfe0ec', colorFar: '#04101f',
              width: 0.10, coreFraction: 0.34, coreStrength: 0.70, haloStrength: 0.20,
              tailPower: 2.8, corePower: 9.4, rimOffsetY: 0.004,
            },
            inner: {
              color: '#a9d2f0', width: 0.09, strength: 0.34, falloff: 2.4,
            },
          },
          lighting: {
            // Ambient lifted off deepNight's 1.0 floor toward a soft pre-dawn fill;
            // sun barely cracking the horizon; stars thinning but not gone.
            ambient: 0.62,
            sun: 0.10,
            stars: 0.46,
            cityLightsOpacity: 0.08, // dead param — logging only
            cityLightClamp: 0.72,
          },
          // First pre-dawn horizon micro-glow: a thin cool band at the limb,
          // warm-tinted core — the earliest sign of the coming sun. Directional
          // bias pushed right (sunDirection is +x/east) so the pre-sunrise hint
          // reads on the correct side, without yet being a full warm sunrise —
          // opacity/color stay mostly cool per spec ("无明显太阳圆盘").
          horizonGlow: {
            enabled: true,
            colorCore:  '#e8ecf0',
            colorMain:  '#9bb8cf',
            colorOuter: '#3a5a78',
            opacity: 0.045,
            blur: 24,
            scale: 1.24,
            innerStop: 0.806,
            coreStop:  0.838,
            midStop:   0.902,
            outerStop: 0.974,
            lightDirX: 66,
            lightDirY: 46,
            rim: {
              color: '#e6f1fb',
              strength: 0.18,
              halfWidth: 0.0036,
              blur: 1.1,
            },
          },
          // Daybase ocean grade: between deepNight's near-black blue-black and
          // earlyMorning's cool morning lift. Ocean begins to read blue, bathymetry
          // faintly visible, deep basins in a soft blue-black band.
          nightGrade: {
            daybaseMode: true,
            nightExposure:    0.060,
            nightSaturation:  0.55,
            nightGamma:       0.90,
            nightBlueBias:    0.030,
            nightGreenBias:   0.003,
            nightRedReduce:   0.022,
            oceanBlendStrength: 0.60,
            // R7 ocean-only blackness swap: dawn's ocean was reading darker than
            // deepNight's because the global mapColor/ambient multipliers crush
            // it ~0.6x. Gentle ocean-only counter-lift (darken 1.35→1.50, lift
            // floor 0.014→0.018) so the sea starts reading blue ahead of the
            // land, per the dawn signature above. Global params untouched.
            oceanDarken: 1.50,
            oceanContrast: 1.01,
            oceanSaturation: 0.58,
            oceanBlueBias: 0.010,
            oceanRedReduce: 0.045,
            oceanGreenReduce: 0.0,
            coastProtection: 0.72,
            tropicalDarken:      0.62,
            tropicalGreenReduce: 0.0,
            aridDarken:          0.58,
            aridWarmReduce:      0.25,
            iceNeutralize:       1.0,
            oceanLift: 0.018, oceanLiftTint: [0.14, 0.40, 0.74], oceanTeal: 0,
            landLift: 0.030, landGamma: 0.87, landStr: 0, landRedRed: 0.024, landGreenB: 0.050, landGlowStr: 0,
            cityLumLow:  0.013,
            cityLumHigh: 0.088,
          },
          // Thin, cool, low-opacity clouds — dawn haze just forming.
          // R10 morphology pass: softer edges (raised alphaLow, lowered
          // alphaPow), reduced opacity to kill the "pasted-on" feel,
          // ambient fill on the dark side, subtle rim glow, alpha
          // softening via mip-bias blend, and a tiny radius bump for
          // floating-above-the-atmosphere presence.
          clouds: {
            texture: 'fair_clouds_soft_8k.jpg',
            opacity: 0.13,
            color: '#e8eef3',
            alphaLow: 0.20,
            alphaHigh: 0.84,
            alphaPow: 1.05,
            oceanSuppress: 0.48,
            deepOceanSuppress: 0.35,
            shade: 0.38,
            ambient: 0.38,
            rim: 0.12,
            alphaSoftness: 0.25,
            mipBias: 1.5,
            radiusScale: 1.0035,
          },
          starSphereOpacity: 0.26,
          sunDirection: { x: 4, y: 1, z: 2 }, // pre-dawn eastern light, sun still low
        },
        sunrise: {
          // V4-2C: sun breaks the eastern horizon. Previously a bare v16 stub
          // (no rimGlow / horizonGlow / nightGrade at all) but its raw-Phong
          // real-lighting look was already correctly bright/well-exposed —
          // land should stay clearly visible here, not crushed toward black.
          // First pass wrongly routed this through daybaseMode:true (the
          // night-base exposure crush meant for near-zero-sunlight themes),
          // which flattened land to near-black. Reverted to daybaseMode:false
          // + dayOceanGrade (the same daytime-safe path morning/noon/afternoon/
          // goldenApproach use) so real Phong lighting keeps driving brightness.
          themeHour: 6.3,
          texture: {
            map: 'day',
            emissiveMap: 'night',
            mapColor: 0x96a6ae,
            // City lights fading out: dawn 0.18 → sunrise 0.06 → earlyMorning 0(off).
            emissiveColor: 0xffe3b0,
            emissiveIntensity: 0.06,
            nightBaseIntensity: 0.05,
          },
          material: {
            specular: 0x000102,
            shininess: 0.16,
          },
          // 3D fresnel shell disabled — Rim Overlay + Inner Horizon Veil (below)
          // now own the limb-glow job, same pattern as dawn/earlyMorning.
          atmosphere: {
            color: '#7ab6d8',
            colorOuter: '#5d86a8',
            radius: 2.04,
            opacity: 0.0,
            power: 12.5,
            powerOuter: 5.0,
            strengthOuter: 0.16,
          },
          // Right-side sunLobe — mirror of sunset's proven left-side structure,
          // strength scaled to ~75%, colors cooled toward morning light.
          // Sky stays deep cold blue, warmth concentrated at eastern limb.
          rimGlow: {
            outer: {
              color: '#9FB6C8', colorNear: '#FFE5BE', colorFar: '#263F58',
              coreStrength: 0.36, haloStrength: 0.16,
              width: 0.23, coreFraction: 0.30, tailPower: 3.0,
              corePower: 5.6, softComposite: true, rimOffsetY: 0.0,
            },
            inner: {
              color: '#F1D7B6', strength: 0.13,
              width: 0.09, falloff: 3.1,
            },
            sunLobe: {
              enabled: true,
              x: 0.96,
              y: 0.31,
              coreColor: '#FFF6E8',
              mainColor: '#E8C090',
              outerColor: '#5A80A0',
              strength: 0.83,
              width: 0.34,
              falloff: 3.2,
              rimBoost: 0.36,
              hStretch: 2.4,
              vCompress: 0.42,
              arcBand: {
                enabled: true,
                colorNear: '#E8C88A',
                colorMid: '#8A9AA5',
                colorFar: '#3A6080',
                strength: 0.26,
                width: 0.16,
                spread: 0.55,
                dirX: 0.88,
                dirFalloff: 3.0,
              },
              surfaceWarmth: {
                enabled: true,
                x: 0.92,
                y: 0.42,
                color: '#D4A870',
                strength: 0.17,
                width: 0.42,
                falloff: 2.4,
              },
            },
          },
          lighting: {
            ambient: 0.44,
            sun: 0.66,
            sunColor: 0xffd9aa,
            stars: 0.06,
            cityLightsOpacity: 0.05,
            cityLightClamp: 0.66,
          },
          // DOM horizonGlow — weak auxiliary only; primary sun via WebGL sunLobe
          horizonGlow: {
            enabled: true,
            colorCore:  '#FFE8CC',
            colorMain:  '#D4956A',
            colorOuter: '#2E5F7A',
            opacity: 0.03,
            blur: 16,
            scale: 0.55,
            innerStop: 0.00,
            coreStop:  0.06,
            midStop:   0.18,
            outerStop: 0.38,
            lightDirX: 84,
            lightDirY: 32,
            rim: {
              color: '#FFE8BE',
              strength: 0.10,
              halfWidth: 0.0032,
              blur: 1.3,
            },
          },
          // daybaseMode:false + dayOceanGrade:true — real daylight, ocean/land
          // graded via the daytime-safe standalone path (same mechanism
          // morning/noon/afternoon/goldenApproach use), not the night-base crush.
          // Note: oceanLiftTint is only consumed by the daybase (night) shader
          // path — the standalone day path hardcodes the 0.35/0.50/1.0 lift hue,
          // so the tint below is recorded intent, not yet live.
          nightGrade: {
            daybaseMode: false,
            dayOceanGrade: true,
            nightExposure: 0.078,
            nightSaturation: 0.70,
            nightGamma: 0.92,
            landLift: 0.016,
            landGamma: 0.90,
            landStr: 0.22,
            oceanBlendStrength: 0.62,
            oceanDarken: 0.52,
            oceanContrast: 1.02,
            oceanSaturation: 0.56,
            oceanBlueBias: 0.006,
            oceanRedReduce: 0.0,
            oceanGreenReduce: 0.0,
            coastProtection: 0.76,
            iceNeutralize: 1.0,
            oceanLift: 0.036,
            oceanLiftTint: [0.12, 0.32, 0.56],
            oceanTeal: 0,
            landRedRed: 0.0,
            landGreenB: 0.03,
            landGlowStr: 0,
          },
          clouds: {
            texture: 'africa_clouds_8k.jpg',
            opacity: 0.22,
            color: '#ffe9d2',
            alphaLow: 0.10,
            alphaHigh: 0.85,
            alphaPow: 1.5,
            oceanSuppress: 0.55,
            deepOceanSuppress: 0.35,
            shade: 0.5,
          },
          starSphereOpacity: 0.06,
          sunDirection: { x: 10, y: 0, z: 0 }, // eastern light: sun from +x (right side lit)
        },
        earlyMorning: {
          themeHour: 7.4,
          texture: {
            map: 'day',
            emissiveMap: null,
            mapColor: 0xffffff,
            emissiveColor: 0x000000,
            emissiveIntensity: 0,
          },
          material: {
            specular: 0x020407,
            shininess: 0.55,
          },
          atmosphere: {
            // Shell radius is earth r=2.0 * 1.02 — a skin-tight shell so the shader's
            // own N·V=0 silhouette stays pinned to earth's visible edge instead of
            // drifting into a separate ring floating in the sky (see devlog: a
            // radius of 2.36 pushed the silhouette far enough out, at this camera
            // distance/FOV, to visibly detach from the terrain edge). This shell is
            // the sole limb-glow source — the sky plane above is flat background only.
            color: '#f7feff',       // thin bright core, right at the limb
            colorOuter: '#9fd7ff',  // soft blue halo fading outward into space
            radius: 2.04,
            // Disabled by default (定版 2026-07-03) — the Rim Overlay + Inner
            // Horizon Veil post-scene layers now own the limb-glow job. Re-enable
            // via the Theme Tuner's Atmosphere > enabled checkbox to A/B compare.
            opacity: 0.0,
            power: 16.0,
            powerOuter: 5.2,
            strengthOuter: 0.18,
          },
          lighting: {
            ambient: 0.56,
            sun: 0.92,
            stars: 0,
            cityLightsOpacity: 0, // dead param — logging only
          },
          nightGrade: {
            daybaseMode: false,
            oceanBlendStrength: 0.36,
            oceanDarken: 0.79,
            oceanContrast: 1.11,
            oceanSaturation: 1.15,
            oceanBlueBias: 0.036,
            oceanRedReduce: 0.036,
            oceanGreenReduce: 0.014,
            coastProtection: 0.77,
            iceNeutralize: 1.0,
            oceanLift: 0.0,
            oceanTeal: 0,
            landLift: 0.020,
            landGamma: 0.89,
            landStr: 0.26,
            landRedRed: 0.024,
            landGreenB: 0.105,
            landGlowStr: 0,
          },
          horizonGlow: {
            enabled: false,
            colorCore:  '#edf8ff',
            colorMain:  '#c2dff5',
            colorOuter: '#6d97b8',
            opacity: 0,
            blur: 30,
            scale: 1.27,
            innerStop: 0.804,
            coreStop:  0.832,
            midStop:   0.900,
            outerStop: 0.974,
            lightDirX: 48,
            lightDirY: 43,
            rim: {
              color: '#eef8ff',
              strength: 0,
              halfWidth: 0.0024,
              blur: 2.2,
            },
          },
          // Thinner, cooler, softer clouds — 定版 2026-07-05. Object form (vs.
          // the plain-number form other themes use) lets this theme alone
          // carry a distinct color/alpha-curve/ocean-suppression without
          // touching the shared cloud shader's defaults for any other theme.
          clouds: {
            texture: 'n_amer_clouds_8k.jpg',
            opacity: 0.38,
            color: '#f4f8fa',
            alphaLow: 0.12,
            alphaHigh: 0.88,
            alphaPow: 1.55,
            oceanSuppress: 0.62,
            deepOceanSuppress: 0.42,
            // Internal light/shadow shading — thin/wispy cloud edges darken
            // toward gray, thick formations stay near full uCloudColor. This
            // is what gives volume instead of a flat sticker cutout now that
            // opacity is high enough to actually see the clouds clearly.
            shade: 0.5,
          },
          rimGlow: {
            outer: {
              color: '#BBD8E8', colorNear: '#E2F1F8', colorFar: '#6C88A2',
              coreStrength: 0.40, haloStrength: 0.20,
              width: 0.24, coreFraction: 0.31, tailPower: 2.9,
              corePower: 4.7, softComposite: true, rimOffsetY: 0.0,
            },
            inner: {
              color: '#D8EEF8', strength: 0.17,
              width: 0.11, falloff: 3.15,
            },
          },
          starSphereOpacity: 0,
          sunDirection: { x: 2, y: 3, z: 6 },
        },
        morning: {
          themeHour: 9.0,
          texture: {
            map: 'day',
            emissiveMap: null,
            mapColor: 0xFAFBFC,
            emissiveColor: 0x000000,
            emissiveIntensity: 0,
          },
          material: {
            specular: 0x020407,
            shininess: 0.55,
          },
          atmosphere: {
            color: '#f7feff',
            colorOuter: '#9fd7ff',
            radius: 2.04,
            opacity: 0.0,
            power: 16.0,
            powerOuter: 5.2,
            strengthOuter: 0.18,
          },
          // Same Rim Overlay structure as earlyMorning's baked-in defaults
          // (see applyRimGlowThemeConfig fallbacks), scaled down ~10% — a full
          // atmospheric limb, not a thin outline, so the four daytime modes
          // share one visual language.
          rimGlow: {
            outer: {
              color: '#C7DCE8', colorNear: '#DCEBF3', colorFar: '#7894AA',
              coreStrength: 0.32, haloStrength: 0.14,
              width: 0.24, coreFraction: 0.30, tailPower: 2.45,
              corePower: 5.0, softComposite: true, rimOffsetY: 0.0,
            },
            inner: {
              color: '#D8EEF8', strength: 0.12,
              width: 0.12, falloff: 3.0,
            },
          },
          lighting: {
            ambient: 0.76,
            sun: 1.14,
            sunColor: 0xfff8ea,
            stars: 0,
            cityLightsOpacity: 0,
          },
          nightGrade: {
            daybaseMode: false,
            dayOceanGrade: true,
            oceanBlendStrength: 0.45,
            oceanDarken: 0.86,
            oceanContrast: 1.05,
            oceanSaturation: 0.80,
            oceanBlueBias: 0.0,
            oceanRedReduce: 0.0,
            oceanGreenReduce: 0.0,
            coastProtection: 0.72,
            iceNeutralize: 1.0,
            oceanLift: 0.0,
            oceanTeal: 0,
            landLift: 0.016,
            landGamma: 0.92,
            landStr: 0.26,
            landRedRed: 0.024,
            landGreenB: 0.105,
            landGlowStr: 0,
          },
          horizonGlow: {
            enabled: false,
            colorCore:  '#edf8ff',
            colorMain:  '#c2dff5',
            colorOuter: '#6d97b8',
            opacity: 0,
            blur: 30,
            scale: 1.27,
            innerStop: 0.804,
            coreStop:  0.832,
            midStop:   0.900,
            outerStop: 0.974,
            lightDirX: 48,
            lightDirY: 43,
            rim: {
              color: '#eef8ff',
              strength: 0,
              halfWidth: 0.0024,
              blur: 2.2,
            },
          },
          clouds: {
            texture: 'fair_clouds_8k.jpg',
            opacity: 0.30,
            color: '#f4f8fa',
            alphaLow: 0.12,
            alphaHigh: 0.88,
            alphaPow: 1.55,
            oceanSuppress: 0.62,
            deepOceanSuppress: 0.42,
            shade: 0.5,
          },
          starSphereOpacity: 0,
          sunDirection: { x: 2, y: 3, z: 6 },
        },
        noon: {
          themeHour: 12.5,
          texture: {
            map: 'day',
            emissiveMap: null,
            mapColor: 0xFFFFFF,
            emissiveColor: 0x000000,
            emissiveIntensity: 0,
          },
          material: {
            specular: 0x020407,
            shininess: 0.55,
          },
          atmosphere: {
            color: '#f7feff',
            colorOuter: '#9fd7ff',
            radius: 2.04,
            opacity: 0.0,
            power: 16.0,
            powerOuter: 5.2,
            strengthOuter: 0.18,
          },
          // Tightest, cleanest rim of the four daytime modes — high sun thins
          // the visible scattering band, but it's still the same full
          // atmospheric structure as earlyMorning, not an outline.
          rimGlow: {
            outer: {
              color: '#C7DCE8', colorNear: '#D9E8F1', colorFar: '#708BA3',
              coreStrength: 0.35, haloStrength: 0.16,
              width: 0.24, coreFraction: 0.28, tailPower: 2.5,
              corePower: 4.5, softComposite: true, rimOffsetY: 0.0,
            },
            inner: {
              color: '#D8EEF8', strength: 0.14,
              width: 0.12, falloff: 3.0,
            },
          },
          lighting: {
            ambient: 0.98,
            sun: 1.46,
            sunColor: 0xfffaf2,
            stars: 0,
            cityLightsOpacity: 0,
          },
          nightGrade: {
            daybaseMode: false,
            dayOceanGrade: true,
            oceanBlendStrength: 0.35,
            oceanDarken: 1.10,
            oceanContrast: 1.03,
            oceanSaturation: 0.88,
            oceanBlueBias: 0.0,
            oceanRedReduce: 0.0,
            oceanGreenReduce: 0.0,
            coastProtection: 0.75,
            iceNeutralize: 1.0,
            oceanLift: 0.0,
            oceanTeal: 0,
            landLift: 0.0,
            landGamma: 1.00,
            landStr: 0.0,
            landRedRed: 0.024,
            landGreenB: 0.105,
            landGlowStr: 0,
          },
          horizonGlow: {
            enabled: false,
            colorCore:  '#edf8ff',
            colorMain:  '#c2dff5',
            colorOuter: '#6d97b8',
            opacity: 0,
            blur: 30,
            scale: 1.27,
            innerStop: 0.804,
            coreStop:  0.832,
            midStop:   0.900,
            outerStop: 0.974,
            lightDirX: 48,
            lightDirY: 43,
            rim: {
              color: '#eef8ff',
              strength: 0,
              halfWidth: 0.0024,
              blur: 2.2,
            },
          },
          clouds: {
            texture: 'se_asia_clouds_8k.jpg',
            opacity: 0.10,
            color: '#f4f8fa',
            alphaLow: 0.12,
            alphaHigh: 0.88,
            alphaPow: 1.55,
            oceanSuppress: 0.62,
            deepOceanSuppress: 0.42,
            shade: 0.5,
          },
          starSphereOpacity: 0,
          sunDirection: { x: 2, y: 3, z: 6 },
        },
        afternoon: {
          themeHour: 16.0,
          texture: {
            map: 'day',
            emissiveMap: null,
            mapColor: 0xF3ECDC,
            emissiveColor: 0x000000,
            emissiveIntensity: 0,
          },
          material: {
            specular: 0x020407,
            shininess: 0.55,
          },
          atmosphere: {
            color: '#f7feff',
            colorOuter: '#9fd7ff',
            radius: 2.04,
            opacity: 0.0,
            power: 16.0,
            powerOuter: 5.2,
            strengthOuter: 0.18,
          },
          // Same atmospheric rim structure, softened and drifted warm-gray —
          // light fading off its noon peak, still clearly daytime (not dusk).
          rimGlow: {
            outer: {
              color: '#C9DCE7', colorNear: '#DCE9F0', colorFar: '#7A91A6',
              coreStrength: 0.34, haloStrength: 0.15,
              width: 0.24, coreFraction: 0.29, tailPower: 2.45,
              corePower: 5.0, softComposite: true, rimOffsetY: 0.0,
            },
            inner: {
              color: '#D9EDF6', strength: 0.13,
              width: 0.12, falloff: 3.0,
            },
          },
          lighting: {
            ambient: 0.58,
            sun: 0.92,
            sunColor: 0xffedd2,
            stars: 0,
            cityLightsOpacity: 0,
          },
          nightGrade: {
            daybaseMode: false,
            dayOceanGrade: true,
            oceanBlendStrength: 0.55,
            oceanDarken: 0.70,
            oceanContrast: 1.06,
            oceanSaturation: 0.68,
            oceanBlueBias: 0.0,
            oceanRedReduce: 0.0,
            oceanGreenReduce: 0.015,
            coastProtection: 0.72,
            iceNeutralize: 1.0,
            oceanLift: 0.0,
            oceanTeal: 0,
            landLift: 0.012,
            landGamma: 0.97,
            landStr: 0.35,
            landRedRed: -0.030,
            landGreenB: 0.02,
            landGlowStr: 0,
          },
          horizonGlow: {
            enabled: false,
            colorCore:  '#edf8ff',
            colorMain:  '#c2dff5',
            colorOuter: '#6d97b8',
            opacity: 0,
            blur: 30,
            scale: 1.27,
            innerStop: 0.804,
            coreStop:  0.832,
            midStop:   0.900,
            outerStop: 0.974,
            lightDirX: 48,
            lightDirY: 43,
            rim: {
              color: '#eef8ff',
              strength: 0,
              halfWidth: 0.0024,
              blur: 2.2,
            },
          },
          clouds: {
            texture: 'australia_clouds_8k.jpg',
            opacity: 0.18,
            color: '#f4f8fa',
            alphaLow: 0.12,
            alphaHigh: 0.88,
            alphaPow: 1.55,
            oceanSuppress: 0.62,
            deepOceanSuppress: 0.42,
            shade: 0.5,
          },
          starSphereOpacity: 0,
          sunDirection: { x: 2, y: 3, z: 6 },
        },
        goldenApproach: {
          // V6: Rebased on afternoon (NOT sunrise). Colder blue-grey sky,
          // slightly darker & warmer than afternoon, subtle left-side
          // warm directional sunLobe + arcBand + surfaceWarmth — 暮前.
          themeHour: 16.5,
          texture: {
            map: 'day',
            emissiveMap: 'night',
            mapColor: 0xF4EFE5,
            emissiveColor: 0xFFC477,
            emissiveIntensity: 0.07,
            nightBaseIntensity: 0.05,
          },
          material: {
            specular: 0x020407,
            shininess: 0.50,
          },
          // 3D fresnel shell disabled — Rim Overlay + sky plane own the limb job.
          atmosphere: {
            color: '#f7feff',
            colorOuter: '#9fd7ff',
            radius: 2.04,
            opacity: 0.0,
            power: 16.0,
            powerOuter: 5.2,
            strengthOuter: 0.18,
          },
          rimGlow: {
            outer: {
              color: '#B7C6D2', colorNear: '#EED9B8', colorFar: '#4E647A',
              coreStrength: 0.37, haloStrength: 0.17,
              width: 0.24, coreFraction: 0.28, tailPower: 3.0,
              corePower: 5.4, softComposite: true, rimOffsetY: 0.0,
            },
            inner: {
              color: '#E8D2B2', strength: 0.14,
              width: 0.10, falloff: 3.15,
            },
            sunLobe: {
              enabled: true,
              x: -0.04,
              y: 0.32,
              coreColor: '#FFE8BE',
              mainColor: '#E7A86A',
              outerColor: '#4E7188',
              strength: 1.05,
              width: 0.34,
              falloff: 3.0,
              rimBoost: 0.32,
              hStretch: 2.6,
              vCompress: 0.45,
              arcBand: {
                enabled: true,
                colorNear: '#E2A76A',
                colorMid: '#B0A28A',
                colorFar: '#768E9E',
                strength: 0.18,
                width: 0.12,
                spread: 0.55,
                dirX: 0.12,
                dirFalloff: 3.0,
              },
              surfaceWarmth: {
                enabled: true,
                x: 0.08,
                y: 0.42,
                color: '#DFA15F',
                strength: 0.10,
                width: 0.42,
                falloff: 2.6,
              },
            },
          },
          lighting: {
            ambient: 0.54,
            sun: 0.84,
            sunColor: 0xffd6a3,
            stars: 0.02,
            cityLightsOpacity: 0.07,
            cityLightClamp: 0.72,
          },
          // DOM horizonGlow disabled — all glow via WebGL sunLobe/arcBand
          horizonGlow: {
            enabled: false,
            colorCore:  '#edf8ff',
            colorMain:  '#c2dff5',
            colorOuter: '#6d97b8',
            opacity: 0,
            blur: 30,
            scale: 1.27,
            innerStop: 0.804,
            coreStop:  0.832,
            midStop:   0.900,
            outerStop: 0.974,
            lightDirX: 48,
            lightDirY: 43,
            rim: {
              color: '#eef8ff',
              strength: 0,
              halfWidth: 0.0024,
              blur: 2.2,
            },
          },
          nightGrade: {
            daybaseMode: false,
            dayOceanGrade: true,
            nightExposure: 0.086,
            nightSaturation: 0.74,
            nightGamma: 0.92,
            landLift: 0.014,
            landGamma: 0.91,
            landStr: 0.30,
            oceanBlendStrength: 0.38,
            oceanDarken: 0.66,
            oceanContrast: 1.07,
            oceanSaturation: 0.70,
            oceanBlueBias: 0.002,
            oceanRedReduce: 0.0,
            oceanGreenReduce: 0.0,
            coastProtection: 0.76,
            iceNeutralize: 1.0,
            oceanLift: 0.0,
            oceanTeal: 0,
            landRedRed: -0.020,
            landGreenB: 0.02,
            landGlowStr: 0,
          },
          clouds: {
            texture: 'storm_clouds_crisp_8k.jpg',
            opacity: 0.16,
            color: '#f0f5f2',
            alphaLow: 0.10,
            alphaHigh: 0.86,
            alphaPow: 1.55,
            oceanSuppress: 0.60,
            deepOceanSuppress: 0.40,
            shade: 0.5,
          },
          starSphereOpacity: 0.02,
          sunDirection: { x: -10, y: 0, z: 0 }, // western light: sun from -x (left side lit)
        },
        sunset: {
          // V4-2C: sun low on the western horizon. Previously a bare stub
          // (flat mapColor tint, no rimGlow/horizonGlow/nightGrade). First
          // pass wrongly routed this through daybaseMode:true (evening's
          // night-base regime), which crushed land toward black the same way
          // it did on sunrise (see sunrise's comment) — the original raw-Phong
          // look had land still clearly visible/warm, just dimmer than
          // goldenApproach. Reverted to daybaseMode:false + dayOceanGrade,
          // darker/warmer than goldenApproach via lower ambient/sun and a
          // deeper oceanDarken, with city lights layered on top via emissive.
          themeHour: 18.2,
          texture: {
            map: 'day',
            emissiveMap: 'night',
            mapColor: 0xF2E0C8,
            emissiveColor: 0xFFB15C,
            emissiveIntensity: 0.24,
          },
          material: {
            specular: 0x000102,
            shininess: 0.20,
          },
          atmosphere: {
            color: '#628fb5',
            colorOuter: '#7a4a2a',
            radius: 2.04,
            opacity: 0.0,
            power: 12.5,
            powerOuter: 5.0,
            strengthOuter: 0.16,
          },
          // Left-side sunLobe mirroring sunrise structure, stronger + lower
          // on the horizon than goldenApproach. Sky stays deep blue, warmth
          // concentrated at the western limb via WebGL glow only.
          rimGlow: {
            outer: {
              color: '#B8B6A8', colorNear: '#FFD2A2', colorFar: '#33465B',
              coreStrength: 0.43, haloStrength: 0.19,
              width: 0.24, coreFraction: 0.28, tailPower: 3.15,
              corePower: 5.8, softComposite: true, rimOffsetY: 0.0,
            },
            inner: {
              color: '#EBC4A0', strength: 0.16,
              width: 0.10, falloff: 3.2,
            },
            sunLobe: {
              enabled: true,
              x: -0.04,
              y: 0.31,
              coreColor: '#FFF1C8',
              mainColor: '#F0A95E',
              outerColor: '#3E6880',
              strength: 1.10,
              width: 0.34,
              falloff: 3.2,
              rimBoost: 0.48,
              hStretch: 2.4,
              vCompress: 0.42,
              arcBand: {
                enabled: true,
                colorNear: '#F2B36A',
                colorMid: '#7A8A90',
                colorFar: '#285C76',
                strength: 0.34,
                width: 0.16,
                spread: 0.55,
                dirX: 0.12,
                dirFalloff: 3.0,
              },
              surfaceWarmth: {
                enabled: true,
                x: 0.08,
                y: 0.42,
                color: '#E6A15A',
                strength: 0.22,
                width: 0.42,
                falloff: 2.4,
              },
            },
          },
          lighting: {
            ambient: 0.34,
            sun: 0.52,
            sunColor: 0xffc488,
            stars: 0.18,
            cityLightsOpacity: 0.26,
            cityLightClamp: 0.72,
          },
          // DOM horizonGlow disabled — all sun warmth via WebGL sunLobe/arcBand
          horizonGlow: {
            enabled: false,
            colorCore:  '#ffdcae',
            colorMain:  '#ff8438',
            colorOuter: '#3a2010',
            opacity: 0,
            blur: 22,
            scale: 1.26,
            innerStop: 0.806,
            coreStop:  0.838,
            midStop:   0.902,
            outerStop: 0.974,
            lightDirX: 14,
            lightDirY: 50,
            rim: {
              color: '#ffcf96',
              strength: 0,
              halfWidth: 0.0034,
              blur: 1.2,
            },
          },
          // daybaseMode:false + dayOceanGrade:true — daytime-safe path,
          // darker than goldenApproach, ocean deepened, city lights visible.
          nightGrade: {
            daybaseMode: false,
            dayOceanGrade: true,
            nightExposure: 0.050,
            nightSaturation: 0.56,
            nightGamma: 0.88,
            nightBlueBias: 0.018,
            nightGreenBias: 0.002,
            nightRedReduce: 0.010,
            landLift: 0.010,
            landGamma: 0.92,
            landStr: 0.38,
            landGlowStr: 0.04,
            oceanBlendStrength: 0.54,
            oceanDarken: 0.62,
            oceanContrast: 1.04,
            oceanSaturation: 0.62,
            oceanBlueBias: 0.0,
            oceanRedReduce: 0.0,
            oceanGreenReduce: 0.0,
            oceanLift: 0.006,
            oceanLiftTint: [0.10, 0.28, 0.42],
            coastProtection: 0.72,
            iceNeutralize: 1.0,
            oceanTeal: 0,
            landRedRed: -0.010,
            landGreenB: 0.0,
          },
          clouds: {
            texture: 'europe_clouds_8k.jpg',
            opacity: 0.18,
            color: '#ffcf9e',
            alphaLow: 0.08,
            alphaHigh: 0.85,
            alphaPow: 1.6,
            oceanSuppress: 0.65,
            deepOceanSuppress: 0.45,
            shade: 0.55,
            ambient: 0.28,
            rim: 0.35,
          },
          starSphereOpacity: 0.10,
          sunDirection: { x: -10, y: 0, z: 0 }, // western light: sun from -x (left side lit)
        },
        evening: {
          themeHour: 20.2,
          texture: {
            map: 'day',
            emissiveMap: 'night',
            mapColor: 0xFFFFFF,
            emissiveColor: 0xFFC477,
            emissiveIntensity: 0.68,
          },
          material: { specular: 0x000001, shininess: 0.08 },
          atmosphere: { color: '#d8f4ff', opacity: 0.0, power: 14.0 },
          rimGlow: {
            outer: {
              color: '#93BDD8', colorNear: '#D8EEF8', colorFar: '#2F4B64',
              // Broad, low-energy air mass instead of a crisp neon ring.
              coreStrength: 0.18, haloStrength: 0.06,
              width: 0.16, coreFraction: 0.22, tailPower: 2.6,
              corePower: 7.0, softComposite: true, rimOffsetY: 0.0,
            },
            inner: {
              color: '#9EBBC9', strength: 0.035,
              width: 0.045, falloff: 3.8,
            },
          },
          lighting: { ambient: 1.0, sun: 0.0, stars: 0.38, cityLightsOpacity: 0.36, cityLightClamp: 0.74 },
          horizonGlow: {
            enabled: false,
            colorCore:  '#cce8f8',
            colorMain:  '#80a8c0',
            colorOuter: '#446888',
            opacity: 0.042,
            blur: 22,
            scale: 1.26,
            innerStop: 0.808,
            coreStop:  0.840,
            midStop:   0.905,
            outerStop: 0.975,
            lightDirX: 47,
            lightDirY: 44,
            rim: {
              color: '#dcf5ff',
              strength: 0.28,
              halfWidth: 0.004,
              blur: 1.0,
            },
          },
          nightGrade: {
            daybaseMode: true,
            nightExposure:    0.078,
            nightSaturation:  0.58,
            nightGamma:       0.94,
            nightBlueBias:    0.035,
            nightGreenBias:   0.004,
            nightRedReduce:   0.018,
            oceanBlendStrength: 0.62,
            oceanDarken: 1.28,
            oceanContrast: 1.01,
            oceanSaturation: 0.56,
            oceanBlueBias: 0.007,
            oceanRedReduce: 0.05,
            oceanGreenReduce: 0.0,
            coastProtection: 0.70,
            tropicalDarken:      0.62,
            tropicalGreenReduce: 0.0,
            aridDarken:          0.58,
            aridWarmReduce:      0.25,
            iceNeutralize:       1.0,
            oceanLift: 0.012, oceanLiftTint: [0.12, 0.38, 0.68], oceanTeal: 0,
            landLift: 0.035, landGamma: 0.85, landStr: 0, landRedRed: 0.025, landGreenB: 0.045, landGlowStr: 0,
            cityLumLow:  0.014,
            cityLumHigh: 0.095,
          },
          clouds: {
            // High-pass cloud mask: reject the broad gray film and retain
            // only localized bright formations, closer to real satellite cloud
            // masses than a translucent global overlay.
            opacity: 0.18,
            texture: 'clouds_live_8k.jpg',
            alphaLow: 0.20,
            alphaHigh: 0.68,
            alphaPow: 1.15,
            detailMix: 0.42,
            detailContrast: 5.0,
            color: '#edf5f8',
            shade: 0.24,
            // Keep the cloud albedo visible on the night-facing hemisphere.
            // Without an ambient floor, the directional cloud light reaches 0
            // there even when alpha is non-zero, producing invisible black clouds.
            ambient: 0.52,
          },
          starSphereOpacity: 0.18,
        },
        lateEvening: {
          themeHour: 21.0,
          texture: {
            map: 'day',
            emissiveMap: 'night',
            mapColor: 0xFFFFFF,
            emissiveColor: 0xFFB85C,
            emissiveIntensity: 0.64,
          },
          material: { specular: 0x000001, shininess: 0.08 },
          atmosphere: { color: '#d8f4ff', opacity: 0.0, power: 14.0 },
          rimGlow: {
            outer: {
              color: '#86B4D0', colorNear: '#D4ECF8', colorFar: '#253F58',
              coreStrength: 0.15, haloStrength: 0.05,
              width: 0.14, coreFraction: 0.21, tailPower: 2.8,
              corePower: 7.3, softComposite: true, rimOffsetY: 0.0,
            },
            inner: {
              color: '#8FAEBD', strength: 0.025,
              width: 0.040, falloff: 4.0,
            },
          },
          lighting: { ambient: 1.0, sun: 0.0, stars: 0.66, cityLightsOpacity: 0.42, cityLightClamp: 0.70 },
          horizonGlow: {
            enabled: false,
            colorCore:  '#cce8f8',
            colorMain:  '#80a8c0',
            colorOuter: '#446888',
            opacity: 0.042,
            blur: 22,
            scale: 1.26,
            innerStop: 0.808,
            coreStop:  0.840,
            midStop:   0.905,
            outerStop: 0.975,
            lightDirX: 47,
            lightDirY: 44,
            rim: {
              color: '#dcf5ff',
              strength: 0.28,
              halfWidth: 0.004,
              blur: 1.0,
            },
          },
          nightGrade: {
            daybaseMode: true,
            nightExposure:    0.060,
            nightSaturation:  0.55,
            nightGamma:       0.88,
            nightBlueBias:    0.031,
            nightGreenBias:   0.003,
            nightRedReduce:   0.022,
            oceanBlendStrength: 0.66,
            oceanDarken: 1.55,
            oceanContrast: 1.01,
            oceanSaturation: 0.55,
            oceanBlueBias: 0.006,
            oceanRedReduce: 0.05,
            oceanGreenReduce: 0.0,
            coastProtection: 0.69,
            tropicalDarken:      0.62,
            tropicalGreenReduce: 0.0,
            aridDarken:          0.58,
            aridWarmReduce:      0.25,
            iceNeutralize:       1.0,
            oceanLift: 0.011, oceanLiftTint: [0.13, 0.39, 0.70], oceanTeal: 0,
            landLift: 0.035, landGamma: 0.85, landStr: 0, landRedRed: 0.025, landGreenB: 0.045, landGlowStr: 0,
            cityLumLow:  0.011,
            cityLumHigh: 0.086,
          },
          clouds: {
            opacity: 0.15,
            texture: 'clouds_live_8k.jpg',
            alphaLow: 0.23,
            alphaHigh: 0.70,
            alphaPow: 1.20,
            detailMix: 0.45,
            detailContrast: 5.0,
            color: '#e7f0f4',
            shade: 0.28,
            ambient: 0.48,
          },
          starSphereOpacity: 0.34,
        },
        deepNight: {
          themeHour: 22.5,
          texture: {
            map: 'day',
            emissiveMap: 'night',
            mapColor: 0xFFFFFF,
            // Golden filament look (ref: ISS night photo): bright white-gold
            // metro cores fading to amber suburbs. Brightness gradient comes
            // from the raised cityLightClamp below — a low clamp flattens all
            // cities to one pale beige tone regardless of intensity.
            emissiveColor: 0xFFA22E,
            emissiveIntensity: 0.78,
          },
          material: { specular: 0x000001, shininess: 0.08 },
          // 3D Fresnel limb (AdditiveBlending): light adds directly to canvas at the limb.
          // With additive blending, opacity=0.24 means the peak limb contribution is +0.24×color
          // added to whatever is behind — true glow, not a translucent color overlay.
          // power=10 keeps the ring thin (falls to ~3% at 30° from limb vs Earth's face).
          atmosphere: { color: '#d8f4ff', opacity: 0.0, power: 14.0 },
          // atmosphere2 intentionally omitted → hidden (avoids double-ring artifact).
          // Screen-space Rim Overlay + Inner Horizon Veil — saturated electric
          // blue arc (ref image): bright cyan-white right at the limb, broad
          // rich-blue halo bleeding upward into the star field.
          rimGlow: {
            outer: {
              color: '#80B2D2', colorNear: '#D8F0FF', colorFar: '#1D364F',
              coreStrength: 0.13, haloStrength: 0.045,
              width: 0.13, coreFraction: 0.20, tailPower: 3.0,
              corePower: 7.6, softComposite: true, rimOffsetY: 0.0,
            },
            inner: {
              color: '#809EAF', strength: 0.018,
              width: 0.035, falloff: 4.2,
            },
          },
          // cityLightClamp 0.92 → 0.75 → 0.68: Reinhard ceiling tightened to reduce metro bloom spread.
          // Lower clamp compresses the brightest cores, keeping city lights point-like rather than haze.
          lighting: { ambient: 1.0, sun: 0.0, stars: 0.82, cityLightsOpacity: 0.45, cityLightClamp: 0.66 },
          horizonGlow: {
            enabled: false,
            // Outer haze: only in space outside Earth's edge (innerStop × scale > 1.0).
            // r_x/r_y now correctly = Earth's projected radius (EARTH_R = 2.0 world units).
            // 3D Fresnel (AdditiveBlending) handles the thin rim glow; CSS haze = ambient air only.
            colorCore:  '#cce8f8',
            colorMain:  '#80a8c0',
            colorOuter: '#446888',
            opacity: 0.042,
            blur: 22,
            scale: 1.26,        // 1.26 keeps haze tight — 26% beyond Earth's edge in space
            innerStop: 0.808,   // 0.808 × 1.26 = 1.018r → transparent hole just outside Earth
            coreStop:  0.840,
            midStop:   0.905,
            outerStop: 0.975,
            // P4: slight directionality — upper-left limb slightly brighter (natural limb scattering)
            lightDirX: 47,
            lightDirY: 44,
            // CSS rim: secondary accent at the projected Earth edge; primary glow is 3D Fresnel.
            rim: {
              color: '#dcf5ff',
              strength: 0.28,
              halfWidth: 0.004,
              blur: 1.0,
            },
          },
          nightGrade: {
            daybaseMode: true,
            // Land gray-warm base (2026-07-08 r3): blue/green bias reduced,
            // exposure + gamma lifted slightly, red reduction eased.
            // Goal: low-saturation dark gray-green/brown, not black-green sludge.
            nightExposure:    0.050,
            nightSaturation:  0.52,
            nightGamma:       0.86,
            nightBlueBias:    0.028,
            nightGreenBias:   0.002,
            nightRedReduce:   0.024,
            // Blend 0.45 → 0.9: at 0.45 the ocean was 55% raw night-base
            // (near-black at exposure 0.044) — the graded tone barely showed
            // and the ocean read as one flat black mass. Letting the graded
            // tone dominate reveals the day-texture bathymetry (continental
            // shelves, deep basins) as natural depth variation.
            oceanBlendStrength: 0.60,
            // Blend 0.60 (2026-07-09 R6 B-candidate): lowered from 0.69 to reduce
            // oceanTone grade coverage, letting raw source + nightBase carry more
            // of the final ocean color. Works with oceanRaw to hit deep blue-black.
            // R7 ocean-only blackness swap: dawn's blacker ocean comes from its
            // global mapColor (~0.3x) + ambient 0.62 multipliers, which are
            // off-limits here — translate that ~0.6x into the ocean-only path
            // instead: oceanDarken 1.75→1.10 (main knob), lift floor halved,
            // raw source darkened. oceanRawMix stays at 0.30 — the raw layer is
            // the darkest component, reducing it would brighten the ocean.
            oceanDarken: 1.10,
            oceanContrast: 1.01,
            oceanSaturation: 0.54,
            oceanBlueBias: 0.005,
            oceanRedReduce: 0.05,
            oceanGreenReduce: 0.0,
            coastProtection: 0.68,
            // R5 deepNight black-ocean raw source — B candidate
            oceanRawMix: 0.30,
            oceanRawExposure: 0.026,
            oceanRawBlueKeep: 0.32,
            // Surface-type suppression: tropical green + arid/highland
            tropicalDarken:      0.62,
            tropicalGreenReduce: 0.0,
            aridDarken:          0.58,
            aridWarmReduce:      0.25,
            iceNeutralize:       1.0,
            // oceanDarken > 1 compensates for nightExposure crush on ocean base.
            // oceanLift adds a flat tinted floor so DEEP water reads as
            // blue-black instead of pure black — without it the bathymetry
            // grade only brightens shelves, leaving a harsh shelf/basin step.
            // oceanLiftTint overrides the default warm ratio (0.35/0.50/1.0)
            // with a cold one so deep basins land in the #010713–#031426
            // blue-black band instead of drifting toward slate grey.
            oceanLift: 0.005, oceanLiftTint: [0.13, 0.39, 0.72], oceanTeal: 0,
            // Land minor assist: very light lift only
            landLift: 0.035, landGamma: 0.85, landStr: 0, landRedRed: 0.025, landGreenB: 0.045, landGlowStr: 0,
            // Wider city mask than the old 0.020/0.082: mid-size cities join
            // the filament network instead of only major metros surviving.
            cityLumLow:  0.016,
            cityLumHigh: 0.092,
          },
          clouds: {
            opacity: 0.13,
            texture: 'clouds_live_8k.jpg',
            alphaLow: 0.26,
            alphaHigh: 0.72,
            alphaPow: 1.25,
            detailMix: 0.48,
            detailContrast: 5.0,
            color: '#dfeaf0',
            shade: 0.32,
            ambient: 0.44,
          },
          starSphereOpacity: 0.45,
        },
        night: {
          themeHour: 22.5,
          texture: {
            map: 'day',
            emissiveMap: 'night',
            mapColor: 0x221809,  // warm dark brown, slightly brighter than deepNight
            emissiveColor: 0xffc86e,
            emissiveIntensity: 2.0,
          },
          material: {
            specular: 0x05070a,
            shininess: 1,
          },
          atmosphere: {
            color: '#0f0d0b',   // near-neutral warm dark
            // Rim Overlay owns the normal home-view atmosphere for night;
            // keep the legacy 3D shell only for audit shell fallback.
            opacity: 0.0,
            power: 6.0,
          },
          rimGlow: {
            outer: {
              color: '#6D8796', colorNear: '#B9CBD2', colorFar: '#182A35',
              coreStrength: 0.10, haloStrength: 0.035,
              width: 0.12, coreFraction: 0.19, tailPower: 3.2,
              corePower: 7.8, softComposite: true, rimOffsetY: 0.0,
            },
            inner: {
              color: '#718A96', strength: 0.012,
              width: 0.030, falloff: 4.4,
            },
          },
          lighting: {
            ambient: 0.058,
            sun: 0.03,
            stars: 0.78,
            cityLightsOpacity: 0.58, // dead param — logging only; use texture.emissiveIntensity for city light strength
          },
          clouds: {
            opacity: 0.11,
            texture: 'clouds_live_8k.jpg',
            alphaLow: 0.29,
            alphaHigh: 0.74,
            alphaPow: 1.30,
            detailMix: 0.50,
            detailContrast: 5.0,
            color: '#d6e3ea',
            shade: 0.36,
            ambient: 0.40,
          },
          starSphereOpacity: 0.22,
        },
      }
      const AUDIT_LIGHTING_CONFIG = {
        themeHour: 13,
        texture: {
          map: 'day',
          emissiveMap: null,
          mapColor: 0xffffff,
          emissiveColor: 0x000000,
          emissiveIntensity: 0,
        },
        material: {
          specular: 0x05080c,
          shininess: 45,
        },
        atmosphere: {
          color: '#b0d9ed',
          opacity: 0.045,
        },
        lighting: {
          ambient: 0.68,
          sun: 0.72,
          stars: 0,
          cityLightsOpacity: 0,
        },
      }
      let auditLightingMode = false
      let _sunDirectionOverride = null // set per-theme via config.sunDirection; null = use real J2000 solar position

      function getThemeVisualConfig(themeKey) {
        if (auditLightingMode) return AUDIT_LIGHTING_CONFIG
        return (
          THEME_VISUAL_CONFIG[themeKey]
          || THEME_VISUAL_CONFIG[currentTheme]
          || THEME_VISUAL_CONFIG[pendingTheme]
          || THEME_VISUAL_CONFIG.night
        )
      }

      function getTargetOrientation(targetDirOverride = null) {
        const vs = window.__rodioVisualState || {}
        const lon = normalizeLon(
          Number.isFinite(vs.lon) ? vs.lon : 121.4737
        )
        const lat = clamp(
          Number.isFinite(vs.lat) ? vs.lat : 31.2304,
          -80,
          80
        )
        const targetPoint = lonLatToVector3(lon, lat, 1).normalize()
        const sourceNorth = lonLatToNorthTangent(lon, lat)

        const targetNormal = (targetDirOverride || visualTargetDir).clone().normalize()

        const screenUp = new THREE.Vector3(0, 1, 0)
        let targetNorth = screenUp.clone().projectOnPlane(targetNormal)

        if (targetNorth.lengthSq() < 1e-6) {
          targetNorth = new THREE.Vector3(0, 0, 1).projectOnPlane(targetNormal)
        }

        targetNorth.normalize()

        return quaternionFromBasis(
          targetPoint,
          sourceNorth,
          targetNormal,
          targetNorth
        )
      }

      let currentTheme = null
      function resolveInitialPendingTheme() {
        // Do NOT read window.__rodioVisualState.themeKey here — it always starts as
        // 'night' (the index.html default) and would override the time-based guess.
        // External callers update pendingTheme later via setTimeOfDay().
        const h = new Date().getHours()
        if (h >= 5 && h < 8) return 'sunrise'
        if (h >= 8 && h < 11) return 'morning'
        if (h >= 11 && h < 15) return 'noon'
        if (h >= 15 && h < 17) return 'afternoon'
        if (h >= 17 && h < 20) return 'sunset'
        if (h >= 20 && h < 23) return 'evening'
        return 'deepNight'
      }
      let pendingTheme = resolveInitialPendingTheme()
      let lastThemeAuditSignature = null

      function getRequiredTextures(themeKey) {
        const config = getThemeVisualConfig(themeKey)
        if (!config) return []

        const required = new Set()
        if (config.texture.map === 'day') required.add('day')
        if (config.texture.map === 'night') required.add('night')
        if (config.texture.emissiveMap === 'day') required.add('day')
        if (config.texture.emissiveMap === 'night') required.add('night')
        return Array.from(required)
      }

      function getRevealTextures(themeKey) {
        const required = new Set(getRequiredTextures(themeKey))
        const config = getThemeVisualConfig(themeKey)
        if (!config) return Array.from(required)

        // Mixed day/night themes should not reveal until the night base is ready.
        // This keeps dawn/sunrise/sunset/earlyMorning from exposing a partial state
        // where only the day layer is visible during startup.
        if (config.texture.emissiveMap === 'night') {
          required.add('night')
        }

        return Array.from(required)
      }

      function areRequiredTexturesReady(themeKey) {
        const required = getRequiredTextures(themeKey)
        if (!required.length) return true

        for (const key of required) {
          if (key === 'day' && !dayTexture) return false
          if (key === 'night' && !nightTexture) return false
        }
        return true
      }

      function areRevealTexturesReady(themeKey) {
        const required = getRevealTextures(themeKey)
        if (!required.length) return true

        for (const key of required) {
          if (key === 'day' && !dayTexture) return false
          if (key === 'night' && !nightTexture) return false
        }
        return true
      }

      function getMissingTextures(requiredTextures) {
        return requiredTextures.filter((key) => {
          if (key === 'day') return !dayTexture
          if (key === 'night') return !nightTexture
          return true
        })
      }

      function getMapMode(config) {
        if (config.texture.map === 'day') return 'dayTexture'
        if (config.texture.map === null) return 'null'
        return 'unknown'
      }

      function getEmissiveMode(config) {
        if (config.texture.emissiveMap === 'night') return 'nightTexture'
        if (config.texture.emissiveMap === null) return 'null'
        return 'unknown'
      }

      function applyOceanTint(themeKey) {
        if (!oceanTintMesh || !oceanTintMaterial) return
        const config = OCEAN_TINT_BY_THEME[themeKey]
        if (config) {
          oceanTintMaterial.color.set(config.color)
          oceanTintMaterial.opacity = config.strength
          oceanTintMesh.visible = true
        } else {
          oceanTintMesh.visible = false
        }
        oceanTintMaterial.needsUpdate = true
      }

      function shouldUseOceanSpecularMap(themeKey) {
        return ['morning', 'noon', 'afternoon', 'goldenApproach'].includes(themeKey)
      }

      function getAuditViewProfile() {
        if (!auditLightingMode || !camera) return 'normal'
        if (camera.position.y >= 1.8) return 'low'
        if (camera.position.y >= 0.75) return 'oblique'
        return 'top'
      }

      function applySurfaceDetailTuning(resolvedTheme, config) {
        const auditProfile = getAuditViewProfile()
        const inAudit = auditProfile !== 'normal'
        const auditNormalScaleByProfile = {
          top: 0.0,
          oblique: 0.012,
          low: 0.02,
        }

        earthMaterial.specular.set(inAudit ? 0x000102 : config.material.specular)
        earthMaterial.shininess = inAudit ? 4 : config.material.shininess
        earthMaterial.specularMap = (!inAudit && shouldUseOceanSpecularMap(resolvedTheme))
          ? oceanSpecularTexture
          : null

        if (normalMapTexture) {
          const normalScale = inAudit ? auditNormalScaleByProfile[auditProfile] : 0.15
          earthMaterial.normalMap = normalScale > 0 ? normalMapTexture : null
          earthMaterial.normalScale = new THREE.Vector2(normalScale, normalScale)
        } else {
          earthMaterial.normalMap = null
        }
      }

      function getSpecularMode(config, themeKey) {
        const auditProfile = getAuditViewProfile()
        if (auditProfile !== 'normal') return `suppressed_${auditProfile}_audit`
        if (!shouldUseOceanSpecularMap(themeKey)) return 'null'
        return oceanSpecularTexture ? 'oceanSpecularTexture' : 'loading'
      }

      function logThemeAudit(themeKey, resolvedThemeKey, config, applyThemeResult, requiredTextures, missingTextures) {
        const cityLightsOpacity = config.lighting?.cityLightsOpacity || 0
        const audit = {
          themeKey,
          resolvedThemeKey,
          applyThemeResult,
          dayReady: Boolean(dayTexture),
          nightReady: Boolean(nightTexture),
          cityLightsReady: false,
          mapMode: getMapMode(config),
          emissiveMode: getEmissiveMode(config),
          specularMode: getSpecularMode(config, resolvedThemeKey),
          emissiveIntensity: config.texture.emissiveMap === 'night'
            ? config.texture.emissiveIntensity
            : 0,
          cityLightsMeshExists: false,
          cityLightsVisible: false,
          cityLightsOpacity,
          requiredTextures,
          missingTextures,
        }
        const signature = JSON.stringify(audit)
        if (signature === lastThemeAuditSignature) return
        lastThemeAuditSignature = signature
        console.log('[earth3d theme audit]', audit)
      }

      function syncRevealState(themeKey, applied) {
        if (!applied || permanentlyUnavailable) return

        const resolvedTheme = themeKey || pendingTheme || currentTheme || 'night'
        if (!areRevealTexturesReady(resolvedTheme)) return

        if (!isReady) {
          isReady = true
          renderer.domElement.style.opacity = '1'
        }

        renderer.render(scene, camera)
      }

      function resetDebugLayerState() {
        currentDebugMode = null
        if (earthMaterial) earthMaterial.visible = true
      }

      function resetNightGradeUniforms() {
        if (!earthShaderUniforms) return
        earthShaderUniforms.uLandDebugMode.value = 0
        earthShaderUniforms.uDaybaseMode.value   = 0
        earthShaderUniforms.uNightExposure.value   = 0.30
        earthShaderUniforms.uNightSaturation.value = 0.62
        earthShaderUniforms.uNightGamma.value      = 0.90
        earthShaderUniforms.uNightBlueBias.value   = 0.06
        earthShaderUniforms.uNightGreenBias.value  = 0.02
        earthShaderUniforms.uNightRedReduce.value  = 0.04
        earthShaderUniforms.uOceanLift.value = 0
        earthShaderUniforms.uOceanTeal.value = 0
        earthShaderUniforms.uOceanBlendStrength.value = 0
        earthShaderUniforms.uDayOceanGrade.value = 0
        earthShaderUniforms.uOceanDarken.value = 1
        earthShaderUniforms.uOceanContrast.value = 1
        earthShaderUniforms.uOceanSaturation.value = 1
        earthShaderUniforms.uOceanBlueBias.value = 0
        earthShaderUniforms.uOceanRedReduce.value = 0
        earthShaderUniforms.uOceanGreenReduce.value = 0
        earthShaderUniforms.uCoastProtection.value = 0.75
        earthShaderUniforms.uLandLift.value = 0
        earthShaderUniforms.uLandGamma.value = 1
        earthShaderUniforms.uLandStr.value = 0
        earthShaderUniforms.uLandRedRed.value = 0
        earthShaderUniforms.uLandGreenB.value = 0
        earthShaderUniforms.uLandGlowStr.value = 0
        earthShaderUniforms.uCityLumLow.value = 0
        earthShaderUniforms.uCityLumHigh.value = 1
        earthShaderUniforms.uCityHighlightClamp.value = 0.88
        earthShaderUniforms.uTropicalDarken.value = 0
        earthShaderUniforms.uTropicalGreenReduce.value = 0
        earthShaderUniforms.uAridDarken.value = 0
        earthShaderUniforms.uAridWarmReduce.value = 0
        earthShaderUniforms.uIceNeutralize.value = 0
        if (earthShaderUniforms.uOceanRawMix)      earthShaderUniforms.uOceanRawMix.value      = 0
        if (earthShaderUniforms.uOceanRawExposure) earthShaderUniforms.uOceanRawExposure.value = 0.025
        if (earthShaderUniforms.uOceanRawBlueKeep) earthShaderUniforms.uOceanRawBlueKeep.value = 0.2
        if (earthShaderUniforms.uOceanLiftTint)    earthShaderUniforms.uOceanLiftTint.value.set(0.35, 0.50, 1.0)
      }

      function clearEmissiveMapForDayModes() {
        earthMaterial.emissive.set(0x000000)
        earthMaterial.emissiveMap = null
        earthMaterial.emissiveIntensity = 0
      }

      function assignDayTexture(config) {
        earthMaterial.map = config.texture.map === 'day' ? dayTexture : null
      }

      function resetMaterialColor(config, useNightEmissive) {
        earthMaterial.color.set(config.texture.mapColor)
        earthMaterial.emissive.set(useNightEmissive ? config.texture.emissiveColor : 0x000000)
      }

      function resetLightingForTheme(config) {
        ambientLight.color.set(0xffffff)
        // Per-theme sun tint (lighting.sunColor). Default = the former hardcoded
        // warm white, so every theme without the key keeps its exact lighting.
        sunLight.color.set(config.lighting.sunColor ?? 0xfff5e0)
        ambientLight.intensity = config.lighting.ambient
        sunLight.intensity = config.lighting.sun
      }

      function forceRenderInvalidation() {
        if (earthMaterial) earthMaterial.needsUpdate = true
        if (atmosphereMaterial) atmosphereMaterial.needsUpdate = true
        if (atmosphere2Material) atmosphere2Material.needsUpdate = true
        _animDirty = true
      }

      function performSceneRefresh(options = {}) {
        const refreshTiles = options.refreshTiles === true
        if (!renderer || !scene || !camera || permanentlyUnavailable) return

        earth.updateMatrixWorld(true)
        atmosphere.updateMatrixWorld(true)
        earthGroup.updateMatrixWorld(true)
        scene.updateMatrixWorld(true)
        camera.updateMatrixWorld(true)

        if (refreshTiles && tileManager) {
          tileManager.safeRefreshVisibleTiles()
        }

        updateStreaming(camera)
        updateRDLOverlays()
        renderer.render(scene, camera)
        _animDirty = true
      }

      function applyTheme(themeKey, options = {}) {
        const resolvedTheme = themeKey || pendingTheme || currentTheme || 'night'
        if (currentTheme === resolvedTheme && options.force !== true) return true

        const config = getThemeVisualConfig(resolvedTheme)
        const requiredTextures = getRequiredTextures(resolvedTheme)
        const missingTextures = getMissingTextures(requiredTextures)
        if (missingTextures.length) {
          pendingTheme = resolvedTheme
          logThemeAudit(themeKey, resolvedTheme, config, false, requiredTextures, missingTextures)
          return false
        }

        const useNightEmissive = config.texture.emissiveMap === 'night'

        resetDebugLayerState()
        resetNightGradeUniforms()
        if (!useNightEmissive) clearEmissiveMapForDayModes()
        assignDayTexture(config)
        resetMaterialColor(config, useNightEmissive)
        const currentNightTex = nightTextureOverrides[resolvedTheme] || nightTexture
        earthMaterial.emissiveMap = useNightEmissive ? currentNightTex : null
        earthMaterial.emissiveIntensity = useNightEmissive ? config.texture.emissiveIntensity : 0
        applySurfaceDetailTuning(resolvedTheme, config)
        atmosphereMaterial.uniforms.uColor.value.set(config.atmosphere.color)
        atmosphereMaterial.uniforms.uColorOuter.value.set(config.atmosphere.colorOuter ?? config.atmosphere.color)
        atmosphereMaterial.uniforms.uOpacity.value = config.atmosphere.opacity
        if (config.atmosphere.power != null) atmosphereMaterial.uniforms.uPower.value = config.atmosphere.power
        atmosphereMaterial.uniforms.uPowerOuter.value    = config.atmosphere.powerOuter    ?? 3.2
        atmosphereMaterial.uniforms.uStrengthOuter.value = config.atmosphere.strengthOuter ?? 0.0
        atmosphereMaterial.uniforms.uRadius.value        = config.atmosphere.radius        ?? 2.10
        atmosphere.visible = (config.atmosphere.opacity ?? 0) > 0.0001
        // Two-layer atmosphere: show rim sphere only for themes that define atmosphere2
        if (atmosphere2 && atmosphere2Material) {
          if (config.atmosphere2) {
            atmosphere2Material.uniforms.uColor.value.set(config.atmosphere2.color)
            atmosphere2Material.uniforms.uColorOuter.value.set(config.atmosphere2.colorOuter ?? config.atmosphere2.color)
            atmosphere2Material.uniforms.uOpacity.value = config.atmosphere2.opacity
            if (config.atmosphere2.power != null) atmosphere2Material.uniforms.uPower.value = config.atmosphere2.power
            atmosphere2Material.uniforms.uRadius.value = config.atmosphere2.radius ?? 2.03
            atmosphere2.visible = true
          } else {
            atmosphere2.visible = false
          }
        }
        // Horizon glow overlays — update CSS config for this theme
        _horizonGlowCfg = config.horizonGlow ?? null
        const _glowActive = _horizonGlowCfg?.enabled
        if (_horizonGlowEl && !_glowActive) _horizonGlowEl.style.opacity = '0'
        if (_rimGlowEl    && !_glowActive) _rimGlowEl.style.opacity = '0'
        _animDirty = true
        resetLightingForTheme(config)
        _sunDirectionOverride = config.sunDirection ?? null
        // Night grade + city clamp — update per-theme via retained shader uniforms
        if (earthShaderUniforms) {
          earthShaderUniforms.uCityHighlightClamp.value = config.lighting?.cityLightClamp ?? 0.88
          const ng = config.nightGrade
          if (ng) {
            // v17 daybase params — active regardless of ocean mask load state
            const isDaybase = !!ng.daybaseMode
            earthShaderUniforms.uDaybaseMode.value = isDaybase ? 1 : 0
            if (isDaybase) {
              earthShaderUniforms.uNightExposure.value   = ng.nightExposure   ?? 0.30
              earthShaderUniforms.uNightSaturation.value = ng.nightSaturation ?? 0.62
              earthShaderUniforms.uNightGamma.value      = ng.nightGamma      ?? 0.90
              earthShaderUniforms.uNightBlueBias.value   = ng.nightBlueBias   ?? 0.06
              earthShaderUniforms.uNightGreenBias.value  = ng.nightGreenBias  ?? 0.02
              earthShaderUniforms.uNightRedReduce.value  = ng.nightRedReduce  ?? 0.04
              earthShaderUniforms.uTropicalDarken.value      = ng.tropicalDarken      ?? 0
              earthShaderUniforms.uTropicalGreenReduce.value = ng.tropicalGreenReduce ?? 0
              earthShaderUniforms.uAridDarken.value          = ng.aridDarken          ?? 0
              earthShaderUniforms.uAridWarmReduce.value      = ng.aridWarmReduce      ?? 0
              earthShaderUniforms.uIceNeutralize.value       = ng.iceNeutralize       ?? 0
            }
            // Ocean Tone Grade — applies regardless of daybaseMode. When isDaybase
            // is true, rodioOceanToneGrade() (routed through the night-exposure
            // base) consumes these; when false, the standalone shader path
            // (rodioOceanToneGradeStandalone) consumes them directly on raw day
            // color, so the same sliders work on any theme.
            earthShaderUniforms.uDayOceanGrade.value      = ng.dayOceanGrade ? 1 : 0
            earthShaderUniforms.uOceanBlendStrength.value = ng.oceanBlendStrength ?? 0
            earthShaderUniforms.uOceanDarken.value        = ng.oceanDarken ?? 1
            earthShaderUniforms.uOceanContrast.value      = ng.oceanContrast ?? 1
            earthShaderUniforms.uOceanSaturation.value    = ng.oceanSaturation ?? 1
            earthShaderUniforms.uOceanBlueBias.value      = ng.oceanBlueBias ?? 0
            earthShaderUniforms.uOceanRedReduce.value     = ng.oceanRedReduce ?? 0
            earthShaderUniforms.uOceanGreenReduce.value   = ng.oceanGreenReduce ?? 0
            earthShaderUniforms.uCoastProtection.value    = ng.coastProtection ?? 0.75
            // Ocean/land/city uniforms — still mask-gated for v16 compat;
            // v17 sets them to 0 via config so they have no effect.
            if (oceanMaskTextureLoadState === 'ready') {
              earthShaderUniforms.uOceanLift.value    = ng.oceanLift   ?? (isDaybase ? 0 : 0.5)
              if (earthShaderUniforms.uOceanLiftTint) {
                // Default (0.35, 0.50, 1.0) = the former hardcoded ratio, so
                // every theme without an explicit oceanLiftTint (and every
                // theme switch away from one that has it) keeps the exact
                // pre-parameterization color.
                const _lt = ng.oceanLiftTint
                earthShaderUniforms.uOceanLiftTint.value.set(_lt?.[0] ?? 0.35, _lt?.[1] ?? 0.50, _lt?.[2] ?? 1.0)
              }
              earthShaderUniforms.uOceanTeal.value    = ng.oceanTeal   ?? 0
              earthShaderUniforms.uLandLift.value     = ng.landLift    ?? 0.04
              earthShaderUniforms.uLandGamma.value    = ng.landGamma   ?? 0.85
              earthShaderUniforms.uLandStr.value      = ng.landStr     ?? (isDaybase ? 0 : 0.75)
              earthShaderUniforms.uLandRedRed.value   = ng.landRedRed  ?? 0.025
              earthShaderUniforms.uLandGreenB.value   = ng.landGreenB  ?? 0.045
              earthShaderUniforms.uLandGlowStr.value  = ng.landGlowStr ?? (isDaybase ? 0 : 0.10)
            }
            // City lum thresholds — NOT mask-gated; required for all night themes
            earthShaderUniforms.uCityLumLow.value   = ng.cityLumLow  ?? 0.008
            earthShaderUniforms.uCityLumHigh.value  = ng.cityLumHigh ?? 0.040
          } else {
            earthShaderUniforms.uDaybaseMode.value = 0
            earthShaderUniforms.uOceanBlendStrength.value = 0
            earthShaderUniforms.uOceanDarken.value = 1
            earthShaderUniforms.uOceanContrast.value = 1
            earthShaderUniforms.uOceanSaturation.value = 1
            earthShaderUniforms.uOceanBlueBias.value = 0
            earthShaderUniforms.uOceanRedReduce.value = 0
            earthShaderUniforms.uOceanGreenReduce.value = 0
            earthShaderUniforms.uCoastProtection.value = 0.75
            earthShaderUniforms.uLandStr.value     = 0
            earthShaderUniforms.uLandGlowStr.value = 0
            earthShaderUniforms.uOceanLift.value   = 0
            if (earthShaderUniforms.uOceanLiftTint) {
              earthShaderUniforms.uOceanLiftTint.value.set(0.35, 0.50, 1.0)
            }
            earthShaderUniforms.uOceanTeal.value   = 0
          }
        }
        if (starSphereLoaded && starSphereMaterial) {
          const _ssOpacity = config.starSphereOpacity ?? STAR_SPHERE_OPACITY[resolvedTheme] ?? 0
          starSphereMaterial.uniforms.uOpacity.value = _ssOpacity
          if (starSphere) starSphere.visible = true
        }
        // Sprite stars stay on together with the starmap (no longer zeroed
        // when the map loads): the map is the faint background sky, the
        // sprites are the bright foreground stars with glow gradients.
        if (stars?.material) {
          stars.material.opacity = PROCEDURAL_STARS_OPACITY[resolvedTheme] ?? 0
        }
        if (cloudMaterial?.uniforms && cloudTexture) {
          console.log('[cloud] applyTheme gate:', JSON.stringify({ resolvedTheme, cfgClouds: config.clouds, hasCfg: !!config, cfgTextureExists: !!(config && config.clouds && config.clouds.texture) }))
          applyCloudThemeConfig(config.clouds)
        }
        applyRimGlowThemeConfig(config.rimGlow, resolvedTheme)
        updateSkyTheme(resolvedTheme)
        updateEarlyMorningSkyPlane(resolvedTheme)
        applyOceanTint(resolvedTheme)

        currentTheme = resolvedTheme
        pendingTheme = resolvedTheme
        forceRenderInvalidation()
        logThemeAudit(themeKey, resolvedTheme, config, true, requiredTextures, missingTextures)
        return true
      }

      loadBootstrapDayAtlasImage()

      tileManager = new FrontendTileStreamingManager(renderer, null)
      dayTexture = tileManager.atlasTexture
      console.log('[RodiO] dayTexture variant:', DAY_TEXTURE_VARIANT)
      console.log('[RodiO] dayTexture source:', {
        mode: EARTH_MODE,
        pipeline: getEarthModeConfig().pipeline,
        tileSource: getEarthModeConfig().tileSource,
      })
      {
        const themeKey = pendingTheme || currentTheme || 'night'
        const applied = applyTheme(themeKey, { force: true })
        syncRevealState(themeKey, applied)
      }

      loadOceanSpecularTexture()
      loadOceanMaskTexture()

      loadTextureWithFallback(
        '/assets/earth_night_8k.jpg',
        ['/assets/earth_night_mid_8k.jpg', '/assets/blackmarble.jpg'],
        (texture, usedPath) => {
          nightTexture = texture
          console.log('[earth3d] night texture loaded:', usedPath)

          // Load theme-specific night texture overrides (non-blocking)
          const OVERRIDE_MAP = {
            goldenApproach: '/assets/earth_night_mid_8k.jpg',
            sunset:         '/assets/earth_night_mid_8k.jpg',
            evening:        '/assets/earth_night_night_8k.jpg',
            lateEvening:    '/assets/earth_night_late_8k.jpg',
            deepNight:      '/assets/earth_night_8k.jpg',
          }
          Object.entries(OVERRIDE_MAP).forEach(([themeKey, path]) => {
            loadTextureWithFallback(path, ['/assets/earth_night_8k.jpg'], (tex) => {
              nightTextureOverrides[themeKey] = tex
              console.log('[earth3d] night texture override loaded:', themeKey, '->', path)
            })
          })

          if (typeof applyTheme === 'function') {
            const themeKey = pendingTheme || currentTheme || 'night'
            const applied = applyTheme(themeKey, { force: true })
            if (applied) {
              performSceneRefresh({ refreshTiles: themeKey === 'noon' })
              if (themeKey === 'noon') {
                logThemeStateSnapshot('A_noon_texture_callback_reapply', {
                  reason: 'nightTextureLoaded',
                  usedPath,
                })
              }
            }
            syncRevealState(themeKey, applied)
            // Shader compiled after this render; re-apply to wire nightGrade uniforms
            if (applied) applyTheme(themeKey, { force: true })
          } else {
            earthMaterial.emissiveMap = texture
            earthMaterial.needsUpdate = true
          }
        }
      )

      // ── Real solar position ──────────────────────────────────────────────────
      // Returns the subsolar point (lat/lon in degrees) for the current instant
      // using the J2000 epoch algorithm (~0.1° accuracy, sufficient for rendering).
      function _computeSubsolarPoint() {
        const now = new Date()
        const JD = now.getTime() / 86400000 + 2440587.5   // Julian date
        const n  = JD - 2451545.0                          // days since J2000.0

        // Geometric mean longitude & mean anomaly (degrees)
        const L = (280.46646  + 0.9856474  * n) % 360
        const M = (((357.52911 + 0.98560028 * n) % 360) + 360) % 360
        const M_r = M * Math.PI / 180

        // Sun's true longitude
        const C = 1.914602 * Math.sin(M_r) + 0.019993 * Math.sin(2 * M_r) + 0.000289 * Math.sin(3 * M_r)
        const sunLon = L + C

        // Apparent longitude (aberration + nutation, simplified)
        const omega   = 125.04 - 1934.136 * n / 36525
        const lambda  = sunLon - 0.00569 - 0.00478 * Math.sin(omega * Math.PI / 180)
        const lam_r   = lambda * Math.PI / 180

        // Obliquity of ecliptic
        const eps_r = (23.439291 - 0.013004 * n / 36525) * Math.PI / 180

        // Declination & right ascension
        const decl = Math.asin(Math.sin(eps_r) * Math.sin(lam_r))
        const ra   = Math.atan2(Math.cos(eps_r) * Math.sin(lam_r), Math.cos(lam_r))

        // Greenwich Apparent Sidereal Time (degrees)
        const GMST = ((280.46061837 + 360.98564736629 * n) % 360 + 360) % 360
        const eot  = -0.000319 * Math.sin(omega * Math.PI / 180) - 0.000024 * Math.sin(2 * lam_r)
        const GAST = GMST + eot * 180 / Math.PI

        // Subsolar longitude: GHA = GAST − RA; subLon = −GHA
        const GHA    = ((GAST - ra * 180 / Math.PI) % 360 + 360) % 360
        let   subLon = -GHA
        if (subLon < -180) subLon += 360
        else if (subLon > 180) subLon -= 360

        return { lat: decl * 180 / Math.PI, lon: subLon }
      }

      // Maps subsolar (lat, lon) to a Three.js direction vector.
      // Coordinate system: y = north pole, equirectangular texture maps
      // longitude 0° (Prime Meridian) → +x, 90°E → −z, 90°W → +z.
      function _syncAtmSunDir() {
        const dir = sunLight.position.clone().normalize()
        if (atmosphereMaterial?.uniforms?.uSunDir)  atmosphereMaterial.uniforms.uSunDir.value.copy(dir)
        if (atmosphere2Material?.uniforms?.uSunDir) atmosphere2Material.uniforms.uSunDir.value.copy(dir)
        if (cloudMaterial?.uniforms?.uSunDir)        cloudMaterial.uniforms.uSunDir.value.copy(dir)
      }

      function updateSunPosition(_hour) {
        if (auditLightingMode && camera) {
          const d = 10
          const dir = camera.position.clone().normalize()
          sunLight.position.set(dir.x * d, dir.y * d, dir.z * d)
          _syncAtmSunDir()
          return
        }
        if (_sunDirectionOverride) {
          const d = 10, o = _sunDirectionOverride
          sunLight.position.set(o.x * d, o.y * d, o.z * d)
          _syncAtmSunDir()
          return
        }
        const { lat, lon } = _computeSubsolarPoint()
        const phi   = (lon + 180) * Math.PI / 180   // azimuthal (0..2π)
        const theta = (90  - lat) * Math.PI / 180   // polar from north
        const d = 10
        sunLight.position.set(
          -Math.cos(phi) * Math.sin(theta) * d,
           Math.cos(theta) * d,
           Math.sin(phi) * Math.sin(theta) * d
        )
        _syncAtmSunDir()
      }

      function getThemeHour(themeKey) {
        const config = getThemeVisualConfig(themeKey)
        return config?.themeHour ?? THEME_VISUAL_CONFIG.night.themeHour
      }

      function getTextureDebugState(texture, expectedTexture) {
        if (!texture) {
          return {
            exists: false,
            imageWidth: null,
            imageHeight: null,
            encoding: null,
            colorSpace: null,
            isExpectedTexture: false,
          }
        }

        const image = texture.image || {}
        return {
          exists: true,
          imageWidth: Number.isFinite(image.width) ? image.width : null,
          imageHeight: Number.isFinite(image.height) ? image.height : null,
          encoding: texture.encoding ?? null,
          colorSpace: texture.colorSpace ?? null,
          isExpectedTexture: Boolean(expectedTexture && texture === expectedTexture),
        }
      }

      function getUniformValue(name, fallback = null) {
        if (!earthShaderUniforms?.[name]) return fallback
        const value = earthShaderUniforms[name].value
        return Number.isFinite(value) ? value : value ?? fallback
      }

      function buildThemeStateSnapshot(label, extra = {}) {
        const state = buildDebugState()
        const mode = getEarthModeConfig()
        return {
          label,
          at: new Date().toISOString(),
          auditLightingEnabled: auditLightingMode,
          currentTheme: state.currentTheme,
          pendingTheme: state.pendingTheme,
          currentMode: EARTH_MODE,
          currentDebugMode,
          material: {
            colorHex: state.material.colorHex,
            mapColorHex: state.material.colorHex,
            mapExists: state.material.mapExists,
            mapIsDayTexture: state.material.mapIsDayTexture,
            mapColorSpace: state.textureBindings.dayTexture?.colorSpace ?? null,
            emissiveMapExists: state.material.emissiveMapExists,
            emissiveMapIsNightTexture: state.material.emissiveMapIsNightTexture,
            emissiveMapColorSpace: state.textureBindings.nightTexture?.colorSpace ?? null,
            needsUpdate: state.material.needsUpdate,
          },
          renderer: {
            toneMapping: state.renderer.toneMapping,
            toneMappingExposure: state.renderer.toneMappingExposure,
            outputColorSpace: state.renderer.outputColorSpace,
            outputEncoding: state.renderer.outputEncoding,
          },
          lights: {
            ambientIntensity: state.lights.ambientLightIntensity,
            ambientColorHex: ambientLight?.color?.getHexString ? `#${ambientLight.color.getHexString()}` : null,
            directionalIntensity: state.lights.sunLightIntensity,
            directionalColorHex: sunLight?.color?.getHexString ? `#${sunLight.color.getHexString()}` : null,
          },
          uniforms: {
            uLandDebugMode: getUniformValue('uLandDebugMode', 0),
            uOceanLift: getUniformValue('uOceanLift', 0),
            uOceanTeal: getUniformValue('uOceanTeal', 0),
            uOceanBlendStrength: getUniformValue('uOceanBlendStrength', 0),
            uOceanDarken: getUniformValue('uOceanDarken', 1),
            uOceanContrast: getUniformValue('uOceanContrast', 1),
            uOceanSaturation: getUniformValue('uOceanSaturation', 1),
            uOceanBlueBias: getUniformValue('uOceanBlueBias', 0),
            uOceanRedReduce: getUniformValue('uOceanRedReduce', 0),
            uOceanGreenReduce: getUniformValue('uOceanGreenReduce', 0),
            uCoastProtection: getUniformValue('uCoastProtection', 0.75),
            uLandGlowStr: getUniformValue('uLandGlowStr', 0),
            uLandLift: getUniformValue('uLandLift', 0),
            uLandGamma: getUniformValue('uLandGamma', null),
            uLandStr: getUniformValue('uLandStr', 0),
            uLandRedRed: getUniformValue('uLandRedRed', 0),
            uLandGreenB: getUniformValue('uLandGreenB', 0),
            uCityLumLow: getUniformValue('uCityLumLow', null),
            uCityLumHigh: getUniformValue('uCityLumHigh', null),
            nightGradeEnabled: Boolean(getThemeVisualConfig(state.currentTheme || state.pendingTheme || 'night')?.nightGrade),
            deepNightResidualActive: Boolean(
              getUniformValue('uLandDebugMode', 0) !== 0 ||
              getUniformValue('uOceanLift', 0) !== 0 ||
              getUniformValue('uOceanTeal', 0) !== 0 ||
              getUniformValue('uOceanBlendStrength', 0) !== 0 ||
              getUniformValue('uLandGlowStr', 0) !== 0 ||
              getUniformValue('uLandStr', 0) !== 0
            ),
            daybaseDarkened: getUniformValue('uDaybaseMode', 0) > 0.5,
            nightExposure: getUniformValue('uNightExposure', null),
          },
          textures: {
            dayReady: state.texture.dayReady,
            nightReady: state.texture.nightReady,
            dayTextureColorSpace: state.texture.dayTextureColorSpace,
            nightTextureColorSpace: state.texture.nightTextureColorSpace,
          },
          streaming: {
            tileSource: mode.tileSource,
            cachePrefix: mode.cachePrefix,
            pipeline: mode.pipeline,
            loadGeneration: tileManager?.loadGeneration ?? null,
            lastVisibleSignature: tileManager?.lastVisibleSignature ?? '',
            activeTileCount: state.streaming.activeTileCount,
            cacheSize: state.streaming.cacheSize,
            pendingTileCount: state.streaming.pendingTileCount,
            cacheKeys: tileManager ? Array.from(tileManager.tileCache.keys()).sort().slice(0, 12) : [],
            activeTileKeys: tileManager ? Array.from(tileManager.activeTiles.keys()).sort() : [],
          },
          extra,
        }
      }

      function logThemeStateSnapshot(label, extra = {}) {
        const snapshot = buildThemeStateSnapshot(label, extra)
        console.log(`[earth3d state snapshot] ${label} ${JSON.stringify(snapshot)}`)
        return snapshot
      }

      function buildDebugState() {
        const rendererCanvas = renderer?.domElement || null
        const rendererContext = renderer?.getContext ? renderer.getContext() : null
        const theme = {
          currentTheme,
          pendingTheme,
          auditLightingEnabled: auditLightingMode,
          isReady,
          isAvailable: isReady && !permanentlyUnavailable,
        }
        const texture = {
          dayReady: Boolean(dayTexture),
          nightReady: Boolean(nightTexture),
          dayTextureExists: Boolean(dayTexture),
          nightTextureExists: Boolean(nightTexture),
          dayTextureImageWidth: Number.isFinite(dayTexture?.image?.width) ? dayTexture.image.width : null,
          dayTextureImageHeight: Number.isFinite(dayTexture?.image?.height) ? dayTexture.image.height : null,
          nightTextureImageWidth: Number.isFinite(nightTexture?.image?.width) ? nightTexture.image.width : null,
          nightTextureImageHeight: Number.isFinite(nightTexture?.image?.height) ? nightTexture.image.height : null,
          dayTextureEncoding: dayTexture?.encoding ?? null,
          dayTextureColorSpace: dayTexture?.colorSpace ?? null,
          nightTextureEncoding: nightTexture?.encoding ?? null,
          nightTextureColorSpace: nightTexture?.colorSpace ?? null,
          oceanSpecularTextureExists: Boolean(oceanSpecularTexture),
          oceanSpecularTextureImageWidth: Number.isFinite(oceanSpecularTexture?.image?.width) ? oceanSpecularTexture.image.width : null,
          oceanSpecularTextureImageHeight: Number.isFinite(oceanSpecularTexture?.image?.height) ? oceanSpecularTexture.image.height : null,
          oceanSpecularTextureEncoding: oceanSpecularTexture?.encoding ?? null,
          oceanSpecularTextureColorSpace: oceanSpecularTexture?.colorSpace ?? null,
        }
        const material = {
          mapExists: Boolean(earthMaterial?.map),
          mapIsDayTexture: Boolean(earthMaterial?.map && earthMaterial.map === dayTexture),
          emissiveMapExists: Boolean(earthMaterial?.emissiveMap),
          emissiveMapIsNightTexture: Boolean(earthMaterial?.emissiveMap && earthMaterial.emissiveMap === nightTexture),
          specularMapExists: Boolean(earthMaterial?.specularMap),
          specularMapIsOceanSpecularTexture: Boolean(earthMaterial?.specularMap && earthMaterial.specularMap === oceanSpecularTexture),
          specularMapPath: oceanSpecularTexturePath,
          specularMapLoadState: oceanSpecularTextureLoadState,
          colorHex: earthMaterial?.color?.getHexString ? `#${earthMaterial.color.getHexString()}` : null,
          emissiveHex: earthMaterial?.emissive?.getHexString ? `#${earthMaterial.emissive.getHexString()}` : null,
          emissiveIntensity: Number.isFinite(earthMaterial?.emissiveIntensity) ? earthMaterial.emissiveIntensity : null,
          opacity: Number.isFinite(earthMaterial?.opacity) ? earthMaterial.opacity : null,
          transparent: Boolean(earthMaterial?.transparent),
          needsUpdate: Boolean(earthMaterial?.needsUpdate),
          visible: Boolean(earthMaterial?.visible),
        }
        const mesh = {
          earthMeshVisible: Boolean(earth?.visible),
          earthGroupVisible: Boolean(earthGroup?.visible),
          earthMeshScale: earth?.scale
            ? {
                x: earth.scale.x,
                y: earth.scale.y,
                z: earth.scale.z,
              }
            : null,
          earthGroupPosition: earthGroup?.position
            ? {
                x: earthGroup.position.x,
                y: earthGroup.position.y,
                z: earthGroup.position.z,
              }
            : null,
        }
        const rendererState = {
          outputEncoding: renderer?.outputEncoding ?? null,
          outputColorSpace: renderer?.outputColorSpace ?? null,
          toneMapping: renderer?.toneMapping ?? null,
          toneMappingExposure: renderer?.toneMappingExposure ?? null,
          canvasWidth: rendererCanvas?.width ?? null,
          canvasHeight: rendererCanvas?.height ?? null,
          drawingBufferWidth: rendererContext?.drawingBufferWidth ?? null,
          drawingBufferHeight: rendererContext?.drawingBufferHeight ?? null,
          animationLoopActive: Boolean(renderer?.getAnimationLoop && renderer.getAnimationLoop()),
        }
        const lights = {
          ambientLightIntensity: Number.isFinite(ambientLight?.intensity) ? ambientLight.intensity : null,
          sunLightIntensity: Number.isFinite(sunLight?.intensity) ? sunLight.intensity : null,
        }
        const uniforms = {
          uLandDebugMode: getUniformValue('uLandDebugMode', 0),
          uOceanLift: getUniformValue('uOceanLift', 0),
          uOceanTeal: getUniformValue('uOceanTeal', 0),
          uOceanBlendStrength: getUniformValue('uOceanBlendStrength', 0),
          uOceanDarken: getUniformValue('uOceanDarken', 1),
          uOceanContrast: getUniformValue('uOceanContrast', 1),
          uOceanSaturation: getUniformValue('uOceanSaturation', 1),
          uOceanBlueBias: getUniformValue('uOceanBlueBias', 0),
          uOceanRedReduce: getUniformValue('uOceanRedReduce', 0),
          uOceanGreenReduce: getUniformValue('uOceanGreenReduce', 0),
          uCoastProtection: getUniformValue('uCoastProtection', 0.75),
          uLandLift: getUniformValue('uLandLift', 0),
          uLandGamma: getUniformValue('uLandGamma', null),
          uLandStr: getUniformValue('uLandStr', 0),
          uLandRedRed: getUniformValue('uLandRedRed', 0),
          uLandGreenB: getUniformValue('uLandGreenB', 0),
          uLandGlowStr: getUniformValue('uLandGlowStr', 0),
          uCityLumLow: getUniformValue('uCityLumLow', null),
          uCityLumHigh: getUniformValue('uCityLumHigh', null),
          uCityHighlightClamp: getUniformValue('uCityHighlightClamp', null),
        }
        const streaming = {
          enabled: Boolean(tileManager),
          lod: tileManager?.lodConfig?.lod ?? null,
          tileCols: tileManager?.lodConfig?.tileCols ?? null,
          tileRows: tileManager?.lodConfig?.tileRows ?? null,
          tileResolution: tileManager?.lodConfig?.tileResolution ?? null,
          atlasTileSize: tileManager?.lodConfig?.atlasTileSize ?? null,
          atlasFilterMode,
          maxCachedTiles: tileManager?.lodConfig?.maxCachedTiles ?? null,
          activeTileCount: tileManager?.activeTiles?.size ?? 0,
          cacheSize: tileManager?.tileCache?.size ?? 0,
          cacheHits: tileManager?.cacheHits ?? 0,
          cacheMisses: tileManager?.cacheMisses ?? 0,
          pendingTileCount: tileManager?.loadingTiles?.size ?? 0,
          visibleTiles: tileManager ? Array.from(tileManager.activeTiles.keys()).sort() : [],
        }
        const sky = {
          skyMeshExists: Boolean(skyMesh),
          skyVisible: Boolean(skyMesh?.visible),
          skyRenderOrder: Number.isFinite(skyMesh?.renderOrder) ? skyMesh.renderOrder : null,
          skyRadius,
          skyDepthWrite: Boolean(skyMaterial?.depthWrite),
          skyDepthTest: Boolean(skyMaterial?.depthTest),
          skyMaterialReady: Boolean(skyGeometry && skyMaterial && skyMesh),
          skyUsesShaderMaterial: Boolean(skyMaterial?.isShaderMaterial),
          skyOpacity: Number.isFinite(skyMaterial?.uniforms?.uOpacity?.value) ? skyMaterial.uniforms.uOpacity.value : null,
          currentThemeKey: currentTheme,
          supportsGoldenApproach: Boolean(THEME_VISUAL_CONFIG.goldenApproach),
          supportsLateEvening: Boolean(THEME_VISUAL_CONFIG.lateEvening),
        }

        return {
          skyMeshExists: sky.skyMeshExists,
          skyVisible: sky.skyVisible,
          skyRenderOrder: sky.skyRenderOrder,
          skyRadius: sky.skyRadius,
          skyDepthWrite: sky.skyDepthWrite,
          skyDepthTest: sky.skyDepthTest,
          skyMaterialReady: sky.skyMaterialReady,
          skyUsesShaderMaterial: sky.skyUsesShaderMaterial,
          skyOpacity: sky.skyOpacity,
          currentThemeKey: sky.currentThemeKey,
          supportsGoldenApproach: sky.supportsGoldenApproach,
          supportsLateEvening: sky.supportsLateEvening,
          auditLightingEnabled: theme.auditLightingEnabled,
          currentTheme: theme.currentTheme,
          pendingTheme: theme.pendingTheme,
          isReady: theme.isReady,
          isAvailable: theme.isAvailable,
          dayReady: texture.dayReady,
          nightReady: texture.nightReady,
          dayTextureExists: texture.dayTextureExists,
          nightTextureExists: texture.nightTextureExists,
          dayTextureImageWidth: texture.dayTextureImageWidth,
          dayTextureImageHeight: texture.dayTextureImageHeight,
          nightTextureImageWidth: texture.nightTextureImageWidth,
          nightTextureImageHeight: texture.nightTextureImageHeight,
          dayTextureEncoding: texture.dayTextureEncoding,
          dayTextureColorSpace: texture.dayTextureColorSpace,
          nightTextureEncoding: texture.nightTextureEncoding,
          nightTextureColorSpace: texture.nightTextureColorSpace,
          oceanSpecularTextureExists: texture.oceanSpecularTextureExists,
          oceanSpecularTextureImageWidth: texture.oceanSpecularTextureImageWidth,
          oceanSpecularTextureImageHeight: texture.oceanSpecularTextureImageHeight,
          oceanSpecularTextureEncoding: texture.oceanSpecularTextureEncoding,
          oceanSpecularTextureColorSpace: texture.oceanSpecularTextureColorSpace,
          mapExists: material.mapExists,
          mapIsDayTexture: material.mapIsDayTexture,
          emissiveMapExists: material.emissiveMapExists,
          emissiveMapIsNightTexture: material.emissiveMapIsNightTexture,
          specularMapExists: material.specularMapExists,
          specularMapIsOceanSpecularTexture: material.specularMapIsOceanSpecularTexture,
          specularMapPath: material.specularMapPath,
          specularMapLoadState: material.specularMapLoadState,
          colorHex: material.colorHex,
          emissiveHex: material.emissiveHex,
          emissiveIntensity: material.emissiveIntensity,
          opacity: material.opacity,
          transparent: material.transparent,
          needsUpdate: material.needsUpdate,
          visible: material.visible,
          earthMeshVisible: mesh.earthMeshVisible,
          earthGroupVisible: mesh.earthGroupVisible,
          earthMeshScale: mesh.earthMeshScale,
          earthGroupPosition: mesh.earthGroupPosition,
          outputEncoding: rendererState.outputEncoding,
          outputColorSpace: rendererState.outputColorSpace,
          toneMapping: rendererState.toneMapping,
          toneMappingExposure: rendererState.toneMappingExposure,
          canvasWidth: rendererState.canvasWidth,
          canvasHeight: rendererState.canvasHeight,
          drawingBufferWidth: rendererState.drawingBufferWidth,
          drawingBufferHeight: rendererState.drawingBufferHeight,
          animationLoopActive: rendererState.animationLoopActive,
          streamingEnabled: streaming.enabled,
          streamingLod: streaming.lod,
          streamingActiveTileCount: streaming.activeTileCount,
          streamingCacheSize: streaming.cacheSize,
          streamingCacheHits: streaming.cacheHits,
          streamingCacheMisses: streaming.cacheMisses,
          streamingPendingTileCount: streaming.pendingTileCount,
          ambientLightIntensity: lights.ambientLightIntensity,
          sunLightIntensity: lights.sunLightIntensity,
          theme: {
            ...theme,
          },
          texture: {
            ...texture,
          },
          textureBindings: {
            dayTexture: getTextureDebugState(dayTexture, earthMaterial?.map),
            nightTexture: getTextureDebugState(nightTexture, earthMaterial?.emissiveMap),
            oceanSpecularTexture: getTextureDebugState(oceanSpecularTexture, earthMaterial?.specularMap),
          },
          material: {
            ...material,
          },
          mesh: {
            ...mesh,
          },
          renderer: {
            ...rendererState,
          },
          lights: {
            ...lights,
          },
          uniforms: {
            ...uniforms,
          },
          streaming: {
            ...streaming,
          },
        }
      }

      function getStreamingCameraState(streamCamera = camera) {
        const visualState = window.__rodioVisualState || {}
        const cameraDistance = streamCamera?.position?.length ? streamCamera.position.length() : null
        return {
          lon: normalizeLon(Number.isFinite(visualState.lon) ? visualState.lon : 121.4737),
          lat: clamp(Number.isFinite(visualState.lat) ? visualState.lat : 31.2304, -80, 80),
          distance: Number.isFinite(cameraDistance) ? cameraDistance : 4.8,
          fovDegrees: Number.isFinite(streamCamera?.fov) ? streamCamera.fov : 28,
        }
      }

      function updateStreaming(camera) {
        if (!tileManager || permanentlyUnavailable) return []
        return tileManager.updateStreaming(getStreamingCameraState(camera))
      }

      function resize() {
        const width = appEl.clientWidth
        const height = appEl.clientHeight
        if (!width || !height) return
        // Guard: skip suspiciously narrow sizes on init — retry next frame instead
        if (width < 100 && renderer.domElement.width >= 100) return
        renderer.setSize(width, height, false)
        camera.aspect = width / height
        camera.updateProjectionMatrix()
        updateVisualTargetDir()
      }

      observer = new ResizeObserver(() => resize())
      observer.observe(appEl)
      resize()
      // If initial size was degenerate (< 100px), schedule retries until layout settles
      if (appEl.clientWidth < 100) {
        let _retries = 0
        const _retryResize = () => {
          resize()
          if (appEl.clientWidth < 100 && _retries++ < 20) requestAnimationFrame(_retryResize)
        }
        requestAnimationFrame(_retryResize)
      }
      updateVisualTargetDir()

      // ─── Scroll-wheel zoom ────────────────────────────────────────────────
      // Zooms by changing camera FOV (28° = global view, 8° = max zoom-in).
      // _rdlZoomLevel drives the RDL regional overlay opacity.
      const _RDL_FOV_NORMAL = 28
      const _RDL_FOV_MIN    = 8
      // ── Camera Narrative Presets (E7) ──────────────────────────────────
      const CAMERA_PRESETS = {
        globe:      { label: 'Globe',      lat: 31.23,  lon: 121.47,  centerMode: false, fov: 28, cameraOffsetY: 0.0, cameraOffsetZ: 4.8,  lookAtY: 0.0  },
        heroClose:  { label: 'Hero Close', lat: 31.23,  lon: 121.47,  centerMode: false, fov: 48, cameraOffsetY: 0.0, cameraOffsetZ: 5.5,  lookAtY: 0.0  },
        hemisphere: { label: 'Hemisphere', lat: 35.0,   lon: 110.0,   centerMode: false, fov: 22, cameraOffsetY: 0.5, cameraOffsetZ: 5.5,  lookAtY: -0.3 },
        horizon:    { label: 'Horizon',    lat: 25.0,   lon: 121.0,   centerMode: true,  fov: 14, cameraOffsetY: 2.0, cameraOffsetZ: 4.0,  lookAtY: -0.5 },
        lowOrbit:   { label: 'Low Orbit',  lat: 30.0,   lon: 121.0,   centerMode: true,  fov: 12, cameraOffsetY: 1.2, cameraOffsetZ: 3.5,  lookAtY: -0.8 },
        cityFocus:  { label: 'City Focus', lat: 31.23,  lon: 121.47,  centerMode: true,  fov: 8,  cameraOffsetY: 0.6, cameraOffsetZ: 3.0,  lookAtY: -1.0 },
        oceanView:  { label: 'Ocean View', lat: -10.0,  lon: -140.0,  centerMode: false, fov: 24, cameraOffsetY: 0.3, cameraOffsetZ: 5.0,  lookAtY: -0.2 },
        deepSpace:  { label: 'Deep Space', lat: 31.23,  lon: 121.47,  centerMode: false, fov: 28, cameraOffsetY: 0.0, cameraOffsetZ: 80.0, lookAtY: 0.0  },
      }

      const _AUDIT_VIEW_ANGLES = {
        top: { y: 0.0, z: 4.8, lookY: -1.4 },
        oblique: { y: 1.35, z: 5.05, lookY: -1.2 },
        low: { y: 2.15, z: 5.45, lookY: -0.9 },
        asiaTilt: { y: 0.65, z: 5.4, lookY: -1.10 },
        asiaWide: { y: 0.28, z: 7.2, lookY: -0.65 },
        tilt: { y: 0.82, z: 6.1, lookY: -1.52 },
        global: { y: 0.18, z: 7.85, lookY: -0.72 },
      }
      renderer.domElement.addEventListener('wheel', (e) => {
        e.preventDefault()
        _rdlZoomLevel = Math.max(0, Math.min(1, _rdlZoomLevel - e.deltaY * 0.0008))
        camera.fov = _RDL_FOV_NORMAL + (_RDL_FOV_MIN - _RDL_FOV_NORMAL) * _rdlZoomLevel
        camera.updateProjectionMatrix()
      }, { passive: false })
      // ──────────────────────────────────────────────────────────────────────
      const initialOrientation = getTargetOrientation()
      earth.quaternion.copy(initialOrientation)
      atmosphere.rotation.set(0, 0, 0)
      updateSunPosition()
      window.__earth3dBootStage = 'before-applyTheme'
      applyTheme(pendingTheme)
      window.__earth3dBootStage = 'after-applyTheme'

      renderer.setAnimationLoop(() => {
        if (!isReady || permanentlyUnavailable) return
        _animFrameCount++
        if (starSphereMaterial && starSphereMaterial.uniforms) {
          if (_starAnimStartTime === 0) _starAnimStartTime = performance.now() / 1000
          starSphereMaterial.uniforms.uTime.value = performance.now() / 1000 - _starAnimStartTime
          if (stars?.material?.uniforms?.uTime) {
            stars.material.uniforms.uTime.value = starSphereMaterial.uniforms.uTime.value
          }
        }
        const target = getTargetOrientation(useAuditCenterTarget ? auditCenterDir : null)
        const isAnimating = earth.quaternion.angleTo(target) > 0.0002
        earth.quaternion.slerp(target, 0.02)
        atmosphere.rotation.set(0, 0, 0)
        if (cloudMesh) cloudMesh.rotation.y += 0.00003

        if (isAnimating || _animDirty) {
          updateStreaming(camera)
          updateRDLOverlays()
          if (!isAnimating) _animDirty = false
        } else if (_animFrameCount % 10 === 0) {
          // Maintenance tick: keep RDL opacity in sync without tile work
          updateRDLOverlays()
        }

        if (DAY_SKY_PLANE_THEMES.has(currentTheme)) {
          updateEarlyMorningGlowMode()
          if (skyMesh) skyMesh.visible = false
          updateEarlyMorningRimProjection()
          renderer.autoClear = false
          renderer.clear(true, true, true)
          renderer.render(earlyMorningSkyScene, earlyMorningSkyCamera)
          renderer.clearDepth()
          renderer.render(scene, camera)
          renderer.clearDepth()
          renderer.render(earlyMorningRimOverlayScene, earlyMorningRimOverlayCamera)
          renderer.autoClear = true
        } else if (RIM_OVERLAY_THEMES.has(currentTheme)) {
          // deepNight etc.: same Rim Overlay + Inner Horizon Veil post-scene
          // stack as earlyMorning, but keep this theme's own sky/star sphere
          // instead of swapping in earlyMorning's dedicated gradient plane.
          updateEarlyMorningGlowMode()
          updateEarlyMorningRimProjection()
          renderer.autoClear = false
          renderer.clear(true, true, true)
          renderer.render(scene, camera)
          renderer.clearDepth()
          renderer.render(earlyMorningRimOverlayScene, earlyMorningRimOverlayCamera)
          renderer.autoClear = true
        } else {
          renderer.render(scene, camera)
        }
        updateHorizonGlow()
      })

      _sunUpdateInterval = setInterval(updateSunPosition, 60000)

      // 七曜零点交接仪式：每秒轮询，仅在 23:58:30–00:01:30 窗口内且 deepNight
      // 主题下，重新应用 rimGlow 配色（blendFactor 随仪式窗口实时呼吸）。
      // 窗口外不触碰颜色，避免无效重绘。
      let _ceremonyWasActive = false
      const _tickCeremony = () => {
        if (currentTheme !== 'deepNight') { _ceremonyWasActive = false; return }
        const now = new Date()
        const s = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds()
        const inWindow = s >= 86400 - SHICHIYOU_CEREMONY_WINDOW_SECONDS || s < SHICHIYOU_CEREMONY_WINDOW_SECONDS // 23:58:30–00:01:30（不含 00:01:30 整点）
        if (inWindow) {
          const cfg = getThemeVisualConfig('deepNight')
          if (cfg?.rimGlow) applyRimGlowThemeConfig(cfg.rimGlow, 'deepNight')
          _ceremonyWasActive = true
        } else if (_ceremonyWasActive) {
          // 刚离开窗口：恢复常态 BASE（blendFactor 回到 0.18）
          const cfg = getThemeVisualConfig('deepNight')
          if (cfg?.rimGlow) applyRimGlowThemeConfig(cfg.rimGlow, 'deepNight')
          _ceremonyWasActive = false
        }
      }
      _ceremonyTimer = setInterval(_tickCeremony, 1000)

      visibilityChangeHandler = () => {
        if (document.hidden) return
      }
      document.addEventListener('visibilitychange', visibilityChangeHandler)

      window.__earth3dBootStage = 'before-api-export'
      // isReady must stay a live accessor — Object.assign below would otherwise
      // read a getter's value once at call time and copy it as a frozen boolean
      // (Object.assign evaluates source getters via [[Get]], then does a plain
      // [[Set]] on the target; it does not transplant the accessor itself).
      // That silently froze window.earth3d.isReady at whatever isReady was
      // during boot (almost always false, since textures aren't loaded yet),
      // breaking every consumer that polls it afterward (Theme Tuner panel,
      // useEarth3D detection).
      Object.defineProperty(earth3dApi, 'isReady', {
        get() { return isReady },
        configurable: true,
        enumerable: true,
      })
      Object.assign(earth3dApi, {
        isAvailable() {
          return isReady && !permanentlyUnavailable
        },
        setDebugLocation(lon, lat, options = {}) {
          useAuditCenterTarget = Boolean(options.center)
          window.__rodioVisualState = {
            ...(window.__rodioVisualState || {}),
            lon,
            lat
          }

          const target = getTargetOrientation(useAuditCenterTarget ? auditCenterDir : null)
          earth.quaternion.copy(target)
          atmosphere.rotation.set(0, 0, 0)

          performSceneRefresh()

          logThemeStateSnapshot('B_after_location_refresh', {
            lon,
            lat,
            centered: useAuditCenterTarget,
            themeAtRefresh: pendingTheme || currentTheme || null,
          })

          if (DEBUG_MARKERS_ENABLED) {
            console.log('[earth3d] debug location set =', lon, lat)
            debugCityMarkers.forEach(({ city, marker }) => {
              const markerWorldPos = new THREE.Vector3()
              marker.getWorldPosition(markerWorldPos)
              const markerScreenPos = markerWorldPos.clone().project(camera)

              console.log(
                `[earth3d] marker ${city.name} screen =`,
                markerScreenPos.x.toFixed(3),
                markerScreenPos.y.toFixed(3),
                markerScreenPos.z.toFixed(3)
              )
            })
          }
        },
        setTimeOfDay(themeKey) {
          if (permanentlyUnavailable) return false
          pendingTheme = themeKey
          const applied = applyTheme(themeKey, { force: true })
          updateSunPosition()
          if (applied) {
            performSceneRefresh({ refreshTiles: themeKey === 'noon' })
            if (themeKey === 'noon') {
              logThemeStateSnapshot('A_noon_initial_apply', {
                reason: 'setTimeOfDay',
              })
            }
          }
          syncRevealState(themeKey, applied)
          return applied
        },
        setAuditLightingMode(enabled) {
          if (permanentlyUnavailable) return false
          auditLightingMode = Boolean(enabled)
          const themeKey = pendingTheme || currentTheme || 'noon'
          const applied = applyTheme(themeKey, { force: true })
          refreshRDLTextureSampling()
          syncRevealState(themeKey, applied)
          updateSunPosition()
          requestRenderUpdate()
          console.log('[earth3d] audit lighting override', {
            enabled: auditLightingMode,
            themeKey,
            ambient: ambientLight?.intensity ?? null,
            sun: sunLight?.intensity ?? null,
          })
          return auditLightingMode
        },
        getAuditLightingMode() {
          return auditLightingMode
        },
        setEarthMode(mode) {
          return setEarthMode(mode)
        },
        getEarthMode() {
          return EARTH_MODE
        },
        setAtlasFilterMode(mode) {
          atlasFilterMode = mode === 'normal' ? 'normal' : 'sharp'
          window.__rodioAtlasFilterMode = atlasFilterMode
          if (tileManager?.atlasTexture) {
            configureAtlasTexture(tileManager.atlasTexture, tileManager.lodConfig?.lod)
          }
          requestRenderUpdate()
          return atlasFilterMode
        },
        getAtlasFilterMode() {
          return atlasFilterMode
        },
        setSkyVisible(visible) {
          if (!skyMesh || !skyMaterial?.uniforms) return false
          skyMesh.visible = Boolean(visible)
          skyMaterial.uniforms.uEnabled.value = skyMesh.visible ? 1 : 0
          if (isReady && !permanentlyUnavailable) {
            renderer.render(scene, camera)
          }
          return skyMesh.visible
        },
        setCloudTexture(path) {
          if (!cloudMesh || !loader) return
          loader.load(path, (tex) => {
            if ('colorSpace' in tex) {
              tex.colorSpace = THREE.SRGBColorSpace
            } else {
              tex.encoding = THREE.sRGBEncoding
            }
            tex.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy())
            if (cloudTexture) cloudTexture.dispose()
            cloudTexture = tex
            cloudMaterial.uniforms.uCloudMap.value = tex
            const _cfg = getThemeVisualConfig(currentTheme || pendingTheme)
            applyCloudThemeConfig(_cfg.clouds)
            requestRenderUpdate()
          })
        },
        setCloudOpacity(opacity) {
          if (!cloudMaterial?.uniforms) return
          cloudMaterial.uniforms.uCloudOpacity.value = Math.max(0, Math.min(1, opacity))
          requestRenderUpdate()
        },
        getRDLZoomLevel() {
          return _rdlZoomLevel
        },
        getRDLDebugInfo() {
          earth.updateWorldMatrix(true, false)
          earth.getWorldPosition(_rdlEarthWorldPos)
          const camDir = camera.position.clone().sub(_rdlEarthWorldPos).normalize()
          return rdlMeshes.map(entry => {
            const localDir = lonLatToVector3(entry.region.centerLon, entry.region.centerLat, 1).normalize()
            const worldDir = localDir.clone().transformDirection(earth.matrixWorld).normalize()
            const facing = camDir.dot(worldDir)
            const ft = Math.max(0, Math.min(1, (facing - _RDL_FACE_THRESH) / (_RDL_FACE_FULL - _RDL_FACE_THRESH)))
            const opacity = ft * ft * (3 - 2 * ft)
            return {
              id: entry.region.id,
              facing: +facing.toFixed(4),
              opacity: +opacity.toFixed(4),
              visible: entry.mesh.visible,
              loaded: entry.loaded,
              loading: entry.loading,
            }
          })
        },
        setRDLZoomLevel(level) {
          _rdlZoomLevel = Math.max(0, Math.min(1, level))
          camera.fov = _RDL_FOV_NORMAL + (_RDL_FOV_MIN - _RDL_FOV_NORMAL) * _rdlZoomLevel
          camera.updateProjectionMatrix()
          updateEarlyMorningGlowMode()
          requestRenderUpdate()
          return _rdlZoomLevel
        },
        setRDLInspectRegion(regionId) {
          _rdlInspectRegion = regionId || null
          refreshRDLTextureSampling()
          requestRenderUpdate()
          return _rdlInspectRegion
        },
        setAuditViewAngle(angle) {
          const preset = _AUDIT_VIEW_ANGLES[angle] || _AUDIT_VIEW_ANGLES.top
          _currentAuditViewAngle = Object.prototype.hasOwnProperty.call(_AUDIT_VIEW_ANGLES, angle) ? angle : 'top'
          camera.position.set(0, preset.y, preset.z)
          camera.lookAt(0, preset.lookY, 0)
          camera.updateProjectionMatrix()
          if (auditLightingMode) {
            const themeKey = pendingTheme || currentTheme || 'noon'
            applyTheme(themeKey, { force: true })
          }
          updateEarlyMorningGlowMode()
          refreshRDLTextureSampling()
          updateSunPosition()
          requestRenderUpdate()
          return _currentAuditViewAngle
        },
        applyCameraPreset(key) {
          const preset = CAMERA_PRESETS[key]
          if (!preset) { console.warn('[earth3d] unknown camera preset:', key); return false }

          // camera position & FOV
          camera.position.set(0, preset.cameraOffsetY, preset.cameraOffsetZ)
          camera.fov = preset.fov
          camera.lookAt(0, preset.lookAtY, 0)
          camera.updateProjectionMatrix()

          // earth orientation via rodioVisualState → getTargetOrientation()
          useAuditCenterTarget = Boolean(preset.centerMode)
          window.__rodioVisualState = {
            ...(window.__rodioVisualState || {}),
            lon: preset.lon,
            lat: preset.lat,
          }

          const target = getTargetOrientation(useAuditCenterTarget ? auditCenterDir : null)
          earth.quaternion.copy(target)
          atmosphere.rotation.set(0, 0, 0)

          performSceneRefresh()
          updateSunPosition()
          requestRenderUpdate()

          return true
        },
        getDebugState() {
          return buildDebugState()
        },
        logStateSnapshot(label, extra = {}) {
          return logThemeStateSnapshot(label || 'manual', extra)
        },
        dispose() {
          isReady = false
          isDestroyed = true
          renderer.setAnimationLoop(null)
          if (_sunUpdateInterval) { clearInterval(_sunUpdateInterval); _sunUpdateInterval = null }
          if (_ceremonyTimer) { clearInterval(_ceremonyTimer); _ceremonyTimer = null }
          if (visibilityChangeHandler) {
            document.removeEventListener('visibilitychange', visibilityChangeHandler)
            visibilityChangeHandler = null
          }
          if (renderer?.domElement) renderer.domElement.style.opacity = '0'
          if (observer) observer.disconnect()
          if (skyGeometry) skyGeometry.dispose()
          if (skyMaterial) skyMaterial.dispose()
          if (_emSkyPlaneMat) _emSkyPlaneMat.dispose()
          earlyMorningSkyScene = null
          earlyMorningSkyCamera = null
          if (earlyMorningRimOverlayMesh?.geometry) earlyMorningRimOverlayMesh.geometry.dispose()
          if (_emRimOverlayMat) _emRimOverlayMat.dispose()
          if (earlyMorningInnerVeilMesh?.geometry) earlyMorningInnerVeilMesh.geometry.dispose()
          if (_emInnerVeilMat) _emInnerVeilMat.dispose()
          earlyMorningRimOverlayScene = null
          earlyMorningRimOverlayCamera = null
          if (earthGeometry) earthGeometry.dispose()
          if (atmosphere?.geometry) atmosphere.geometry.dispose()
          if (atmosphere2?.geometry) atmosphere2.geometry.dispose()
          if (stars?.geometry) stars.geometry.dispose()
          skyGeometry = null
          skyMaterial = null
          skyMesh = null
          if (earthMaterial) earthMaterial.dispose()
          if (atmosphereMaterial) atmosphereMaterial.dispose()
          if (atmosphere2Material) atmosphere2Material.dispose()
          if (stars?.material) stars.material.dispose()
          if (tileManager) {
            tileManager.dispose()
            tileManager = null
            dayTexture = null
          } else if (dayTexture) {
            dayTexture.dispose()
          }
          if (nightTexture) nightTexture.dispose()
          Object.values(nightTextureOverrides).forEach(tex => { if (tex) tex.dispose() })
          if (oceanSpecularTexture) oceanSpecularTexture.dispose()
          if (normalMapTexture) normalMapTexture.dispose()
          if (oceanTintMesh?.parent) oceanTintMesh.parent.remove(oceanTintMesh)
          if (oceanTintGeometry) oceanTintGeometry.dispose()
          if (oceanTintMaterial) oceanTintMaterial.dispose()
          if (oceanMaskTexture) oceanMaskTexture.dispose()
          renderer.dispose()
          mountEl.innerHTML = ''
          window.__earth3dDeletedAt = 'destroy'
          delete window.earth3d
        },
        // Patch individual fields of a theme config and re-apply live.
        // patch shape: { texture?: {…}, atmosphere?: {…}, lighting?: {…} }
        // Used by the dev Theme Tuner panel in index.html.
        patchTheme(themeKey, patch) {
          if (permanentlyUnavailable) return false
          const base = THEME_VISUAL_CONFIG[themeKey]
          if (!base) return false
          if (patch.texture)    Object.assign(base.texture,    patch.texture)
          if (patch.atmosphere) Object.assign(base.atmosphere, patch.atmosphere)
          if (patch.lighting)   Object.assign(base.lighting,   patch.lighting)
          if (patch.material)   Object.assign(base.material,   patch.material)
          if (patch.nightGrade) {
            base.nightGrade = base.nightGrade || {}
            Object.assign(base.nightGrade, patch.nightGrade)
          }
          const applied = applyTheme(themeKey, { force: true })
          // Re-enter debug mode if one is active — applyTheme resets uLandDebugMode to 0
          // and restores material properties, so we need to re-apply the isolation setup.
          if (applied && currentDebugMode) this.setDebugLayer(currentDebugMode)
          requestRenderUpdate()
          return applied
        },
        getThemeConfig(themeKey) {
          const cfg = THEME_VISUAL_CONFIG[themeKey]
          if (!cfg) return null
          return {
            mapColor:           cfg.texture?.mapColor,
            emissiveColor:      cfg.texture?.emissiveColor,
            emissiveIntensity:  cfg.texture?.emissiveIntensity,
            atmosphereColor:    cfg.atmosphere?.color,
            atmosphereOpacity:  cfg.atmosphere?.opacity,
            ambient:            cfg.lighting?.ambient,
            sun:                cfg.lighting?.sun,
            nightGrade:         cfg.nightGrade ? { ...cfg.nightGrade } : null,
          }
        },
        getRimOverlayMat() {
          return _emRimOverlayMat || null
        },
        getSkyPlaneMat() {
          return _emSkyPlaneMat || null
        },
        getInnerVeilMat() {
          return _emInnerVeilMat || null
        },
        // Toggle CSS glow overlays on/off — useful for diagnosing polar artifacts.
        // Usage: window.earth3d.toggleGlowOverlays(false) to hide, (true) to restore.
        toggleGlowOverlays(visible) {
          const opacity = visible ? null : '0'  // null = restore CSS-managed value, '0' = force hidden
          if (_horizonGlowEl) _horizonGlowEl.style.opacity = opacity === null ? '' : opacity
          if (_rimGlowEl)     _rimGlowEl.style.opacity     = opacity === null ? '' : opacity
          requestRenderUpdate()
        },
        // Toggle 3D Fresnel atmosphere sphere.
        toggleAtmosphere3d(visible) {
          if (atmosphere) atmosphere.visible = visible ?? !atmosphere.visible
          requestRenderUpdate()
        },
        // Debug layer isolation — localhost dev only.
        setDebugLayer(mode) {
          if (permanentlyUnavailable || !earthMaterial) return
          currentDebugMode = (mode === 'final') ? null : mode
          const theme = currentTheme || 'deepNight'
          // Helper: silently restore night-sky material properties for modes
          // that need active city lights (cityMaskOnly, cityColorOnly).
          const _restoreEmissive = () => {
            const _cfg = THEME_VISUAL_CONFIG[theme]?.texture
            if (_cfg) {
              earthMaterial.emissive.set(_cfg.emissiveColor ?? 0xFFD07A)
              earthMaterial.emissiveIntensity = _cfg.emissiveIntensity ?? 1.35
              earthMaterial.emissiveMap = nightTextureOverrides[theme] || nightTexture
            }
          }
          const _hideAtmo = () => {
            if (atmosphere) atmosphere.visible = false
            if (atmosphere2) atmosphere2.visible = false
          }
          const _zeroOceanShader = () => {
            if (!earthShaderUniforms) return
            earthShaderUniforms.uOceanLift.value = 0
            earthShaderUniforms.uOceanTeal.value = 0
          }
          switch (mode) {
            case 'baseOnly':
              earthMaterial.emissiveIntensity = 0
              earthMaterial.visible = true
              _hideAtmo()
              ambientLight.intensity = 0.12
              if (earthShaderUniforms) earthShaderUniforms.uLandDebugMode.value = 0
              break
            case 'emissiveOnly':
              earthMaterial.color.set(0x000000)
              _restoreEmissive()
              earthMaterial.visible = true
              _hideAtmo()
              ambientLight.intensity = 0
              if (earthShaderUniforms) earthShaderUniforms.uLandDebugMode.value = 0
              break
            case 'atmosphereOnly':
              earthMaterial.visible = false
              if (atmosphere) {
                atmosphere.visible = true
                atmosphereMaterial.uniforms.uOpacity.value = 0.35
              }
              if (atmosphere2) {
                atmosphere2.visible = true
                atmosphere2Material.uniforms.uOpacity.value = 0.2
              }
              if (earthShaderUniforms) earthShaderUniforms.uLandDebugMode.value = 0
              break
            case 'landOnly':
              // Land grade + glow vs dim diffuse; city lights zeroed two ways
              earthMaterial.emissiveIntensity = 0
              earthMaterial.visible = true
              _hideAtmo()
              ambientLight.intensity = 0.065
              if (earthShaderUniforms) {
                earthShaderUniforms.uLandDebugMode.value = 1.0
                _zeroOceanShader()
              }
              break
            case 'landGlowOnly':
              // Only land pseudo-emissive; diffuse = black, city = zero
              earthMaterial.color.set(0x000000)
              earthMaterial.emissiveIntensity = 0
              earthMaterial.visible = true
              _hideAtmo()
              ambientLight.intensity = 0
              if (earthShaderUniforms) {
                earthShaderUniforms.uLandDebugMode.value = 1.0
                _zeroOceanShader()
              }
              break
            case 'shadowOnly':
              // Land glow shadow-weight map; greyscale, black = excluded
              earthMaterial.color.set(0x000000)
              earthMaterial.emissiveIntensity = 0
              earthMaterial.visible = true
              _hideAtmo()
              ambientLight.intensity = 0
              if (earthShaderUniforms) {
                earthShaderUniforms.uLandDebugMode.value = 2.0
                _zeroOceanShader()
              }
              break
            case 'oceanMaskOnly':
              // Ocean mask confidence weight: raw _omv×2 greyscale.
              // If full black → uOceanMask uniform is still the 1×1 placeholder (mask not loaded).
              earthMaterial.color.set(0x000000)
              earthMaterial.emissiveIntensity = 0
              earthMaterial.visible = true
              _hideAtmo()
              ambientLight.intensity = 0
              if (earthShaderUniforms) earthShaderUniforms.uLandDebugMode.value = 3.0
              {
                const _maskTex = earthShaderUniforms?.uOceanMask?.value
                const _w = _maskTex?.image?.width  ?? (_maskTex?.image?.videoWidth  ?? '?')
                const _h = _maskTex?.image?.height ?? (_maskTex?.image?.videoHeight ?? '?')
                console.log(
                  '[debug⑧] oceanMaskOnly — maskState:', oceanMaskTextureLoadState,
                  '| uOceanMask uniform:', _maskTex ? (_w + '×' + _h) : 'NULL',
                  '| isPlaceholder:', (_maskTex === _maskPlaceholder || (_w === 1 && _h === 1)),
                  '| uLandDebugMode: 3.0'
                )
                if (oceanMaskTextureLoadState !== 'ready') {
                  console.warn('[debug⑧] ocean mask NOT ready — screen will be black. Check network for /assets/earth/masks/ocean_mask_4096x2048_soft.png')
                }
              }
              break
            case 'oceanGradeOnly':
              // Ocean tone grade only from raw day texture; no city lights.
              earthMaterial.color.set(0xffffff)
              earthMaterial.emissiveIntensity = 0
              earthMaterial.visible = true
              _hideAtmo()
              ambientLight.intensity = 1.0
              sunLight.intensity = 0
              if (earthShaderUniforms) {
                earthShaderUniforms.uLandDebugMode.value = 4.0
                const _ng = THEME_VISUAL_CONFIG[theme]?.nightGrade
                console.log(
                  '[debug⑨] oceanGradeOnly — maskState:', oceanMaskTextureLoadState,
                  '| oceanBlendStrength:', _ng?.oceanBlendStrength ?? earthShaderUniforms.uOceanBlendStrength.value,
                  '| oceanDarken:', _ng?.oceanDarken ?? earthShaderUniforms.uOceanDarken.value,
                  '| oceanContrast:', _ng?.oceanContrast ?? earthShaderUniforms.uOceanContrast.value,
                  '| oceanSaturation:', _ng?.oceanSaturation ?? earthShaderUniforms.uOceanSaturation.value,
                  '| oceanBlueBias:', _ng?.oceanBlueBias ?? earthShaderUniforms.uOceanBlueBias.value,
                  '| oceanRedReduce:', _ng?.oceanRedReduce ?? earthShaderUniforms.uOceanRedReduce.value,
                  '| oceanGreenReduce:', _ng?.oceanGreenReduce ?? earthShaderUniforms.uOceanGreenReduce.value,
                  '| coastProtection:', _ng?.coastProtection ?? earthShaderUniforms.uCoastProtection.value,
                  '| uLandDebugMode: 4.0',
                  '| shader blend actual:', earthShaderUniforms.uOceanBlendStrength.value
                )
              }
              break
            case 'cityMaskOnly':
              // City light luminance mask; needs active emissive → restore night state
              _restoreEmissive()
              earthMaterial.color.set(0x000000)
              earthMaterial.visible = true
              _hideAtmo()
              ambientLight.intensity = 0
              if (earthShaderUniforms) {
                earthShaderUniforms.uLandDebugMode.value = 5.0
                _zeroOceanShader()
              }
              break
            case 'daybaseOnly':
              // v17: show daybase-darkened diffuse only (no city lights, no atmosphere).
              // ambient=1 so the darkened diffuseColor appears at full strength.
              earthMaterial.emissiveIntensity = 0
              earthMaterial.visible = true
              _hideAtmo()
              ambientLight.intensity = 1.0
              sunLight.intensity = 0
              if (earthShaderUniforms) {
                earthShaderUniforms.uLandDebugMode.value = 7.0
              }
              console.log('[debug] daybaseOnly — uDaybaseMode:', earthShaderUniforms?.uDaybaseMode?.value,
                '| uNightExposure:', earthShaderUniforms?.uNightExposure?.value)
              break
            case 'cityColorOnly':
              // City lights with emissiveColor applied; no diffuse, no land, no ocean
              _restoreEmissive()
              earthMaterial.color.set(0x000000)
              earthMaterial.visible = true
              _hideAtmo()
              ambientLight.intensity = 0
              if (earthShaderUniforms) {
                earthShaderUniforms.uLandDebugMode.value = 6.0
                _zeroOceanShader()
              }
              console.log(
                '[debug⑪] cityColorOnly — emissive:', '#' + earthMaterial.emissive.getHexString(),
                '| emissiveIntensity:', earthMaterial.emissiveIntensity,
                '| emissiveMap:', earthMaterial.emissiveMap ? 'SET' : 'NULL',
                '| uLandDebugMode: 6.0',
                '| cityLumLow:', earthShaderUniforms?.uCityLumLow?.value,
                '| cityLumHigh:', earthShaderUniforms?.uCityLumHigh?.value
              )
              break
            case 'final':
            default:
              earthMaterial.visible = true
              if (atmosphere) atmosphere.visible = true
              applyTheme(theme, { force: true })
              break
          }
          requestRenderUpdate()
          console.log('[earth3d] debugLayer:', mode)
        },
      })
      window.__earth3dBootStage = 'after-api-export'

      // ── Star system debug API (dev/audit only) ─────────────────────────────
      window.earth3dDebug = {
        starState() {
          return {
            starSphereInScene: Boolean(starSphere?.parent),
            starSphereVisible: Boolean(starSphere?.visible),
            starSphereOpacity: starSphereMaterial?.opacity ?? null,
            starSphereLoaded,
            proceduralStarsInScene: Boolean(stars?.parent),
            proceduralStarsVisible: Boolean(stars?.visible),
            proceduralStarsOpacity: stars?.material?.opacity ?? null,
            skyMeshOpacity: skyMaterial?.uniforms?.uOpacity?.value ?? null,
            STAR_SPHERE_OPACITY_deepNight: STAR_SPHERE_OPACITY['deepNight'],
          }
        },
        showSkyDomeOnly() {
          if (starSphere) starSphere.visible = false
          if (stars) stars.visible = false
          if (skyMesh) { skyMesh.visible = true; skyMaterial.uniforms.uOpacity.value = 1.0 }
          requestRenderUpdate()
        },
        hideSkyDome() {
          if (skyMesh) { skyMesh.visible = false; skyMaterial.uniforms.uEnabled.value = 0 }
          requestRenderUpdate()
        },
        showProceduralStarsOnly() {
          if (starSphere) starSphere.visible = false
          if (skyMesh) skyMesh.visible = false
          if (stars) { stars.visible = true; stars.material.opacity = 0.8 }
          requestRenderUpdate()
        },
        hideProceduralStars() {
          if (stars) { stars.material.opacity = 0; stars.material.needsUpdate = true }
          requestRenderUpdate()
        },
        showStarmapOnly() {
          if (stars) { stars.material.opacity = 0; stars.material.needsUpdate = true }
          if (skyMesh) { skyMesh.visible = false; skyMaterial.uniforms.uEnabled.value = 0 }
          if (starSphere) { starSphere.visible = true; starSphereMaterial.uniforms.uOpacity.value = 1.0; }
          requestRenderUpdate()
        },
        setSkyDomeOpacity(v) {
          if (skyMaterial?.uniforms) { skyMaterial.uniforms.uOpacity.value = v; skyMesh.visible = v > 0 }
          requestRenderUpdate()
        },
        setStarmapOpacity(v) {
          if (starSphereMaterial) { starSphereMaterial.uniforms.uOpacity.value = v; if (starSphere) starSphere.visible = v > 0 }
          requestRenderUpdate()
        },
        setProceduralStarsOpacity(v) {
          if (stars?.material) { stars.material.opacity = v; stars.material.needsUpdate = true; stars.visible = v > 0 }
          requestRenderUpdate()
        },
        restoreNormal() {
          if (skyMesh) { skyMesh.visible = true; skyMaterial.uniforms.uEnabled.value = 1 }
          if (starSphere) starSphere.visible = true
          if (stars) stars.visible = true
          window.earth3d.setTimeOfDay(currentTheme || 'deepNight')
        },
      }

      return true
    } catch (error) {
      isReady = false
      permanentlyUnavailable = true
      window.__earth3dBootstrapError = String(error?.stack || error)
      if (renderer) renderer.dispose()
      if (mountEl) mountEl.innerHTML = ''
      window.__earth3dDeletedAt = 'catch'
      delete window.earth3d
      console.warn('[earth3d] 3D renderer unavailable, falling back to canvas visuals', error)
      return false
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createEarth3D, { once: true })
  } else {
    createEarth3D()
  }
})()
