# moonView 构图 + farOrbit 回归验证报告

> 生成时间：2026-07-20
> 验证：Playwright + 系统 Chrome (swiftshader)，静态服务器 `static_pwa.js` (`:8080`)
> 验收：全部 5 项 PASS，几何级月亮边距检查通过

---

## 1. 改动总览

### Step 1 — `pwa/earth3d.js`：新增 `moonView` 构图（纯新增，Category A）

| 字段 | 值 | 说明 |
|------|-----|------|
| 名称 | `moonView` | 紧挨 lunarHalo 插入 CAMERA_COMPOSITIONS |
| lat / lon | 31.23 / 121.47 | 同 deepSpace / lunarHalo |
| cameraOffsetZ | **48.0** | 相机距地心 ≈48 ∈ [MOON_VISIBLE_DIST(35), MOON_HIDE_DIST(65)) |
| fov | 28 | 同其他远档构图 |

- 已加入 `FAR_COMPOSITIONS` 集合（与 lunarHalo 同机制：FAR_VIEW 太阳经度对齐）。
- 未修改任何现有构图条目。

**几何保证（月亮完整在框内）**：
相机距地心=48，月亮距地心=6 → 最大角偏移 = asin(6/48)=7.18° << FOV/2(14°)。无论月亮出现在画面任何方向，其中心到视轴角偏 ≤7.2°，加上月亮自身半径 ≈1.17°，总角范围 ≤8.35° < 14°。**月亮任意方向都完整在框内，不贴边、不裁切。**

### Step 2 — `pwa/real-celestial.js`：月亮可见性下限提升

| 常量 | 旧值 | 新值 | 说明 |
|------|------|------|------|
| `MOON_VISIBLE_DIST` | **20** | **35** | farOrbit(25.15) 越出下界 → 不再显示月亮；moonView(48)/lunarHalo(58) 仍在 [35,65) 区间 |
| `MOON_HIDE_DIST` | 65 | 65（不变） | deepSpace(80) 越过上界 → 月亮隐藏 |
| `MOON_DIST` | 6 | 6（不变） | 月亮距地心 = 3 R_earth，保留上次拉开的视觉分离 |

**farOrbit 的有意行为变化**：从"显示月亮（可能裁切）"回归为 #52 之前的"纯地球远景，无任何天体"。这是本轮设计意图。

---

## 2. 新四档分层矩阵

| 构图 | 距地心 | 月亮 | 太阳 | 行星 | 公转环* | 用途 |
|------|--------|------|------|------|---------|------|
| near / homeGlobe | ~5 | ✗ | ✗ | ✗ | ✗ | 近景地球（零影响） |
| **farOrbit** | ~25.15 | **✗** | ✗ | ✗ | ✗ | **纯地球远景（回归 #52 原始用途）** |
| **moonView（新）** | **~48** | **✓** | ✗ | ✗ | ✗ | **月亮专属，完整在框** |
| **lunarHalo** | ~58 | ✓ | ✓ | ✗ | ✓ | 月亮+太阳同框 |
| deepSpace | ~80 | ✗ | ✓ | ✓ | ✓ | 太阳+五行星 |

\* 公转环绑定 SUN_VISIBLE_DIST(50)，故 moonView 不显示（camDist<50），lunarHalo/deepSpace 显示。

---

## 3. 几何级"月亮完整在框内"证明（NDC 空间，非像素计数）

> 用户明确要求："不只看 moonVisible 布尔值和像素计数"，需要月亮确实完整在框内的硬证据。
> 本报告采用 **NDC 归一化设备坐标空间**的几何边框检查——分辨率无关、数学严谨、不依赖像素计数。

### 方法论

月亮是 THREE.Mesh（SphereGeometry + 相位着色器），世界半径 `r = camToMoon × tan(MOON_ANG_DIAM/2)`。其在 NDC 空间的半高/半宽：

```
ndcHalfH = tan(MOON_ANG_DIAM/2) / tan(FOV/2)     ← 与分辨率无关
ndcHalfW = ndcHalfH / aspect                       ← 水平受 aspect 拉伸
```

月亮 NDC 中心 `C = (cx, cy)`（由 `getState().moonNDC` 提供）。月亮圆盘 NDC 边界：
- 左 = cx − ndcHalfW, 右 = cx + ndcHalfW
- 下 = cy − ndcHalfH, 上 = cy + ndcHalfH
- 视口边界 = [-1, 1]²

**inFrame 条件**：四边 margin ≥ 0（即边界不超出 [-1,1]）。

### 实测数据（moonView 构图）

