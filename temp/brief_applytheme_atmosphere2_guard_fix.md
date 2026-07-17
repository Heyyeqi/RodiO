# 修复:applyTheme()重新触发时,不知道当前处于远景构图状态,错误重置atmosphere2/atmosphere可见性

本轮阶段:正式修复(根因已确认,不需要再排查)
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件
允许 commit:否,除非我后续明确批准

---

## 背景(根因已确认)

`applyTheme()`(`earth3d.js:5617`)每次被调用(不管因为什么触发，包括你诊断出来的night texture异步加载完成后的回调`applyTheme(themeKey, {force:true})`)，都会无条件按`config.atmosphere2`是否存在来设置`atmosphere2.visible`，以及按`config.atmosphere.opacity`设置`atmosphere.visible`——完全不知道"当前是不是正停留在远景构图状态"。这导致`transitionToComposition('farOrbit', ...)`刚设置好`atmosphere2.visible=true`，之后`applyTheme()`被异步重新触发一次，就把它冲刷回`false`。

## 要做的事

### 1. 新增一个记录"当前构图"的模块级变量

在`FAR_COMPOSITIONS`常量附近新增：
```js
let _currentCompositionKey = 'homeGlobe'
```

### 2. `transitionToComposition()`开头记录当前构图

在`transitionToComposition(compositionKey, opts = {}, _isSequenceStep = false) {`函数体的**第一行**，新增：
```js
_currentCompositionKey = compositionKey
```
（这一行要放在函数最前面，确保不管函数后面因为什么原因提前return，这个记录都已经更新了）

### 3. `applyTheme()`里，设置atmosphere/atmosphere2可见性之前，先判断当前是否处于远景构图状态

把`earth3d.js:5648`这一行：
```js
atmosphere.visible = (config.atmosphere.opacity ?? 0) > 0.0001
```
改成：
```js
const isInFarComposition = FAR_COMPOSITIONS.has(_currentCompositionKey)
if (!isInFarComposition) {
  atmosphere.visible = (config.atmosphere.opacity ?? 0) > 0.0001
}
// isInFarComposition为true时，atmosphere.visible保持远景逻辑设置的false，这里不碰
```

`atmosphere2`那部分(`earth3d.js:5651`附近`if (atmosphere2 && atmosphere2Material) {...}`整个块)，同样加guard：
```js
if (atmosphere2 && atmosphere2Material && !isInFarComposition) {
  if (config.atmosphere2) {
    // ...现有逻辑不变...
    atmosphere2.visible = true
  } else {
    atmosphere2.visible = false
  }
}
// isInFarComposition为true时，跳过整个atmosphere2的theme配置逻辑，保持远景逻辑设置的uniform和visible=true
```

**记得删除排查阶段加的临时诊断代码**(`earth3d.js:5649`那行`console.log('[debug] applyTheme atmosphere.visible set to'...)`，以及之前为了这次排查加的其他`console.log`调用栈打印代码，正式修复不需要保留这些调试输出)。

## 严格边界

**只允许改动**：新增`_currentCompositionKey`变量；`transitionToComposition()`开头新增一行记录；`applyTheme()`里给`atmosphere.visible`赋值和`atmosphere2`整个逻辑块加`isInFarComposition`判断guard；删除排查阶段加的临时`console.log`调试代码。

**禁止改动**：`applyTheme()`其余逻辑(纹理/材质/rimGlow等其他部分不受这次改动影响)；`transitionToComposition()`/`_updateGramTransition()`已有的插值逻辑本身；`FAR_COMPOSITIONS`常量本身。

## 完成后请提供

1. git diff(确认临时诊断代码已清理干净)
2. 按上一版的严格验证流程重新走一遍：`farOrbit`触发→等`getGramDebug().transitionRef`变成`null`→检查`getAtmosphereLayerState('atmosphere2')`，这次`visible`应该稳定保持`true`，不会再被异步的`applyTheme()`重置
3. 等待10秒以上(确保任何异步纹理加载回调都有机会触发)，再次检查`atmosphere2`的`visible`，确认依然是`true`(没有被延迟触发的`applyTheme()`重新冲掉)
4. 截图：`farOrbit`稳定后的整圈辉光效果
5. 从`farOrbit`切回`homeGlobe`，确认`atmosphere`/`atmosphere2`可见性恢复正常
6. 切换主题(比如从noon切到afternoon)测试，确认正常主题切换流程不受这次guard逻辑影响
7. 控制台无新增报错

## 验证方式

1. `atmosphere2.visible`在far composition状态下能稳定保持`true`，不会被任何后续的`applyTheme()`调用重置
2. 整圈辉光效果视觉确认(不只是顶部)
3. 离开远景构图、正常主题切换均不受影响
4. 控制台无新增报错，无残留调试log
