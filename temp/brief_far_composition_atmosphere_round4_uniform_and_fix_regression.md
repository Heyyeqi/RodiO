# 远景构图大气辉光 第四轮:改为整球均匀发光(不再跟随太阳方向)+ 修复近景回归bug

本轮阶段:方向调整(简化目标) + 修复上一轮引入的回归问题
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件
允许 commit:否,除非我后续明确批准

---

## 背景

前两轮一直在尝试"让辉光有方向性(朝阳侧亮、背阳侧暗一点)同时背阳侧依然可见"，反复调`sunInfluence`都没能让3点/6点方向的辉光变得可见——用户看完截图后决定简化目标：**远景构图的辉光不需要再区分朝阳/背阳，直接做成整个球体轮廓均匀发光**，像一整个发光体，不再依赖太阳方向调制。这样就不存在"背光侧太暗"这个问题了。

同时上一轮验证时发现一个回归bug：从`farOrbit`切回`homeGlobe`后，近景辉光变成"过度明亮、不自然的环状晕圈"，怀疑是`power`/`powerOuter`/`strengthOuter`插值没有正确回到主题自身数值。这轮一并修复。

## 这一轮做什么

### 1. 远景辉光改为均匀发光（不跟随太阳方向）

把`FAR_VIEW_ATMOSPHERE`(`earth3d.js:6408`附近)的`sunInfluence`改成接近0的值：
```js
const FAR_VIEW_ATMOSPHERE = { opacity: 0.30, sunInfluence: 0.05, power: 3.5, powerOuter: 2.2, strengthOuter: 0.22 }
```
`sunInfluence`降到`0.05`之后，shader里的`modFactor = mix(1.0, sunFactor, uSunInfluence)`会非常接近`1.0`，不管`sunDot`是多少，辉光亮度基本不再受太阳方向影响，整个可见轮廓应该均匀发光。`opacity`从`0.34`略降到`0.30`（因为不再需要"暗面也要挣扎着可见"，均匀发光后基础亮度可以适度降低，避免朝阳侧过曝——如果视觉判断后觉得偏亮或偏暗，可以在`0.24~0.34`区间调整）。

**如果这样做完之后视觉上仍然能看出朝阳侧比背阳侧亮，属于正常残留（fresnel本身在极端斜角会有一点自然差异），不需要纠结到完全无差别，只要"四个方位都清晰可见、不再有一侧完全看不见的情况"就算达标。**

### 2. 排查修复近景回归bug

先加一个诊断手段：`getGramDebug()`(`earth3d.js:7020`)返回对象里新增这几个字段：
```js
atmosphereOpacity: atmosphereMaterial.uniforms.uOpacity.value,
atmospherePower: atmosphereMaterial.uniforms.uPower.value,
atmospherePowerOuter: atmosphereMaterial.uniforms.uPowerOuter.value,
atmosphereStrengthOuter: atmosphereMaterial.uniforms.uStrengthOuter.value,
atmosphereSunInfluence: atmosphereMaterial.uniforms.uSunInfluence.value,
```

然后请你实际复现一次"farOrbit切回homeGlobe后辉光变形"的问题，复现后立刻在控制台执行`window.earth3d.getGramDebug()`，把返回的这几个数值截图/贴给我。

**根据这几个数值判断根因**（不要在没有实际数值之前就动手改代码猜测性修复）：
- 如果`atmospherePower`显示接近`16.0`而不是`6.0`左右：说明`themeCfg.atmosphere?.power`这个读取在切回近景时没有拿到预期的主题数值（需要打印`currentTheme`和`THEME_VISUAL_CONFIG[currentTheme].atmosphere.power`确认实际值，检查`currentTheme`这个变量在切换构图的那个时间点是否是预期的主题key）
- 如果这几个数值都显示正常（比如opacity≈0.09, power≈6.0），但视觉上依然不对：说明问题不在这几个uniform本身，可能是别的地方（比如`atmosphere.visible`判断、`radius`没有插值导致近景用了远景的半径感——检查`_gramTransition`和`_updateGramTransition()`有没有遗漏对`uRadius`/`uColor`/`uColorOuter`这几个没有加入插值的字段，它们目前应该完全没被这轮改动碰过，如果被意外改了需要恢复）

## 严格边界

**只允许改动**：`FAR_VIEW_ATMOSPHERE`的`sunInfluence`/`opacity`数值；`getGramDebug()`新增诊断字段；根据实际排查结果修复的回归bug（具体改动范围取决于排查结论，如果需要改动`_gramTransition`/`_updateGramTransition()`之外的地方，请先告诉我排查到的根因，不要直接扩大改动范围）。

**禁止改动**：`_atmVert`/`_atmFrag`shader本身；`atmosphere2Material`；`THEME_VISUAL_CONFIG`里各主题的`atmosphere`数值本身。

## 完成后请提供

1. git diff
2. `?earthCandidate=cameraGrammarV1`，noon主题下触发`farOrbit`，稳定后在12/3/6/9点四个方位截图或描述，确认辉光不再有"一侧完全看不见"的情况
3. 从`farOrbit`切回`homeGlobe`，截图确认辉光恢复正常（不再是"过度明亮的环状晕圈"），并贴一下`getGramDebug()`在这个状态下的返回值
4. 如果发现了回归bug的根因，简单说明一下是什么原因

## 验证方式

1. far视角下四个方位辉光都可见，不存在完全消失的一侧
2. 近景`homeGlobe`辉光恢复正常近景观感，不再变形/过曝
3. 夜间主题、其余候选不受影响
4. 控制台无新增报错
