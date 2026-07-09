# Phase B-6.2X-M1-A — Semantic Mask Derivation Design

Stage: B-6.2X-M1-A  
Type: Design document — no masks generated  
Status: Design / pre-prototype  
Date: 2026-06-24

---

## 1. Current Source Readiness

Phase 1 8K source cache 已全部通过 D3 / D3-R import test，可进入 M1 设计阶段。

| Source | 大小 | D3 状态 | 备注 |
|--------|------|---------|------|
| `esa_worldcover_2021_v200_map_8192x4096.tif` | 1.29 MB | ✅ PASS | class 0 = nodata（无 tag，需显式处理）|
| `etopo1_bedrock_8192x4096.tif` | 56.45 MB | ✅ PASS | min -10761 m / max 7980 m |
| `etopo1_ice_surface_8192x4096.tif` | 55.30 MB | ✅ PASS | mean 高于 bedrock，冰盖抬升正常 |
| `jrc_gsw_occurrence_8192x4096.tif` | 4.82 MB | ✅ PASS | 0–100，全 101 值 |
| `jrc_gsw_seasonality_8192x4096.tif` | 2.61 MB | ✅ PASS | 0–12 months |
| `jrc_gsw_recurrence_8192x4096.tif` | 4.48 MB | ✅ PASS | 0–100（缺 value=2，正常）|
| `jrc_gsw_max_extent_8192x4096.tif` | 0.48 MB | ✅ PASS | binary 0/1 |
| `jrc_gsw_transition_8192x4096.tif` | 2.12 MB | ✅ PASS | 0–10，11 classes |
| `copernicus_dem_glo30_slope_8192x4096.tif` | 5.60 MB | ✅ PASS | max 6.03°（8K 平滑，C2 记录）|
| `copernicus_dem_glo30_elevation_8192x4096.tif` | 21.02 MB | ✅ D3-R PASS | tile stitch，min -427m / max 7953m |

**10 / 10 source complete. 全部 8192×4096，CRS WGS84，north-up，grid 对齐。**

---

## 2. Source-to-Mask Mapping

| Source | Layer / Values | Candidate Mask | Confidence | Caveats |
|--------|---------------|----------------|------------|---------|
| ESA WorldCover | class 10 | `forest_mask` | high | 含温带 / 热带 / 针叶混合，不区分类型 |
| ESA WorldCover | class 20 | `shrubland_mask` | high | — |
| ESA WorldCover | class 30 | `grassland_mask` | high | 含高原草地，与 plateau 有重叠 |
| ESA WorldCover | class 40 | `cropland_mask` | high | — |
| ESA WorldCover | class 50 | `builtup_mask` | high | 8K 分辨率下小城市可能丢失 |
| ESA WorldCover | class 60 | `bare_sparse_land_mask` | medium | ≠ desert_mask；含裸岩、荒漠、高山裸地 |
| ESA WorldCover | class 70 | `snow_ice_mask` | medium | ≠ glacier_mask；8K 平滑后极地边界有误差 |
| ESA WorldCover | class 80 | `esa_permanent_water_mask` | medium | ≠ lake topology；不含 lake island hierarchy |
| ESA WorldCover | class 90 | `wetland_mask` | medium | 不含 true delta / floodplain complex |
| ESA WorldCover | class 95 | `mangrove_mask` | high | 像素稀少（仅 6,279 px 在 8K），精度有限 |
| ESA WorldCover | class 100 | `moss_lichen_mask` | medium | 主要集中在极地 / 高纬度苔原 |
| ESA WorldCover | class 0 | — | — | ocean / background，**不作为 land cover class** |
| JRC GSW occurrence | ≥ 90 | `jrc_permanent_water_candidate` | medium-high | cross-check，非 topology |
| JRC GSW occurrence | 10–89 | `jrc_seasonal_water_candidate` | medium | 与 seasonality 联合使用更可靠 |
| JRC GSW max_extent | = 1 | `jrc_water_extent_mask` | medium | 历史最大范围，含已消退水体 |
| JRC GSW transition | 1,7,8,9 | `lake_water_crosscheck` | medium | 辅助 GSHHG 湖泊 topology 验证 |
| JRC GSW seasonality | ≥ 1 | `wetland_water_support` | low | 辅助 ESA class 90 wetland |
| Copernicus DEM elev | > 3500 m + slope < 5° | `plateau_candidate` | low-medium | proxy；需结合 ESA class |
| Copernicus DEM elev | > 2000 m + slope > 10° | `high_mountain_candidate` | low-medium | proxy；slope 8K 平滑，阈值需调校 |
| Copernicus DEM elev | < 200 m + slope < 2° | `lowland_plain_candidate` | low-medium | proxy；大量 nodata（海洋）需 mask |
| Copernicus DEM slope | 0–6.03° | `slope_relief_supplement` | low | resolution-limited；仅供粗趋势参考 |
| ETOPO1 bedrock | < -200 m | `deep_ocean_context` | medium | 与既有 deep_ocean_mask 对齐 |
| ETOPO1 bedrock | -200 – 0 m | `shallow_sea_context` | medium | 含陆架浅水，不含 reef |
| ETOPO1 bedrock | -200 – -2000 m | `continental_shelf_context` | medium | 粗分辨率，边界模糊 |
| ETOPO1 bedrock | < -6000 m | `bathymetry_context` | medium | 深渊 / 海沟定性 |
| ETOPO1 ice_surface | polar region | `ice_surface_context` | medium | 与 bedrock 差值可估计冰厚 |
| ETOPO1 bedrock | Antarctic / Greenland + < 0 | `polar_bedrock_context` | medium | 冰下地形参考，不作 mask |

