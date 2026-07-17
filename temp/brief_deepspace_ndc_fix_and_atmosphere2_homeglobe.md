# 两个修复:①deepSpace锚点残留bug(多轮前诊断过没修) ②atmosphere2整圈辉光扩大到homeGlobe

本轮阶段:两个明确的修复,都已经定位清楚，直接实施
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件
允许 commit:否,除非我后续明确批准

---

## 修复1:deepSpace构图辉光跟地球位置脱节(锚点残留bug)

### 背景

之前诊断过(见更早的排查记录)：`CAMERA_COMPOSITIONS.deepSpace`(`earth3d.js:6406-6410`)没有定义`anchorNdcX`/`anchorNdcY`。`transitionToComposition()`里：
```js
const targetNdcX = compositionKey === 'homeGlobe' ? undefined : comp.anchorNdcX
const targetNdcY = compositionKey === 'homeGlobe' ? undefined : comp.anchorNdcY
```
`comp.anchorNdcX`/`comp.anchorNdcY`对`deepSpace`来说是`undefined`。而`_updateGramTransition()`收尾块里：
```js
if (_gramTransition.toNdcX !== undefined) vs._targetNdcX = _gramTransition.toNdcX
if (_gramTransition.toNdcY !== undefined) vs._targetNdcY = _gramTransition.toNdcY
```
值是`undefined`时这两行被跳过，**`vs._targetNdcX`/`vs._targetNdcY`会保留上一个构图残留的值，不会重置**。这就是为什么切到`deepSpace`后，画面里的辉光/视觉锚点经常跟那颗缩得很小的地球完全脱节——锚点其实还停留在上一个构图(比如`cityAnchor`的偏移量)的位置上。

这次实测用户截图确认了这个bug依然存在，之前只诊断没有修复。

### 要做的事

把`targetNdcX`/`targetNdcY`的计算，从"没定义就是undefined(不重置)"改成"没定义就明确给0(居中，重置)"：
```js
const targetNdcX = compositionKey === 'homeGlobe' ? undefined : (comp.anchorNdcX ?? 0)
const targetNdcY = compositionKey === 'homeGlobe' ? undefined : (comp.anchorNdcY ?? 0)
```
（`homeGlobe`保持原样传`undefined`不变，这是它自己特殊的逻辑，不要动；其余所有构图，只要没有显式定义`anchorNdcX`/`anchorNdcY`，都会明确重置为屏幕居中，不再继承上一个构图的残留值）

**请顺便检查一下**：除了`deepSpace`，`CAMERA_COMPOSITIONS`里还有没有别的构图同样没定义`anchorNdcX`/`anchorNdcY`（比如`homeGlobe`本身除外），确认这次改动能覆盖所有类似情况，不是只修deepSpace这一个。

## 修复2:atmosphere2整圈辉光扩大到homeGlobe

### 背景

`atmosphere2`的整圈辉光(`FAR_VIEW_ATMOSPHERE`那套)目前只在`isFarComposition`为真时生效(`FAR_COMPOSITIONS`包含`farOrbit`/`oceanExpanse`/`deepSpace`/`polarDiagonal`/`cityAnchor`/`portraitMarble`/`terminatorPortrait`)，不包含`homeGlobe`——用户平时看到的默认首页视角就是`homeGlobe`，一直没有整圈辉光效果，只有之前扩大过的rimGlow outer/inner(那套本身有方向性限制，独木难支)。

### 要做的事

新增一个判断变量(参照`RIM_BOOST_COMPOSITIONS`的写法)：
```js
const APPLY_ATM2_COMPOSITIONS = new Set([...FAR_COMPOSITIONS, 'homeGlobe'])
```
把`transitionToComposition()`里目前用`isFarComposition`控制`atmosphere2`可见性切换和目标值计算的地方（`atmosphere.visible=false / atmosphere2.visible=true`那个if/else块，以及`toAtm2Opacity`等目标值计算），改成用这个新变量：
```js
const applyAtm2 = APPLY_ATM2_COMPOSITIONS.has(compositionKey)
// 原本用 isFarComposition 判断 atmosphere/atmosphere2 可见性切换的地方，改用 applyAtm2
// 原本用 isFarComposition 计算 toAtm2Opacity/toAtm2SunInfluence/toAtm2Power/toAtm2PowerOuter/toAtm2StrengthOuter 的地方，也改用 applyAtm2
```

**注意**：`isFarComposition`这个变量本身**不要删**，它还被`toSunLobeStrength`(rimGlow压制sunLobe那部分)和镜头经度跟随太阳(`resolvedLon`那段)用着，这两处**继续用`isFarComposition`不变**，只有`atmosphere2`相关的这几处换成新的`applyAtm2`。

（这样homeGlobe会有atmosphere2整圈辉光 + rimGlow的outer/inner增强，但不会触发sunLobe压制和"镜头经度跟随太阳"这套远景专属逻辑，因为homeGlobe本来就不需要这些）

## 完成后请提供

1. git diff
2. `deepSpace`修复验证：先切到`cityAnchor`(有偏移锚点)，再切到`deepSpace`，截图确认辉光/画面锚点这次能正确居中，不再跟着`cityAnchor`的偏移量走
3. `homeGlobe`默认视角截图(noon/evening各一张)，确认整圈辉光已经生效，不再是"只有顶部"
4. `farOrbit`等原有远景构图截图，确认不受这次改动影响(效果跟之前一致)
5. 控制台无新增报错

## 验证方式

1. `deepSpace`辉光/锚点不再受其他构图残留状态影响，正确居中
2. `homeGlobe`默认视角有整圈辉光效果
3. 远景构图行为不受影响，`isFarComposition`相关的sunLobe压制/镜头经度逻辑保持不变
4. 控制台无新增报错
