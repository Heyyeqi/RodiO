# 远景构图大气辉光 第五轮:改用atmosphere2(BackSide)网格,替代第四轮方案

## 【重要提醒:上一次没有真正执行这份brief】

上一次收到这份brief后,实际提交的diff里**完全没有出现"atmosphere2"字样**(核实过,0处)——也就是说上次根本没有切换到`atmosphere2`,而是继续在原来的`atmosphereMaterial`(FrontSide)上调了一组新参数(`opacity:0.12, sunInfluence:0.0, power:4.0, powerOuter:2.0, strengthOuter:0.45`)就提交了。这不是这份brief的内容,是完全另外做的一轮。

而且这次测试结果很有参考价值：**`sunInfluence`已经调到`0.0`(理论上最强的"完全不受太阳方向影响"设置),辉光依然只在朝阳侧一小块区域可见**。这证明问题根本不是太阳方向调制的问题,不管怎么调`atmosphereMaterial`的参数都不会有用——必须真正切换到`atmosphere2`(BackSide渲染)才可能解决,这也是为什么这份brief从一开始就要求切换网格,而不是继续调参数。

**这次请严格按下面的步骤来,尤其是第2步"隐藏atmosphere、显示atmosphere2"这一步必须真正写进代码，不能跳过。提交前请自己先执行一遍这个自查：**
```js
// 在浏览器控制台，触发一次远景构图后立即执行：
console.log('atmosphere.visible:', window.earth3d && document.querySelector('canvas') ? 'check via devtools' : 'n/a')
```
更直接的自查方式：完成后，git diff里必须能搜到`atmosphere2Material.uniforms`被赋值的代码（不是只在判断里提到它），如果`grep -c "atmosphere2Material.uniforms" 改动的文件`结果是0，说明还是没有真正切换，需要重做。

## 【追加范围】扩大到所有"露出完整地球球体"的构图

用户进一步明确了判断标准：不是所有近景构图都要改，只有**镜头里能看到完整地球球体轮廓**的构图才需要这套远景辉光处理；`homeGlobe`保持现状不动（哪怕它也接近露出完整球体，用户明确表态"homeglobe不改"）。

按这个标准，`FAR_COMPOSITIONS`(`earth3d.js:6404`)要从：
```js
const FAR_COMPOSITIONS = new Set(['farOrbit', 'oceanExpanse', 'deepSpace'])
```
扩大成：
```js
const FAR_COMPOSITIONS = new Set(['farOrbit', 'oceanExpanse', 'deepSpace', 'polarDiagonal', 'cityAnchor'])
```
（`polarDiagonal`的`earthDiameterPct:0.6`、`cityAnchor`的`earthDiameterPct:0.65`，已核实这两个都是完整球体入镜，不是`horizonSkim`/`limbHero`那种贴地表局部特写，符合"露出完整球体"标准）

`approach`序列(`CAMERA_SEQUENCES.approach`)本身会经过`farOrbit`这一步，不需要额外处理，扩大`FAR_COMPOSITIONS`后会自动带上这次效果。

其余`homeGlobe`/`portraitMarble`/`terminatorPortrait`/`horizonSkim`/`limbHero`不在这次范围内，保持现状。

下面是原有的第五轮方案（技术实现不变，只是`FAR_COMPOSITIONS`的定义要按上面这样扩大）：

---

本轮阶段:改用替代技术方案(取代第四轮`brief_far_composition_atmosphere_round4_...`的思路,那版不要再继续做)
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件
允许 commit:否,除非我后续明确批准

---

## 背景

前几轮持续调`atmosphereMaterial`(FrontSide)的`opacity`/`sunInfluence`/`power`,始终没能让远景构图的辉光在12/3/6/9点四个方位都可见。你提出改用`atmosphere2`(现有的第二层大气网格,`BackSide + depthTest:false + AdditiveBlending`,目前只有`deepNight`等夜间主题在用)来代替——这个方向可以试,但有两点要注意,已经在下面的实现步骤里写清楚了：

1. `atmosphere2Material`用的是**跟`atmosphereMaterial`完全相同的`_atmVert`/`_atmFrag`shader**(同一份fresnel公式),只是`side`/`depthTest`不同——所以`sunInfluence`同样需要设成接近0的值，不能假设换了BackSide就自动不受太阳方向影响
2. `atmosphere2`现在是被夜间主题(`deepNight`等)使用的现成资源(`applyTheme()`里`config.atmosphere2`存在时才显示,`earth3d.js:5648-5657`)——这次要在白天远景构图时"借用"这个网格，必须确保离开远景构图/切换主题时能正确恢复，不会跟夜间主题自己的`atmosphere2`用法互相污染

## 现状(已核实)

