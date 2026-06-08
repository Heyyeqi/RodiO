# E1-R2 Noon Runtime Exposure Audit
# 正午 Runtime 过曝归因审计

> 文件类型：runtime 归因审计报告
> 对象：d5b_design_v3_2_1（贴图层）× noon runtime（sun / atmosphere / specular / tone mapping）
> 日期：2026-06-08
> 阶段：E1-R2 Browser 截图测量，不修改任何文件
> 父文档：docs/e1_day_master_reference_metrics_baseline.md
> 关联：docs/e1_r1_current_metrics_audit.md（贴图层基线）
> 数据：docs/metrics/e1_r2_noon_runtime_measurements.json / .csv

**本轮严格约束（全程生效）：**
```
禁止修改 earth3d.js
禁止修改 DAY_TEXTURE_VARIANT
禁止生成任何新地球贴图
禁止修改 production / candidates 中任何图片
禁止调整 atmosphere / sun / ambient / specular / shininess
禁止 commit，除非 RW 明确确认
```

---

## 0. 审计目标与方法

### 0.1 目标

判断当前 RodiO globe 在 noon 模式下观察到的"过亮 / 偏冷白 / 动画感 / 正午滤镜感"，
其根因究竟来自：

- **贴图层**（Texture Layer）：d5b_design_v3_2_1 本身的 L* / S% / 色相值；可在 E1-R3 改善。
- **Runtime 层**（Runtime Layer）：Three.js PhongMaterial + DirectionalLight（sun）+ atmosphere 球壳 + specular map；只能在 Phase 7（lighting 调整）改善。

### 0.2 归因判断规则

| ΔL = scr_L − tex_L | 现象 | 主因 | 处理阶段 |
|---|---|---|---|
| ΔL ≥ +10 | 屏幕明显亮于贴图 | Runtime 层（atmosphere/sun 提亮） | Phase 7 |
| +5 ≤ ΔL < +10 | 屏幕偏亮 | Runtime 层为主 | Phase 7 |
| −5 ≤ ΔL < +5 | 与贴图接近 | 贴图层基线 | E1-R3 |
| ΔL < −5 | 屏幕偏暗（sun 角度遮蔽） | 日照角度差异 | 记录注意 |

---

## 1. 工作区状态

```
（记录时）git status --short：M devlog.md（E1-R4A 遗留，未提交）
（记录时）git log -3：
  f4cdb04 Add E1 metrics audit and preview requirements
  ee45c98 Update devlog for E1-R1 audit
  bbb471a Add E1 current texture metrics audit
```

---

## 2. 被测对象确认

| 项目 | 值 |
|---|---|
| 贴图候选 | `pwa/assets/earth/candidates/d5b_design_v3_2_1_8192x4096.jpg` |
| URL 参数 | `?dayTexture=d5b_design_v3_2_1` |
| 加载路径 | `loadTextureWithFallback` → `getDayTexturePaths()` → candidates 目录 |
| 贴图层数据来源 | E1-R1 报告 51 点测量值（同坐标点直接引用） |
| 本轮测量范围 | Browser noon 模式下的屏幕实际渲染像素；包含全部 runtime 叠加 |
| 不测内容 | 贴图文件本身（已由 E1-R1 完成） |

---

## 3. Runtime 配置确认（Noon 模式）

从 `pwa/earth3d.js` 读取 noon 主题配置（只读，不修改）：

```javascript
noon: {
  themeHour: 13,
  texture:   { map: 'day', mapColor: 0xffffff, emissiveColor: 0x000000, emissiveIntensity: 0 },
  material:  { specular: 0x091018, shininess: 1.12 },
  atmosphere: { color: '#b0d9ed', opacity: 0.14 },
  lighting:  { ambient: 0.09, sun: 1.25, stars: 0.01, cityLightsOpacity: 0 },
}
```

