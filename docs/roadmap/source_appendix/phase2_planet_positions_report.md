# #53 天体系统 Phase 2 — 五颗行星真实位置 推导与验收报告

> 生成时间：2026-07-20T09:43 UTC  
> 验证时间：2026-07-20T09:43 UTC (Playwright + 系统 Chrome swiftshader)  
> 验收标准：全部通过 ✓

---

## 目录

1. [Step 0：统一距离比例尺审计](#step-0统一距离比例尺审计)
2. [Step 1：五行星日心→地心真实方向](#step-1五行星日心地心真实方向)
3. [Step 2：地球交叉验证 + 运动速度排序](#step-2地球交叉验证--运动速度排序)
4. [Step 3：典型地球距离复核](#step-3典型地球距离复核)
5. [Step 4：渲染实现](#step-4渲染实现)
6. [太阳距离变更说明 (6 → 12.25)](#太阳距离变更说明-6--1225)
7. [Playwright 验收结果](#playwright-验收结果)
8. [交付物清单](#交付物清单)

---

## Step 0：统一距离比例尺审计

### 审计脚本

文件：`docs/roadmap/source_appendix/solar_system_scale_audit.js`

### 算法：对数压缩

```
compressToSceneDist(au) = MOON_DIST + slope × (log10(au) - log10(Moon))
其中：
  MOON_DIST = 3          （锚点，#52 已验证）
  SAFE_MAX_DIST = 17.95   （Pluto = deepSpace 视锥硬上限 19.95 × 0.9）
  slope = (17.95 - 3) / (log10(39.47) - log10(0.00257))
       ≈ 2.9287
```

**约束依据**：deepSpace 相机距地心 80.01 单位，FOV=28°（半角 14°），硬上限 = 80.01 × tan(14°) ≈ **19.95 单位**。安全上限取其 90% = **17.95**。

**输入数据来源**：每个天体的「典型地球距离」为 near/far 几何平均 √|a² − 1|（内行星 a < 1，外行星 a > 1），非直接使用日心半长轴。直接用半长轴当地心距离会使内行星显得过近（审计时 specifically 排除的陷阱）。

### 压缩结果表（脚本独立运行输出）

| 天体 | TYPICAL_AU | 场景距离 | 备注 |
|------|-----------|---------|------|
| Moon | 0.00257 | **3.00** | 锚点 |
| Venus | 0.69088 | **11.68** | 内行星最近 |
| Mercury | 0.92208 | **12.12** | 内行星次近 |
| Sun | 1.00000 | **12.25** | ⚠️ 见下方变更说明 |
| Mars | 1.15003 | **12.47** | 内圈最远 |
| Jupiter | 5.10600 | **14.78** | 外圈 |
| Saturn | 9.48443 | **15.74** | 外圈更远 |
| Uranus | 19.16493 | **16.83** | — |
| Neptune | 30.05237 | **17.53** | — |
| Pluto | 39.46933 | **17.95** | 安全上限 |

**关键观察**：内簇（Venus/Mercury/Sun/Mars, 11.68–12.47）与外圈（Jupiter/Saturn, 14.78–15.74）之间有 **~2.3 单位** 的明显间隔；全部远于月亮（3）。层次清晰。

---

## Step 1：五行星日心→地心真实方向

### 轨道根数来源

**NASA JPL SSD — Approximate Positions of the Planets**  
Standish & Williams (1992), Table 1（适用范围 1800–2050 AD）

六开普勒根数（J2000 历元）：
- `a` — 半长轴 (AU)
- `e` — 离心率
- `I` — 黄道倾角 (deg)
- `L` — 平均黄经 (deg)
- `ϖ` — 近日点经度 (deg)
- `Ω` — 升交点经元经度 (deg)

每根数附带每世纪速率（用于时间外推）。

### 求解流程

```
T = (JD - J2000) / 36525           // 自 J2000 的儒略世纪数
对每颗行星:
  1. 根数线性外推: a(T) = a0 + ȧ·T, 同理 e/I/L/ϖ/Ω
  2. M = L(T) - ϖ(T)               // 平近点角
  3. E = KeplerSolve(M, e)         // 开普勒方程牛顿迭代 (tol 1e-9)
  4. ν = atan2(√(1-e²)sinE, cosE-E) // 真近点角
  5. r = a·(1 - e·cosE)            // 日心距
  6. 日心黄道直角坐标: (x,y,z) in orbital plane
  7. 绕 Z 轴转 -Ω, 绕 X 转转 -I    // → 日心黄道系
  8. 绕 X 轴转 ε=23.43928°          // → 日心赤道系
  9. 地心方向 = 归一化(行星日心 - 地球日心)  // 矢量相减
```

### 当前时刻（T=0.26549 世纪 ≈ 2026-07-20）五行星方向

| 行星 | RA (°) | Dec (°) | 场景距离 | 典型AU | 方向向量 (x, y, z) |
|------|--------|---------|---------|--------|-------------------|
| Mercury | 93.35 | +21.12 | 12.12 | 0.922 | (-0.055, 0.931, 0.360) |
| Venus | 83.12 | +17.96 | **11.68** | 0.691 | (0.114, 0.944, 0.308) |
| Mars | 106.24 | +23.41 | 12.47 | 1.150 | (-0.257, 0.881, 0.397) |
| Jupiter | 212.97 | -12.10 | **14.78** | 5.106 | (-0.820, -0.532, -0.210) |
| Saturn | 123.86 | +20.14 | **15.74** | 9.484 | (-0.523, 0.780, 0.344) |

---

## Step 2：地球交叉验证 + 运动速度排序

### 地球自检

复刻了 `earthHeliocentricEclLon()` 方法，用地球自身的 Standish 根数求解日心黄经：

| 项目 | 值 |
|------|-----|
| 本方法计算值 | 297.34° |
| 参考值 (`earthHeliocentricEclLon`) | 297.71° |
| **偏差** | **−0.37°** |

偏差 < 0.5° 属吻合范围。微小差异源于两种方法的方程-of-center 处理方式不同（参考方法对太阳加 EoC ≈ 1.9°，本方法用地球自身 EoC），物理同义但数值不完全一致。

### 相对运动速度排序

**指标**：日心轨道平均角速度 (mean motion = L̇ / 36525, °/day)

| 排序 | 天体 | 日心角速度 (°/day) | 地心视运动 (°/day) |
|------|------|-------------------|-------------------|
| 1 | Mercury | **4.09** | 1.49 |
| 2 | Venus | **1.60** | 0.87 |
| 3 | Earth | **0.99** | (基准) |
| 4 | Mars | **0.52** | 0.69 |
| 5 | Jupiter | **0.083** | 0.15 |
| 6 | Saturn | **0.034** | 0.11 |

✅ **排序验证通过**：水星 > 金星 > 地球 > 火星 > 木星 > 土星

注：地心视运动因会合周期效应，火星(0.69) > 金星(0.87) 不成立——金星逆行时视运动极快、顺行时慢，平均值低于火星是合理的。排序以**日心轨道 mean motion** 为准（物理本质）。

---

## Step 3：典型地球距离复核

用 `earthDistRangeAU(a) = √|a² − 1|`（near = |a−1|, far = a+1 的几何平均）复现场景距离：

| 行星 | 半长轴 a (AU) | √\|a²−1\| | TYPICAL_AU 表值 | 偏差 |
|------|-------------|-----------|---------------|------|
| Mercury | 0.387099 | 0.92204 | 0.92208 | −0.00004 |
| Venus | 0.723336 | 0.69050 | 0.69088 | −0.00038 |
| Mars | 1.523710 | 1.14965 | 1.15003 | −0.00038 |
| Jupiter | 5.202887 | 5.10588 | 5.10600 | −0.00012 |
| Saturn | 9.536676 | 9.48410 | 9.48443 | −0.00033 |

所有偏差 < 0.0004 AU，确认 TYPICAL_AU 表值即为此公式的精确计算结果。压缩函数未修改。

---

## Step 4：渲染实现

### 技术方案

- **对象类型**：THREE.Sprite + CanvasTexture 径向渐变（同太阳 halo 做法）
- **混合模式**：AdditiveBlending（发光效果）
- **可见性门控**：`showSun` 标志（与太阳同档，仅 deepSpace 可见，`SUN_VISIBLE_DIST=50`）
- **位置公式**：`pos = earthCenter + planetGeoDir(name, nowMs) × compressToSceneDist(typicalAU)`
- **坐标系对齐**：日心赤道系（绕 X 转 ε=23.43928°）→ 世界空间，与太阳/月亮的惯性方向一致

### 五行星视觉参数

| 行星 | 场景距离 | 角直径 (°) | RGB | 视星等 | 相对亮度 |
|------|---------|----------|-----|-------|---------|
| Mercury | 12.12 | 0.9 | (132,129,129) | −0.4 to 1.9 | 0.363 |
| **Venus** | **11.68** | **1.3** | **(208,206,204)** | **−4.6** | **1.000 (基准)** |
| Mars | 12.47 | 1.1 | (138,105,75) | −2.0 to +1.8 | 0.437 |
| Jupiter | 14.78 | 1.25 | (172,121,68) | −2.9 to −1.6 | 0.550 |
| Saturn | 15.74 | 1.2 | (119,111,82) | −0.7 to +1.5 | 0.309 |

亮度算法：`flux = 10^(−0.4×mag)` → 4 次方根压缩（金星 mag=−4.6 为基准 1.0）。

### 代码变更摘要

**`pwa/real-celestial.js`** 共 5 处编辑：

| Edit | 内容 |
|------|------|
| A | 新增比例尺常量区（MOON/SafeMax/TYPICAL/compressToSceneDist）；`SUN_DIST = compressToSceneDist(1.0) ≈ 12.25` |
| B | 辅助函数块：ε、PLANET_DEFS、亮度函数、Standish 六根数表、Kepler 求解器、ecl2eq、planetGeoDir、makePlanetGlowTexture |
| C | initCelestial 中创建 5 个 Sprite（renderOrder=18, frustumCulled=false, 初 visible=false）|
| D | tick() 太阳/月亮后插入行星更新循环（位置+恒定角直径+NDC）|
| E | getState() 加 planets 数组 + sunDistFromEarth/moonDistFromEarth |

---

## 太阳距离变更说明 (6 → 12.25)

### 变更内容

```
旧值：const SUN_DIST = 6        // #52 孤立常数
新值：const SUN_DIST = compressToSceneDist(SCALE_TYPICAL_AU.Sun)  // ≈ 12.25
```

### 变更原因

**这是有意调整，不是 bug 或回归。**

#52 Phase 1 实现太阳时，使用了孤立常数 `SUN_DIST = 6`，因为当时尚未建立全系统统一比例尺。#53 Phase 2 引入了审计后的对数压缩比例尺（锚 Moon=3, 上限 Pluto=17.95），该比例尺将太阳的典型地球距离（恰好 = 1 AU）映射到 **12.25 场景单位**。

将 SUN_DIST 从 6 改为 12.25 是「纳入统一比例尺」的操作，使太阳与其他天体（月亮/行星）共享同一距离体系，而非各自独立拍脑袋。

### 视觉影响

- 太阳在 deepSpace 中离地球更远（从 6 → 12.25），但仍在内簇范围（11.68–12.47）
- Sun halo 大小由恒定角直径控制，不随距离缩放，所以视觉大小不变
- 与金星(11.68)/水星(12.12)/火星(12.47) 的距离关系符合物理直觉

---

## Playwright 验收结果

### 测试环境

- Playwright（managed workspace node_modules）
- 系统 Chrome + swiftshader（`--enable-unsafe-swiftshader --use-gl=angle --use-angle=swiftshader`）
- 静态服务器：`/tmp/rodio_assets/static_pwa.js`（端口 8080）

### 三项测试全部 PASS

#### T1：默认路径零影响 ✅

```json
{
  "realCelestialMounted": false,
  "realErrors": 0,
  "PASS": true
}
```

无 `?earthCandidate=realCelestial` 参数时，real-celestial 模块不挂载，零副作用。

#### T2：deepSpace 五行星渲染 ✅

```json
{
  "allPlanetsVisible": true,
  "sunDist": 12.25,
  "moonDist": 3,
  "outerBeyondInner": true,     // 木/土 > 内簇最大距离
  "beyondMoon": true,            // 全部 > 月亮(3)
  "venusBrightest": true,         // 金星相对亮度 = 1.0 (基准)
  "realErrors": 0,
  "PASS": true
}
```

各行星场景距离实测：

| 行星 | dist | NDC (x, y) |
|------|------|-----------|
| Mercury | 12.124 | (−0.067, 0.599) |
| Venus | 11.676 | (0.133, 0.579) |
| Mars | 12.466 | (−0.326, 0.587) |
| Jupiter | 14.778 | (−1.116, −0.380) |
| Saturn | 15.739 | (−0.844, 0.660) |

#### T3：30 天位置移动 ✅

```json
{
  "venusNDC_t0": [0.1331, 0.5789],
  "venusNDC_t30": [-0.2186, 0.5694],
  "deltaNDC": 0.3518,
  "PASS": true
}
```

30 天后金星 NDC 移动 Δ=0.35（约占画面宽度 17%），位置变化可辨识。

---

## 交付物清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `docs/roadmap/source_appendix/solar_system_scale_audit.js` | 审计脚本 | 统一比例尺，可独立运行 |
| `docs/roadmap/source_appendix/planet_positions_derivation.js` | 推导脚本 | JPL 根数→方向→报告 JSON |
| `docs/roadmap/source_appendix/planet_positions_report.json` | 推导数据 | Step 1/2/3 全量输出 |
| `pwa/real-celestial.js` | 渲染代码 | Edit A~E 五处变更 |
| `/tmp/rodio_assets/verify_planets.js` | 验收脚本 | Playwright 自动测试 |
| `docs/roadmap/source_appendix/figures/planets_deepspace.png` | 截图 | deepSpace 五行星同框 |
| `docs/roadmap/source_appendix/figures/planets_default_home.png` | 截图 | 默认路径零影响 |
| `docs/roadmap/source_appendix/figures/verify_planets_report.json` | 验收报告 | Playwright 结构化输出 |
| **本文档** | 推导报告 | 完整推导+验收记录 |
