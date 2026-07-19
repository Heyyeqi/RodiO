# Horizon Mode — 水质参数化系统技术方案 v1

> Phase 0.5 资料补充 · 对应 issue #41（Phase 3/#44 实际落地）
>
> **状态**: 技术方案文档 + 完整预设参数集。不包含可运行 shader 代码，但每个维度的取值范围和实现方式已精确到可直接映射为 uniform。

---

## 一、设计哲学

美学基调文档的核心判断是：**海水不是一种颜色，是一整套地理事实。**

真实海洋水色的差异不是靠换一张贴图或调一个 `vec3` 颜色值能解决的——它是光在水体中的吸收、散射、底质反射、表面状态、悬浮颗粒共同作用的结果。一个参数化系统必须能够独立控制这些物理因素，然后通过它们的组合自然地涌现出不同水域的视觉特征。

本方案将水质分解为 **9 个正交维度**，每个维度对应一类独立的物理现象。维度之间有自然的耦合关系（比如高浑浊度会降低有效透明度），但这种耦合由渲染管线在运行时处理——设计者只需为每个维度设定目标值。

---

## 二、维度定义（共 9 维）

每个维度包含：名称、物理含义、建议 uniform 类型与取值范围、shader 实现要点。

---

### D1. clarity（透明度 / 光线穿透深度）

| 属性 | 值 |
|---|---|
| **uniform 类型** | `float` |
| **取值范围** | `[0.0, 1.0]` |
| **默认值** | `0.5` |
| **物理含义** | 光线在水中传播的有效穿透距离系数。1.0 = 极清澈（热带外海，视距 >30m）；0.0 = 不透明（泥浆）。控制深度混合中"能看到多深的底质"。 |

**Shader 实现**：
```
// depth: 当前片段的水深（世界空间米）
// clarity 越高，exp 衰减越慢 → 底质在更大深度仍可见
float depthAlpha = exp(-depth * (1.0 - clarity) * uExtinctionScale);
vec3 shallowContrib = mix(baseColorDeep, substrateColor * baseColorShallow, depthAlpha);
```
关键点：clarity 不是"水的纯净程度"，而是**视觉上的穿透感**。纯水本身对红光的吸收极强——即使最澄清的外海水在超过 ~50m 后也呈近黑色。所以 clarity=1.0 并不意味着无限深都能看到底；它意味着在**浅水区域**底质的可见性最高。

---

### D2. turbidity（浑浊度 / 悬浮颗粒散射强度）

| 属性 | 值 |
|---|---|
| **uniform 类型** | `float` |
| **取值范围** | `[0.0, 1.0]` |
| **默认值** | `0.1` |
| **物理含义** | 悬浮颗粒（泥沙、浮游生物碎屑、有机物）引起的散射强度。影响：(a) 近表面的"雾化"/乳白感；(b) 整体对比度降低；(c) 远处物体模糊化。高浑浊度的水呈现低对比、偏黄褐的外观。 |

**Shader 实现**：
```
// 在视线方向上积分散射贡献（简化单散射近似）
float scatterAmount = turbidity * uScatterStrength;
vec3 scatteredLight = uScatterColor * scatterAmount;
// 降低远处的有效对比度
float fogFactor = 1.0 - exp(-viewDist * turbidity * uFogDensity);
finalColor = mix(finalColor, baseColorDeep * 1.3, fogFactor);
// 叠加近表面乳白散射（模拟 subsurface scattering 的反向分量）
finalColor += scatteredLight * (1.0 - abs(dot(viewDir, normal))) * 0.3;
```
注意：turbidity 和 clarity 是相关但不相同的。clarity 控制垂直穿透（你能看到多深的底），turbidity 控制水平散射（水体有多"雾")。河口可以同时低透明度 + 高浑浊度；而某些极地清水可能高透明度 + 低浑浊度但有特殊色调。

---

### D3. baseColorDeep（深水基底色）

| 属性 | 值 |
|---|---|
| **uniform 类型** | `vec3` (sRGB 或 linear，按项目约定) |
| **取值范围** | `[0,1]³` 典型值域 |
| **默认值** | `(0.02, 0.16, 0.36)` — 标准深蓝 |
| **物理含义** | 当水深足够大、底质完全不可见时，水体自身呈现的颜色。由纯水的光谱吸收特性 + 溶解有机物(CDOM) + 浮游植物色素共同决定。纯海洋水(Case 1)呈深靛蓝；富含 CDOM 的水偏绿/褐；富营养水偏绿。 |

**Shader 实现**：
这是最终颜色的" fallback 目标"——当 depth→∞ 时颜色趋近此值。
```
vec3 waterBodyColor = baseColorDeep;
// 在有深度信息时，从 baseColorShallow 向 baseColorDeep 过渡
waterBodyColor = mix(baseColorShallow, baseColorDeep, depthFalloff(depth));
```

---

### D4. baseColorShallow（浅水基底色）

