# RodiO 动态地球镜头系统 D轮:Deep Space构图 + Breathe/RollDrift两个新运动原语

本轮阶段：生成候选 + 接入候选（延续A/B/C轮做法，一轮内完成）
本轮目标：见下文
允许修改文件：`pwa/earth3d.js`、`pwa/index.html`（仅 "Camera Grammar V1 (debug)" 面板部分）
禁止修改文件：其余所有文件
允许生成资源：否
允许 commit：否，除非我后续明确批准
本轮不处理事项：见"这一轮不做"
回滚方案：全部改动在 `?earthCandidate=cameraGrammarV1` gate 后面，且是既有引擎的小范围扩展，出问题直接 revert 这几处 diff

---

## 背景

A/B/C三轮已做完9个构图、4种运动原语、roll自由度（目前只是构图的静态值）。这轮补：`deepSpace`构图（老`CAMERA_PRESETS`里早就有现成数值，纯搬运）、`breathe`原语（相机距离低频呼吸）、`rollDrift`原语（把roll从静态值升级成能持续摆动的原语）。

## 现状(不要动的部分)

- `CAMERA_COMPOSITIONS`(`earth3d.js:6255`)现有9个构图；老`CAMERA_PRESETS.deepSpace`数值是`{ fov: 28, cameraOffsetY: 0.0, cameraOffsetZ: 80.0, lookAtY: 0.0 }`
- `_updateGramMotion()`(`earth3d.js:202`附近)按`_gramActivePrimitive`分支，目前处理`latitudeDrift`/`longitudeDrift`/`diagonalDrift`
- `getTargetOrientation()`(`earth3d.js:5202`附近)读取`vs._gramLatOffset`/`_gramLonOffset`/`_gramRollDeg`
- `transitionToComposition()`/`_updateGramTransition()`(`earth3d.js:6330`附近)——过渡结束(`_gramTransition = null`)后不会再有代码碰`camera.position.z`
- `setGramPrimitive(key)`白名单目前是`['hold','latitudeDrift','longitudeDrift','diagonalDrift']`
- debug面板下拉(`index.html:5301`附近)同样是这4个选项

## 要做的事

### 1. Deep Space构图

```js
// CAMERA_COMPOSITIONS 里加:
deepSpace: {
  lat: 31.23, lon: 121.47,
  cameraOffsetZ: 80.0,
  fov: 28,
},
```
走现有`transitionToComposition()`里"没有`earthDiameterPct`就用`cameraOffsetZ`原始值"那条分支（跟`horizonSkim`/`limbHero`一样），不需要新逻辑。

### 2. Breathe原语

`MOTION_PRIMITIVES`加：
```js
breathe: { amplitudePct: 0.025, periodSec: 30 },
```

新增模块级变量（跟`_gramLastLookAtY`放一起）：
```js
let _gramSettledZ = null
```

`_updateGramTransition()`的`t>=1`收尾块加一行：
```js
_gramSettledZ = camera.position.z
```

`_updateGramMotion()`新增分支（在现有latitude/longitude逻辑之后）：
```js
if (prim === 'breathe' && !_gramTransition && _gramSettledZ !== null) {
  const cfg = (_gramMotionPrimitives && _gramMotionPrimitives.breathe) || { amplitudePct: 0.025, periodSec: 30 }
  const breatheFactor = 1 + Math.sin((elapsed % cfg.periodSec) / cfg.periodSec * Math.PI * 2) * cfg.amplitudePct
  camera.position.z = _gramSettledZ * breatheFactor
  camera.updateProjectionMatrix()
}
```
**关键约束**：只在`!_gramTransition`（没有活跃过渡）时生效——过渡进行中呼吸暂停，过渡结束后呼吸接管，不要让两者同时争抢`camera.position.z`。

### 3. RollDrift原语

`MOTION_PRIMITIVES`加：
```js
rollDrift: { rangeDeg: 6, periodSec: 35 },
```

