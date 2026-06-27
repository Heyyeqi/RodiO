# Phase B-6 Current Development Recap and Next Plan

Stage: B-6.2X-D2 / GEE 8K source export in progress  
Type: Development recap and next execution plan  
Status: Planning / coordination only

---

## 1. Current Position

当前项目不处于上色阶段，也不处于 d6 接入阶段。当前位于 **B-6.2X-D2：GEE 8K source export / download in progress**。

主线路线：

```
GEE global source cache
→ local import / alignment
→ semantic mask derivation
→ validation
→ API / priority design
→ d6 / visual color application
```

B-6.2X 是一次统一补齐全球 source cache 的阶段升级，而非 B-6.2G 系列的单点扩展。所有后续 mask 派生、验证、API 设计均依赖本阶段 source cache 就绪。

---

## 2. Completed Work Before B-6.2X

### 2.1 B-6.1 / B-6.2 Base Structure Layer

已完成基础陆海结构 mask：

- `land_mask`
- `ocean_mask`
- `deep_ocean_mask`
- `mid_ocean_mask`
- `continental_shelf_mask`
- `shallow_sea_mask`
- `coastline_distance_mask`
- `mountain_mask`
- `plateau_mask`

### 2.2 B-6.2P Polar Patch

已完成极地冰盖 mask：

- `antarctica_ice_mask`
- `greenland_ice_mask`
- `polar_land_ice_mask`

### 2.3 B-6.2S Special Sea Masks

已完成特殊海区语义 mask：

- `red_sea_water_mask`
- `yellow_sea_water_mask`
- `east_china_sea_water_mask`
- `japan_sea_water_mask`
- `mediterranean_water_mask`
- `aegean_sea_water_mask`
- `caribbean_water_mask`
- `persian_gulf_water_mask`
- `north_sea_water_mask`
- `baltic_sea_water_mask`
- `south_china_sea_water_mask`

> **Caveat：** Mediterranean 与 Aegean 存在父子嵌套关系。后续 API priority 设计必须处理 `aegean_sea_water_mask` 优先于 `mediterranean_water_mask` 的问题。

### 2.4 B-6.2G-1 Inland Water / Lake

已完成内陆水体 mask：

- `lake_mask_from_GSHHG_L2`
- `lake_island_mask`
- `inland_water_mask`
- `large_lake_mask`

> **Caveat：**
> - 2K 分辨率下小型湖泊可能被 hard mask 压掉，精度存在下限；
> - Lake Chad、Aral Sea 等历史性缩减水域需要 watchlist，当前 GSHHG 源可能与现实有偏差；
> - GSHHG L2/L3 层级对 lake topology（湖中岛、岛中湖）仍有参考价值，不宜完全废弃。

### 2.5 B-6.2G-2 Terrain / Relief

已完成地形 mask（ETOPO1-derived proxy）：

- `high_mountain_mask`
- `plateau_refined_mask`
- `lowland_or_basin_proxy`
- `hill_or_relief_proxy`

> **Caveat：**
> - 已修复早期 ocean leakage 问题；
> - 当前 terrain masks 为 ETOPO1 proxy，精度受限于 ETOPO1 约 1 arcmin 分辨率；
> - 后续可用 Copernicus DEM GLO-30 升级至高精度版本。

### 2.6 B-6.2G-3 River / Delta / Wetland

已完成河流缓冲区 proxy mask：

- `major_river_proxy`
- `river_buffer_proxy`
- `major_river_proxy_l01_l02`
- `river_buffer_proxy_l01_l02`

> **Caveat：**
> - WDBII 提供的是 polyline 数据，不是 river water polygon；当前 river mask 是 buffer proxy，而非真实水面宽度；
> - 真实 delta / wetland / floodplain 仍 deferred，需要 JRC GSW 或专项数据；
> - JRC GSW 可作为 water cross-check（尤其是 occurrence / seasonality 层），但不能替代 WDBII topology。

### 2.7 B-6.2G-4 Desert / Arid / Bare Land

**结论：本阶段未能建立可靠的 global desert / arid / bare land mask。**

评估过的 source：ESA WorldCover、Global Aridity Index、MODIS LC、CGLS-LC100 等。

> - 当前仓库内没有可直接用于 global desert 派生的可靠 source；
> - 不能用 day texture RGB 反推 structure truth（外观特征不等于语义分类）；
> - B-6.2G-4 的核心价值是暴露了 source 体系不完整的根本问题；
> - 这是触发 B-6.2X 升级的直接原因。

---

## 3. Why B-6.2X Replaces Single-Point B-6.2G Expansion

| 阶段 | 角色 |
|------|------|
| B-6.2G 前期工作 | 问题发现 + 局部原型 |
| B-6.2X | 统一补齐全球 source cache |
| B-6.2X 后续 | 用统一 source 重建 / 强化 structure semantic layer |

B-6.2X 不是回退，也不是推翻前期工作。前期建立的 mask 仍然有效，B-6.2X 的目标是在数据源层面完成以下升级：