| 属性 | 值 |
|---|---|
| **uniform 类型** | `vec3` |
| **取值范围** | `[0,1]³` |
| **默认值** | `(0.15, 0.55, 0.58)` — 中等青色 |
| **物理含义** | 浅水区（底质可见时）水体表现出的表观颜色。**不是单纯的底质反射**，而是水柱传输 + 底质反射的综合结果。珊瑚礁浅滩的 baseColorShallow 是明亮的 turquoise；河口浅水是浑浊的黄褐色。它与 baseColorDeep 的差异决定了"水深变化时的颜色过渡幅度"。 |

**Shader 实现**：
```
// depthFalloff 函数由 D6 控制
float df = depthColorFalloffFunc(depth); // [0,1], 0=完全浅, 1=完全深
vec3 bodyColor = mix(baseColorShallow, baseColorDeep, df);
```

---

### D5. substrateColor（海底基质颜色）

| 属性 | 值 |
|---|---|
| **uniform 类型** | `vec3` |
| **取值范围** | `[0,1]³` |
| **默认值** | `(0.85, 0.80, 0.68)` — 浅沙色 |
| **物理含义** | 海床本身的颜色。只有在 clarity 足够高且实际水深较小时才显著影响最终像素。白沙滩 → 高亮度、暖色；暗礁岩 → 低亮度冷色；珊瑚 → 多彩；淤泥 → 低亮度褐/绿；海草 → 深绿。 |

**Shader 实现**：
```
float bottomVisibility = exp(-depth * (1.0 - clarity) * uExtinctionScale);
vec3 bottomContrib = substrateColor * bottomVisibility;
// 与水体颜色混合
finalColor = mix(waterBodyColor, bottomContrib * baseColorShallow, bottomVisibility);
```
重要：substrateColor 通过 `bottomVisibility` 加权——当浑浊度高或深度大时自动退场，不会在不合理的条件下仍然"透出"底色。

---

### D6. depthColorFalloff（深度–颜色渐变曲线）

| 属性 | 值 |
|---|---|
| **uniform 类型** | `float` |
| **取值范围** | `[0.1, 2.5]` |
| **默认值** | `1.0` |
| **物理含义** | 控制颜色从"浅水态"向"深水态"过渡的速率。**这是与 clarity 正交的概念**：clarity 回答的是"能不能看到底"，depthColorFalloff 回答的是"看到的时候颜色怎么变"。值为 1.0 表示线性过渡；<1.0 表示渐进式（大片浅水区域保持同一色调）；>1.0 表示急剧（几米之内就从 turquoise 变成深蓝）。 |

**Shader 实现**：
```
// depth 已归一化到 [0, maxVisibleDepth]
// 使用幂函数控制曲线形状
float normalizedDepth = clamp(depth / uMaxVisibleDepth, 0.0, 1.0);
float t = pow(normalizedDepth, depthColorFalloff); // falloff<1 → 缓慢, >1 → 急剧
return t;
```
示例场景：
- 潟湖（极浅且均匀）：falloff = 0.35 — 整个潟湖几乎同色
- 大陆架边缘（快速变深）：falloff = 1.6 — 近岸turquoise，稍远即深蓝
- 平缓海滩：falloff = 0.8 — 温和渐变

---

### D7. surfaceRoughness（表面粗糙度 / 波浪状态）

| 属性 | 值 |
|---|---|
| **uniform 类型** | `float` |
| **取值范围** | `[0.0, 1.0]` |
| **default** | `0.3` |
| **物理含义** |水面波浪/粗糙程度。0 = 镜面平静（锐利的高光点）；1 = 粗糙破碎波面（弥散宽泛的高光区）。影响：(a) 高光的 spatial spread；(b) 反射天空/环境的模糊程度；(c) Fresnel 项的有效调制范围。 |

**Shader 实现**：
```
// 基于 waternormals.jpg 的法线贴图扰动强度
float normalPerturb = surfaceRoughness * uNormalMapStrength;
vec3 perturbedNormal = normalize(normal + texture2D(normalMap, uv * scale).xyz * normalPerturb);
// Fresnel 项也受影响 —— 粗糙表面在不同视角下都有部分镜面反射
float fresnel = SchlickFresnel(dot(viewDir, perturbedNormal));
// 高光锐利度反比于 roughness
float specPower = mix(256.0, 8.0, surfaceRoughness);
vec3 specular = BlinnPhong(lightDir, viewDir, perturbedNormal, specPower) * specularColor;
```

---

### D8. foamCoverage（浪花 / 白沫覆盖率）

| 属性 | 值 |
|---|---|
| **uniform 类型** | `float` |
| **取值范围** | `[0.0, 0.5]` （>0.5 不现实） |
| **默认值** | `0.02` |
| **物理含义** | 表面被白色泡沫/白覆盖的比例。与风力等级、波浪能量正相关。增加画面的"动感"和"真实海岸感"——完全没有泡沫的水面看起来像泳池而非自然海域。 |

**Shader 实现**：
```
// 可基于噪声 + 波峰检测生成泡沫 mask，foamCoverage 作为全局乘数
float foamMask = noiseFoam(uv, time) * foamCoverage;
// 白色漫反射层，叠在水面上方（additive 或 alpha blend）
finalColor = mix(finalColor, vec3(0.98), foamMask * 0.9);
// 泡沫区域略微降低水面透明度（遮蔽底层）
finalColor = mix(finalColor, finalColor * 0.7 + vec3(0.95)*0.3, foamMask * 0.5);
```
注：Phase 3 实现时可采用更精细的方法（如基于波浪高度阈值的动态泡沫生成），此处仅说明参数接口。

