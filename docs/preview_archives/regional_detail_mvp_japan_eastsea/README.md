# Regional Detail Layer MVP — Japan / East Sea

## 目的

验证 **Shader UV Region Blend** 技术：在 Three.js 球体上，通过 fragment shader 在特定经纬度区域内叠加高分辨率细节贴图，而不修改全局贴图或地球主渲染代码。

测试区域：日本/东海 (lon 118–148°E, lat 24–48°N)。

---

## 技术路线

```
全局 8K 贴图 (d5b_design_v3_2_1) — 始终渲染整个球体
         +
区域细节贴图 (1024×820 / 2048×1638) — 通过 shader 在 Japan 区域内 mix 叠加
         |
MeshPhongMaterial.onBeforeCompile → 注入 #include <map_fragment> 替换
```

技术关键点：
- 禁止修改 `earth3d.js`、`DAY_TEXTURE_VARIANT`、`pwa/assets`
- 细节贴图从 21.6K 源图直接裁切，不从 8K 放大
- 非方形贴图保持地理纵横比
- 距离自适应 blend：相机拉近时淡入，拉远时淡出

---

## 资产来源

| 资产 | 来源 | 说明 |
|---|---|---|
| `detail_japan_eastsea_1024.png` | `earth_day_source_21600x10800.jpg` 直接裁切 | 1873×1497 原始像素 → LANCZOS 降采样 |
| `detail_japan_eastsea_2048.png` | 同上 | 同一裁切区域，更高输出分辨率 |
| 全局贴图 | `d5b_design_v3_2_1_8192x4096.jpg` | 正式候选，只读，不替换 |

### 21.6K 源图有效分辨率审计结果

| 区域 | 21K 清晰度 | 8K 清晰度（上采样到同尺寸） | 比值 | 结论 |
|---|---|---|---|---|
| Kyushu / Japan Sea | 148.7 | 13.7 | **10.82×** | 21K clearly better |
| Korea South | 252.8 | 20.9 | **12.09×** | 21K clearly better |
| Shanghai / Yangtze | 136.8 | 7.7 | **17.78×** | 21K clearly better |
| Taiwan / Ryukyu | 32.7 | 6.5 | **5.05×** | 21K clearly better |
| Hokkaido / Sea of Japan | 32.1 | 6.8 | **4.68×** | 21K clearly better |
| **全区域综合** | — | — | **10.88×** | **USE 21.6K SOURCE** |

---

## 贴图规格：非方形设计

贴图输出为非方形，保持地理纵横比：

```
逻辑显示区域: lon 30° × lat 24°  → 宽高比 1.25
含 2% overdraw 的裁切区: lon 31.2° × lat 24.96° → 宽高比 1.250

1024 × 820  → 1.249 (精度误差 < 0.1%)
2048 × 1638 → 1.250
```

**为什么不用方形？** 等经纬度区域的地理宽高比在赤道附近约为 1.25:1（lon/lat = 30/24）。使用方形贴图会引入各向异性拉伸，造成陆地形状在纬度方向上被压缩。

---

## UV 常数

### 地理参数

```
逻辑显示区域: lon [118°, 148°E], lat [24°, 48°N]
Overdraw:     lon ±0.6°, lat ±0.48°（各边缘 2%）
裁切区域:     lon [117.4°, 148.6°E], lat [23.52°, 48.48°N]
```

### Shader 中实际使用的 UV 值

Three.js r128 `SphereGeometry` 将 UV 存储为 `(u, 1-v_geo)` 而非 `(u, v_geo)`，
其中 `v_geo = (90-lat)/180`（0=北极, 1=南极）。

因此 `vUv.y = 1 - v_geo`，向北增大。下表中所有 `v` 值均为 **vUv.y 坐标系**：

```
v_geo 到 vUv.y 的换算: vUv.y = 1 - (90 - lat) / 180 = (90 + lat) / 180

                lat=48°N  →  vUv.y = 0.7693
                lat=24°N  →  vUv.y = 0.6307
```

| 参数 | 值 | 说明 |
|---|---|---|
| `uMin` | 0.8261 | lon=117.4°E overdraw 左边界 |
| `uMax` | 0.9128 | lon=148.6°E overdraw 右边界 |
| `vMin` | 0.6307 | lat=23.52°N overdraw 南边界 (vUv.y) |
| `vMax` | 0.7693 | lat=48.48°N overdraw 北边界 (vUv.y) |
| `duMin` | 0.8278 | lon=118°E 显示左边界 (feather 参考) |
| `duMax` | 0.9111 | lon=148°E 显示右边界 (feather 参考) |
| `dvMin` | 0.6333 | lat=24°N 显示南边界 (feather 参考, vUv.y) |
| `dvMax` | 0.7667 | lat=48°N 显示北边界 (feather 参考, vUv.y) |

