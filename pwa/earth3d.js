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
    let skyGeometry = null
    let skyMaterial = null
    let skyMesh = null
    let skyRadius = 300
    let earthGeometry = null
    let atmosphere = null
    let stars = null
    let cloudGeometry = null
    let cloudMaterial = null
    let cloudMesh = null
    let cloudTexture = null
    let cloudTextureLoadState = 'idle'
    let cloudTextureWarned = false
    let cloudTexturePath = null
    let cloudTextureError = null
    let cloudVisibleRequested = true
    let isDestroyed = false
    const cloudRadius = 2.04
    let cloudDriftLastTick = 0
    let visibilityChangeHandler = null
    let earthMaterial = null
    let atmosphereMaterial = null
    let dayTexture = null
    let nightTexture = null
    let oceanSpecularTexture = null
    let oceanSpecularTextureLoadState = 'idle'
    let oceanSpecularTextureWarned = false
    let oceanSpecularTexturePath = null
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
              top: '#04050d',
              horizon: '#5f8fa9',
              bottom: '#3c1e4a',
              opacity: 0.96,
            }
          case 'sunrise':
            return {
              top: '#111830',
              horizon: '#8ad0ff',
              bottom: '#432048',
              opacity: 0.95,
            }
          case 'earlyMorning':
            return {
              top: '#182e5c',
              horizon: '#d0e4f2',
              bottom: '#4a72aa',
              opacity: 0.94,
            }
          case 'morning':
            return {
              top: '#123270',
              horizon: '#c4dcf0',
              bottom: '#3e76b8',
              opacity: 0.94,
            }
          case 'noon':
            return {
              top: '#0c2c68',
              horizon: '#cce2f4',
              bottom: '#3272b0',
              opacity: 0.93,
            }
          case 'afternoon':
            return {
              top: '#12347a',
              horizon: '#d0dcc8',
              bottom: '#0f2e6e',
              opacity: 0.93,
            }
          case 'goldenApproach':
            return {
              top: '#0f2e6e',
              horizon: '#dcc070',
              bottom: '#eee8dc',
              opacity: 0.93,
            }
          case 'sunset':
            return {
              top: '#0c1a38',
              horizon: '#d0b070',
              bottom: '#542238',
              opacity: 0.95,
            }
          case 'evening':
            return {
              top: '#060a18',
              horizon: '#202c50',
              bottom: '#0c142e',
              opacity: 0.97,
            }
          case 'lateEvening':
            return {
              top: '#04070f',
              horizon: '#162840',
              bottom: '#1c2a48',
              opacity: 0.98,
            }
          case 'night':
          case 'deepNight':
          default:
            return {
              top: '#020308',
              horizon: '#0b1220',
              bottom: '#060a14',
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

      const CLOUD_OPACITY_BY_THEME = {
        dawn: 0.08,
        sunrise: 0.09,
        earlyMorning: 0.095,
        morning: 0.1,
        noon: 0.15,
        afternoon: 0.13,
        goldenApproach: 0.1,
        sunset: 0.08,
        evening: 0.04,
        lateEvening: 0.025,
        deepNight: 0.018,
        night: 0.025,
      }

      function normalizeCloudThemeKey(themeKey) {
        return themeKey === 'night' ? 'deepNight' : themeKey
      }

      function getCloudOpacity(themeKey) {
        const resolvedTheme = normalizeCloudThemeKey(
          themeKey || currentTheme || pendingTheme || 'deepNight'
        )
        const baseOpacity = CLOUD_OPACITY_BY_THEME[resolvedTheme] ?? CLOUD_OPACITY_BY_THEME.deepNight
        const deviceScale = isLowCloudDevice() ? 0.95 : 1
        return clamp(baseOpacity * deviceScale, 0, 1)
      }

      const CLOUD_DRIFT_BY_THEME = {
        dawn: 0.000012,
        sunrise: 0.000013,
        earlyMorning: 0.000016,
        morning: 0.00002,
        noon: 0.000024,
        afternoon: 0.000021,
        goldenApproach: 0.000014,
        sunset: 0.000008,
        evening: 0.000003,
        lateEvening: 0.0000015,
        deepNight: 0.0000005,
        night: 0.000001,
      }
      const CLOUD_DRIFT_LOW_DEVICE_SCALE = 0.5

      function isLowCloudDevice() {
        const smallViewport = Math.min(window.innerWidth || 0, window.innerHeight || 0) <= 820
        const coarsePointer = Boolean(window.matchMedia && window.matchMedia('(pointer: coarse)').matches)
        const lowDpr = (window.devicePixelRatio || 1) <= 1.25
        return smallViewport || coarsePointer || lowDpr
      }

      function getCloudDriftLowDeviceScale() {
        return isLowCloudDevice() ? CLOUD_DRIFT_LOW_DEVICE_SCALE : 1
      }

      function getCloudDriftSpeed(themeKey) {
        const resolvedTheme = normalizeCloudThemeKey(
          themeKey || currentTheme || pendingTheme || 'deepNight'
        )
        const baseSpeed = CLOUD_DRIFT_BY_THEME[resolvedTheme] ?? CLOUD_DRIFT_BY_THEME.deepNight
        return baseSpeed * getCloudDriftLowDeviceScale()
      }

      function updateCloudDrift(now = performance.now()) {
        if (!cloudMesh || cloudTextureLoadState !== 'ready') {
          cloudDriftLastTick = now
          return
        }

        const speed = getCloudDriftSpeed(currentTheme || pendingTheme || 'deepNight')
        if (!Number.isFinite(speed) || speed <= 0) {
          cloudDriftLastTick = now
          return
        }

        if (!cloudDriftLastTick) {
          cloudDriftLastTick = now
          return
        }

        const deltaSeconds = Math.min((now - cloudDriftLastTick) / 1000, 0.1)
        cloudDriftLastTick = now
        if (deltaSeconds <= 0) return

        cloudMesh.rotation.y += speed * deltaSeconds * 60
      }

      function resetCloudDriftLastTick() {
        cloudDriftLastTick = 0
      }

      function alignCloudDriftLastTick(now = performance.now()) {
        cloudDriftLastTick = now
      }

      function getCloudAlphaTexturePaths() {
        const highResPath = '/assets/earth/clouds/cloud_alpha_4096x2048_refined.png'
        const lowResPath = '/assets/earth/clouds/cloud_alpha_2048x1024_refined.png'
        return isLowCloudDevice()
          ? [lowResPath, highResPath]
          : [highResPath, lowResPath]
      }

      function configureCloudTexture(texture) {
        if ('encoding' in texture && typeof THREE.LinearEncoding !== 'undefined') {
          texture.encoding = THREE.LinearEncoding
        }
        texture.wrapS = THREE.ClampToEdgeWrapping
        texture.wrapT = THREE.ClampToEdgeWrapping
        texture.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy())
        texture.minFilter = THREE.LinearMipmapLinearFilter
        texture.magFilter = THREE.LinearFilter
        texture.generateMipmaps = true
        texture.needsUpdate = true
        return texture
      }

      function refreshCloudAppearance(themeKey = currentTheme || pendingTheme || 'deepNight') {
        if (!cloudMaterial || !cloudMesh) return false
        cloudMaterial.opacity = getCloudOpacity(themeKey)
        cloudMesh.visible = cloudVisibleRequested && cloudTextureLoadState === 'ready'
        return cloudMesh.visible
      }

      function loadCloudAlphaTextureIfExists(path) {
        return fetch(path, { method: 'HEAD' })
          .then((response) => {
            if (!response.ok) return null
            return new Promise((resolve) => {
              loader.load(
                path,
                (texture) => {
                  if (isDestroyed) {
                    texture.dispose()
                    resolve(null)
                    return
                  }
                  resolve(configureCloudTexture(texture))
                },
                undefined,
                () => resolve(null)
              )
            })
          })
          .catch(() => null)
      }

      async function loadCloudAlphaTexture() {
        if (cloudTextureLoadState !== 'idle' || isDestroyed) return cloudTexture
        cloudTextureLoadState = 'loading'
        cloudTextureError = null

        const [preferredPath, fallbackPath] = getCloudAlphaTexturePaths()
        let texture = await loadCloudAlphaTextureIfExists(preferredPath)
        let usedPath = preferredPath
        if (!texture) {
          texture = await loadCloudAlphaTextureIfExists(fallbackPath)
          usedPath = fallbackPath
        }

        if (isDestroyed) {
          if (texture) texture.dispose()
          return null
        }

        if (texture) {
          cloudTexture = texture
          cloudTextureLoadState = 'ready'
          cloudTexturePath = texture.image?.src || usedPath

          if (!cloudGeometry) {
            cloudGeometry = new THREE.SphereGeometry(cloudRadius, 64, 64)
          }

          if (!cloudMaterial) {
            cloudMaterial = new THREE.MeshBasicMaterial({
              color: 0xffffff,
              side: THREE.FrontSide,
              transparent: true,
              opacity: getCloudOpacity(),
              alphaMap: cloudTexture,
              depthWrite: false,
              depthTest: true,
            })
          } else {
            cloudMaterial.alphaMap = cloudTexture
            cloudMaterial.transparent = true
            cloudMaterial.depthWrite = false
            cloudMaterial.depthTest = true
            cloudMaterial.needsUpdate = true
          }

          if (!cloudMesh) {
            cloudMesh = new THREE.Mesh(cloudGeometry, cloudMaterial)
            cloudMesh.renderOrder = 2
            cloudMesh.frustumCulled = false
            cloudMesh.visible = false
            earthGroup.add(cloudMesh)
          }

          refreshCloudAppearance()
          if (!permanentlyUnavailable && isReady) {
            renderer.render(scene, camera)
          }
          return cloudTexture
        }

        cloudTextureLoadState = 'missing'
        cloudTextureError = `cloud alpha map unavailable: ${preferredPath}${fallbackPath ? `, ${fallbackPath}` : ''}`
        if (!cloudTextureWarned) {
          cloudTextureWarned = true
          console.warn('[earth3d] cloud alpha map unavailable; skipping')
        }
        return null
      }

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
            color: '#5f8fa9',
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
            specular: 0x06090f,
            shininess: 1.05,
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
            specular: 0x091018,
            shininess: 1.12,
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
            specular: 0x05080d,
            shininess: 0.96,
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
            specular: 0x070503,
            shininess: 0.68,
          },
          atmosphere: {
            color: '#c0a878',
            opacity: 0.1,
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
            color: '#203750',
            opacity: 0.18,
          },
          lighting: {
            ambient: 0.06,
            sun: 0.04,
            stars: 0.78,
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
            color: '#162840',
            opacity: 0.17,
          },
          lighting: {
            ambient: 0.038,
            sun: 0.015,
            stars: 0.72,
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
            color: '#0d2136',
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
            color: '#15283f',
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

      function shouldUseOceanSpecularMap(themeKey) {
        return ['morning', 'noon', 'afternoon', 'goldenApproach'].includes(themeKey)
      }

      function getSpecularMode(config, themeKey) {
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
        earthMaterial.specular.set(config.material.specular)
        earthMaterial.shininess = config.material.shininess
        earthMaterial.specularMap = shouldUseOceanSpecularMap(resolvedTheme) ? oceanSpecularTexture : null
        atmosphereMaterial.color.set(config.atmosphere.color)
        atmosphereMaterial.opacity = config.atmosphere.opacity
        ambientLight.intensity = config.lighting.ambient
        sunLight.intensity = config.lighting.sun
        if (stars?.material) {
          stars.material.opacity = config.lighting.stars
          stars.material.needsUpdate = true
        }
        updateSkyTheme(resolvedTheme)
        refreshCloudAppearance(resolvedTheme)

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

      loadOceanSpecularTexture()
      loadCloudAlphaTexture()

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
        const cloudDriftSpeed = getCloudDriftSpeed(currentTheme || pendingTheme || 'deepNight')
        const cloudLowDeviceScale = getCloudDriftLowDeviceScale()
        const cloud = {
          driftSpeed: cloudDriftSpeed,
          lowDeviceScale: cloudLowDeviceScale,
          enabled: Boolean(cloudVisibleRequested),
          visible: Boolean(cloudMesh?.visible),
          loaded: cloudTextureLoadState === 'ready',
          texturePath: cloudTexturePath,
          opacity: Number.isFinite(cloudMaterial?.opacity) ? cloudMaterial.opacity : null,
          radius: cloudRadius,
          renderOrder: Number.isFinite(cloudMesh?.renderOrder) ? cloudMesh.renderOrder : null,
          materialType: cloudMaterial?.type ?? null,
          loadError: cloudTextureError,
          driftEnabled: Boolean(cloudMesh && cloudTextureLoadState === 'ready' && cloudDriftSpeed > 0),
          rotationY: Number.isFinite(cloudMesh?.rotation?.y) ? cloudMesh.rotation.y : null,
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
          cloud: {
            ...cloud,
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
        updateCloudDrift()

        renderer.render(scene, camera)
      })

      visibilityChangeHandler = () => {
        if (document.hidden) {
          resetCloudDriftLastTick()
          return
        }
        alignCloudDriftLastTick()
      }
      document.addEventListener('visibilitychange', visibilityChangeHandler)

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
        setSkyVisible(visible) {
          if (!skyMesh || !skyMaterial?.uniforms) return false
          skyMesh.visible = Boolean(visible)
          skyMaterial.uniforms.uEnabled.value = skyMesh.visible ? 1 : 0
          if (isReady && !permanentlyUnavailable) {
            renderer.render(scene, camera)
          }
          return skyMesh.visible
        },
        setCloudVisible(visible) {
          cloudVisibleRequested = Boolean(visible)
          if (cloudMesh) {
            cloudMesh.visible = cloudVisibleRequested && cloudTextureLoadState === 'ready'
          }
          if (cloudMaterial) {
            cloudMaterial.opacity = getCloudOpacity(currentTheme || pendingTheme || 'deepNight')
          }
          if (isReady && !permanentlyUnavailable) {
            renderer.render(scene, camera)
          }
          return Boolean(cloudMesh?.visible)
        },
        getDebugState() {
          return buildDebugState()
        },
        dispose() {
          isReady = false
          isDestroyed = true
          renderer.setAnimationLoop(null)
          if (visibilityChangeHandler) {
            document.removeEventListener('visibilitychange', visibilityChangeHandler)
            visibilityChangeHandler = null
          }
          if (renderer?.domElement) renderer.domElement.style.opacity = '0'
          if (observer) observer.disconnect()
          if (skyGeometry) skyGeometry.dispose()
          if (skyMaterial) skyMaterial.dispose()
          if (cloudMesh?.parent) cloudMesh.parent.remove(cloudMesh)
          if (cloudGeometry) cloudGeometry.dispose()
          if (cloudMaterial) cloudMaterial.dispose()
          if (cloudTexture) cloudTexture.dispose()
          if (earthGeometry) earthGeometry.dispose()
          if (atmosphere?.geometry) atmosphere.geometry.dispose()
          if (stars?.geometry) stars.geometry.dispose()
          skyGeometry = null
          skyMaterial = null
          skyMesh = null
          cloudGeometry = null
          cloudMaterial = null
          cloudMesh = null
          cloudTexture = null
          if (earthMaterial) earthMaterial.dispose()
          if (atmosphereMaterial) atmosphereMaterial.dispose()
          if (stars?.material) stars.material.dispose()
          if (dayTexture) dayTexture.dispose()
          if (nightTexture) nightTexture.dispose()
          if (oceanSpecularTexture) oceanSpecularTexture.dispose()
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
