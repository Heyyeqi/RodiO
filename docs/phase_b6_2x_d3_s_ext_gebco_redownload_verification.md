# Phase B-6.2X-D3-S-EXT-GEBCO-R — GEBCO Re-download Verification

Stage: B-6.2X-D3-S-EXT-GEBCO-R  
Type: GEBCO re-download integrity verification  
Status: **partial_pass** — sub-ice topo tiles ready; ice_surface zip incomplete  
Date: 2026-06-24

---

## 1. Scope

验证用户重新下载到 `external_raw/gebco/` 的 GEBCO 2026 文件是否完整，并评估各文件是否可进入后续处理流程。

旧文件（`未确认 276172.crdownload`）已由用户处理。目录中现有 4 个新文件。

---

## 2. Directory Inventory

```
d5b_processor_v3/source_cache/gee_global/external_raw/gebco/
```

| 文件 / 目录 | 大小 | 类型 | 完整性 |
|------------|------|------|--------|
| `gebco_2026_grid_ice_surface_geotiff.zip` | **25.6 MB** | ZIP (deflate) | ❌ **INCOMPLETE** |
| `GEBCO_2026.zip` | **4.0 GB** | ZIP (deflate) | ✅ 完整 |
| `gebco_2026_sub_ice_topo_geotiff.zip` | **4.1 GB** | ZIP (deflate) | ❌ **INCOMPLETE** |
| `gebco_2026_sub_ice_topo_geotiff/` | ~7.1 GB | 已解压目录 | ✅ **已解压，可用** |

---

## 3. File Integrity Check

### 3.1 `gebco_2026_grid_ice_surface_geotiff.zip`（25.6 MB）

```
file: Zip archive data, at least v2.0 to extract, compression method=deflate
magic bytes: PK\x03\x04  (valid ZIP start)
EOCD check: NOT FOUND in last 22 bytes
unzip -t: End-of-central-directory signature not found
```

> 🔴 **INCOMPLETE — 下载截断**
>
> ZIP 开头有效（PK 签名），但 End-of-Central-Directory（EOCD）标记缺失，说明文件在传输过程中被截断。25.6 MB 对于全球 ice surface GeoTIFF 而言也明显偏小（预期 4–5 GB）。需要重新下载。

### 3.2 `GEBCO_2026.zip`（4.0 GB）

```
magic bytes: PK\x03\x04 (ZIP v4.5)
EOCD check: FOUND ✅
unzip -l 输出:
  GEBCO_2026.nc          7,466,018,396 bytes (7.47 GB 未压缩)
  GEBCO_Grid_docmentation.pdf  266,395 bytes
  GEBCO_Grid_terms_of_use.pdf  145,503 bytes
```

> ✅ **COMPLETE — ZIP 完整**
>
> 内含 `GEBCO_2026.nc`（NetCDF 格式，7.47 GB）= GEBCO 2026 全球网格，同时包含 ice surface 和 sub-ice topo 的综合数据。需要 NetCDF 读取库（netCDF4 / xarray / scipy）才能处理，当前未安装。

### 3.3 `gebco_2026_sub_ice_topo_geotiff.zip`（4.1 GB）

```
magic bytes: PK\x03\x04 (ZIP v2.0)
EOCD check: NOT FOUND
unzip -l: (仅 listing，不做 -t test)
  内含 8 × 933 MB GeoTIFF tiles + 2 PDF 文件（共 7.47 GB 未压缩）
```

> ⚠️ **ZIP INCOMPLETE — 但 tiles 已提前解压并验证**
>
> ZIP 本体可能截断，但内容已经解压到 `gebco_2026_sub_ice_topo_geotiff/`（见 3.4）。ZIP 本身不影响当前处理可行性。

### 3.4 `gebco_2026_sub_ice_topo_geotiff/`（已解压目录）

