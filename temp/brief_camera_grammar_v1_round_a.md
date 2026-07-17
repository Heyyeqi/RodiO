# RodiO 动态地球镜头系统 A轮:引擎骨架 + 3个构图 + 纬度运动原语

本轮阶段：生成候选 + 接入候选（合并一轮，参照本session之前 `level1motion`/`precomputeschedule`/`eastAsiaHeroV1` 三个候选的做法，每个都是一轮内完成生成+接入+调试入口）
本轮目标：见下文
允许修改文件：`pwa/earth3d.js`、`pwa/index.html`（仅 Theme Tuner 调试面板部分）
禁止修改文件：其余所有文件，尤其是 `core/*`、`server.js`
允许生成资源：否
允许 commit：否，除非我后续明确批准
本轮不处理事项：见"这一轮不做"
回滚方案：全部新增代码，且 gate 在新的 `?earthCandidate=cameraGrammarV1` 参数后面，默认不生效；出问题直接 `git diff` revert 即可

---

## 背景

用户反馈现有地球运动"千篇一律"：只有经度左右转，没有纬度上下运动，构图单一。外部协作者 Evan 提出了一套四层镜头语言体系（静态构图 `CAMERA_COMPOSITIONS` / 运动原语 `MOTION_PRIMITIVES` / 速度曲线 `MOTION_ENVELOPES` / 产品触发规则），核心思路是用"地球占屏幕比例/中心偏移"这类构图参数反推相机距离，而不是直接猜 Z/FOV 数值。

这一轮只做四层引擎的最小骨架（3个构图 + 1个新运动原语 + 过渡动画），不做完整的12个日常模式、评分引擎、歌曲联动——那些留到后续轮次。

## 现状（已核实，写代码前请自己也确认一遍，不要假设）

- `getTargetOrientation()`（`earth3d.js:5159`）目前只支持 lat/lon 目标 + 经度方向运动偏移（`_level1LonOffset` + `_precomputeLonOffset` 相加），**没有纬度偏移**，**没有 roll 自由度**。
- `quaternionFromBasis()`（`earth3d.js:396`）是纯正交基构造，没有绕视轴滚转能力——这轮不加 roll（3个构图都用不到）。
- `CAMERA_PRESETS`（`earth3d.js:6183`）现有9个预设，字段是 `lat/lon/centerMode/fov/cameraOffsetY/cameraOffsetZ/lookAtY`（`eastAsiaHeroV1` 额外有 `targetNdcX/targetNdcY/screenOffsetY`）。相机位置永远在 `(0, cameraOffsetY, cameraOffsetZ)`，lookAt 永远是 `(0, lookAtY, 0)`——相机被约束在 Y-Z 平面上，过渡插值不会有路径穿入地球的问题。
- `applyCameraPreset()`（`earth3d.js:6506`）是**瞬间硬切**，没有任何过渡动画——这次新增的过渡引擎不能复用它的调用方式，需要新写一个函数，不要改 `applyCameraPreset()` 本身。
- `_getVisualTargetNdc()`（`earth3d.js:2743`）已经支持"构图锚点"概念（NDC坐标，-1到1，0是屏幕中心，默认 `(0.25,-0.24)`），`eastAsiaHeroV1` 已经在用这个机制（写入 `window.__rodioVisualState._targetNdcX/_targetNdcY`）。**这次新构图的锚点直接复用这个已有机制**，不要另外发明一套 0-1 百分比坐标（Evan 文档里写的是百分比坐标，我们统一用现有NDC约定，这是有意的简化决定，不是遗漏）。
- 两个现有运动候选（`_level1Motion`/`_precomputeMotion`）通过同一个 `?earthCandidate=` 参数互斥选择，各自独立写偏移字段到 `window.__rodioVisualState`。这次新加的是**第三个独立候选**，**不要修改这两者任何一行代码**。
- 渲染循环（`earth3d.js:6219`）执行顺序：`_updateLevel1Motion()` → `_updatePrecomputeMotion()` → 缩放lerp（`camera.position.z += (target-current)*0.08`，刚修的平滑写法，不要动）→ `getTargetOrientation()` → `earth.quaternion.slerp(target, 0.02)` → 渲染。新逻辑插入这个循环，不能打乱现有顺序，也不要去改缩放lerp那几行。
- 主题系统（`THEME_VISUAL_CONFIG`/`applyTheme()`）和相机状态完全解耦——这轮不碰颜色/光照/大气参数。