- `atmosphere2Material`(`earth3d.js:2162-2181`)：`uColor:'#C8F5FF', uOpacity:0.0, uPower:5.0, uPowerOuter:3.2, uStrengthOuter:0.0, uRadius:2.03, uSunInfluence:0.85, side:THREE.BackSide, depthTest:false, depthWrite:false, blending:AdditiveBlending`
- `atmosphere2.visible`(`earth3d.js:541`声明，初始`false`)目前完全由`applyTheme()`(`earth3d.js:5648-5657`)控制：主题定义了`config.atmosphere2`就显示并应用该主题的配置，否则隐藏。白天四个主题(`morning`/`noon`/`afternoon`/`goldenApproach`)目前都没有定义`config.atmosphere2`，所以现在这几个主题下`atmosphere2.visible`恒为`false`
- 上一轮(第四轮)在`atmosphereMaterial`上做的`FAR_VIEW_ATMOSPHERE`覆盖逻辑（`transitionToComposition()`/`_gramTransition`/`_updateGramTransition()`里那些`fromAtmosphereOpacity`等字段）**这轮全部要改造成操作`atmosphere2Material`，不是新增，是把目标从`atmosphereMaterial`换成`atmosphere2Material`，同时`atmosphereMaterial`本身在远景构图时需要隐藏**

## 这一轮做什么

### 1. `FAR_VIEW_ATMOSPHERE`新增`sunInfluence`保持接近0

```js
const FAR_VIEW_ATMOSPHERE = { opacity: 0.30, sunInfluence: 0.05, power: 3.5, powerOuter: 2.2, strengthOuter: 0.22 }
```
（跟第四轮brief里的数值一致，这次只是换了作用对象）

### 2. `transitionToComposition()`里，远景构图时隐藏`atmosphere`、显示并配置`atmosphere2`

在已有的`applyFarViewTreatment`判断之后，新增：
```js
if (applyFarViewTreatment) {
  atmosphere.visible = false
  atmosphere2.visible = true
  atmosphere2Material.uniforms.uColor.value.set('#f7feff')
  atmosphere2Material.uniforms.uColorOuter.value.set('#9fd7ff')
  atmosphere2Material.uniforms.uRadius.value = 2.04
} else {
  atmosphere2.visible = false
  // atmosphere.visible 交给 applyTheme() 已有逻辑（atmosphere.visible = (config.atmosphere.opacity ?? 0) > 0.0001）
  // 这里不需要手动设 true，因为 applyTheme() 在主题加载/切换时已经处理了这个判断；
  // 但为了保险，如果发现离开远景构图后 atmosphere 没有正确恢复可见，
  // 可以显式加一行 atmosphere.visible = (themeCfg.atmosphere?.opacity ?? 0) > 0.0001
}
```
**注意**：`atmosphere2`的`uColor`/`uColorOuter`/`uRadius`这几个字段直接在这里设置一次即可（不需要过渡插值），因为`atmosphere2`在近景时完全不可见，不存在"从近景颜色过渡到远景颜色"这种视觉需求。

### 3. `opacity`/`power`/`powerOuter`/`strengthOuter`/`sunInfluence`的目标值计算，改成从`atmosphere2Material`读取起始值、写入`atmosphere2Material`

把第四轮brief里这几行：
```js
const toAtmosphereOpacity = applyFarViewTreatment ? FAR_VIEW_ATMOSPHERE.opacity : (themeCfg.atmosphere?.opacity ?? 0)
const toSunInfluence = applyFarViewTreatment ? FAR_VIEW_ATMOSPHERE.sunInfluence : 0.85
const toAtmospherePower = applyFarViewTreatment ? FAR_VIEW_ATMOSPHERE.power : (themeCfg.atmosphere?.power ?? 16.0)
const toAtmospherePowerOuter = applyFarViewTreatment ? FAR_VIEW_ATMOSPHERE.powerOuter : (themeCfg.atmosphere?.powerOuter ?? 3.2)
const toAtmosphereStrengthOuter = applyFarViewTreatment ? FAR_VIEW_ATMOSPHERE.strengthOuter : (themeCfg.atmosphere?.strengthOuter ?? 0.0)
```
改成（目标值不变，只是`applyFarViewTreatment`为`false`时的"近景默认值"要改成`atmosphere2`自己主题配置的值，而不是`atmosphereMaterial`那套）：
```js
const toAtm2Opacity = applyFarViewTreatment ? FAR_VIEW_ATMOSPHERE.opacity : (themeCfg.atmosphere2?.opacity ?? 0)
const toAtm2SunInfluence = applyFarViewTreatment ? FAR_VIEW_ATMOSPHERE.sunInfluence : 0.85
const toAtm2Power = applyFarViewTreatment ? FAR_VIEW_ATMOSPHERE.power : (themeCfg.atmosphere2?.power ?? 5.0)
const toAtm2PowerOuter = applyFarViewTreatment ? FAR_VIEW_ATMOSPHERE.powerOuter : (themeCfg.atmosphere2?.powerOuter ?? 3.2)
const toAtm2StrengthOuter = applyFarViewTreatment ? FAR_VIEW_ATMOSPHERE.strengthOuter : (themeCfg.atmosphere2?.strengthOuter ?? 0.0)
```
`_gramTransition`对象里新增（这次字段名用`atm2`前缀，跟第四轮的`atmosphere`前缀区分，避免混淆）：
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

