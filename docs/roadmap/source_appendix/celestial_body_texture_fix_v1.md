# 天体贴图渲染修正方案 v1 — 从"光斑"到"看得清的球体"

> 状态：**方案文档，尚未实现**。`pwa/real-celestial.js` / `pwa/index.html` 已还原到 commit `b186894`（本方案提出前的状态），本文件描述接下来要做什么，不是已完成的记录。
> 背景 issue：[#53](https://github.com/Heyyeqi/RodiO/issues/53) / [#54](https://github.com/Heyyeqi/RodiO/issues/54)（已 Done，本方案是收尾质量修正，不是新范围）。

---

## 1. 问题

用户反馈（2026-07-21，附截图）：太阳、8颗行星、5颗卫星在 `?earthCandidate=realCelestial` 各专属远景构图（`sunView`/`venusView`/…/`plutoView`/`deepSpace`）下都是模糊的光斑，"看不清"、"太敷衍了"。用户给了两张参考图（真实太阳系海报风格插画），每颗行星都是**清晰、带真实表面细节的圆球**，太阳是**明亮发光的暖白球体**。

对照唯一渲染正确的参照物——**地球**（`SphereGeometry` + Mapbox/Blue Marble 贴图）和**月亮**（`SphereGeometry` + `moon_lroc_color_2k.jpg` 真实贴图 + terminator shader）——两者都清晰可辨；而太阳/8行星/5卫星当前是 `THREE.Sprite` + 程序生成的径向渐变（`makeSunGlowTexture`/`makePlanetGlowTexture`，纯代码画的模糊光斑，不含任何真实图案），这是"看不清"的根本原因：不是没做好，是从设计上就没有真实纹理。

## 2. 已验证的关键事实（不要重新踩坑）

### 2.1 真实贴图资源已经下载好，只是没接入渲染

`docs/roadmap/source_appendix/celestial_texture_resources.md` 记录了 Step 0（2026-07-20）已经下载并实测验证的全部真实 NASA/JPL 探测器影像，文件已经在磁盘上可直接用：

| 天体 | 文件路径（相对 `pwa/`） | 尺寸 |
|---|---|---|
| 太阳 | `assets/textures/sun/sun_sdo_hmi_luminance.jpg` | 2048×2048 |
| 水星 Mercury | `assets/textures/planets/mercury_messenger_truecolor.jpg` | 1040×1040 |
| 金星 Venus | `assets/textures/planets/venus_mariner10_truecolor.jpg` | 1000×1000 |
| 火星 Mars | `assets/textures/planets/mars_truecolor.jpg` | 2560×1920 |
| 木星 Jupiter | `assets/textures/planets/jupiter_pia01369.jpg` | 916×901 |
| 土星 Saturn | `assets/textures/planets/saturn_truecolor.jpg` | 1001×1628 |
| 天王星 Uranus | `assets/textures/planets/uranus_pia18182.jpg` | 1720×1720 |
| 海王星 Neptune | `assets/textures/planets/neptune_pia01492.jpg` | 2188×2185 |
| 冥王星 Pluto | `assets/textures/planets/pluto_pia19708.jpg` | 1024×1020 |
| 木卫一 Io | `assets/textures/planets/io_truecolor.jpg` | 2572×1286 |
| 木卫二 Europa | `assets/textures/planets/europa_pia19048.jpg` | 2300×1700 |
| 木卫三 Ganymede | `assets/textures/planets/ganymede_pia00716.jpg` | 800×800 |
| 木卫四 Callisto | `assets/textures/planets/callisto_pia03456.jpg` | 740×753 |
| 土卫六 Titan | `assets/textures/planets/titan_pia06230.jpg` | 758×766 |

全部通过 `curl http://localhost:8080/assets/textures/...` 确认可正常访问（server.js 静态服务，跟月球贴图同一套路径规则）。

### 2.2 ⚠️ 这些贴图不能直接按球体 UV 贴（已实测踩坑确认）

上表所有文件都是探测器拍的**全圆盘照片**（一张圆形星球快照，四周是黑色背景，尺寸近似正方形/1:1 或接近），**不是**月球贴图 `moon_lroc_color_2k.jpg`（2048×1024，严格 2:1）那种**等距柱状全球展开图**。

`THREE.SphereGeometry` 默认 UV 展开是按 2:1 等距柱状设计的（经度 0-360°、纬度 -90~90°）。如果把一张"圆盘照片"直接当贴图 `map` 贴到 `SphereGeometry` 上，图像内容和黑色背景会一起被拉伸缠绕到球面各个位置——**实测复现的效果是"球体大半发黑，只有一小块亮斑"**，这正是用户反馈"看不清"截图里出现的现象。这条路已经试过且确认走不通，不要重复实现。

**结论：太阳/8行星/5卫星不能用 `SphereGeometry` + 这批贴图；月亮 `SphereGeometry` + `moon_lroc_color_2k.jpg` 保持不变（贴图本身就是对的，代码也无需改动）。**

### 2.3 正确路径：Sprite（公告板）+ 真实贴图 + 叠加混合

`THREE.Sprite` 恒朝向相机，直接把整张贴图画成一个始终正对镜头的面片，不做任何球面 UV 映射/畸变——对"圆盘照片"这种素材是完全合适的展示方式（用户是"先不考虑互动，先把清晰的球体做出来"，不需要真的能绕着转到背面）。

黑色背景的处理：贴图不需要额外做透明通道/抠图。只要材质用 `blending: THREE.AdditiveBlending`，黑色像素（RGB≈0,0,0）在叠加模式下贡献为 0，自然融进背景的深空黑色里，不会出现"方块边框"。这跟现有 `sunHalo`（太阳光晕）、`makePlanetGlowTexture` 生成的旧光斑用的是同一种混合模式，只是这次贴图换成真实照片而不是程序生成的渐变。

---

## 3. 实施方案

### 3.1 范围

只改 `pwa/real-celestial.js` 一个文件（+ 如遇浏览器缓存问题，见 §5）。**不改**：
- `pwa/earth3d.js` 的相机构图 / `FAR_COMPOSITIONS` / 可见性阈值——全部保持 [#53](https://github.com/Heyyeqi/RodiO/issues/53)/[#54](https://github.com/Heyyeqi/RodiO/issues/54) 已验证的现状不动。
- 位置计算（开普勒轨道、`compressToSceneDist`、`planetGeoDir` 等）——不动。
- 月亮渲染（`moonGeo`/`moonMat`/`MOON_VERT`/`MOON_FRAG`）——不动，它本来就是对的。

纯粹是"太阳 + 8行星 + 5卫星怎么画"这一件事的修正。

### 3.2 新增一个 Sprite 工厂函数（替代原来的 `makeSunGlowTexture`/`makePlanetGlowTexture` 光斑生成逻辑，用于太阳核心+行星+卫星）

```js
// 通用天体贴图 Sprite 工厂：太阳/8行星/5卫星的真实贴图都是探测器拍的"全圆盘照片"（近似
// 正方形），不是月球贴图那种等距柱状全球展开图，不能贴 SphereGeometry（会拉伸畸变+黑背景
// 缠绕到球面各处）。改用 Sprite（恒朝向相机）直接显示原图，AdditiveBlending 让黑色背景
// 自然消失于深空背景，圆盘内容不经任何拉伸/球面畸变。
function createBodyTexSprite(scene, colorTint) {
  const mat = new THREE.SpriteMaterial({
    map: null, color: colorTint || 0xffffff, transparent: true,
    blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false,
  })
  const sprite = new THREE.Sprite(mat)
  sprite.frustumCulled = false
  sprite.visible = false
  scene.add(sprite)
  return sprite
}
function loadSpriteTexture(sprite, path) {
  new THREE.TextureLoader().load(path, function (tex) {
    if (THREE.sRGBEncoding !== undefined) tex.encoding = THREE.sRGBEncoding
    sprite.material.map = tex
    sprite.material.needsUpdate = true
  }, undefined, function (e) { console.error('[realCelestial] 贴图加载失败:', path, e) })
}
```

### 3.3 太阳：光晕（保留不变）+ 真实贴图核心盘（新增，叠在光晕上层）

现有的 `sun`（`THREE.Sprite` + `makeSunGlowTexture()` 程序生成径向渐变）改名为 `sunHalo`，逻辑完全不动，只把 `renderOrder` 设低一点（如 18，先画）。

新增一个太阳核心盘 `sun`（沿用外部代码里 `sun.position`/`sun.visible`/`sun.scale` 的既有调用点，变量名 `sun` 继续代表"太阳的主体"）：

```js
const sun = createBodyTexSprite(scene, 0xfff0cc)  // 暖白色调，配合 SDO 灰阶亮度图
sun.renderOrder = 20  // 画在 sunHalo(18) 之上
loadSpriteTexture(sun, '/assets/textures/sun/sun_sdo_hmi_luminance.jpg')
```

`sun_sdo_hmi_luminance.jpg` 是去色的亮度图（米粒组织+黑子细节，实测中性灰 RGB≈155），`SpriteMaterial.color` 的暖白色调（`0xfff0cc`）会跟贴图相乘，得到暖白发光的日面效果（资源文档 `celestial_texture_resources.md` §8.1 明确写了"太阳是自发光体...由 shader 自行着色（白/黄）"）。

`tick()` 里太阳的缩放逻辑：现有代码是 `sun.scale.set(d, d, 1)`（`d` = 直径，Sprite 用直径缩放是对的，不用改成半径）。只需要给 `sunHalo` 一个比 `sun` 稍大的缩放（比如 `d * 1.7`），让光晕在核心盘边缘柔和溢出，两者都要跟着已有的 `pulse` 呼吸节奏缩放。伪代码：

```js
if (showSun) {
  const camToSun = camera.position.distanceTo(sunPos)
  const d = 2 * camToSun * Math.tan((SUN_ANG_DIAM * DEG) / 2)
  sun.scale.set(d * pulse, d * pulse, 1)
  sunHalo.scale.set(d * 1.7 * pulse, d * 1.7 * pulse, 1)
  sunHalo.position.copy(sunPos)  // 别忘了光晕也要跟着太阳位置走
}
```

### 3.4 8颗行星：从光斑贴图换成真实贴图

`PLANET_DEFS` 每一项加一个 `texture` 字段（真实贴图路径，§2.1 表）；`ang`（渲染角直径）建议从"点光源够用"的 0.6–1.3° 上调，理由：这批数值是给"模糊光斑"标定的，现在要显示真实纹理细节，太小会看不清图案。建议新值（保留气态巨行星 > 类地行星的尺寸层级，仍不抢太阳/月亮的主角位）：

| 行星 | 原 ang | 建议新 ang | 贴图 |
|---|---|---|---|
| Mercury | 0.9 | 1.2 | `mercury_messenger_truecolor.jpg` |
| Venus | 1.3 | 1.8 | `venus_mariner10_truecolor.jpg` |
| Mars | 1.1 | 1.5 | `mars_truecolor.jpg` |
| Jupiter | 1.25 | 2.6 | `jupiter_pia01369.jpg` |
| Saturn | 1.2 | 2.4 | `saturn_truecolor.jpg` |
| Uranus | 1.10 | 1.9 | `uranus_pia18182.jpg` |
| Neptune | 1.05 | 1.8 | `neptune_pia01492.jpg` |
| Pluto | 0.60 | 1.0 | `pluto_pia19708.jpg` |

创建循环里把原来的：
```js
const mat = new T.SpriteMaterial({ map: makePlanetGlowTexture(def.rgb, texBright), ... })
```
换成：
```js
const sprite = createBodyTexSprite(scene, 0xffffff)  // 真彩图不需要额外调色
loadSpriteTexture(sprite, def.texture)
```
其余（`planets[name] = { sprite, dist, ang, bright, rgb, ndc, visible }` 结构、`亮度分级地板 Math.max(bright,0.22)` 那段逻辑）都不需要动——那段是给旧光斑的透明度分级用的，如果新贴图整体偏暗可以保留 sprite 的 `color` 用 bright 值做个整体提亮（可选，先看效果再决定要不要加）。

`tick()` 里原来的：
```js
const d = 2 * camToP * Math.tan((P.ang * DEG) / 2)
P.sprite.scale.set(d, d, 1)
```
**这段逻辑完全不用改**——Sprite 本来就是直径缩放，跟原来的旧光斑用法一致，只是贴图换了。

### 3.5 5颗卫星：同样的模式

`SATELLITE_DEFS` 每一项加 `texture` 字段（§2.1 表最后 5 行），`ang` 从 0.26–0.36 上调到大约 0.48–0.65（同样是"给光斑标定的尺寸太小，显示真实图案需要更大"的理由，比行星小一档，保持"看得清但明显小于母星"）。创建/更新逻辑跟 §3.4 同理，替换贴图来源即可，位置/公转计算不动。

---

## 4. 明确排除的范围（不要顺手做）

- **不做行星环**（木星/土星/天王星/海王星环的贴图资源 `celestial_texture_resources.md` §8.2-8.4 里也下载好了，但这是"后期表达/排布"阶段的加分项，这次只解决"球体清不清楚"，不在本次范围）。
- **不改动月亮**的任何渲染逻辑，它本来就是对的。
- **不做真实太阳/行星自转**（这些贴图是静态快照，不需要转起来，跟"先不考虑互动"的要求一致）。
- **不需要给行星做 terminator（明暗分界）光照**——之前有个中间方案尝试给行星复用月球的 terminator shader，结果因为相机站位是"悬浮在地球外侧固定方向拍摄"而不是真实地球视角，会让本该几乎全亮的外行星（火星以远，太阳-地球-行星夹角天生很小）显示成诡异的黑色残月状，是好心办坏事，不要重新加。Sprite 直接显示原图即可，不需要任何光照计算。

---

## 5. 已知坑：浏览器脚本缓存

`pwa/index.html` 里引用这个文件是 `<script src="/real-celestial.js?v=real-celestial-v1"></script>`，服务端对静态资源设了 `Cache-Control: public, max-age=604800`（7天）。改完 `real-celestial.js` 后，**必须把这个查询字符串的版本号往上加一位**（比如改成 `?v=real-celestial-v2`），否则浏览器会直接用磁盘缓存里的旧版本，刷新/重启 server 都看不到新代码生效（这是本轮调试实际踩过的坑，数值明明改对了但 `getState()` 读出来还是旧值，查了很久才发现是缓存）。

---

## 6. 验证清单

1. 本机起 `node server.js`（不是 stub），打开 `http://localhost:8080/?earthCandidate=realCelestial`。
2. 确认改完后确实生效：`fetch('/real-celestial.js', {cache:'no-store'}).then(r=>r.text())` 里能搜到新加的 `texture:` 字段；页面里 `window.realCelestial.getState().planets` 里每颗行星的 `ang` 是新表格里的值（不是旧的 0.9/1.3/…）。
3. Theme Tuner → Camera Grammar V1 (debug)，依次点 `sunView`/`venusView`/`mercuryView`/`marsView`/`jupiterView`/`saturnView`/`deepSpace`/`uranusView`/`neptuneView`/`plutoView`，每个视角应该能看到清晰的、带真实表面图案的圆盘（木星应该有条纹、土星应该是暖色调、水星应该是灰褐色布满环形山质感），不再是模糊光斑，也不应该出现"大半发黑的球"。
4. 控制台确认无 `[realCelestial] 贴图加载失败` 报错。
5. 默认路径（不带 `?earthCandidate=`）确认零影响，`window.realCelestial` 应为 `undefined`。
6. 截图存证，跟用户给的参考图（本文档背景来源的两张参考截图）做主观对比，判断"清晰度"这个主观要求是否达标——这是本次任务最终验收标准，不是数值断言能完全代替的。
