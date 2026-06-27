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
    for (let i = 0; i < count; i += 1) {
      const u = Math.random()
      const v = Math.random()
      const theta = 2 * Math.PI * u
      const phi = Math.acos(2 * v - 1)
      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = radius * Math.cos(phi)
      positions[i * 3 + 2] = radius * Math.sin(phi) * Math.sin(theta)
    }
    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
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
    let earthMaterial = null
    let atmosphereMaterial = null
    let tileManager = null
    let dayTexture = null
    let nightTexture = null
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
    let isReady = false
    let permanentlyUnavailable = false

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

      function getSkyThemePreset(themeKey) {
        switch (themeKey) {
          case 'dawn':
            return {
              top: '#03040a',
              horizon: '#567f95',
              bottom: '#341932',
              opacity: 0.96,
            }
          case 'sunrise':
            return {
              top: '#0f1629',
              horizon: '#7ab6d8',
              bottom: '#38203f',
              opacity: 0.95,
            }
          case 'earlyMorning':
            return {
              top: '#16284f',
              horizon: '#c6d8e5',
              bottom: '#456995',
              opacity: 0.94,
            }
          case 'morning':
            return {
              top: '#113062',
              horizon: '#c0d5e7',
              bottom: '#356ca5',
              opacity: 0.94,
            }
          case 'noon':
            return {
              top: '#0b295d',
              horizon: '#c7dcee',
              bottom: '#2d689b',
              opacity: 0.93,
            }
          case 'afternoon':
            return {
              top: '#10306e',
              horizon: '#c8d2c4',
              bottom: '#0d285e',
              opacity: 0.93,
            }
          case 'goldenApproach':
            return {
              top: '#0e2a62',
              horizon: '#d2bb78',
              bottom: '#e6e1d6',
              opacity: 0.93,
            }
          case 'sunset':
            return {
              top: '#0a162f',
              horizon: '#c7a665',
              bottom: '#4a1d30',
              opacity: 0.95,
            }
          case 'evening':
            return {
              top: '#040812',
              horizon: '#182239',
              bottom: '#09101e',
              opacity: 0.97,
            }
          case 'lateEvening':
            return {
              top: '#03050b',
              horizon: '#101a2b',
              bottom: '#111a2e',
              opacity: 0.98,
            }
          case 'night':
          case 'deepNight':
          default:
            return {
              top: '#010205',
              horizon: '#070d17',
              bottom: '#03060c',
              opacity: 0.98,
            }
        }
      }

      function updateSkyTheme(themeKey) {
        if (!skyMaterial || !skyMaterial.uniforms) return
        const preset = getSkyThemePreset(themeKey)
        skyMaterial.uniforms.uColorTop.value.set(preset.top)
        skyMaterial.uniforms.uColorHorizon.value.set(preset.horizon)
        skyMaterial.uniforms.uColorBottom.value.set(preset.bottom)
        skyMaterial.uniforms.uOpacity.value = preset.opacity
        skyMaterial.uniforms.uEnabled.value = skyMesh?.visible ? 1 : 0
      }

      // 白天 tint 仍置 0（A/B 测试阶段，不干扰 dayTexture 判断）。
      // 夜晚主题补充极弱冷深蓝，给海洋添加暗部层次，不影响城市灯光。
      const OCEAN_TINT_BY_THEME = {
        morning:    { color: 0x164556, strength: 0 },
        noon:       { color: 0x1a4f5f, strength: 0 },
        afternoon:  { color: 0x123847, strength: 0 },
        evening:    { color: 0x071827, strength: 0.08 },
        lateEvening:{ color: 0x061522, strength: 0.09 },
        deepNight:  { color: 0x04101A, strength: 0.10 },
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
        const distance = Number.isFinite(cameraState.distance) ? cameraState.distance : 4.8
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
        const radiusX = Math.max(0, Math.ceil(fov / (360 / tileCols) / 2))
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
              console.warn('[tile-stream] tile unavailable:', key, url)
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
          if (this.atlasContext) {
            this.atlasContext.fillStyle = '#020514'
            this.atlasContext.fillRect(0, 0, width, height)
          }
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
      loadNormalMapTexture()
      earthGeometry = new THREE.SphereGeometry(2, 128, 128)
      const earth = new THREE.Mesh(earthGeometry, earthMaterial)
      atmosphereMaterial = new THREE.MeshPhongMaterial({
        color: new THREE.Color('#7ab8e6'),
        transparent: true,
        opacity: 0.12,
        depthWrite: false,
        side: THREE.BackSide,
      })
      atmosphere = new THREE.Mesh(
        new THREE.SphereGeometry(2.07, 128, 128),
        atmosphereMaterial
      )

      const earthGroup = new THREE.Group()
      earthGroup.position.set(0, -1.4, 0)
      // earthGroup.rotation.z = THREE.MathUtils.degToRad(23.4)
      earth.add(atmosphere)
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

      function updateRDLOverlays() {
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
            const isTarget = entry.region.id === _rdlInspectRegion
            entry.mesh.visible = isTarget
            if (isTarget) entry.mat.uniforms.uOpacity.value = 0.995
          })
        } else {
          // Normal mode: only the single most-facing region, above threshold
          const best = scores.reduce((a, b) => a.facingOpacity > b.facingOpacity ? a : b)
          scores.forEach(({ entry, facingOpacity }) => {
            const isBest = entry.region.id === best.entry.region.id
            const opacity = isBest && best.facingOpacity > 0.25 ? best.facingOpacity * 0.70 : 0.0
            entry.mesh.visible = opacity > 0.005
            if (opacity > 0.005) entry.mat.uniforms.uOpacity.value = opacity
          })
        }
      }
      // ──────────────────────────────────────────────────────────────────────

      stars = new THREE.Points(
        buildStarField(900, 60),
        new THREE.PointsMaterial({
          color: 0xffffff,
          size: 0.038,
          sizeAttenuation: true,
          transparent: true,
          opacity: 0.78,
        })
      )
      scene.add(stars)

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
      const THEME_VISUAL_CONFIG = {
        dawn: {
          themeHour: 5.4,
          texture: {
            map: 'day',
            emissiveMap: 'night',
            mapColor: 0x667780,
            emissiveColor: 0xffe6b6,
            emissiveIntensity: 0.72,
            nightBaseIntensity: 0.34,
          },
          material: {
            specular: 0x000102,
            shininess: 0.12,
          },
          atmosphere: {
            color: '#567f95',
            opacity: 0.078,
          },
          lighting: {
            ambient: 0.048,
            sun: 0.18,
            stars: 0.42,
            cityLightsOpacity: 0.60,
          },
        },
        sunrise: {
          themeHour: 6.3,
          texture: {
            map: 'day',
            emissiveMap: 'night',
            mapColor: 0x96a6ae,
            emissiveColor: 0xffe3b0,
            emissiveIntensity: 0.46,
            nightBaseIntensity: 0.20,
          },
          material: {
            specular: 0x000102,
            shininess: 0.16,
          },
          atmosphere: {
            color: '#7ab6d8',
            opacity: 0.106,
          },
          lighting: {
            ambient: 0.072,
            sun: 0.48,
            stars: 0.2,
            cityLightsOpacity: 0.26,
          },
        },
        earlyMorning: {
          themeHour: 7.4,
          texture: {
            map: 'day',
            emissiveMap: 'night',
            mapColor: 0xc3d1da,
            emissiveColor: 0xffddb0,
            emissiveIntensity: 0.10,
          },
          material: {
            specular: 0x020407,
            shininess: 0.55,
          },
          atmosphere: {
            color: '#86c4e6',
            opacity: 0.11,
          },
          lighting: {
            ambient: 0.068,
            sun: 0.72,
            stars: 0.08,
            cityLightsOpacity: 0.10,
          },
        },
        morning: {
          themeHour: 9.5,
          texture: {
            map: 'day',
            emissiveMap: null,
            mapColor: 0xffffff,
            emissiveColor: 0x000000,
            emissiveIntensity: 0,
          },
          material: {
            specular: 0x0a1018,
            shininess: 120,
          },
          atmosphere: {
            color: '#83c3e7',
            opacity: 0.142,
          },
          lighting: {
            ambient: 0.09,
            sun: 1.05,
            stars: 0.04,
            cityLightsOpacity: 0,
          },
        },
        noon: {
          themeHour: 13,
          texture: {
            map: 'day',
            emissiveMap: null,
            mapColor: 0xffffff,
            emissiveColor: 0x000000,
            emissiveIntensity: 0,
          },
          material: {
            specular: 0x0c1420,
            shininess: 150,
          },
          atmosphere: {
            color: '#b0d9ed',
            opacity: 0.14,
          },
          lighting: {
            ambient: 0.12,
            sun: 1.25,
            stars: 0.01,
            cityLightsOpacity: 0,
          },
        },
        afternoon: {
          themeHour: 15.4,
          texture: {
            map: 'day',
            emissiveMap: null,
            mapColor: 0xf2f4f5,
            emissiveColor: 0x000000,
            emissiveIntensity: 0,
          },
          material: {
            specular: 0x0a1018,
            shininess: 120,
          },
          atmosphere: {
            color: '#7eb6e1',
            opacity: 0.13,
          },
          lighting: {
            ambient: 0.078,
            sun: 0.96,
            stars: 0.008,
            cityLightsOpacity: 0,
          },
        },
        goldenApproach: {
          themeHour: 16.5,
          texture: {
            map: 'day',
            emissiveMap: null,
            mapColor: 0xeee8dc,
            emissiveColor: 0x000000,
            emissiveIntensity: 0,
          },
          material: {
            specular: 0x180e04,
            shininess: 60,
          },
          atmosphere: {
            color: '#b7a169',
            opacity: 0.095,
          },
          lighting: {
            ambient: 0.052,
            sun: 0.88,
            stars: 0,
            cityLightsOpacity: 0,
          },
        },
        sunset: {
          themeHour: 18.2,
          texture: {
            map: 'day',
            emissiveMap: 'night',
            mapColor: 0xb4c2cb,
            emissiveColor: 0xffdca3,
            emissiveIntensity: 0.16,
          },
          material: {
            specular: 0x000102,
            shininess: 0.18,
          },
          atmosphere: {
            color: '#628fb5',
            opacity: 0.072,
          },
          lighting: {
            ambient: 0.058,
            sun: 0.40,
            stars: 0.26,
            cityLightsOpacity: 0.18,
          },
        },
        evening: {
          themeHour: 20.2,
          texture: {
            // Keep day texture as a dark base so the globe shape is visible even
            // over ocean. City lights (emissive) dominate in populated areas.
            map: 'day',
            emissiveMap: 'night',
            mapColor: 0x050912,
            emissiveColor: 0xffd08a,
            emissiveIntensity: 2.2,
          },
          material: {
            specular: 0x000102,
            shininess: 0.10,
          },
          atmosphere: {
            color: '#162234',
            opacity: 0.154,
          },
          lighting: {
            ambient: 0.06,
            sun: 0.04,
            stars: 0.68,
            cityLightsOpacity: 0.58,
          },
        },
        lateEvening: {
          themeHour: 21.0,
          texture: {
            map: 'day',
            emissiveMap: 'night',
            mapColor: 0x030710,
            emissiveColor: 0xffc068,
            emissiveIntensity: 2.35,
          },
          material: {
            specular: 0x000102,
            shininess: 0.09,
          },
          atmosphere: {
            color: '#101826',
            opacity: 0.142,
          },
          lighting: {
            ambient: 0.038,
            sun: 0.015,
            stars: 0.62,
            cityLightsOpacity: 0.58,
          },
        },
        deepNight: {
          themeHour: 22.5,
          texture: {
            map: 'day',
            emissiveMap: 'night',
            mapColor: 0x02050B,
            emissiveColor: 0xffbe63,
            emissiveIntensity: 2.5,
          },
          material: {
            specular: 0x000001,
            shininess: 0.08,
          },
          atmosphere: {
            color: '#08131f',
            opacity: 0.13,
          },
          lighting: {
            ambient: 0.025,
            sun: 0.008,
            stars: 0.82,
            cityLightsOpacity: 0.58,
          },
        },
        night: {
          themeHour: 22.5,
          texture: {
            map: 'day',
            emissiveMap: 'night',
            mapColor: 0x040810,
            emissiveColor: 0xffc86e,
            emissiveIntensity: 2.0,
          },
          material: {
            specular: 0x05070a,
            shininess: 1,
          },
          atmosphere: {
            color: '#0c1521',
            opacity: 0.138,
          },
          lighting: {
            ambient: 0.05,
            sun: 0.03,
            stars: 0.78,
            cityLightsOpacity: 0.58,
          },
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

        earthMaterial.map = config.texture.map === 'day' ? dayTexture : null
        earthMaterial.color.set(config.texture.mapColor)
        earthMaterial.emissive.set(useNightEmissive ? config.texture.emissiveColor : 0x000000)
        earthMaterial.emissiveMap = useNightEmissive ? nightTexture : null
        earthMaterial.emissiveIntensity = useNightEmissive ? config.texture.emissiveIntensity : 0
        applySurfaceDetailTuning(resolvedTheme, config)
        atmosphereMaterial.color.set(config.atmosphere.color)
        atmosphereMaterial.opacity = config.atmosphere.opacity
        ambientLight.intensity = config.lighting.ambient
        sunLight.intensity = config.lighting.sun
        if (stars?.material) {
          stars.material.opacity = config.lighting.stars
          stars.material.needsUpdate = true
        }
        updateSkyTheme(resolvedTheme)
        applyOceanTint(resolvedTheme)

        currentTheme = resolvedTheme
        pendingTheme = resolvedTheme
        earthMaterial.needsUpdate = true
        atmosphereMaterial.needsUpdate = true
        logThemeAudit(themeKey, resolvedTheme, config, true, requiredTextures, missingTextures)
        return true
      }

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
        '/assets/blackmarble.jpg',
        (texture, usedPath) => {
          nightTexture = texture
          console.log('[earth3d] night texture loaded:', usedPath)

          if (typeof applyTheme === 'function') {
            const themeKey = pendingTheme || currentTheme || 'night'
            const applied = applyTheme(themeKey, { force: true })
            syncRevealState(themeKey, applied)
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
      function updateSunPosition(_hour) {
        if (auditLightingMode && camera) {
          const d = 10
          const dir = camera.position.clone().normalize()
          sunLight.position.set(dir.x * d, dir.y * d, dir.z * d)
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

      function buildDebugState() {
        const rendererCanvas = renderer?.domElement || null
        const rendererContext = renderer?.getContext ? renderer.getContext() : null
        const theme = {
          currentTheme,
          pendingTheme,
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
        renderer.setSize(width, height, false)
        camera.aspect = width / height
        camera.updateProjectionMatrix()
        updateVisualTargetDir()
      }

      observer = new ResizeObserver(() => resize())
      observer.observe(appEl)
      resize()
      updateVisualTargetDir()

      // ─── Scroll-wheel zoom ────────────────────────────────────────────────
      // Zooms by changing camera FOV (28° = global view, 8° = max zoom-in).
      // _rdlZoomLevel drives the RDL regional overlay opacity.
      const _RDL_FOV_NORMAL = 28
      const _RDL_FOV_MIN    = 8
      const _AUDIT_VIEW_ANGLES = {
        top: { y: 0.0, z: 4.8, lookY: -1.4 },
        oblique: { y: 1.35, z: 5.05, lookY: -1.2 },
        low: { y: 2.15, z: 5.45, lookY: -0.9 },
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
      applyTheme(pendingTheme)

      let _animDirty = true
      let _animFrameCount = 0

      renderer.setAnimationLoop(() => {
        if (!isReady || permanentlyUnavailable) return
        _animFrameCount++
        const target = getTargetOrientation(useAuditCenterTarget ? auditCenterDir : null)
        const isAnimating = earth.quaternion.angleTo(target) > 0.0002
        earth.quaternion.slerp(target, 0.02)
        atmosphere.rotation.set(0, 0, 0)

        if (isAnimating || _animDirty) {
          updateStreaming(camera)
          updateRDLOverlays()
          if (!isAnimating) _animDirty = false
        } else if (_animFrameCount % 10 === 0) {
          // Maintenance tick: keep RDL opacity in sync without tile work
          updateRDLOverlays()
        }

        renderer.render(scene, camera)
      })

      _sunUpdateInterval = setInterval(updateSunPosition, 60000)

      visibilityChangeHandler = () => {
        if (document.hidden) return
      }
      document.addEventListener('visibilitychange', visibilityChangeHandler)

      window.earth3d = {
        get isReady() {
          return isReady
        },
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

          earth.updateMatrixWorld(true)
          atmosphere.updateMatrixWorld(true)
          earthGroup.updateMatrixWorld(true)
          scene.updateMatrixWorld(true)
          camera.updateMatrixWorld(true)
          updateStreaming(camera)
          updateRDLOverlays()
          renderer.render(scene, camera)

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
          syncRevealState(themeKey, applied)
          updateSunPosition()
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
          camera.position.set(0, preset.y, preset.z)
          camera.lookAt(0, preset.lookY, 0)
          camera.updateProjectionMatrix()
          if (auditLightingMode) {
            const themeKey = pendingTheme || currentTheme || 'noon'
            applyTheme(themeKey, { force: true })
          }
          refreshRDLTextureSampling()
          updateSunPosition()
          requestRenderUpdate()
          return Object.prototype.hasOwnProperty.call(_AUDIT_VIEW_ANGLES, angle) ? angle : 'top'
        },
        getDebugState() {
          return buildDebugState()
        },
        dispose() {
          isReady = false
          isDestroyed = true
          renderer.setAnimationLoop(null)
          if (_sunUpdateInterval) { clearInterval(_sunUpdateInterval); _sunUpdateInterval = null }
          if (visibilityChangeHandler) {
            document.removeEventListener('visibilitychange', visibilityChangeHandler)
            visibilityChangeHandler = null
          }
          if (renderer?.domElement) renderer.domElement.style.opacity = '0'
          if (observer) observer.disconnect()
          if (skyGeometry) skyGeometry.dispose()
          if (skyMaterial) skyMaterial.dispose()
          if (earthGeometry) earthGeometry.dispose()
          if (atmosphere?.geometry) atmosphere.geometry.dispose()
          if (stars?.geometry) stars.geometry.dispose()
          skyGeometry = null
          skyMaterial = null
          skyMesh = null
          if (earthMaterial) earthMaterial.dispose()
          if (atmosphereMaterial) atmosphereMaterial.dispose()
          if (stars?.material) stars.material.dispose()
          if (tileManager) {
            tileManager.dispose()
            tileManager = null
            dayTexture = null
          } else if (dayTexture) {
            dayTexture.dispose()
          }
          if (nightTexture) nightTexture.dispose()
          if (oceanSpecularTexture) oceanSpecularTexture.dispose()
          if (normalMapTexture) normalMapTexture.dispose()
          if (oceanTintMesh?.parent) oceanTintMesh.parent.remove(oceanTintMesh)
          if (oceanTintGeometry) oceanTintGeometry.dispose()
          if (oceanTintMaterial) oceanTintMaterial.dispose()
          if (oceanMaskTexture) oceanMaskTexture.dispose()
          renderer.dispose()
          mountEl.innerHTML = ''
          delete window.earth3d
        },
      }
      return true
    } catch (error) {
      isReady = false
      permanentlyUnavailable = true
      if (renderer) renderer.dispose()
      if (mountEl) mountEl.innerHTML = ''
      delete window.earth3d
      console.warn('[earth3d] 3D renderer unavailable, falling back to canvas visuals')
      return false
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createEarth3D, { once: true })
  } else {
    createEarth3D()
  }
})()
