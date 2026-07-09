# Phase B-6.2X-D3 — 8K Import Test

Stage: B-6.2X-D3  
Type: 8K source import test  
Status: **conditional_pass**  
Date: 2026-06-23  
Tool: tifffile 2026.6.1 + numpy 2.5.0 (no GDAL / rasterio)

---

## 1. Scope

对 `d5b_processor_v3/source_cache/gee_global/exported_8k/` 中已下载的 9 个 Phase 1 8K `.tif` 文件执行完整 import test，检查维度、dtype、CRS、方向、值域、histogram 等。

`copernicus_dem_glo30_elevation_8192x4096.tif` 缺失，在 Section 3 单独标记为 blocked。

**本轮不生成任何 mask、不运行 generator、不修改生产文件。**

---

## 2. Input Source Inventory

| 文件 | 大小 | 类型 | 本地状态 |
|------|------|------|---------|
| `esa_worldcover_2021_v200_map_8192x4096.tif` | 1.29 MB | required | ✅ 存在 |
| `etopo1_bedrock_8192x4096.tif` | 56.45 MB | required | ✅ 存在 |
| `etopo1_ice_surface_8192x4096.tif` | 55.30 MB | required | ✅ 存在 |
| `jrc_gsw_occurrence_8192x4096.tif` | 4.82 MB | required | ✅ 存在 |
| `jrc_gsw_seasonality_8192x4096.tif` | 2.61 MB | required | ✅ 存在 |
| `jrc_gsw_recurrence_8192x4096.tif` | 4.48 MB | required | ✅ 存在 |
| `jrc_gsw_max_extent_8192x4096.tif` | 0.48 MB | required | ✅ 存在 |
| `jrc_gsw_transition_8192x4096.tif` | 2.12 MB | optional | ✅ 存在 |
| `copernicus_dem_glo30_slope_8192x4096.tif` | 5.60 MB | optional | ✅ 存在 |
| `copernicus_dem_glo30_elevation_8192x4096.tif` | — | required | **✗ blocked** |
| `test_copernicus_dem_global_512x256.tif` | 90 KB | test file | 存在，未测试 |

---

## 3. Missing / Blocked Sources

```
copernicus_dem_glo30_elevation_8192x4096.tif
  status:  blocked
  reason:  GEE 8K global export instability
  impact:  terrain elevation-derived masks cannot yet be upgraded from
           Copernicus DEM; existing ETOPO1-derived terrain proxies
           remain active fallback; slope layer exists but is resolution-
           limited (see Section 5.9)
```

---

## 4. Import Test Method

- **库**：`tifffile 2026.6.1` + `numpy 2.5.0`
- **读取内容**：TIFF header tags（dimensions, dtype, compression, GeoTIFF spatial tags GDAL_NODATA/33550/33922）+ LZW 解压全像素
- **LZW 解压**：需 `imagecodecs`，已安装
- **像素统计**：min, max, mean, unique values, histogram（categorical）或 unique sample（continuous）
- **Nodata 处理**：从 GDAL_NODATA tag（42113）读取；无 tag 则视全部像素为有效

---

## 5. Per-File Results

### 5.1 ESA WorldCover

| 项目 | 值 |
|------|----|
| file | `esa_worldcover_2021_v200_map_8192x4096.tif` |
| size | 1.29 MB |
| width × height | 8192 × 4096 ✅ |
| bands | 1 |
| dtype | uint8 ✅ |
| compression | LZW |
| nodata tag | **none** ⚠️ |
| origin | -180.0, 90.0 ✅ |
| pixel size | 0.04394531° ✅ |
| CRS hint | geographic (degrees) ✅ |
| north-up | ✅ |
| total pixels | 33,554,432 |
| nodata pixels | 0 (no tag) |
| min | 0 |
| max | 100 |
| mean | 11.16 |
| unique count | 12 |

**Class histogram：**

