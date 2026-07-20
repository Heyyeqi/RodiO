# 地球远景 NASA 真彩贴图 — 实现规格（#53/#54 衍生）

> **目标读者**：执行此任务的开发者（Claude Code / 同类 agent）
> **关联任务**：#53/#54 天体系统。本规格是「Step 0 资源」之后的**地球自身远景质感一致性**改造，独立于行星贴图渲染（不改动 real-celestial.js 的行星逻辑）。
> **状态**：方案已与 RW 讨论确认，待执行。

---

## 0. 背景与问题

当前 `pwa/earth3d.js` 里的地球**有贴图**，但其「白天贴图」来源是 `tileManager` 的 Mapbox **`topo_bathy` 瓦片**（`bmng21k/topo_bathy/tiles_rdl_regions/.../tile_noon_air_mapbox_*.jpg`，约 line 3404–3409），再叠加 shader 里的海洋/陆地分级着色（`uOceanLift` / `uOceanTeal` / `uLandStr` 等），呈现**制图 + 水深夸张**风格（"偏地图设计"）。

在深空远景里，地球会与使用 NASA 可见光真彩贴图的行星（#53 已采集 8 行星 + 5 卫星 2K 贴图）同框，此时地球的地图像素与行星的照片质感**明显不搭**。但地球的**光照已经和行星一致**（共用 `sunDirection` 方向光，terminator 天然对齐），因此只需替换**远景下的表面反照率来源**，不必动光照。

**决策（已与 RW 确认）**：
- 机制 **A**：同一个球，远景时通过 shader blend 把近景瓦片图与 NASA 图混合（非硬换 `map`），交叉淡入。
- **保留夜灯**（Black Marble 城市灯 emissiveMap）。
- 远景地球贴图 = **NASA Blue Marble 真彩等距柱状 4K**（PD）；行星维持 2K 不变。
- 切换方式 = **距离阈值 + `uFarMix` 透明度交叉淡入**。
- 阈值绑定 **`MOON_VISIBLE_DIST`(=20)**，过渡**上界**取该值，使「第一颗行星（月亮）出现的那一刻（d=20）地球已**完全** NASA 真彩」，同框零错位（详见 §4 数学：过渡区间 `[12, 20]`，d=20 时 `uFarMix = 1.0` 恰好收口）。

---

## 1. 当前架构关键定位（earth3d.js，已核实行号）

| 关注点 | 位置 | 说明 |
|--------|------|------|
| 地球材质 | line 1734 | `earthMaterial = new THREE.MeshPhongMaterial({ color:0x1a3a5c, shininess:1, specular:0x05070a })` |
| Shader 注入入口 | line 1750 | `earthMaterial.onBeforeCompile = (shader) => { ... }`，注入大量 uniform（`uOceanMask` / `uOceanLift` / `uOceanTeal` / `uLandLift` / `uLandStr` / `uNightExposure` 等） |
| map 采样点 | line 2124 / 2199 / 2226 | fragment 中 `texture2D(map, vUv)`（即 MeshPhong 的白天贴图） |
| map 赋值 | line 6318 | `earthMaterial.map = config.texture.map === 'day' ? dayTexture : null` |
| day 贴图来源 | line 6530 | `dayTexture = tileManager.atlasTexture`（Mapbox topo_bathy 瓦片集） |
| 夜灯 emissiveMap | line 6383 / 6546–6584 | `earthMaterial.emissiveMap = useNightEmissive ? currentNightTex : null`；`nightTexture` = Black Marble |
| 海洋掩膜 | line 1647–1656 | `oceanMaskTexture`，shader 内 `uOceanMask` 用于海陆分级 |
| 贴图过滤 | line 952 / 976 / 1567 | 已用 `LinearMipmapLinearFilter`（mipmap 已开，远景缩放下清晰） |
| 距离钩子 | （memory） | `getCameraDistanceToEarth()` 已暴露，返回相机→地心实际距离 |
| 地球几何 | line 2241 / 2368–2373 | `earth = new THREE.Mesh(earthGeometry, earthMaterial)`，`earthGroup.position=(0,-1.4,0)`，`earthGroup.add(earth)`，半径 R≈2.0 |
| 行星可见阈值 | real-celestial.js | `MOON_VISIBLE_DIST=20` / `SUN_VISIBLE_DIST=50`（相机→地心实际距离） |
| 远景状态变量 | L590–595 | `blueMarbleTexture` / `earthFarMix` / `earthFarMixTarget` / `blueMarbleRequested` / `_debugFarMixOverride` |
| 远景 uniform | L1815–1816 | `shader.uniforms.uMapFar`（初始 `_maskPlaceholder`）/ `uFarMix`（初始 0） |
| fragment 声明 | L1865–1866 | `uniform sampler2D uMapFar;` / `uniform float uFarMix;`（`#include <common>` 注入区） |
| 远景混合块 | L2105–2110 | `#include <map_fragment>` 之后：`diffuseColor.rgb = mix(diffuseColor.rgb, texture2D(uMapFar,vUv).rgb, uFarMix)` |
| 惰性加载 | L2268–2293 | `ensureBlueMarble()`：`/assets/textures/earth/blue_marble_4k.jpg`，`blueMarbleRequested` 防重入 |
| 每帧更新 | L7762–7783 | 渲染循环：`smoothstep(12,20,d)` → `earthFarMix`（lerp 0.15 跟随）；`_debugFarMixOverride` 非 null 时直接采用 |
| 验证钩子 | L2312–2325 | `getEarthFarMix` / `isBlueMarbleLoaded` / `__debugSetFarMix` / `__debugSetCameraDistance` |