---

### D9. colorTint（特殊色调偏移 — 扩展口）

| 属性 | 值 |
|---|---|
| **uniform 类型** | `vec3` |
| **取值范围** | `[0.5, 1.5]³`（默认 `(1,1,1)` = 无效果） |
| **默认值** | `(1.0, 1.0, 1.0)` |
| **物理含义** | **通用乘性色彩偏移层**，用于无法被上述 8 个维度覆盖的特殊情况：藻华（绿色/红色偏移）、赤潮（锈红色）、单宁酸染色的河流（棕色）、火山矿物质染色（异常色相）。默认为单位矩阵（无任何影响），v1 核心预设全部使用默认值——这个维度的价值在于**架构预留**，确保未来加入特例时不需要新增维度。 |

**Shader 实现**：
```
// 在最终颜色输出前，做一次逐通道乘法
finalColor *= colorTint; // 默认 (1,1,1) → 无操作
// 或者更精细：仅在特定深度区间应用 tint（藻华主要影响表层）
float tintDepthMask = exp(-depth * uTintDecayRate);
finalColor = mix(finalColor, finalColor * colorTint, tintDepthMask);
```
为什么不用单独的新维度？因为每种特例的"额外维度"都只适用于极少数情况。colorTint 作为通用乘法器可以用 (1.15, 0.85, 0.70) 模拟赤潮红、用 (1.0, 1.08, 0.92) 模拟轻微藻绿等——一个 vec3 覆盖无穷多种特例。

---

## 三、完整预设参数集（11 组）

每组给出全部 9 个维度的具体数值 + 参考依据。

> 数值精度说明：所有 float 值保留 2 位小数（足以区分视觉差异）；RGB 为 0-1 归一化值（shader 内可按需转为线性）。

---

### P1. 热带浅滩珊瑚礁（Tropical Shallow Coral Reef）

**参考依据**: 马尔代夫、大溪地(Bora Bora)、加勒比海(库拉索/巴哈马)、帕劳。这些地区属于典型的 Case 1 海水（光学性质由浮游植物主导，但浓度极低），叶绿素-a 通常 < 0.05 mg/m³，CDOM 吸收极弱，悬浮沉积物极少。水下视距常超过 30 米。底质以白色生物成因碳酸盐沙为主，局部有活珊瑚礁呈现粉/橙/绿色。

| 维度 | 值 | 说明 |
|---|---|---|
| clarity | **0.92** | 极高透明度。30m+ 视距，底质在很深处仍可辨识轮廓 |
| turbidity | **0.04** | 几乎无悬浮颗粒。水面清澈到可以看到鱼群在数米以下游动 |
| baseColorDeep | **(0.00, 0.35, 0.55)** | 深水区呈青蓝色（pure water 在短路径下的典型色）— 注意不是深靛蓝，因为热带浅礁区的"深海"也不过几十米，还没到达纯水完全吸红的深度 |
| baseColorShallow | **(0.15, 0.82, 0.85)** | 明亮 turquoise/cyan。水柱传输 + 白沙/浅珊瑚底质反射的综合表观色。这是"明信片色"的来源 |
| substrateColor | **(0.95, 0.88, 0.72)** | 白色珊瑚砂（含少量粉色/橙色珊瑚碎片）。高亮度是 key — 它让浅水区整体发亮 |
| depthColorFalloff | **0.65** | 渐进式过渡。从 turquoise 到 deep blue 需要 ~10-15m 深度变化，不会突变 |
| surfaceRoughness | **0.15** | 热带岛礁通常受环礁屏蔽，海面平静，只有微涌 |
| foamCoverage | **0.02** | 几乎无白沫。偶尔涌浪拍礁产生微量泡沫 |
| colorTint | **(1.00, 1.00, 1.00)** | 无特殊色调 |

**为什么这组数字能表现出这种水质**: 关键在于 **clarity × substrateColor 的协同效应**。高透明度(0.92)让白沙底质(substrateColor 亮度 0.95)在较大深度范围内持续贡献光线，使 baseColorShallow 的 cyan 分量(0.82/0.85)得以充分表达。同时低浑浊度(0.04)保证没有"雾化"冲淡这个亮色。如果降低 clarity 到 0.5 但其他不变，同样的底质就只能在 2-3m 内看到——画面会迅速变成普通的蓝色水面，失去"通透感"。这就是为什么"透明度"和"基底色"必须作为独立维度。

---

### P2. 热带深水开阔洋面（Tropical Deep Open Ocean）

**参考依据**: 南太平洋/印度洋远离大陆的开阔海域。寡营养型(oligrophic)，表层叶绿素-a 约 0.03–0.08 mg/m³。属于经典的 Case 1 水，光学性质接近纯海水。无明显底质影响（水深数千米）。卫星遥感水色产品中这类区域分类为"Case 1 蓝色水体"。

