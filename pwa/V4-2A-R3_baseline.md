# RodiO V4-2A-R3 基线快照

**锁定时间**: 2026-07-08
**锁定范围**: evening (20.2h) / lateEvening (21.0h) / deepNight (22.5h)
**状态**: 视觉验收通过

---

## 三时段对比

| 参数 | evening (20.2h) | lateEvening (21.0h) | deepNight (22.5h) |
|---|---|---|---|
| **Sky top** | #020914 | #01060D | #010409 |
| **Sky horizon** | #0D2740 | #071525 | #041020 |
| **Sky bottom** | #07182A | #040C16 | #030a14 |
| **emissiveColor** | 0xFFC477 | 0xFFB85C | 0xFFA22E |
| **emissiveIntensity** | 0.68 | 0.86 | 0.92 |
| **rimGlow outer.color** | #6FA6D6 | #7198B5 | #7F9DB4 |
| rimGlow outer.colorNear | #D4ECFF | #D0E4EE | #d8e4ec |
| rimGlow outer.coreStrength | 0.66 | 0.74 | 0.82 |
| rimGlow outer.haloStrength | 0.24 | 0.20 | 0.18 |
| rimGlow inner.color | #8ABCE8 | #9BBED4 | #9fd0ff |
| rimGlow inner.strength | 0.28 | 0.32 | 0.40 |
| **nightExposure** | 0.078 | 0.060 | 0.050 |
| nightSaturation | 0.58 | 0.55 | 0.52 |
| nightGamma | 0.94 | 0.88 | 0.86 |
| nightBlueBias | 0.035 | 0.031 | 0.028 |
| nightGreenBias | 0.004 | 0.003 | 0.002 |
| nightRedReduce | 0.018 | 0.022 | 0.024 |
| **oceanBlendStrength** | 0.62 | 0.66 | 0.69 |
| **oceanDarken** | 1.28 | 1.55 | 1.75 |
| oceanSaturation | 0.56 | 0.55 | 0.54 |
| oceanBlueBias | 0.007 | 0.006 | 0.005 |
| oceanLift | 0.012 | 0.011 | 0.010 |
| oceanLiftTint | [0.12,0.38,0.68] | [0.13,0.39,0.70] | [0.13,0.39,0.72] |
| coastProtection | 0.70 | 0.69 | 0.68 |
| **cityLightClamp** | 0.74 | 0.71 | 0.68 |
| cityLumLow | 0.014 | 0.013 | 0.012 |
| cityLumHigh | 0.095 | 0.088 | 0.080 |
| **stars** | 0.38 | 0.66 | 0.82 |
| **starSphereOpacity** | 0.18 | 0.34 | 0.45 |
| **clouds** | 0.025 | 0.020 | 0.015 |
| **OCEAN_TINT color** | 0x041827 | 0x03131D | 0x031018 |
| **OCEAN_TINT strength** | 0.028 | 0.025 | 0.022 |

## 不变项（三时段一致）

- material: specular 0x000001, shininess 0.08
- atmosphere: color #d8f4ff, opacity 0.0, power 14.0
- horizonGlow: enabled=false
- rimGlow width/coreFraction/tailPower: 0.10/0.34/2.8
- surface suppression: tropicalDarken 0.62, aridDarken 0.58, aridWarmReduce 0.25, iceNeutralize 1.0

## 渲染白名单

RIM_OVERLAY_THEMES: `['earlyMorning', 'deepNight', 'evening', 'lateEvening']`

## 验收结论

- evening: 蓝色时刻，地表/海水可见，城市灯光开始主导
- lateEvening: 入夜过渡，比 evening 更暗，灯光和星场增强
- deepNight: 最暗锚点，灯光和星场最强
- 输出截取的图直接使用，无需重截，因为 RDL 404 不影响主视觉