> **关键结论**：`earthMaterial.map` 始终指向 `dayTexture`（近景瓦片图）即可保持现有管线；远景只需在 shader 里**额外混合**一张 `uMapFar`，不替换 `map`、不干扰 `tileManager` 生命周期。

---

## 2. 资源采集（Step 0 风格，PD）

- **来源**：NASA Visible Earth / SVS 的 **Blue Marble 真彩**（等距柱状 2:1，例如 "Blue Marble Next Generation" 或 "Blue Marble (land + ocean)" 合成图），公共领域（美国联邦政府作品）。
- **规格**：**4096×2048**（4K）。理由：深空里地球是中心参照体，屏幕占比往往大于远处小行星盘，2K 会偏软；4K 留余量，且只远景惰性加载。
- **落点**：`pwa/assets/textures/earth/blue_marble_4k.jpg`
- **校验**：脚本确认 mode=RGB、等距柱状 2:1、测 mean RGB 作参考（预期偏蓝绿海洋 + 棕绿陆地，约 (60–110, 80–130, 110–160) 区间，仅记录不强制）。
- **版权**：NASA PD，文档登记（参照 `celestial_texture_resources.md` 风格）。

---

## 3. earth3d.js 实现步骤

### 3.1 新增状态变量（near line 587 `dayTexture` 声明处）
```js
let blueMarbleTexture = null      // 远景 NASA 真彩（惰性加载）
let earthFarMix = 0               // 当前远景混合系数 0=近景 1=远景
let earthFarMixTarget = 0
let blueMarbleRequested = false   // 防止重复请求
```

### 3.2 惰性加载（首次进入远带时）
```js
function ensureBlueMarble() {
  if (blueMarbleRequested) return
  blueMarbleRequested = true
  new THREE.TextureLoader().load(
    '/assets/textures/earth/blue_marble_4k.jpg',
    (tex) => {
      if (THREE.sRGBEncoding !== undefined) tex.encoding = THREE.sRGBEncoding
      tex.minFilter = THREE.LinearMipmapLinearFilter
      tex.magFilter = THREE.LinearFilter
      tex.generateMipmaps = true
      blueMarbleTexture = tex
      if (earthShaderUniforms?.uMapFar) earthShaderUniforms.uMapFar.value = tex
    },
    undefined,
    (e) => console.error('[earthFar] Blue Marble 加载失败:', e)
  )
}
```
> `earthShaderUniforms` 指 onBeforeCompile 里保存的 shader 引用（沿用现有 `_prev` / `earthShaderUniforms` 模式）。

### 3.3 onBeforeCompile 注入（line 1750 区块内）
新增两个 uniform，并声明 fragment 变量：
```js
shader.uniforms.uMapFar  = { value: blueMarbleTexture ?? _maskPlaceholder }
shader.uniforms.uFarMix = { value: _prev?.uFarMix?.value ?? 0 }
```
在 `shader.fragmentShader` 顶部（`#include <common>` 之后或 `void main()` 前）插入声明：
```glsl
uniform sampler2D uMapFar;
uniform float uFarMix;
```
在 `#include <map_fragment>` **之后、且所有自定义海洋/陆地分级注入点之后**（albedo 计算全部完成、光照计算之前）插入混合。此处需**同时处理两件事**：① 把近景 `diffuseColor` 里已预乘的 `material.color`（各主题 mapColor，如 `0x8a98a4` 冷灰蓝、`0xF2E0C8` 暖米）随 `uFarMix` 淡向纯白，避免远景被主题色调染；② 再把 NASA 远景图混入。