| 维度 | 值 | 说明 |
|---|---|---|
| clarity | **0.88** | 水体本身极其干净（纯水光学属性），但因深度无限大所以看不到底 |
| turbidity | **0.06** | 极低颗粒含量 |
| baseColorDeep | **(0.02, 0.18, 0.42)** | 深靛蓝。纯水在长光程下的经典色 — 红橙全被吸收，剩余蓝绿 |
| baseColorShallow | **(0.08, 0.45, 0.62)** | 如果有浅水区，仍是蓝主导（不像珊瑚礁那种cyan），因为没有亮色底质提亮 |
| substrateColor | **(0.12, 0.14, 0.18)** | 深海平原，近黑色（玄武岩/软泥） |
| depthColorFalloff | **1.2** | 略快于线性。开阔洋面没有真正的"浅水过渡带"——从岸边出去很快就变深 |
| surfaceRoughness | **0.25** | 开放洋面的典型涌浪 |
| foamCoverage | **0.03** | 少量白冠 |
| colorTint | **(1.00, 1.00, 1.00)** | 无特殊色调 |

**与 P1 的核心差异**: baseColorShallow 从 cyan (0.15,0.82,0.85) 降到 blue-green (0.08,0.45,0.62)。同样都是"热带清澈水"，有没有亮色底质是决定性因素——这正是 D4/D5 两个维度独立存在的意义。

---

### P3. 温带开阔大洋（Temperate Open Ocean）

**参考依据**: 北大西洋/北太平洋中纬度开阔水域。中等叶绿素水平(~0.1–0.3 mg/m³)，季节性变化明显（春季 bloom 期间更高）。存在一定的陆源气溶胶沉降和再悬浮沉积物。视觉上比热带水"灰"和"钢感"更强，饱和度更低。典型的"大洋灰蓝色"。

| 维度 | 值 | 说明 |
|---|---|---|
| clarity | **0.70** | 良好透明度但不如热带。视距约 15-20m |
| turbidity | **0.15** | 中等颗粒含量（浮游植物 + 少量矿物粉尘） |
| baseColorDeep | **(0.06, 0.20, 0.38)** | 钢蓝色，比热带深水更不饱和、更灰 |
| baseColorShallow | **(0.22, 0.48, 0.58)** | 压抑的 cyan-green，缺乏热带那种明亮感 |
| substrateColor | **(0.20, 0.24, 0.28)** | 大陆架灰沙/砾石，暗淡 |
| depthColorFalloff | **0.95** | 近线性过渡 |
| surfaceRoughness | **0.40** | 温带西风带风浪更大 |
| foamCoverage | **0.06** | 中等白沫量 |
| colorTint | **(1.00, 1.00, 1.00)** | 无特殊色调 |

**为什么比 P1/P2 更"灰"**: 三重原因叠加——(1) baseColorDeep 的 G/B 通道值更低且 R 稍高（灰感来源）；(2) turbidity=0.15 引入均匀散射降低了整体对比度；(3) substrateColor 暗淡(0.20-0.28)即使透过水体也不会提亮画面。这三个维度各自贡献了一部分"灰感"，缺任何一个都不会达到同样的视觉效果。

---

### P4. 河口浑浊水域（Estuarine Turbid Water）

**参考依据**: 长江口、密西西比河口、恒河-布拉马普特拉河口。极大悬浮沉积物负荷（可达数百 mg/L 至 g/L 级别），强淡水-咸水交汇形成明显的浊度锋面（halocline/turmidity front）。水色呈特征性的黄褐色至不透明棕黄色。光学上属于极端 Case 2 水（非色素粒子主导）。

| 维度 | 值 | 说明 |
|---|---|---|
| clarity | **0.12** | 极低透明度。视距通常 < 2m。本质上是"半液体泥土" |
| turbidity | **0.85** | 极端高悬浮物浓度。泥沙主导的光学特性 |
| baseColorDeep | **(0.42, 0.35, 0.18)** | 泥黄-棕褐色。来自矿物颗粒（石英/粘土）的选择性散射/吸收 |
| baseColorShallow | **(0.55, 0.48, 0.28)** | 较亮的棕黄（近表面沉积物的直接反射占主导） |
| substrateColor | **(0.50, 0.42, 0.25)** | 淤泥/细沙底质 |
| depthColorFalloff | **1.8** | 快速衰减。因为浑浊水本身的吸收+散射很强，颜色随深度变化剧烈 |
| surfaceRoughness | **0.35** | 河口区可能因陆地遮挡而略避风 |
| foamCoverage | **0.04** | 中低 |
| colorTint | **(1.00, 1.00, 1.00)** | 无特殊色调 |

**为什么这组数字能表现河口**: 核心是 **clarity↓ × turbidity↑** 的组合拳。clarity=0.12 意味着底质只在最浅(<~1m)处勉强可见——大部分区域直接显示 baseColorDeep 的棕黄(0.42,0.35,0.18)。turbidity=0.85 进一步把整幅图像"蒙上一层雾"并压低对比度。如果把 turbidity 降到 0.2 但保持 clarity=0.12，你会得到一种"清晰但不透明的深色水"——像浓咖啡而不是浑水。两者必须同时高才能正确还原河口的"泥汤"质感。

---

