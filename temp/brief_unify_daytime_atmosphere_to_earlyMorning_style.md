# 统一设计:白天四个主题的atmosphere关掉,以earlyMorning为模板,只保留rimGlow这一层

本轮阶段:设计统一(小改动,明确范围)
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件
允许 commit:否,除非我后续明确批准

---

## 背景

`earlyMorning`主题的`atmosphere.opacity`一直是`0.0`(代码注释标注"定版 2026-07-03"，只用rimGlow/Rim Overlay做边缘光，效果是一条干净的细线)。而`morning`/`noon`/`afternoon`/`goldenApproach`这四个主题的`atmosphere.opacity`在更早的"视觉升级第一批"里被从`0.0`改成了`0.09~0.10`（配合power从16降到6），这四个主题现在是`atmosphereMaterial` + `rimGlow`两层叠加，看起来比`earlyMorning`厚很多。

用户决定：以`earlyMorning`为模板统一风格——**这四个主题的`atmosphere.opacity`改回`0.0`**，只保留`rimGlow`这一层，保持清爽简洁的设计。

## 要做的事

把`morning`(`earth3d.js`附近4295行开始的主题块)/`noon`/`afternoon`/`goldenApproach`这四个主题各自的`atmosphere.opacity`，从当前值改回`0.0`：

```js
atmosphere: {
  color: '#f7feff',
  colorOuter: '#9fd7ff',
  radius: 2.04,
  opacity: 0.0,   // 改回0.0，跟earlyMorning统一，只用rimGlow做边缘光
  power: 6.0,        // power/powerOuter/strengthOuter这几个数值不用改，opacity=0时它们不产生实际效果，保留即可
  powerOuter: 3.0,
  strengthOuter: 0.12,
},
```

**只改`opacity`这一个字段，改成`0.0`**。`power`/`powerOuter`/`strengthOuter`/`color`/`colorOuter`/`radius`都不用动（opacity为0时这些值不影响任何视觉效果，没必要跟着改，保留现状即可，减少改动范围）。

## 严格边界

**只允许改动**：`morning`/`noon`/`afternoon`/`goldenApproach`四个主题各自`atmosphere.opacity`字段的数值，改成`0.0`。

**禁止改动**：
- `rimGlow`相关的任何配置或代码(`_emRimOverlayMat`/`_emInnerVeilMat`/`RIM_BOOST_COMPOSITIONS`等)——这套本来就该保留，是现在唯一的边缘光来源
- `atmosphere2`(远景构图BackSide整圈辉光)相关的任何代码——这是完全独立的机制，`toAtm2Opacity`等逻辑引用的是`themeCfg.atmosphere2`（不是`themeCfg.atmosphere`），这次改动不会影响它，但请确认一下代码里没有意外的交叉引用
- `earlyMorning`主题本身的任何配置——它已经是目标模板，不用动
- 夜间主题(`evening`/`lateEvening`/`deepNight`/`night`)——不在这次范围内

## 完成后请提供

1. git diff（应该只有4处`opacity`数值改动）
2. 四个白天主题（morning/noon/afternoon/goldenApproach）homeGlobe默认视角截图，对比`earlyMorning`确认风格统一（只有细线状rimGlow边缘光，不再有加厚的atmosphere柔光）
3. 确认远景构图(`farOrbit`等)的`atmosphere2`整圈辉光不受影响，行为跟改动前一致
4. 确认夜间主题不受影响
5. 控制台无新增报错

## 验证方式

1. 白天四个主题的homeGlobe视角，边缘光风格跟earlyMorning一致（细线状，无加厚感）
2. 远景构图的atmosphere2整圈辉光效果不受影响
3. 夜间主题、其余候选不受影响
4. 控制台无新增报错