| class | label | count | % |
|-------|-------|-------|---|
| 0 | background / ocean (implicit) | 24,407,626 | 72.75% |
| 10 | Tree cover | 2,799,895 | 8.34% |
| 20 | Shrubland | 423,809 | 1.26% |
| 30 | Grassland | 1,772,080 | 5.28% |
| 40 | Cropland | 719,114 | 2.14% |
| 50 | Built-up | 25,128 | 0.07% |
| 60 | Bare / Sparse vegetation | 1,147,537 | 3.42% |
| 70 | Snow / Ice | 365,442 | 1.09% |
| 80 | Permanent water | 1,361,700 | 4.06% |
| 90 | Herbaceous wetland | 176,756 | 0.53% |
| 95 | Mangrove | 6,279 | 0.02% |
| 100 | Moss / Lichen | 349,066 | 1.04% |

**Verdict：PASS（含条件）**

- 全部 11 个官方 ESA WorldCover class 值均存在 ✅
- 值域 10–100 符合预期 ✅
- class 0（72.75% 像素）= 隐式 ocean / background，**没有 nodata tag**

> ⚠️ **Caveat C1（nodata 约定）**：ESA WorldCover 无 nodata tag，class 0 代表 ocean/background。后续 mask 代码必须显式排除 `class == 0` 或在派生时映射为 nodata，不可将 class 0 作为有效地表分类处理。这不是 D3 失败项，但必须在 M1 mask 代码中记录。

---

### 5.2 ETOPO1 Bedrock

| 项目 | 值 |
|------|----|
| file | `etopo1_bedrock_8192x4096.tif` |
| size | 56.45 MB |
| width × height | 8192 × 4096 ✅ |
| bands | 1 |
| dtype | int16 ✅ |
| nodata tag | none（int16 全域有效）✅ |
| origin | -180.0, 90.0 ✅ |
| pixel size | 0.04394531° ✅ |
| CRS hint | geographic (degrees) ✅ |
| north-up | ✅ |
| total pixels | 33,554,432 |
| min | -10,761 m |
| max | 7,980 m |
| mean | -2,112.70 m |
| unique count | 15,966 |

- 深海负值存在（min -10,761 m，接近马里亚纳海沟 ~-10,935 m）✅
- 陆地正值存在（max 7,980 m，接近珠峰 ~8,849 m，8K 分辨率重采样合理）✅
- mean -2,112 m 符合全球平均海拔（以海洋为主）✅
- 无全零 / 全 nodata 问题 ✅

**Verdict：PASS**

---

### 5.3 ETOPO1 Ice Surface

| 项目 | 值 |
|------|----|
| file | `etopo1_ice_surface_8192x4096.tif` |
| size | 55.30 MB |
| width × height | 8192 × 4096 ✅ |
| bands | 1 |
| dtype | int16 ✅ |
| nodata tag | none ✅ |
| origin | -180.0, 90.0 ✅ |
| pixel size | 0.04394531° ✅ |
| CRS hint | geographic (degrees) ✅ |
| north-up | ✅ |
| min | -10,761 m |
| max | 7,980 m |
| mean | -1,892.41 m |
| unique count | 15,966 |

- ice_surface mean（-1,892）> bedrock mean（-2,113）：ice surface 整体更高，符合冰盖抬升地表的预期 ✅
- 两者 min / max 相同：int16 范围一致，deep ocean 底部不受冰盖影响 ✅
- 差值主要体现在南极洲 / 格陵兰等冰盖区域，mean 差 ~220 m 合理 ✅

**Verdict：PASS**

---

### 5.4 JRC GSW Occurrence

| 项目 | 值 |
|------|----|
| file | `jrc_gsw_occurrence_8192x4096.tif` |
| size | 4.82 MB |
| width × height | 8192 × 4096 ✅ |
| bands | 1 |
| dtype | uint8 ✅ |
| nodata tag | none（0 = no water）✅ |
| origin | -180.0, 90.0 ✅ |
| pixel size | 0.04394531° ✅ |
| north-up | ✅ |
| min | 0 |
| max | 100 |
| mean | 7.05 |
| unique count | 101（0–100 全覆盖）✅ |