```glsl
#ifdef USE_MAP
  // ① 材质基础色淡出：diffuse 即 MeshPhong material.color（已在 diffuseColor 预乘）
  vec3 _themeTint = diffuse;                              // 当前主题 mapColor
  vec3 _effTint   = mix(_themeTint, vec3(1.0), uFarMix);  // 远景：主题色 -> 纯白
  // 抵消 diffuseColor 中已含的 material.color，换成淡出版，远景零主题色残留
  diffuseColor.rgb *= (_effTint / max(_themeTint, vec3(1e-3)));

  // ② 混入 NASA Blue Marble 真彩（uMapFar 初始为 1x1 placeholder，uFarMix=0 时不影响）
  vec4 _farTexel = texture2D(uMapFar, vUv);
  diffuseColor.rgb = mix(diffuseColor.rgb, _farTexel.rgb, uFarMix);
#endif
```
> **自洽性证明**：
> - `uFarMix = 0`：`_effTint = _themeTint`，第一式乘子 = `1.0`，`diffuseColor` 不变；第二式 `mix` 保留 near → **与现状逐像素等价**（近景零影响）。
> - `uFarMix = 1`：第一式把 `material.color` 完全除掉，`diffuseColor = nearTexel`（纯反照率，无主题色）；第二式 `mix` 替换为 `_farTexel` → **输出 = 纯 Blue Marble，零主题色残留**。
> - 中间态：主题色与分级同时随 `uFarMix` 淡出，far 比例上升，呈现「半地图半真彩」过渡。
>
> `uMapFar` 初始为 1×1 placeholder（`_maskPlaceholder`），安全无副作用。

> **v1.2 实际实现说明**：上述 ①「`_effTint` 抵消 `material.color`」与 ②「mix 到 far」两式，在实现时合并为**单句**（见 §1「远景混合块」L2105–2110）：在 `#include <map_fragment>` 之后、所有海洋/陆地分级注入点之后，直接 `diffuseColor.rgb = mix(diffuseColor.rgb, _farTexel.rgb, uFarMix)`。因此刻 `diffuseColor` 已含 `material.color` 与全部分级，单句 `mix` 在 `uFarMix=0/1` 两端与两式逐像素等价，且注入点唯一、更易维护。§3.4 的「分级随远景淡出」因此**不再需要**——分级已被整段 `mix` 替换掉。

### 3.4 分级着色随远景淡出
> **范围说明**：本节只处理**海洋/陆地分级**（`uOceanLift`/`uOceanTeal`/`uLandStr`/`uLandLift` 等）随 `uFarMix` 淡出。**材质基础色 `material.color`（各主题 mapColor）** 的淡向纯白已在 §3.3 注入块内一并处理（见 `_effTint`），二者独立、同受 `uFarMix` 驱动，勿重复处理。

海洋/陆地分级逻辑读取 `map` 并改写 `diffuseColor`。远景时 NASA 图应呈**真彩**，不被分级重新染色。两种方式任选（推荐 b，改动最小）：

- **(a) JS 层**：每帧把 `uOceanLift`/`uOceanTeal`/`uLandStr`/`uLandLift` 等乘 `(1 - uFarMix)` 写回 uniform（需保存 theme 基值，重 applyTheme 会重置）。
- **(b) shader 层（推荐）**：在分级注入点把分级强度乘以 `(1.0 - uFarMix)`。例如原 `uOceanLift` 贡献处改为 `uOceanLift * (1.0 - uFarMix)`。具体注入点见现有 ocean grade / land grade 代码（搜索 `uOceanLift`、`uLandStr` 在 fragment 中的使用处）。

> 夜灯 emissiveMap 路径**不动**（保留，符合决策）。远景地球夜面仍发城市光，物理正确且具辨识度。

### 3.5 每帧更新（动画循环 / update 函数内）
```js
const THRESH = 20   // = MOON_VISIBLE_DIST，行星（月亮）出现临界；同时作为过渡上界
const LEAD   = 8    // 过渡起始提前量：d = THRESH - LEAD = 12 起开始淡入（过渡带 [12, 20]）
const d = getCameraDistanceToEarth()   // 相机→地心实际距离

if (d > THRESH - LEAD) ensureBlueMarble()   // 进入过渡带即惰性加载 4K

// smoothstep 目标：上界 = THRESH，故 d=20（月亮出现）时 uFarMix 恰好 = 1.0（完全真彩）
const t = THREE.MathUtils.smoothstep(d, THRESH - LEAD, THRESH)
earthFarMixTarget = t
// 平滑跟随，避免数值抖动
earthFarMix += (earthFarMixTarget - earthFarMix) * 0.15
if (earthShaderUniforms?.uFarMix) earthShaderUniforms.uFarMix.value = earthFarMix
```
> `THRESH` / `LEAD` 设为可调常量，便于后续微调。建议初值 `THRESH=20`、`LEAD=8`（过渡带 `[12, 20]`，d=20 时 `uFarMix=1.0` 完成过渡，与 §0 承诺一致）。