- 引入具有全球覆盖、已验证语义分类的 source（ESA WorldCover 2021 v200）
- 引入高精度 elevation / slope source（Copernicus DEM GLO-30）
- 引入水体动态 source（JRC GSW occurrence / seasonality / max_extent / transition）
- 在统一 source 基础上派生 semantic mask，取代当前 proxy 体系

---

## 4. Current GEE Export Status

当前用户正在手动通过 Google Earth Engine 导出 Phase 1 8K source，下载后放入：

```
d5b_processor_v3/source_cache/gee_global/exported_8k/
```

> `source_cache/` 内实际数据不进入 git，已在 `.gitignore` 中排除。

**Phase 1 目标文件列表：**

```
d5b_processor_v3/source_cache/gee_global/exported_8k/
  esa_worldcover_2021_v200_map_8192x4096.tif
  etopo1_bedrock_8192x4096.tif
  etopo1_ice_surface_8192x4096.tif
  jrc_gsw_occurrence_8192x4096.tif
  jrc_gsw_seasonality_8192x4096.tif
  jrc_gsw_recurrence_8192x4096.tif
  jrc_gsw_max_extent_8192x4096.tif
  jrc_gsw_transition_8192x4096.tif       ← optional supplement
  copernicus_dem_glo30_elevation_8192x4096.tif
  copernicus_dem_glo30_slope_8192x4096.tif    ← optional supplement
```

`jrc_gsw_transition` 与 `copernicus_dem_glo30_slope` 如未导出，视为 optional supplement，不阻塞 D3。

---

## 5. Immediate Next Gate: B-6.2X-D3 8K Import Test

**D3 目标：验证所有 Phase 1 8K source 可用性。**

**D3 允许：**

- 读取 gitignored `source_cache` 中手动导出的 8K raster；
- 检查文件是否存在；
- 检查图像尺寸（dimensions）；
- 检查数据类型（dtype）；
- 检查 nodata 值；
- 检查数值范围（value range）；
- 检查影像方向（orientation，north-up 验证）；
- 检查类别直方图（class histogram，尤其 ESA WorldCover）；
- 输出诊断报告（diagnostic report）。

**D3 禁止：**

- 生成正式 structure masks；
- 运行 structure mask generator；
- 运行 d6；
- 写 pwa / production / candidates；
- 修改 `d6_noon_air_earth_generator.py`；
- 提交 source_cache 数据。

**D3 exit criteria（全部满足方可退出）：**

- 每个 Phase 1 8K source 文件有明确 import verdict（pass / fail / missing）；
- missing / invalid / split 文件已列出；
- ESA WorldCover class histogram 已验证（10 个 class 值分布合理）；
- JRC GSW 各层 value range 已验证（occurrence 0–100，seasonality 0–12，等）；
- Copernicus DEM nodata policy 已验证；
- ETOPO1 bedrock / ice_surface value range 已验证（含负值海底深度）；
- 未发生任何 production-side 变更。

---

## 6. Later Gates

### 6.1 B-6.2X-D4 — 21.6K Master Registration

D3 通过后，导出第一批 21.6K source 用于 master-resolution 工作：

```
esa_worldcover_2021_v200_map_21600x10800.tif
copernicus_dem_glo30_elevation_21600x10800.tif
copernicus_dem_glo30_slope_21600x10800.tif
```

> ETOPO1 / JRC 21.6K 可延后，原因：ETOPO1 原始分辨率约 1 arcmin（与 21.6K 接近），JRC GSW 原始分辨率 ~30m，21.6K resampled 版不增加真实细节，优先级低于 ESA / DEM。

### 6.2 B-6.2X-M1 — Semantic Mask Derivation Prototype

从 source 派生 prototype semantic masks，包括（不限于）：

**Land cover（from ESA WorldCover）：**
- `forest_mask`（class 10）
- `shrubland_mask`（class 20）
- `grassland_mask`（class 30）
- `cropland_mask`（class 40）
- `builtup_mask`（class 50）
- `bare_sparse_land_mask`（class 60）
- `wetland_mask`（class 90）
- `mangrove_mask`（class 95）
- `snow_ice_mask`（class 70，ESA-derived）

**Water body（from JRC GSW）：**
- `permanent_water_mask`（occurrence ≥ 90）
- `seasonal_water_mask`（occurrence 10–90）

**Terrain（from Copernicus DEM / ETOPO1）：**
- `high_mountain_mask`
- `plateau_mask`
- `slope_relief_mask`
- `lowland_plain_mask`

**Bathymetry（from ETOPO1）：**
- `shallow_sea_mask`
- `continental_shelf_mask`
- `deep_ocean_mask`

> **关键 caveat：** ESA class 60（Bare/Sparse Vegetation）只能先映射为 `bare_sparse_land_mask`，**不能直接等于 `desert_mask`**。Desert 语义需要结合 aridity / climate 信息，不能仅凭地表覆盖类别推断。

