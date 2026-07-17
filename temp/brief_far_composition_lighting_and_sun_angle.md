# 远景构图专属光照 + 镜头角度跟随真实太阳(farOrbit/oceanExpanse/deepSpace)

本轮阶段:直接实施,已用Preview实测验证过全部数值
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件,尤其不要碰`earthMaterial.onBeforeCompile`里那段自定义调色shader(v17 daybase-darkened,`earth3d.js:1586-1923`)——这次改动完全不需要动它
允许 commit:否,除非我后续明确批准

---

## 背景

用户反馈当前地球辉光/观感跟参考图(Apple地球屏保风格,阳光从一侧斜射、有明显方向性明暗+柔和辉光)差距明显,尤其是"远景/全球构图"(`farOrbit`/`oceanExpanse`/`deepSpace`,整个地球都入镜的那几个构图)。排查后确认两个根因,这轮一起修:

1. **这几个远景构图的镜头经度是写死的固定值**(比如`farOrbit`固定`lon:121.47`),不跟随真实太阳位置——运气不好时镜头会对着地球一片比较平淡无方向感的区域,做不出参考图那种"侧光"戏剧效果
2. **当前白天主题的环境光(`ambient`)设得很高(noon是0.98)**,导致地表几乎不呈现方向性阴影,不管镜头对着哪个角度,地表亮度都差不多——参考图那种"一半亮一半有阴影渐变"的立体感做不出来

已经用`window.earth3d.patchTheme()`+`setDebugLocation()`在Preview里反复实测验证:
- 读过`earthMaterial.onBeforeCompile`(`earth3d.js:1586-1923`)的完整自定义shader,确认它只处理漫反射贴图分级(`map_fragment`)和夜景灯光叠加(`emissivemap_fragment`),**没有绕过标准Phong光照计算**——所以调`ambientLight`/`sunLight`强度是安全的,不需要碰这段小心调过的v17调色代码
- 把`ambient`降到`0.2`左右、`sun`提到`1.6`左右,配合镜头经度设为"当前真实太阳直射点经度 + 65°偏移"时,画面呈现出清晰自然的方向性明暗渐变,配合大气辉光,整体效果明显更接近参考图

**范围限定**:这次改动只影响白天主题(`morning`/`noon`/`afternoon`/`goldenApproach`)下的这三个远景构图。夜间主题(`deepNight`/`lateEvening`/`evening`/`night`)本来就不依赖方向性地表阴影(它们`ambient:1.0, sun:0.0`,完全靠emissive夜景灯光呈现"夜晚"观感,这套已经很好),这次**不touch夜间主题下这几个构图的行为**,保持现在这样。

## 现状(已核实)

- `CAMERA_COMPOSITIONS.farOrbit`/`.oceanExpanse`/`.deepSpace`(`earth3d.js:6356`/`6381`/`6401`附近)各自的`lon`字段是写死的常量
- `_computeSubsolarPoint()`(`earth3d.js:5838`)返回`{lat, lon}`,是基于真实UTC时间算出的真实太阳直射点,纯函数、无副作用,可以随时调用
- `normalizeLon()`(`earth3d.js:418`,模块顶层函数,`createEarth3D()`外面,但本身不依赖任何闭包状态,可以在`createEarth3D()`内部任意调用)用于把经度归一化到合理范围
- `THEME_VISUAL_CONFIG[themeKey].lighting.ambient`/`.sun`是每个主题的基准光照值,`resetLightingForTheme(config)`(`earth3d.js:5579`)负责把这两个值写入真正的`ambientLight.intensity`/`sunLight.intensity`(场景里唯二的两盏灯,`earth3d.js:3809`/`3812`)
- `transitionToComposition()`(`earth3d.js:6501`)是所有构图切换的唯一入口,`_gramTransition`对象(`earth3d.js:6530`)记录本次过渡的起止值,`_updateGramTransition()`(`earth3d.js:6546`)每帧插值——这次要新增的"经度动态计算"和"光照跟随过渡"都应该嵌入这套已有的插值机制,不要另起一套定时器
- `currentTheme`(`earth3d.js:5336`附近声明的模块级变量)记录当前生效的主题key,`transitionToComposition()`内部可以直接读取

## 要做的事

### 1. 定义远景构图集合 + 目标光照/角度参数

放在`CAMERA_COMPOSITIONS`附近:
```js
const FAR_COMPOSITIONS = new Set(['farOrbit', 'oceanExpanse', 'deepSpace'])
const FAR_VIEW_SUN_LON_OFFSET_DEG = 65   // 镜头经度 = 真实太阳直射经度 + 此偏移，已实测验证
const FAR_VIEW_LIGHTING = { ambient: 0.2, sun: 1.6 }   // 已实测验证，白天主题专用
```

### 2. `transitionToComposition()`里,远景构图动态计算经度 + 目标光照

