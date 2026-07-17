# 重建远景构图的atmosphere2整圈辉光(Fresnel机制,替代/补充rimGlow)

本轮阶段:重新搭建(上一版远景相关代码已被删除，这次是重建，不是修补)
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件,尤其不要碰`_atmVert`/`_atmFrag`shader本身、`_emRimOverlayMat`相关的rimGlow代码(那套保留不动，跟这次是两套互补的系统)
允许 commit:否,除非我后续明确批准

---

## 背景

排查确认：`rimGlow`(`_emRimOverlayMat`)这套系统的shader公式(`earth3d.js:2473`附近`arcY = uRimCenter.y + uRimRadius.y * sqrt(...)`，`sqrt`前恒定是`+`号)，**从几何设计上就只能在地球上半部分产生辉光**，不管强度参数怎么调，下半部分和两侧永远不会亮。这不是这次要修的东西——rimGlow保留现状(它提供的"上方辉光弧线+定向太阳高光"效果本身是好的，不动)。

真正能做到"整圈都发光"的是`atmosphereMaterial`/`atmosphere2Material`这套基于Fresnel公式(`1-|法线·视线|`)的3D网格——这套在球体轮廓任何角度都对称成立，天生就能整圈发光。之前几轮为此搭建过一套"远景专属大气层"机制，但诊断后发现farOrbit下实际数值没有生效，后来在转向rimGlow方案时**这套代码被整体删除了**。现在决定重新搭建它，作为rimGlow的补充(不是替代)：rimGlow负责上方的强化辉光弧线+方向性太阳高光，`atmosphere2`负责整圈的柔和基础辉光。

## 现状(已核实，当前代码库实际情况)

- `atmosphere2.frustumCulled = false`、`atmosphere2.renderOrder = 1`(`earth3d.js:2186-2188`)已经修复并保留，这次不用重复处理
- `applyTheme()`(`earth3d.js:5648-5659`)仍然保留theme驱动的`atmosphere`/`atmosphere2`可见性和uniform赋值逻辑(白天主题`atmosphere.visible`由`opacity>0.0001`决定；`atmosphere2`只有主题定义了`config.atmosphere2`才显示，白天主题目前都没定义，所以默认`atmosphere2.visible=false`)
- 诊断API已经保留并可用：`window.earth3d.getGramDebug()`(含`atm2Visible/atm2Opacity/atm2Power/atm2PowerOuter/atm2StrengthOuter/atm2SunInfluence`等字段)、`window.earth3d.setAtmosphereLayerVisible(layerName, visible)`、`window.earth3d.getAtmosphereLayerState(layerName)`——这次直接复用，不需要重新加
- `FAR_COMPOSITIONS`(`earth3d.js`，包含`farOrbit`/`oceanExpanse`/`deepSpace`/`polarDiagonal`/`cityAnchor`/`portraitMarble`/`terminatorPortrait`)、`isFarComposition`判断变量仍然保留，直接复用
- `transitionToComposition()`/`_updateGramTransition()`里，之前的`FAR_VIEW_ATMOSPHERE`/`atmosphere2`相关的可见性切换和插值代码**已经被完全删除**，需要重新加

## 要做的事

### 1. 新增`FAR_VIEW_ATMOSPHERE`常量(数值沿用之前验证过的)

```js
const FAR_VIEW_ATMOSPHERE = { opacity: 0.30, sunInfluence: 0.08, power: 3.5, powerOuter: 2.2, strengthOuter: 0.22 }
```
（`sunInfluence`定为`0.08`，比之前试过的`0.05`稍微保留一点点方向性，具体数值你视觉测试后可以在`0.05~0.15`之间微调，但**不能省略这个字段或者用默认的`0.85`**，这是能否整圈发光的关键）

### 2. `transitionToComposition()`里，远景构图时切换`atmosphere`/`atmosphere2`可见性

在已有的`isFarComposition`判断之后，新增：
```js
if (isFarComposition) {
  atmosphere.visible = false
  atmosphere2.visible = true
  atmosphere2Material.uniforms.uColor.value.set('#f7feff')
  atmosphere2Material.uniforms.uColorOuter.value.set('#9fd7ff')
  atmosphere2Material.uniforms.uRadius.value = 2.04
} else {
  atmosphere2.visible = false
  atmosphere.visible = (themeCfg.atmosphere?.opacity ?? 0) > 0.0001
}
```
（这次统一用`isFarComposition`判断，不需要像之前那样区分白天/夜间主题——`atmosphere2`本身在夜间主题下如果`config.atmosphere2`有定义，会被这里的`else`分支覆盖，但夜间主题不在`FAR_COMPOSITIONS`触发路径里通常也不会造成冲突；**如果测试中发现夜间主题+远景构图组合出现异常，请截图告诉我，不要自己决定怎么处理**）

### 3. 目标值计算 + `_gramTransition`插值(照抄之前验证过、后来被删除的写法)

