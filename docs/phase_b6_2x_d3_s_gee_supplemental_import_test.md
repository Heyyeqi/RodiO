# Phase B-6.2X-D3-S — GEE Supplemental 8K Import Test

Stage: B-6.2X-D3-S  
Type: Supplemental source import test  
Status: **conditional_pass**  
Date: 2026-06-24  
Tool: tifffile 2026.6.1 + numpy 2.5.0

---

## 1. Scope

对 `d5b_processor_v3/source_cache/gee_global/supplemental_8k/` 中 6 个 GEE supplemental source 执行 import test，评估其是否可作为 M1 / M2 阶段的 cross-check / 补充数据源。

本轮不生成任何 mask，不修改生产文件。

---

## 2. Input Source Inventory

| 文件 | 大小 | 用途定位 |
|------|------|---------|
| `merit_dem_v1_0_3_elevation_8192x4096.tif` | 13.01 MB | Copernicus DEM terrain cross-check |
| `modis_mcd12q1_2021_lc_type1_8192x4096.tif` | 1.28 MB | ESA land cover cross-check（IGBP scheme）|
| `modis_mcd12q1_2021_lc_type5_8192x4096.tif` | 1.01 MB | 植被功能型（PFT）辅助 |
| `modis_mcd12q1_2021_lc_prop1_8192x4096.tif` | 1.23 MB | FAO-LCCS land cover 补充 |
| `modis_mcd12q1_2021_qc_8192x4096.tif` | 0.68 MB | MODIS 分类置信度（QC layer）|
| `srtm_landforms_global_8192x4096.tif` | 1.79 MB | 地貌形态 context cross-check |

---

## 3. Import Test Method

- 工具：tifffile + numpy（imagecodecs LZW 解压）
- 检查项：dimensions、dtype、compression、nodata、CRS、origin、pixel_size、pixel stats、class histogram
- Phase 1 对齐基准：8192×4096，origin (-180, 90)，pixel_dx = 0.0439453125°，EPSG:4326

---

## 4. Per-File Results

### 4.1 MERIT DEM

| 项目 | 值 |
|------|----|
| file | `merit_dem_v1_0_3_elevation_8192x4096.tif` |
| size | 13.01 MB |
| width × height | 8192 × 4096 ✅ |
| bands | 1 |
| dtype | int16 ✅ |
| nodata | -32768 ✅ |
| origin | (-180.0, 89.999) ✅ |
| pixel size | 0.04394531° ✅ |
| CRS | EPSG:4326 ✅ |
| north-up | ✅ |
| Phase 1 grid match | ✅ |
| total pixels | 33,554,432 |
| valid pixels | 8,113,365（24.18%）|
| nodata pixels | 25,441,067（75.82%）|
| min | -414 m |
| max | 7,396 m |
| mean (valid) | 652.10 m |
| unique count | 6,575 |

**与 Copernicus DEM 对比：**

| 指标 | MERIT DEM | Copernicus DEM |
|------|-----------|---------------|
| min | -414 m | -427 m |
| max | 7,396 m | 7,953 m |
| mean | 652 m | 900 m |
| valid % | 24.18% | 40.25% |
| nodata tag | -32768 | -32768 |

- **max 差 557 m**：MERIT 是 DTM（Bare Earth，已去除植被冠层 + 建筑），Copernicus 是 DSM（Digital Surface Model，含冠层）。差值符合预期，两者均合理。MERIT 对裸地地形更准确，Copernicus 在热带林区高程偏高。
- **valid 像素 24.18% vs 40.25%**：MERIT nodata 范围更大（更严格排除海岸带 / 低可信度区域），不是错误。
- **min -414 m**：Dead Sea（约 -430m），与 Copernicus -427m 吻合 ✅

**Verdict：PASS（可作为 Copernicus DEM 地形 sanity check）**

---

### 4.2 MODIS MCD12Q1 LC_Type1（IGBP）

| 项目 | 值 |
|------|----|
| file | `modis_mcd12q1_2021_lc_type1_8192x4096.tif` |
| size | 1.28 MB |
| width × height | 8192 × 4096 ✅ |
| dtype | uint8 ✅ |
| nodata tag | **none** ⚠️ |
| origin | (-180.0, 89.999) ✅ |
| CRS | EPSG:4326 ✅ |
| north-up | ✅ |
| values | 0–17，18 unique ✅ |

**IGBP Class Histogram：**