---

## 3. ESA WorldCover Class Handling

### 3.1 Class 映射规则

```
class  0 → ocean / background / non-landcover
         → 不作为正式 land-cover class，在所有派生中显式 mask 排除
class 10 → forest_mask
class 20 → shrubland_mask
class 30 → grassland_mask
class 40 → cropland_mask
class 50 → builtup_mask
class 60 → bare_sparse_land_mask
class 70 → snow_ice_mask
class 80 → esa_permanent_water_mask
class 90 → wetland_mask
class 95 → mangrove_mask
class 100 → moss_lichen_mask
```

### 3.2 重要语义边界

**`bare_sparse_land_mask` ≠ `desert_mask`**

- ESA class 60 = "Bare or Sparse Vegetation"，覆盖范围包括：撒哈拉沙漠、阿拉伯半岛、澳大利亚内陆、青藏高原裸岩、高山无植被带、海岸沙滩、建筑废地
- desert 是气候 + 地貌概念，需要 aridity index（如 Global Aridity Index）联合判断
- M1 仅输出 `bare_sparse_land_mask`，不等价于 desert；`desert_mask` 列为 deferred

**`snow_ice_mask` ≠ `glacier_mask`**

- ESA class 70 = 2021 年影像中显示为雪 / 冰的像素，包含：极地冰盖、永久性冰川、季节性积雪（部分）
- glacier 需要单独的冰川数据集（如 GLIMS / RGI），不能由 ESA class 70 直接派生
- `glacier_mask` 列为 deferred

**`esa_permanent_water_mask` ≠ lake topology**

- ESA class 80 是像素级分类，不含湖泊边界 topology
- 无法区分湖中岛（lake island）、岛中湖（island lake）等嵌套结构
- lake topology 仍依赖 GSHHG L2/L3 层级；ESA water 仅作 cross-check

### 3.3 Nodata 处理约定

```python
# M1 代码约定：
ESA_NODATA = 0   # class 0 = ocean/background，显式标记为 nodata
mask = (esa_data == target_class) & (esa_data != ESA_NODATA)
```

---

## 4. JRC GSW Water Rules

### 4.1 各层语义

| Layer | 值域 | 语义 |
|-------|------|------|
| occurrence | 0–100 | 历史水体出现频率（%）；0 = 从未，100 = 全时段 |
| seasonality | 0–12 | 2021 年单年内水体出现月份数 |
| recurrence | 0–100 | 跨年重复出现频率（%）|
| max_extent | 0/1 | 历史最大水体范围（binary）|
| transition | 0–10 | 水体状态变化分类 |