```js
const toAtm2Opacity = isFarComposition ? FAR_VIEW_ATMOSPHERE.opacity : (themeCfg.atmosphere2?.opacity ?? 0)
const toAtm2SunInfluence = isFarComposition ? FAR_VIEW_ATMOSPHERE.sunInfluence : 0.85
const toAtm2Power = isFarComposition ? FAR_VIEW_ATMOSPHERE.power : (themeCfg.atmosphere2?.power ?? 5.0)
const toAtm2PowerOuter = isFarComposition ? FAR_VIEW_ATMOSPHERE.powerOuter : (themeCfg.atmosphere2?.powerOuter ?? 3.2)
const toAtm2StrengthOuter = isFarComposition ? FAR_VIEW_ATMOSPHERE.strengthOuter : (themeCfg.atmosphere2?.strengthOuter ?? 0.0)
```
`_gramTransition`对象里新增(`atm2`前缀)：
```js
fromAtm2Opacity: atmosphere2Material.uniforms.uOpacity.value,
toAtm2Opacity,
fromAtm2SunInfluence: atmosphere2Material.uniforms.uSunInfluence.value,
toAtm2SunInfluence,
fromAtm2Power: atmosphere2Material.uniforms.uPower.value,
toAtm2Power,
fromAtm2PowerOuter: atmosphere2Material.uniforms.uPowerOuter.value,
toAtm2PowerOuter,
fromAtm2StrengthOuter: atmosphere2Material.uniforms.uStrengthOuter.value,
toAtm2StrengthOuter,
```
`_updateGramTransition()`里新增插值：
```js
atmosphere2Material.uniforms.uOpacity.value = _gramTransition.fromAtm2Opacity + (_gramTransition.toAtm2Opacity - _gramTransition.fromAtm2Opacity) * e
atmosphere2Material.uniforms.uSunInfluence.value = _gramTransition.fromAtm2SunInfluence + (_gramTransition.toAtm2SunInfluence - _gramTransition.fromAtm2SunInfluence) * e
atmosphere2Material.uniforms.uPower.value = _gramTransition.fromAtm2Power + (_gramTransition.toAtm2Power - _gramTransition.fromAtm2Power) * e
atmosphere2Material.uniforms.uPowerOuter.value = _gramTransition.fromAtm2PowerOuter + (_gramTransition.toAtm2PowerOuter - _gramTransition.fromAtm2PowerOuter) * e
atmosphere2Material.uniforms.uStrengthOuter.value = _gramTransition.fromAtm2StrengthOuter + (_gramTransition.toAtm2StrengthOuter - _gramTransition.fromAtm2StrengthOuter) * e
```

## 严格的验证流程(这次务必按这个顺序，不要提前下结论)

**关键教训**：上一次诊断时`transitionRef`可能还没结束就去读数值，导致误判"没生效"。这次请严格按顺序：

1. 硬刷新页面，`?earthCandidate=cameraGrammarV1`，noon主题
2. 触发 `window.earth3d.transitionToComposition('farOrbit', { duration: 3 })`
3. **先执行 `window.earth3d.getGramDebug().transitionRef`，必须确认返回`null`(过渡已完全结束)才能继续下一步**——如果还是`'active'`，等1-2秒再检查一次，直到确认是`null`
4. 确认过渡结束后，再执行 `window.earth3d.getAtmosphereLayerState('atmosphere2')`，核对`opacity`≈0.30、`sunInfluence`≈0.08、`power`≈3.5、`visible`应该是`true`
5. 数值确认无误后，截图看视觉效果——用`window.earth3d.setAtmosphereLayerVisible('atmosphere', false)`把第一层也隐藏，只看`atmosphere2`单独的辉光形状，确认是否贴合球体整圈轮廓(不只是顶部)
6. 记得测完把`atmosphere`的可见性恢复(`setAtmosphereLayerVisible('atmosphere', true)`)

## 完成后请提供

1. git diff
2. 严格按上面验证流程走一遍的完整记录(每一步的实际返回值，不要跳步)
3. `farOrbit`确认整圈辉光后，截图对比：只有`atmosphere2`(隐藏`atmosphere`)时的形状 + 正常状态(两层都在，rimGlow+atmosphere2叠加)的最终视觉效果
4. 从`farOrbit`切回`homeGlobe`，确认`atmosphere2.visible`正确变回`false`，`atmosphere`正常恢复
5. 夜间主题(比如`deepNight`)+ `farOrbit`组合测一下，确认没有异常
6. 控制台无新增报错

## 验证方式

1. 按严格验证流程确认数值真正生效(不是过渡未完成时的误读)
2. `atmosphere2`单独隔离查看时，辉光形状贴合球体整圈轮廓
3. 叠加rimGlow后，整体效果是"整圈柔和辉光打底 + 顶部方向性太阳高光增强"，两者协调不冲突
4. 近景、夜间主题不受影响
5. 控制台无新增报错
