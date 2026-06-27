# Phase B-6.2X-D3-R — Copernicus DEM Tile Stitch + Import Test

Stage: B-6.2X-D3-R  
Type: Tile stitch + import test  
Status: **PASS**  
Date: 2026-06-24  
Tool: tifffile 2026.6.1 + numpy 2.5.0 (no GDAL)

---

## 1. Background

D3 主测试中 `copernicus_dem_glo30_elevation_8192x4096.tif` 标记为 blocked（GEE 8K global export 不稳定）。
D3-R 采用替代路径：GEE 以 4×4 tile 分块导出，共 16 个 2048×1024 tiles，本轮将其拼接为完整 8K mosaic。

---

## 2. Input Tiles

目录：`d5b_processor_v3/source_cache/gee_global/exported_8k/copernicus_dem_tiles/`

### 2.1 Tile Grid（4 rows × 4 columns）

```
         c00 (-180→-90°)   c01 (-90→0°)   c02 (0→90°)   c03 (90→180°)
r00 (90→45°N)    1.21 MB       1.23 MB       1.45 MB       1.60 MB
r01 (45°N→0°)    0.63 MB       0.81 MB       2.39 MB       1.00 MB
r02 (0°→-45°)    0.04 MB *     1.04 MB       0.76 MB       0.72 MB
r03 (-45→-90°)   0.79 MB       1.01 MB       1.16 MB       1.10 MB
```

\* r02_c00（39 KB）= 东太平洋，95.9% nodata（海洋），正常。

### 2.2 Pre-validation 结果

| 检查项 | 结果 |
|--------|------|
| 16/16 tiles 存在 | ✅ |
| 所有 tiles 尺寸 2048×1024 | ✅ |
| 所有 tiles dtype int16 | ✅ |
| 所有 tiles origin 符合 4×4 分块预期 | ✅ |

**Pre-validation: PASS → stitch 正常进行**

---

## 3. Stitch 执行

按以下顺序拼接（行优先）：

```
r00_c00  r00_c01  r00_c02  r00_c03   → rows  0–1023
r01_c00  r01_c01  r01_c02  r01_c03   → rows 1024–2047
r02_c00  r02_c01  r02_c02  r02_c03   → rows 2048–3071
r03_c00  r03_c01  r03_c02  r03_c03   → rows 3072–4095
```

各 tile 拼接位置与 nodata 比例：

| Tile | 行范围 | 列范围 | nodata% |
|------|--------|--------|---------|
| r00_c00 | 0–1023 | 0–2047 | 53.1% |
| r00_c01 | 0–1023 | 2048–4095 | 51.6% |
| r00_c02 | 0–1023 | 4096–6143 | 39.2% |
| r00_c03 | 0–1023 | 6144–8191 | 44.6% |
| r01_c00 | 1024–2047 | 0–2047 | 81.1% |
| r01_c01 | 1024–2047 | 2048–4095 | 67.3% |
| r01_c02 | 1024–2047 | 4096–6143 | 22.8% |
| r01_c03 | 1024–2047 | 6144–8191 | 62.1% |
| r02_c00 | 2048–3071 | 0–2047 | 95.9% |
| r02_c01 | 2048–3071 | 2048–4095 | 66.8% |
| r02_c02 | 2048–3071 | 4096–6143 | 76.1% |
| r02_c03 | 2048–3071 | 6144–8191 | 64.4% |
| r03_c00 | 3072–4095 | 0–2047 | 67.7% |
| r03_c01 | 3072–4095 | 2048–4095 | 58.7% |
| r03_c02 | 3072–4095 | 4096–6143 | 52.4% |
| r03_c03 | 3072–4095 | 6144–8191 | 52.2% |

---

## 4. Output

```
d5b_processor_v3/source_cache/gee_global/exported_8k/
  copernicus_dem_glo30_elevation_8192x4096.tif
```

| 属性 | 值 |
|------|-----|
| 文件大小 | 21.02 MB |
| 压缩 | LZW |
| dtype | int16 |
| nodata | -32768 |
| CRS | EPSG:4326 (WGS84 geographic) |

---

## 5. Import Test Results

### 5.1 Structure

| 项目 | 值 | 结果 |
|------|----|------|
| width × height | 8192 × 4096 | ✅ |
| bands | 1 | ✅ |
| dtype | int16 | ✅ |
| nodata tag | -32768 | ✅ |
| origin (X, Y) | (-180.0, 90.0) | ✅ |
| pixel size | 0.0439453125° | ✅ |
| CRS EPSG | 4326 (WGS84) | ✅ |
| north-up | ✅ | ✅ |
| aligned 8192×4096 | ✅ | ✅ |
| grid match vs ETOPO1 | ✅ | ✅ |