### 3.6 默认路径 / 近景零影响
- 当 `d < THRESH - LEAD`（即 `d < 12`）：`uFarMix = 0` → `diffuseColor` 完全 = 近景瓦片图 + 全部分级（且 `material.color` 未淡出）→ **与现状像素一致**。
- 不替换 `earthMaterial.map`、不改动 `tileManager`、不动 atmosphere / clouds / night texture / oceanMask。
- real-celestial.js 行星渲染逻辑**完全不碰**。

---

## 4. 阈值与淡入数学

```
uFarMix(d) = smoothstep(12, 20, d)      // d = 相机→地心距离；上界 = THRESH = MOON_VISIBLE_DIST = 20
  d ≤ 12  → 0.0  (纯近景地图风，与现状像素一致)
  12~20   → 0→1 交叉淡入（地球表面从地图风渐变为 NASA 真彩）
  d ≥ 20  → 1.0  (纯 NASA 真彩，与同框行星风格一致)
```
绑定 `MOON_VISIBLE_DIST=20`：月亮在 d≈20 出现，**此时 `uFarMix = smoothstep(12,20,20) = 1.0`，地球已完全 NASA 真彩**——过渡恰在 d=20 收口，而非半程。即**行星可见的整段区间（d≥20）里地球已是纯真彩**，绝无「半地图半真彩」与行星混合同框。这修正了初稿 `smoothstep(16,24,d)` 在 d=20 仅得 0.5 的矛盾（初稿 §0 承诺「出现即真彩」与 §4 公式不一致，现已统一）。

---

## 5. 风险与对策

| 风险 | 对策 |
|------|------|
| `uMapFar` 初始 null 导致 shader 采样崩溃 | 初始绑定 1×1 `_maskPlaceholder`（沿用现有模式）；`uFarMix=0` 时 mix 结果等同 near |
| onBeforeCompile 重编译丢失 uniform 值 | 沿用现有 `_pv(key, fallback)` 携带机制；`uFarMix` 默认 0 |
| 分级着色 / 材质色在远景重新染色 NASA 图 | 分级强度乘 `(1-uFarMix)` 淡出（§3.4）；材质基础色 `material.color` 经 §3.3 注入块 `_effTint = mix(diffuse, white, uFarMix)` 抵消，`uFarMix=1` 时 far 输出 = 纯 blueMarble，零主题色残留 |
| 4K 贴图加载阻塞近景 | 惰性加载（3.2），仅首次进入远带才请求 |
| 淡入带内地球闪烁 | 每帧 lerp 跟随（3.5 的 0.15 系数）+ smoothstep，非硬跳 |
| 改动误伤近景 | 近景 `uFarMix=0` 路径与现状逐像素等价；用基线截图比对验证 |

---

## 6. 验收标准（Playwright + 系统 Chrome swiftshader）

1. **近景零影响**：`d < 12` 时 `uFarMix = 0`，地球像素与改造前基线截图差异 < 阈值（my_code 改动不影响近景输出）。
2. **远景真彩 + 零主题色**：`d ≥ 20` 时 `uFarMix ≈ 1`，地球中心盘采样 RGB 接近 Blue Marble 实测均值（误差允许因光照/大气）；**切换冷灰蓝(`0x8a98a4`) / 暖米(`0xF2E0C8`) 等主题后远景地球色保持一致**，证明 `material.color` 已随 `uFarMix` 淡出、未染 far 贴图。
3. **交叉淡入**：`d ∈ [12,20]` 可见中间态（地球表面半地图半真彩过渡），无硬跳。
4. **夜灯保留**：远景夜面 city lights 仍可见（emissiveMap 未动）。
5. **行星一致性**：real-celestial.js 行星（月球/各行星）渲染与改造前完全一致；同框时地球风格与行星无错位。
6. **默认路径**：分类 console 报错 `my_code_errors = 0`。
7. **资源登记**：Blue Marble 4K 落盘 + 在 `celestial_texture_resources.md` 补一条地球远景条目（来源/年份/PD/实测均值）。

---

## 7. 不在范围内（明确排除）