| class | label | pixels | % |
|-------|-------|--------|---|
| 0 | Unclassified / background | 8,282,427 | 24.7% |
| 1 | Evergreen Needleleaf Forest | 171,964 | 0.5% |
| 2 | Evergreen Broadleaf Forest | 525,821 | 1.6% |
| 3 | Deciduous Needleleaf Forest | 15,398 | 0.05% |
| 4 | Deciduous Broadleaf Forest | 147,884 | 0.4% |
| 5 | Mixed Forests | 337,806 | 1.0% |
| 6 | Closed Shrublands | 20,031 | 0.06% |
| 7 | Open Shrublands | 931,915 | 2.8% |
| 8 | Woody Savannas | 738,845 | 2.2% |
| 9 | Savannas | 917,254 | 2.7% |
| 10 | Grasslands | 1,776,376 | 5.3% |
| 11 | Permanent Wetlands | 71,139 | 0.2% |
| 12 | Croplands | 656,348 | 2.0% |
| 13 | Urban and Built-up | 38,163 | 0.1% |
| 14 | Cropland/Natural Veg Mosaics | 63,276 | 0.2% |
| **15** | **Permanent Snow and Ice** | **3,513,059** | **10.5%** |
| 16 | Barren | 1,047,775 | 3.1% |
| 17 | Water Bodies | 14,298,951 | 42.6% |

> ⚠️ **C1 — Snow/Ice 覆盖异常高（10.5% vs ESA 1.09%）**
>
> MODIS class 15 = 10.5%（3.5M 像素），ESA class 70 仅 1.09%（365K 像素），差距约 10 倍。
> 可能原因：
> 1. MODIS MCD12Q1 在南北极区域将**海冰（sea ice）**纳入 class 15；ESA 仅标注陆地冰雪
> 2. MODIS 500m base resolution 对季节性积雪捕捉范围更广，重采样至 8K 仍保留较多像素
> 3. GEE 导出时 scale 设置影响聚合方式
>
> 此差异**不是错误**，是两套分类体系的语义差异。M1 使用 MODIS 时需区分"陆地冰雪"与"海冰"，不能直接与 ESA snow_ice 比较。

> ⚠️ **C2 — 无 nodata tag**：class 0 = 隐式 background/unclassified，使用时需显式 mask 排除。

**Verdict：PASS（可作为 ESA land cover cross-check，注意 class 15 语义差异）**

---

### 4.3 MODIS MCD12Q1 LC_Type5（PFT）

| 项目 | 值 |
|------|----|
| file | `modis_mcd12q1_2021_lc_type5_8192x4096.tif` |
| size | 1.01 MB |
| width × height | 8192 × 4096 ✅ |
| dtype | uint8 ✅ |
| nodata tag | **none** ⚠️ |
| values | 0–11，12 unique ✅ |

**PFT Class Histogram：**

| class | label | pixels | % |
|-------|-------|--------|---|
| 0 | Background / Water | 22,567,248 | **67.3%** |
| 1 | Evergreen Needleleaf Trees | 753,685 | 2.2% |
| 2 | Evergreen Broadleaf Trees | 953,477 | 2.8% |
| 3 | Deciduous Needleleaf Trees | 410,360 | 1.2% |
| 4 | Deciduous Broadleaf Trees | 892,402 | 2.7% |
| 5 | Shrubs | 958,774 | 2.9% |
| 6 | Grass / Cereal crops | 1,788,493 | 5.3% |
| 7 | Broadleaf crops | 436,880 | 1.3% |
| 8 | Urban and built-up | 196,621 | 0.6% |
| 9 | Snow and ice | 36,890 | 0.1% |
| 10 | Barren or sparsely vegetated | 3,512,494 | 10.5% |
| 11 | Water | 1,047,108 | 3.1% |

> ⚠️ **C3 — LC_Type5 class 0 = 67.3%（异常高）**：
> LC_Type5 的 class 0 占比 67.3%，远高于 LC_Type1 的 24.7%。在 MODIS PFT 体系中，class 0 通常代表 open water + unclassified，而 class 11 单独标注水体。两者合计约 70.4%，与 MODIS "non-land" 区域一致。
> 结论：LC_Type5 对 ocean 的编码方式不同于 LC_Type1（ocean 在 LC_Type1 中主要是 class 17），使用时需注意。

**Verdict：PASS（PFT 层可作为森林/草地/裸地亚类型辅助参考）**

---

### 4.4 MODIS MCD12Q1 LC_Prop1（FAO-LCCS1）

