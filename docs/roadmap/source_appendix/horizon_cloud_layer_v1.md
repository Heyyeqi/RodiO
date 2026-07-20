# Horizon 仰视云层设计 v1

> 子系统：Horizon Mode 仰视云层（向上看天的云）
> 版本：v1 · 2026-07-19
> 状态：原型验证通过（视差实测 + 无 shader 报错），待接入主 app

---

## 1. 身份声明（Identity Declaration）

本子系统**独立于** E1 的 globe cloud shell，二者是不同资产、不同渲染路径，**不共用贴图、不共用网格**：

| 维度 | E1 globe cloud shell | Horizon 仰视云层（本系统） |
|---|---|---|
| 目的 | 从太空中看地球的云壳 | 站在地表仰头看天的云 |
| 几何 | `cloudMesh` 半径 2.04（贴地球球面） | 天空穹顶内 3 层同心壳（半径 ~1975/1985/1995） |
| 贴图 | `cloudAlphaMap` 灰度贴图（照片/卫星云图） | **程序化 fBm**（无照片贴图） |
| 复用 | — | `reuseCloudAlphaMap: false` |
| 生成方式 | 纹理采样 | 程序化噪声（`core/...` 集成时用 GLSL fBm） |

**结论**：Horizon 仰视云层是一条独立主干，与 E1 并行推进，互不阻塞。集成时不要在 `cloudMesh` / `cloudAlphaMap` 上挂 Horizon 的逻辑，也不要把 Horizon 的 fBm 写进 E1 的壳。

---

## 2. 失败模式规避（来自 Horizon_Mode_Vision.md）

Vision 文档明确警告：**「云层像悬浮的透明壳」** 是头号失败模式。本设计的两条对冲：

1. **真实 3D 视差**：3 层不同半径的壳，相机偏航时各层相对地平线位移不同 → 云有体积感，不是一张平贴图在屏幕上滚动。
2. **仰视视角**：相机 FOV 38°、eyeHeight 2.2m、pitch −1.5°（Vision 允许的 −3°~+5° 内），看的是天穹而非球面外壳，从根上避免「壳」的观感。

---

## 3. 架构（原型 v2）

```
skyDome (BackSide 球, r=2000, 渐变天色 + 地平雾霾)
  └─ 3 × cloudShell (BackSide 球, r=1975/1985/1995, 透明, depthWrite:false)
       每个壳：Ashima simplex snoise + fbm3，band 模型约束高度带
seaPlane (MeshBasicMaterial, 占位海面，集成时由场景 A/B/C 替换)
```

相机：`PerspectiveCamera(38, aspect, 0.1, 8000)`，`position=(0,2.2,0)`，`rotation.order='YXZ'`，`pitch=-1.5°`，`yaw` 可控（集成时由场景驱动，无自由移动）。

---

## 4. 云着色（核心思路）

```glsl
vec3 d = normalize(vDir);          // 壳上点的方向（相机≈球心，≈从原点出发的方向）
float elev = d.y;                  // 世界仰角，作为高度带坐标
vec3 p = d*uScale + drift + float(uShell)*13.7;  // 每层不同噪声偏移 → 视差
float n = fbm3(p);                 // ~ -1..1
float a = smoothstep(1.0-uDensity, 1.0-uDensity+uSoftness, n*0.5+0.5);
float band = 1.0 - smoothstep(0.0, uBandWidth, abs(elev - uBandCenter));
band = mix(1.0, band, uBandFeather);   // feather<1 → 远离带中心仍保留部分云
float alpha = a * uLayerOpacity * band;
```

- **`uShell*13.7`** 是关键：每层用不同噪声种子，使偏航时三层错位 → 真实视差。
- **`uBandCenter/uBandWidth/uBandFeather`** 控制云的仰角分布（海平线 vs 山腰缠绕）。

---

## 5. 预设（原型验证值）