- 不替换近景瓦片源（保持 RW 喜欢的近景地图风）。
- 不改 oceanMask / night texture / atmosphere / clouds / real-celestial.js 行星逻辑。
- 不为行星增加夜灯或大气（保持 #53 已定方案）。
- 不做「近景也统一成真彩」（选项 E，RW 已否决，近景保留）。

---

*本规格基于 `pwa/earth3d.js` 实际代码行号（2026-07-20 核实）与 #53/#54 Step 0 资源采集结论。执行后请回填实际改动行号与验证截图路径。*

---

## 8. 修订记录

- **2026-07-20（v1.1）** 据 RW 复核修正两处技术缺口：
  1. **阈值数学矛盾**：原 §4 `smoothstep(16,24,d)` 在 d=20 仅得 `uFarMix≈0.5`，与 §0「月亮出现即真彩」承诺冲突。改为 `smoothstep(12,20,d)`（过渡带 `[12,20]`、上界=THRESH=20），d=20 时 `uFarMix=1.0` 恰好收口；同步更新 §0/§3.5/§6 所有 `16/24` 引用为 `12/20`。
  2. **材质主题色残留**：原 §3.4 未处理 `material.color`（各主题 mapColor 非纯白）对 far 贴图的染色。在 §3.3 注入块新增 `_effTint = mix(diffuse, white, uFarMix)`，先抵消 `diffuseColor` 中预乘的 `material.color` 再 mix 到 far，保证 `uFarMix=1` 输出 = 纯 Blue Marble、零主题色残留；§3.4 增范围说明、§5 风险表合并、§6 验收新增「换主题后远景地球色一致」子项。

- **2026-07-20（v1.2，已执行）** 按 v1.1 实现并验证通过（Playwright swiftshader，5/5 PASS）。实际落点：
  - **单段交叉淡入（推荐等价格式）**：§3.3 的「`_effTint` 抵消 `material.color` 后再 `mix` 到 far」两式，实际合并为一句 —— 在 `#include <map_fragment>` 之后、**所有自定义海洋/陆地分级注入点之后**插入 `diffuseColor.rgb = mix(diffuseColor.rgb, _farTexel.rgb, uFarMix)`（`_farTexel = texture2D(uMapFar, vUv)`）。因 `diffuseColor` 此时已含 `material.color` 与全部分级，`mix(near, far, 0)` 逐像素等价近景、`mix(near, far, 1)` = 纯 Blue Marble（无主题色、无分级），与 §3.3 两式数学等价且改动点唯一、更不易出错。
  - **实际行号（v1.2 执行后）**：状态变量 `blueMarbleTexture/earthFarMix/earthFarMixTarget/blueMarbleRequested/_debugFarMixOverride` ≈ L590–595；`onBeforeCompile` 内 `uMapFar` uniform L1815、`uFarMix` L1816；fragment 声明 `uniform sampler2D uMapFar` L1865、`uniform float uFarMix` L1866；混合块（含注释）L2105–2110；`ensureBlueMarble()` L2268–2293；验证调试钩子 `getEarthFarMix/isBlueMarbleLoaded/__debugSetFarMix/__debugSetCameraDistance` L2312–2325；每帧更新（含 `_debugFarMixOverride` 权威覆盖分支）L7762–7783。
  - **调试钩子权威覆盖修复**：初版 `__debugSetFarMix(v)` 仅写 uniform，被每帧距离驱动更新覆盖（T2/T3 假阴性）。改为维护 `_debugFarMixOverride`（默认 null）；渲染循环检测其非 null 时直接采用该值（并据此触发 `ensureBlueMarble()`），否则走距离 `smoothstep(12,20,d)`。生产态永不调用，故默认路径零影响。
  - **资源**：`pwa/assets/textures/earth/blue_marble_4k.jpg`（NASA Blue Marble 真彩，5400×2700 源降采样至 4096×2048，2:1 等距柱状，PD，实测均值 RGB≈(63,74,91)）。
  - **验证**：`docs/roadmap/source_appendix/figures/verify_far_report.json` + 截图 `far_*.png`；验收 5 项全 PASS（近景零影响 / 远景真彩零主题色 / 主题一致性 / 距离映射 d=25→1、d=16→0.5、d=5→0 / realCelestial 远景 d=25 月球可见 d=60 太阳可见且地球仍真彩）；中心像素分析 `far_sunset_far`(br=-11.8) 与 `far_dawn_far`(br=-12.4) 差 0.6 → 主题色已完全移除。
  - **已知良性噪声**：静态校验服务器无 `/stream` WS（426）与零星 404，与本次改动无关，已在校验脚本过滤。