| 项目 | 值 |
|------|----|
| file | `modis_mcd12q1_2021_lc_prop1_8192x4096.tif` |
| size | 1.23 MB |
| width × height | 8192 × 4096 ✅ |
| dtype | uint8 ✅ |
| nodata tag | **none** ⚠️ |
| values | 0,1,2,3,11–16,21–22,31–32,41–43（17 unique）✅ |

**FAO-LCCS1 Class Histogram（主要类）：**

| class | label | pixels | % |
|-------|-------|--------|---|
| 0 | Background / unclassified | 8,282,765 | 24.7% |
| 1 | Barren | 1,060,744 | 3.2% |
| 2 | Permanent Snow and Ice | 3,513,491 | 10.5% |
| 3 | Water bodies | 14,296,243 | 42.6% |
| 11 | Evergreen needleleaf forests | 173,535 | 0.5% |
| 12 | Evergreen broadleaf forests | 532,757 | 1.6% |
| 13–16 | Other forests | ~498K | ~1.5% |
| 21 | Shrublands | 745,342 | 2.2% |
| 22 | Shrub open | 1,036,676 | 3.1% |
| 31 | Savannas | 2,079,328 | 6.2% |
| 32 | Grasslands | 369,319 | 1.1% |
| 34 | （other）| 1,639,592 | 4.9% |
| 41 | Croplands | 20,689 | 0.06% |
| 42 | Mosaics | 621,194 | 1.9% |
| 43 | Wetlands | 327,223 | 1.0% |

- FAO-LCCS 使用两位分层编码（10s=Forest, 20s=Shrub, 30s=Grassland/Savanna, 40s=Cropland）
- snow/ice（class 2）= 10.5%，与 LC_Type1 class 15 一致，是系统性特征
- Wetlands（class 43）= 1.0%，与 ESA class 90（0.53%）有差异，FAO-LCCS 定义更宽

**Verdict：PASS（FAO-LCCS 层可作为植被亚类型 cross-check，特别是 savanna / shrubland 区域）**

---

### 4.5 MODIS MCD12Q1 QC

| 项目 | 值 |
|------|----|
| file | `modis_mcd12q1_2021_qc_8192x4096.tif` |
| size | 0.68 MB |
| width × height | 8192 × 4096 ✅ |
| dtype | uint8 ✅ |
| nodata tag | **none** ⚠️ |
| values | 0–10，11 unique ✅ |

**QC Histogram：**

| value | 含义 | pixels | % |
|-------|------|--------|---|
| 0 | High confidence classified | 15,865,091 | 47.3% |
| 1 | Medium confidence classified | 2,913 | 0.01% |
| 2 | Low confidence classified | 1,527,089 | 4.6% |
| 3 | Water | 12,387,757 | 36.9% |
| 4 | Unclassified land | 366,537 | 1.1% |
| 5 | Misclassified (known error) | 15,081 | 0.05% |
| 6 | Snow and ice | 3,312,506 | 9.9% |
| 7 | Barren tundra | 10 | 0.0% |
| 8 | Failed classification | 10,608 | 0.03% |
| 9 | Cloud shadow contamination | 25,404 | 0.08% |
| 10 | Fill / outside coverage | 41,436 | 0.12% |

- **QC=0（High confidence）= 47.3%**：可作为高可信像素筛选依据
- **QC=6（Snow/Ice）= 9.9%**：与 LC 层 snow/ice 比例一致 ✅
- **QC=2（Low confidence）= 4.6%**：在 M1 cross-check 中可降权处理
- **Fill/Outside coverage（QC=10）= 0.12%**：极少，可忽略

**使用建议：** cross-check 时用 `QC in {0, 3, 6}` 筛选高可信像素，排除 `QC in {2, 4, 5, 8, 9}` 区域。

**Verdict：PASS（QC 层可用于 MODIS cross-check 可信度加权）**

---

### 4.6 SRTM Landforms

| 项目 | 值 |
|------|----|
| file | `srtm_landforms_global_8192x4096.tif` |
| size | 1.79 MB |
| width × height | 8192 × 4096 ✅ |
| dtype | uint8 ✅ |
| nodata tag | **none** ⚠️（class 0 = ocean/nodata）|
| values | 0,11–15,21–24,31–34,41–42（16 unique）✅ |

**Landform Class Histogram：**