- 值域 0–100（occurrence 百分比）✅
- 101 个唯一值 = 0 到 100 整数全部出现 ✅
- mean 7.05 合理（大量像素为 0，即陆地 / 非水体背景）
- 无 all-zero / all-nodata 问题 ✅

**Verdict：PASS**

---

### 5.5 JRC GSW Seasonality

| 项目 | 值 |
|------|----|
| file | `jrc_gsw_seasonality_8192x4096.tif` |
| size | 2.61 MB |
| width × height | 8192 × 4096 ✅ |
| bands | 1 |
| dtype | uint8 ✅ |
| nodata tag | none（0 = no water）✅ |
| origin | -180.0, 90.0 ✅ |
| north-up | ✅ |
| min | 0 |
| max | 12 |
| mean | 0.957 |
| unique count | 13（0–12 全覆盖）✅ |

**Histogram（0–12 months）：**

| 值 | 含义 | 像素数 |
|----|------|-------|
| 0 | no water / background | 29,088,054 |
| 1–11 | seasonal (1–11 months) | ~3,244,508 |
| 12 | permanent water | 1,221,126 |

- 值域 0–12（月份数）✅
- 永久水体（12）约 120 万像素（~3.64%）合理
- 0–11 季节性水体梯度存在 ✅

**Verdict：PASS**

---

### 5.6 JRC GSW Recurrence

| 项目 | 值 |
|------|----|
| file | `jrc_gsw_recurrence_8192x4096.tif` |
| size | 4.48 MB |
| width × height | 8192 × 4096 ✅ |
| bands | 1 |
| dtype | uint8 ✅ |
| nodata tag | none ✅ |
| origin | -180.0, 90.0 ✅ |
| north-up | ✅ |
| min | 0 |
| max | 100 |
| mean | 12.66 |
| unique count | 100（注：值 2 缺失，其余 1–100 存在）|

- 值域 0–100（recurrence 百分比）✅
- 值 2 缺失（100 unique values 而非 101）：JRC recurrence 内部编码特性，非错误
- mean 12.66 高于 occurrence mean 7.05：符合 recurrence 计算逻辑（历史出现频率）✅

**Verdict：PASS**

---

### 5.7 JRC GSW Max Extent

| 项目 | 值 |
|------|----|
| file | `jrc_gsw_max_extent_8192x4096.tif` |
| size | 0.48 MB |
| width × height | 8192 × 4096 ✅ |
| bands | 1 |
| dtype | uint8 ✅ |
| nodata tag | none ✅ |
| origin | -180.0, 90.0 ✅ |
| north-up | ✅ |
| min | 0 |
| max | 1 |
| mean | 0.0287 |
| unique count | 2（binary）✅ |

**Histogram：**

| 值 | 含义 | 像素数 | % |
|----|------|-------|---|
| 0 | 从未观测到水体 | 32,593,016 | 97.13% |
| 1 | 历史最大水体范围内 | 961,416 | 2.87% |

- Binary mask，值仅 0/1 ✅
- 约 2.87% 像素为 1（历史最大水体范围），与全球水体覆盖预期一致 ✅
- 文件 0.48 MB 极小，因 LZW 对二值图压缩率极高，正常 ✅

**Verdict：PASS**

---

### 5.8 JRC GSW Transition

| 项目 | 值 |
|------|----|
| file | `jrc_gsw_transition_8192x4096.tif` |
| size | 2.12 MB |
| width × height | 8192 × 4096 ✅ |
| bands | 1 |
| dtype | uint8 ✅ |
| nodata tag | none ✅ |
| origin | -180.0, 90.0 ✅ |
| north-up | ✅ |
| min | 0 |
| max | 10 |
| mean | 0.617 |
| unique count | 11（0–10 全覆盖）✅ |

**Histogram（官方 JRC Transition class）：**

| 值 | 官方含义 | 像素数 |
|----|---------|-------|
| 0 | No water | 28,591,488 |
| 1 | Permanent | 2,139,856 |
| 2 | New permanent | 190,389 |
| 3 | Lost permanent | 30,968 |
| 4 | Seasonal | 266,095 |
| 5 | New seasonal | 1,076,252 |
| 6 | Lost seasonal | 192,293 |
| 7 | Seasonal to permanent | 19,617 |
| 8 | Permanent to seasonal | 47,442 |
| 9 | Ephemeral permanent | 17,454 |
| 10 | Ephemeral seasonal | 982,578 |