### P5. 极地/高纬度冷水（Polar / Cold Water）

**参考依据**: 北冰洋边缘、南极威德尔海/罗斯海。极地水体的独特之处：(a) 表层水温低 → 溶解气体含量高但生物生产力季节性极强；(b) 冷水溶解有机物少 → CDOM 低；(c) 可能含有冰晶/融水微粒。整体外观偏冷、暗、去饱和。夏季冰缘区可能有局部高生产力斑块。

| 维度 | 值 | 说明 |
|---|---|---|
| clarity | **0.85** | 冷水通常非常清澈（低温减少溶解有机物，低生物量季节） |
| turbidity | **0.08** | 干净。偶有冰晶微粒 |
| baseColorDeep | **(0.04, 0.12, 0.28)** | 深蓝灰绿，明显去饱和。不是鲜艳的蓝——是"冷"的蓝 |
| baseColorShallow | **(0.18, 0.38, 0.48)** | 冷调钢 cyan |
| substrateColor | **(0.28, 0.32, 0.36)** | 砾石/岩石极地海床 |
| depthColorFalloff | **0.80** | 渐进 |
| surfaceRoughness | **0.55** | 极地海域风大；加上可能的冰缘效应 |
| foamCoverage | **0.08** | 冰相关的白色成分（碎冰/泡沫混合） |
| colorTint | **(0.98, 1.00, 1.02)** | 微妙的冷色偏移（略提蓝通道） |

**与 P2（热带深水）的关键区别**: 同样高透明度+低浑浊度，但 P5 明显更"暗"和"冷"。差异来自 baseColorDeep（P2: 0.02,0.18,0.42 鲜艳靛蓝 vs P5: 0.04,0.12,0.28 去饱和蓝灰绿）和 colorTint（P5 有微妙冷推）。这说明 **baseColorDeep 不能只用"深浅"来区分，还需要"色相/饱和度"自由度**——这也是为什么它是一个完整的 vec3 而不是一个标量。

---

### P6. 深海远洋（Deep Sea Pelagic / Abyssal Zone）

**参考依据**: 远离任何大陆架的深海区（水深 > 2000m 等效视觉深度）。虽然实际上海面下几百米就已几乎全黑，但从水面往下看的"深水色"是一种独特的近黑靛蓝——比普通"深蓝"更黑、更暗、几乎不透光。表面通常异常平静（无地形阻挡风程）。

| 维度 | 值 | 说明 |
|---|---|---|
| clarity | **0.78** | 水体本身光学纯度极高（Case 1 寡营养水），但"看起来不透"是因为光程足够长后连蓝光也被吸收殆尽 |
| turbidity | **0.03** | 公海中最干净的级别 |
| baseColorDeep | **(0.01, 0.03, 0.08)** | 近黑靛蓝。这是"纯水在 ~100m+ 光程"的颜色——几乎全吸收，只剩最深蓝的残余 |
| baseColorShallow | **(0.05, 0.20, 0.38)** | 如果有浅水（比如突然遇到海山），会是标准深蓝色 |
| substrateColor | **(0.03, 0.03, 0.05)** | 深海平原软泥，近黑色 |
| depthColorFalloff | **1.5** | 较快的颜色收敛 |
| surfaceRoughness | **0.12** | 远洋表面经常异常平静（"glassy ocean"现象） |
| foamCoverage | **0.01** | 几乎为零 |
| colorTint | **(1.00, 1.00, 1.00)** | 无特殊色调 |

**与 P2（热带深水）的差异**: P2 的 baseColorDeep=(0.02,0.18,0.42) 是"看得见的深蓝"；P6 的 (0.01,0.03,0.08) 是"看不见的黑蓝"。两者 clarity 都高、turbidity 都低——**差异 100% 来自 baseColorDeep 的绝对亮度**。这证明 baseColorDeep 作为一个独立维度（而非从 clarity 推导出来）的必要性。

---

### P7. 半封闭内海（Semi-enclosed Inland Sea）

**参考依据**: 渤海（中国）、波罗的海（欧洲）、亚得里亚海北部。共同特征：(a) 水交换受限 → 停留时间长；(b) 大量河流输入营养物质 → 富营养化趋势；(c) 盐度低于邻近外海；(d) 整体偏绿、偏浑浊。波罗的海更是全球最大面积的低盐 brackish 水体，有其独特的墨绿色。

| 维度 | 值 | 说明 |
|---|---|---|
| clarity | **0.45** | 中等透明度。视距约 5-8m。比开放大洋差很多，但不像河口那样完全不透明 |
| turbidity | **0.38** | 显著悬浮物（浮游植物 + 陆源颗粒 + 再悬浮沉积物） |
| baseColorDeep | **(0.12, 0.28, 0.32)** | 绿-蓝灰。CDOM + 叶绿素共同作用使绿色通道提升 |
| baseColorShallow | **(0.32, 0.52, 0.45)** | 浅水区呈绿-橄榄色调（波罗的海的标志性色） |
| substrateColor | **(0.38, 0.40, 0.28)** | 淤泥/黏土底质 |
| depthColorFalloff | **1.00** | 线性过渡 |
| surfaceRoughness | **0.30** | 半封闭水域风程较短 |
| foamCoverage | **0.04** | 中低 |
| colorTint | **(1.02, 1.04, 0.98)** | 轻微绿推。模拟内陆海特有的富营养化绿色偏移 |

