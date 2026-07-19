# Horizon Mode — GEBCO 近景细节噪声技术方案 v1

> Phase 0.5 资料补充 · 对应 issue #41（Phase 7/#48 实际落地）
>
> **状态**: 技术方案文档，不包含可运行代码。Phase 7 实现时直接参考本文件。

---

## 问题陈述

RodiO 当前使用 GEBCO 全球测深/地形数据作为地球表面高度源，原始分辨率约 **450 米/像素**（30 弧秒网格）。在 Orbit 模式下这个分辨率完全够用——从数千公里外看，450m 的细节远低于一个像素的尺寸。

但 Horizon Mode 的核心体验是"站在地上看见具体的东西"。当摄像机拉近到地面附近（几公里到几十米），GEBCO 数据的平滑感变得肉眼可见：山脊缺少岩石粗糙、平原过于均匀、海岸线缺乏微地形起伏。这不是渲染精度的问题——是数据本身在近处"不够细"。

**目标**: 在不替换或重新采样 GEBCO 数据的前提下，叠加一层程序化噪声，补足近处的微观粗糙感，同时让远处自然退回到纯 GEBCO 大轮廓。

---

## 方案选择: fBm 叠加层

### 为什么是 fBm（而非其他方案）

| 方案 | 优势 | 劣势 | 结论 |
|---|---|---|---|
| **fBm（分形布朗运动）** | 多频率尺度自然融合；参数空间成熟且直觉性强；GPU 计算成本低（单次着色器调用）；与 GEBCO 无缝混合 | 单一噪声模式可能显得重复（需域扭曲缓解） | ✅ **首选** |
| Worley / Voronoi 噪声 | 适合裂纹/蜂窝状地貌（熔岩流、干涸河床） | 不像自然地形的一般粗糙度；参数调优更难 | ❌ 不作主噪声 |
| 预烘焙法线贴图 | 视觉效果最好（可手绘） | 球面 UV 接缝问题；需要大量纹理内存；无法随距离动态衰减 | ❌ Horizon 模式不适合 |
| Wavelet 噪声 | 更自然的频谱分布 | GLSL 实现复杂度高；调试困难 | ❌ 过度工程化 |

**fBm 选择理由总结**: 地形微观粗糙本质上是多尺度的——厘米级的碎石纹理、米级的不平整、十米级的起伏、百米级的地形褶皱。fBm 通过 octave 叠加天然覆盖了这个频谱范围，而且振幅可以通过 persistence 参数精确控制各尺度的贡献比例。对于"补足 GEBCO 近场不足"这个特定需求，fBm 是成本/效果比最高的方案。

### 域扭曲（Domain Warping）

为避免大范围重复感，建议对 fBm 输入坐标做一次低频扰动：

```
vec2 warpedPos = pos + 0.8 * vec2(
    fbm(pos * 0.03 + offsetA),
    fbm(pos * 0.04 + offsetB)
);
float detail = fbm(warpedPos);
```

这会让同一片噪声在不同地理位置呈现不同形态，消除 tile 感。域扭曲本身的计算开销约为 2 次 extra fbm 调用（可以用较少 octave 如 3 次），可接受。

---

## 核心设计: 振幅–距离衰减曲线

### 设计原则

1. **近场有可见效果**：距离 < 5 km 时，噪声振幅足够让山体轮廓产生可察觉的粗糙变化
2. **中场过渡自然**：5–50 km 区间平滑衰减，无可见边界带
3. **远场归零**：距离 > 50 km 时，噪声贡献趋近于 0（此时 GEBCO 自身的 450m 分辨率已超过屏幕像素密度，不需要额外细节）
4. **不破坏 GEBCO 大结构**：噪声只做加法/乘法调制，不替代原始高程值

### 衰减函数推荐: 平滑阶跃（Smoothstep-based falloff）

```
// distanceToCamera 单位: km（世界空间）
float nearDist  = 3.0;    // 距离 < 3km 时全振幅
float farDist   = 40.0;   // 距离 > 40km 时振幅 ≈ 0
float fadeRange = farDist - nearDist;

float t = clamp((distanceToCamera - nearDist) / fadeRange, 0.0, 1.0);
// 使用三次 smoothstep 让衰减曲线两端都平缓
float attenuation = smoothstep(0.0, 1.0, t);  // 或自定义更高次: t*t*(3-2t)

float finalAmplitude = baseAmplitude * (1.0 - attenuation);
```