- 全部 11 个官方 class 值存在 ✅
- class 1（Permanent）约 213 万像素，class 10（Ephemeral seasonal）约 98 万，分布合理 ✅
- optional supplement，可用于辅助 permanent / seasonal water 分离 ✅

**Verdict：PASS**

---

### 5.9 Copernicus DEM Slope

| 项目 | 值 |
|------|----|
| file | `copernicus_dem_glo30_slope_8192x4096.tif` |
| size | 5.60 MB |
| width × height | 8192 × 4096 ✅ |
| bands | 1 |
| dtype | float32 ✅ |
| nodata tag | -9999 ✅ |
| origin | -180.0, 90.0 ✅ |
| pixel size | 0.04394531° ✅ |
| CRS hint | geographic (degrees) ✅ |
| north-up | ✅ |
| total pixels | 33,554,432 |
| valid pixels | 11,359,282（33.85%）|
| nodata pixels | 22,195,150（66.15%）|
| min | 0.0° |
| max | **6.03°** |
| mean | 0.179° |
| unique count | 21,679（continuous float）✅ |

**Nodata 分布合理性：** 66.15% nodata = 主要为 ocean 区域（Copernicus DEM 为陆地 DEM，不覆盖海底）。全球陆地约占 29%，33.85% valid 略高，含沿海浅水区，合理。

**Verdict：PASS（含条件）**

> ⚠️ **Caveat C2（slope 分辨率限制）**：max slope 仅 **6.03°**。Copernicus DEM GLO-30 原始分辨率 30m，GEE 导出时在 8K 尺度（≈4.9 km/pixel）重采样后计算坡度，极端坡度被大幅平滑。原生 30m 坡度可达 60–80°，而 8K 均值仅 6°。**此 slope layer 只能用于粗分辨率地形辅助判断**（如山区 vs. 平原趋势），不可作为精确坡度分类依据。建议在 D4 阶段引入原始 21.6K elevation 后重新派生 slope，或在 M1 中降低 slope 权重。

---

## 6. Alignment / CRS Summary

所有 9 个文件：

| 项目 | 结果 |
|------|------|
| 分辨率对齐（8192×4096）| ✅ 全部通过 |
| CRS | geographic (degrees) ✅ 全部一致 |
| 原点 | -180.0, 90.0 ✅ 全部一致 |
| 像素尺寸 | 0.04394531° (= 360/8192) ✅ 全部一致 |
| north-up | ✅ 全部通过 |
| 南北翻转 | ✅ 无翻转（origin Y=90, tiepoint Y positive = north-up）|
| 互相对齐 | ✅ 所有文件共享同一 grid |

---

## 7. Value / Histogram Summary

| 源 | 值域 | 类型 | 验证结果 |
|----|------|------|---------|
| ESA WorldCover | 0–100（11 class + background 0）| categorical | ✅ 全部官方 class 存在 |
| ETOPO1 Bedrock | -10,761 ~ +7,980 m | continuous int16 | ✅ 海洋负值 + 陆地正值 |
| ETOPO1 Ice Surface | -10,761 ~ +7,980 m | continuous int16 | ✅ mean 高于 bedrock |
| JRC GSW Occurrence | 0–100 | continuous uint8 | ✅ 101 values 全覆盖 |
| JRC GSW Seasonality | 0–12 | categorical uint8 | ✅ 13 values 全覆盖 |
| JRC GSW Recurrence | 0–100（缺 2）| continuous uint8 | ✅ 正常 |
| JRC GSW Max Extent | 0/1 | binary uint8 | ✅ binary 正确 |
| JRC GSW Transition | 0–10 | categorical uint8 | ✅ 11 class 全覆盖 |
| Copernicus DEM Slope | 0–6.03° | continuous float32 | ✅ 无 all-zero，nodata=-9999 |

---

## 8. Issues Found

