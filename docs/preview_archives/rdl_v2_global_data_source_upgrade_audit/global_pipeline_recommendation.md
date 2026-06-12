# Global Pipeline Recommendation — RodiO 全球高精度审美地球

> 设计原则：RodiO 是审美型地球，不是 GIS。所有层的叠加强度应服从"感受到山、感受到海、感受到夜，但不觉得在看地形图"的标准。

---

## 一、推荐全局数据架构

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 6: Vector / Light Overlay (城市灯网、路网微光) [独立立项]   │
├─────────────────────────────────────────────────────────────────┤
│  Layer 5: Regional Detail Tile (区域 2048/4096 精细合成)          │
├─────────────────────────────────────────────────────────────────┤
│  Layer 4: Global Coastline Edge (GSHHG coastline mask)           │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: Global Bathymetry Tint (GEBCO 2024 深度分层)            │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Global Terrain Relief (Copernicus DEM hillshade)       │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Visual Source Detail (21.6K source 色调匹配)            │
├─────────────────────────────────────────────────────────────────┤
│  Layer 0: Global Base Texture (d5b_v3.2.1 8K — 全局底色)         │
└─────────────────────────────────────────────────────────────────┘
```

每一层叠加在前一层之上，blend 强度由设计决定（不由技术上限决定）。

---

## 二、各层详细推荐

### Layer 0：Global Base Texture

**结论：维持 d5b_v3.2.1，不替换。**

- d5b_v3.2.1 的海洋色彩增强是积累的设计投入，维持原样
- 作为全球统一底色和 fallback
- 后续如有全球视觉更新，应走 `d6` / `d7` 版本号迭代，不是覆盖旧版本
- 运行时 8K 足够，不建议更高（网络/内存）

### Layer 1：Visual Source Detail（局部叠加）

**结论：继续使用 21.6K source，但必须加入色调匹配步骤。**

- 21.6K source 有 7–14× 的纹理清晰度优势（Laplacian 验证）
- 根本限制：与 d5b 来自同一 NASA BMNG 系谱，色调本质相似
- **色调匹配**（color grading）是 v2 的关键工程：
  - 陆地区域：按 d5b 的绿度/明度匹配，blend 0.4–0.6
  - 海洋区域：blend = 0（由 Layer 3 接管海洋的精度增益）
- 不替换 21.6K source，而是修正 blend 策略

### Layer 2：Global Terrain DEM

**结论：Copernicus DEM GLO-30 作为主数据源，ALOS AW3D30 日本区优先。**

**为什么选 Copernicus DEM**：
- TanDEM-X 雷达精度，数据采集于 2011–2015 年，系统性更好
- 无需注册账号，AWS S3 直接下载
- 命名规范统一（`N35_E138`），批量下载脚本易写
- void 比 SRTM 少得多
- 全球覆盖完整

**为什么考虑 ALOS 日本区**：
- JAXA 本土数据，日本山地表现特别好
- 但全球一致性不如 Copernicus，且需注册
- 结论：日本样板可以用 ALOS 对比验证，全球 pipeline 以 Copernicus 为准

**产出**：hillshade（多光源合成），混合 strength 15–30%，避免地形图感。
不输出等高线。不输出科学配色地形图。

**分区处理策略**：
- 日本区：32°×28° → 约 1000 幅 ×4MB = ~4GB，可接受
- 地中海：~50°×30° → ~6GB
- 建议按 Region 建目录，每 Region 独立处理，不一次性下载全球

### Layer 3：Global Bathymetry Tint

**结论：GEBCO 2024 取代 ETOPO1 作为主数据源。**

**GEBCO 2024 的决定性优势**：
- 15 arc-sec (≈460m) vs ETOPO1 1 arc-min (≈1852m)：精度 **4× 更高**
- 整合了最新声呐测深数据（Seabed 2030 项目持续更新）
- 对 Okinawa Trough（冲绳海槽）、Japan Trench（日本海沟）、East China Sea shelf（东海陆架）等特征分辨率更清晰
- Subset 下载工具友好，无需注册

**深度分层方案（5级，审美而非科学）**：
```
0   ~  -50m  → 极浅陆架：接近 Layer 0 ocean 色调，轻微增亮
-50 ~ -200m  → 浅陆架：轻微蓝化
-200 ~ -1500m→ 上陆坡：适度加深
-1500 ~ -4000m → 深海：显著加深，参考 d5b 深海色调
< -4000m     → 深渊/海沟：接近黑蓝，不低于 d5b 最深色
```
blend 强度：海洋区域 25–40%，确保 d5b 底色可见。

**ETOPO1 去留**：
- 保留本地文件，作为全球 low-res preview 和 fallback
- 不再作为精度上限的参考
- 未来可用于：全球 LOD（远景低分辨率），全球无 GEBCO 覆盖区域补充

**分区处理策略**：
- 日本：gebco.net subset 下载 lon 118–150°, lat 22–50° → 约 200–400 MB
- 地中海：lon -6–42°, lat 30–48° → 约 500 MB
- 建议每 Region 独立缓存，不维护一份全球大文件

### Layer 4：Global Coastline Edge

**结论：GSHHG full resolution 是唯一有效选择。**

**为什么 GSHHG 解决了 ETOPO1 无法解决的问题**：
- ETOPO1 1 arc-min 无法分辨 < 3km 的海湾开口
- GSHHG full：精度约 100–500m，东京湾（9km）、伊势湾（30km）均可清晰表现
- 全球文件仅 **50 MB**（代价极低）

**叠加方式（非地图边界线）**：
- 从 GSHHG 生成 coastline mask（距海岸 0–5km 区域）
- 在 coastal zone 增加轻微的 edge clarity（边缘亮化/暗化）
- Strength：10–20%，仅在近距离（dist < 2.0）激活
- 不画边界线，不画轮廓，只做"隐形的清晰感增强"

**分区处理**：GSHHG 是全球单文件，裁切特定区域多边形即可，无需分区下载。

### Layer 5：Regional Detail Tile

**结论：基于以上 Layers 0–4 合成的区域高精度贴图，按需按区域生成。**

- 日本是第一个 benchmark region
- 每个区域输出 2048×H 和 4096×H（非方形，保持地理比例）
- 合成步骤（以日本为例）：
  1. 21.6K source 色调匹配（陆地细节）
  2. GEBCO 2024 海洋深度分层 tint
  3. Copernicus DEM hillshade（陆地叠加）
  4. GSHHG coastline edge 增强
  5. 混合输出为 PNG tile
- 下一批区域：地中海、加勒比、大堡礁、南太平洋、喜马拉雅（见 japan_benchmark_plan.md）

### Layer 6：Vector / Light Overlay（独立立项）

**结论：必须单独立项，不混入 v2 terrain/bathymetry 主线。**

**原因**：
- 矢量渲染需要不同的技术路线（Line / Sprite，不是纹理叠加）
- 夜间灯光叠加条件与地球白天/夜间切换绑定
- 开发复杂度远高于 Layer 0–5，不宜一起推进

**建议 Layer 6 内容**：
```
6a. Road micro-glow：OSM motorway/trunk/primary → 极细 white/gold 线条纹理
6b. City halo：VIIRS 夜间灯光 → 城市区域 warm glow mask
6c. Airport/port nodes：OSM 点位 → Three.js Sprite
6d. Railway lines：OSM 铁路 → 轻微虚线轨迹
```

**技术架构（未来参考）**：
- 矢量 → 光栅化（Mapnik 或 Canvas2D）→ PNG 贴图 tile
- 或 Three.js Line / ShaderMaterial 矢量直接渲染
- 夜间模式下激活，白天模式下关闭或 opacity = 0

---

## 三、ETOPO1 是否保留？

**保留，降级为以下用途**：
1. 全局低精度预览（加载 GEBCO 前的 fallback）
2. 极地区域补充（GEBCO 偶有质量问题的区域）
3. 历史对照（v1 审计已用，数据完整，不应删除）
4. 超低分辨率全球 bathymetry LOD（远景球体无需 GEBCO 精度）

---

## 四、如何避免 RodiO 变成 GIS

核心原则：**感受到，而不是读到**。

| 错误做法（GIS 感） | 正确做法（审美感） |
|---|---|
| 等深线 | 颜色渐变层次 |
| 海拔标注 | hillshade 光影 |
| 海岸线描边 | edge clarity 轻微增强 |
| 道路导航线 | 微光线条，opacity < 20% |
| 科学配色（蓝-绿-红-白）| 审美配色（与 d5b 色系一致）|
| 精确比例尺 | 不显示比例尺 |
| 完整路网 | 仅 motorway + trunk 级别 |

---

## 五、全球可扩展设计原则

### 5.1 目录结构（建议）

```
pwa/assets/source/
├── earth_day_source_21600x10800.jpg       (已有)
├── bathy/
│   ├── ETOPO1_Ice_g_gdal.grd              (已有，fallback)
│   └── gebco_2026/                        (待下载，按 region subset)
│       ├── japan_lon118_150_lat22_50.nc
│       ├── mediterranean_lon-6_42_lat30_48.nc
│       └── ...
├── dem/
│   ├── copernicus_glо30/                  (待下载，按 region tiles)
│   │   └── japan/
│   │       ├── N35_E138_DEM.tif
│   │       └── ...
│   └── alos_aw3d30/
│       └── japan/ (可选，对比验证)
└── coastline/
    └── gshhg/
        └── gshhg-shp-2.3.7/               (全球单次下载 50MB)