### 参数取值建议

| 参数 | 建议起始值 | 说明 |
|---|---|---|
| `nearDist` | **3–5 km** | 近场全强度起点。太小则只有极近距离才有细节；太大则中远景也受影响，可能引入伪影 |
| `farDist` | **35–50 km** | 远场归零终点。应大于 GEBCO 在当前视角下的有效分辨率对应的距离 |
| `baseAmplitude`（陆地） | **15–45 m**（视场景类型） | 噪声最大偏移量。山地可用较高值（30-45m），平原较低（10-20m） |
| `baseAmplitude`（海底） | **3–12 m** | 海底细节比陆地小得多（沙波纹、小型海丘） |
| 衰减曲线形状 | **smoothstep(t)** 或 **t³(6t²-15t+10)**（五次 Hermite） | 三次 smoothstep 在两端的一阶导数为零（C¹连续）。如果发现视觉上有"突然出现"感，升级到五次 |

### 为什么不用线性衰减？

线性衰减在 `farDist` 处一阶导数跳变（从某个斜率突变为 0），在某些光照条件下会在衰减边界产生可察觉的亮度/法线突变带。Smoothstep 类衰减保证了 C¹ 连续，代价仅是一次额外的 `mix()` 运算。

---

## 噪声频率与 Octave 配置

### 频率基准（Base Frequency）

频率决定单个 octave 中噪声特征的尺寸。基准频率应使 **最小特征尺寸对应约 10–30 米**（近场时）：

```
// 世界空间坐标单位: 米
float baseFreq = 1.0 / 80.0;   // 一个周期 ≈ 80m → 最小可见特征约 20-40m
```

为什么选 80m 周期而不是更大或更小：
- **太低频率**（如 500m/周期）：噪声看起来像"大疙瘩"，不像微观粗糙
- **太高频率**（如 5m/周期）：在远处会产生 moiré 闪烁（aliasing），且 GPU 计算量增大
- **80m 周期**：在 3km 距离处，一个像素覆盖约 1.5m（假设 1080p + 60° FOV），80m 周期对应 ~53 像素/周期——足够看到细节但不至于 aliasing

### Octave 数量

| Octave 数 | 适用场景 | 建议 |
|---|---|---|
| **4** | 性能敏感（移动端 / 低端 GPU） | 可接受，但高频细节有限 |
| **5** | **默认推荐** | 最佳平衡点 |
| **6–7** | 高质量桌面端 / 特写镜头 | 更多高频细节，但有边际收益递减 |

**推荐: 5 octaves 作为默认值**，Phase 7/8 调参时可按设备档次切换 4/5/6。

### Lacunarity 与 Persistence（增益）

```
lacunarity  = 2.0;     // 每层频率翻倍（标准值）
persistence = 0.50;     // 每层振幅减半（标准值，产生 1/f 噪声谱）
```

- **Lacunativity 2.0** 是地形噪声的标准值，保证每层 octave 覆盖恰好上一层的半波长区域
- **Persistence 0.5** 产生粉红噪声谱（1/f），与真实地形功率谱接近（真实地形功率谱大致遵循 k^(-2) 到 k^(-3)，persistence 0.55-0.65 更接近但 0.5 更稳定）

### 各 Octave 贡献示例（5 octaves, persistence=0.5）

| Octave | 频率 (周期) | 相对振幅 | 物理含义 |
|---|---|---|---|
| 0 | ~80 m | 1.000 | 最大起伏（丘陵级） |
| 1 | ~40 m | 0.500 | 中等起伏 |
| 2 | ~20 m | 0.250 | 小丘/沟壑 |
| 3 | ~10 m | 0.125 | 岩石凸起/凹陷 |
| 4 | ~5 m | 0.063 | 微观粗糙（最细颗粒） |

---

## 应用方式: 顶点位移 vs 法线扰动

两种方式各有适用场景，Phase 7 建议采用**混合方案**：

### 低频部分（Octave 0–2）→ 顶点位移（Vertex Shader）

```
// 在顶点着色器中对 position 做位移
float lowDetail = fbm(worldPos * baseFreq, 3);  // 只算前 3 个 octave
worldPos += normal * lowDetail * amplitude * attenuation;
```

**优点**: 改变几何体实际位置 → 影响剪影（silhouette）、自阴影、投射阴影
**缺点**: 需要足够的几何细分度才能表现高频。GEBCO 球面网格在近处可能不够密 → 可能需要在近场动态细分（Tessellation 或预生成 LOD 网格）

