(function () {
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

  function shortestLonDelta(a, b) {
    let delta = normalizeLon(a) - normalizeLon(b)
    while (delta < -180) delta += 360
    while (delta > 180) delta -= 360
    return delta
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
      mountEl.appendChild(renderer.domElement)

      function markUnavailable() {
        isReady = false
        permanentlyUnavailable = true
        if (renderer) renderer.setAnimationLoop(null)
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
      dayTexture = loader.load('/assets/bluemarble.jpg')
      nightTexture = loader.load('/assets/blackmarble.jpg')
      ;[dayTexture, nightTexture].forEach((texture) => {
        texture.colorSpace = THREE.SRGBColorSpace
        texture.anisotropy = 8
      })

      earthMaterial = new THREE.MeshPhongMaterial({
        color: 0x1a3a5c,
        shininess: 4,
        specular: new THREE.Color(0x11161f),
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
      earthGroup.rotation.z = THREE.MathUtils.degToRad(23.4)
      earth.add(atmosphere)
      earthGroup.add(earth)
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

      const sunLight = new THREE.DirectionalLight(0xfff5e0, 1.8)
      scene.add(sunLight)

      function getTargetOrientation() {
        const vs = window.__rodioVisualState || {}
        const lon = normalizeLon(Number.isFinite(vs.lon) ? vs.lon : 121.4737)
        const lat = clamp(
          Number.isFinite(vs.lat) ? vs.lat : 31.2304,
          -80,
          80
        )
        const baseRotY = THREE.MathUtils.degToRad(-227)
      const baseRotX = THREE.MathUtils.degToRad(-20)
        const deltaLon = shortestLonDelta(lon, 121.4737)
        const deltaLat = clamp(lat - 31.2304, -25, 25)
        return {
          x: baseRotX + THREE.MathUtils.degToRad(-deltaLat * 0.18),
          y: baseRotY + THREE.MathUtils.degToRad(-deltaLon * 0.32),
        }
      }

      let currentTheme = null
      function applyTheme(themeKey) {
        if (currentTheme === themeKey) return
        currentTheme = themeKey

        switch (themeKey) {
          case 'morning':
          case 'noon':
            earthMaterial.map = dayTexture
            earthMaterial.color.set(0xffffff)
            earthMaterial.emissive.set(0x000000)
            earthMaterial.emissiveMap = null
            earthMaterial.emissiveIntensity = 0
            atmosphereMaterial.color.set('#88ccff')
            atmosphereMaterial.opacity = 0.15
            ambientLight.intensity = themeKey === 'noon' ? 0.05 : 0.06
            break
          case 'sunrise':
            earthMaterial.map = dayTexture
            earthMaterial.color.set(0xffffff)
            earthMaterial.emissive.set(0x000000)
            earthMaterial.emissiveMap = null
            earthMaterial.emissiveIntensity = 0
            atmosphereMaterial.color.set('#ff8844')
            atmosphereMaterial.opacity = 0.22
            ambientLight.intensity = 0.08
            break
          case 'sunset':
            earthMaterial.map = dayTexture
            earthMaterial.color.set(0xffffff)
            earthMaterial.emissive.set(0x000000)
            earthMaterial.emissiveMap = null
            earthMaterial.emissiveIntensity = 0
            atmosphereMaterial.color.set('#ff5522')
            atmosphereMaterial.opacity = 0.20
            ambientLight.intensity = 0.07
            break
          case 'night':
          default:
            earthMaterial.map = null
            earthMaterial.color.set(0x000000)
            earthMaterial.emissive.set(0xffffff)
            earthMaterial.emissiveMap = nightTexture
            earthMaterial.emissiveIntensity = 0.85
            atmosphereMaterial.color.set('#060d1f')
            atmosphereMaterial.opacity = 0.18
            ambientLight.intensity = 0.015
            break
        }
        earthMaterial.needsUpdate = true
        atmosphereMaterial.needsUpdate = true
      }

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

      function resize() {
        const width = appEl.clientWidth
        const height = appEl.clientHeight
        if (!width || !height) return
        renderer.setSize(width, height, false)
        camera.aspect = width / height
        camera.updateProjectionMatrix()
      }

      observer = new ResizeObserver(() => resize())
      observer.observe(appEl)
      resize()
      const initialOrientation = getTargetOrientation()
      earth.rotation.x = initialOrientation.x
      earth.rotation.y = initialOrientation.y
      atmosphere.rotation.x = initialOrientation.x
      atmosphere.rotation.y = initialOrientation.y
      updateSunPosition(new Date().getHours())
      applyTheme('night')

      renderer.setAnimationLoop(() => {
        if (!isReady || permanentlyUnavailable) return
        const target = getTargetOrientation()
        earth.rotation.x = damp(earth.rotation.x, target.x, 0.02)
        earth.rotation.y = damp(earth.rotation.y, target.y, 0.02)
        atmosphere.rotation.x = earth.rotation.x
        atmosphere.rotation.y = earth.rotation.y
        renderer.render(scene, camera)
      })

      isReady = true

      window.earth3d = {
        get isReady() {
          return isReady
        },
        isAvailable() {
          return isReady && !permanentlyUnavailable
        },
        setTimeOfDay(themeKey) {
          if (!isReady || permanentlyUnavailable) return
          applyTheme(themeKey)
          updateSunPosition(new Date().getHours())
        },
        dispose() {
          isReady = false
          renderer.setAnimationLoop(null)
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