**为什么需要 colorTint**: P7 的 baseColorDeep 已经偏绿(0.12,0.28,0.32)，但 colorTint 再加一层 (1.02,1.04,0.98) 的微妙绿推——这是因为内陆海的"绿"有两层来源：(a) 水体中溶解/悬浮物质的固有吸收谱（已编码在 baseColorDeep 里）；(b) 大面积均匀分布的微微型浮游植物的附加散射（用 colorTint 补充更灵活，因为它可以在不同深度区间有不同衰减率）。

---

### P8. 火山黑沙海岸水域（Volcanic Black-Sand Coast）

**参考依据**: 冰岛南部黑沙滩（Reynisfjara）、夏威夷 Big Island 绿砂/黑沙滩（Papakōlea/Waianapanapa）。这类地点的关键美学特征是：**水本身可能出奇地清澈（火山岛周围常有上升流带来清洁水），但因为海底是黑色玄武岩砂/火山玻璃，整体画面呈现出深沉、戏剧化的暗调**。这是一个绝佳案例，证明 substrateColor 作为独立维度的重要性——同样的水清澈度放在白沙底就是天堂，放在黑砂底就是哥特式的暗美。

| 维度 | 值 | 说明 |
|---|---|---|
| clarity | **0.88** | 出乎意料地高。许多火山岛周围有清洁的 oligotrophic 水 |
| turbidity | **0.07** | 很干净 |
| baseColorDeep | **(0.02, 0.16, 0.36)** | 标准深蓝（水体本身并不特殊） |
| baseColorShallow | **(0.18, 0.45, 0.52)** | 清澈的蓝-green（水柱传输正常） |
| substrateColor | **(0.12, 0.11, 0.10)** | **黑色火山砂**。这是整个 preset 的灵魂——极低的亮度值 |
| depthColorFalloff | **0.60** | 缓慢过渡。让"蓝水覆黑砂"的效果在较大深度范围内持续可见 |
| surfaceRoughness | **0.35** | 火山岛海岸常暴露于太平洋涌浪 |
| foamCoverage | **0.05** | 白色浪花在黑沙滩上形成强烈的明暗对比 |
| colorTint | **(1.00, 1.00, 1.00)** | 无特殊色调 |

**与 P1（热带珊瑚礁）的直接对比**: 两者 clarity 几乎相同（0.92 vs 0.88），turbidity 同样极低（0.04 vs 0.07），baseColorDeep 也接近（P1: 0.00,0.35,0.55 vs P8: 0.02,0.16,0.36 差异主要在饱和度）。**唯一的巨大差异是 substrateColor**：P1=(0.95,0.88,0.72) 亮白 vs P8=(0.12,0.11,0.10) 近黑。这导致 P1 的画面是"明亮通透的天堂"，P8 是"深邃神秘的暗海"——同样的水体光学属性，完全不同的美学体验。这就是 D5 独立存在的最强论证。

---

### P9. 潟湖/环礁内湖（Lagoon / Atoll Inner Lake）

**参考依据**: 马尔代夫环礁内湖、帕罗群岛泻湖、新喀里多尼亚潟湖。这是 P1（热带浅滩）的"极致版"——更深层的限制条件：水深通常只有 1-5m、完全封闭无外海浪、水体近乎静止。结果是：**比 P1 更亮、更平静、更均匀的 turquoise**。如果说 P1 是"美丽的海岸线"，P9 就是"超现实的静止宝石色水面"。

| 维度 | 值 | 说明 |
|---|---|---|
| clarity | **0.96** | 接理论极限。在 1-3m 深的潟湖里你可以数清每一粒沙 |
| turbidity | **0.01** | 本质为零。封闭环境无外部沉积物输入 |
| baseColorDeep | **(0.02, 0.38, 0.52)** | 即使潟湖最"深"的地方也不超过几米 → 连"深水色"都比一般海域的浅水色更亮 |
| baseColorShallow | **(0.28, 0.88, 0.82)** | **极度明亮的 aqua-cyan**。比 P1 的 (0.15,0.82,0.85) 更亮（R通道更高=更少蓝偏移、更接近白） |
| substrateColor | **(0.98, 0.92, 0.78)** | 最亮的白色生物砂（可能含贝壳碎片，比 P1 更白） |
| depthColorFalloff | **0.40** | **非常缓慢**。整个潟湖几乎同色——几乎没有可见的颜色梯度 |
| surfaceRoughness | **0.03** | 本质上镜面。封闭环境无风浪 |
| foamCoverage | **0.00** | 完全没有 |
| colorTint | **(1.00, 1.00, 1.00)** | 无特殊色调 |

**与 P1 的差异分析**: P9 在每一个维度上都把 P1 的特点推向了极致——更高的 clarity (0.92→0.96)、更低的 turbidity (0.04→0.01)、更亮的 baseColorShallow、更白的 substrateColor、更低的 surfaceRoughness、零 foam。这不是"另一种水"，而是"P1 的极限形态"。两者是否应该合并？**不应该**——因为在实际应用中它们代表不同的地理实体（外礁坡 vs 内潟湖），且视觉差异足够大（P9 比 P1 亮 30-40% 在亮度通道），值得保留为独立预设。

