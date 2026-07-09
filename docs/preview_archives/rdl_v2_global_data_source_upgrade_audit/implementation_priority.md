# Implementation Priority — RodiO Global Earth Visual Pipeline

> 优先级基于：技术风险 × 视觉收益 × 实施成本。
> P0 = 不做下一步就卡住；P1 = 高价值、低风险；P2 = 中期；P3 = 远期/单独立项。

---

## P0 — 必须先做（解锁后续工作的基础）

### P0.1：GEBCO 2024 日本 Subset 下载可行性确认

**内容**：确认 GEBCO 2024 区域下载流程，在日本区域 (118–150°E, 22–50°N) 执行一次试下载。
**为什么是 P0**：不验证 GEBCO 可下载性，所有 bathymetry 增强路径都无法推进。
**体量**：约 200–400 MB（需 RW 确认后下载）
**完成标准**：成功读取 GEBCO NetCDF，提取日本区 elevation array，与 ETOPO1 对比精度。
**成本**：低（1 次脚本执行，< 1 天）

---

### P0.2：GSHHG Full Resolution 下载

**内容**：下载 GSHHG 2.3.7 全精度全球海岸线（50 MB，全球一次下载）。
**为什么是 P0**：50 MB 极小，代价可忽略，解锁所有 coastline mask 工作。
**完成标准**：成功裁切 Japan 区域多边形，生成东京湾 coastline mask。
**成本**：极低（< 半天）

---

### P0.3：全球 Pipeline 目录和命名规范建立

**内容**：建立 `pwa/assets/source/` 下的统一目录结构，建立脚本参数规范 (`--bounds lon_w lon_e lat_s lat_n`)。
**为什么是 P0**：命名不统一会导致日本代码无法复用，积累 Japan-only 技术债务。
**完成标准**：`global_pipeline_recommendation.md` 中的目录结构建立；第一个通用脚本（如 `gebco_subset.py`）使用标准参数。
**成本**：低（纯设计/脚本改造，< 1 天）

---

### P0.4：日本 Benchmark 数据补强方案执行（GEBCO + GSHHG）

**内容**：在 P0.1/P0.2 完成后，生成日本区域的：
- GEBCO 5 深度级 ocean tint tile（对比 ETOPO1 版）
- GSHHG coastline distance field
- 两者与 Layer 0 的视觉合成效果验证

**完成标准**：demo 中可见 GEBCO 海洋层次明显优于 ETOPO1；东京湾海岸线清晰度验证。
**成本**：中（下载 + 处理 + demo 更新，约 2–3 天）

---

## P1 — 高价值，下一步

### P1.1：Copernicus DEM GLO-30 日本区下载和 Hillshade 生成

**内容**：下载 Copernicus DEM 日本区（约 1000 幅，~4 GB），生成 30m hillshade，与 ETOPO1 对比。
**为什么是 P1 而非 P0**：体量大（4 GB），需要 RW 确认存储和时间。GSHHG + GEBCO 先行可已有显著视觉提升。
**完成标准**：富士山 ETOPO1（3481m）vs Copernicus DEM（预期 ~3750m）精度对比；日本阿尔卑斯 hillshade 对比。
**注意**：建议先下载少量幅（5×5° 富士山区域），验证流程后再批量。

---

### P1.2：Japan RDL v2 Visual Tile 合成（4 Layer 版本）

**内容**：将 GEBCO depth tint + GSHHG coastline + Copernicus hillshade + 21.6K 陆地细节 合成为 Japan v2 tile。
**依赖**：P0.4 + P1.1 完成后执行。
**输出**：`japan_v2_detail_2048×H.png`、`japan_v2_detail_4096×H.png`
**完成标准**：与 v1 tile 对比图，海洋层次、山形、海岸线均有明显提升。

---

### P1.3：lonLatToUV 统一工具模块

**内容**：将 `vUv.y = 1 - v_geo` 翻转逻辑封装为共享工具，建立 `uvBoundsFromBounds(lon_w, lon_e, lat_s, lat_n)` 函数。
**为什么是 P1**：防止未来每个区域重复踩 V 轴翻转的 bug；是扩展到其他区域的基础工具。
**实现位置**：`scripts/geo/lon_lat_to_uv.js`（不修改 earth3d.js）

---

### P1.4：2048 vs 4096 Benchmark 对比

**内容**：在 Three.js demo 中验证 4096 tile 的性能和视觉提升，明确 runtime 建议尺寸。
**完成标准**：4096 tile 帧率 > 40 FPS；4096 在 dist=1.25 比 2048 有明显清晰度提升。

---

## P2 — 中期

### P2.1：OSM / Geofabrik Japan Extract 处理

**内容**：下载 Geofabrik Japan PBF（约 700 MB），提取 motorway + trunk + railway + airport + port，生成低 opacity 光晕纹理 tile。
**为什么是 P2**：需要单独技术路线（矢量→光栅化），不混入 v2 terrain 主线。
**完成标准**：东京湾区域主干道微光 tile，在 dist < 1.3 时有隐约感知但不像地图。

---

### P2.2：VIIRS / Black Marble 夜间灯光集成