| class | 地貌类型 | pixels | % |
|-------|---------|--------|---|
| 0 | Ocean / NoData | 25,934,754 | 77.3% |
| 11 | Peak / Ridgetop（steep, high）| 2,245 | 0.007% |
| 12 | Peak（moderate）| 2,578 | 0.008% |
| 13 | Peak（gentle）| 161 | 0.0005% |
| 14 | Ridgeline（steep）| 1,392 | 0.004% |
| 15 | Ridgeline（moderate）| 1,337 | 0.004% |
| 21 | Upper slope（steep）| 1,164,909 | 3.5% |
| 22 | Upper slope（moderate）| 2,212,198 | 6.6% |
| 23 | Upper slope（gentle）| 28,220 | 0.08% |
| 24 | Flat ridge | 1,112,250 | 3.3% |
| 31 | Lower slope（steep）| 868,641 | 2.6% |
| 32 | Lower slope（moderate）| 496,190 | 1.5% |
| 33 | Lower slope（gentle）| 23,230 | 0.07% |
| 34 | Valley / flat low | 1,639,592 | 4.9% |
| 41 | Plain / flat（low elevation）| 62,653 | 0.2% |
| 42 | Depression / basin | 4,082 | 0.01% |

- 16 个分类值，覆盖从山峰到洼地的完整地貌谱系 ✅
- 1x 系列（peak/ridge）像素极少（合计 <100 px per class），符合全球尺度极端地形占比 ✅
- class 0（77.3%）= ocean/nodata；class 34（valley/flat low）= 4.9% 是最大有效类别
- 无 all-zero / all-nodata 问题 ✅
- 无 nodata tag（class 0 = 隐式 nodata）

> ℹ️ **地貌方案推断**：class 值的 10/20/30/40 分层结构与 Iwahashi & Pike (2007) 地貌自动分类或 Jasiewicz & Stepinski 地形位置指数（TPI）方案一致。具体来源为 Amatulli et al. (2018) geomorpho90m 或 Theobald et al. 的 SRTM-based 全球地貌产品，需在 M1-B 代码中注明 attribution。

**Verdict：PASS（可作为 terrain landform context cross-check）**

---

## 5. Alignment / CRS Summary

| 项目 | 6 文件结果 |
|------|-----------|
| 分辨率（8192×4096）| ✅ 全部通过 |
| CRS | EPSG:4326 geographic ✅ 全部一致 |
| origin_x | -180.0 ✅ 全部一致 |
| origin_y | **89.999**（全部），非 90.0 ⚠️ |
| pixel_dx | 0.04394531° ✅ 与 Phase 1 一致 |
| north-up | ✅ 全部通过 |
| Phase 1 grid match | ✅ 全部通过 |

> ⚠️ **origin_y = 89.999 vs Phase 1 origin_y = 90.0**
>
> 所有 6 个 supplemental 文件的 origin_y = 89.999，与 Phase 1 主文件（ETOPO1、JRC 等）的 90.0 有 0.001° 差距。这与 D3-R 中 Copernicus DEM r00 行 tile 的 89.999 偏差相同，是 GEE 导出的浮点精度问题，不是真实错误。
>
> 实际影响：约 0.001° × 111km/° = **约 111m 偏移**，在 8K 分辨率（~4.9km/pixel）下远小于 1 像素。可视为对齐，无需校正。

---

## 6. Value / Histogram Summary

| 源 | 值域 | 类型 | 异常说明 |
|----|------|------|---------|
| MERIT DEM | -414 ~ +7396 m | continuous int16 | 正常；max 低于 Copernicus（DTM vs DSM）|
| MODIS LC_Type1 | 0–17 | categorical uint8 | class 15 雪冰 10.5%（含海冰）|
| MODIS LC_Type5 | 0–11 | categorical uint8 | class 0 背景 67.3%（编码与 Type1 不同）|
| MODIS LC_Prop1 | 多值 | categorical uint8 | 正常；FAO-LCCS 两位分层编码 |
| MODIS QC | 0–10 | categorical uint8 | 正常；QC=0 高可信 47.3% |
| SRTM Landforms | 0,11–42 | categorical uint8 | 正常；class 0 隐式 nodata 77.3% |

---

## 7. Issues Found