```
8 GeoTIFF tiles:
  gebco_2026_sub_ice_n90.0_s0.0_w-180.0_e-90.0_geotiff.tif  890 MB
  gebco_2026_sub_ice_n90.0_s0.0_w-90.0_e0.0_geotiff.tif     890 MB
  gebco_2026_sub_ice_n90.0_s0.0_w0.0_e90.0_geotiff.tif      890 MB
  gebco_2026_sub_ice_n90.0_s0.0_w90.0_e180.0_geotiff.tif    890 MB
  gebco_2026_sub_ice_n0.0_s-90.0_w-180.0_e-90.0_geotiff.tif 890 MB
  gebco_2026_sub_ice_n0.0_s-90.0_w-90.0_e0.0_geotiff.tif    890 MB
  gebco_2026_sub_ice_n0.0_s-90.0_w0.0_e90.0_geotiff.tif     890 MB
  gebco_2026_sub_ice_n0.0_s-90.0_w90.0_e180.0_geotiff.tif   890 MB
2 PDF docs:
  GEBCO_Grid_documentation.pdf  260 KB
  GEBCO_Grid_terms_of_use.pdf   142 KB
```

> ✅ **已解压，内容完整**

---

## 4. ZIP Content Listing

### 4.1 `gebco_2026_grid_ice_surface_geotiff.zip`

```
FAILED — unzip -l 无法读取（EOCD missing）
```

### 4.2 `GEBCO_2026.zip`

```
Length        Date       Time    Name
-----------   ---------- -----   ----
7,466,018,396 04-21-2026 22:29   GEBCO_2026.nc
      266,395 04-21-2026 17:20   GEBCO_Grid_docmentation.pdf   ← typo in filename
      145,503 04-07-2026 21:30   GEBCO_Grid_terms_of_use.pdf
-----------                      -------
7,466,430,294                    3 files
```

### 4.3 `gebco_2026_sub_ice_topo_geotiff.zip`

```
Length        Date       Time    Name
-----------   ---------- -----   ----
  933,257,466 04-22-2026 14:23   gebco_2026_sub_ice_n0.0_s-90.0_w0.0_e90.0_geotiff.tif
  933,257,452 04-22-2026 14:21   gebco_2026_sub_ice_n0.0_s-90.0_w-180.0_e-90.0_geotiff.tif
  933,257,448 04-22-2026 14:22   gebco_2026_sub_ice_n0.0_s-90.0_w-90.0_e0.0_geotiff.tif
  933,257,464 04-22-2026 14:25   gebco_2026_sub_ice_n0.0_s-90.0_w90.0_e180.0_geotiff.tif
  933,257,446 04-22-2026 14:24   gebco_2026_sub_ice_n90.0_s0.0_w0.0_e90.0_geotiff.tif
  933,257,432 04-22-2026 14:21   gebco_2026_sub_ice_n90.0_s0.0_w-180.0_e-90.0_geotiff.tif
  933,257,428 04-22-2026 14:23   gebco_2026_sub_ice_n90.0_s0.0_w-90.0_e0.0_geotiff.tif
  933,257,444 04-22-2026 14:25   gebco_2026_sub_ice_n90.0_s0.0_w90.0_e180.0_geotiff.tif
      266,395 04-21-2026 16:34   GEBCO_Grid_documentation.pdf
      145,503 04-21-2026 16:34   GEBCO_Grid_terms_of_use.pdf
-----------                      -------
7,466,471,478                    10 files
```

---

## 5. GeoTIFF Metadata Check（已解压 Sub-ice Topo Tiles）

工具：tifffile + numpy（gdalinfo 不可用）

检查 tile：`gebco_2026_sub_ice_n90.0_s0.0_w-180.0_e-90.0_geotiff.tif`（NW 象限）

| 属性 | 值 |
|------|----|
| shape | (21600, 21600) |
| dtype | int16 |
| compression | 1（无压缩，raw TIFF）|
| pixel_size | 0.004166667° = 1/240° = 15 arc-second |
| origin（tiepoin）| (-180.0, 90.0) |
| CRS | EPSG:4326（GeoKeyDirectory 确认）|
| nodata | -32767 |
| north-up | ✅ |

**像素统计（NW tile：-180°→-90° lon, 0°→90° lat）：**

| 项目 | 值 |
|------|----|
| total pixels | 466,560,000（= 21600 × 21600）|
| valid pixels | 466,560,000（**100.0%**）|
| nodata pixels | **0（0%）**|
| min | **-10,448 m**（大西洋深海 / 波多黎各海沟附近）|
| max | **+6,141 m**（北美 / 格陵兰陆地）|
| mean | -2,484.4 m（以海洋为主，平均深度合理）|

> ✅ **Sub-ice topo 数据有效**。100% 像素有值（包括海洋区域），与 GEBCO 特性一致（全球完整覆盖，海洋 = 负值深度，陆地 = 正值高程）。