| 参数 | 值 | 说明 |
|---|---|---|
| mapColor | 0xffffff（白色，无色彩偏移） | 不对贴图色调加权 |
| emissiveIntensity | 0 | 无自发光 |
| specular | 0x091018（极深，R=9 G=16 B=24） | 镜面高光极弱 |
| shininess | 1.12 | 高光散射很宽，低峰值 |
| atmosphere.color | #b0d9ed（RGB 176,217,237，浅天蓝） | 宽阔大气覆盖色 |
| atmosphere.opacity | 0.14 | 14% alpha 叠加 |
| ambient | 0.09（ambientLight.intensity） | Three.js 场景环境光 |
| sun | 1.25（DirectionalLight intensity） | 主光源强度 |
| sunColor | 0xfff5e0（暖白 RGB 255,245,224） | 轻微暖色 |
| themeHour | 13 | 太阳位置在黄道 h=13h 处 |

**太阳方位（themeHour=13 → updateSunPosition(13)）：**
```
h=13 falls in [12,18]: from=[4,3,3], to=[1,0,4], t=(13-12)/6=0.167
sunLight.position = lerp([4,3,3],[1,0,4], 0.167) ≈ (3.5, 2.5, 3.17)
```
方位向量 ≈ (0.65, 0.46, 0.59)：正前偏右上，与相机（z=4.8）同侧。

**渲染器设置：**

| 参数 | 值 |
|---|---|
| outputColorSpace | THREE.SRGBColorSpace |
| toneMapping | NoToneMapping（未显式设置） |
| toneMappingExposure | 1.0（默认） |

**CDP 测量时 runtime 状态确认：**
```
ambientLight.intensity = 0.09   ← 与 noon 配置匹配
sunLight.intensity     = 1.25   ← 与 noon 配置匹配
```

---

## 4. 测量工具链说明

| 组件 | 方案 |
|---|---|
| 浏览器 | Chrome 149（单独调试实例，--remote-debugging-port=9222，独立 profile） |
| 截图方式 | Chrome DevTools Protocol `Page.captureScreenshot`（format=png，fromSurface=true） |
| 截图分辨率 | 2400×1488（设备像素，2× Retina scale） |
| canvas 位置 | CSS: x=385, y=16, w=430, h=712 → 设备像素: (770,32)–(1630,1456) |
| 采样区域 | canvas 中心 ±50px（100×100 device px = 50×50 CSS px）对应地理中心 |
| 像素处理 | Python PIL + numpy；sRGB→linear→Y→CIE Lab L* |
| globe 导航 | `window.earth3d.setTimeOfDay('noon')` + `window.earth3d.setDebugLocation(lon, lat)` |
| noon 验证 | CDP 查询 `getDebugState()` 确认 ambientIntensity=0.09, sunIntensity=1.25 后开始测量 |
| 等待时间 | setDebugLocation 后等待 4000ms，保证 WebGL 重渲染完成 |
| 前 4 点重测 | 初次测量在 TUNE IN 覆盖层下（night 模式），noon 确认后重新采集 |

---

## 5. 10 点测量数据表

> 采样点坐标与 E1-R1 保持一致。tex_L / tex_p95 / tex_S 引用自 E1-R1 测量值。
> delta_L = scr_L − tex_L；正值 = 屏幕亮于贴图；负值 = 屏幕暗于贴图。

| # | Name | Cat | tex_L | scr_L | ΔL | scr_p95 | scr_S% | 判断 | 归因 | Phase7 | 有效 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | Sahara_Libya | 沙漠 | 71.5 | 71.4 | **−0.1** | 76.1 | 31 | 正常 | 贴图层基线 | 否 | ✓ |
| E2 | Arabian_Desert | 沙漠 | 70.7 | 71.1 | **+0.4** | 76.7 | 29 | 正常 | 贴图层基线 | 否 | ✓ |
| E3 | Australia_Simpson | 沙漠 | 53.2 | 48.1 | **−5.1** | 57.9 | 35 | 偏暗 | 贴图层基线 | 否 | ✓ |
| F1 | Antarctica_Inland | 极地 | 89.6 | 81.7 | **−7.9** | 93.6 | 3 | 正常 | 贴图层基线 | 否 | ✓ |
| F2 | Greenland_Inland | 极地 | 91.9 | 90.5 | **−1.4** | 93.5 | 2 | 正常 | 贴图层基线 | 否 | ✓ |
| F3 | Ross_Ice_Shelf | 极地 | 81.8 | 47.3 | −34.5 | 52.0 | 30 | **采样无效** | 中心偏至Southern Ocean | — | ✗ |
| D1 | Pacific_Deep | 深海 | 21.4 | 31.3 | **+9.9** | 46.2 | 36 | 偏亮 | runtime 层为主 | **是** | ✓ |
| D2 | Indian_Deep | 深海 | 20.8 | 43.1 | **+22.3** | 52.0 | 39 | 偏亮（atm提亮） | runtime 层（atmosphere） | **是** | ✓ |
| A4 | Bahamas | 热带 | 44.9 | 40.9 | −4.0 | 58.0 | 20 | 正常 | 贴图层色相/饱和 | 否 | ✓* |
| A1 | Boracay | 热带 | 43.5 | 45.0 | **+1.5** | 54.3 | 36 | 正常 | 贴图层色相/饱和 | 否 | ✓ |