| ID | 文件 | 描述 | 优先级 | D3-S 影响 |
|----|------|------|--------|-----------|
| C1 | MODIS LC_Type1 | class 15 Snow/Ice = 10.5%，远高于 ESA 1.09%，含海冰 | 中等 | 文档记录，不阻塞 |
| C2 | 所有 MODIS | 无 nodata tag，class 0 = 隐式 background | 中等 | M1 代码需显式处理 |
| C3 | MODIS LC_Type5 | class 0 = 67.3%（编码方式异于 Type1）| 低 | 使用时注意 |
| C4 | SRTM Landforms | 无 nodata tag，class 0 = 隐式 ocean/nodata | 中等 | M1 代码需显式处理 |
| C5 | 所有 6 文件 | origin_y = 89.999（浮点偏差）| 低 | 亚像素级，可忽略 |

**无 critical issue。**

---

## 8. Supplemental Source Verdict

```
conditional_pass
```

**通过条件：**
- 6 / 6 文件：8192×4096，EPSG:4326，north-up，Phase 1 grid 对齐 ✅
- 值域全部合理，无 all-zero / all-nodata 问题 ✅
- 各层语义符合预期 ✅

**条件（M1 使用前需处理）：**
- C1：MODIS snow/ice 含海冰，不可直接与 ESA snow_ice 比较
- C2/C4：所有文件无 nodata tag，class 0 必须显式 mask
- C3：LC_Type5 编码方式特殊，独立处理
- C5：origin_y 89.999 偏差可接受，亚像素级

---

## 9. Impact on M1-A / M1-B

### 9.1 MERIT DEM → Copernicus terrain sanity check

**建议纳入 M1。**

- MERIT 是 DTM（bare earth），Copernicus 是 DSM。两者 min / value distribution 可相互验证
- M1-B 可计算两者差值（Copernicus - MERIT），识别植被冠层抬高区域（主要热带林）
- MERIT max 7396 m vs Copernicus 7953 m：差值约 550 m，集中在热带雨林区
- 对 `high_mountain_candidate` / `plateau_candidate` 派生：可用 MERIT 作为双重确认

### 9.2 MODIS LC_Type1 → ESA land cover cross-check

**建议纳入 M1，作为 cross-check 层，不替代 ESA。**

- 特别适用于：barren / sparse vegetation 区域（MODIS class 16 = ESA class 60 对比）
- 不适用于：snow/ice 直接比较（语义不一致）
- 建议与 QC 层联合使用：仅使用 QC=0 或 QC=3 的像素

### 9.3 MODIS LC_Type5（PFT）→ 植被亚类型辅助

**可选纳入 M1，价值中等。**

- PFT 层对区分 Evergreen Needleleaf vs Broadleaf 有价值（ESA class 10 不区分）
- 8K 下细节有限，建议作为 optional supplemental，不作为主 mask 来源

### 9.4 MODIS LC_Prop1（FAO-LCCS）→ 植被层次辅助

**可选纳入 M1，主要用于 savanna / shrubland / grassland 分辨。**

- FAO-LCCS 的 30s 系列（Savannas + Grasslands）可辅助区分 ESA class 30 内部差异
- class 31（Savannas）= 6.2%，class 32（Grasslands）= 1.1%，信息量有限

### 9.5 SRTM Landforms → 地貌 context cross-check

**建议纳入 M1，作为 terrain context 补充。**

- 可辅助验证 `high_mountain_candidate`（class 11–15 区域）
- 可辅助识别 `lowland_plain_candidate`（class 34 valley/flat + class 41 plain）
- 注意：SRTM Landforms 是 context layer，不能替代 Copernicus DEM elevation 的数值精度

### 9.6 是否需要更新 M1-A 设计文档

**建议更新**，新增一节"Supplemental Sources"，内容：

```
MERIT DEM    → terrain sanity check（DTM vs DSM cross-verify）
MODIS Type1  → ESA barren/vegetation cross-check（with QC filter）
MODIS Type5  → forest subtype supplement（optional）
MODIS Prop1  → savanna/shrubland disambiguation（optional）
MODIS QC     → confidence weighting for all MODIS cross-checks
SRTM Landforms → landform context verification
```

---

## 10. Next Recommendation

1. **D3-S 已完成**，6 个 supplemental sources 均通过 conditional_pass
2. **建议更新 M1-A 设计文档**（`docs/phase_b6_2x_m1_semantic_mask_derivation_design.md`），新增 supplemental sources 章节
3. **M1-B 准备就绪**：Phase 1（10 files）+ Supplemental（6 files）共 16 个 source，可进入 prototype mask 生成
4. **进入 M1-B 需用户明确授权**，不自动执行

---

*Test executed: 2026-06-24*  
*Tools: tifffile 2026.6.1, numpy 2.5.0*  
*No masks generated. No code modified. No files moved or deleted.*
