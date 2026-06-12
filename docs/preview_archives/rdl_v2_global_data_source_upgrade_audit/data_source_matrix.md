# Data Source Matrix — RodiO Global High-Resolution Earth Visual Pipeline

> 本文档覆盖全球数据源，日本只是第一验证样板。所有推荐以全球可扩展为基准。
> 每条"是否推荐"基于 RodiO 的审美型地球定位，而非 GIS 准确性需求。

---

## 分类一：全球海底地形 / Bathymetry

### GEBCO 2024 Grid

| 字段 | 详情 |
|---|---|
| **全称** | General Bathymetric Chart of the Oceans 2024 Grid |
| **类型** | 全球海底地形（含陆地高程） |
| **用途** | 海底深度分层、大陆架、海沟、洋中脊、海盆可视化 |
| **全球覆盖** | ✅ 完整，包含南北极 |
| **分辨率** | **15 arc-second**（1/240°）≈ 460m/px 赤道，日本地区约 380m/px |
| **ETOPO1 对比** | ETOPO1 为 1 arc-min（1/60°）；GEBCO 精度 **4× 更高** |
| **格式** | NetCDF-4 (`.nc`)，GeoTIFF 亦可导出 |
| **下载方式** | gebco.net → 官方下载工具，支持全球整包或**区域 subset** |
| **区域 Subset** | ✅ 支持，Web 工具可直接指定经纬度范围下载 NetCDF/GeoTIFF |
| **许可** | CC BY 4.0，需 attribution：`GEBCO Compilation Group (2024) GEBCO 2024 Grid` |
| **全球文件体量** | 压缩约 8–10 GB（全球）；日本区域 subset ≈ 200–400 MB（NetCDF，15 arc-sec） |
| **区域体量** | 日本 32°×28°：约 7680×6720 cells ≈ 200 MB |
| **下载复杂度** | 低，无需注册账号，直接 Web 工具下载 |
| **是否推荐** | ✅ **强烈推荐作为全球 bathymetry 主数据源** |
| **推荐优先级** | **P0** |
| **RodiO 层级** | **Layer 3: Global Bathymetry** |
| **适合日本样板** | ✅ 是，可 subset 日本区域，比 ETOPO1 精度提升 4× |
| **适合全球管线** | ✅ 是，分区 subset + 统一处理脚本可全球复制 |
| **生成的 masks** | bathymetry depth color、shallow shelf (0~-200m)、trench/basin (<-3000m)、ocean tint layer |
| **ETOPO1 关系** | 取代 ETOPO1 作为主数据；ETOPO1 可降级为 low-res preview / fallback |

---

### ETOPO1（已有，对照）

| 字段 | 详情 |
|---|---|
| **全称** | ETOPO1 Global Relief Model (Ice Surface) |
| **类型** | 全球地形 + 海底地形 |
| **用途** | 当前已在使用，作为 bathymetry 基础 |
| **全球覆盖** | ✅ 完整 |
| **分辨率** | **1 arc-minute**（1/60°）≈ 1.85 km/px |
| **格式** | NetCDF (GMT grd) ✅ 已本地可用 |
| **下载方式** | 已下载，路径 `pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd` |
| **文件体量** | 890 MB（本地已有） |
| **是否推荐** | ⚠️ 保留为 fallback / preview，不作为最终精度上限 |
| **推荐优先级** | 保留（已有），新项目中被 GEBCO 替代 |
| **RodiO 层级** | Layer 3 fallback，或全局低精预览 |
| **适合日本样板** | ⚠️ 已用于 v2 审计，建议升级至 GEBCO |
| **GEBCO 关系** | 被 GEBCO 4× 精度超越，降格为低分预览源 |

---

## 分类二：全球海岸线 / Coastline Vector

### GSHHG (Global Self-Consistent Hierarchical High-Resolution Geography)

