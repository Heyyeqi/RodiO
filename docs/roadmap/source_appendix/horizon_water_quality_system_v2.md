# Horizon Mode — 水质参数化系统技术方案 v2（数据驱动 + 系统性审计）

> 升级版 · 对应 issue #41（Phase 3/#44 实际落地）
> 状态: 技术方案 + 数据驱动参考实现（`water_params_reference.js`，已用 5 个真实海洋站位验证）+ 系统性审计 + 跨子系统耦合规范
> 前版: `horizon_water_quality_system_v1.md`（9 维 / 11 预设 / 纯手编）

---

## 〇、v1 → v2 升级摘要

| 项 | v1 | v2 |
|---|---|---|
| 维度来源 | 手编预设值 | **Copernicus 海洋色 → 4 项 IOPs → 9 维** 反演 |
| 颜色维度色空间 | 未声明（隐含 sRGB，深度渐变直接 `mix` → 色相漂移风险） | **强制 OKLab 路径**（sRGB 存储 → linear → OKLab；深度渐变在 OKLab 内插值） |
| 标量维度单位 | 无量纲 `[0,1]` | **锚定物理量**（ZSD/m、SPM/g·m⁻³、KD490/m⁻¹、风速/m·s⁻¹） |
| 跨子系统耦合 | 仅文字提及 | **显式耦合公式**（foam↔specular、tint↔sky、water↔terrain、turbidity↔散射相函数） |
| 数据支撑 | 依赖设计者经验 | **Copernicus-GlobColour 全球 4km 日/月产品**（1997–今）可规模化驱动 |
| 验证 | 无 | 5 真实站位反演，与 v1 手编预设对标（见第四节 + `figures/water_validation.png`） |

**核心结论**：v1 的 9 维接口与 11 预设在 v2 中被证明是**数据可还原**的——每个预设都能反推为一组 (CHL, SPM, ZSD, wind) 元组（见第五节），说明 v1 的"策展样本"选点准确；v2 把它们升级为可由真实地理数据即时生成的连续场。

---

## 一、数据驱动管线

```
[Copernicus-GlobColour]                [气象/地形]
 CHL  chlorophyll-a  mg·m⁻³             wind  风速 m·s⁻¹ ──┐
 SPM  suspended matter g·m⁻³           bathy GEBCO 水深 ──┤
 ZSD  Secchi depth m   (或 KD490)                        ├─→  deriveWaterParams()
 CDM  a_cdom@440 m⁻¹                                     │
 RRS  remote sensing reflectance 光谱 ┘                 │
        │                                                        │
        ▼  IOP 反演（4 项模型）                                  │
 a(λ)=a_w + a_phy(CHL) + a_cdom(CDM/SPM) + a_det(SPM)          │
 b_b(λ)=b_bw + b_bp(SPM)                                        │
        │                                                        │
        ▼  9 维映射                                              ▼
 clarity · turbidity · baseColorDeep · baseColorShallow ·
 substrateColor · depthColorFalloff · surfaceRoughness ·
 foamCoverage · colorTint
```

### 1.1 IOP 反演（4 项模型，波长 443/490/510/555/650 nm）

纯水项用 Pope & Fry (1997) 光谱；生物/颗粒项用经验反演（Bricaud 1998、Morel/Maritorena 量级）：

| IOP | 公式（CHL/SPM 为输入） | 物理含义 |
|---|---|---|
| 浮游植物吸收 `a_phy(443)` | `0.06 · CHL^0.65` | 色素吸收，光谱 `exp(-0.015·(λ-443))` |
| CDOM 吸收 `a_cdom(440)` | `0.01·CHL^0.5 + 0.01·SPM^0.6`（或直接给 CDM） | 有色溶解有机物，光谱 `exp(-0.014·(λ-440))` |
| 碎屑吸收 `a_det(440)` | `0.02 · SPM^0.7` | 矿物/有机碎屑，光谱 `exp(-0.011·(λ-440))` |
| 颗粒后向散射 `b_bp(555)` | `0.0025 · SPM^0.9` | 悬浮颗粒散射，光谱 `(550/λ)^0.8` |

> 参考实现：`water_params_reference.js` 的 `computeIOPs()`。常数可在集成时按区域标定（如河口 b_bp 斜率更高）。

### 1.2 9 维映射（物理锚定）