## 要做的事

### 1. 四层数据结构骨架

在 `earth3d.js` 里 `CAMERA_PRESETS`（`6183`附近）旁边新增：

```js
const CAMERA_COMPOSITIONS = {
  homeGlobe: null,  // 特殊值：表示直接复用 CAMERA_PRESETS.globe，不重复定义数值
  portraitMarble: {
    lat: 31.23, lon: 121.47,
    earthDiameterPct: 0.72,
    anchorNdcX: 0.0, anchorNdcY: -0.08,
    fov: 27,
  },
  farOrbit: {
    lat: 31.23, lon: 121.47,
    earthDiameterPct: 0.32,
    anchorNdcX: 0.0, anchorNdcY: 0.0,
    fov: 28,
  },
}

const MOTION_PRIMITIVES = {
  hold: {},
  latitudeDrift: { rangeDeg: 6, periodSec: 40 },
}

const MOTION_ENVELOPES = {
  linear: (t) => t,
  easeInOutCubic: (t) => t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t+2, 3)/2,
  easeOutCubic: (t) => 1 - Math.pow(1-t, 3),
}
```

上面这些具体数值都是起点，视觉调试后可以调整，不需要锁死这几个数字，但结构（字段名）请照抄，后续轮次要在这个结构上继续加东西。

### 2. 构图参数 → 相机距离反推函数

不要用"地球半径大概是2.0"这种猜测，从真实几何体读半径：

```js
function computeCameraOffsetZForComposition(earthDiameterPct, fovDeg) {
  const earthRadius = earth.geometry.parameters.radius  // 实际读取，不要硬编码
  const fovRad = fovDeg * Math.PI / 180
  const alpha = Math.atan(earthDiameterPct * Math.tan(fovRad / 2))
  return earthRadius / Math.sin(alpha)
}
```

这是标准透视投影下"给定屏幕占比和FOV反推距离"的公式（角半径 alpha 满足 tan(alpha)/tan(halfFov) = 目标屏幕占比，再用 sin(alpha) = 半径/距离 反解距离）。`portraitMarble`/`farOrbit` 的相机 Z 距离都通过调用这个函数得到，不要直接写死一个猜的 Z 值。

### 3. 固定时长可打断过渡动画

新写一个函数（不要改 `applyCameraPreset()`）：