### 4.2 Candidate Mask 派生规则

```
jrc_permanent_water_candidate:
  occurrence >= 90
  意义：长期稳定永久水体（湖泊核心、主要河流）

jrc_seasonal_water_candidate:
  10 <= occurrence < 90
  意义：季节性水体（湿季湖泊、季节性洪泛区）

jrc_water_extent_mask:
  max_extent == 1
  意义：历史曾为水体的最大范围（含已消退的 Aral Sea、Lake Chad 历史范围）

lake_water_crosscheck:
  transition in {1, 7, 8, 9}   (Permanent / Seasonal→Perm / Perm→Seasonal / Ephemeral Perm)
  意义：与 GSHHG L2 lake mask 做空间交叉验证

wetland_water_support:
  seasonality >= 1 AND occurrence < 50
  意义：辅助标记 ESA class 90 wetland 中含水比例较高的区域
```

### 4.3 JRC 的局限性

- **JRC 不替代 GSHHG lake topology**：GSHHG L2/L3 提供 lake 边界 polygon 和 lake island hierarchy，JRC 仅是像素级水体分类，无法表达湖中岛 / 岛中湖拓扑结构
- **JRC 不代表 true delta / floodplain**：三角洲和洪泛平原需要专项数据（如 GFW、HydroSHEDS），JRC max_extent 是近似
- **Aral Sea / Lake Chad 历史水域**：max_extent 可反映历史范围，但 occurrence 会显示当前已消退，使用时需区分 current vs. historical

---

## 5. Copernicus DEM Elevation / Slope Rules

### 5.1 Candidate Masks

```
high_mountain_candidate:
  elevation > 2000 m
  AND copernicus_dem nodata != -32768
  （slope 可选辅助；但 slope 8K 平滑限制阈值可靠性）
  Confidence: low-medium（proxy）

plateau_candidate:
  elevation > 3000 m
  AND slope < 3°    ← 8K 分辨率下近似平坦判断
  AND esa_class in {30, 60}  ← 草地或裸地（排除冰盖）
  Confidence: low-medium（proxy，藏高原适用，其他高原需验证）

lowland_plain_candidate:
  elevation < 200 m
  AND copernicus_dem nodata != -32768
  AND esa_class not in {80, 90}  ← 排除水体
  Confidence: low-medium（proxy，大量过滤需求）

slope_relief_supplement:
  slope > 1.0°    ← 8K 分辨率下任何 slope > 1° 可视为有地形起伏
  仅供辅助参考，不单独作为 mask
  Confidence: low（resolution-limited）

terrain_context:
  elevation 连续值保留，不二值化
  供后续 M2 validation / visual audit 使用
```

### 5.2 重要 Caveats

**Copernicus DEM GLO-30 是 DSM（Digital Surface Model），不是裸地 DEM（DTM）**

- DSM 包含植被冠层高度、建筑物高度，热带雨林区域高程会被抬高 10–30m
- 不要将其作为绝对地貌高程真值
- 高山 / 高原判断在热带植被区需额外谨慎

**Slope 精度限制（C2 Caveat，来自 D3）**

- 8K 导出时坡度最大值仅 6.03°，远低于真实坡度
- 所有 slope 阈值必须在低值范围内设计（如 < 3° = 平坦，> 1° = 有坡度）
- M1-B 实现时必须注明 slope 阈值是 8K-resolution-specific

**Nodata = -32768 = 主要为海洋**

- Copernicus DEM 不覆盖海底，nodata 区域主要为 ocean + 部分极地
- 派生地形 mask 时必须 `elevation != -32768` 作为前置过滤

---

## 6. ETOPO1 Bathymetry / Ocean Context Rules

### 6.1 Candidate Contexts

