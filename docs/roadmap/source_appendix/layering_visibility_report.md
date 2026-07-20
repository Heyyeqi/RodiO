# 天体场景构图分层 — 月亮距离 + 中间构图 + 可见性拆分 验收报告

> 生成时间：2026-07-20  
> 验证：Playwright + 系统 Chrome (swiftshader)，静态服务器 `static_pwa.js` (`:8080`)  
> 验收：全部 5 项 PASS，月亮像素级检测佐证

---

## 1. 改动总览

### Step 1 — `pwa/real-celestial.js`：月亮距离 + 可见性拆分

| 项 | 旧值 | 新值 | 说明 |
|----|------|------|------|
| `MOON_DIST` | 3 | **6** | 月亮距地心 = 3 R_earth；与地球(半径2)明显分离，不再贴着/穿透 |
| `MOON_HIDE_DIST` | — | **65**（新增） | 月亮隐藏上界；deepSpace(80) 越过 → 月亮隐藏 |
| `PLANETS_VISIBLE_DIST` | — | **70**（新增） | 行星独立可见下界；不再与太阳共用阈值 |
| `MOON_VISIBLE_DIST` | 20 | 20（不变） | 月亮可见下界 |
| `SUN_VISIBLE_DIST` | 50 | 50（不变） | 太阳可见下界 |

**可见性判断逻辑（按相机→地心实际直线距离，不按构图名）：**
```js
showMoon    = camDistEarth >= MOON_VISIBLE_DIST  && camDistEarth < MOON_HIDE_DIST   // [20, 65)
showSun     = camDistEarth >= SUN_VISIBLE_DIST                                        // [50, ∞)
showPlanets = camDistEarth >= PLANETS_VISIBLE_DIST                                    // [70, ∞)
```
- 月亮 `moon.visible = showMoon`（新增上界，拆分出"中间档可见、deepSpace 隐藏"）
- 行星 `P.visible = showPlanets`（**从复用 `showSun` 改为独立判断**）
- 太阳 `sun.visible = showSun`（不变）

### Step 2 — `pwa/earth3d.js`：新增中间构图 `lunarHalo`

纯新增条目，**未修改任何现有构图**（Category A 纪律）：
```js
lunarHalo: {
  lat: 31.23, lon: 121.47,
  cameraOffsetZ: 58.0,   // 相机距地心 ≈58，落在 [SUN_VISIBLE_DIST(50), MOON_HIDE_DIST(65)) 区间
  fov: 28,
}
```
- 参照 `deepSpace` 写法（固定 `cameraOffsetZ`，非 `earthDiameterPct` 百分比公式）。
- 同步将 `'lunarHalo'` 加入 `FAR_COMPOSITIONS` 集合 —— 使该构图获得 FAR_VIEW 太阳经度对齐处理（与 farOrbit/deepSpace 同机制），保证太阳在画面内成帧。仅新增集合成员，不改现有条目。

---

## 2. 三档拆分阈值命名（可扩展模式）

RW 要求阈值命名遵循 `XXX_VISIBLE_DIST` / `XXX_HIDE_DIST` 模式，便于未来扩展。当前边界（相机距地心，场景单位）：

| 天体 | 可见区间 | 常量 |
|------|---------|------|
| 月亮 | [20, 65) | `MOON_VISIBLE_DIST` / `MOON_HIDE_DIST` |
| 太阳 | [50, ∞) | `SUN_VISIBLE_DIST` |
| 行星 | [70, ∞) | `PLANETS_VISIBLE_DIST` |

**构图 × 天体可见性矩阵**（camDist 由 `cameraOffsetZ` 决定）：

| 构图 | camDist | 月亮 | 太阳 | 行星 | 公转环* |
|------|---------|------|------|------|--------|
| near / homeGlobe | ~5 | — | — | — | — |
| farOrbit | ~25 | ✅ | — | — | — |
| **lunarHalo（新）** | **~58** | **✅** | **✅** | — | ✅ |
| deepSpace | ~80 | — | ✅ | ✅ | ✅ |

\* 公转环/地球标记绑定 `SUN_VISIBLE_DIST`（与太阳同档），故 lunarHalo 与 deepSpace 均显示。这是既有设计，本次未改动；lunarHalo 显示轨道环属预期行为。

新增天体或新构图时，只需：(1) 加一对 `XXX_VISIBLE_DIST` / `XXX_HIDE_DIST` 常量；(2) 在对应天体的 tick 判断里加一行 `camDistEarth` 区间比较。无需重设计现有逻辑。

