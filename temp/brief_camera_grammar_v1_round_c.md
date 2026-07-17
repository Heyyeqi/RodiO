# RodiO 动态地球镜头系统 C轮:补齐剩余构图(含新增roll能力)

本轮阶段：生成候选 + 接入候选（延续 A/B轮做法，一轮内完成）
本轮目标：见下文
允许修改文件：`pwa/earth3d.js`、`pwa/index.html`（仅 "Camera Grammar V1 (debug)" 面板部分）
禁止修改文件：其余所有文件
允许生成资源：否
允许 commit：否，除非我后续明确批准
本轮不处理事项：见"这一轮不做"
回滚方案：全部改动在 `?earthCandidate=cameraGrammarV1` gate 后面，出问题直接 revert 这几处 diff

---

## 背景

A/B轮已上线并验证通过:四层引擎骨架、构图占比反推相机距离、固定时长过渡引擎、4种运动原语(`hold`/`latitudeDrift`/`longitudeDrift`/`diagonalDrift`)、4个构图(`homeGlobe`/`portraitMarble`/`farOrbit`/`terminatorPortrait`)。这轮补齐 Evan 方案里剩余的5个构图(`polarDiagonal`/`cityAnchor`/`oceanExpanse`/`horizonSkim`/`limbHero`),其中 `polarDiagonal` 需要新增相机滚转(roll)能力——这是 A/B轮明确排除、这次才要加的自由度。不接歌曲播放联动，仍然是纯 debug 面板手动验证。

## 现状(已核实，写代码前自己也确认一遍)

- `getTargetOrientation()`(`earth3d.js:5202`)算出 `targetNormal` 后，取 `screenUp.projectOnPlane(targetNormal)` 当"北"方向传给 `quaternionFromBasis()`——这个取法决定了画面永远是正的，没有 roll 自由度。
- `quaternionFromBasis()`(`earth3d.js:396`)是纯基向量构造，**不需要改这个函数本身**——把传给它的 `targetNorth` 提前绕 `targetNormal` 轴转一个角度，就能实现 roll。
- `transitionToComposition()`(`earth3d.js:6296`附近)目前按 `compositionKey === 'homeGlobe'` 特判来决定用 `earthDiameterPct` 公式还是写死0。这次新增的 `horizonSkim`/`limbHero` 是贴近地表的近景构图，"占屏比例反推距离"这个几何关系在近景不适用（地平线会超出画面边缘，不是能用"直径占比"描述的完整圆盘），这两个要**直接给 `cameraOffsetY`/`cameraOffsetZ` 数值**（跟老的 `CAMERA_PRESETS.horizon`/`.lowOrbit` 一样的直给方式）。所以判断条件要从"是否homeGlobe"改成"这个构图有没有定义 `earthDiameterPct`"。
- `CAMERA_PRESETS.oceanView`(`earth3d.js:6222`附近)已有验证过的大洋视角坐标(`lat:-10.0, lon:-140.0`)，`oceanExpanse` 直接复用。

## 要做的事

### 1. 新增 roll 能力(`getTargetOrientation()`,`earth3d.js:5202`附近)

在计算完 `targetNorth` 并归一化之后、调用 `quaternionFromBasis()` 之前，加:
```js
const gramRollDeg = _gramMotion.enabled ? (vs._gramRollDeg || 0) : 0
if (gramRollDeg !== 0) {
  targetNorth.applyAxisAngle(targetNormal, gramRollDeg * Math.PI / 180)
}
```
只在 `_gramMotion.enabled` 时生效（跟纬度/经度偏移的写法完全对称），其他候选/默认播放的 `_gramRollDeg` 永远是0，不受影响。

roll 不需要新的插值机制——跟现有 lat/lon/NDC锚点一样，只在 `_updateGramTransition()` 的 `t>=1` 收尾块里一次性写入 `vs._gramRollDeg`，平滑效果完全靠已有的 `earth.quaternion.slerp(target, 0.02)` 逐帧追赶新目标（这个函数每帧都会重新调用 `getTargetOrientation()`，所以 roll 值变化后会自动被下一次 slerp 捕捉到）。

### 2. `transitionToComposition()` 判断条件泛化(`earth3d.js:6296`附近)

把 `compositionKey === 'homeGlobe'` 特判改成按构图是否定义 `earthDiameterPct` 判断：

```js
function transitionToComposition(compositionKey, opts = {}) {
  const duration = opts.duration ?? 4
  const envelopeName = opts.envelope ?? 'easeInOutCubic'
  const comp = compositionKey === 'homeGlobe' ? CAMERA_PRESETS.globe : CAMERA_COMPOSITIONS[compositionKey]
  if (!comp) return false

  const usesPercentFormula = compositionKey !== 'homeGlobe' && Number.isFinite(comp.earthDiameterPct)
  const targetZ = usesPercentFormula
    ? computeCameraOffsetZForComposition(comp.earthDiameterPct, comp.fov)
    : comp.cameraOffsetZ
  const targetY = compositionKey === 'homeGlobe'
    ? comp.cameraOffsetY
    : (Number.isFinite(comp.cameraOffsetY) ? comp.cameraOffsetY : 0)
  const targetFov = comp.fov
  const targetNdcX = compositionKey === 'homeGlobe' ? undefined : comp.anchorNdcX
  const targetNdcY = compositionKey === 'homeGlobe' ? undefined : comp.anchorNdcY
  const targetRollDeg = compositionKey === 'homeGlobe' ? 0 : (comp.rollDeg || 0)

  _gramTransition = {
    fromY: camera.position.y, fromZ: camera.position.z, fromFov: camera.fov,
    toY: targetY, toZ: targetZ, toFov: targetFov,
    toNdcX: targetNdcX, toNdcY: targetNdcY, toRollDeg: targetRollDeg,
    toLat: comp.lat ?? (compositionKey === 'homeGlobe' ? CAMERA_PRESETS.globe.lat : 31.2304),
    toLon: comp.lon ?? (compositionKey === 'homeGlobe' ? CAMERA_PRESETS.globe.lon : 121.4737),
    startTime: performance.now() / 1000,
    duration,
    envelope: MOTION_ENVELOPES[envelopeName] || MOTION_ENVELOPES.easeInOutCubic,
  }
  return true
}
```

