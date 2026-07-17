# 修复:切换到没有定义sunLobe的主题时,sunLobe状态没有重置,导致残留污染

本轮阶段:先修复重置bug,再重新诊断(不要跳过这一步直接调参)
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件
允许 commit:否

---

## 背景(纠正上一轮诊断的误读)

上一轮报告里说的"noon的sunLobe参数(x:0.96, y:0.31, hStretch:2.4, strength:0.83...)",经过核实**这其实是`sunrise`主题的配置**(`earth3d.js:4073-4085`附近),不是noon的。我直接读了`noon`自己的`rimGlow`(`earth3d.js:4421-4432`)，**noon根本没有定义`sunLobe`这个子字段，只有`outer`/`inner`两层**。

## 真正的bug

`applyRimGlowThemeConfig()`(`earth3d.js:2704`)里：
```js
const sunLobe = rimGlowCfg?.sunLobe
// ...
if (sunLobe) {
  ro.uSunLobeEnabled.value = sunLobe.enabled ? 1.0 : 0.0
  // ...(其余sunLobe相关uniform赋值)
}
```
**当主题的`rimGlow`没有定义`sunLobe`时（比如noon），这整个`if`块被跳过，`uSunLobeEnabled`等一系列uniform完全不会被重置或关闭。** 也就是说，如果应用主题的顺序是"先应用了一个定义了sunLobe的主题（比如sunrise/sunset那种），再切换到noon这种没有sunLobe的主题"，noon会**继续沿用上一个主题残留的sunLobe状态**（包括它的x/y位置、strength强度、颜色等），而不是正确关闭。

**这很可能才是这几轮反复看到的"顶部/右上角强烈定向光斑"的真正来源**——不是noon自己设计上就有一个偏强的sunLobe，而是被别的主题的sunLobe残留污染了。之前的诊断（包括我上一轮的判断）都是在这个污染状态下观测的，不能作为"noon的rimGlow该怎么调"的可靠依据。

## 要做的事

### 1. 先修复重置bug

`applyRimGlowThemeConfig()`里，`sunLobe`不存在时，应该显式关闭sunLobe相关uniform，而不是什么都不做：
```js
if (sunLobe) {
  ro.uSunLobeEnabled.value     = sunLobe.enabled ? 1.0 : 0.0
  ro.uSunLobeX.value           = sunLobe.x           ?? 0.86
  // ...(现有逻辑不变)
} else {
  ro.uSunLobeEnabled.value = 0.0
  // arcBand/surfaceWarmth 同理，没有sunLobe时也应该一起关闭
  ro.uArcBandEnabled.value = 0.0
  if (rv.uSurfWarmthEnabled) rv.uSurfWarmthEnabled.value = 0.0
}
```
**只加`else`分支处理"关闭"这几个enable标记，不需要重置sunLobe的其他数值字段（x/y/color等），因为`enabled=0`时shader应该已经不会使用这些值——但请先确认一下shader里`uSunLobeEnabled`是否真的完整gate住了所有sunLobe视觉效果，如果gate不完整（比如某个视觉分支忘记检查这个enabled标记），需要额外告诉我，不要自己去改shader。**

### 2. 修复后，重新诊断noon在farOrbit下的真实rimGlow效果（不带任何残留污染）

1. 硬刷新页面（确保没有残留状态），直接从默认加载进入noon主题（不要先切换到其他主题再切回noon，避免引入新的残留路径干扰这次诊断）
2. `?earthCandidate=cameraGrammarV1`，触发`farOrbit`
3. 截图，看现在（sunLobe正确关闭后）rimGlow的`outer`/`inner`两层单独呈现出来是什么效果——大概率会很微弱（`coreStrength:0.35, haloStrength:0.16`这几个数值本来就不高），但这次看到的应该是真实的、没有被污染的noon自己的rimGlow效果

## 请提供

1. git diff
2. 修复前后的对比截图（修复前应该还能看到那个强光斑残留，修复后不应该有）
3. 修复后，noon在farOrbit下真实的rimGlow外观截图
4. 控制台无新增报错

## 暂不做

不需要在这轮里调`outer`/`inner`的强度或者新增sunLobe给noon——先把这个真实、干净的基线看清楚，我们再决定下一步往哪个方向调（这轮只修复重置bug + 提供干净的诊断结果）。
