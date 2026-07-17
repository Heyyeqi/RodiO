# rimGlow远景适配:抑制远景构图下比例失调的sunLobe + 补上之前遗漏的重置bug修复

本轮阶段:两件事一起做(重置bug必须先落地,远景抑制是新增)
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件
允许 commit:否,除非我后续明确批准

---

## 背景

排查确认了两个独立问题：

1. **重置bug(上一轮brief要求修但没有落地)**：`applyRimGlowThemeConfig()`(`earth3d.js:2704`)里`if (sunLobe) {...}`，主题没定义`sunLobe`时整个块被跳过，`uSunLobeEnabled`等uniform不会被重置，导致切换主题时可能沿用上一个主题残留的sunLobe状态。**这次请务必真正实现，之前发出的brief这部分没有被执行。**

2. **sunLobe比例失调(这次新确认的)**：sunLobe的`(x, y)`是屏幕空间归一化坐标，不随构图缩放。近景(地球占屏幕大部分)下比例协调，但远景(`farOrbit`/`oceanExpanse`/`deepSpace`/`polarDiagonal`/`cityAnchor`，地球缩得很小)下，同一个sunLobe相对地球比例失调，看起来像一根突兀的光柱——这不是bug，是sunLobe设计时没考虑远景场景，这次要专门针对远景构图抑制/关闭它。

## 现状(已核实)

- `FAR_COMPOSITIONS`(`earth3d.js:6404`附近)已经是现成的远景构图集合:`['farOrbit', 'oceanExpanse', 'deepSpace', 'polarDiagonal', 'cityAnchor']`，`applyFarViewTreatment`(`isFarComposition && isDaytimeTheme`)也已经在`transitionToComposition()`里算好了，这次直接复用，不需要重新判断
- `_emRimOverlayMat.uniforms`(rim overlay材质，`applyRimGlowThemeConfig()`写入的目标)、`_emInnerVeilMat.uniforms`是模块作用域内可直接访问的变量
- `transitionToComposition()`/`_updateGramTransition()`已经建立了"计算目标值→写入`_gramTransition`→每帧插值"这套机制(之前用在ambient/sun/atmosphere2上)，这次sunLobe抑制、outer/inner增强，复用同一套模式

## 要做的事

### 1. 修复重置bug(务必先做)

`applyRimGlowThemeConfig()`里：
```js
if (sunLobe) {
  ro.uSunLobeEnabled.value     = sunLobe.enabled ? 1.0 : 0.0
  // ...(现有逻辑不变)
} else {
  ro.uSunLobeEnabled.value = 0.0
  ro.uArcBandEnabled.value = 0.0
  if (rv.uSurfWarmthEnabled) rv.uSurfWarmthEnabled.value = 0.0
}
```

### 2. 远景构图下抑制sunLobe、增强outer/inner

在`transitionToComposition()`里，已有的`applyFarViewTreatment`判断附近，新增目标值计算：
```js
const currentSunLobeStrength = _emRimOverlayMat.uniforms.uSunLobeStrength?.value ?? 0
const toSunLobeStrength = applyFarViewTreatment ? 0.0 : currentSunLobeStrength
// outer/inner 的目标：远景时提高，近景保持当前主题apply后的原值
const baseOuterCore = _emRimOverlayMat.uniforms.uCoreStrength?.value ?? 0
const baseOuterHalo = _emRimOverlayMat.uniforms.uHaloStrength?.value ?? 0
const baseInnerStrength = _emInnerVeilMat.uniforms.uInnerVeilStrength?.value ?? 0
// 远景下的目标强度，这几个数值请你先视觉测试确定，下面是起点估计：
const FAR_VIEW_RIM = { outerCoreStrength: 0.75, outerHaloStrength: 0.42, innerStrength: 0.34 }
const toOuterCoreStrength = applyFarViewTreatment ? FAR_VIEW_RIM.outerCoreStrength : baseOuterCore
const toOuterHaloStrength = applyFarViewTreatment ? FAR_VIEW_RIM.outerHaloStrength : baseOuterHalo
const toInnerStrength = applyFarViewTreatment ? FAR_VIEW_RIM.innerStrength : baseInnerStrength
```

**注意**:`currentSunLobeStrength`/`baseOuterCore`等"当前值"的读取，必须在`applyFarViewTreatment`判断**之前**、也就是这次调用还没有对这些uniform做任何远景覆盖之前读取——如果连续两次都触发远景构图(比如`farOrbit`切到`polarDiagonal`)，第二次读到的"current"应该是第一次远景覆盖后的值(这是对的，因为它本来就该保持远景状态，不需要重新插值)，但离开远景构图时的"current"必须是远景状态的值，這样才能正确插值回近景——**这套逻辑请参照已有的`fromAmbient: ambientLight.intensity`那种写法(直接读当前live uniform值作为from，不是重新计算主题基准值)**，避免重新引入之前`atmosphere2`那次"the base value fallback写死成主题配置而不是实时值"导致对不上的问题。

`_gramTransition`对象里新增对应的`from/to`字段(照抄已有模式)，`_updateGramTransition()`里新增对应插值行，插值目标是：
```js
_emRimOverlayMat.uniforms.uSunLobeStrength.value = ...
_emRimOverlayMat.uniforms.uCoreStrength.value = ...
_emRimOverlayMat.uniforms.uHaloStrength.value = ...
_emInnerVeilMat.uniforms.uInnerVeilStrength.value = ...
```

（`FAR_VIEW_RIM`这几个数值是估算起点，不是精确值——请你视觉测试后确认，如果偏差较大可以在合理范围内调整，但请截图告诉我最终用的数值）

## 清理:atmosphere2远景相关代码全部回退

确认这次rimGlow方案是真正生效的视觉来源后，请把之前几轮(`FAR_COMPOSITIONS`触发的`atmosphere`/`atmosphere2`可见性切换、`FAR_VIEW_LIGHTING`地表光照、`FAR_VIEW_ATMOSPHERE`大气层uniform这几块)全部回退删除——**但这个清理请放在这轮最后一步，先把rimGlow远景抑制做完、验证真的达到预期效果之后再做，不要一开始就删，万一这轮效果不理想还需要回头对照**。

`FAR_COMPOSITIONS`这个集合本身、`applyFarViewTreatment`这个判断变量要保留（这次sunLobe抑制还要用），只删`atmosphere`/`atmosphere2`/地表光照相关的覆盖逻辑。

## 完成后请提供

1. git diff
2. 主题切换重置bug的验证:找一个有sunLobe的主题(比如sunset)切到没有sunLobe的主题(比如noon)，确认noon下不再有残留的sunLobe光斑
3. `farOrbit`/`oceanExpanse`/`polarDiagonal`/`cityAnchor`/`deepSpace`五个远景构图，白天主题下(建议测noon和sunset两个，一个没有sunLobe一个有强sunLobe)，截图确认sunLobe不再比例失调，outer/inner的rim环强度是否足够、观感是否协调
4. 近景构图(homeGlobe等)不受影响，sunLobe/outer/inner保持原本近景观感
5. 最终使用的`FAR_VIEW_RIM`数值
6. 确认atmosphere2相关代码清理干净(git diff里应该看不到`FAR_VIEW_ATMOSPHERE`/`FAR_VIEW_LIGHTING`/`atmosphere2.visible`相关内容了)
7. 控制台无新增报错

## 验证方式

1. 切换主题(有sunLobe→无sunLobe)不再残留污染
2. 远景构图下sunLobe不再比例失调，outer/inner足够撑起观感
3. 近景不受影响
4. atmosphere2清理干净，代码库不留死代码
5. 控制台无新增报错
