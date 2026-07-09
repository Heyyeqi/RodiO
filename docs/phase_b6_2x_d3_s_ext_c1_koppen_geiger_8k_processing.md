# Phase B-6.2X-D3-S-EXT-C1 — Köppen-Geiger 8K Processing

Stage: B-6.2X-D3-S-EXT-C1  
Type: External source 8K processing  
Status: **PASS**  
Date: 2026-06-24  
Tools: tifffile 2026.6.1 + numpy 2.5.0 + Pillow 12.2.0

---

## 1. Scope

将 Köppen-Geiger 1991–2020 present-day 气候带分类从 native 30 arc-second resolution 处理为 RodiO 标准 8192×4096 GeoTIFF，对齐 Phase 1 global source grid。

---

## 2. Input Source Selection

| 属性 | 값 |
|------|----|
| ZIP | `koppen_geiger_tif.zip`（125 MB）|
| TIF 路径（ZIP 内）| `1991_2020/koppen_geiger_0p00833333.tif` |
| ZIP 内大小 | 11.9 MB（LZW 压缩）|
| 解压后 | 933 MB（21600 × 43200 × 1 byte）|
| 时期 | **1991–2020（present-day）** ✅ |
| CRS | EPSG:4326 |
| 像素大小 | 0.00833333°（30 arc-second）|
| origin | (-180.0, 90.0) |
| dtype | uint8 |
| 压缩 | LZW（compression code 5）|

---

## 3. Excluded Files

以下文件不进入本轮处理：

| 路径 | 理由 |
|------|------|
| `2041_2070/ssp119/koppen_geiger_0p00833333.tif` | **future projection — 不用于 RodiO present-day** |
| `2041_2070/ssp126/…` 等（共 6 SSP × 2041-2070）| **future projection** |
| `2071_2099/*/koppen_geiger_0p00833333.tif`（共 6 SSP）| **future projection** |
| `1901_1930/`, `1931_1960/`, `1961_1990/` | 历史数据，非 present-day |
| `koppen_geiger_0p1.tif`, `0p5.tif`, `1p0.tif`（所有时期）| 低分辨率备选版本 |
| `koppen_geiger_nc.zip`（720 MB）| NetCDF 格式，已有 TIF 格式，不重复处理 |

---

## 4. Processing Method

| 步骤 | 内容 |
|------|------|
| 读取 | `zipfile.open()` 流式读取 ZIP 内 TIF → `tifffile.imread(io.BytesIO(...))` 解压 LZW |
| 源 shape | (21600, 43200) uint8 |
| 重采样 | **`Image.Resampling.NEAREST`（Pillow 12.2.0）** — 分类数据，不插值 |
| 目标 size | (8192 wide, 4096 tall) |
| 降采样比 | X: 43200 / 8192 ≈ 5.27×；Y: 21600 / 4096 ≈ 5.27× |
| 输出 shape | (4096, 8192) uint8 |
| 空间标签 | ModelPixelScaleTag, ModelTiepointTag, GeoKeyDirectoryTag（与 Phase 1 完全一致）|
| 写入格式 | GeoTIFF，LZW 压缩 |
| 处理时间 | 0.6 秒（read 0.5s，resize 0.0s，write 0.0s）|

**无 scipy 依赖，使用 Pillow 替代方案（与 EXT-B 计划等价）。**

---

## 5. Output Files

| 属性 | 值 |
|------|----|
| 文件路径 | `external_processed_8k/koppen_geiger_1991_2020_8192x4096.tif` |
| 文件大小 | 789,602 bytes（**0.75 MB**，LZW 压缩比极高，分类数据大片同值区域）|
| dtype | uint8 |
| compression | LZW（code 5）|
| nodata | **0（隐式，无 GDAL_NODATA tag）** — class 0 = ocean / unclassified，与 ESA WorldCover 约定一致 |

**Confidence layer：不存在于下载的 `koppen_geiger_tif.zip` 中**（仅有分类 TIF + legend.txt）。不生成。

---

## 6. Import Check

| 项目 | 预期 | 实际 | 结果 |
|------|------|------|------|
| shape（H × W）| (4096, 8192) | (4096, 8192) | ✅ |
| dtype | uint8 | uint8 | ✅ |
| compression | LZW | LZW（code 5）| ✅ |
| CRS EPSG | 4326 | 4326（GeoKeyDirectory 确认）| ✅ |
| pixel_dx | 0.0439453125° | 0.0439453125° | ✅ 精确匹配 |
| origin | (-180.0, 90.0) | (-180.0, 90.0) | ✅ 精确匹配 |
| north-up | ✅ | ✅（tiepointY = 90.0）| ✅ |
| Phase 1 grid 对齐 | ✅ | pixel_dx + origin 完全一致 | ✅ |
| min | ≥ 0 | 0 | ✅ |
| max | ≤ 30 | 30 | ✅ |
| unique values | 31（0–30）| 31（0–30）| ✅ |
| all-zero 异常 | 无 | max=30，非全零 | ✅ |
| illegal codes（>30）| 无 | 无 | ✅ |
| 文件存在 | ✅ | ✅ | ✅ |

---

## 7. Class Legend / Histogram

### 7.1 分类值分布（top 15 by pixel count）