```
bathymetry_context:
  etopo1_bedrock 连续值（全域）
  供 ocean depth 视觉分层使用，不二值化

deep_ocean_context:
  etopo1_bedrock < -3500 m
  覆盖 abyssal plains、ocean trenches
  与既有 deep_ocean_mask 对齐验证

continental_shelf_context:
  -200 m <= etopo1_bedrock < 0 m
  AND esa_class == 0 (ocean)    ← 排除陆地上的低洼地
  粗近似大陆架范围

shallow_sea_context:
  -200 m <= etopo1_bedrock < 0 m（细化子集）
  与 jrc_water_extent 交叉可识别近海浅水
  不含 reef / atoll（需专项数据）

ice_surface_context:
  etopo1_ice_surface 连续值
  与 bedrock 的差值 = 冰层厚度估计（定性参考）
  ice_surface > bedrock 的区域 = 冰盖存在

polar_bedrock_context:
  etopo1_bedrock（南极洲 / 格陵兰 lat 范围）
  与 polar_land_ice_mask 联合使用
  不单独作为 mask 输出
```

### 6.2 ETOPO1 的局限性

- ETOPO1 分辨率约 1 arcmin（~1.85 km），在 8K 下尚可，但边界模糊
- **不解决 reef / atoll / 浅水细节**：Bahamas Bank、Maldives、Great Barrier Reef 等地物需要 GEBCO / Allen Coral Atlas 等专项数据，列为 Phase 3
- 海陆边界在 ETOPO1 中基于模型，实际海岸线以 GSHHG 为准

---

## 7. Confidence Levels

| Level | 定义 | 典型案例 |
|-------|------|---------|
| **high** | 直接来自可靠 source，语义明确，8K 精度可接受 | forest_mask, cropland_mask, mangrove_mask |
| **medium** | 来自可靠 source，但 8K 精度有限，或语义有歧义 | snow_ice_mask, jrc_permanent_water_candidate |
| **low** | proxy 推断，阈值设计依赖假设，需 M2 audit | high_mountain_candidate, plateau_candidate |
| **proxy** | 无直接 source，以间接数据近似 | slope_relief_supplement, terrain_context |
| **deferred** | 当前 source 不足以可靠派生 | desert_mask, glacier_mask, reef_mask |

### 各 Mask Confidence 汇总

| Mask | Confidence |
|------|-----------|
| `forest_mask` | high |
| `shrubland_mask` | high |
| `grassland_mask` | high |
| `cropland_mask` | high |
| `builtup_mask` | high |
| `bare_sparse_land_mask` | medium |
| `snow_ice_mask` | medium |
| `esa_permanent_water_mask` | medium |
| `wetland_mask` | medium |
| `mangrove_mask` | high（但像素稀少）|
| `moss_lichen_mask` | medium |
| `jrc_permanent_water_candidate` | medium-high |
| `jrc_seasonal_water_candidate` | medium |
| `jrc_water_extent_mask` | medium |
| `lake_water_crosscheck` | medium |
| `wetland_water_support` | low |
| `high_mountain_candidate` | low-medium |
| `plateau_candidate` | low-medium |
| `lowland_plain_candidate` | low-medium |
| `slope_relief_supplement` | low |
| `deep_ocean_context` | medium |
| `shallow_sea_context` | medium |
| `continental_shelf_context` | medium |
| `bathymetry_context` | medium |
| `ice_surface_context` | medium |
| `polar_bedrock_context` | medium |

---

## 8. Data-derived vs Proxy Classification

### Data-derived（直接从 source 二值化或分类）

以下 masks 为 **data-derived**：数值直接来自 source，无需推断。

- `forest_mask`、`shrubland_mask`、`grassland_mask`、`cropland_mask`、`builtup_mask`（ESA class 直接映射）
- `bare_sparse_land_mask`（ESA class 60）
- `snow_ice_mask`（ESA class 70）
- `esa_permanent_water_mask`（ESA class 80）
- `wetland_mask`（ESA class 90）
- `mangrove_mask`（ESA class 95）
- `moss_lichen_mask`（ESA class 100）
- `jrc_permanent_water_candidate`（occurrence threshold）
- `jrc_seasonal_water_candidate`（occurrence range）
- `jrc_water_extent_mask`（max_extent binary）
- `deep_ocean_context`（ETOPO1 threshold）
- `bathymetry_context`（ETOPO1 continuous）