`_updateGramTransition()` 在 `t>=1` 的收尾块里，跟现有写 `vs._targetNdcX`/`vs._targetNdcY` 完全对称地加一行 `vs._gramRollDeg = _gramTransition.toRollDeg`。

**注意**：`homeGlobe`/`portraitMarble`/`farOrbit`/`terminatorPortrait` 这4个已验证过的构图都没有 `rollDeg` 字段，`targetRollDeg` 对它们应该正确落到 `0`（`comp.rollDeg || 0`），不能因为这次的泛化改动导致它们的行为发生任何变化——完成后请专门确认这4个构图切换后 `_gramRollDeg` 确实是0。

### 3. 补5个构图(`CAMERA_COMPOSITIONS`,`earth3d.js:6250`附近)

用 `earthDiameterPct` 反推距离的3个：
```js
polarDiagonal: {
  lat: 68, lon: 90,
  earthDiameterPct: 0.6,
  anchorNdcX: 0.0, anchorNdcY: 0.0,
  fov: 26,
  rollDeg: 10,
},
cityAnchor: {
  lat: 31.23, lon: 121.47,
  earthDiameterPct: 0.65,
  anchorNdcX: 0.0, anchorNdcY: -0.15,
  fov: 27,
},
oceanExpanse: {
  lat: -10.0, lon: -140.0,   // 复用 CAMERA_PRESETS.oceanView 已验证过的坐标
  earthDiameterPct: 0.55,
  anchorNdcX: 0.15, anchorNdcY: 0.1,
  fov: 26,
},
```
直给相机参数的2个近景构图(不用 `earthDiameterPct`)：
```js
horizonSkim: {
  lat: 25.0, lon: 121.0,
  cameraOffsetY: 1.6, cameraOffsetZ: 3.7,
  anchorNdcX: 0.0, anchorNdcY: -0.3,
  fov: 13,
},
limbHero: {
  lat: 31.23, lon: 121.47,
  cameraOffsetY: 1.0, cameraOffsetZ: 4.2,
  anchorNdcX: 0.0, anchorNdcY: -0.35,
  fov: 26,
},
```
以上数值都是起点，视觉调试后可以调整，不需要锁死。

### 4. 调试面板加5个按钮(`pwa/index.html:5301`附近)

`gramCompositions` 数组追加 `'polarDiagonal', 'cityAnchor', 'oceanExpanse', 'horizonSkim', 'limbHero'` 这5个 key，照抄现有按钮生成逻辑（`forEach` 循环里的写法），不需要新写模板。

## 严格边界

**只允许改动**:`getTargetOrientation()` 加 roll 应用那几行、`transitionToComposition()` 的条件判断泛化 + `toRollDeg` 字段、`_updateGramTransition()` 收尾块加一行、`CAMERA_COMPOSITIONS` 新增5个构图、debug 面板的 `gramCompositions` 数组。

**禁止改动**:`quaternionFromBasis()`、`_updateGramMotion()`（运动原语部分不动）、`MOTION_PRIMITIVES`、已有的4个构图(`homeGlobe`/`portraitMarble`/`farOrbit`/`terminatorPortrait`)数值、三个既有候选(`level1motion`/`precomputeschedule`/`eastAsiaHeroV1`)代码、`THEME_VISUAL_CONFIG`/`applyTheme()`。

## 这一轮不做

歌曲生命周期时序、跟播放/情绪的自动联动、评分引擎、roll类型的运动原语（持续滚转）——这些都留到后续轮次。

## 完成后请提供

1. git diff
2. 5个新构图切换后的截图
3. `polarDiagonal` 切换前后 `_gramRollDeg` 的实际数值（确认非0），以及切到其他4个已验证构图时 `_gramRollDeg` 确认是0
4. 确认默认播放、`level1motion`、`precomputeschedule`、`eastAsiaHeroV1`、A/B轮已验证的4个构图和4种运动原语均未受影响

## 验证方式

1. `?earthCandidate=cameraGrammarV1`，依次切换5个新构图，确认能正常渲染、无穿模/黑屏
2. 重点看 `polarDiagonal`——确认画面有对角线/倾斜构图效果，切换到其他构图后画面恢复水平，不残留倾斜
3. `horizonSkim`/`limbHero` 确认地表细节可见、地平线/大气边缘自然，没有相机穿入地球内部的情况
4. 控制台无新增报错
