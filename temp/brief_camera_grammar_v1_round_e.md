# RodiO 动态地球镜头系统 E轮:Orbital Arc + Target Shift 两个新运动原语

本轮阶段：生成候选 + 接入候选（延续A/B/C/D轮做法，一轮内完成）
本轮目标：见下文
允许修改文件：`pwa/earth3d.js`、`pwa/index.html`（仅 "Camera Grammar V1 (debug)" 面板部分）
禁止修改文件：其余所有文件
允许生成资源：否
允许 commit：否，除非我后续明确批准
本轮不处理事项：见"这一轮不做"
回滚方案：全部改动在 `?earthCandidate=cameraGrammarV1` gate 后面，出问题直接 revert 这几处 diff

---

## 背景 & D轮的教训(务必先读)

D轮 `breathe` 原语第一次实现时，在 `_updateGramMotion()`（声明在 `createEarth3D()` **外面**，`earth3d.js:205`）里直接写了 `camera.position.z = ...`——但 `camera`（`earth3d.js:632`）声明在 `createEarth3D()`（`earth3d.js:505`）**里面**，`_updateGramMotion()` 访问不到它，导致每次执行到那行都抛 `ReferenceError`。`renderer.setAnimationLoop()` 的回调一旦抛出未捕获异常，**后续所有帧都不再被排定，整个渲染循环彻底冻结**，不只是原语失效。修复方式是让 `_updateGramMotion()` 只算数值、写进 `window.__rodioVisualState`，真正碰 `camera` 的代码挪到渲染循环里（`camera` 在那里真正可访问）。

**这轮的两个原语必须从一开始就遵守这个规则，没有例外**：任何涉及移动 `camera` 的代码，只能出现在渲染循环内部（`earth3d.js:6464`附近，`renderer.setAnimationLoop(() => {...})` 回调体里），不能出现在 `_updateGramMotion()` 里。写完之后请自己先搜一遍 `_updateGramMotion()` 函数体内有没有出现 `camera.` 这个词，有就是错的。

## 现状(已核实最新行号)

- `_updateGramMotion()`(`earth3d.js:205`)——外层作用域，只能写 `window.__rodioVisualState`，不能碰 `camera`
- `_getVisualTargetNdc()`(`earth3d.js:2806`)——声明在 `createEarth3D()` **里面**（`2806 > 505`），可以直接读 `_gramMotion.enabled`（外层变量，内层函数读外层永远没问题，跟 `_updateGramMotion()` 那次反过来的情况不一样）
- `_getVisualTargetNdc()` 只在 `updateVisualTargetDir()` 内部被调用，而 `updateVisualTargetDir()` 只在几个一次性时刻被调用（开机、构图切换完成等，`earth3d.js:6232`/`6247`/`6420`/`7123`），**不是每帧自动生效**——Target Shift 要持续摆动，必须每帧主动调用 `updateVisualTargetDir()`
- `_gramSettledZ`/`_gramSettledZRef`（D轮桥接，`earth3d.js:6422`/`6424`附近）、`_gramLastLookAtY`（C轮加的，`earth3d.js:6359`）——Orbital Arc复用这两个，不要新发明
- `transitionToComposition()`/`_updateGramTransition()`(`earth3d.js:6401`附近) 目前只插值 `camera.position.y/z`+`fov`+`lookAtY`，从未碰过 `camera.position.x`（一直假设X=0）——Orbital Arc会让X非零，必须给过渡引擎补上X轴插值，否则离开Orbital Arc后X会卡住不归零

## 要做的事

### 1. Target Shift原语

`MOTION_PRIMITIVES`加：
```js
targetShift: { rangeNdc: 0.15, periodSec: 25 },
```

`_updateGramMotion()`里（D轮已有分支之后）：
```js
let ndcOffsetX = 0
if (prim === 'targetShift') {
  const cfg = (_gramMotionPrimitives && _gramMotionPrimitives.targetShift) || { rangeNdc: 0.15, periodSec: 25 }
  ndcOffsetX = Math.sin((elapsed % cfg.periodSec) / cfg.periodSec * Math.PI * 2) * cfg.rangeNdc
}
window.__rodioVisualState._gramNdcOffsetX = ndcOffsetX
```
只做水平摆动，不叠加垂直分量。

`_getVisualTargetNdc()`(`earth3d.js:2806`)叠加offset：
```js
function _getVisualTargetNdc() {
  const vs = window.__rodioVisualState || {}
  const gramNdcOffsetX = _gramMotion.enabled ? (vs._gramNdcOffsetX || 0) : 0
  return new THREE.Vector2(
    (Number.isFinite(vs._targetNdcX) ? vs._targetNdcX : 0.25) + gramNdcOffsetX,
    Number.isFinite(vs._targetNdcY) ? vs._targetNdcY : -0.24
  )
}
```