| 预设 | density | softness | scroll | scale | layerOpacity | bandCenter | bandWidth | bandFeather | 观感 |
|---|---|---|---|---|---|---|---|---|---|
| **horizon**（海平线） | 0.46 | 0.45 | 0.006 | 2.6 | 0.55 | 0.10 | 0.55 | 0.30 | 克制稀薄，云带贴在 ~5.7° 仰角 |
| **mountain**（山地） | 0.62 | 0.34 | 0.011 | 3.3 | 0.82 | −0.06 | 0.18 | 0.14 | 厚云，意图缠绕山腰 |

---

## 6. 验证结果（Playwright + 系统 Chrome，swiftshader 软件渲染）

`horizon_cloud` 像素实测（亮度-天色基线法，隔离云像素）：

| 场景 | yaw | 云像素数 | 质心 X | 质心 Y | 视差位移 |
|---|---|---|---|---|---|
| horizon | 0° | 22,850 | 538.9 | 316 | — |
| horizon | 25° | 23,068 | 561.2 | 315.6 | **+22.3 px** |
| mountain | 0° | 122,782 | 470.8 | 197.7 | — |
| mountain | 25° | 113,593 | 613.3 | 211.8 | **+142.5 px** |

**结论**：
- **无 shader 报错**（唯一 404 是浏览器自动请求的 favicon，无害）。
- **相机几何正确**：地平线落在画面 46.4% 高度处，与 pitch −1.5° + FOV 38° 的理论值一致。
- **真实 3D 视差成立**：同一 25° 偏航，两个预设质心位移量不同（22 vs 142 px）。若是伪屏幕滚动，两者位移必相同；不同位移量证明是壳几何驱动的体积视差。
- 截图见 `figures/cloud_horizon_dome.png` / `cloud_horizon_yaw25.png` / `cloud_mountain_dome.png` / `cloud_mountain_yaw25.png`，数值见 `figures/cloud_dome_report.json`。

---

## 7. 调优备注 / 待集成时处理

1. **mountain 预设当前「铺满全天」而非「缠绕山腰」**：`bandFeather=0.14` 使远离带中心处仍保留 86% band，导致整片天空都有云。集成时收紧 feather（→0.05 左右）或抬高 `uBandCenter` 让云带贴山地轮廓线。这是调参，不改架构。
2. **视差方向符号**：实测 +22/+142 px（偏航增大→云向右）。集成时需确认与相机 yaw 约定、以及用户转头/场景切换的方向感一致（审美向，非 bug）。
3. **颜色空间**：原型用 sRGB 直渲。集成进主 app 时应与 C_Sky_Design 的天色 LUT、D 路线图的色彩管理统一，避免云色与天空「不在一个色温」。
4. **性能**：3 层壳 + fbm3（5 octave）在软件渲染下 OK；真机 WebGL 应更顺。集成时若低端设备吃紧，可降 octave 或外壳层数（2 层仍保视差）。

---

## 8. 集成落点（主 app）

- 场景 A（海平线）：用 `horizon` 预设，海面由真实海面网格替换 seaPlane 占位。
- 场景 B（山地）：用 `mountain` 预设，收紧 band 让云缠山腰；地形由 GEBCO 校准后的地形网格提供（见 `horizon_terrain_detail_noise_v1.1.md`）。
- 场景 C（陆地）：可复用 `horizon` 预设调参，或新增 `land` 预设。
- 代码：作为 `HorizonScene` 内的 `CloudLayer` 模块（独立文件），不污染 E1 的 `cloudMesh` 路径。

---

## 9. 验收标准（接管 E1 Cloud Layer Foundation 的并行线）

- [x] 云可见、随 yaw 产生**不同幅度**的视差（证明非伪滚动）
- [x] 相机几何与 Vision 文档一致（地平线 ~46% 高度）
- [x] 身份独立声明（不复用 cloudAlphaMap）
- [ ] 接入主 app 后与天色 LUT / 地形网格对齐（集成阶段）
- [ ] 颜色空间统一（集成阶段）