---

## 3. Playwright 验收结果（5/5 PASS）

| 测试 | 结果 | 关键证据 |
|------|------|---------|
| **T1 默认路径零影响** | ✅ PASS | `realCelestialMounted=false`, `realErrors=0` |
| **T2 farOrbit** | ✅ PASS | `moonVisible=true`, `sunVisible=false`, `planetsHidden=true`, `moonDist=6` |
| **T3 lunarHalo（新构图）** | ✅ PASS | `moonVisible=true`, `sunVisible=true`, `planetsHidden=true`, `moonDist=6`, `sunDist=12.25`；经 `transitionToComposition` 导航 |
| **T4 deepSpace** | ✅ PASS | **`moonVisible=false`**（月亮明确隐藏）, `sunVisible=true`, `planetsAllVisible=true` |
| **T5 月亮分离** | ✅ PASS | `moonDistFromEarth=6`, 与地球半径比 = 3.0（3 个地球半径，明显分离） |

各构图相机距实测：`farOrbit=25.19`, `lunarHalo=58.02`, `deepSpace=80.01`（与设定一致）。

---

## 4. 月亮"真的消失"像素级佐证（针对上次漏检）

用户特别要求 deepSpace 下月亮**确确实实**不可见，而非逻辑漏检。除 `getState().moonVisible=false` 的布尔证据外，追加屏幕像素检测（暖灰低饱和圆盘，排除右侧 Theme Tuner UI 面板区域）：

| 截图 | 最大暖灰簇面积 | 月亮存在？ |
|------|--------------|-----------|
| `layering_deepSpace.png` | 126 px（背景噪点级） | **否** ✅ |
| `layering_lunarHalo.png` | 674 px @ (521,387) | **是** ✅ |
| `layering_farOrbit.png` | 702 px @ (519,121) | **是** ✅ |

- 真实月亮圆盘签名 ≈ 680–700 px；deepSpace 仅 126 px 背景噪点 → 月亮确已隐藏。
- lunarHalo 月亮簇中心 (521,387) 与 `getState().moonNDC≈(-0.005, 0.273)` 推算的屏幕坐标 (500,364) 吻合。

---

## 5. 月亮距离 3 → 6 的视觉分离

- 旧 `MOON_DIST=3`：月亮角偏移 `atan(3/58)=2.96°`，地球边缘 `atan(2/58)=1.97°` → 月亮仅比地球边缘远 ~1°，**几乎贴着/穿透**。
- 新 `MOON_DIST=6`：月亮角偏移 `atan(6/58)=5.9°` → 比地球边缘远 ~3.9°，**明显分离**（lunarHalo 截图中月亮距地球中心屏幕距离 ~115px，地球屏幕半径 ~70px → 月心在地球边缘外 ~45px）。
- 视锥安全：farOrbit(25) `atan(6/25)=13.4° < FOV/2(14°)`；lunarHalo(58) `atan(6/58)=5.9°` 余量大。月亮与太阳均 `depthTest:false + frustumCulled:false`，合格构图内始终成帧。

---

## 6. 交付物

| 文件 | 说明 |
|------|------|
| `pwa/real-celestial.js` | MOON_DIST 3→6；新增 MOON_HIDE_DIST/PLANETS_VISIBLE_DIST；月亮上界 + 行星独立判断 |
| `pwa/earth3d.js` | 新增 `lunarHalo` 构图（CAMERA_COMPOSITIONS）；加入 `FAR_COMPOSITIONS` |
| `/tmp/rodio_assets/verify_layering.js` | 验收脚本（T1–T5） |
| `/tmp/rodio_assets/moon_detect.py` | 月亮像素级存在检测 |
| `docs/roadmap/source_appendix/figures/layering_default_home.png` | 默认路径零影响 |
| `docs/roadmap/source_appendix/figures/layering_farOrbit.png` | farOrbit：仅月亮 |
| `docs/roadmap/source_appendix/figures/layering_lunarHalo.png` | **新构图：月亮+太阳+轨道环** |
| `docs/roadmap/source_appendix/figures/layering_deepSpace.png` | deepSpace：太阳+五行星（**月亮消失**） |
| `docs/roadmap/source_appendix/figures/layering_moon_separation.png` | 月亮在 6 单位距离下与地球分离 |
| `docs/roadmap/source_appendix/figures/verify_layering_report.json` | 结构化验收数据 |
