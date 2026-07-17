# RodiO 动态地球镜头系统 B轮:运动原语可切换 + 补齐经度/斜向运动 + terminatorPortrait构图

本轮阶段：生成候选 + 接入候选（延续 A轮做法，一轮内完成）
本轮目标：见下文
允许修改文件：`pwa/earth3d.js`、`pwa/index.html`（仅 "Camera Grammar V1 (debug)" 面板部分）
禁止修改文件：其余所有文件
允许生成资源：否
允许 commit：否，除非我后续明确批准
本轮不处理事项：见"这一轮不做"
回滚方案：全部改动在 `?earthCandidate=cameraGrammarV1` gate 后面，且是 A轮已有代码的小范围扩展，出问题直接 revert 这几处 diff

---

## 背景

A轮已上线并验证通过:四层引擎骨架、构图占比反推相机距离公式、固定时长过渡引擎、纬度往返运动原语(`latitudeDrift`)。全部 gate 在 `?earthCandidate=cameraGrammarV1`。

A轮遗留一个问题:`_updateGramMotion()`(`earth3d.js:201`附近)**只硬编码了 latitudeDrift 一种行为**,`MOTION_PRIMITIVES` 虽然定义了 `hold`/`latitudeDrift` 两个条目，但运行时不会真的按选中哪个去分支。这轮要把它变成真正可切换的选择器,补齐经度/斜向运动原语,再加一个新构图 `terminatorPortrait`(已经过 Terminator 解冻审计确认可以做,见下文)。

## 现状(A轮验证过的部分,不要动)