**内容**：下载 NASA Black Marble VNP46A3 月合成，生成全球城市光晕 mask，集成到 earth3d.js 夜间模式。
**为什么是 P2**：与 earth3d.js 夜间切换逻辑绑定，需要先理解夜间贴图切换机制再集成。
**注意**：不修改 earth3d.js 主逻辑；作为额外夜间叠加层。

---

### P2.3：地中海 / 加勒比 Benchmark（全球 pipeline 验证第二批）

**内容**：用完全相同的 pipeline 脚本处理第二批区域：地中海 (`-6_42_30_48`)、加勒比 (`-90_-60_10_30`)。
**完成标准**：脚本零修改直接复用；对比日本样板和地中海区域的 tile 视觉效果。
**此阶段意义**：证明全球可扩展，pipeline 不是 Japan-only。

---

### P2.4：Regional Detail Config 管理模块

**内容**：建立 `regionalDetailConfig.js`，管理多个区域的 UV bounds、tile 路径、blend 参数。
**为什么是 P2**：需要等到至少两个 region（日本 + 一个其他）完成后，才能抽象出合理的配置结构。
**建议格式**：
```js
{
  "118_150_22_50": {
    label: "Japan",
    uvBounds: { uMin, uMax, vMin, vMax, duMin, duMax, dvMin, dvMax },
    tiles: { "2048": "...", "4096": "..." },
    blendDefault: 0.5,
    distNear: 1.8, distFar: 2.8
  }
}
```

---

### P2.5：Tile Loading Manager

**内容**：在 Three.js demo 中支持按相机距离/区域动态切换不同 tile，不提前加载全部。
**为什么是 P2**：多 region 后内存管理变得重要，但当前单 region 不紧迫。

---

## P3 — 远期 / 单独立项

### P3.1：全球批量生产 Pipeline（自动化）

**内容**：将 P0–P1 的脚本组合为全自动 pipeline，批量生成全球所有目标区域的 tile。
**前提**：至少 3 个 region 验证完成；脚本成熟稳定。

---

### P3.2：KTX2 / BasisU 格式优化

**内容**：将 PNG tile 转为 KTX2/BasisU 格式，提升 GPU 内存效率和加载速度。
**适用场景**：桌面高质量模式，tile 数量 > 10 个时开始有意义。

---

### P3.3：高质量桌面模式 / 4K+ 显示优化

**内容**：为高分辨率屏（4K+）优化 tile 尺寸，提供 8192 tile 选项。
**前提**：需要先验证 4096 tile 的价值（P1.4）。

---

### P3.4：城市灯网 × 音乐联动

**内容**：根据当前播放的音乐风格、情绪，动态改变城市灯网的亮度/颜色/范围。
**技术路线**：Qwen 选曲情绪标签 → 影响 Layer 6 的 uniform 参数。
**为什么是 P3**：这是 RodiO 差异化功能，但依赖 Layer 6 先落地。

---

## 优先级汇总表

| ID | 内容 | 优先级 | 前提 | 预估成本 |
|---|---|---|---|---|
| P0.1 | GEBCO 日本 subset 可行性 | **P0** | 无 | 低，需 RW 确认下载 |
| P0.2 | GSHHG 全球下载（50MB）| **P0** | 无 | 极低 |
| P0.3 | 全球目录/命名规范 | **P0** | 无 | 低 |
| P0.4 | Japan GEBCO+GSHHG 视觉验证 | **P0** | P0.1+P0.2 | 中 |
| P1.1 | Copernicus DEM 日本（~4GB）| **P1** | P0 确认 | 中，需 RW 确认 |
| P1.2 | Japan v2 tile 合成（4 Layer）| **P1** | P0.4+P1.1 | 中 |
| P1.3 | lonLatToUV 工具模块 | **P1** | 无 | 低 |
| P1.4 | 2048 vs 4096 benchmark | **P1** | P1.2 | 低 |
| P2.1 | OSM Japan Layer 6 MVP | P2 | P1 完成 | 中 |
| P2.2 | VIIRS 夜间灯光 | P2 | earth3d 夜间理解 | 中 |
| P2.3 | 地中海/加勒比 pipeline 验证 | P2 | P1 完成 | 低（复用 P1 脚本）|
| P2.4 | regionalDetailConfig.js | P2 | ≥2 regions | 低 |
| P2.5 | Tile loading manager | P2 | ≥3 regions | 中 |
| P3.1 | 全球批量生产自动化 | P3 | P2 完成 | 高 |
| P3.2 | KTX2 / BasisU | P3 | 性能需求出现 | 中 |
| P3.3 | 4K+ 桌面模式 | P3 | 用户需求 | 低 |
| P3.4 | 城市灯网 × 音乐联动 | P3 | Layer 6 落地 | 中 |

---

## 立即可执行的第一步（不需要 RW 额外确认的）

1. **下载 GSHHG（50 MB，极小）**：`https://www.soest.hawaii.edu/pwessel/gshhg/` → 直接下载，无需注册
2. **建立目录结构**：`pwa/assets/source/bathy/gebco_2026/`、`pwa/assets/source/dem/copernicus_glo30/`、`pwa/assets/source/coastline/gshhg/`、`scripts/geo/`
3. **建立命名规范文档**：`scripts/geo/README.md` 定义 region key 格式和参数规范
4. **GEBCO 下载 UI 验证**：访问 gebco.net 下载工具，确认 subset 参数格式，不实际下载（等 RW 确认体量）