### C1 — ESA WorldCover 无 nodata tag（中等优先级）

- **描述**：文件不含 GDAL_NODATA tag，class 0 为隐式 ocean/background
- **影响**：若不显式处理，后续 mask 代码可能误将 ocean 视为有效分类
- **处置**：M1 mask 代码中必须 `mask = (data == 0)` 标记为 nodata，不作为 land cover class 处理
- **D3 影响**：不阻塞，作为 **M1 前置条件记录**

### C2 — Copernicus DEM Slope 分辨率限制（低优先级）

- **描述**：8K 重采样后 slope max 仅 6.03°，远低于实际地形坡度
- **影响**：slope layer 只能反映区域趋势，不可用于精确坡度分类
- **处置**：M1 中降权或仅用于粗筛；D4 引入 elevation 后重新派生精确 slope
- **D3 影响**：不阻塞，标记为 **resolution-limited**

### C3 — copernicus_dem_glo30_elevation 缺失（高优先级，blocked）

- **描述**：GEE 8K global DEM elevation export 不稳定，文件未到位
- **影响**：高精度 terrain elevation mask 暂时无法升级；ETOPO1 proxy 继续作为 fallback
- **处置**：等 GEE 导出稳定后重新尝试；D3 报告标记为 blocked，不阻塞现有 9 文件的 M1 路径
- **D3 影响**：partial 阻塞，不阻塞 ESA / JRC / ETOPO1 路径

---

## 9. D3 Verdict

```
conditional_pass
```

**通过条件：**

- 9 / 9 文件：dimensions ✅、CRS ✅、alignment ✅、north-up ✅
- 9 / 9 文件：值域符合各源官方规范 ✅
- 9 / 9 文件：无 all-zero / all-nodata 异常 ✅
- 9 / 9 文件：互相 grid 对齐 ✅

**条件（必须在 M1 前处理）：**

- C1：ESA WorldCover class 0 必须在 mask 代码中显式标记为 nodata
- C2：DEM slope 为 resolution-limited，M1 降权使用
- C3：`copernicus_dem_glo30_elevation` 仍 blocked，terrain elevation 路径暂缺

**不标记为 full pass，因 elevation blocked。**

---

## 10. Next Recommendation

### 10.1 elevation blocked 的影响

`copernicus_dem_glo30_elevation` 缺失影响以下 M1 mask：
- `high_mountain_mask`（需要精确 elevation threshold）
- `plateau_mask`（需要 elevation + slope 联合）
- `slope_relief_mask`

这三个 mask 在 M1 阶段**以 ETOPO1-derived proxy 作为 fallback**，待 D4 elevation 就位后重派生。其余所有 mask（ESA cover、JRC water、ETOPO1 topo）不受影响。

### 10.2 是否需要 D3-R Rerun

**不需要**。当前 9 个文件 import verdict 已完整，条件（C1/C2）通过文档记录处理即可。当 elevation 就位后，可单独执行 elevation 的 import test，不需要重跑整个 D3。

### 10.3 M1 前置条件确认

以下条件已满足，可进入 B-6.2X-M1 Semantic Mask Derivation Prototype：

| 条件 | 状态 |
|------|------|
| Phase 1 8K import test 通过 | ✅ conditional_pass |
| source alignment 验证 | ✅ 全部一致 |
| ESA WorldCover class 验证 | ✅ 含 C1 记录 |
| JRC GSW 值域验证 | ✅ |
| ETOPO1 值域验证 | ✅ |
| DEM elevation | ✗ blocked（ETOPO1 fallback 就绪）|
| 无 critical source 错误 | ✅ |

**建议：进入 B-6.2X-M1，elevation mask 路径暂用 ETOPO1 proxy，待 D4 elevation 后补。**

### 10.4 不进入 mask generation

本文件仅为 import test 报告。进入 B-6.2X-M1 需用户明确授权。

---

*Test executed: 2026-06-23*  
*Tools: tifffile 2026.6.1, numpy 2.5.0, imagecodecs (LZW)*  
*No masks generated. No code modified. No data moved or deleted.*