```js
let _gramTransition = null  // { fromY, fromZ, fromFov, toY, toZ, toFov, toNdcX, toNdcY, startTime, duration, envelope }

function transitionToComposition(compositionKey, opts = {}) {
  const duration = opts.duration ?? 4
  const envelopeName = opts.envelope ?? 'easeInOutCubic'
  const comp = compositionKey === 'homeGlobe' ? CAMERA_PRESETS.globe : CAMERA_COMPOSITIONS[compositionKey]
  if (!comp) return false

  const targetZ = compositionKey === 'homeGlobe'
    ? comp.cameraOffsetZ
    : computeCameraOffsetZForComposition(comp.earthDiameterPct, comp.fov)
  const targetY = compositionKey === 'homeGlobe' ? comp.cameraOffsetY : 0
  const targetFov = comp.fov
  const targetNdcX = compositionKey === 'homeGlobe' ? undefined : comp.anchorNdcX
  const targetNdcY = compositionKey === 'homeGlobe' ? undefined : comp.anchorNdcY

  // 从相机当前实时状态开始，不是从上一个构图的起点开始
  _gramTransition = {
    fromY: camera.position.y, fromZ: camera.position.z, fromFov: camera.fov,
    toY: targetY, toZ: targetZ, toFov: targetFov,
    toNdcX: targetNdcX, toNdcY: targetNdcY,
    toLat: comp.lat ?? (compositionKey === 'homeGlobe' ? CAMERA_PRESETS.globe.lat : 31.2304),
    toLon: comp.lon ?? (compositionKey === 'homeGlobe' ? CAMERA_PRESETS.globe.lon : 121.4737),
    startTime: performance.now() / 1000,
    duration,
    envelope: MOTION_ENVELOPES[envelopeName] || MOTION_ENVELOPES.easeInOutCubic,
  }
  return true
}

function _updateGramTransition() {
  if (!_gramTransition) return
  const now = performance.now() / 1000
  const t = Math.min(1, (now - _gramTransition.startTime) / _gramTransition.duration)
  const e = _gramTransition.envelope(t)
  camera.position.y = _gramTransition.fromY + (_gramTransition.toY - _gramTransition.fromY) * e
  camera.position.z = _gramTransition.fromZ + (_gramTransition.toZ - _gramTransition.fromZ) * e
  camera.fov = _gramTransition.fromFov + (_gramTransition.toFov - _gramTransition.fromFov) * e
  camera.updateProjectionMatrix()
  if (!window.__rodioVisualState) window.__rodioVisualState = {}
  window.__rodioVisualState.lat = _gramTransition.toLat
  window.__rodioVisualState.lon = _gramTransition.toLon
  if (Number.isFinite(_gramTransition.toNdcX)) window.__rodioVisualState._targetNdcX = _gramTransition.toNdcX
  if (Number.isFinite(_gramTransition.toNdcY)) window.__rodioVisualState._targetNdcY = _gramTransition.toNdcY
  if (t >= 1) _gramTransition = null
}
```

（以上是设计思路和大致实现，具体写法你可以按代码库现有风格调整，但"从当前实时状态开始插值、新过渡触发时替换旧的_gramTransition、固定时长、用envelope函数"这几个行为要保留。地球朝向不用在这里处理，仍然走现有的 `getTargetOrientation()` + `slerp`，这个过渡函数只管相机 position/fov 和 NDC锚点。）

在渲染循环（`earth3d.js:6219`）里，`_updatePrecomputeMotion()` 之后加一行 `_updateGramTransition()`（只在 `_gramMotion.enabled` 时调用，见下）。

### 4. 纬度运动原语

参照 `_level1Motion`（`earth3d.js:22-77`）的写法风格，新增：

```js
let _gramMotion = (function () {
  const m = { enabled: false, latOffset: 0 }
  if (typeof window !== 'undefined') {
    m.enabled = new URLSearchParams(window.location.search).get('earthCandidate') === 'cameraGrammarV1'
  }
  return m
})()

let _gramLatDriftEnabled = false  // 由调试面板开关控制

function _updateGramMotion() {
  if (!_gramMotion.enabled) return
  if (_gramLatDriftEnabled) {
    const cfg = MOTION_PRIMITIVES.latitudeDrift
    const t = performance.now() / 1000
    _gramMotion.latOffset = cfg.rangeDeg * Math.sin((2 * Math.PI * t) / cfg.periodSec)
  } else {
    _gramMotion.latOffset = 0
  }
  if (!window.__rodioVisualState) window.__rodioVisualState = {}
  window.__rodioVisualState._gramLatOffset = _gramMotion.latOffset
  _updateGramTransition()
}
```

在渲染循环里，`_updatePrecomputeMotion()` 后面加一行 `_updateGramMotion()`（这一行同时负责调用上面第3步的过渡更新，见函数体最后一行）。

`getTargetOrientation()`（`earth3d.js:5159`）里，在计算 `lat` 那一行加纬度偏移，跟现有经度偏移写法完全对称：