### Proxy（由多 source 推断，或单 source + 假设阈值）

以下 masks 为 **proxy**：依赖阈值假设，不直接对应 source 的单一语义层。

- `high_mountain_candidate`（elevation threshold，受 DSM 影响）
- `plateau_candidate`（elevation + slope 联合，slope 8K 平滑严重）
- `lowland_plain_candidate`（elevation + land cover 过滤）
- `slope_relief_supplement`（slope 连续值参考）
- `continental_shelf_context`（ETOPO1 + ESA water 联合）
- `shallow_sea_context`（ETOPO1 bathymetry range）
- `lake_water_crosscheck`（JRC transition + GSHHG 联合）
- `wetland_water_support`（JRC seasonality + ESA class）
- `ice_surface_context`（ETOPO1 bedrock vs ice_surface 差值）

---

## 9. Priority / Conflict Principles

当同一像素被多个 mask 覆盖时，按以下原则处理：

### 9.1 基本优先级（高优先级覆盖低优先级）

```
polar_land_ice > snow_ice_mask
  → 极地冰盖优先于 ESA snow/ice 分类

lake_island > inland_water / jrc_water
  → 湖中岛优先于水体 mask（需要 GSHHG 拓扑支持）

special_sea > generic shallow_sea
  → Mediterranean / Red Sea 等特殊海区优先于通用浅海 mask

mangrove_mask > wetland_mask > grassland_mask
  → 越精细的植被分类优先级越高

builtup_mask 不覆盖 water / ocean mask
  → 不应因分类噪声将海上像素标为 built-up

JRC water cross-check，不自动替代 GSHHG topology
  → JRC 可辅助验证，但 lake boundary 仍以 GSHHG polygon 为准

Copernicus terrain context 不覆盖已验证的 water / ocean masks
  → 即使 elevation > 0，如果 JRC 标为永久水体，不应被地形 mask 覆盖
```

### 9.2 Conflict Resolution 原则

```
1. Water beats terrain:
   jrc_permanent_water 和 esa_permanent_water 优先于地形分类

2. Polar overrides:
   polar_land_ice 优先于所有非 polar 分类

3. Specificity beats generality:
   mangrove > wetland > bare_sparse_land（同区域时）

4. Existing verified masks not overwritten by proxy:
   既有通过 B-6.1/2 验证的 mask（ocean_mask, deep_ocean_mask 等）不被 M1 proxy 覆盖

5. Confidence-based fallback:
   low-confidence mask 不覆盖 high-confidence mask
```

### 9.3 已知冲突区域

| 区域 | 冲突 | 处理原则 |
|------|------|---------|
| 藏高原 | grassland vs plateau_candidate | grassland 保留，plateau_candidate 作 context 层 |
| 撒哈拉 | bare_sparse_land vs desert（deferred）| 仅输出 bare_sparse，注明 ≠ desert |
| 南极洲 | snow_ice vs polar_land_ice | polar_land_ice 优先 |
| 红树林区 | mangrove vs wetland vs esa_water | mangrove > wetland |
| 咸海 / Lake Chad | jrc_water_extent（历史）vs current water | 区分 current / historical，不合并 |

---

## 10. Deferred Masks

以下 masks 因 Phase 1 source 不足以可靠派生，暂缓至 Phase 2/3：

| Mask | 原因 | 所需 source |
|------|------|------------|
| `desert_mask` | ESA class 60 ≠ desert；需 aridity index | Global Aridity Index（GAI）|
| `true_delta_mask` | JRC 无三角洲拓扑 | HydroSHEDS / GFW |
| `true_wetland_complex_mask` | ESA class 90 过于粗略 | GLWD / HydroLAKES |
| `reef_mask` | GEE source 不覆盖 | Allen Coral Atlas / UNEP-WCMC |
| `atoll_mask` | 亚像素级地物，8K 下不可分辨 | 专项 reef / atoll 数据 |
| `glacier_mask` | ESA snow_ice ≠ glacier | GLIMS / RGI v7 |
| `high-confidence geomorphology` | 需要 DEM + geomorphon 分析 | 30m DEM + 专项处理 |
| `biome_mask` | 需要 Köppen / WWF Biome | WWF Terrestrial Ecoregions |
| `commercial-grade aridity` | 许可证待确认 | Trabucco & Zomer GAI |
| `floodplain_mask` | 历史洪泛需要时序数据 | JRC Annual Surface Water |