渲染循环里（`_updateGramMotion()`调用之后）补一行：
```js
if (_gramActivePrimitive === 'targetShift' && _gramMotion.enabled) {
  updateVisualTargetDir()
}
```
**这一步不能漏**——只改数值不重新调用这个函数，画面不会有任何变化。

### 2. Orbital Arc原语

`MOTION_PRIMITIVES`加：
```js
orbitalArc: { rangeDeg: 30, periodSec: 12 },
```

`_updateGramMotion()`（只算角度，绝对不碰camera）：
```js
if (prim === 'orbitalArc' && !_gramTransitionRef && _gramSettledZRef !== null) {
  const cfg = (_gramMotionPrimitives && _gramMotionPrimitives.orbitalArc) || { rangeDeg: 30, periodSec: 12 }
  const thetaDeg = Math.sin((elapsed % cfg.periodSec) / cfg.periodSec * Math.PI * 2) * (cfg.rangeDeg / 2)
  window.__rodioVisualState._gramOrbitalArcDeg = thetaDeg
} else {
  window.__rodioVisualState._gramOrbitalArcDeg = undefined
}
```

渲染循环里（`camera`真正在作用域内的地方，紧邻D轮breathe的Z写入那几行）：
```js
if (Number.isFinite(window.__rodioVisualState?._gramOrbitalArcDeg) && _gramSettledZ !== null) {
  const thetaRad = window.__rodioVisualState._gramOrbitalArcDeg * Math.PI / 180
  camera.position.x = _gramSettledZ * Math.sin(thetaRad)
  camera.position.z = _gramSettledZ * Math.cos(thetaRad)
  camera.lookAt(0, _gramLastLookAtY, 0)
  camera.updateProjectionMatrix()
}
```
绕Y轴转，保持跟原点距离不变，复用已有的`_gramLastLookAtY`保持相机看向地球。

### 3. 过渡引擎补X轴插值

`_gramTransition` 加 `fromX: camera.position.x, toX: 0`（所有构图目标X永远是0，只有Orbital Arc期间X才非零）。`_updateGramTransition()` 每帧加：
```js
camera.position.x = _gramTransition.fromX + (_gramTransition.toX - _gramTransition.fromX) * e
```
这样任何一次`transitionToComposition()`调用都会把X平滑带回0，不管当前X是不是被Orbital Arc带偏了。

### 4. 白名单/调试面板

`setGramPrimitive`的`valid`数组、debug面板下拉都加`'targetShift'`/`'orbitalArc'`。

## 严格边界

**只允许改动**：`MOTION_PRIMITIVES`加两个条目、`_updateGramMotion()`加两个分支（只写`window.__rodioVisualState`，不碰camera）、`_getVisualTargetNdc()`叠加offset、`transitionToComposition()`/`_updateGramTransition()`加X轴插值、渲染循环里加`updateVisualTargetDir()`调用和相机X/Z/lookAt写入、`setGramPrimitive`白名单、debug面板。

**禁止改动**：`computeCameraOffsetZForComposition()`、既有10个构图数值、既有6种运动原语现有逻辑、三个既有候选(`level1motion`/`precomputeschedule`/`eastAsiaHeroV1`)。**`_updateGramMotion()`函数体内不允许出现`camera.`**——写完请自己grep检查一遍。

## 这一轮不做

`Flyby`/`Approach`/`Retreat`/`Spiral`/`Terminator Track`、日常模式/评分引擎/歌曲联动。

## 完成后请提供

1. git diff
2. 自查结果：`_updateGramMotion()`函数体内grep `camera.` 的结果（应该为空）
3. `targetShift`/`orbitalArc`各自持续观察20秒以上的截图或数值记录，证明动画没有中途冻结
4. 离开`orbitalArc`切换到其他构图后，`camera.position.x`确认平滑回到0的数值记录
5. 确认默认播放、三个既有候选、A/B/C/D轮全部构图/原语不受影响

## 验证方式

1. 选`targetShift`，观察构图中心左右缓慢移动，地球大小/朝向不变
2. 选`orbitalArc`，观察相机本身左右摆动（不是地球在转），地球全程在画面内，距离感基本不变
3. **重点**：`orbitalArc`摆动一段时间后切到`homeGlobe`，确认过渡完成后画面正常、无残留水平偏移
4. 持续观察至少20秒确认无冻结，控制台无新增报错、无调试脚手架残留
5. 确认A/B/C/D轮已验证内容不受影响