`_updateGramTransition()`里新增插值（**注意：这次不要再对`atmosphereMaterial`的uniform做插值了，第四轮加的那几行如果已经写进代码，这次要删掉/替换掉，不要两套并存**）：
```js
atmosphere2Material.uniforms.uOpacity.value = _gramTransition.fromAtm2Opacity + (_gramTransition.toAtm2Opacity - _gramTransition.fromAtm2Opacity) * e
atmosphere2Material.uniforms.uSunInfluence.value = _gramTransition.fromAtm2SunInfluence + (_gramTransition.toAtm2SunInfluence - _gramTransition.fromAtm2SunInfluence) * e
atmosphere2Material.uniforms.uPower.value = _gramTransition.fromAtm2Power + (_gramTransition.toAtm2Power - _gramTransition.fromAtm2Power) * e
atmosphere2Material.uniforms.uPowerOuter.value = _gramTransition.fromAtm2PowerOuter + (_gramTransition.toAtm2PowerOuter - _gramTransition.fromAtm2PowerOuter) * e
atmosphere2Material.uniforms.uStrengthOuter.value = _gramTransition.fromAtm2StrengthOuter + (_gramTransition.toAtm2StrengthOuter - _gramTransition.fromAtm2StrengthOuter) * e
```

### 4. `atmosphereMaterial`(第一层)本身完全不用碰

第一层`atmosphereMaterial`的`opacity`/`power`等这次**不需要任何插值改动**——近景时它保持`applyTheme()`已有逻辑控制的可见性和数值，远景时靠第2步的`atmosphere.visible = false`直接隐藏，不需要同时把它的opacity插值到0（两者效果一样，但没必要维护两套插值逻辑）。**如果第四轮已经在`atmosphereMaterial`上加了插值代码，这一轮要把那些`fromAtmosphereOpacity`/`toAtmosphereOpacity`等字段和对应插值行整体删除**，避免两层大气叠加造成不可预期的效果。

## 严格边界

**只允许改动**：`FAR_VIEW_ATMOSPHERE`常量（保留/调整数值）；`transitionToComposition()`内`atmosphere.visible`/`atmosphere2.visible`切换逻辑、`atmosphere2Material`目标值计算；`_gramTransition`对象里`atm2`前缀的新字段（同时删除第四轮加的`atmosphereMaterial`相关字段，如果已经存在）；`_updateGramTransition()`里对应插值行（同时删除第四轮加的`atmosphereMaterial`插值行，如果已经存在）。

**禁止改动**：`_atmVert`/`_atmFrag`shader本身；`atmosphereMaterial`/`atmosphere2Material`的构造代码（`earth3d.js:2129-2181`）；`applyTheme()`里`atmosphere2`的现有主题判断逻辑（`earth3d.js:5648-5657`，夜间主题的`atmosphere2`使用方式不能被这次改动影响）；`THEME_VISUAL_CONFIG`里各主题数值本身。

## 完成后请提供

1. git diff（重点看一下第四轮如果已经落地的`atmosphereMaterial`插值代码是否被正确清理/替换，不要两套并存）
2. `?earthCandidate=cameraGrammarV1`，noon主题下触发`farOrbit`，稳定后在12/3/6/9点四个方位截图或描述，确认辉光都可见
3. 从`farOrbit`切回`homeGlobe`，截图确认：① 第一层`atmosphere`辉光恢复正常近景观感（不是变形的环状晕圈）② `atmosphere2.visible`正确变回`false`
4. 切换到`deepNight`主题（本来就用`atmosphere2`的夜间主题），确认它自己的辉光效果不受这次改动影响，且触发`farOrbit`后再切回，`atmosphere2`能正确恢复成deepNight自己的配置（不会残留白天远景的参数）
5. 控制台无新增报错

## 验证方式

1. far视角下12/3/6/9点四个方位辉光均可见，不存在完全消失的一侧
2. 近景`homeGlobe`两层大气都恢复正常（第一层近景观感正常，第二层完全隐藏）
3. 夜间主题（`deepNight`等，本身用`atmosphere2`）不受影响，包括切入切出远景构图后再回到夜间主题
4. 其余候选/近景构图不受影响
5. 控制台无新增报错
