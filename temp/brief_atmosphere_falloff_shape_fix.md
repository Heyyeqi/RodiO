# 地球视觉升级 大气光晕:修正渐变形状(power过高导致"硬边光圈"而非柔和过渡)

本轮阶段:直接修复,已用Theme Tuner实时验证过数值
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件
允许 commit:否,除非我后续明确批准

---

## 背景

上一轮把四个白天主题的`atmosphere.opacity`从`0.0`改成`0.09-0.10`,用户线上实测后反馈:辉光看起来还是不自然,像"贴了一圈硬边白圈",不是参考图那种柔和渐变扩散的效果。

我重新在Preview里排查,读了shader代码(`_atmFrag`,`earth3d.js:2098-2127`)后发现真正的问题**不是opacity不够,而是`power`/`powerOuter`这两个衰减指数太高**:

```glsl
float fresnel = 1.0 - abs(dot(vNormal, vViewDir));
float core  = pow(fresnel, uPower) * uOpacity;
float outer = pow(fresnel, uPowerOuter) * uStrengthOuter * uOpacity;
```

四个白天主题现在的`power: 16.0`是一个非常陡峭的指数——意味着只有`fresnel`（视线与法线夹角）几乎贴到90°（正好是地球轮廓边缘那一圈极窄范围）时,亮度才会显著上升,稍微往内一点就迅速掉到接近0。这在视觉上表现为"边缘一圈很窄的亮线/硬边光圈",跟真实大气散射"从边缘往内大范围柔和过渡、逐渐消失"完全不是一回事。单纯调`opacity`只能调这圈硬边的亮度,调不出渐变宽度,所以怎么调都还是"一圈"而不是"一片柔光"。

我已经用`window.earth3d.patchTheme(themeName, {atmosphere:{power,powerOuter,strengthOuter,opacity}})`在Preview里实时测试过,把`power`从16降到6、`powerOuter`从5.2降到3、`strengthOuter`从0.18降到0.12,配合opacity在noon(阳光最强)和afternoon两个主题上都验证过——效果是明显更宽、更柔和的渐变光晕,边缘不再是硬圈,也没有过曝发白。这次要把这组修正后的数值正式写进代码,**覆盖/取代上一轮的opacity数值**。

## 现状(已核实)

`THEME_VISUAL_CONFIG`(`earth3d.js`)四个白天主题当前(上一轮改完后)的`atmosphere`:

```js
atmosphere: {
  color: '#f7feff',
  colorOuter: '#9fd7ff',
  radius: 2.04,
  opacity: 0.10,   // noon是0.09，其余三个是0.10（上一轮改的）
  power: 16.0,      // ← 这次要改
  powerOuter: 5.2,  // ← 这次要改
  strengthOuter: 0.18,  // ← 这次要改
},
```

四个白天主题(`morning`/`noon`/`afternoon`/`goldenApproach`)行号仍是之前确认过的（约`4310`/`4411`/`4511`/`4615`附近，如果上一轮改动导致行号有±几行偏移，以实际`grep`结果为准）。

## 要做的事

把四个白天主题的`atmosphere`改成:

```js
atmosphere: {
  color: '#f7feff',
  colorOuter: '#9fd7ff',
  radius: 2.04,
  opacity: 0.10,        // noon保持0.09(已验证)，morning/afternoon/goldenApproach保持0.10(已验证)——这个字段这次不用再变
  power: 6.0,           // 从16.0改
  powerOuter: 3.0,      // 从5.2改
  strengthOuter: 0.12,  // 从0.18改
},
```

即:`opacity`维持上一轮的数值不变(noon=0.09，其余=0.10)，这次只改`power`/`powerOuter`/`strengthOuter`这三个衰减/混合参数，四个白天主题使用同一组新数值。

`color`/`colorOuter`/`radius`不变。`rimGlow`/`clouds`/`lighting`/`nightGrade`/夜间主题/shader代码本身，这次依然不碰。

## 严格边界

**只允许改动**:四个白天主题各自`atmosphere`里的`power`/`powerOuter`/`strengthOuter`这三个数值。

**禁止改动**:`opacity`/`color`/`colorOuter`/`radius`;`rimGlow`/`clouds`/`lighting`(尤其`sun`强度)/`nightGrade`/`texture`等其他所有配置字段;夜间主题的任何内容;`_atmVert`/`_atmFrag`shader代码本身;Camera Grammar相关的任何代码。

## 完成后请提供

1. git diff
2. 四个白天主题各一张改动后的截图(可以用`window.earth3d.patchTheme(themeName, {atmosphere:{power:16.0, powerOuter:5.2, strengthOuter:0.18}})`临时切回旧值拍"改动前"对比图,不需要真的回退代码)

## 验证方式

1. 依次切换四个白天主题,确认地球边缘的光晕是"宽范围柔和渐变扩散",不再是"贴着轮廓的一圈硬边亮线",且不过曝发白
2. 切换到夜间主题,确认不受影响
3. `?earthCandidate=cameraGrammarV1`/`cameraGrammarAuto`等候选,确认相机构图/运动逻辑不受影响
4. 控制台无新增报错