| 字段 | 详情 |
|---|---|
| **全称** | GSHHG 2.3.7 (Wessel & Smith, NOAA + Univ. Hawaii) |
| **类型** | 全球矢量海岸线、湖泊、岛屿多边形 |
| **用途** | 海岸线增强、海湾轮廓清晰化、岛屿边界、coastline mask |
| **全球覆盖** | ✅ 完整全球，包含岛屿、湖泊、内陆海 |
| **分辨率** | 5 级：crude / low / intermediate / high / **full** |
| **Full 精度** | 约 100–500m 特征，东京湾、大阪湾开口完整可见 |
| **格式** | 二进制 + Shapefile + WKB，可转 GeoJSON / GeoTIFF |
| **下载方式** | soest.hawaii.edu/pwessel/gshhg 直接下载，无需注册 |
| **区域 Subset** | ✅ 可按经纬度矩形裁切多边形 |
| **许可** | **LGPL** (GNU Lesser GPL)，商业使用需注意，非商业可自由使用；attribution 推荐 |
| **文件体量** | 全精度全球 ≈ **50 MB**（极小！）|
| **下载复杂度** | 极低，单文件 zip，全球一次下载 |
| **是否推荐** | ✅ **强烈推荐，解决 ETOPO1 无法区分的海湾/海岸线精度问题** |
| **推荐优先级** | **P0** |
| **RodiO 层级** | **Layer 4: Global Coastline Vector** |
| **适合日本样板** | ✅ 是，东京湾、大阪湾、濑户内海、琉球等均清晰 |
| **适合全球管线** | ✅ 是，同一文件全球适用 |
| **生成的 masks** | coastline distance field、edge enhancement mask、land/water boundary、bay polygon |
| **对比 ETOPO1** | ETOPO1 无法分辨 < 3km 海湾，GSHHG full 分辨率可达 ~100m 级别 |

---

### Natural Earth 海岸线（低精度对照）

| 字段 | 详情 |
|---|---|
| **类型** | 全球低精度地理矢量数据 |
| **分辨率** | 10m / 50m / 110m（比例尺级别） |
| **用途** | 全球概览图、极低缩放级别参考 |
| **格式** | Shapefile / GeoJSON |
| **许可** | Public Domain |
| **是否推荐** | ⚠️ 仅作为低精度对照，不作为 RodiO 主线 |
| **推荐优先级** | P3（参考用） |
| **RodiO 层级** | 不进入正式 layer |

---

## 分类三：全球陆地 DEM / Terrain

### Copernicus DEM GLO-30