> **重要：V 轴反转（已修正）**
>
> 开发过程中发现一个关键 bug：若直接使用 equirectangular 约定的 `v_geo` 坐标系，
> shader 的区域判断会完全错过日本区域（判断落在南半球 −48° 到 −24°）。
> 修复：所有 `v` 边界值从 `v_geo` 转换为 `vUv.y = 1 - v_geo`。
>
> 若将此系统扩展到其他区域，必须使用 `vUv.y` 坐标而非 equirectangular `v` 坐标。

---

## Shader 注入

使用 `MeshPhongMaterial.onBeforeCompile`，替换 `#include <map_fragment>`：

```glsl
// 关键变量
float u = vUv.x;                           // 经度方向，东向增大
float v = vUv.y;                           // 纬度方向（vUv.y），北向增大

// 区域检查
if (u >= ubMin && u <= ubMax && v >= vbMin && v <= vbMax) {
  // 映射到贴图局部 UV（非方形，vUv.y 坐标下直接线性映射即正确）
  vec2 tileUV = vec2(
    (u - ubMin) / (ubMax - ubMin),
    (v - vbMin) / (vbMax - vbMin)
  );

  // 边缘羽化（smoothstep, 约 3.5% tile 范围）
  float feather = feL * feR * feT * feB;   // 四边 smoothstep 乘积

  // 距离自适应 blend（near=1.8, far=2.8 对应 sphere radius=1）
  float distFactor = smoothstep(uDetailFar, uDetailNear, uCameraDistance);

  // 混合
  diffuseColor.rgb = mix(diffuseColor.rgb, detailSample.rgb, uDetailBlend * feather * distFactor);
}
```

---

## 相机距离测试结果

Sphere radius = 1（demo 专用，见下方换算说明）。

| 距离 | 说明 | Detail visible | FPS |
|---|---|---|---|
| 3.0 | 全球视图（拉远） | ~0.00 (distFactor=0) | 43 |
| 2.5 | 过渡区 | ~0.21 | 43 |
| 1.50 | 接近 | ~0.75 × feather | 43 |
| 1.35 | 较近 | ~0.75 × feather | 43 |
| 1.25 | 最近（min dist）| ~0.75 × feather | 42 |

**near/far 参数（radius=1 单位）：**
- `uDetailNear = 1.8` ← 全强度距离阈值
- `uDetailFar  = 2.8` ← 完全淡出距离阈值

### Radius 换算：demo vs 生产

```
Demo：   sphere radius = 1,   minDistance = 1.25
生产：   sphere radius = 2,   earth3d.js 中 minDistance 约为 2.5

换算公式：生产距离 = demo 距离 × 2
         生产 uDetailNear = 3.6
         生产 uDetailFar  = 5.6

注意：earth3d.js 中 camera.position.length() 需同样 ×2 换算后传入 uniform。
```

---

## Blend 强度对比（dist=1.35, tile=2048）

| Blend | 视觉效果 | 推荐场景 |
|---|---|---|
| 0.35 | 轻微叠加，ocean 色调基本保持 d5b_v3.2.1 风格 | 推荐：生产起点 |
| 0.50 | 适中，细节渗入明显，色调略有偏移 | 可接受 |
| **0.75** | **强烈，明显看出 21K 源色调（海洋偏暗）** | **demo 默认** |
| 1.00 | 完全替换为 21K 原始贴图，ocean 色变化最大 | 诊断用途 |

> **色调差异说明**：d5b_v3.2.1 经过海洋颜色增强处理（H/S 调整），
> 21K 原始源图使用 NASA BMNG 自然色，海洋偏暗绿色。
> 生产集成时建议对细节贴图做色调匹配，或将 blend 控制在 0.35 以下。

---

## 羽化与 Overdraw

- **Overdraw**（2% 每边）：贴图裁切范围比显示区域各边多 0.6°（lon）/ 0.48°（lat）。
  这确保 feather 过渡区内有真实像素，避免边缘采样到无效区域。
- **Feather**：以显示边界（`du/dvMin/Max`）为参考，宽度约为 tile UV 范围的 3.5%，
  使用四边 `smoothstep` 乘积，形成平滑过渡框。

---

## TEXTURE_LON_OFFSET 未来集成注意

`earth3d.js` 中存在 `TEXTURE_LON_OFFSET = 90`，该值用于 `lonLatToVector3()` 中
相机/标记的球面坐标计算，**不影响** `SphereGeometry` 的贴图 UV 映射。

集成 Regional Detail Layer 时：
- Shader UV bounds 基于 equirectangular 贴图坐标，与 `TEXTURE_LON_OFFSET` 无关。
- 若日后需要通过 lon/lat 动态计算 UV 边界，须注意 `lonLatToVector3()` 的坐标系
  与 shader UV 坐标系之间有 90° 偏移，需单独处理。

