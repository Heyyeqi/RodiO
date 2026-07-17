# 远景构图大气辉光 第三轮:加大力度 + 换falloff形状,让暗面辉光真正可见

本轮阶段:继续调优,加大数值力度(第二轮`opacity:0.22, sunInfluence:0.40`力度不够)
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件
允许 commit:否,除非我后续明确批准

---

## 背景

第二轮(`opacity:0.22, sunInfluence:0.40`)已上线,我核对过git diff跟brief完全一致,机制没有问题。但用户实测截图显示:辉光在球体顶部(朝阳侧)依然很亮,但往左右两侧移动时衰减得还是太快,到9点/3点钟方向基本看不太出来了,没有达到"整个可见轮廓都能感知到辉光"的效果。这不是"完全没生效",是"生效了但力度不够",这轮直接加大力度。

## 这一轮做什么

### 1. 大幅提高力度

把`FAR_VIEW_ATMOSPHERE`(`earth3d.js:6408`附近)改成:
```js
const FAR_VIEW_ATMOSPHERE = { opacity: 0.34, sunInfluence: 0.18, power: 3.5, powerOuter: 2.2, strengthOuter: 0.22 }
```
这次不只调`opacity`/`sunInfluence`,**新增`power`/`powerOuter`/`strengthOuter`也一起覆盖**——原因:`power`控制的是"辉光从轮廓边缘往内衰减的形状",数值越低,衰减范围越宽,越容易在整个可见轮廓上都"沾到光"。远景构图现在复用的`power`还是各主题近景调好的`6.0`(第二批第一轮定的),这个值对近景合适,但对"要让辉光覆盖整个球体轮廓"这个远景专属目标来说偏窄,这次一起放宽。

（这几个数值同样是估算起点，不是精确值——如果视觉判断后觉得还是不够或者过头了，请在这个范围内继续试：`opacity: 0.28~0.40`、`sunInfluence: 0.12~0.25`、`power: 3.0~4.5`、`powerOuter: 1.8~2.8`）

### 2. 应用方式(照抄现有機制,只是新增两个字段的传递)

`transitionToComposition()`里现有的:
```js
const toAtmosphereOpacity = applyFarViewTreatment ? FAR_VIEW_ATMOSPHERE.opacity : (themeCfg.atmosphere?.opacity ?? 0)
const toSunInfluence = applyFarViewTreatment ? FAR_VIEW_ATMOSPHERE.sunInfluence : 0.85
```
旁边新增:
```js
const toAtmospherePower = applyFarViewTreatment ? FAR_VIEW_ATMOSPHERE.power : (themeCfg.atmosphere?.power ?? 16.0)
const toAtmospherePowerOuter = applyFarViewTreatment ? FAR_VIEW_ATMOSPHERE.powerOuter : (themeCfg.atmosphere?.powerOuter ?? 3.2)
const toAtmosphereStrengthOuter = applyFarViewTreatment ? FAR_VIEW_ATMOSPHERE.strengthOuter : (themeCfg.atmosphere?.strengthOuter ?? 0.0)
```

`_gramTransition`对象里跟`fromAtmosphereOpacity/toAtmosphereOpacity`并列,新增：
```js
fromAtmospherePower: atmosphereMaterial.uniforms.uPower.value,
toAtmospherePower,
fromAtmospherePowerOuter: atmosphereMaterial.uniforms.uPowerOuter.value,
toAtmospherePowerOuter,
fromAtmosphereStrengthOuter: atmosphereMaterial.uniforms.uStrengthOuter.value,
toAtmosphereStrengthOuter,
```

`_updateGramTransition()`里跟`atmosphereMaterial.uniforms.uOpacity.value = ...`并列，新增三行插值：
```js
atmosphereMaterial.uniforms.uPower.value = _gramTransition.fromAtmospherePower + (_gramTransition.toAtmospherePower - _gramTransition.fromAtmospherePower) * e
atmosphereMaterial.uniforms.uPowerOuter.value = _gramTransition.fromAtmospherePowerOuter + (_gramTransition.toAtmospherePowerOuter - _gramTransition.fromAtmospherePowerOuter) * e
atmosphereMaterial.uniforms.uStrengthOuter.value = _gramTransition.fromAtmosphereStrengthOuter + (_gramTransition.toAtmosphereStrengthOuter - _gramTransition.fromAtmosphereStrengthOuter) * e
```

## 严格边界

**只允许改动**:`FAR_VIEW_ATMOSPHERE`常量增加三个字段；`transitionToComposition()`内对应的目标值计算；`_gramTransition`对象新增三组`from/to`字段；`_updateGramTransition()`新增三行插值。

**禁止改动**:`_atmVert`/`_atmFrag`shader本身；`atmosphere2Material`；`THEME_VISUAL_CONFIG`里各主题自己的`atmosphere`数值（近景不受影响）；第一、二轮已经生效的`FAR_VIEW_LIGHTING`/镜头经度逻辑。

## 完成后请提供（这次请按这个方式截图，不要只拍一张整体图）

1. git diff
2. `?earthCandidate=cameraGrammarV1`，noon主题下触发`farOrbit`，等镜头完全稳定后：
   - 一张整体截图
   - 然后**用`window.earth3d.setGramPrimitive('rollDrift')`或手动等待自转一会儿，分别在地球轮廓的12点、3点、6点、9点四个方位附近截图或者描述**，明确告诉我这四个方位是否都能看到辉光（哪怕亮度不同），而不是只有12点方向可见
3. 从`farOrbit`切回`homeGlobe`，确认近景辉光/衰减形状没有被这次改动影响（这是最容易漏测的地方——因为这次新增了`power`/`powerOuter`/`strengthOuter`的插值，近景切回时这几个值应该正确插值回主题自己的数值）
4. 最终使用的数值

## 验证方式

1. far视角下，球体轮廓的12/3/6/9点四个方位都能看到辉光（不要求四个方位一样亮，但都不应该是"完全看不见"）
2. 近景构图（homeGlobe等）辉光形状/亮度不受这次改动影响
3. 夜间主题不受影响
4. 控制台无新增报错