| 字段 | 详情 |
|---|---|
| **全称** | Copernicus DEM Global 30m (ESA/DLR TanDEM-X) |
| **类型** | 全球陆地数字高程模型 |
| **用途** | hillshade、山形可视化、地貌起伏、斜坡、朝向 |
| **全球覆盖** | ✅ 基本完整（82°N-90°S 大部分）；极地存在数据质量下降 |
| **分辨率** | **GLO-30：30m（1 arc-second）**；GLO-90：90m |
| **ETOPO1 对比** | Copernicus DEM 精度 **3.7× 更高**（30m vs 1852m equivalent） |
| **格式** | GeoTIFF，1°×1° 分幅，命名：`Copernicus_DSM_COG_10_N35_E138_DEM.tif` 等 |
| **下载方式** | AWS Open Data (s3://copernicus-dem-30m)，无需注册，免费 |
| **区域 Subset** | ✅ 按分幅下载；日本区 32°×28° ≈ 约 1000 幅，每幅约 4MB |
| **许可** | **ESA open access，允许非商业用途，attribution 必须** |
| **全球文件体量** | 全球 GLO-30 总计约 170 GB（分幅下载）；日本区约 **4 GB** |
| **下载复杂度** | 中，需 aws s3 cli 或手动 HTTP 按幅下载 |
| **数据质量** | 比 SRTM 好：void 更少，高频细节更丰富，极北/南极地区覆盖更完整 |
| **是否推荐** | ✅ **推荐作为全球陆地 terrain 主数据源** |
| **推荐优先级** | **P1** |
| **RodiO 层级** | **Layer 2: Global Terrain DEM** |
| **适合日本样板** | ✅ 是，日本山地 30m 分辨率远超 ETOPO1 1852m |
| **适合全球管线** | ✅ 是，统一命名格式，可按区域批量下载 |
| **生成的 masks** | hillshade（多光源）、elevation color、slope mask、terrain relief |

---

### NASADEM

| 字段 | 详情 |
|---|---|
| **全称** | NASA Digital Elevation Model (Improved SRTM Processing) |
| **类型** | 全球陆地 DEM |
| **分辨率** | **30m（1 arc-second）** |
| **覆盖** | 60°S–60°N（不含极地） |
| **格式** | HGT / GeoTIFF，按 1°×1° 分幅 |
| **下载方式** | NASA Earthdata（**需注册免费账号**）|
| **许可** | NASA Open Data，attribution 需要 |
| **全球体量** | 约 170 GB（与 Copernicus 相近） |
| **优劣对比** | 比 SRTM 好（void 更少）；略逊于 Copernicus DEM（TanDEM-X 精度更高） |
| **是否推荐** | ⚠️ 次选，Copernicus DEM 更优 |
| **推荐优先级** | P2（Copernicus 不可用时的备选）|
| **RodiO 层级** | Layer 2 备选 |

---

### SRTM（1 arc-second）

| 字段 | 详情 |
|---|---|
| **全称** | Shuttle Radar Topography Mission (NASA/NGA, 2000) |
| **类型** | 全球陆地 DEM |
| **分辨率** | 30m（SRTM1，原始仅美国，后全球开放）；90m（SRTM3，更早开放） |
| **覆盖** | 60°S–60°N |
| **格式** | HGT，1°×1° 分幅 |
| **下载方式** | USGS EarthExplorer 或 OpenTopography（较便捷）|
| **质量问题** | 已知 void（无效区域）；不如 NASADEM/Copernicus |
| **是否推荐** | ❌ 不推荐，已被 NASADEM / Copernicus DEM 取代 |
| **推荐优先级** | P3（仅作为历史对照或快速测试）|

---

### ALOS World 3D-30m (AW3D30)

| 字段 | 详情 |
|---|---|
| **全称** | ALOS World 3D-30m (JAXA) |
| **类型** | 全球陆地 DEM（光学立体摄影测量） |
| **分辨率** | **30m（1 arc-second）** |
| **覆盖** | 82°N–82°S |
| **格式** | GeoTIFF，5°×5° 分幅 |
| **下载方式** | JAXA EORC 网站，**需免费注册** |
| **许可** | 研究/非商业免费；commercial use 需授权 |
| **优势** | 在亚洲地区（日本、中国、东南亚）质量特别好；JAXA 用 ALOS 光学传感器 |
| **日本特别说明** | JAXA 对日本本土有更高精度版本（5m DEM，GSI），但非全球适用 |
| **是否推荐** | ✅ 日本样板优先候选；全球可用但注册略繁 |
| **推荐优先级** | P1（与 Copernicus 并列，Japan 区域可优先） |
| **RodiO 层级** | Layer 2：可与 Copernicus 混合，日本区域替换或补强 |

---

## 分类四：全球城市 / 路网 / 人类活动层

### OpenStreetMap / Geofabrik Regional Extracts

| 字段 | 详情 |
|---|---|
| **全称** | OpenStreetMap (ODbL) + Geofabrik regional extracts |
| **类型** | 全球矢量地理数据：道路、建筑、铁路、机场、港口等 |
| **用途** | 路网微光、主干道线条、城市区域轮廓、机场/港口节点 |
| **全球覆盖** | ✅ 全球，数据质量因地区差异大（发达国家质量高）|
| **分辨率** | 矢量，理论无上限（实际精度 ~1–10m 城市区域）|
| **格式** | PBF（Protocol Buffer）、Shapefile；Geofabrik 提供分区下载 |
| **下载方式** | download.geofabrik.de，按大洲/国家直接下载，无需注册 |
| **区域 Subset** | ✅ Japan PBF：约 700 MB；全球约 72 GB |
| **许可** | **ODbL 2.0**，attribution 必须，衍生数据需开放共享 |
| **下载复杂度** | 低（直接 HTTP 下载）；处理复杂（需 osmium / osmfilter 提取要素）|
| **提取要素** | motorway, trunk, primary, railway, aerodrome, harbour, industrial |
| **是否推荐** | ✅ 推荐，但**必须单独进入 Layer 6（Vector / Light Overlay）** |
| **推荐优先级** | **P2**（不应混入 bathymetry/terrain 主线）|
| **RodiO 层级** | **Layer 6: Vector / Light Overlay Layer**（独立立项）|
| **适合日本样板** | ✅ 东京湾、大阪湾城市灯网样板 |
| **全球化** | ✅ Geofabrik 分区 extracts 可全球按需下载 |
| **重要边界** | 必须做成"信号层"（低 opacity 光晕），不能做成导航地图 |

---

### NASA VIIRS / Black Marble（夜间灯光）

| 字段 | 详情 |
|---|---|
| **全称** | NASA Black Marble VNP46 (VIIRS Day/Night Band) |
| **类型** | 全球夜间灯光 raster 数据（卫星观测） |
| **用途** | 城市光晕、人类活动感、夜间地球视觉 |
| **全球覆盖** | ✅ 完整全球 |
| **分辨率** | **500m（VNP46A3 月合成）**；部分产品 15 arc-sec |
| **格式** | HDF5 (.h5)，按瓦片分发 |
| **下载方式** | NASA LAADS DAAC（**需免费注册**）或 NASA Earthdata |
| **许可** | NASA Open Data，citation 需要 |
| **文件体量** | 月合成全球约 1–2 GB（多文件） |
| **下载复杂度** | 中（需注册、可批量 wget）|
| **是否推荐** | ✅ 推荐用于夜间模式，**但独立进入 Layer 6** |
| **推荐优先级** | **P2** |
| **RodiO 层级** | Layer 6，夜间灯光子层 |
| **注意** | 不用于白天地球；与 earth3d.js 夜间贴图可叠加或替代 |

---

## 数据源精度汇总对比

| 数据源 | 分辨率 | 日本区等效 px | 最小可分辨特征 | 主要用途 |
|---|---|---|---|---|
| GEBCO 2024 | 15 arc-sec | 7680×6720 | ~1 km | 海底地形 |
| ETOPO1 | 1 arc-min | 1920×1680 | ~3–4 km | 海底地形（低精） |
| GSHHG full | ~100–500m vector | N/A (矢量) | ~100m | 海岸线 |
| Copernicus DEM GLO-30 | 30m | ~100K×90K | ~60m | 陆地地形 |
| ALOS AW3D30 | 30m | ~100K×90K | ~60m | 陆地地形 |
| NASADEM | 30m | ~100K×90K | ~60m | 陆地地形（备选）|
| OSM (roads) | 矢量 ~1m | N/A | ~1m | 路网/城市 |
| VIIRS Black Marble | 500m | 3840×3360 | ~1 km | 夜间灯光 |
| 21.6K source | 1 arc-min | 1800×1440 | ~3–4 km | 卫星视觉 |
| d5b_v3.2.1 8K | 2.6 arc-min | 682×546 | ~8–10 km | 全局底色 |

---

## 层级-数据源映射总表

| Layer | 名称 | 主数据源 | 备选/Fallback |
|---|---|---|---|
| Layer 0 | Global Base Texture | d5b_v3.2.1 8K | 未来高质量全球日图 |
| Layer 1 | Visual Source Detail | 21.6K source（色调匹配后）| 无 |
| Layer 2 | Global Terrain DEM | **Copernicus DEM GLO-30** | ALOS AW3D30（日本优先） |
| Layer 3 | Global Bathymetry | **GEBCO 2024** | ETOPO1（fallback/preview） |
| Layer 4 | Global Coastline Vector | **GSHHG full** | Natural Earth（低精对照） |
| Layer 5 | Regional Detail Tile | 从 Layer 1-4 合成 2048/4096 | — |
| Layer 6 | Vector / Light Overlay | OSM/Geofabrik + VIIRS | — |