---

## 11. M1-B Prototype Scope

M1-A（本文件）= 设计阶段，只输出 design doc，不生成任何 mask。

**M1-B = Prototype Mask Generation**，在获得用户明确授权后执行：

- 目标：生成上述 data-derived masks 的 prototype
- 输出目录：`d5b_processor_v3/source_cache/gee_global/derived_masks/prototype_8k/`（gitignored）
- 输出格式：uint8 GeoTIFF，binary（0/1）或 categorical
- 空间对齐：与 Phase 1 source 相同 grid（8192×4096，WGS84）

**M1-B 仍不允许：**

- 接入 d6 generator
- 写 pwa / production / candidates
- 替换任何 production texture
- 提交 derived masks 到 git

---

## 12. M1 Forbidden Actions

本 M1 阶段（M1-A 和 M1-B）明确禁止：

```
✗ run d6
✗ generate Noon Air
✗ write pwa / production / candidates
✗ replace production texture
✗ commit source_cache data
✗ commit generated rasters (masks)
✗ push any binary data
✗ modify d5b_processor_v3/d6_noon_air_earth_generator.py
✗ download new source data without explicit authorization
✗ run scripts/generate_b6_structure_masks.py on production paths
```

---

## 13. Exit Criteria before M1-B

进入 M1-B（Prototype Mask Generation）前，以下条件必须全部满足：

| 条件 | 状态 |
|------|------|
| source-to-mask mapping 经用户 review / approved | ⬜ 待确认 |
| confidence labels 经用户 review / approved | ⬜ 待确认 |
| deferred masks 列表经用户确认 | ⬜ 待确认 |
| priority principles draft 经用户确认 | ⬜ 待确认 |
| M1-B 输出路径已确认（不接触 production）| ⬜ 待确认 |
| M1-B prototype mask 列表已确认（哪些先做）| ⬜ 待确认 |
| validation checklist for M2 drafted | ⬜ 待确认 |
| 用户明确授权 M1-B 执行 | ⬜ 待授权 |

---

## Appendix A：Phase 1 Source Class / Value Reference

### ESA WorldCover 2021 v200

| Class | Label | 8K pixel count | % |
|-------|-------|---------------|---|
| 0 | Background / Ocean | 24,407,626 | 72.75% |
| 10 | Tree cover | 2,799,895 | 8.34% |
| 20 | Shrubland | 423,809 | 1.26% |
| 30 | Grassland | 1,772,080 | 5.28% |
| 40 | Cropland | 719,114 | 2.14% |
| 50 | Built-up | 25,128 | 0.07% |
| 60 | Bare / Sparse vegetation | 1,147,537 | 3.42% |
| 70 | Snow and ice | 365,442 | 1.09% |
| 80 | Permanent water bodies | 1,361,700 | 4.06% |
| 90 | Herbaceous wetland | 176,756 | 0.53% |
| 95 | Mangroves | 6,279 | 0.02% |
| 100 | Moss and lichen | 349,066 | 1.04% |

### JRC GSW Transition Class Reference

| Value | Label |
|-------|-------|
| 0 | No water |
| 1 | Permanent |
| 2 | New permanent |
| 3 | Lost permanent |
| 4 | Seasonal |
| 5 | New seasonal |
| 6 | Lost seasonal |
| 7 | Seasonal to permanent |
| 8 | Permanent to seasonal |
| 9 | Ephemeral permanent |
| 10 | Ephemeral seasonal |

---

*Document created: 2026-06-24*  
*Stage: B-6.2X-M1-A (Design only)*  
*No masks generated. No code modified. No data moved or deleted.*
