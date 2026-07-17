# 打回:纬度漂移开关没做 + 配置对象没被实际读取

## 核实结论(先说好消息)

核心引擎部分(`CAMERA_COMPOSITIONS`/`computeCameraOffsetZForComposition()`/`transitionToComposition()`/`_updateGramTransition()`)已经独立验证正确:

- `earth.geometry.parameters.radius` 确认是 2,反推公式用的是真实值,不是猜的
- 实测切到 `farOrbit`,截图目测地球直径约占屏幕高度33%,跟配置的 `earthDiameterPct: 0.32` 几乎精确吻合
- 连续切换 `portraitMarble` → `farOrbit`,过渡是平滑渐变,不是瞬间跳变
- `earth3dApi.transitionToComposition` 走的是 `Object.assign` 正确导出方式,boot激活代码调用的是同一闭包作用域内的裸函数(不是像上次 `applyCameraPreset` 那样只存在于对象属性里),不会重蹈那次 boot-hang 的覆辙
- 现有四个候选(默认播放/`level1motion`/`precomputeschedule`/`eastAsiaHeroV1`)逐行比对,代码一字未改

只有两处跟 brief 要求不符,需要这次修:

## 问题1:纬度漂移开关完全没实现

brief 第5点明确要求:"一个开关：打开/关闭 `latitudeDrift`"。但现在 `_updateGramMotion()` 里没有任何开关判断,只要 `?earthCandidate=cameraGrammarV1` 一开,纬度漂移就无条件运行:

```js
function _updateGramMotion() {
  if (!_gramMotion.enabled) return
  if (_gramMotion.startTime === 0) _gramMotion.startTime = performance.now() / 1000
  const elapsed = (performance.now() / 1000) - _gramMotion.startTime
  const period = 40
  const range = 6
  const phase = (elapsed % period) / period
  const latOffset = Math.sin(phase * Math.PI * 2) * (range / 2)
  if (!window.__rodioVisualState) window.__rodioVisualState = {}
  window.__rodioVisualState._gramLatOffset = latOffset
}
```

我实测过:打开 `?earthCandidate=cameraGrammarV1`,`window.__rodioVisualState._gramLatOffset` 直接是非零值(0.14°左右),全程无法关闭。这样没法做"开/关对比"这个验收点(brief 验证方式第3条要求的)。

### 修复方式

加一个模块级变量 `_gramLatDriftEnabled`(默认 `true` 或 `false` 都可以,建议默认 `true` 保持现有观感,加开关只是为了能关掉验证),`_updateGramMotion()` 里判断这个变量:

```js
let _gramLatDriftEnabled = true

function _updateGramMotion() {
  if (!_gramMotion.enabled) return
  if (!_gramLatDriftEnabled) {
    if (!window.__rodioVisualState) window.__rodioVisualState = {}
    window.__rodioVisualState._gramLatOffset = 0
    return
  }
  // ...其余逻辑不变
}
```

再加一个 `earth3dApi` 方法(放进现有 `Object.assign(earth3dApi, {...})` 里,不要裸函数):

```js
setGramLatDrift(enabled) {
  _gramLatDriftEnabled = Boolean(enabled)
  return _gramLatDriftEnabled
},
```

`index.html` 的 "Camera Grammar V1 (debug)" 面板(`pwa/index.html:5301`附近)里加一个 checkbox/toggle,参照现有 dat.GUI 面板里其他 boolean 开关的写法(面板里应该已经有别的 `gui.add(obj, key)` 布尔类型的例子,照抄那个写法),绑定到 `e3d.setGramLatDrift(bool)`。

## 问题2:`MOTION_PRIMITIVES.latitudeDrift` 配置对象没被实际读取

`_updateGramMotion()` 里 `period`/`range` 是硬编码的本地常量,没有读 `MOTION_PRIMITIVES.latitudeDrift.periodSec`/`.rangeDeg`。现在数值凑巧对得上(40/6),但这个配置对象等于是摆设,以后想调参数不会真的生效。

### 修复方式

```js
function _updateGramMotion() {
  if (!_gramMotion.enabled) return
  if (!_gramLatDriftEnabled) { /* ...同上... */ return }
  if (_gramMotion.startTime === 0) _gramMotion.startTime = performance.now() / 1000
  const elapsed = (performance.now() / 1000) - _gramMotion.startTime
  const cfg = MOTION_PRIMITIVES.latitudeDrift
  const phase = (elapsed % cfg.periodSec) / cfg.periodSec
  const latOffset = Math.sin(phase * Math.PI * 2) * (cfg.rangeDeg / 2)
  // ...
}
```

## 严格边界

只改这两处(`_updateGramMotion()` 内部逻辑 + 新增 `_gramLatDriftEnabled`/`setGramLatDrift` + debug面板加一个开关)。不要碰其他任何已经验证过的部分(`computeCameraOffsetZForComposition`/`transitionToComposition`/`_updateGramTransition`/`CAMERA_COMPOSITIONS`/三个已有候选)。

## 验证方式

1. 加 `?earthCandidate=cameraGrammarV1`,确认 `window.__rodioVisualState._gramLatOffset` 默认非零(漂移在跑)
2. 通过 debug 面板关闭开关,确认 `_gramLatOffset` 变成0且不再变化,地球停止上下漂移
3. 重新打开开关,确认漂移恢复
4. 改一下 `MOTION_PRIMITIVES.latitudeDrift.periodSec`(比如改成20测试),确认漂移周期真的跟着变了,证明配置对象被实际读取,不是摆设