---

## 性能测试

测试环境：MacBook, Chrome, Three.js r128, SphereGeometry(64,64)。

| 场景 | FPS |
|---|---|
| 无细节贴图 (global only) | 44 |
| detail=ON, 1024×820 tile | 43 |
| detail=ON, 2048×1638 tile | 42–43 |

**结论**：额外 shader 计算 + 细节贴图纹理采样开销可忽略（< 2 fps 影响）。

---

## 产出文件清单

```
previews/regional_detail_mvp_japan_eastsea/
├── README.md                               (本文件)
├── demo_regional_detail.html               (独立 Three.js demo)
├── three.min.js                            (r128, 本地副本)
├── detail_japan_eastsea_1024.png           (1024×820 细节贴图)
├── detail_japan_eastsea_2048.png           (2048×1638 细节贴图)
├── detail_japan_eastsea_uv_backtest_1024.png
├── detail_japan_eastsea_uv_backtest_2048.png
├── source_audit.md                         (21.6K 有效分辨率审计报告)
├── audit_kyushu_japan_sea.png              (5 区域源图对比)
├── audit_korea_south.png
├── audit_shanghai_yangtze.png
├── audit_taiwan_north_ryukyu.png
├── audit_hokkaido_sea_japan.png
└── screenshots/
    ├── global_wide_dist3.0.png
    ├── global_only_dist1.{50,35,25}.png    (3 张，global only)
    ├── detail_1024_dist1.{50,35,25}.png    (3 张，1024 tile)
    ├── detail_2048_dist1.{50,35,25}.png    (3 张，2048 tile)
    ├── blend_{0.35,0.5,0.75,1.0}_dist1.35.png  (4 张 blend 对比)
    ├── uv_outline_dist1.35.png             (tile 边界可视化)
    ├── feather_view_dist2.5.png            (羽化过渡视图)
    ├── crop_{kyushu,korea,shanghai,taiwan}_{global,1024,2048}.png  (12 张局部裁切)
    ├── fixed_detail_{ON,OFF}_blend1.0.png  (V 轴修正后验证对比)
    └── fixed_diff_x6.png                  (差异图 ×6 放大)
```

---

## Demo 使用说明

```bash
# 启动本地服务器（必须，不能直接 file:// 打开）
cd /Users/rodrianwei/Projects/RodiO
python3 -m http.server 8765
# 然后访问: http://localhost:8765/previews/regional_detail_mvp_japan_eastsea/demo_regional_detail.html
```

Demo 控制：
- **Tile size**：切换 1024×820 / 2048×1638 细节贴图
- **Detail ON/OFF**：对比有无细节贴图
- **Blend**：0.35 / 0.50 / 0.75 / 1.00 强度对比
- **Cam dist**：1.50 / 1.35 / 1.25 / 3.00（回到全球视图）
- **Near/Far**：距离 blend 阈值实时调节
- **Outline**：显示 tile 边界红框（调试用）
- 鼠标拖拽旋转，滚轮缩放

---

## 关键发现与工程结论

1. **Shader UV Region Blend 技术路线成立**：在不修改 `earth3d.js` 的前提下，通过 `onBeforeCompile` 注入实现了区域细节叠加，性能开销可忽略。

2. **V 轴坐标系陷阱**：Three.js r128 `SphereGeometry` 存储 UV 为 `(u, 1-v_geo)`，直接使用 equirectangular `v_geo` 坐标做 shader 边界判断会导致贴图完全错位（落在南半球）。修复：所有 V 边界换算为 `vUv.y = 1 - v_geo`。

3. **21.6K 源图有效分辨率显著优于 8K**：全区域 Laplacian 方差比 10.88×，细节贴图从原始源直接裁切有实质意义。

4. **色调匹配是生产集成的关键 gap**：21K 原始色调 vs d5b_v3.2.1 增强色调在 blend > 0.5 时有明显差异，生产集成前需对细节贴图做色调预处理或降低 blend 强度。

5. **Non-square 贴图方案正确**：1024×820 和 2048×1638 贴图在 shader 中的非方形 UV 映射数学正确（vUv.y 坐标系下线性映射即是正确的等经纬度映射）。

---

## 约束声明（已遵守）

- ✅ 未修改 `earth3d.js`
- ✅ 未修改 `DAY_TEXTURE_VARIANT`
- ✅ 未替换 `pwa/assets/earth` 下任何贴图
- ✅ 未写入 `pwa/assets`
- ✅ 未删除任何现有资产
- ✅ 未 commit（等待 RW 确认）
- ✅ 细节贴图从 21.6K 源裁切，非从 8K 放大
- ✅ 所有结果输出到 `previews/regional_detail_mvp_japan_eastsea/`