| 维度 | 反演公式 | 物理锚点 |
|---|---|---|
| **clarity** | `ZSD/(ZSD+8)`（ZSD 缺则 `1.7/KD490` 反推） | Secchi 深度：河口 0.5m→0.06，热带 30m→0.79 |
| **turbidity** | `1 - exp(-SPM/18)` | 悬浮物：清澈 0.1→0.01，河口 200→1.0 |
| **baseColorDeep** | 深水反射率 `Rrs≈0.33·b_b/(a+b_b)` → 取 RGB 波段色度 → OKLab 色相；**亮度 L 用艺术曲线** `0.35+0.32·murk`（清晰→深蓝，浑浊→乳白） | 色相由 IOP 光谱比决定（蓝/绿/棕） |
| **baseColorShallow** | `baseColorDeep` 提亮 + `substrateColor` 按 `clarity·0.5` 渗透 | 浅水区水柱透射 + 底质反射 |
| **substrateColor** | 优先 `GEBCO/GEOSEABED`；缺省启发式（SPM>5→淤泥；clarity>0.75→白沙；否则灰岩） | 底质分类 |
| **depthColorFalloff** | `0.4 + (KD490-0.02)·2.4` | KD490：清澈 0.03→0.4，河口 2.5→2.5 |
| **surfaceRoughness** | `(wind-2)/16` | 风速：2→0（镜面），18→1（破碎波） |
| **foamCoverage** | `(wind-7)/13 · 0.42` | 白冠分数：7m/s 起，20m/s→0.42 |
| **colorTint** | 浮游植物主导(CHL>1 且 SPM<10·CHL)→绿推；强 CDOM 河流染色→棕推 | 藻华 / 河流染色事件 |

> **关键设计判断**：`baseColorDeep` 的**色相**完全由 IOP 光谱比物理决定（这是"诗意表达的真实"根基）；**亮度/彩度**用艺术曲线，因为纯反射率亮度不等于人眼感知的深水色。这是 v2 相对"纯物理渲"的务实折中——色相不可妥协地真实，亮度服务于画面。

---

## 二、系统性审计

### 2.1 色彩空间：OKLab 强制路径

v1 把颜色维存为 `[0,1]³` 但**未声明色空间**，且 D6 的深度渐变 `mix(baseColorShallow, baseColorDeep, df)` 在存储空间直接插值——若存的是 sRGB，蓝→白中点会发紫（色相漂移），违背"克制"。

**v2 规则（shader 必须遵守）**：

```
1. 所有颜色维度以 sRGB 存储（设计者可读写）。
2. 使用前: sRGB → linear (pow 2.2 或精确 sRGB→linear)。
3. 深度渐变 D6 必须在 OKLab 内插值:
     okS = lin2oklab(srgb2lin(baseColorShallow))
     okD = lin2oklab(srgb2lin(baseColorDeep))
     okMix = mix(okS, okD, df)          // L/a/b 各通道线性插值
     body = lin2srgb(oklab2lin(okMix))
4. 输出前 OKLab → linear → sRGB。
```

OKLab 转换函数见 `water_params_reference.js`（`linToOKLab` / `oklabToLin`，Björn Ottosson 标准系数）。**益处**：蓝→白渐变保持干净的"带雾蓝"而非脏紫；多光源/天色混合也在感知均匀空间进行。

### 2.2 单位归一与范围（每维硬约束）

| 维度 | 物理锚点 | 归一/映射 | 着色器硬范围 |
|---|---|---|---|
| clarity | ZSD / KD490 | `ZSD/(ZSD+8)` | `[0,1]` |
| turbidity | SPM | `1-exp(-SPM/18)` | `[0,1]` |
| baseColorDeep/Shallow | IOP→OKLab | 艺术 L/C 曲线 | sRGB `[0,1]³` |
| substrateColor | 底质分类 | 查表/启发式 | sRGB `[0,1]³` |
| depthColorFalloff | KD490 | `0.4+(KD490-0.02)·2.4` | `[0.3, 2.5]` |
| surfaceRoughness | 风速 | `(wind-2)/16` | `[0,1]` |
| foamCoverage | 风速(白冠) | `(wind-7)/13·0.42` | `[0, 0.42]` |
| colorTint | CHL 异常/CDOM | 事件触发 | `[0.5, 1.5]³` |

