# 地球视觉升级 第一批:白天主题大气光晕重新调参

本轮阶段:生成候选(直接修复,已用Theme Tuner实时验证过数值方向)
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件
允许 commit:否,除非我后续明确批准

---

## 背景

用户对比当前渲染和参考图(柔和大气光晕/云层/太阳光斑的照片级效果),指出现在的地球看起来"不够成熟"。排查发现:白天四个主题(`morning`/`noon`/`afternoon`/`goldenApproach`)的`atmosphere.opacity`**全部是`0.0`**,完全禁用。之前(2026-06-07)有过一次专项审计(`docs/e1_r1a_photorealism_anti_cartoon_audit.md`),当时认为大气层"太强"(opacity 0.14 太亮),但后来被直接调成了完全禁用,矫枉过正了。

我已经用`window.earth3d.patchTheme('noon', {atmosphereOpacity: X})`在Preview里实时测试过0.10和0.16两个值,效果都是"地球边缘出现柔和蓝色光晕,不过曝发白",方向是对的。这次要把测试过的合理数值正式写进代码。

## 现状(已核实)

- `THEME_VISUAL_CONFIG`(`earth3d.js:3744`起)的`morning`(`4293`)/`noon`(`4394`)/`afternoon`(`4494`)/`goldenApproach`(`4593`)四个白天主题,`atmosphere`配置结构完全一致:
  ```js
  atmosphere: {
    color: '#f7feff',
    colorOuter: '#9fd7ff',
    radius: 2.04,
    opacity: 0.0,     // ← 这次要改的字段
    power: 16.0,
    powerOuter: 5.2,
    strengthOuter: 0.18,
  },
  ```
- 只有`opacity`字段需要改,`color`/`colorOuter`/`radius`/`power`/`powerOuter`/`strengthOuter`这几个不用动
- 大气层是独立于`rimGlow`的另一套系统(Fresnel边缘光shader,`_atmVert`/`_atmFrag`,`earth3d.js:2082-2127`附近),`rimGlow`配置保持不变,这次不碰

## 要做的事

把四个白天主题的`atmosphere.opacity`从`0.0`改成:

- `noon`(`earth3d.js:4411`附近):`0.09`(正午阳光最强,保守一点)
- `morning`(`earth3d.js:4310`附近):`0.10`
- `afternoon`(对应`earth3d.js:4494`区块内的atmosphere):`0.10`
- `goldenApproach`(对应`earth3d.js:4593`区块内的atmosphere):`0.10`

(这几个数值是我实测验证过方向正确的起点,不是精确到小数点后必须一模一样——如果你在实现时视觉检查发现某个主题看起来偏亮/偏暗,可以在0.06-0.12这个区间内小幅微调,但不要超出这个区间,超出的话请截图告诉我而不是自己决定用更极端的值)

只改这一个字段,其余`atmosphere`子字段、`rimGlow`、`lighting`、`clouds`等配置全部保持不变。

## 严格边界

**只允许改动**:四个白天主题各自`atmosphere.opacity`这一个数值。

**禁止改动**:`rimGlow`/`clouds`/`lighting`(尤其`sun`强度)/`nightGrade`/`texture`等其他所有配置字段;夜间主题(`deepNight`/`lateEvening`/`evening`/`night`)的任何内容;`_atmVert`/`_atmFrag`shader代码本身;Camera Grammar相关的任何代码。

## 完成后请提供

1. git diff
2. 四个白天主题各一张切换前后的对比截图(可以用`window.earth3d.patchTheme(themeName, {atmosphereOpacity: 0})`临时切回0来拍"改动前"对比图,不需要真的回退代码)

## 验证方式

1. 依次切换四个白天主题(Theme Tuner的Mode下拉),确认地球边缘出现柔和的大气光晕,不发白过曝
2. 切换到夜间主题(deepNight等),确认不受影响
3. `?earthCandidate=cameraGrammarV1`/`cameraGrammarAuto`等候选,确认相机构图/运动逻辑不受影响(这次改动跟相机系统完全独立)
4. 控制台无新增报错