- `_gramMotion`(`earth3d.js:189-195`)、`_gramLatDriftEnabled`/`_gramMotionPrimitives`(`197-199`)、`_updateGramMotion()`(`201-217`)
- `CAMERA_COMPOSITIONS`/`MOTION_PRIMITIVES`/`MOTION_ENVELOPES`(`earth3d.js:6240-6264`)、`computeCameraOffsetZForComposition()`(`6266`附近)、`transitionToComposition()`/`_updateGramTransition()`(`earth3d.js:6296`附近）
- `getTargetOrientation()`(`earth3d.js:5188`附近)现有的经度计算:`(vs.lon 或默认值) + level1Offset + precomputeOffset`,纬度计算已经加了 `+ gramLatOffset`
- `earth3dApi.setGramLatDrift(enabled)`(`earth3d.js:6668`附近，在 `Object.assign(earth3dApi,{...})` 导出块里)
- `pwa/index.html:5301`附近的 "Camera Grammar V1 (debug)" 面板,现有3个构图按钮 + 1个 latitudeDrift checkbox

## 要做的事

### 1. `_updateGramMotion()` 从硬编码改成按选中原语分支

```js
let _gramActivePrimitive = 'latitudeDrift'  // 'hold' | 'latitudeDrift' | 'longitudeDrift' | 'diagonalDrift'
let _gramMotionPrimitives = null  // 桥接变量不变，沿用 A轮已有的赋值方式

function _updateGramMotion() {
  if (!_gramMotion.enabled) return
  if (!_gramMotion.startTime) _gramMotion.startTime = performance.now() / 1000
  const elapsed = (performance.now() / 1000) - _gramMotion.startTime
  const prim = _gramActivePrimitive
  let latOffset = 0, lonOffset = 0

  if (prim === 'latitudeDrift' || prim === 'diagonalDrift') {
    const cfg = (_gramMotionPrimitives && _gramMotionPrimitives.latitudeDrift) || { rangeDeg: 6, periodSec: 40 }
    latOffset = Math.sin((elapsed % cfg.periodSec) / cfg.periodSec * Math.PI * 2) * (cfg.rangeDeg / 2)
  }
  if (prim === 'longitudeDrift' || prim === 'diagonalDrift') {
    const cfg = (_gramMotionPrimitives && _gramMotionPrimitives.longitudeDrift) || { degPerSec: 0.8 }
    lonOffset = (elapsed * cfg.degPerSec) % 360
  }

  if (!window.__rodioVisualState) window.__rodioVisualState = {}
  window.__rodioVisualState._gramLatOffset = latOffset
  window.__rodioVisualState._gramLonOffset = lonOffset
}
```

**`setGramLatDrift(bool)` 保留向后兼容**,内部实现改成:
```js
setGramLatDrift(enabled) {
  _gramActivePrimitive = enabled ? 'latitudeDrift' : 'hold'
  return _gramActivePrimitive
},
```

**新增 `setGramPrimitive(key)`**,放进同一个 `Object.assign(earth3dApi,{...})` 导出块(跟 `setGramLatDrift`/`transitionToComposition` 放在一起,不要写成裸函数——A轮那次 boot-hang bug 的教训,这次的检查重点还是这个):
```js
setGramPrimitive(key) {
  if (!MOTION_PRIMITIVES[key]) return false
  _gramActivePrimitive = key
  return true
},
```

### 2. `getTargetOrientation()`(`earth3d.js:5188`附近)叠加经度偏移

现有代码(不要动经度/纬度已有的部分，只加 `gramLonOffset` 这一项):
```js
const gramLatOffset = _gramMotion.enabled ? (vs._gramLatOffset || 0) : 0
const gramLonOffset = _gramMotion.enabled ? (vs._gramLonOffset || 0) : 0
const lon = normalizeLon(
  (Number.isFinite(vs.lon) ? vs.lon : 121.4737) + level1Offset + precomputeOffset + gramLonOffset
)
const lat = clamp((Number.isFinite(vs.lat) ? vs.lat : 31.2304) + gramLatOffset, -80, 80)
```

`longitudeDrift` 是单向持续累加(经度可以一直转圈,不像纬度会转到极点),不需要 smoothstep 缓动。

### 3. `MOTION_PRIMITIVES` 补两个条目(`earth3d.js:6255`附近)

```js
const MOTION_PRIMITIVES = {
  hold: {},
  latitudeDrift: { rangeDeg: 6, periodSec: 40 },
  longitudeDrift: { degPerSec: 0.8 },
  diagonalDrift: {},  // 复用上面两个的参数，不重复定义数值
}
```

### 4. 新构图 `terminatorPortrait`(`earth3d.js:6240`附近的 `CAMERA_COMPOSITIONS`)

```js
terminatorPortrait: {
  lat: 31.23, lon: 121.47,
  earthDiameterPct: 0.72,
  anchorNdcX: 0.0, anchorNdcY: -0.08,
  fov: 27,
},
```

这个构图已经过 Terminator 解冻审计确认可以做——地球材质昼夜分界是现有真实太阳位置计算的自然渲染结果，这次不新增任何 shader/渲染代码，纯粹是相机取景，跟 `portraitMarble`/`farOrbit` 走同一套 `computeCameraOffsetZForComposition()` 逻辑。

**这次不加 roll**，晨昏线在画面里的具体角度这次不精确控制，只是这组经纬度+当前太阳方向算出来的自然结果，先能用即可，后续如果需要精确调角度再单独加 roll。

### 5. 调试面板更新(`pwa/index.html:5301`附近)

把现有的单一 `latitudeDrift` checkbox 换成下拉选择器:
```js
var gramPrimitiveCtl = { primitive: 'latitudeDrift' }
fGrammar.add(gramPrimitiveCtl, 'primitive', ['hold', 'latitudeDrift', 'longitudeDrift', 'diagonalDrift'])
  .name('Motion Primitive')
  .onChange(function (v) { e3d.setGramPrimitive?.(v) })
```
再照抄现有三个构图按钮的写法，加一个 `terminatorPortrait` 按钮。

## 严格边界

**只允许改动**:`_updateGramMotion()` 内部逻辑、`getTargetOrientation()` 加经度偏移那一行、`MOTION_PRIMITIVES`/`CAMERA_COMPOSITIONS` 新增条目、`earth3dApi` 新增 `setGramPrimitive()`、`setGramLatDrift()` 内部实现调整（保持向后兼容的行为，调用方式不变）、debug 面板换成下拉选择器 + 新增按钮。

**禁止改动**:`computeCameraOffsetZForComposition()`、`transitionToComposition()`、`_updateGramTransition()`、`homeGlobe`/`portraitMarble`/`farOrbit` 已有数值、三个既有候选(`level1motion`/`precomputeschedule`/`eastAsiaHeroV1`)的任何代码、roll(不加)、`THEME_VISUAL_CONFIG`/`applyTheme()`。

## 这一轮不做

Roll、`polarDiagonal`/`cityAnchor`/`oceanExpanse`/`horizonSkim`/`limbHero` 等其余构图、12个日常模式、评分引擎、去重、歌曲生命周期、跟播放/情绪的自动联动。

## 完成后请提供

1. git diff
2. 四种运动原语(`hold`/`latitudeDrift`/`longitudeDrift`/`diagonalDrift`)切换后的实际截图或数值变化记录
3. `terminatorPortrait` 构图截图
4. 确认 `setGramPrimitive` 是通过 `Object.assign` 正确导出的（不是裸函数调用）
5. 确认默认播放、`level1motion`、`precomputeschedule`、`eastAsiaHeroV1`、A轮三个构图(`homeGlobe`/`portraitMarble`/`farOrbit`)均未受影响

## 验证方式

1. `?earthCandidate=cameraGrammarV1`，依次切换四种运动原语，确认行为符合预期(hold不动、latitudeDrift纬度往返、longitudeDrift经度持续转、diagonalDrift两者叠加)
2. 切到 `terminatorPortrait`，确认能看到明暗过渡
3. 控制台无新增报错
4. 独立复核 `_gramActivePrimitive`/`setGramPrimitive` 的实际接线，不要只看报告