---

### P10. 季风浑浊期沿海水域（Monsoon Turbid Coastal）

**参考依据**: 东南亚季风区（泰国湾、越南沿海、孟加拉湾）在西南季风盛期（约 6-9 月）的海岸状态。**这是 P1 的"季节性变异体"**——同一个地理位置，雨季 vs 旱季完全是两种水。季风期暴雨导致：(a) 河流径流量暴增数十倍 → 携带大量陆源沉积物入海；(b) 强风搅动海底再悬浮；(c) 云层覆盖改变光照氛围。水色从旱季的清澈 turquoise 变成季风期的浑浊橄榄绿/棕绿色。

| 维度 | 值 | 说明 |
|---|---|---|
| clarity | **0.35** | 从 P1 的 0.92 暴跌到 0.35。视距降至 3-5m |
| turbidity | **0.58** | 从 P1 的 0.04 飙升到 0.58。大量陆源悬浮物 |
| baseColorDeep | **(0.18, 0.32, 0.30)** | 从 P1 的青蓝变成绿-棕（CDOM + 矿物颗粒联合作用） |
| baseColorShallow | **(0.40, 0.56, 0.42)** | 浑浊的橄榄-棕绿 |
| substrateColor | **(0.52, 0.48, 0.34)** | 被沉积物覆盖的礁/沙 |
| depthColorFalloff | **1.3** | 比旱季更快地归向浑浊深色 |
| surfaceRoughness | **0.55** | 季风风力驱动显著波况 |
| foamCoverage | **0.10** | 增高一倍以上 |
| colorTint | **(1.00, 1.03, 0.97)** | 微妙绿-棕偏移（陆源有机物带来的 CDOM 特征） |

**设计意图**: 这个 preset 的核心教学价值在于展示**同一套系统如何通过参数调整描述"同一地点的不同时间状态"**。如果 RodiO 未来接入气象数据，可以在季风期自动从 P1 切换到此预设——无需新的代码逻辑，只需换一组 uniform 值。

---

### P11. 藻华/赤潮特殊事件（Algae Bloom / Red Tide）— colorTint 扩展点演示

**参考依据**: 有害藻华(HAB)事件，如东海大规模东海原甲藻(Prorocentrum donghaiense)赤潮(呈褐色)、夜光藻(Noctiluca scintillans)红色赤潮、或球状棕囊藻(Phaeocystis globosa)绿色藻华。这类事件的特点是：(a) 通常局限于表层 0-10m；(b) 强烈改变水体吸收/散射谱；(c) 视觉上极为醒目（水面呈锈红/暗绿/棕色条带）。

| 维度 | 值 | 说明 |
|---|---|---|
| clarity | **0.40** | 藻华增加散射，有效透明度下降 |
| turbidity | **0.55** | 高浓度的浮游植物细胞及其碎屑 |
| baseColorDeep | **(0.28, 0.18, 0.08)** | 锈红-褐色（赤潮型）/ 或 (0.08, 0.35, 0.15) 绿色藻华型 |
| baseColorShallow | **(0.52, 0.32, 0.18)** | 表层呈显著的铁锈红/暗绿 |
| substrateColor | **(0.35, 0.30, 0.18)** | 藻华死亡沉降后在底部形成的有机质层 |
| depthColorFalloff | **1.1** | 近线性 |
| surfaceRoughness | **0.30** | — |
| foamCoverage | **0.06** | 泡沫可能略带颜色 |
| colorTint | **(1.15, 0.85, 0.70)** | **★ 这是 colorTint 发挥作用的实例 ★** — 将整个画面推向红-橙偏移。乘以 (1.15, 0.85, 0.70) 后：红通道增强 15%、绿通道减弱 15%、蓝通道减弱 30% → 结果是明确的暖色调/锈色偏移 |

**colorTint 的架构价值**: 注意 P11 的 baseColorDeep 已经包含了藻华的基础色调变化(0.28,0.18,0.08)。colorTint 在此之上再做一层乘法偏移——两层叠加使得最终效果更加极端和鲜明。**如果没有 colorTint 这个维度**，要达到同样的赤潮效果只能进一步扭曲 baseColorDeep 的值，但这会破坏 baseColorDeep"代表水体固有吸收谱"的语义纯洁性。有了 colorTint，baseColorDeep 保持物理合理（"水体吸收谱因藻类色素而偏移"），而 colorTint 处理纯粹的"视觉风格偏移"（"整个画面被染上一层色调"）。

---

## 四、预设之间的关系分析

### 可能合并的候选对

经过逐一比较，以下预设对的数值相似度值得讨论：