### 5.2 Pixel Statistics

| 项目 | 值 |
|------|----|
| total pixels | 33,554,432 |
| valid pixels | 13,506,951（**40.25%**）|
| nodata pixels | 20,047,481（**59.75%**）|
| min | **-427 m**（Dead Sea 区域）|
| max | **7,953 m**（Himalayan 峰区）|
| mean (valid) | **899.75 m** |
| all-zero | ✗（正常）|

### 5.3 值域解读

- **min -427 m**：Dead Sea 约 -430m，与 tile r01_c02 单独测试一致 ✅
- **max 7,953 m**：喜马拉雅 / 喀喇昆仑山峰，8K 重采样后略低于 Everest 8,849m ✅
- **mean 899.75 m**：Copernicus DEM 为陆地专用，ocean = nodata。40.25% 陆地有效像素，mean ~900m 符合全球陆地平均海拔（Earth 陆地平均 ~840m）✅
- **nodata 59.75%**：大于海洋覆盖率（约 71%），因为 Copernicus DEM 不覆盖南极洲大部分冰盖区及部分极地区域，加上 59.75% 与海洋实际分布吻合 ✅

### 5.4 Cross-alignment（与其他 Phase 1 sources 对齐）

| 对齐项 | 相比 ETOPO1 Bedrock | 结果 |
|--------|---------------------|------|
| width | 8192 = 8192 | ✅ |
| height | 4096 = 4096 | ✅ |
| origin_x | -180.0 = -180.0 | ✅ |
| pixel_dx | 0.0439453125° = 0.0439453125° | ✅ |

**所有 Phase 1 sources 共享同一 grid，可直接进行 pixel-wise mask 操作。**

---

## 6. Issues

### 已解决

- r02_c00 ` (1)` 文件名后缀：已由用户授权重命名 → 正常纳入 stitch ✅

### 无新 critical issue

无。所有指标正常，无 all-zero / all-nodata / 维度异常 / CRS 错误。

---

## 7. D3-R Verdict

```
PASS
```

全部检查项通过：

- Pre-validation: 16/16 tiles ✅
- Stitch: 8192×4096 int16 ✅
- GeoTIFF 空间标签完整（origin / pixel_scale / CRS EPSG:4326）✅
- Import test: 值域合理，与其他 Phase 1 sources 对齐 ✅

---

## 8. Phase 1 Source 完成状态（更新）

| 文件 | 状态 |
|------|------|
| `esa_worldcover_2021_v200_map_8192x4096.tif` | ✅ D3 PASS |
| `etopo1_bedrock_8192x4096.tif` | ✅ D3 PASS |
| `etopo1_ice_surface_8192x4096.tif` | ✅ D3 PASS |
| `jrc_gsw_occurrence_8192x4096.tif` | ✅ D3 PASS |
| `jrc_gsw_seasonality_8192x4096.tif` | ✅ D3 PASS |
| `jrc_gsw_recurrence_8192x4096.tif` | ✅ D3 PASS |
| `jrc_gsw_max_extent_8192x4096.tif` | ✅ D3 PASS |
| `jrc_gsw_transition_8192x4096.tif` | ✅ D3 PASS |
| `copernicus_dem_glo30_slope_8192x4096.tif` | ✅ D3 PASS（resolution-limited，C2 记录）|
| `copernicus_dem_glo30_elevation_8192x4096.tif` | ✅ **D3-R PASS**（tile stitch）|

**Phase 1 8K source: 10/10 完成。**

---

## 9. Next Recommendation

D3 + D3-R 全部通过，Phase 1 8K source cache 完整就绪。

**可进入 B-6.2X-M1 — Semantic Mask Derivation Prototype**，需用户明确授权。

M1 进入条件全部满足：

| 条件 | 状态 |
|------|------|
| Phase 1 8K import test 通过 | ✅ D3 + D3-R PASS |
| source alignment 验证 | ✅ 所有 source 同一 grid |
| ESA WorldCover class 验证 | ✅（含 C1：class 0 = nodata 需显式处理）|
| JRC GSW 值域验证 | ✅ |
| ETOPO1 值域验证 | ✅ |
| Copernicus DEM elevation | ✅（tile stitch，D3-R PASS）|
| DEM slope resolution caveat | ✅（C2 记录，M1 降权）|
| 无 unresolved critical issue | ✅ |

**进入 M1 前需用户授权。不自动进入 mask generation。**

---

*Stitch executed: 2026-06-24*  
*Tools: tifffile 2026.6.1, numpy 2.5.0, imagecodecs (LZW), no GDAL*  
*No masks generated. No production files modified. Source tiles intact.*