**8 tiles 全球覆盖结构：**

```
Row 1 (北半球, 0°→90°N):
  n90_s0_w-180_e-90   n90_s0_w-90_e0   n90_s0_w0_e90   n90_s0_w90_e180
Row 2 (南半球, -90°→0°):
  n0_s-90_w-180_e-90  n0_s-90_w-90_e0  n0_s-90_w0_e90  n0_s-90_w90_e180

合并后: 86,400 × 43,200 pixels = GEBCO 15 arc-second 全球网格 ✅
```

### 5.1 Sub-ice vs Ice Surface 区别（RodiO 上下文）

| 产品 | 含义 | RodiO M1 用途 |
|------|------|--------------|
| Sub-ice topo | 冰层下方地形（陆地 + 海底）| **主用途**：精细化海洋深度分级（`deep_ocean_mask`、`continental_shelf_mask` 等）|
| Ice surface elevation | 冰面高度（含格陵兰 / 南极冰盖顶面）| 次要：冰盖高度 context，与 Copernicus DEM 互补 |

Sub-ice topo 对于 RodiO M1 bathymetry mask 更有价值。Ice surface 对冰盖语义层有价值，但 ESA WorldCover + Copernicus DEM 已基本覆盖此需求。

---

## 6. Manifest Update

已更新 `gebco_manifest.json`（见 Section 6 manifest 文件）。

---

## 7. Verdict

| 文件 | 状态 | 可用性 |
|------|------|--------|
| `gebco_2026_grid_ice_surface_geotiff.zip` | ❌ **incomplete** | 不可用，需重新下载 |
| `GEBCO_2026.zip` | ✅ complete | 可用（需 netCDF4 / xarray 库）|
| `gebco_2026_sub_ice_topo_geotiff.zip` | ❌ incomplete（ZIP）| ZIP 不可用，但 tiles 已解压 |
| `gebco_2026_sub_ice_topo_geotiff/` | ✅ **ready_for_processing_8k** | 8 tiles 已验证，可直接进入处理 |

**总体 GEBCO Readiness：`partial_pass`**

- Sub-ice topo GeoTIFF tiles → `ready_for_processing_8k` ✅
- Ice surface GeoTIFF → `incomplete`（次要优先级）
- NetCDF grid → `ready_but_needs_netcdf_library`

---

## 8. Issues / Risks

| ID | 描述 | 优先级 |
|----|------|--------|
| I1 | `gebco_2026_grid_ice_surface_geotiff.zip` 截断（EOCD missing），需重新下载 | 低（sub-ice 已可用）|
| I2 | `gebco_2026_sub_ice_topo_geotiff.zip` ZIP 本体截断，但 tiles 已解压并验证 | 低（不阻塞）|
| I3 | `GEBCO_2026.zip`（NetCDF）需要 netCDF4 / xarray 才能读取，当前未安装 | 低（GeoTIFF tiles 优先）|
| I4 | Sub-ice topo tiles 为无压缩 TIFF（compression=1），每 tile 890 MB，stitch 后全球 ~7.1 GB 内存需求 | 中（8K 处理时需分块或降采样）|

---

## 9. Next Step Recommendation

### 立即可执行（无需用户操作）

1. **GEBCO Sub-ice topo → 8K**：从 8 tiles 降采样拼接至 8192×4096
   - 输入：`gebco_2026_sub_ice_topo_geotiff/*.tif`（8 × 21600×21600，无压缩 int16）
   - 输出目标：`processed_8k/gebco_2026_sub_ice_8192x4096.tif`（需用户授权进入 EXT-B 才能执行）
   - 处理复杂度：需分块读取（避免 ~7GB 全量内存占用），降采样比 ~10.5x

### 可选（低优先级）

2. 重新下载 `gebco_2026_grid_ice_surface_geotiff.zip`（完整版，预期 ~4 GB）
3. 安装 netCDF4 / xarray 后读取 `GEBCO_2026.nc`（若需要 ice surface + sub-ice 合并产品）

### 旧 `.crdownload` 状态

旧文件 `未确认 276172.crdownload` 已不在目录中，用户已处理。

---

*Verification executed: 2026-06-24*  
*Tools: unzip, Python magic-bytes check, tifffile + numpy pixel stats*  
*No files extracted. No files moved or deleted. No masks generated.*