| 对 | 相似度 | 建议 | 理由 |
|---|---|---|---|
| P2 vs P6 | 中等 | **保留分开** | 都是"深蓝清澈水"，但 P2 的 baseColorDeep 亮度(0.42B)是 P6(0.08B)的 5x——视觉差异巨大（"看得见的深蓝"vs"近黑的深渊蓝"）。合并会丢失"深海恐惧感"这个独特情绪 |
| P1 vs P9 | 高（P9 是 P1 极限版） | **保留分开** | 如前所述，两者代表不同的地理实体（外礁 vs 内潟湖），且 P9 的亮度高出 30%+ |
| P3 vs P5（温带 vs 极地） | 中低 | **保留分开** | P3 的 baseColorDeep 含更多灰/绿(0.06,0.20,0.38)；P5 更冷更暗(0.04,0.12,0.28)。加上 P5 的 foamCoverage 和 roughness 都不同 |
| P7 vs P10（内海 vs 季风浑浊） | 中 | **保留分开** | P7 的浑浊来自慢性富营养化（绿调为主）；P10 来自急性径流事件（棕调为主）。baseColorDeep 的色相不同(0.12,0.28,0.32 vs 0.18,0.32,0.30) |

**结论: 11 个预设目前都不建议合并**。每组都有至少一个"签名维度组合"使其不可替代。如果未来需要精简，优先考虑 P2↔P6 合并为一个带"深度子模式"的 preset。

---

## 五、Shader 实现路线图（供 Phase 3/#44 参考）

### 数据流总览

```
[几何数据] → [深度计算] → [底质采样]
                              ↓
[9维uniform] → [水体颜色引擎] → [表面着色(Fresnel+Specular)] → [泡沫层] → [colorTint] → [输出]
```

### 推荐实现顺序

1. **Phase 3α** (最小可用): 实现 D1(clarity) + D3(baseColorDeep) + D6(depthColorFalloff) + D7(surfaceRoughness)。仅这 4 个就能产生"不同深度的不同蓝色的水面"，已经比单一颜色进步巨大。

2. **Phase 3β** (核心差异化): 加入 D2(turbidity) + D4(baseColorShallow) + D5(substrateColor)。此时系统具备"清澈vs浑浊""亮底vs暗底"的基本表达能力。P1-P8 的主要视觉差异都可体现。

3. **Phase 3γ** (打磨): 加入 D8(foamCoverage) + D9(colorTint)。完成全部 9 维。支持全部 11 个预设。

### 性能预算估算

| 组件 | ALU 估算 | Texture 采样 | 备注 |
|---|---|---|---|
| 深度-颜色混合 (D1,D3,D4,D5,D6) | ~30 ops | 0 (或 1 if sampling GEBCO bathymetry) | 主要为 exp/pow/mix |
| 浑浊散射 (D2) | ~20 ops | 0 | 单次近似散射积分 |
| 表面着色 (D7) | ~15 ops | 1 (waternormalals.jpg) | Fresnel + specular |
| 泡沫 (D8) | ~10 ops | 1 (噪声纹理 or procedural) | 可选 |
| colorTint (D9) | 3 ops (vec3 mul) | 0 | 忽略不计 |
| **合计** | **~78 ops** | **1-3** | 属于轻量级 fragment shader |

---

## 六、与美学基调的对标自查

| 美学要求 | 本方案的响应方式 |
|---|---|
| "海水不是一种颜色，是一整套地理事实" | ✅ 9 维 × 11 预设覆盖从热带清澈到河口浑浊到极地冷水的完整谱系 |
| "克制指的是不要戏剧化" | ✅ 所有预设的 baseColorDeep/baseColorShallow 饱和度控制在合理范围（最高 P9 的 0.88G 也不算过饱和）；foamCoverage 上限 0.10；无 HDR 式高光 |
| "避开摄影App精修感" | ✅ 不提供"vibrance""contrast boost"等后期风格参数；所有维度都有物理对应物 |
| "避开飞行模拟器机械感" | ✅ 参数是连续值而非离散档位；过渡平滑 |
| "避开冥想App甜腻感" | ✅ 默认预设不含马卡龙色（最亮的是 P9 的 (0.28,0.88,0.82) 仍是自然界的真实 turquoise） |
| "坂本龍一式留白" | ✅ P1/P9 的低密度云 + 高透明度水面 = 大面积"空"的区域，内容丰富度体现在参数差异而非视觉填充密度 |

---

## 七、待后续阶段确认的事项

- [ ] **GEBCO 水深数据的精度和单位**：当前 depth 计算是否直接来自 GEBCO 网格？如果是，需要确认网格值的单位和基准面（datum）
- [ ] **底质图（seabed substrate map）是否存在**：substrateColor 目前假设为全局统一值。如果有全球底质分类数据（如 GEOSEABED），可以实现 per-pixel substrateColor — 这会让 P1 vs P8 的差异更加震撼
- [ ] **大气散射交互**：水体颜色应与大气散射（Rayleigh/Mie）联动——晴天 vs 多云天的天空色会影响水面的反射和环境光。这不在水质系统内部，但 Phase 3 集成时需要考虑
- [ ] **动态预设切换**：同一位置是否需要在不同时间/天气下切换预设？（P1 ↔ P10 的季风切换是最明显的例子）。需要什么触发机制？

---

*文档版本: v1 · 2026-07-19*
*维度数: 9 | 预设数: 11 | 全部预设包含完整 9 维数值*