**审计发现（v1 模糊点已修复）**：
- D1/D2 原无量纲 → 现锚定 ZSD/SPM，可回归物理校验。
- D3/D4 原"按项目约定 sRGB 或 linear" → 现强制 sRGB 存储 + OKLab 插值。
- D7/D8 原无数据来源 → 现锚定风速（与气象系统对接，非海洋色）。
- D9 原仅"架构预留" → 现含可触发的数据逻辑（藻华/河流染色）。

### 2.3 色彩一致性自查（对标美学基调）

- 所有颜色统一走 OKLab → 同色温混合，避免"精修感"的脏色相漂移。
- 亮度曲线 `murk` 驱动 → 浑浊水自然更亮更乳白（符合"克制"而非高饱和戏剧化）。
- colorTint 仍为乘法器（v1 架构预留保留），但**有理触发**（非任意）。

---

## 三、跨子系统耦合规范

> 约束（来自 `C_Sky_Design_v3.2.md` §10.4）：海洋高光保持 **`MeshPhongMaterial` + `specularMap`**，**不得引入 PBR `roughnessMap`/`metalness`**。以下耦合均在此前提下实现。

### 3.1 foamCoverage ↔ 海洋高光（specularMap）

泡沫是白色、粗糙、破坏镜面。耦合：
```
// specularMap 控制高光强度; 泡沫区局部覆盖
float foamMask = noiseFoam(uv, time) * foamCoverage;
vec3 specular = phongSpec * specularMap * (1.0 - foamMask);   // 泡沫抑制镜面
finalColor = mix(finalColor, vec3(0.96), foamMask * 0.9);     // 泡沫叠加白色漫反射
```
- 泡沫区 `specular` 趋零，代之以漫白 → 与 `specularMap` 共存不冲突。
- 不引入 roughnessMap（保持 MeshPhong）。

### 3.2 colorTint ↔ 天色 LUT（sky reflection）

水面反射天空；染色水染其反射。耦合：
```
vec3 skyRefl = skyLUT(reflect(viewDir, normal));   // C_Sky_Design 天色 LUT
vec3 waterRefl = mix(skyRefl, skyRefl * colorTint, tintStrength); // 染色水调其反射
finalColor += waterRefl * fresnel;
```
- 赤潮/藻华时，水面反射的天空也被染 → 整体协调（避免"水绿天蓝"割裂）。
- `tintStrength` 由 `colorTint` 偏离 `(1,1,1)` 的程度决定。

### 3.3 water ↔ terrain（GEBCO 底质/水深）

- `substrateColor` 由 GEBCO 水深 + 区域底质分类（GEOSEABED 若有）驱动 per-pixel；未接入前用 v2 启发式。
- `depthColorFalloff` / `clarity` 与**实际 GEBCO 水深**联动：深水区即使清澈也快速趋深蓝（P6 深海模式由 bathymetry 触发，非仅海洋色）。
- 与 `horizon_terrain_detail_noise_v1.1.md` 的 GEBCO 校准共用同一底质/水深源。

### 3.4 turbidity ↔ 散射相函数

高 turbidity → 颗粒浓度高 → 散射更趋各向同性（前向峰变钝）：
```
float phase = mix(henyeyGreenstein(g=0.8), 0.25, turbidity); // 浑浊→更均匀散射
vec3 sss = uScatterColor * turbidity * phase * (1.0 - abs(dot(viewDir,normal)));
```
- 浑浊水近表面"乳白雾化"由此自然增强，与 D2 语义一致。

---

## 四、参考实现与验证

参考实现 `water_params_reference.js`（CommonJS，无依赖）含 `deriveWaterParams()`，已用 5 个真实海洋站位反演：

| 站位 | clarity | turbidity | falloff | rough | foam | deep 色相 | 对标 v1 |
|---|---|---|---|---|---|---|---|
| S1 远洋寡营养 | 0.79 | 0.01 | 0.42 | 0.13 | 0 | 214° 蓝 | P2 |
| S2 热带珊瑚礁 | 0.81 | 0.00 | 0.41 | 0.06 | 0 | 224° 蓝 | P1 |
| S3 温带开阔 | 0.69 | 0.02 | 0.54 | 0.38 | 0.03 | 186° 青 | P3 |
| S4 长江口浑浊 | 0.06 | 1.00 | 2.50 | 0.25 | 0 | 68° 棕 | P4 |
| S5 波罗的海藻华 | 0.27 | 0.11 | 1.79 | 0.31 | 0 | 81° 绿 + 绿 tint | P7/P11 |