> ✓* Bahamas 采样中心含美国东海岸陆地，S%=20% vs 贴图 44%，L* 受影响；结论方向成立但数值仅供参考。

---

## 6. 分类归因分析

### 6.1 沙漠（Desert）— Runtime 中性，贴图不判定为过曝

| 点 | ΔL | 结论 |
|---|---|---|
| Sahara | −0.1 | Runtime 几乎透明；noon 对撒哈拉几乎无额外抬亮 |
| Arabia | +0.4 | 同上；两点 scr_L 与 tex_L 误差 < 0.5，在采样误差范围内 |
| Australia | −5.1 | 南半球斜照角导致轻度压暗；runtime 未提亮澳洲内陆 |

**归因结论：**

- Sahara scr_L=71.4 vs tex_L=71.5（ΔL=−0.1），仅证明 noon runtime 对撒哈拉几乎没有额外抬亮；
- **不能据此判定"沙漠贴图层过亮"**；
- 根据 E1-R1 的 RW 阈值确认，白沙漠 / 浅色沙漠 L* 70–84 属合理范围；
- Sahara tex_L=71.5 在该阈值范围内，不构成贴图层过曝；
- Runtime 层（noon sun/atmosphere）未对沙漠区产生显著提亮或压暗。

**修复路径：E1-R3 观察项（非强制修复）。**
Phase 7 无需专门处理沙漠区。
沙漠贴图不得作为第一优先修改项；后续如需调整，须通过 E1-R4A Regional Visual Preview 确认后再决定。

### 6.2 极地（Polar）— Runtime 未过曝，不建议直接压暗贴图

| 点 | ΔL | scr_p95 | 结论 |
|---|---|---|---|
| Antarctica | −7.9 | 93.6 | Runtime 略压暗贴图；p95=93.6 为少量高镜面像素，均值未过曝 |
| Greenland | −1.4 | 93.5 | 与贴图几乎持平；runtime 不放大冰层亮度 |
| Ross | 采样无效 | — | 中心落在 Southern Ocean，dL=−34.5 为海洋信号，非冰盖有效数据 |

**归因结论：**

- Greenland / Antarctica 屏幕 L* 接近或低于贴图 L*，说明 noon runtime **未造成额外过曝**；
- **不能据此推出极地贴图必须修复**；
- 内陆冰盖天然高亮（tex_L=89–92），属均质冰盖正常状态；
- 极地高 L* 是物理合理值，不构成贴图缺陷；
- Runtime 层对极地不起放大作用（ΔL 为负）。

**修复路径：E1-R3 谨慎观察项（非第一优先贴图修改项）。**
Phase 7 无需专门处理极地区。
若后续有调整需求，应以"保留冰雪洁净感，同时避免死白"为目标，
不得直接压暗极地贴图，须通过 E1-R4A Regional Visual Preview 确认方向。

> **p95 高光说明：** 极地点 p95=93.5–93.6（略高于贴图 p95=91.3–92.1），
> 系 runtime specular（shininess=1.12，specular=0x091018 极弱）产生少量高光像素所致；
> 均值 ΔL 为负，不构成过曝，属正常冰雪材质效果。

### 6.3 深海（Deep Ocean）— Runtime 层主因（大气层提亮）

