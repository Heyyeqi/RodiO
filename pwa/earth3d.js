(function () {
  const TEXTURE_LON_OFFSET = 90
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
    let earthGeometry = null
    let atmosphere = null
    let stars = null
    let earthMaterial = null
    let atmosphereMaterial = null
    let dayTexture = null
    let nightTexture = null
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

      const loader = new THREE.TextureLoader()
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

      function loadTextureWithFallback(primaryPath, fallbackPath, onLoad) {
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

      earthMaterial = new THREE.MeshPhongMaterial({
        color: 0x1a3a5c,
        shininess: 1,
        specular: new THREE.Color(0x05070a),
      })
      earthGeometry = new THREE.SphereGeometry(2, 64, 64)
      const earth = new THREE.Mesh(earthGeometry, earthMaterial)
      atmosphereMaterial = new THREE.MeshPhongMaterial({
        color: new THREE.Color('#88ccff'),
        transparent: true,
        opacity: 0.13,
        depthWrite: false,
        side: THREE.BackSide,
      })
      atmosphere = new THREE.Mesh(
        new THREE.SphereGeometry(2.07, 64, 64),
        atmosphereMaterial
      )

      const earthGroup = new THREE.Group()
      earthGroup.position.set(0, -1.4, 0)
      // earthGroup.rotation.z = THREE.MathUtils.degToRad(23.4)
      earth.add(atmosphere)
      earthGroup.add(earth)

      const VISUAL_TARGET_NDC = new THREE.Vector2(0.25, -0.24)
      const visualRaycaster = new THREE.Raycaster()
      const visualTargetDir = new THREE.Vector3(0, 0, 1)

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

      stars = new THREE.Points(
        buildStarField(1200, 60),
        new THREE.PointsMaterial({
          color: 0xffffff,
          size: 0.05,
          sizeAttenuation: true,
          transparent: true,
          opacity: 0.9,
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
            color: '#6fb8ff',
            opacity: 0.082,
          },
          lighting: {
            ambient: 0.032,
            sun: 0.18,
            stars: 0.55,
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
            color: '#8ad0ff',
            opacity: 0.115,
          },
          lighting: {
            ambient: 0.055,
            sun: 0.48,
            stars: 0.24,
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
            color: '#8ecfff',
            opacity: 0.12,
          },
          lighting: {
            ambient: 0.052,
            sun: 0.72,
            stars: 0.12,
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
            specular: 0x05070a,
            shininess: 1,
          },
          atmosphere: {
            color: '#88ccff',
            opacity: 0.15,
          },
          lighting: {
            ambient: 0.06,
            sun: 1.05,
            stars: 0.08,
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
            specular: 0x05070a,
            shininess: 1,
          },
          atmosphere: {
            color: '#B7E3FF',
            opacity: 0.15,
          },
          lighting: {
            ambient: 0.09,
            sun: 1.25,
            stars: 0.02,
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
            specular: 0x04060a,
            shininess: 0.9,
          },
          atmosphere: {
            color: '#84bdf0',
            opacity: 0.14,
          },
          lighting: {
            ambient: 0.048,
            sun: 0.96,
            stars: 0.01,
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
            color: '#6a9fd1',
            opacity: 0.075,
          },
          lighting: {
            ambient: 0.046,
            sun: 0.40,
            stars: 0.34,
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
            color: '#254061',
            opacity: 0.18,
          },
          lighting: {
            ambient: 0.06,
            sun: 0.04,
            stars: 0.78,
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
            color: '#112844',
            opacity: 0.16,
          },
          lighting: {
            ambient: 0.025,
            sun: 0.008,
            stars: 0.94,
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
            color: '#1B3350',
            opacity: 0.17,
          },
          lighting: {
            ambient: 0.05,
            sun: 0.03,
            stars: 0.9,
            cityLightsOpacity: 0.58,
          },
        },
      }

      function getThemeVisualConfig(themeKey) {
        return (
          THEME_VISUAL_CONFIG[themeKey]
          || THEME_VISUAL_CONFIG[currentTheme]
          || THEME_VISUAL_CONFIG[pendingTheme]
          || THEME_VISUAL_CONFIG.night
        )
      }

      function getTargetOrientation() {
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

        const targetNormal = visualTargetDir.clone().normalize()

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
        earthMaterial.specular.set(config.material.specular)
        earthMaterial.shininess = config.material.shininess
        atmosphereMaterial.color.set(config.atmosphere.color)
        atmosphereMaterial.opacity = config.atmosphere.opacity
        ambientLight.intensity = config.lighting.ambient
        sunLight.intensity = config.lighting.sun
        if (stars?.material) {
          stars.material.opacity = config.lighting.stars
          stars.material.needsUpdate = true
        }

        currentTheme = resolvedTheme
        pendingTheme = resolvedTheme
        earthMaterial.needsUpdate = true
        atmosphereMaterial.needsUpdate = true
        logThemeAudit(themeKey, resolvedTheme, config, true, requiredTextures, missingTextures)
        return true
      }

      loadTextureWithFallback(
        '/assets/earth_day_8k.jpg',
        '/assets/bluemarble.jpg',
        (texture, usedPath) => {
          dayTexture = texture
          console.log('[earth3d] day texture loaded:', usedPath)

          if (typeof applyTheme === 'function') {
            // Use pendingTheme as authoritative source: it was seeded from time-of-day
            // at startup and updated by setTimeOfDay() when external state changes.
            // Avoid reading __rodioVisualState.themeKey here — it starts as 'night'.
            const themeKey = pendingTheme || currentTheme || 'night'
            const applied = applyTheme(themeKey, { force: true })
            syncRevealState(themeKey, applied)
          } else {
            earthMaterial.map = texture
            earthMaterial.needsUpdate = true
          }
        }
      )

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

      function updateSunPosition(hour) {
        const h = ((hour % 24) + 24) % 24
        let from
        let to
        let t
        if (h < 6) {
          from = [-4, -1, 3]
          to = [-1, 0, 4]
          t = h / 6
        } else if (h < 12) {
          from = [-1, 0, 4]
          to = [4, 3, 3]
          t = (h - 6) / 6
        } else if (h < 18) {
          from = [4, 3, 3]
          to = [1, 0, 4]
          t = (h - 12) / 6
        } else {
          from = [1, 0, 4]
          to = [-4, -1, 3]
          t = (h - 18) / 6
        }
        sunLight.position.set(
          lerp(from[0], to[0], t),
          lerp(from[1], to[1], t),
          lerp(from[2], to[2], t)
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
        }
        const material = {
          mapExists: Boolean(earthMaterial?.map),
          mapIsDayTexture: Boolean(earthMaterial?.map && earthMaterial.map === dayTexture),
          emissiveMapExists: Boolean(earthMaterial?.emissiveMap),
          emissiveMapIsNightTexture: Boolean(earthMaterial?.emissiveMap && earthMaterial.emissiveMap === nightTexture),
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

        return {
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
          mapExists: material.mapExists,
          mapIsDayTexture: material.mapIsDayTexture,
          emissiveMapExists: material.emissiveMapExists,
          emissiveMapIsNightTexture: material.emissiveMapIsNightTexture,
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
        }
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
      const initialOrientation = getTargetOrientation()
      earth.quaternion.copy(initialOrientation)
      atmosphere.rotation.set(0, 0, 0)
      updateSunPosition(new Date().getHours())
      applyTheme(pendingTheme)

      renderer.setAnimationLoop(() => {
        if (!isReady || permanentlyUnavailable) return
        const target = getTargetOrientation()
        earth.quaternion.slerp(target, 0.02)
        atmosphere.rotation.set(0, 0, 0)

        renderer.render(scene, camera)
      })

      window.earth3d = {
        get isReady() {
          return isReady
        },
        isAvailable() {
          return isReady && !permanentlyUnavailable
        },
        setDebugLocation(lon, lat) {
          window.__rodioVisualState = {
            ...(window.__rodioVisualState || {}),
            lon,
            lat
          }

          const target = getTargetOrientation()
          earth.quaternion.copy(target)
          atmosphere.rotation.set(0, 0, 0)

          earth.updateMatrixWorld(true)
          atmosphere.updateMatrixWorld(true)
          earthGroup.updateMatrixWorld(true)
          scene.updateMatrixWorld(true)
          camera.updateMatrixWorld(true)
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
          updateSunPosition(getThemeHour(themeKey))
          return applied
        },
        getDebugState() {
          return buildDebugState()
        },
        dispose() {
          isReady = false
          renderer.setAnimationLoop(null)
          if (renderer?.domElement) renderer.domElement.style.opacity = '0'
          if (observer) observer.disconnect()
          if (earthGeometry) earthGeometry.dispose()
          if (atmosphere?.geometry) atmosphere.geometry.dispose()
          if (stars?.geometry) stars.geometry.dispose()
          if (earthMaterial) earthMaterial.dispose()
          if (atmosphereMaterial) atmosphereMaterial.dispose()
          if (stars?.material) stars.material.dispose()
          if (dayTexture) dayTexture.dispose()
          if (nightTexture) nightTexture.dispose()
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