**标量维度**模型值与 v1 手编预设高度一致（见 `figures/water_validation.png` 上表）；**baseColorDeep** 色相/亮度与 v1 同族（模型略亮，更适合 Horizon 仰视/平视观感）。

**验证结论**：
1. 色相物理正确：清澈→蓝、浮游植物→绿、CDOM/碎屑→棕，全部由 IOP 光谱比自动涌现。
2. 透明度/浑浊度/衰减/风成项全部锚定真实物理量，量级合理。
3. 河口(S4)与藻华(S5)**正确分化**：S4 褐变来自碎屑物理（colorTint 中性），S5 绿推来自浮游植物主导（colorTint 绿）——未把两者混淆。

---

## 五、11 预设的"数据锚点"重释

v1 的 11 预设在 v2 中可表示为 (CHL, SPM, ZSD, wind, [substrate]) 元组，由数据驱动系统即时生成：

| 预设 | CHL | SPM | ZSD | wind | substrate | 触发说明 |
|---|---|---|---|---|---|---|
| P1 珊瑚礁 | 0.04 | 0.02 | 35 | 3 | 白沙/珊瑚 | 极清澈 + 亮底 |
| P2 热带深水 | 0.05 | 0.1 | 30 | 4 | 深海 | 清澈但无底 |
| P3 温带 | 0.2 | 0.3 | 18 | 8 | 灰沙 | 中浑浊 + 风浪 |
| P4 河口 | 5 | 200 | 0.5 | 6 | 淤泥 | 极端 SPM |
| P5 极地 | 0.1 | 0.05 | 25 | 12 | 岩 | 高风 + 冷色调 |
| P6 深海 | 0.03 | 0.02 | ∞(深) | 4 | 深渊软泥 | **bathymetry 触发近黑深蓝** |
| P7 内海 | 0.8 | 2 | 5 | 6 | 淤泥 | 慢性富营养绿 |
| P8 火山黑沙 | 0.05 | 0.05 | 30 | 6 | **黑玄武岩** | 清水 + 黑底（与 P1 仅底质异） |
| P9 潟湖 | 0.03 | 0.01 | 40 | 2 | 最白沙 | 极致镜面清澈 |
| P10 季风浑浊 | 1 | 50 | 4 | 10 | 礁/沙覆盖 | P1 站位的雨季变异 |
| P11 藻华 | 15 | 2 | 3 | 6 | 有机质层 | 强 CHL → 绿/红 tint |

> P6 的深渊黑蓝由**水深**（GEBCO bathymetry）而非海洋色触发，体现 water↔terrain 耦合；其余由海洋色 + 风即时反演。

---

## 六、集成指引

| 数据 | 来源 | 备注 |
|---|---|---|
| CHL / SPM / ZSD / KD490 / CDM / RRS | **Copernicus-GlobColour**（Earth Engine 资产，全球 4km，日/月，1997–今） | 按 (lon,lat,date) 取像元；RRS 可直接作 baseColorDeep 真值校验 |
| 风速 / 白冠 | **ERA5**（或本地气象） | 驱动 D7/D8 |
| 底质 / 水深 | **GEBCO**（已校准，见 terrain 文档）+ GEOSEABED(可选) | 驱动 substrateColor / P6 深渊模式 |
| 时间切换 | 同位置不同 date → 不同 CHL/SPM（如 P1↔P10 季风切换） | 无需新代码，仅换 uniform 集 |

集成顺序沿用 v1 路线图（3α/3β/3γ），但 **uniform 值不再手编**，由 `deriveWaterParams()` 在 (lon,lat,date) 解析后填充。

---

## 七、验收标准

- [x] 数据驱动：任意 (CHL,SPM,ZSD,wind) → 9 维，物理锚定
- [x] 审计：颜色维强制 OKLab 路径；标量维锚定物理量；范围硬约束
- [x] 耦合：foam↔specular / tint↔sky / water↔terrain / turbidity↔散射相函数 均有公式
- [x] 验证：5 真实站位反演与 v1 对标通过
- [ ] 集成阶段：Copernicus/ERA5/GEBCO 取数接入主 app（Earth Engine / API）
- [ ] 集成阶段：shader 落地 OKLab 混合 + 耦合公式
- [ ] 集成阶段：per-pixel substrateColor（GEOSEABED 如有）

---

*文档版本: v2 · 2026-07-20*
*维度数: 9 | 预设数: 11（现为数据可还原的连续场）| 参考实现: water_params_reference.js | 验证: figures/water_validation.png + water_validation.json*