| 点 | tex_L | scr_L | ΔL | 结论 |
|---|---|---|---|---|
| Pacific Deep | 21.4 | 31.3 | **+9.9** | Atmosphere 将深海从 L*=21.4 提亮至 31.3 |
| Indian Deep | 20.8 | 43.1 | **+22.3** | 最强提亮；scr_L=43.1 是 tex_L=20.8 的 2× |

**归因结论：深海偏亮 / 偏冷白的根因在 runtime 层——atmosphere 球壳（opacity=0.14，color=#b0d9ed）
对极深色区域（tex_L=20–22）产生显著提亮（+10 至 +22 L*），
这是 `MeshPhongMaterial` 半透明叠加在高对比度表面的物理结果。**

修复路径：**Phase 7**（降低 atmosphere.opacity 或调整 atmosphere.color 饱和度）。
E1-R3 在贴图层无法修复此问题（即使贴图更暗，atmosphere 提亮量绝对值不变）。

**大气层提亮量化（noon mode）：**
```
atmosphere 提亮量：
  Pacific Deep:  ΔL = +9.9  L* unit（tex_L=21.4，ΔL/tex_L = 46%）
  Indian Deep:   ΔL = +22.3 L* unit（tex_L=20.8，ΔL/tex_L = 107%）

atmosphere color: #b0d9ed = RGB(176, 217, 237)
  线性 L* 计算值 ≈ 85.3（纯大气层颜色的亮度）
  opacity=0.14 时理论叠加贡献：
    0.14 × 85.3 + 0.86 × 21 ≈ 12.0 + 18.1 ≈ 30 L*（粗估，不考虑 3D 视角）
  实测 31.3（Pacific）与理论值接近，验证大气层叠加为主要机制。
  Indian Deep ΔL 更大（+22.3），可能与该点太阳角度和大气壳视角效果叠加有关。
```

> ⚠ 深海明亮感是 E1-R1 报告中"D 类高风险（High Risk）"采样点的主因之一，
> 现已由本轮实测明确归因为 **runtime 层（atmosphere）**，E1-R3 无法从贴图侧修复。

### 6.4 热带浅海（Tropical Shallow）— 贴图层主因

| 点 | ΔL | 结论 |
|---|---|---|
| Bahamas | −4.0 | 采样含陆地（S%=20 vs tex 44），方向成立：runtime 不提亮热带浅海 |
| Boracay | +1.5 | Runtime 几乎中性；浅海层次/色相问题在贴图层 |

**归因结论：热带浅海"层次不足 / 颜色不准"主要属于贴图层问题，
runtime noon 对浅水区几乎中性（ΔL < 2），Phase 7 无法解决浅水色差。**

修复路径：**E1-R3 / D5z 强候选方向**（浅水增强在贴图层操作）。
但必须等待 E1-R4A Regional Visual Preview 后方可进入正式候选；
不得在 E1-R2 阶段生成候选，不得直接进入 production。

---

## 7. 核心归因汇总

| 视觉问题 | Runtime ΔL（实测） | Runtime 是否主因 | 贴图层现状 | 修复路径 | 优先级 |
|---|---|---|---|---|---|
| 沙漠亮度 | −0.1 ~ +0.4（中性） | 否 | tex_L=71–72，属合理范围，不判定过曝 | E1-R3 **观察项** | 低 |
| 极地高亮 | −7.9 ~ −1.4（轻度压暗） | 否 | tex_L=89–92，冰盖正常值，不判定缺陷 | E1-R3 **谨慎观察项** | 低 |
| 深海偏亮/冷白 | **+9.9 ~ +22.3（显著提亮）** | **是** | tex_L=20–22，贴图暗但被 atmosphere 提亮 | **Phase 7 强候选** | 高 |
| 热带浅海层次不足 | −4.0 ~ +1.5（中性） | 否 | 色相/饱和属贴图层问题 | E1-R3/D5z **强候选** | 高 |

---

## 8. E1-R3 影响评估

基于本轮归因，E1-R3 候选生成的范围和约束：