previews/
└── rdl_v2_regions/                        (统一 region 输出目录)
    ├── japan_118-150_22-50/               (lon/lat 为 key，不是 region name)
    │   ├── detail_tile_2048.png
    │   ├── detail_tile_4096.png
    │   └── metadata.json
    ├── mediterranean_-6-42_30-48/
    └── caribbean_-90--60_10-30/
```

### 5.2 命名规范

- Region key：`{lon_w}_{lon_e}_{lat_s}_{lat_n}`（数字，不用地名）
- 例：日本 → `118_150_22_50`，地中海 → `-6_42_30_48`
- 好处：避免 Japan-specific 代码，pipeline 可直接复用
- Tile 命名：`detail_tile_2048_118_150_22_50.png`

### 5.3 统一工具模块（建议命名）

```
scripts/geo/
├── region_config.js      // { bounds, uvBounds, zoomLevels }
├── lon_lat_to_uv.js      // 统一处理 vUv.y = 1 - v_geo 翻转
├── tile_generator.py     // 通用 tile 生成，接受 bounds 参数
├── gebco_subset.py       // 从 GEBCO NetCDF 提取任意 region
├── dem_hillshade.py      // 从 Copernicus DEM 生成 hillshade
└── gshhg_mask.py         // 从 GSHHG 生成 coastline mask
```

每个脚本以 `--lon_w --lon_e --lat_s --lat_n --output_dir` 为标准参数，不硬编码地名。

### 5.4 分区处理，避免全球超大数据

**关键原则**：永远不在本地维护一份"全球 DEM"或"全球 GEBCO"。

- 每次只为当前 benchmark region 下载和处理
- 数据处理完成后，输出 tile 留存，原始数据可选择性保留
- 扩展新区域时，走同一套 pipeline，不需要修改代码

---

## 六、数据源决策表

| 问题 | 结论 |
|---|---|
| GEBCO 是否应作为 bathymetry 主线？ | ✅ 是，4× 精度提升，subset 便捷，推荐 P0 |
| ETOPO1 是否保留？ | ✅ 保留为 fallback / 低精预览，不作为精度上限 |
| GSHHG 是否应作为 coastline 主线？ | ✅ 是，50MB 全球文件，100m 级精度，推荐 P0 |
| 哪个 DEM 作为 terrain 主线？ | Copernicus DEM GLO-30（全球首选），ALOS AW3D30（日本补强）|
| OSM 是否进入 RDL v2 主线？ | ❌ 否，单独进入 Layer 6，另立项 |
| 夜间灯光数据是否有必要？ | ✅ 有价值，但 Layer 6 独立，非 v2 主线 |
| 如何避免 GIS 感？ | 颜色渐变 > 等值线；hillshade > 等高线；edge clarity > 描边 |
| 如何全球可扩展？ | 统一命名（lon/lat 而非地名）；分区下载；通用脚本 |
