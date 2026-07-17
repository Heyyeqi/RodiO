# rimGlow:把outer/inner环形辉光增强也扩大到homeGlobe(sunLobe压制维持只在远景)

本轮阶段:小范围扩展(在上一轮已落地的机制上加一个判断条件,不是重新做)
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件
允许 commit:否,除非我后续明确批准

---

## 背景

上一轮做完之后，用户看了homeGlobe(近景默认视角)下的效果，还是"只有顶部亮"的老样子——这是符合上一轮设计的（`isFarComposition`只覆盖`farOrbit`/`oceanExpanse`/`deepSpace`/`polarDiagonal`/`cityAnchor`/`portraitMarble`/`terminatorPortrait`这几个远景构图，`homeGlobe`不在其中）。

现在决定：**`outer`/`inner`这个环形辉光的增强，也要扩大到`homeGlobe`**，让默认视角也能有"贴合球体轮廓、不只是顶部一块"的效果。但`sunLobe`的压制**维持只在远景构图生效**，不动homeGlobe——因为homeGlobe下sunLobe的比例是协调的（近景本来就是为它设计的），压掉反而会丢失每个主题自己的"阳光方向感"这个特色，只有远景下地球缩小才会比例失调。

## 现状(已核实，`earth3d.js:6527-6549`附近)

```js
const isFarComposition = FAR_COMPOSITIONS.has(compositionKey)
// ...
const fromSunLobeStrength = _emRimOverlayMat.uniforms.uSunLobeStrength?.value ?? 0
const fromOuterCore = _emRimOverlayMat.uniforms.uCoreStrength?.value ?? 0
const fromOuterHalo = _emRimOverlayMat.uniforms.uHaloStrength?.value ?? 0
const fromInnerStrength = _emInnerVeilMat.uniforms.uInnerVeilStrength?.value ?? 0
const FAR_VIEW_RIM = { outerCoreStrength: 0.75, outerHaloStrength: 0.42, innerStrength: 0.34 }
const toSunLobeStrength   = isFarComposition ? 0.0 : fromSunLobeStrength
const toOuterCoreStrength = isFarComposition ? FAR_VIEW_RIM.outerCoreStrength : fromOuterCore
const toOuterHaloStrength = isFarComposition ? FAR_VIEW_RIM.outerHaloStrength : fromOuterHalo
const toInnerStrength     = isFarComposition ? FAR_VIEW_RIM.innerStrength : fromInnerStrength
```
`toOuterCoreStrength`/`toOuterHaloStrength`/`toInnerStrength`目前跟`toSunLobeStrength`共用同一个`isFarComposition`判断。这次要把outer/inner这三个的判断条件换成一个新的、范围更大的集合（包含homeGlobe），`sunLobe`的判断条件不变。

## 要做的事

在`FAR_COMPOSITIONS`(`earth3d.js:6404`附近)旁边新增：
```js
const RIM_BOOST_COMPOSITIONS = new Set([...FAR_COMPOSITIONS, 'homeGlobe'])
```

在`isFarComposition`旁边新增：
```js
const applyRimBoost = RIM_BOOST_COMPOSITIONS.has(compositionKey)
```

把outer/inner这三行的判断条件从`isFarComposition`换成`applyRimBoost`（`sunLobe`那一行`toSunLobeStrength`保持`isFarComposition`不变）：
```js
const toOuterCoreStrength = applyRimBoost ? FAR_VIEW_RIM.outerCoreStrength : fromOuterCore
const toOuterHaloStrength = applyRimBoost ? FAR_VIEW_RIM.outerHaloStrength : fromOuterHalo
const toInnerStrength     = applyRimBoost ? FAR_VIEW_RIM.innerStrength : fromInnerStrength
```

**这三个数值(`FAR_VIEW_RIM.outerCoreStrength/outerHaloStrength/innerStrength`)是上一轮已经在远景验证过的，这次直接复用同一组数值应用到homeGlobe，不需要重新调——但请视觉测试确认一下homeGlobe这种近景视角下用同一组数值是否合适（近景地球本身占屏幕比例更大，同样的强度在近景可能显得比远景更明显/更暗，如果观感明显不对，可以告诉我，不要自己改动这几个数值，除非差异很小可以直接微调）。**

## 严格边界

**只允许改动**:新增`RIM_BOOST_COMPOSITIONS`常量、新增`applyRimBoost`变量、把outer/inner三行判断条件从`isFarComposition`换成`applyRimBoost`。

**禁止改动**:`toSunLobeStrength`那一行(继续用`isFarComposition`，不要跟着换成`applyRimBoost`)；`FAR_VIEW_RIM`的数值本身(除非视觉测试后确实需要微调，需要先说明理由)；`_gramTransition`/`_updateGramTransition()`里的插值逻辑结构本身；其余任何代码。

## 完成后请提供

1. git diff
2. `homeGlobe`(白天任一主题，比如noon/afternoon/evening都测一下)截图，确认outer/inner辉光现在能贴合球体大部分轮廓可见，同时sunLobe的方向性光斑依然保留(不是被一起压掉了)
3. 远景构图(比如`farOrbit`)截图，确认之前的效果不受这次改动影响(sunLobe依然被压制，outer/inner依然是远景那组增强值)
4. 控制台无新增报错

## 验证方式

1. homeGlobe下辉光包裹范围明显比之前更大，sunLobe方向性光斑保留不变
2. 远景构图效果不受影响
3. 其余近景构图(`portraitMarble`/`terminatorPortrait`——注意这两个已经被加进`FAR_COMPOSITIONS`了，属于远景处理，不在这次`homeGlobe`扩展范围内，行为不应该因为这次改动而变化)、夜间主题不受影响
4. 控制台无新增报错