| 类别 | E1-R3 处理方向 | 分组 | 说明 |
|---|---|---|---|
| 热带浅海（A 类） | 色相修正 + 浅水层次增强（D5z 专项） | **强候选** | 主要处理对象；须通过 E1-R4A 预览 |
| 海洋饱和度（全局） | 回调 D5b 降饱和过量部分 | **强候选** | 与热带浅海协同；须通过 E1-R4A 预览 |
| 沙漠（E 类） | **不建议主动调整**；若有调整须经 E1-R4A 确认 | **观察项** | tex_L=71–72 在合理范围，不判定为过曝 |
| 极地（F 类） | **不建议主动压暗**；若调整须保留洁净感，须经 E1-R4A | **谨慎观察项** | 内陆冰盖高 L* 属正常，不判定为缺陷 |
| 深海（D 类） | **禁止在贴图层暗化** | 禁止项 | Atmosphere 提亮量固定；贴图变暗只会加剧脏感 |

**深海不得暗化原则：**
```
若 E1-R3 将 D 类贴图从 tex_L=21 降至 tex_L=15：
  atmosphere 提亮仍约 +10~22 L*
  屏幕结果 scr_L 约 25–37，视觉更加均匀模糊
  贴图与 runtime 反差加剧，更难后续调整
→ 深海问题须从 Phase 7（降低 atmosphere opacity/color）解决，不得在 E1-R3 处理
```

---

## 9. Phase 7 影响评估

Phase 7（lighting / atmosphere 调整）的范围和优先级：

| 问题 | Phase 7 必要性 | 建议方向 |
|---|---|---|
| 深海偏亮（ΔL +10~+22） | **必要** | 降低 atmosphere.opacity（0.14→0.10）或调整 atmosphere.color 饱和度 |
| 沙漠过白 | 非必要 | 根因在贴图，Phase 7 操作沙漠无意义 |
| 极地过曝 | 非必要 | 根因在贴图，runtime 已轻度压暗极地 |
| 热带浅海层次 | 非必要 | 根因在贴图，Phase 7 无法改善浅水色差 |

> Phase 7 仅需针对深海 atmosphere 提亮问题介入。
> E1-R2 归因审计完成后，Phase 7 工作项已可明确定义。

---

## 10. 采样质量说明

### 有效测量（9 点）

| 点 | 采样质量 | 备注 |
|---|---|---|
| Sahara_Libya | 高 | 撒哈拉沙漠中心清晰，无混入 |
| Arabian_Desert | 高 | 阿拉伯半岛清晰 |
| Australia_Simpson | 高 | 澳洲内陆，仅含陆地像素 |
| Antarctica_Inland | 中 | 中心在冰/海边界，p5 偏低；均值 81.7 可参考 |
| Greenland_Inland | 高 | 格陵兰冰盖内陆，最干净的极地样本 |
| Pacific_Deep | 高 | 西太平洋深海，均质深蓝 |
| Indian_Deep | 高 | 印度洋深海，均质深蓝 |
| Bahamas | 中 | 中心含美国东海岸陆地（S%=20 vs tex 44%）；L*=40.9 低于 tex 44.9；方向成立 |
| Boracay | 中-高 | 菲律宾海域，含少量岛陆 |

### 无效测量（1 点）

| 点 | 问题 | 处理 |
|---|---|---|
| Ross_Ice_Shelf (−175°E, −80°S) | 采样中心落在 Southern Ocean（S%=30, L*=47），非冰盖区域 | **数据标记 sample_valid=false，不参与归因** |

> Ross Ice Shelf 数据已在 JSON/CSV 中保留，sample_valid=false，供审计记录。
> 极地冰盖归因以 Antarctica_Inland 和 Greenland_Inland 两点为准。

### 采样中心计算说明

```
canvas CSS 位置：x=385, y=16; 宽=430, 高=712
截图分辨率：2400×1488（设备像素 2×Retina）
canvas 设备像素区域：(770,32)–(1630,1456)
canvas 中心设备像素：(1200, 744)
采样窗口：100×100 device px = 50×50 CSS px = 约 ±25 CSS px

截图时 setDebugLocation(lon, lat) 将 (lon, lat) 旋转至画布正中心，
globe 中心即为目标地理点，采样结果代表该点的 runtime 合成亮度。
```

---

## 11. 数据文件输出