```js
// 现有经度偏移写法（不要动，照抄这个风格）：
// const level1Offset = _level1Motion.enabled ? (vs._level1LonOffset || 0) : 0
// const precomputeOffset = _precomputeMotion.enabled ? (vs._precomputeLonOffset || 0) : 0
// const lon = normalizeLon((Number.isFinite(vs.lon) ? vs.lon : 121.4737) + level1Offset + precomputeOffset)

// 新增对称的纬度偏移：
const gramLatOffset = _gramMotion.enabled ? (vs._gramLatOffset || 0) : 0
const lat = clamp((Number.isFinite(vs.lat) ? vs.lat : 31.2304) + gramLatOffset, -80, 80)
```

**重要**：纬度是正弦往返（`±rangeDeg`），不是像经度那样单向累加——纬度往一个方向转到底会转到极点附近，画面会很奇怪，这跟经度可以一直转圈不一样，不要写成累加逻辑。

### 5. 调试面板入口

参照 `pwa/index.html` 里现有 "Camera Presets (E7 debug)" 那个 GUI 折叠面板的写法（搜索 `Camera Presets` 或 `dbgBtns` 附近的代码），新增一个类似的面板（比如叫 "Camera Grammar V1 (debug)"），只在 `?earthCandidate=cameraGrammarV1` 时显示，包含：
- 三个按钮：切换到 `homeGlobe`/`portraitMarble`/`farOrbit`（调用 `earth3dApi.transitionToComposition(key)`，需要把 `transitionToComposition` 加到 `earth3dApi` 的 `Object.assign` 导出里，不要漏掉——**这正是上次 `eastAsiaHeroV1` 那个boot-hang bug的根源**，`applyCameraPreset` 是 `Object.assign(earth3dApi,{...})` 里的属性不是裸函数，这次新函数也要放进同一个 `Object.assign` 导出，调用方式必须是 `earth3dApi.transitionToComposition(...)`，不能裸调用）
- 一个开关：打开/关闭 `latitudeDrift`（直接设置 `_gramLatDriftEnabled` 变量，或者提供一个 `earth3dApi.setGramLatDrift(bool)` 方法）

## 严格边界

**只允许修改**：`pwa/earth3d.js`（新增代码块，不修改现有 `_level1Motion`/`_precomputeMotion`/`CAMERA_PRESETS`/`applyCameraPreset`/`getTargetOrientation`除了新增那一行/渲染循环除了新增两行调用）、`pwa/index.html`（仅新增调试面板部分）。

**禁止修改**：其他任何文件；现有三个候选（`level1motion`/`precomputeschedule`/`eastAsiaHeroV1`）的任何现有代码；`THEME_VISUAL_CONFIG`/`applyTheme()`；任何 shader/颜色/光照参数；roll（这轮不加）；晨昏线相关构图（这轮不做，虽然已解冻）。

## 这一轮不做

- Roll、`terminatorPortrait`、独立晨昏线特效、12个日常模式、评分引擎、去重规则、歌曲生命周期、跟播放/情绪的自动联动——这些都是后续轮次的事，这轮只做手动调试可验证的引擎骨架。

## 完成后请提供

1. 实际修改的文件清单和 git diff
2. 三个构图反推出来的实际 `cameraOffsetZ` 数值（验证公式算出来的结果是否合理）
3. 验证截图：`homeGlobe`/`portraitMarble`/`farOrbit` 三个构图各一张
4. 确认 `earth3dApi.transitionToComposition` 是通过 `Object.assign` 正确导出的（不是裸函数调用）
5. 确认默认播放、`level1motion`、`precomputeschedule`、`eastAsiaHeroV1` 四者未受影响

## 验证方式

1. 加 `?earthCandidate=cameraGrammarV1`，用调试面板手动切换三个构图，确认平滑过渡（不是瞬间跳变），`portraitMarble` 地球明显更小、四周留白明显，`farOrbit` 更小、宇宙感更强
2. 连续快速切换（上一个过渡没播完就点下一个），确认新过渡从当前实时画面接续，不会跳回起点重新开始
3. 打开 `latitudeDrift` 开关，确认地球有肉眼可见的上下往返运动，不会转到极点附近产生怪异画面
4. 确认默认播放、`level1motion`、`precomputeschedule`、`eastAsiaHeroV1` 四者行为完全不受影响，控制台无新增报错
