(function () {
  // ── Horizon Mode 隔离试验场景骨架 ──
  // 仅在 ?earthCandidate=horizonLab 时激活；其余情况下本文件是纯 no-op。
  // Category B 纪律：独立 THREE.Scene / 独立相机 / 独立渲染循环，完全不复用主 earth3d.js
  // 的 mesh / shader / EARTH_MODES / 相机语法系统，不 import 主脚本的任何变量。
  // 场景+着色器逻辑照搬自已验证过的原型 /tmp/rodio_assets/cloud_proto_dome.html
  // （视差实测 22.3px / 142.5px，地平线几何 46.4%，见
  //  docs/roadmap/source_appendix/horizon_cloud_layer_v1.md §6）。
  if (new URLSearchParams(window.location.search).get('earthCandidate') !== 'horizonLab') return

  function boot() {
    const appEl = document.getElementById('app')
    const mountEl = document.getElementById('earth3d-layer')
    if (!appEl || !mountEl || !window.THREE) {
      console.warn('[horizon-lab] missing app/mount element or THREE, aborting')
      return
    }

    console.log('[horizon-lab] activating isolated Horizon lab scene (?earthCandidate=horizonLab)')

    const PRESETS = {
      horizon: {
        sky: { top: 0x2a3b52, bottom: 0xa9b8c6, haze: 0xb9c6d2 },
        clouds: {
          density: 0.46, softness: 0.45, scroll: 0.006, scale: 2.6,
          layerOpacity: 0.55, bandCenter: 0.10, bandWidth: 0.55, bandFeather: 0.30,
          color: 0xeef2f6,
        },
        sea: 0x006792,  // S2 马尔代夫珊瑚礁 baseColorDeep（water_params_reference.js 实算，非拍脑袋）
      },
      mountain: {
        sky: { top: 0x3a4654, bottom: 0x9aa6b0, haze: 0xb6c0c8 },
        clouds: {
          density: 0.62, softness: 0.34, scroll: 0.011, scale: 3.3,
          layerOpacity: 0.82, bandCenter: -0.06, bandWidth: 0.18, bandFeather: 0.14,
          color: 0xf2f4f6,
        },
        sea: 0x007167,  // S3 北大西洋温带 baseColorDeep（water_params_reference.js 实算，非拍脑袋）
      },
    }

    const SNOISE3 = `
    vec3 mod289(vec3 x){return x-floor(x*(1.0/289.0))*289.0;}
    vec4 mod289(vec4 x){return x-floor(x*(1.0/289.0))*289.0;}
    vec4 permute(vec4 x){return mod289(((x*34.0)+1.0)*x);}
    vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-0.85373472095314*r;}
    float snoise(vec3 v){
      const vec2 C=vec2(1.0/6.0,1.0/3.0); const vec4 D=vec4(0.0,0.5,1.0,2.0);
      vec3 i=floor(v+dot(v,C.yyy)); vec3 x0=v-i+dot(i,C.xxx);
      vec3 g=step(x0.yzx,x0.xyz); vec3 l=1.0-g; vec3 i1=min(g.xyz,l.zxy); vec3 i2=max(g.xyz,l.zxy);
      vec3 x1=x0-i1+C.xxx; vec3 x2=x0-i2+C.yyy; vec3 x3=x0-D.yyy;
      i=mod289(i);
      vec4 p=permute(permute(permute(i.z+vec4(0.0,i1.z,i2.z,1.0))+i.y+vec4(0.0,i1.y,i2.y,1.0))+i.x+vec4(0.0,i1.x,i2.x,1.0));
      float n_=0.142857142857; vec3 ns=n_*D.wyz-D.xzx;
      vec4 j=p-49.0*floor(p*ns.z*ns.z);
      vec4 x_=floor(j*ns.z); vec4 y_=floor(j-7.0*x_);
      vec4 x=x_*ns.x+ns.yyyy; vec4 y=y_*ns.x+ns.yyyy; vec4 h=1.0-abs(x)-abs(y);
      vec4 b0=vec4(x.xy,y.xy); vec4 b1=vec4(x.zw,y.zw);
      vec4 s0=floor(b0)*2.0+1.0; vec4 s1=floor(b1)*2.0+1.0; vec4 sh=-step(h,vec4(0.0));
      vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy; vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
      vec3 p0=vec3(a0.xy,h.x); vec3 p1=vec3(a0.zw,h.y); vec3 p2=vec3(a1.xy,h.z); vec3 p3=vec3(a1.zw,h.w);
      vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));
      p0*=norm.x; p1*=norm.y; p2*=norm.z; p3*=norm.w;
      vec4 m=max(0.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.0); m=m*m;
      return 42.0*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));
    }
    float fbm3(vec3 p){
      float a=0.5,f=1.0,s=0.0;
      for(int i=0;i<5;i++){ s+=a*snoise(p*f); f*=2.0; a*=0.5; }
      return s;
    }`

    // ── 独立 renderer / scene / camera ──
    const canvas = document.createElement('canvas')
    canvas.id = 'horizon-lab-canvas'
    canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:auto;'
    mountEl.appendChild(canvas)

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 8000)
    camera.position.set(0, 2.2, 0)          // eyeHeight 2.2（Vision doc）
    camera.rotation.order = 'YXZ'
    let yaw = 0
    let pitch = -1.5 * Math.PI / 180        // 基准 pitch -1.5°，Vision 允许范围 -3°..+5°
    camera.rotation.x = pitch

    // Sky dome（最外层）
    const skyMat = new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false,
      uniforms: { uTop: { value: new THREE.Color() }, uBottom: { value: new THREE.Color() }, uHaze: { value: new THREE.Color() } },
      vertexShader: `varying vec3 vDir; void main(){ vDir=position; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
      fragmentShader: `varying vec3 vDir; uniform vec3 uTop,uBottom,uHaze;
        void main(){ vec3 d=normalize(vDir); float t=clamp(d.y*0.5+0.5,0.0,1.0);
          vec3 col=mix(uBottom,uTop,pow(t,0.8));
          float h=1.0-smoothstep(0.0,0.12,abs(d.y)); col+=uHaze*h*0.5;
          gl_FragColor=vec4(col,1.0);}`,
    })
    const skyDome = new THREE.Mesh(new THREE.SphereGeometry(2000, 64, 48), skyMat)
    scene.add(skyDome)

    // 3 层不同半径的云壳 → 真实 3D 视差（非屏幕滚动伪视差）
    const cloudMats = []
    const SHELL_R = [1975, 1985, 1995]
    SHELL_R.forEach((R, idx) => {
      const mat = new THREE.ShaderMaterial({
        side: THREE.BackSide, transparent: true, depthWrite: false,
        blending: THREE.NormalBlending,
        uniforms: {
          uDensity: { value: 0.46 }, uSoftness: { value: 0.45 }, uScroll: { value: 0.006 },
          uScale: { value: 2.6 }, uLayerOpacity: { value: 0.55 },
          uBandCenter: { value: 0.10 }, uBandWidth: { value: 0.55 }, uBandFeather: { value: 0.30 },
          uTime: { value: 0 }, uShell: { value: idx },
          uColor: { value: new THREE.Color(0xeef2f6) },
        },
        vertexShader: `varying vec3 vDir; void main(){ vDir=position; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
        fragmentShader: SNOISE3 + `
          varying vec3 vDir;
          uniform float uDensity,uSoftness,uScroll,uScale,uLayerOpacity,uBandCenter,uBandWidth,uBandFeather,uTime,uShell;
          uniform vec3 uColor;
          void main(){
            vec3 d=normalize(vDir);
            float elev=d.y;
            vec3 p=d*uScale + vec3(uTime*uScroll, 0.0, uTime*uScroll*0.6) + float(uShell)*13.7;
            float n=fbm3(p);
            float a=smoothstep(1.0-uDensity, 1.0-uDensity+uSoftness, n*0.5+0.5);
            float band=1.0-smoothstep(0.0,uBandWidth,abs(elev-uBandCenter));
            band=mix(1.0,band,uBandFeather);
            float alpha=a*uLayerOpacity*band;
            if(alpha<0.003) discard;
            gl_FragColor=vec4(uColor,alpha);
          }`,
      })
      cloudMats.push(mat)
      scene.add(new THREE.Mesh(new THREE.SphereGeometry(R, 64, 48), mat))
    })

    // ── 真实反射海面（#44）：THREE.Water，复用 Phase 2 天空穹顶+云壳做倒影 ──
    // 这是判断"真反射 vs 假水"的硬指标：水面上要能看到天空/云的倒影。
    // 水色锚点用 water_params_reference.js 算出的真实海洋站位色值（非拍脑袋）。
    // 固定低角度太阳（贴近地平线）留一处高光即可，不接入天文系统（后续场景打磨阶段）。
    let water
    const waterGeom = new THREE.PlaneGeometry(9000, 9000)
    if (typeof THREE.Water === 'function') {
      water = new THREE.Water(waterGeom, {
        textureWidth: 512,
        textureHeight: 512,
        waterNormals: new THREE.TextureLoader().load('/assets/textures/water/waternormals.jpg', (tex) => {
          tex.wrapS = tex.wrapT = THREE.RepeatWrapping
        }),
        sunDirection: new THREE.Vector3(0.35, 0.22, 0.25).normalize(),
        sunColor: 0xffffff,
        waterColor: 0x0e2a33,   // 占位，applyPreset 会立刻用真实色值覆盖
        distortionScale: 3.7,
        fog: false,
      })
      water.rotation.x = -Math.PI / 2
      water.position.y = 0
      scene.add(water)
    } else {
      // 防御性降级：addon 未加载时也不至于整屏空白（Category B 红线保护）
      console.warn('[horizon-lab] THREE.Water unavailable, falling back to flat sea')
      const seaMat = new THREE.MeshBasicMaterial({ color: 0x0e2a33 })
      water = new THREE.Mesh(waterGeom, seaMat)
      water.rotation.x = -Math.PI / 2
      water.position.y = 0
      scene.add(water)
    }

    // 同时兼容 THREE.Water（uniform）与降级 MeshBasicMaterial（.color）
    function applyWaterColor(hex) {
      const m = water.material
      if (m && m.uniforms && m.uniforms['waterColor']) m.uniforms['waterColor'].value.setHex(hex)
      else if (m && m.color) m.color.setHex(hex)
    }

    function applyPreset(name) {
      const P = PRESETS[name]
      if (!P) return
      skyMat.uniforms.uTop.value.setHex(P.sky.top)
      skyMat.uniforms.uBottom.value.setHex(P.sky.bottom)
      skyMat.uniforms.uHaze.value.setHex(P.sky.haze)
      applyWaterColor(P.sea)
      const c = P.clouds
      cloudMats.forEach((m, i) => {
        m.uniforms.uDensity.value = c.density
        m.uniforms.uSoftness.value = c.softness
        m.uniforms.uScroll.value = c.scroll * (1.0 + i * 0.25)
        m.uniforms.uScale.value = c.scale * (1.0 + i * 0.18)
        m.uniforms.uLayerOpacity.value = c.layerOpacity
        m.uniforms.uBandCenter.value = c.bandCenter
        m.uniforms.uBandWidth.value = c.bandWidth
        m.uniforms.uBandFeather.value = c.bandFeather
        m.uniforms.uColor.value.setHex(c.color)
      })
      currentPreset = name
    }
    let currentPreset = 'horizon'
    applyPreset('horizon')

    // ── 尺寸：与主 earth3d.js 相同的 appEl.clientWidth/Height + ResizeObserver 约定 ──
    function resize() {
      const w = appEl.clientWidth
      const h = appEl.clientHeight
      if (!w || !h) return
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h, false)
    }
    resize()
    const observer = new ResizeObserver(resize)
    observer.observe(appEl)

    // ── 独立的拖拽看方向（不接入 GestureRouter，仅作用于本 canvas）──
    let dragging = false
    let lastX = 0, lastY = 0
    const PITCH_MIN = -3 * Math.PI / 180
    const PITCH_MAX = 5 * Math.PI / 180
    canvas.addEventListener('pointerdown', (e) => { dragging = true; lastX = e.clientX; lastY = e.clientY; canvas.setPointerCapture(e.pointerId) })
    canvas.addEventListener('pointermove', (e) => {
      if (!dragging) return
      const dx = e.clientX - lastX, dy = e.clientY - lastY
      lastX = e.clientX; lastY = e.clientY
      yaw -= dx * 0.003
      pitch = Math.max(PITCH_MIN, Math.min(PITCH_MAX, pitch - dy * 0.001))
      camera.rotation.y = yaw
      camera.rotation.x = pitch
    })
    canvas.addEventListener('pointerup', (e) => { dragging = false; canvas.releasePointerCapture(e.pointerId) })
    canvas.addEventListener('pointercancel', () => { dragging = false })

    // ── Debug info / preset 面板（仅 horizonLab 激活时挂载，不影响正常用户 DOM） ──
    const panel = document.createElement('div')
    panel.style.cssText = 'position:absolute;top:8px;left:8px;color:#cdd6e0;font-size:11px;line-height:1.5;' +
      'background:rgba(10,14,20,.72);padding:8px 11px;border-radius:8px;max-width:340px;z-index:10;pointer-events:auto;' +
      'font-family:-apple-system,system-ui,"PingFang SC",sans-serif;'
    panel.innerHTML = '<b style="color:#7fd1ff">Horizon Lab（隔离试验场景，?earthCandidate=horizonLab）</b><br/>' +
      '独立 Scene/Camera/渲染循环，不复用主 earth3d.js 的 mesh/shader<br/>' +
      '拖拽画面看方向（yaw 自由，pitch 限制 -3°..+5°）<br/>' +
      '预设：<select id="horizon-lab-preset"><option value="horizon">海平线（克制稀薄）</option><option value="mountain">山地（缠绕山腰）</option></select>'
    mountEl.appendChild(panel)
    panel.querySelector('#horizon-lab-preset').addEventListener('change', (e) => applyPreset(e.target.value))

    // ── 渲染循环 ──
    let destroyed = false
    let t0 = performance.now()
    function loop() {
      if (destroyed) return
      const t = (performance.now() - t0) / 1000
      cloudMats.forEach((m) => { m.uniforms.uTime.value = t })
      if (water.material && water.material.uniforms && water.material.uniforms['time']) {
        water.material.uniforms['time'].value += 1 / 60   // 固定步长即可，lab 场景不依赖真实 delta
      }
      renderer.render(scene, camera)
      requestAnimationFrame(loop)
    }
    loop()

    // ── 供自动化验证 / 人工调试使用的调试 API ──
    window.horizonLab = {
      isReady: true,
      setPreset: applyPreset,
      getPreset: () => currentPreset,
      setYaw: (deg) => { yaw = deg * Math.PI / 180; camera.rotation.y = yaw },
      setPitch: (deg) => { pitch = Math.max(PITCH_MIN, Math.min(PITCH_MAX, deg * Math.PI / 180)); camera.rotation.x = pitch },
      getState: () => ({
        preset: currentPreset,
        yawDeg: yaw * 180 / Math.PI,
        pitchDeg: pitch * 180 / Math.PI,
        waterColor: water.material && water.material.uniforms && water.material.uniforms['waterColor']
          ? '#' + water.material.uniforms['waterColor'].value.getHexString()
          : (water.material && water.material.color ? '#' + water.material.color.getHexString() : null),
        waterReflective: typeof THREE.Water === 'function',
      }),
      render: () => renderer.render(scene, camera),
      destroy: () => {
        destroyed = true
        observer.disconnect()
        renderer.dispose()
        canvas.remove()
        panel.remove()
        delete window.horizonLab
      },
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true })
  } else {
    boot()
  }
})()