### 6.3 B-6.2X-M2 — Validation Audit

对全球关键区域执行 mask 正确性验证，重点区域包括：

| 区域 | 验证重点 |
|------|---------|
| Japan / East China Sea / Yellow Sea / Japan Sea | 特殊海区 mask 边界 |
| Mediterranean / Aegean | 父子嵌套关系，优先级 |
| Red Sea / Persian Gulf | 封闭海 mask 准确性 |
| Tibetan Plateau / Himalaya | plateau / mountain 边界 |
| Sahara / Arabian Peninsula / Australia interior | bare_sparse_land 范围 |
| Great Lakes / Baikal / Caspian / Dongting / Qiandao | 湖泊覆盖率 |
| Antarctica / Greenland | 冰盖 mask 一致性 |
| Caribbean / Bahamas Bank | 浅水区、bank 区分 |
| Maldives / Tuamotu / Pacific atolls | 礁石 / 环礁 |

> **重要限制：** reef / atoll / Bahamas Bank / Maldives / Tuamotu 等区域不能完全依赖 GEE source 解决。这些地物的正确表达需要专项 reef / coral 数据（UNEP-WCMC、Allen Coral Atlas 等），在 Phase 3 source 补充前，此类区域 mask 为 incomplete。

### 6.4 B-6.2X-API — Structure Semantic API Draft

API draft 需处理以下维度：

- **mask groups**：按类型分组（land cover / water / terrain / special sea / polar）
- **priority**：同位置多 mask 重叠时的优先级
- **parent-child relationships**：如 Mediterranean > Aegean，lake > lake_island
- **proxy flags**：标记哪些 mask 是 proxy（非直接 source 派生）
- **missing masks**：标记尚未生成或 deferred 的 mask
- **versioning**：source 版本与 mask 版本绑定
- **attribution**：每个 mask 的数据来源
- **commercial clearance**：各 source 商业使用许可状态

典型 priority 示例（高优先级在上）：

```
polar_land_ice > snow_ice
lake_island > inland_water
special_sea > generic shallow_sea
mangrove > wetland > grassland
glacier > mountain > bare_sparse_land
permanent_water > seasonal_water
```

### 6.5 d6 Refactor / Visual Application

只有以下条件全部满足后，才允许考虑 d6 refactor 和 Noon Air 上色：

1. validation audit 通过（或条件通过，附已知 caveat 列表）
2. API / priority draft 就绪
3. 所有 blocking source issue 解决
4. 无未解决的 orientation / nodata / class-value 异常

---

## 7. Source Download Policy

| Phase | Source | 状态 |
|-------|--------|------|
| Phase 1（8K）| ESA WorldCover / ETOPO1 / JRC GSW / Copernicus DEM | 当前目标 |
| Phase 1（21.6K）| ESA WorldCover / Copernicus DEM / slope | D3 通过后 |
| Phase 2 | Dynamic World / GLIMS | 延后 |
| Phase 3（补充）| GEBCO / reef / coral / Global Aridity / Köppen / MODIS / CGLS-LC100 | 延后或外部 |

**约束：**

- 不下载 full global raw 10m tiles（存储不可行）；
- 不以 2K 作为主路线（精度不足以支撑后续 semantic layer）；
- `source_cache/` 不进入 git（`.gitignore` 已配置）。

---

## 8. Boundary Rules

本阶段（B-6.2X-D2 至 D3 完成前）明确禁止：

- 不运行 d6
- 不执行上色操作
- 不替换 production 文件
- 不写 pwa / production / candidates
- 不生成 Noon Air 候选
- 不提交 exported rasters 到 git
- 不提交 source_cache 目录内容
- 不 commit / push 任何数据文件
- 不处理 `d5b_processor_v3/d6_noon_air_earth_generator.py`
- root previews 暂不处理

---

## 9. Completion Criteria Before Coloring

进入白天上色（d6 / Noon Air）前，至少需要满足以下全部条件：

1. Phase 1 8K import test passed（D3 exit criteria 全部通过）
2. source alignment verified（所有 source 坐标系、方向、extent 一致）
3. semantic mask prototype generated（M1 完成）
4. validation audit passed or conditional（M2 完成，附已知限制说明）
5. API / priority draft ready（B-6.2X-API 完成）
6. 无未解决的 source orientation / nodata / class-value 异常

以上任一条件未满足，均不进入 d6 / Noon Air 阶段。

---

## 10. Current Recommendation

**结论：**

- 当前不继续单点 B-6.2G-4D-2-R8K expansion；
- 当前主线为 B-6.2X；
- 等待用户完成 GEE 8K export / download（B-6.2X-D2）；
- 下一步执行 B-6.2X-D3 8K Import Test；
- 在 validation / API 全部就绪前，不进入 d6 / Noon Air / production。

---

*Document created: 2026-06-23*  
*Stage: B-6.2X-D2*  
*Status: Planning / coordination only — no code, no masks, no coloring*
