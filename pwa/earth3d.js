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
        texture.colorSpace = THREE.SRGBColorSpace
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

      let cityLightsTexture = null

      earthMaterial = new THREE.MeshPhongMaterial({
        color: 0x1a3a5c,
        shininess: 1,
        specular: new THREE.Color(0x05070a),
      })
      earthGeometry = new THREE.SphereGeometry(2, 64, 64)
      const earth = new THREE.Mesh(earthGeometry, earthMaterial)
      const cityLightsMaterial = new THREE.MeshBasicMaterial({
        color: new THREE.Color(0xfff7e8),
        transparent: true,
        opacity: 0,
        depthWrite: false,
        depthTest: true,
        blending: THREE.AdditiveBlending,
      })
      const cityLightsMesh = new THREE.Mesh(
        new THREE.SphereGeometry(2.004, 64, 64),
        cityLightsMaterial
      )
      cityLightsMesh.renderOrder = 5
      cityLightsMesh.visible = false

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
      earth.add(cityLightsMesh)
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

        console.log(
          '[earth3d] visual target ndc =',
          VISUAL_TARGET_NDC.x.toFixed(3),
          VISUAL_TARGET_NDC.y.toFixed(3)
        )

        console.log(
          '[earth3d] earth center world =',
          earthCenterWorld.x.toFixed(3),
          earthCenterWorld.y.toFixed(3),
          earthCenterWorld.z.toFixed(3)
        )

        console.log(
          '[earth3d] visual ray origin =',
          visualRaycaster.ray.origin.x.toFixed(3),
          visualRaycaster.ray.origin.y.toFixed(3),
          visualRaycaster.ray.origin.z.toFixed(3)
        )

        console.log(
          '[earth3d] visual ray direction =',
          visualRaycaster.ray.direction.x.toFixed(3),
          visualRaycaster.ray.direction.y.toFixed(3),
          visualRaycaster.ray.direction.z.toFixed(3)
        )

        console.log('[earth3d] visual target hit =', Boolean(intersection))

        if (!intersection) {
          visualTargetDir.set(0, 0, 1)
        } else {
          console.log(
            '[earth3d] visual hit world =',
            hit.x.toFixed(3),
            hit.y.toFixed(3),
            hit.z.toFixed(3)
          )

          const localHit = earth.worldToLocal(hit.clone())

          console.log(
            '[earth3d] visual hit local =',
            localHit.x.toFixed(3),
            localHit.y.toFixed(3),
            localHit.z.toFixed(3)
          )

          visualTargetDir.copy(localHit.normalize())
        }

        earth.quaternion.copy(savedQuaternion)
        earth.updateMatrixWorld(true)

        console.log(
          '[earth3d] visualTargetDir final =',
          visualTargetDir.x.toFixed(3),
          visualTargetDir.y.toFixed(3),
          visualTargetDir.z.toFixed(3)
        )
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
            emissiveColor: 0xffffff,
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
            emissiveColor: 0xffffff,
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
            emissiveColor: 0xffffff,
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
            color: '#88ccff',
            opacity: 0.15,
          },
          lighting: {
            ambient: 0.05,
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
            emissiveColor: 0xffffff,
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
            map: null,
            emissiveMap: 'night',
            mapColor: 0x010204,
            emissiveColor: 0xffffff,
            emissiveIntensity: 1.38,
            nightBaseIntensity: 0.40,
          },
          material: {
            specular: 0x000102,
            shininess: 0.10,
          },
          atmosphere: {
            color: '#061027',
            opacity: 0.042,
          },
          lighting: {
            ambient: 0.010,
            sun: 0.04,
            stars: 0.78,
            cityLightsOpacity: 0.58,
          },
        },
        deepNight: {
          themeHour: 22.5,
          texture: {
            map: null,
            emissiveMap: 'night',
            mapColor: 0x000000,
            emissiveColor: 0xffffff,
            emissiveIntensity: 1.18,
            nightBaseIntensity: 0.34,
          },
          material: {
            specular: 0x000001,
            shininess: 0.08,
          },
          atmosphere: {
            color: '#040912',
            opacity: 0.022,
          },
          lighting: {
            ambient: 0.004,
            sun: 0.008,
            stars: 0.94,
            cityLightsOpacity: 0.58,
          },
        },
        night: {
          themeHour: 22.5,
          texture: {
            map: null,
            emissiveMap: 'night',
            mapColor: 0x000000,
            emissiveColor: 0xffffff,
            emissiveIntensity: 1.55,
            nightBaseIntensity: 0.38,
          },
          material: {
            specular: 0x05070a,
            shininess: 1,
          },
          atmosphere: {
            color: '#040912',
            opacity: 0.028,
          },
          lighting: {
            ambient: 0.006,
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
      let pendingTheme = 'night'

      function getRequiredTextures(themeKey) {
        const config = getThemeVisualConfig(themeKey)
        if (!config) return []

        // Stable 4D path: the earth body always depends on the day texture.
        // City lights are an optional enhancement layer and must never block
        // the base globe from rendering.
        const required = new Set()
        required.add('day')
        if (config.texture.map === 'night') required.add('night')
        if (config.texture.emissiveMap === 'day') required.add('day')
        if (
          config.texture.emissiveMap === 'night'
          && (
            (config.lighting?.cityLightsOpacity || 0) <= 0
            || (config.texture.nightBaseIntensity || 0) > 0
          )
        ) {
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

      function applyTheme(themeKey, options = {}) {
        const resolvedTheme = themeKey || pendingTheme || currentTheme || 'night'
        if (currentTheme === resolvedTheme && options.force !== true) return true

        const config = getThemeVisualConfig(resolvedTheme)
        if (!areRequiredTexturesReady(resolvedTheme)) {
          pendingTheme = resolvedTheme
          return false
        }

        const cityLightsOpacity = config.lighting?.cityLightsOpacity || 0
        const nightBaseIntensity = config.texture.nightBaseIntensity || 0
        const shouldUseNightBase = config.texture.emissiveMap === 'night'
          && (cityLightsOpacity <= 0 || nightBaseIntensity > 0)

        earthMaterial.map = config.texture.map === 'day' ? dayTexture : null
        earthMaterial.color.set(config.texture.mapColor)
        earthMaterial.emissive.set(shouldUseNightBase ? config.texture.emissiveColor : 0x000000)
        earthMaterial.emissiveMap = shouldUseNightBase ? nightTexture : null
        earthMaterial.emissiveIntensity = shouldUseNightBase
          ? (cityLightsOpacity > 0 ? nightBaseIntensity : config.texture.emissiveIntensity)
          : 0
        earthMaterial.specular.set(config.material.specular)
        earthMaterial.shininess = config.material.shininess
        atmosphereMaterial.color.set(config.atmosphere.color)
        atmosphereMaterial.opacity = config.atmosphere.opacity
        ambientLight.intensity = config.lighting.ambient
        sunLight.intensity = config.lighting.sun
        cityLightsMaterial.map = cityLightsTexture
        cityLightsMaterial.opacity = cityLightsOpacity
        cityLightsMaterial.needsUpdate = true
        cityLightsMesh.visible = cityLightsOpacity > 0 && Boolean(cityLightsTexture)
        if (stars?.material) {
          stars.material.opacity = config.lighting.stars
          stars.material.needsUpdate = true
        }

        currentTheme = resolvedTheme
        pendingTheme = resolvedTheme
        earthMaterial.needsUpdate = true
        atmosphereMaterial.needsUpdate = true
        return true
      }

      loadTextureWithFallback(
        '/assets/earth_day_8k.jpg',
        '/assets/bluemarble.jpg',
        (texture, usedPath) => {
          dayTexture = texture
          console.log('[earth3d] day texture loaded:', usedPath)

          if (typeof applyTheme === 'function') {
            const applied = applyTheme(pendingTheme || currentTheme || 'night', { force: true })
            if (applied) {
              isReady = true
              renderer.render(scene, camera)
              renderer.domElement.style.opacity = '1'
            }
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
            const applied = applyTheme(pendingTheme || currentTheme || 'night', { force: true })
            if (applied) {
              isReady = true
              renderer.render(scene, camera)
              renderer.domElement.style.opacity = '1'
            }
          } else {
            earthMaterial.emissiveMap = texture
            earthMaterial.needsUpdate = true
          }
        }
      )

      loader.load(
        '/assets/earth_city_lights_alpha_preview_v3.png',
        (texture) => {
          cityLightsTexture = configureEarthTexture(texture)
          console.log('[earth3d] city lights texture loaded:', '/assets/earth_city_lights_alpha_preview_v3.png')
          cityLightsMaterial.map = cityLightsTexture
          cityLightsMaterial.needsUpdate = true

          if (typeof applyTheme === 'function') {
            const applied = applyTheme(pendingTheme || currentTheme || 'night', { force: true })
            if (applied) {
              isReady = true
              renderer.render(scene, camera)
              renderer.domElement.style.opacity = '1'
            }
          }
        },
        undefined,
        () => {
          console.warn('[earth3d] city lights texture unavailable:', '/assets/earth_city_lights_alpha_preview_v3.png')
          cityLightsTexture = null
          cityLightsMaterial.map = null
          cityLightsMaterial.needsUpdate = true
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
          if (permanentlyUnavailable) return
          pendingTheme = themeKey
          if (areRequiredTexturesReady(themeKey)) {
            const applied = applyTheme(themeKey, { force: true })
            if (applied) {
              isReady = true
              renderer.render(scene, camera)
              renderer.domElement.style.opacity = '1'
            }
          }
          updateSunPosition(getThemeHour(themeKey))
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