在`transitionToComposition()`内部(`earth3d.js:6501`起),现有这几行:
```js
const targetLookAtY = compositionKey === 'homeGlobe' ? comp.lookAtY : (comp.lookAtY || 0)
```
之后、`prefetchTilesForCameraState({...})`调用之前,插入:
```js
const isFarComposition = FAR_COMPOSITIONS.has(compositionKey)
const isDaytimeTheme = ['morning', 'noon', 'afternoon', 'goldenApproach'].includes(currentTheme)
const applyFarViewTreatment = isFarComposition && isDaytimeTheme

let resolvedLon = comp.lon ?? (compositionKey === 'homeGlobe' ? CAMERA_PRESETS.globe.lon : 121.4737)
if (applyFarViewTreatment) {
  const subsolar = _computeSubsolarPoint()
  resolvedLon = normalizeLon(subsolar.lon + FAR_VIEW_SUN_LON_OFFSET_DEG)
}
```

把`prefetchTilesForCameraState({...})`调用和`_gramTransition`对象里所有原本写`comp.lon ?? (compositionKey === 'homeGlobe' ? CAMERA_PRESETS.globe.lon : 121.4737)`的地方(现在有两处,一处在`prefetchTilesForCameraState`调用里,一处在`_gramTransition.toLon`),**统一替换成`resolvedLon`**。

光照目标值:
```js
const themeCfg = THEME_VISUAL_CONFIG[currentTheme] || THEME_VISUAL_CONFIG.night
const toAmbient = applyFarViewTreatment ? FAR_VIEW_LIGHTING.ambient : themeCfg.lighting.ambient
const toSun = applyFarViewTreatment ? FAR_VIEW_LIGHTING.sun : themeCfg.lighting.sun
```

`_gramTransition = {...}`对象里新增两组起止值(照抄现有`fromY/toY`这类写法):
```js
_gramTransition = {
  // ...现有字段不变...
  fromAmbient: ambientLight.intensity,
  toAmbient,
  fromSun: sunLight.intensity,
  toSun,
}
```

### 3. `_updateGramTransition()`里每帧插值光照

`_updateGramTransition()`(`earth3d.js:6546`)现有的插值行(`camera.position.y = ...`等)旁边,加两行:
```js
ambientLight.intensity = _gramTransition.fromAmbient + (_gramTransition.toAmbient - _gramTransition.fromAmbient) * e
sunLight.intensity = _gramTransition.fromSun + (_gramTransition.toSun - _gramTransition.fromSun) * e
```
这样光照变化会跟着镜头移动的缓动曲线同步过渡,不会有突兀的"啪"一下变暗/变亮。

## 已知限制(这轮不处理,口头告知即可)

如果在停留于远景构图期间,恰好发生了主题切换(比如从`noon`跨到`afternoon`),`applyTheme()`里的`resetLightingForTheme()`(`earth3d.js:5579`)会用新主题的基准`ambient`/`sun`覆盖掉这次的远景专属光照值,导致远景光照"跳回"主题默认值,需要下一次构图切换才会重新应用远景处理。这个边界情况这轮不修,只需要知道即可,不需要额外写代码规避。

## 严格边界

**只允许改动**:新增`FAR_COMPOSITIONS`/`FAR_VIEW_SUN_LON_OFFSET_DEG`/`FAR_VIEW_LIGHTING`常量;`transitionToComposition()`内部新增的经度/光照目标值计算逻辑;`_gramTransition`对象新增`fromAmbient/toAmbient/fromSun/toSun`字段;`_updateGramTransition()`新增两行光照插值。

**禁止改动**:`earthMaterial.onBeforeCompile`任何代码;`resetLightingForTheme()`/`applyTheme()`本身的实现;`_computeSubsolarPoint()`/`normalizeLon()`本身的实现(只调用,不改);`CAMERA_COMPOSITIONS`里各构图现有的`lat`/`earthDiameterPct`/`anchorNdcX`/`anchorNdcY`/`fov`等其他字段;夜间主题(`deepNight`/`lateEvening`/`evening`/`night`)下这几个远景构图的行为(通过`isDaytimeTheme`判断天然排除,不需要额外处理,但验证时请确认夜间主题下这几个构图确实没有变化);上一轮已验证的大气辉光`power`/`powerOuter`/`strengthOuter`数值(那部分维持现状,这轮不重复改)。

## 完成后请提供

1. git diff
2. `?earthCandidate=cameraGrammarV1`,在白天任一主题下(比如noon),依次触发`farOrbit`/`oceanExpanse`/`deepSpace`,各截一张图,确认地球呈现方向性明暗渐变(不是之前那种均匀亮度),辉光观感自然
3. 从远景构图切回`homeGlobe`等近景构图,截图确认光照/亮度平滑过渡回正常近景观感,没有突兀跳变
4. 切换到夜间主题(比如`deepNight`),触发`farOrbit`,截图确认跟改动前行为一致(不受这次远景专属光照/角度逻辑影响)
5. 播放中正常触发这几个远景构图(如果`cameraGrammarAuto`候选目前会用到`farOrbit`,确认自动播放场景下也正常),确认无冻结、控制台无新增报错

## 验证方式

1. 白天主题下(至少测noon+另一个主题),远景构图截图对比明显更有立体感/方向光效果
2. 近景构图(`homeGlobe`/`portraitMarble`等)不受影响,光照/角度逻辑没有变化
3. 夜间主题下远景构图行为不受影响
4. 远景↔近景来回切换多次,光照过渡平滑,无跳变、无残留错误状态
5. 控制台无新增报错