### 高频部分（Octave 3–4）→ 法线扰动（Fragment Shader Normal Mapping）

```
// 在片段着色器中通过有限差分计算扰动后的法线
float eps = 0.001;
float hL = fbm((worldPos - eps * tangent) * baseFreq, 5);
float hR = fbm((worldPos + eps * tangent) * baseFreq, 5);
float hD = fbm((worldPos - eps * bitangent) * baseFreq, 5);
float hU = fbm((worldPos + eps * bitangent) * baseFreq, 5);

vec3 perturbedNormal = normalize(normal +
    vec3((hL - hR), (hD - hU), 1.0) * normalMapStrength * attenuation);
```

**优点**: 不依赖网格细分度；高频法线细节在任意距离下都能正确表现
**缺点**: 不改变几何体剪影；需要 careful tuning of `eps` 和 `normalMapStrength`

**推荐策略**: Phase 7 先实现法线扰动版本（开发快、无需改几何），Phase 8 再根据性能预算考虑加入低频顶点位移。

---

## 与 GEBCO 数据的混合策略

噪声不应独立存在，而是**调制** GEBCO 高程：

### 方案 A: 加性叠加（简单、安全）

```
float geElevation = sampleGEBCO(uv);       // 原始 GEBCO 值
float noiseDetail  = fbm(...) * amplitude * attenuation;
float finalElevation = geElevation + noiseDetail;
```

**优点**: 实现 trivial，不会丢失任何 GEBCO 信息
**风险**: 在 GEBCO 已有的陡峭区域（悬崖、峡谷），叠加噪声可能让边缘过粗。可通过 `slopeMask` 缓解：坡度 > 45° 时降低噪声振幅。

### 方案 B: 乘性调制（更有层次）

```
float slope = computeSlope(geElevation);   // 从 GEBCO 局部梯度估算
float slopeFactor = smoothstep(0.0, 0.5, 1.0 - slope);  // 平坦区更多细节
float finalElevation = geElevation + noiseDetail * slopeFactor;
```

**优点**: 自动保护陡峭特征不被噪声模糊
**推荐**: Phase 7 初始实现用 A（加性），后续迭代引入 B 的坡度遮罩。

---

## 场景类型差异化参数

不同 Horizon 场景对"细节量"的需求不同：

| 场景 | baseAmplitude (陆地) | baseAmplitude (海底) | nearDist | farDist | 说明 |
|---|---|---|---|---|---|
| 海岸/海滩 | 8–18 m | 2–5 m | 2 km | 25 km | 细腻沙纹、潮间带纹理 |
| 山地/峡谷 | 30–50 m | N/A | 4 km | 45 km | 岩壁粗糙、碎石坡 |
| 平原/草原 | 6–15 m | 3–8 m | 3 km | 30 km | 微地形起伏 |
| 极地冰盖 | 10–25 m | 5–12 m | 5 km | 40 km | 冰裂隙、雪丘 |

这些参数可以作为 per-scene uniform 组，由相机系统根据当前场景类型自动选择。

---

## 性能考量

| 操作 | 成本估算 (per-vertex/fragment) | 备注 |
|---|---|---|
| 5-octave fBm（snoise × 5） | ~50 ALU ops | 主成本 |
| 域扭曲（额外 2× 3-oct fbm） | ~30 ALU ops | 可选优化项 |
| 距离衰减 | ~5 ALU ops | 忽略不计 |
| 法线有限差分（额外 4× fbm） | ~200 ALU ops | 仅 FS 路径 |

**总估算**: 顶点路径 ~85 ALU，片段路径 ~255 ALU（含法线差分）。在现代桌面 GPU 上属于轻量级操作；移动端可能需要降 octave 至 4 或禁用法线差分。

---

## 待 Phase 7/8 确认的事项

- [ ] 球面网格在最近摄距下的实际细分度是否够支持顶点位移？如不够是否需要 Tessellation？
- [ ] 噪声 seed 是否需要按经纬度分区以避免全球重复？（域扭曲可能已解决大部分问题）
- [ ] 是否需要对 GEBCO 本身已有的海岸线做特殊保护（避免噪声让海岸变模糊）？
- [ ] 远场衰减的 `farDist` 是否需要根据当前 FOV 动态调整？（宽 FOV 时远场像素覆盖更大地理面积）

---

*文档版本: v1 · 2026-07-19*
