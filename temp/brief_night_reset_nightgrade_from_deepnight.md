# night主题:nightGrade整块替换成deepNight的数值(绕开具体bug,重置到已验证的基线)

本轮阶段:直接实施(不再继续深挖_deMagenta的具体数学问题，改用"已验证基线覆盖"的方式)
允许修改文件:仅 `pwa/earth3d.js`
允许 commit:否，除非我后续明确批准

---

## 背景

`_deMagenta`这个bug排查了好几轮，上一次的"单次smoothstep"修复没有解决问题。这次改变策略：不再继续深挖具体是哪个数学细节触发的，而是**把night的`nightGrade`配置整块替换成deepNight已验证没有这个问题的数值**，其余属于night自己"身份特征"的参数（主题时段、城市灯光颜色/强度、云层、星空、rimGlow等）保持不变。

## 现状(已核实两者当前完整数值)

**night当前的`nightGrade`**(`earth3d.js:5264-5289`)：
```js
nightGrade: {
  daybaseMode: true,
  nightExposure:    0.055,
  nightSaturation:  0.535,
  nightGamma:       0.87,
  nightBlueBias:    0.0295,
  nightGreenBias:   0.0025,
  nightRedReduce:   0.023,
  oceanBlendStrength: 0.63,
  oceanDarken: 1.325,
  oceanContrast: 1.01,
  oceanSaturation: 0.545,
  oceanBlueBias: 0.0055,
  oceanRedReduce: 0.05,
  oceanGreenReduce: 0.0,
  coastProtection: 0.685,
  tropicalDarken:      0.62,
  tropicalGreenReduce: 0.0,
  aridDarken:          0.58,
  aridWarmReduce:      0.25,
  iceNeutralize:       1.0,
  oceanLift: 0.008, oceanLiftTint: [0.13, 0.39, 0.71], oceanTeal: 0,
  landLift: 0.035, landGamma: 0.85, landStr: 0, landRedRed: 0.025, landGreenB: 0.045, landGlowStr: 0,
  cityLumLow:  0.0135,
  cityLumHigh: 0.089,
},
```

**deepNight的`nightGrade`**(`earth3d.js:5142-5199`，已确认没有菱形纹路问题)：
```js
nightGrade: {
  daybaseMode: true,
  nightExposure:    0.050,
  nightSaturation:  0.52,
  nightGamma:       0.86,
  nightBlueBias:    0.028,
  nightGreenBias:   0.002,
  nightRedReduce:   0.024,
  oceanBlendStrength: 0.60,
  oceanDarken: 1.10,
  oceanContrast: 1.01,
  oceanSaturation: 0.54,
  oceanBlueBias: 0.005,
  oceanRedReduce: 0.05,
  oceanGreenReduce: 0.0,
  coastProtection: 0.68,
  oceanRawMix: 0.30,
  oceanRawExposure: 0.026,
  oceanRawBlueKeep: 0.32,
  tropicalDarken:      0.62,
  tropicalGreenReduce: 0.0,
  aridDarken:          0.58,
  aridWarmReduce:      0.25,
  iceNeutralize:       1.0,
  oceanLift: 0.005, oceanLiftTint: [0.13, 0.39, 0.72], oceanTeal: 0,
  landLift: 0.035, landGamma: 0.85, landStr: 0, landRedRed: 0.025, landGreenB: 0.045, landGlowStr: 0,
  cityLumLow:  0.016,
  cityLumHigh: 0.092,
},
```

**注意**：deepNight的`nightGrade`比night多3个字段（`oceanRawMix`/`oceanRawExposure`/`oceanRawBlueKeep`），night当前没有这几个字段——这次一起补上，让night的`nightGrade`跟deepNight完全一致。

## 要做的事

把`night`主题(`earth3d.js:5264`附近)的`nightGrade`对象，**整块替换成上面deepNight的`nightGrade`完整内容**（一字不改，直接照抄deepNight的这十几行）。

night配置里**其余部分完全不动**：`themeHour: 21.75`、`texture`（`emissiveColor: 0xFFB26E`/`emissiveIntensity: 0.72`）、`material`、`atmosphere`、`rimGlow`、`lighting`（`stars: 0.74`/`cityLightsOpacity: 0.435`/`cityLightClamp: 0.68`）、`horizonGlow`、`clouds`、`starSphereOpacity: 0.39`——这些都是night自己的"身份特征"，保持原样不要碰。

## 严格边界

**只允许改动**：`night`主题的`nightGrade`对象整体替换为deepNight的`nightGrade`内容。

**禁止改动**：`night`配置里其余任何字段；`deepNight`主题本身的任何配置（只是拿它的数值来抄，不要改deepNight自己）；其余任何代码逻辑。

## 完成后请提供

1. git diff（应该只有`night`主题`nightGrade`对象内部的替换）
2. `night`主题下，之前出现菱形纹路的同一构图/视角截图，确认纹路是否消失
3. `night`主题整体色调截图（陆地+海洋+城市灯光），确认没有因为这次替换出现新的色偏问题（比如城市灯光暖色调、整体亮度是否还保持night原本该有的"比deepNight亮一点"的过渡感）
4. 确认`noon`/`deepNight`/其余主题不受影响
5. 控制台无新增报错

## 验证方式

1. night主题菱形纹路消失
2. night主题整体观感依然保持自己的身份特征（不会看起来跟deepNight完全一样，emissive/云层/星空等这些没变的部分还在）
3. 其余主题不受影响
4. 控制台无新增报错
