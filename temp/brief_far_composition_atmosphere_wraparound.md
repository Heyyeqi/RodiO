# 远景构图大气辉光补充:让辉光包裹整个可见球体轮廓(不只是顶部一小块)

本轮阶段:直接实施,补充上一轮(`远景构图专属光照 + 镜头角度跟随真实太阳`)遗漏的部分
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件,尤其不要碰`earthMaterial.onBeforeCompile`那段自定义调色shader、`_atmVert`/`_atmFrag`shader代码本身
允许 commit:否,除非我后续明确批准

---

## 背景

上一轮("远景构图专属光照 + 镜头角度跟随真实太阳")已经上线,用户实测`farOrbit`后反馈:辉光依然只出现在地球顶部朝向镜头的一小块区域,不是参考图那种"包裹整个可见球体轮廓"的效果——**这是我这边规划时的疏漏,上一轮brief只处理了地表明暗(ambient/sun),漏掉了大气辉光本身也需要专门为远景构图调整这一块**,不是Marvis实施有问题。

## 根因(已读shader代码确认)

`_atmFrag`(`earth3d.js:2098-2127`)里,大气辉光的太阳方向调制:
```glsl
float sunDot   = dot(vWorldNormal, uSunDir);
float sunFactor = clamp(sunDot * 0.55 + 0.55, 0.06, 1.0);
float modFactor = mix(1.0, sunFactor, uSunInfluence);
total *= modFactor;
```
`uSunInfluence`目前是硬编码常量`0.85`(`earth3d.js:2141`,`atmosphereMaterial`构造时写死,从来没有被任何主题配置或代码路径改过)。在完全背对太阳的一侧(`sunDot=-1`),`sunFactor`被压到floor值`0.06`,`modFactor = mix(1, 0.06, 0.85) ≈ 0.20`——也就是说背对太阳那一侧的辉光亮度只有"未调制"亮度的20%左右。配合远景构图现在复用的是各个白天主题原本就调得比较保守的`opacity`(比如noon是`0.09`,本来是给近景构图调的),两者叠加后,背光一侧的辉光亮度只有`0.09 × 0.20 ≈ 0.018`这个数量级,在深色的太空背景下几乎不可见——这就是"辉光只出现在顶部朝阳一小块"的直接原因。

## 要做的事

### 1. 给`atmosphereMaterial`新增远景构图专属的opacity + sunInfluence

复用上一轮已经建立的`FAR_COMPOSITIONS`/`applyFarViewTreatment`判断和`_gramTransition`插值机制,新增两组目标值。

在`FAR_VIEW_LIGHTING`常量旁边(`earth3d.js:6407`附近)新增:
```js
const FAR_VIEW_ATMOSPHERE = { opacity: 0.30, sunInfluence: 0.40 }
```
(这两个数值是根据shader公式反推的起点估计,不是实测过的精确值——**这轮请你先视觉调试确认效果,如果太暗/太亮/包裹范围不够,可以在`opacity: 0.22~0.38`、`sunInfluence: 0.30~0.55`这个区间内微调,不需要死板照抄,但请截图告诉我你最终用的数值**)

### 2. `transitionToComposition()`里新增大气目标值

在上一轮加的这段(`earth3d.js:6529`附近)旁边:
```js
const themeCfg = THEME_VISUAL_CONFIG[currentTheme] || THEME_VISUAL_CONFIG.night
const toAmbient = applyFarViewTreatment ? FAR_VIEW_LIGHTING.ambient : themeCfg.lighting.ambient
const toSun = applyFarViewTreatment ? FAR_VIEW_LIGHTING.sun : themeCfg.lighting.sun
```
再加两行:
```js
const toAtmosphereOpacity = applyFarViewTreatment ? FAR_VIEW_ATMOSPHERE.opacity : (themeCfg.atmosphere?.opacity ?? 0)
const toSunInfluence = applyFarViewTreatment ? FAR_VIEW_ATMOSPHERE.sunInfluence : 0.85
```

`_gramTransition = {...}`对象里,跟`fromAmbient/toAmbient`并列的地方,新增:
```js
fromAtmosphereOpacity: atmosphereMaterial.uniforms.uOpacity.value,
toAtmosphereOpacity,
fromSunInfluence: atmosphereMaterial.uniforms.uSunInfluence.value,
toSunInfluence,
```

### 3. `_updateGramTransition()`里插值

跟上一轮加的`ambientLight.intensity = ...`/`sunLight.intensity = ...`两行并列,新增:
```js
atmosphereMaterial.uniforms.uOpacity.value = _gramTransition.fromAtmosphereOpacity + (_gramTransition.toAtmosphereOpacity - _gramTransition.fromAtmosphereOpacity) * e
atmosphereMaterial.uniforms.uSunInfluence.value = _gramTransition.fromSunInfluence + (_gramTransition.toSunInfluence - _gramTransition.fromSunInfluence) * e
```

这样离开远景构图、回到近景构图时,`opacity`会平滑插值回当前主题原本的数值,`sunInfluence`平滑插值回默认的`0.85`,不会有残留。

## 严格边界

**只允许改动**:新增`FAR_VIEW_ATMOSPHERE`常量;`transitionToComposition()`内新增的大气目标值计算;`_gramTransition`对象新增`fromAtmosphereOpacity/toAtmosphereOpacity/fromSunInfluence/toSunInfluence`字段;`_updateGramTransition()`新增两行大气插值。

**禁止改动**:`_atmVert`/`_atmFrag`shader代码本身;`atmosphereMaterial`/`atmosphere2Material`的构造代码(`earth3d.js:2129-2176`);`atmosphere2Material`(这次只碰主大气层`atmosphereMaterial`,不碰第二层);上一轮已经加的`FAR_VIEW_LIGHTING`/镜头经度逻辑(维持不变);`THEME_VISUAL_CONFIG`里各主题的`atmosphere.opacity`/`power`等数值(这次不改主题本身的配置,只在远景构图过渡时临时覆盖运行时的uniform值)。

## 完成后请提供

1. git diff
2. `?earthCandidate=cameraGrammarV1`,白天主题(noon)下触发`farOrbit`,截图确认辉光现在能在球体轮廓的大部分范围可见(不只是顶部一小块),背光一侧应该能看到明显更暗但依然可辨认的辉光,不是完全消失
3. 从`farOrbit`切回`homeGlobe`,截图确认辉光恢复正常近景观感(不残留远景的高opacity/低sunInfluence)
4. 如果视觉判断后调整了`FAR_VIEW_ATMOSPHERE`的数值,请告诉我最终用的具体数值和理由

## 验证方式

1. 白天主题下`farOrbit`/`oceanExpanse`/`deepSpace`三个远景构图,辉光包裹范围明显比之前更大,背光侧不再是完全看不见
2. 近景构图不受影响
3. 夜间主题下这几个远景构图不受影响(`applyFarViewTreatment`判断天然排除)
4. 远景↔近景来回切换,辉光过渡平滑无跳变
5. 控制台无新增报错