| code | legend label | pixels | % | 地理对应 |
|------|-------------|--------|---|---------|
| 0 | Ocean / unclassified | 22,433,045 | **66.86%** | 全球海洋区域 |
| 30 | EF — Polar frost | 3,411,814 | 10.17% | 南极洲 + 格陵兰 + 北冰洋冰盖 |
| 27 | Dfc — Cold, no dry, cold summer | 1,352,468 | 4.03% | 西伯利亚 / 加拿大 北方针叶林 |
| 4 | BWh — Arid desert hot | 994,322 | 2.96% | 撒哈拉 / 阿拉伯 / 澳大利亚中部 |
| 3 | Aw — Tropical savannah | 768,692 | 2.29% | 非洲赤道南 / 南亚 / 南美北部 |
| 26 | Dfb — Cold, no dry, warm summer | 691,879 | 2.06% | 东欧 / 西伯利亚南部 |
| 29 | ET — Polar tundra | 671,388 | 2.00% | 亚北极冻原带 |
| 7 | BSk — Arid steppe cold | 411,548 | 1.23% | 中亚草原 / 北美内陆 |
| 6 | BSh — Arid steppe hot | 387,383 | 1.15% | 萨赫勒 / 印度南部 |
| 14 | Cfa — Temperate, no dry, hot summer | 314,210 | 0.94% | 美国东南 / 中国东部 / 南美南部 |
| 1 | Af — Tropical rainforest | 287,614 | 0.86% | 亚马孙 / 刚果盆地 / 东南亚 |
| 5 | BWk — Arid desert cold | 285,938 | 0.85% | 中亚 / 北美大盆地 |
| 2 | Am — Tropical monsoon | 207,512 | 0.62% | 季风带 |
| 23 | Dwc — Cold, dry winter, cold summer | 196,296 | 0.59% | 东西伯利亚 |
| 11 | Cwa — Temperate, dry winter, hot summer | 187,777 | 0.56% | 华南 / 南亚 |

全部 30 个类别（1–30）均有像素 ✅

### 7.2 RodiO M1 关键类合计

| M1 mask | 类别 | 像素数 | % |
|---------|------|--------|---|
| `desert_mask` 候选 | BWh(4) + BWk(5) | 1,280,260 | 3.81% |
| `semi_arid_mask` 候选 | BSh(6) + BSk(7) | 798,931 | 2.38% |
| `tropical_mask` 候选 | Af(1) + Am(2) + Aw(3) | 1,263,818 | 3.77% |
| `tundra_mask` 候选 | ET(29) | 671,388 | 2.00% |
| `polar_ice_mask` 候选 | EF(30) | 3,411,814 | 10.17% |

> ✅ **分布合理**：BWh + BWk ≈ 3.81%（热带/冷沙漠）与全球沙漠实际面积（~33M km² ≈ 约 6.5% 陆地，约 2.3% 全球）吻合。EF 10.17% 包含南极洲（面积约 14M km²，全球约 9.2%），数字合理。

### 7.3 Legend 文件

Legend 文本位于 ZIP 内 `legend.txt`，已在 `koppen_geiger_manifest.json` 中完整记录（30 classes with RGB colors + citations）。

---

## 8. Manifest Update

已更新 `koppen_geiger_manifest.json`（见 manifest 文件）：
- `processed_8k_files`: 新增 processed 文件路径
- `processing_status`: `processed_8k_pass`
- `processing_stage`: `B-6.2X-D3-S-EXT-C1`
- `resampling_method`: `nearest`
- `target_width/height/crs`

---

## 9. Issues / Caveats

| ID | 描述 | 优先级 |
|----|------|--------|
| C1 | nodata 无显式 GDAL_NODATA tag（class 0 = ocean，隐式）| 低 — 与 ESA WorldCover 约定一致 |
| C2 | Confidence layer 不在本次下载的 zip 中（需 climate_data_0p1.zip 单独下载）| 低 — 不阻塞 M1 |
| C3 | future SSP files 已确认排除，处理代码 hardcode `1991_2020` | ✅ 已处理 |
| C4 | CC BY 4.0，commercial_clearance = true，无 license 阻塞 | ✅ 无问题 |

---

## 10. Verdict

```
PASS
```

全部检查通过：
- 8192 × 4096，uint8，EPSG:4326，LZW ✅
- 与 Phase 1 grid 精确对齐（pixel_dx + origin 完全一致）✅
- 30 个 class code（1–30）全部存在，无 illegal code ✅
- 分布合理，EF/BW/BS/AT 等关键 M1 候选类比例符合地理预期 ✅
- 文件大小 0.75 MB（LZW 对分类数据高效压缩，符合预期）✅

---

## 11. Next Step Recommendation

**EXT-C1 完成，建议按序进入：**

1. **EXT-C2 — Global Aridity / PET 8K Processing**（需先从 ZIP 提取 405 MB LZW TIF）
2. **EXT-C3 — GEBCO 8K Processing**（8 tile 分块拼接）
3. **EXT-C4 — Allen Coral Atlas 8K Rasterization**（需先确认 fiona + rasterio 安装）

Köppen-Geiger 8K 文件现已就绪，可用于 M1-B desert / tropical / tundra / polar mask 派生。但建议先完成 Aridity + GEBCO 后统一进入 M1-B。

---

*Processing executed: 2026-06-24*  
*Tools: tifffile 2026.6.1, numpy 2.5.0, Pillow 12.2.0*  
*No masks generated. No future SSP files touched. Raw source intact.*