| 文件 | 路径 | 状态 |
|---|---|---|
| 审计报告 | `docs/e1_r2_noon_exposure_audit.md` | 本文件（未提交） |
| JSON 测量数据 | `docs/metrics/e1_r2_noon_runtime_measurements.json` | 已写入（未提交） |
| CSV 测量数据 | `docs/metrics/e1_r2_noon_runtime_measurements.csv` | 已写入（未提交） |
| 截图原始文件 | `/tmp/e1r2_*.png`（Sahara, Greenland, Ross, Antarctica, Australia, Bahamas） | 已保存，临时目录 |

> 截图不进入 docs / production / candidates；仅作测量辅助用途。

---

## 12. 最终结论

### 12.1 归因清单（E1-R2 结论）

```
沙漠（Sahara tex_L=71.5）   → runtime ΔL=−0.1，几乎中性
                              → 不判定为贴图层过曝（L*=71–72 属合理范围）
                              → 列为 E1-R3 观察项，非强制修复

极地（Greenland/Antarctica） → runtime ΔL=−1.4~−7.9，轻度压暗
                              → 不判定为 runtime 过曝，不推导贴图须压暗
                              → 列为 E1-R3 谨慎观察项，非第一优先修复

深海（Pacific/Indian）       → runtime ΔL=+9.9~+22.3，atmosphere 显著提亮
                              → 根因为 runtime 层（atmosphere opacity/color）
                              → Phase 7 强候选；不得在贴图层压暗处理

热带浅海（Boracay/Bahamas）  → runtime ΔL≈0，中性
                              → 层次/色相问题属贴图层，E1-R3/D5z 强候选方向
                              → 须等待 E1-R4A Regional Visual Preview 后方可生成候选
```

### 12.2 修复路径（三组）

#### E1-R3 强候选项

1. 热带浅海色相修正（H° 向青蓝方向，195–210°）；
2. 海洋整体降饱和过量的回调（D5b 对 BMNG 降饱和约 −10.2%，可部分回调）；
3. D5z 近海浅水层次增强（A 类采样点）。

#### E1-R3 观察项

1. 沙漠是否需要轻微局部亮度调整（tex_L=71–72，当前不判定为过曝）；
2. 极地是否需要保护性微调（tex_L=89–92，当前不判定为缺陷）。

> 沙漠和极地不得作为第一优先贴图修改项。
> 后续如有调整需求，必须通过 E1-R4A Regional Visual Preview 确认，
> 避免沙漠变脏（灰化）、极地变灰（失去洁净感）。

#### Phase 7 强候选项

1. noon atmosphere opacity 调整（现状 0.14，建议实验范围 0.08–0.10）；
2. noon atmosphere color 中性化（现状 #b0d9ed 偏冷蓝）；
3. 深海 runtime 提亮量验证（调整后重测 Pacific/Indian Deep ΔL）；
4. sun / specular 对浅色表面（沙漠/极地）的影响观察（非主要问题，可作附属验证）。

### 12.3 E1-R2 对后续阶段的解锁

| 后续阶段 | 解锁状态 | 备注 |
|---|---|---|
| E1-R3 候选生成 | ✅ 已解锁 | 热带/饱和方向明确；沙漠/极地作为观察项 |
| D5z（浅水增强） | ✅ 已解锁 | 热带浅海 runtime 中性，贴图层修改有效 |
| Phase 7（lighting 调整） | ✅ 工作项明确 | 深海 atmosphere 提亮问题已量化（+10~+22 L*） |
| production decision | ❌ 未解锁 | 须完成 E1-R4A Regional Visual Preview 后方可 |

### 12.4 结论适用边界

```
本轮结论仅适用于：
  贴图：d5b_design_v3_2_1（候选，非 production 默认）
  模式：noon（themeHour=13）
  Browser：Chrome 149，设备 Retina 2× 显示

本轮结论不适用于：
  其他时段（dawn / evening / night）
  其他贴图候选（D5z 等）
  调整 atmosphere 参数后的渲染效果
```

---

*本报告数据不授权直接进行 E1-R3 候选生成或 Phase 7 参数修改。
所有下游操作须经 RW 明确确认后方可执行。*
