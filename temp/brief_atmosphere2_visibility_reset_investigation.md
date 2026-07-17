# 排查:atmosphere2的uniform数值正确但visible被重置为false

本轮阶段:排查定位(先查是什么代码把visible改回false的,不要猜测性修复)
允许修改文件:仅 `pwa/earth3d.js`(诊断用临时代码)
禁止修改文件:其余所有文件
允许 commit:否

---

## 背景

严格按上一版brief的验证流程测试：`?earthCandidate=cameraGrammarV1`，noon主题，触发`farOrbit`，等到`getGramDebug().transitionRef`确认变成`null`后，执行`getAtmosphereLayerState('atmosphere2')`，结果：
```json
{"visible":false,"uOpacity":0.3,"uPower":3.5,"uPowerOuter":2.2,"uStrengthOuter":0.22,"uSunInfluence":0.08,"uRadius":2.04}
```
`getAtmosphereLayerState('atmosphere')`：
```json
{"visible":false,"uOpacity":0,"uPower":14,"uPowerOuter":5.2,"uStrengthOuter":0.18,"uSunInfluence":0.85}
```

**uniform数值是对的**(跟`FAR_VIEW_ATMOSPHERE`完全匹配)，但**`atmosphere`和`atmosphere2`的`visible`都是`false`**——两层大气全部不可见。`transitionToComposition()`里`isFarComposition`为真时应该同步执行`atmosphere2.visible = true`（不是走插值，是直接赋值），照理说函数调用完成的那一刻就应该是`true`，但过几秒后再检查又变成了`false`。

## 请排查(不要直接猜测性修复，先定位)

### 1. 检查是否有其他代码路径在之后把visible又改回去了

搜索代码里所有对`atmosphere.visible`/`atmosphere2.visible`赋值的地方(不只是这次新加的那处)，特别注意：
- `applyTheme()`(`earth3d.js:5648`附近)里`atmosphere.visible = (config.atmosphere.opacity ?? 0) > 0.0001`和`atmosphere2.visible = true/false`这两处赋值——是否在`transitionToComposition()`调用之后，又被某个周期性触发的`applyTheme()`重新执行覆盖了？（比如主题根据真实时钟小时数自动重新apply的逻辑，即使主题key没变，只要重新调用了`applyTheme()`，就会按噪音主题`config.atmosphere2`未定义这条走`else`分支，把`atmosphere2.visible`重置为`false`；同时`atmosphere.visible`那行如果读到的`config`不是当前实际opacity，也可能被误设为`false`）
- 是否有别的地方调用了类似`_hideAtmo()`这种统一隐藏大气层的函数？

### 2. 加临时console.log定位调用时序

在`atmosphere.visible = xxx`和`atmosphere2.visible = xxx`这几处赋值语句旁边，临时加：
```js
console.log('[debug] atmosphere.visible set to', atmosphere.visible, new Error().stack.split('\n')[2])
console.log('[debug] atmosphere2.visible set to', atmosphere2.visible, new Error().stack.split('\n')[2])
```
（用`new Error().stack`打印调用栈的第二行，能看出是哪个函数调用链设置的这个值）

重新走一遍验证流程(触发farOrbit，等待几秒)，把控制台完整日志贴给我，看visible到底被设置了几次、每次是什么值、从哪个函数调用过来的。

### 3. 检查代码里`case 'atmosphereOnly'`等调试模式相关的逻辑

确认当前测试过程中没有意外触发任何调试隔离模式(`setDebugLayer`那几个case分支)，如果不小心处于某个调试状态，也会导致两层都被强制隐藏。

## 请提供

1. 完整的console.log调用栈记录(哪些代码路径设置了`visible`，按时间顺序)
2. 你的根因判断
3. **不要在这一步直接修复，先把排查结果发给我确认根因，我们再定修复方案**