| 参数 | 值 |
|------|-----|
| 相机距地心 camDistEarth | 48.02 场景单位 |
| 月亮可见性 | true |
| 月亮 NDC 中心 (cx, cy) | (0.131, 0.369) |
| 月亮渲染角直径 MOON_ANG_DIAM | 2.33°（4.5×真实 0.518°） |
| 相机 FOV | 28°（half = 14°） |
| 视口 aspect | 1.667（1000/600） |
| **ndcHalfH（垂直半径）** | **0.0816** |
| **ndcHalfW（水平半半径）** | **0.0490** |

**四边 NDC 余量（margin）：**

| 方向 | 计算式 | NDC 余量 | 像素余量（@1000×600） |
|------|--------|----------|------------------------|
| 左 | (0.131−0.049) − (−1) = **1.082** | 1.082 | 325 px |
| 右 | 1 − (0.131+0.049) = **0.820** | 0.820 | 246 px |
| 下 | (0.369−0.082) − (−1) = **1.288** | 1.288 | 386 px |
| 上 | 1 − (0.369+0.082) = **0.549** | 0.549 | **165 px** |

**最小余量 minMargin = 0.549 NDC = 165 px**（上边缘，最紧方向）。月亮距离最近的画面边缘有 165 像素的安全空间。

### 结论：**月亮完整在框内，无贴边、无裁切** ✅

---

## 4. farOrbit 裁切问题对比（几何证明）

上一轮 MOON_VISIBLE_DIST=20 时，farOrbit(25.15) 会显示月亮。但此时月亮的最大角偏移已接近 FOV 边界：

| 场景 | camDist | 最大角偏移 | NDC 中心 | NDC 半径 | 上边缘 | 裁切？ |
|------|---------|-----------|----------|----------|--------|--------|
| **farOrbit（旧）** | 25.15 | 13.80° | 0.986 | 0.0816 | **1.067 > 1** | **✅ 会裁切** |
| **moonView（新）** | 48.0 | 7.18° | 0.513 | 0.0816 | **0.594 < 1** | **❌ 安全** |

- farOrbit 最坏情况下月亮上边缘超出画面 6.7% NDC（约 20 像素被截断）。
- moonView 最坏情况下月亮上边缘距画面边缘仍有 40.5% NDC 余量（121 像素安全区）。
- **将月亮展示职责从 farOrbit 迁移到 moonView 从根本上消除了裁切风险。**

---

## 5. Playwright 验收结果（5/5 PASS）

| 测试 | 结果 | 关键证据 |
|------|------|---------|
| **T1 默认路径零影响** | ✅ PASS | `realCelestialMounted=false`, 错误 0 |
| **T2 farOrbit 回归** | ✅ PASS | 月亮/太阳/行星/公转环 **全部 false**（有意变更，截图确认纯地球远景） |
| **T3 moonView（新构图）** | ✅ PASS | `moonVisible=true`; 几何 inFrame=true; **minMargin=0.55 NDC (165px)**; 经 `transitionToComposition` 正常导航 |
| **T4 lunarHalo 不变** | ✅ PASS | `moonVisible=true, sunVisible=true, planetsVisible=false`（与上次一致）|
| **T5 deepSpace 不变** | ✅ PASS | `moonVisible=false, sunVisible=true, planetsAllVisible=true`（5 星全显，月亮确认消失）|

各构图相机距实测：`farOrbit=25.19`, `moonView=48.02`, `lunarHalo=58.02`, `deepSpace=80.01`

---

## 6. 交付物

| 文件 | 说明 |
|------|------|
| `pwa/earth3d.js` | 新增 `moonView` 构图（CAMERA_COMPOSITIONS）；加入 FAR_COMPOSITIONS |
| `pwa/real-celestial.js` | MOON_VISIBLE_DIST 20→35；更新注释（三档→四档矩阵） |
| `/tmp/rodio_assets/verify_moonview.js` | 验收脚本（含 NDC 几何边框检查） |
| `figures/moonview_default_home.png` | 默认路径零影响 |
| `figures/moonview_farOrbit.png` | farOrbit：纯地球远景（天体全隐，有意变更） |
| `figures/moonview_moonView.png` | **moonView：月亮完整在框（几何余量 165px）** |
| `figures/moonview_lunarHalo.png` | lunarHalo：不变（月亮+太阳） |
| `figures/moonview_deepSpace.png` | deepSpace：不变（太阳+五行星，月亮消失） |
| `figures/verify_moonview_report.json` | 结构化验收数据（含几何边距） |