`_updateGramMotion()`里跟现有`latOffset`/`lonOffset`并列，新增：
```js
let rollOffset = 0
if (prim === 'rollDrift') {
  const cfg = (_gramMotionPrimitives && _gramMotionPrimitives.rollDrift) || { rangeDeg: 6, periodSec: 35 }
  rollOffset = Math.sin((elapsed % cfg.periodSec) / cfg.periodSec * Math.PI * 2) * (cfg.rangeDeg / 2)
}
window.__rodioVisualState._gramRollOffset = rollOffset
```

`getTargetOrientation()`现有：
```js
const gramRollDeg = _gramMotion.enabled ? (vs._gramRollDeg || 0) : 0
if (gramRollDeg !== 0) {
  targetNorth.applyAxisAngle(targetNormal, gramRollDeg * Math.PI / 180)
}
```
改成叠加offset（基准值+摆动量）：
```js
const gramRollDeg = _gramMotion.enabled ? (vs._gramRollDeg || 0) : 0
const gramRollOffset = _gramMotion.enabled ? (vs._gramRollOffset || 0) : 0
const totalRollDeg = gramRollDeg + gramRollOffset
if (totalRollDeg !== 0) {
  targetNorth.applyAxisAngle(targetNormal, totalRollDeg * Math.PI / 180)
}
```
这样`polarDiagonal`(基准10°)+`rollDrift`原语 = 以10°为中心±3°摆动；其余构图基准0，单独摆动±3°。

### 4. 白名单/调试面板

`setGramPrimitive(key)`的`valid`数组、debug面板下拉(`index.html:5301`附近)都要加`'breathe'`/`'rollDrift'`；`gramCompositions`数组加`'deepSpace'`。

## 严格边界

**只允许改动**：`CAMERA_COMPOSITIONS`加`deepSpace`、`MOTION_PRIMITIVES`加`breathe`/`rollDrift`、新增`_gramSettledZ`、`_updateGramTransition()`收尾处记录`_gramSettledZ`、`_updateGramMotion()`加两个分支、`getTargetOrientation()`叠加`gramRollOffset`那几行、`setGramPrimitive`白名单、debug面板。

**禁止改动**：`computeCameraOffsetZForComposition()`、`transitionToComposition()`已有逻辑（除非是给`deepSpace`走通已有分支，不需要改这个函数本身）、`quaternionFromBasis()`、既有9个构图的数值、既有4种运动原语的现有逻辑、三个既有候选(`level1motion`/`precomputeschedule`/`eastAsiaHeroV1`)。

## 这一轮不做

`Orbital Arc`/`Flyby`/`Approach`/`Retreat`/`Spiral`/`Target Shift`/`Terminator Track`、`breathing`/`crescendo`/`dissolve`曲线、日常模式/评分引擎/歌曲联动。

## 完成后请提供

1. git diff
2. `deepSpace`截图
3. `breathe`原语启用后，间隔几秒各截一张图，或直接贴出`camera.position.z`随时间变化的数值记录，证明确实在周期性呼吸
4. `rollDrift`在`homeGlobe`（基准0）和`polarDiagonal`（基准10°）下的`_gramRollDeg`+`_gramRollOffset`数值记录，证明是"基准+摆动"而不是从0重新摆动
5. 确认breathe在过渡进行中不生效（截图或数值记录：触发切换的瞬间到过渡完成前，`camera.position.z`不应该有呼吸的正弦扰动，只应该是过渡本身的插值）

## 验证方式

1. 切到`deepSpace`，确认地球变成远处小点，星空为主体
2. 选`breathe`，静置观察30秒左右，确认相机距离有肉眼可见的周期性远近变化
3. 选`rollDrift`，`homeGlobe`下观察缓慢往返倾斜；`polarDiagonal`下确认倾斜以10°为中心摆动
4. 确认默认播放、三个既有候选、A/B/C轮全部构图/原语不受影响，控制台无新增报错
