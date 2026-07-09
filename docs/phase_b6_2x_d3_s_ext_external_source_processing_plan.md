# Phase B-6.2X-D3-S-EXT-B — External Source Processing Plan

Stage: B-6.2X-D3-S-EXT-B  
Type: External source processing plan  
Status: **Planning only — no processing executed**  
Date: 2026-06-24

---

## 1. Scope

为 4 个通过 EXT-A 审查的外部数据源制定从 raw 到 8192×4096 GeoTIFF 的处理计划。本文件只规划，不执行任何处理。

**目标网格（Phase 1 对齐基准）：**

| 属性 | 值 |
|------|----|
| width × height | 8192 × 4096 |
| CRS | EPSG:4326（WGS84）|
| origin（upper-left corner）| (-180.0, 90.0) |
| pixel size | 0.0439453125°（= 360/8192° = 158.2 arcsec ≈ 4.9 km at equator）|
| extent | -180° to 180° lon, -90° to 90° lat |
| axis | north-up |

**输出目录：**

```
d5b_processor_v3/source_cache/gee_global/external_processed_8k/
```

（目录已存在，当前为空。）

---

## 2. Input Readiness Summary

| 源 | Raw Verdict | Primary Input | 处理复杂度 |
|----|-------------|---------------|-----------|
| Global Aridity / PET | `ready_but_license_restricted` | `Global-AI_ET0__annual_v3_1.zip` (616 MB) | 中：从 ZIP 流式读取 405 MB LZW TIFF + 南极覆盖缺口处理 |
| Köppen-Geiger | `ready_for_processing_8k` | `koppen_geiger_tif.zip/1991_2020/koppen_geiger_0p00833333.tif` (12.5 MB in zip) | 低：小文件，直接从 ZIP 读取 |
| GEBCO | `ready_for_processing_8k`（extracted tiles）| `gebco_2026_sub_ice_topo_geotiff/`（8 × 890 MB tiles）| 高：分块读取 8 个大 tile，非整数降采样比 |
| Allen Coral Atlas | `ready_for_processing_8k` | 30 ZIP files（`*.gpkg` vector）| 高：需 rasterize，每个区域单独处理，合并 |

---

## 3. Global Aridity / PET Processing Plan

### 3.1 输入文件

| 文件 | 用途 | 压缩后大小 | 解压后大小 |
|------|------|-----------|-----------|
| `Global-AI_ET0__annual_v3_1.zip` → `ai_v31_yr.tif` | Annual Aridity Index | 405 MB（LZW TIFF）| ~1.5 GB（uint16，43200×18000）|
| `Global-AI_ET0__annual_v3_1.zip` → `et0_v31_yr.tif` | Annual ET0（PET）| 211 MB（LZW）| ~777 MB |

### 3.2 Native Resolution

| 属性 | 값 |
|------|----|
| pixel size | 0.0083333°（30 arcsec）|
| width | 43,200 |
| height | 18,000（仅覆盖 -60° 到 90°）|
| coverage | **-180° to 180°, -60° to 90°**（不含南极洲）|

### 3.3 降采样参数

| 计算 | 値 |
|------|----|
| 目标 pixel size | 158.2 arcsec |
| 降采样比（X/Y）| 158.2 / 30 ≈ **5.27x** |
| 目标尺寸（有数据区）| 8192 × 3413（对应 -60° to 90°，= 150°/180° × 4096 ≈ 3413 行）|
| 无数据区（Antarctic 缺口）| 最后 **683 行**（对应 -90° to -60°，约 30°/180° × 4096 ≈ 683 行）|

> ℹ️ 说明：原来估算 1365 行有误。重新计算：
> 南极缺口 = -90 到 -60° = 30°。在 4096 行中占 30/180 × 4096 ≈ 683 行（不是 1365 行）。
> 即 8K grid 的最后 683 行（行号 3413–4095）无 aridity 数据。

### 3.4 重采样方式

| 层 | 数据类型 | 重采样方式 | 理由 |
|----|---------|-----------|------|
| Aridity Index (ai) | uint16（连续值，AI × 10000）| **average（均值）** | 连续数据，降采样取均值更准确 |
| ET0 annual | uint16（连续值，mm × 10）| **average（均值）** | 同上 |

### 3.5 输出规格

| 属性 | ai_v31_yr | et0_v31_yr |
|------|-----------|------------|
| output filename | `global_aridity_index_8192x4096.tif` | `global_pet_annual_8192x4096.tif` |
| output path | `external_processed_8k/` | `external_processed_8k/` |
| dtype | uint16 | uint16 |
| nodata | **0**（Antarctic 缺口和无数据区）| **0** |
| compression | LZW | LZW |
| CRS | EPSG:4326 | EPSG:4326 |
| origin | (-180.0, 90.0) | (-180.0, 90.0) |
| spatial tags | ModelPixelScaleTag + ModelTiepointTag + GeoKeyDirectoryTag | 同上 |

> ⚠️ **值域说明（使用时注意）：**
> - `ai_v31_yr`：uint16，AI = value / 10000（典型范围：0–65535，对应 AI 0.0 to 6.5+）
>   - Hyperarid: AI < 500（AI < 0.05）
>   - Arid: AI 500–2000（AI 0.05–0.2）
>   - Semi-arid: AI 2000–5000（AI 0.2–0.5）
>   - Dry sub-humid: AI 5000–6500
>   - Humid: AI > 6500
> - nodata = 0 在技术上与 hyperarid 极端干旱值重叠 → M1 使用时需用 ESA / JRC mask 区分 ocean nodata vs dry land

### 3.6 处理伪代码

```python
import zipfile, tifffile, numpy as np

ZIP_AI = "external_raw/global_aridity_pet/Global-AI_ET0__annual_v3_1.zip"
TIF_IN = "Global-AI_ET0__annual_v3_1/ai_v31_yr.tif"
OUT = "external_processed_8k/global_aridity_index_8192x4096.tif"

# Step 1: Extract to temp, read
with zipfile.ZipFile(ZIP_AI) as z:
    z.extract(TIF_IN, path="/tmp/rodio_ext/")

src = tifffile.imread(f"/tmp/rodio_ext/{TIF_IN}")  # (18000, 43200) uint16

# Step 2: Resize (18000→3413, 43200→8192) via scipy or PIL
from scipy.ndimage import zoom
out_3413 = zoom(src.astype(np.float32), (3413/18000, 8192/43200), order=1)
out_3413 = np.round(out_3413).astype(np.uint16)

# Step 3: Place in full 8192×4096 grid, Antarctic rows → 0 (nodata)
output = np.zeros((4096, 8192), dtype=np.uint16)
output[0:3413, :] = out_3413  # rows 0-3412 = 90° to -60°
# rows 3413-4095 remain 0 = nodata (Antarctic gap)

# Step 4: Write GeoTIFF with spatial tags
# (same extratags pattern as Phase 1 GEE imports)
tifffile.imwrite(OUT, output, compression='lzw', extratags=[...])

# Cleanup temp
import shutil; shutil.rmtree("/tmp/rodio_ext/")
```

### 3.7 License Flag

> ⚠️ **research_only = true**。output file 需在文件名或 manifest 中标注 license 限制，防止误入商业发布流程。

---

## 4. Köppen-Geiger Processing Plan

### 4.1 输入文件

```
koppen_geiger_tif.zip → 1991_2020/koppen_geiger_0p00833333.tif
                          (uncompressed size in zip: 12,494,241 bytes ≈ 12.5 MB)
```

> ✅ 12.5 MB 可直接从 ZIP 流式读取（zipfile.open → tifffile.imread），无需全量解压。

**明确排除（不进入处理）：**
- `2041_2070/*/koppen_geiger_*.tif` — future SSP projections
- `2071_2099/*/koppen_geiger_*.tif` — future SSP projections
- `1901_1930/`, `1931_1960/`, `1961_1990/` — historical（非 present-day）

### 4.2 Native Resolution

| 属性 | 值 |
|------|----|
| pixel size | 0.0083333°（30 arcsec）|
| width × height | 43,200 × 21,600 |
| coverage | global（-180° to 180°, -90° to 90°）|
| dtype | uint8（class values 1–30）|
| nodata | 0（海洋 / 背景）|

### 4.3 降采样参数

| 计算 | 值 |
|------|----|
| 降采样比 | 158.2 / 30 ≈ **5.27x** |
| 目标尺寸 | 8192 × 4096（覆盖全球，无缺口）|
| 重采样方式 | **nearest-neighbor（order=0）** — 分类数据，不可插值 |

### 4.4 输出规格

| 属性 | 值 |
|------|-----|
| filename | `koppen_geiger_1991_2020_8192x4096.tif` |
| path | `external_processed_8k/` |
| dtype | uint8 |
| nodata | 0（海洋）|
| class range | 1–30（legend.txt 已读取并记录在 manifest）|
| compression | LZW |
| CRS | EPSG:4326 |
| origin | (-180.0, 90.0) |

### 4.5 Confidence Layer

本次下载的 `koppen_geiger_tif.zip` 不含 confidence 层（仅有 `koppen_geiger_*.tif` 分类图）。若需 confidence，需单独下载 `climate_data_0p1.zip` / `climate_data_0p5.zip`。当前 EXT-B 阶段暂不处理 confidence 层。

`koppen_geiger_1991_2020_confidence_8192x4096.tif` → **deferred（未下载数据）**

### 4.6 处理伪代码

```python
import zipfile, io, tifffile, numpy as np
from scipy.ndimage import zoom

ZIP = "external_raw/koppen_geiger/koppen_geiger_tif.zip"
TIF = "1991_2020/koppen_geiger_0p00833333.tif"
OUT = "external_processed_8k/koppen_geiger_1991_2020_8192x4096.tif"

# Stream from ZIP (12.5 MB — safe to read in memory)
with zipfile.ZipFile(ZIP) as z:
    with z.open(TIF) as f:
        src = tifffile.imread(io.BytesIO(f.read()))  # (21600, 43200) uint8

# Nearest-neighbor downsample
out = zoom(src.astype(np.float32), (4096/21600, 8192/43200), order=0)
out = out.astype(np.uint8)

# Write GeoTIFF
tifffile.imwrite(OUT, out, compression='lzw', extratags=[...])
```

---

## 5. GEBCO Processing Plan

### 5.1 主输入源

```
d5b_processor_v3/source_cache/gee_global/external_raw/gebco/
  gebco_2026_sub_ice_topo_geotiff/    ← 唯一有效输入
    gebco_2026_sub_ice_n90.0_s0.0_w-180.0_e-90.0_geotiff.tif  (890 MB)
    gebco_2026_sub_ice_n90.0_s0.0_w-90.0_e0.0_geotiff.tif     (890 MB)
    gebco_2026_sub_ice_n90.0_s0.0_w0.0_e90.0_geotiff.tif      (890 MB)
    gebco_2026_sub_ice_n90.0_s0.0_w90.0_e180.0_geotiff.tif    (890 MB)
    gebco_2026_sub_ice_n0.0_s-90.0_w-180.0_e-90.0_geotiff.tif (890 MB)
    gebco_2026_sub_ice_n0.0_s-90.0_w-90.0_e0.0_geotiff.tif    (890 MB)
    gebco_2026_sub_ice_n0.0_s-90.0_w0.0_e90.0_geotiff.tif     (890 MB)
    gebco_2026_sub_ice_n0.0_s-90.0_w90.0_e180.0_geotiff.tif   (890 MB)
```

**明确排除（当前不进入处理）：**
- `gebco_2026_grid_ice_surface_geotiff.zip` — ZIP 截断，incomplete
- `gebco_2026_sub_ice_topo_geotiff.zip` — ZIP 截断（但 tiles 已解压）
- `GEBCO_2026.zip` — ZIP 完整但为 NetCDF，需 netCDF4/xarray；当前 GeoTIFF tiles 优先

### 5.2 Tile Grid 结构

```
Tile 排列（4列 × 2行）：

Row 0 (北半球, lat 0°→90°N):
  col 0: n90_s0_w-180_e-90    col 1: n90_s0_w-90_e0
  col 2: n90_s0_w0_e90        col 3: n90_s0_w90_e180

Row 1 (南半球, lat -90°→0°):
  col 0: n0_s-90_w-180_e-90   col 1: n0_s-90_w-90_e0
  col 2: n0_s-90_w0_e90       col 3: n0_s-90_w90_e180
```

### 5.3 Native Resolution

| 속성 | 값 |
|------|----|
| pixel size | 0.004166667°（15 arcsec）|
| 每 tile | 21,600 × 21,600 |
| 全局合并 | 86,400 × 43,200 |
| dtype | int16 |
| nodata | -32767 |
| compression | 无压缩（raw TIFF）|

### 5.4 降采样参数

| 计算 | 값 |
|------|----|
| 降采样比 | 158.2 / 15 ≈ **10.55x** |
| 每 tile 输出大小 | 21600 × (2048/21600) ≈ 2048 × 2048 pixels |
| 非整数 scale factor | 2048 / 21600 = **0.094815**（scipy zoom 可处理）|
| 全局合并 | 4 × 2048 = 8192 wide，2 × 2048 = 4096 tall ✅ |
| 重采样方式 | **average（order=1 bilinear）** — 连续高程 / 深度值 |

> ℹ️ 每 tile 读取时峰值内存：21600 × 21600 × 2 bytes ≈ **889 MB**（无压缩 TIFF，直接加载）。处理器和内存允许的情况下单次加载一个 tile，处理后释放。不要同时加载多个 tile。

### 5.5 陆地 / 海洋边界处理策略

| 策略 | 说明 |
|------|------|
| 保留正值（陆地）| bathymetry 输出层保留全值（海洋负值 + 陆地正值），不 mask |
| M1 使用时过滤 | 在 mask 派生脚本中，使用 ESA class 0 / JRC max_extent 区分海洋区域，然后应用深度阈值 |
| 与 ETOPO1 关系 | GEBCO 15 arcsec > ETOPO1 ~1 arcmin；用 GEBCO 替代 ETOPO1 作为首选 bathymetry 层。ETOPO1 仍可用于 cross-check |
| 与 Copernicus / MERIT 关系 | 陆地高程以 Copernicus / MERIT 为准（更精细陆地 DEM）；GEBCO 正值区域 M1 不依赖 |
| nodata | -32767（沿用源 nodata；实际上 GEBCO 全球无 nodata，但保持兼容）|

### 5.6 输出规格

| 属性 | 値 |
|------|----|
| filename | `gebco_2026_sub_ice_bathymetry_8192x4096.tif` |
| path | `external_processed_8k/` |
| dtype | int16 |
| nodata | -32767 |
| compression | LZW |
| CRS | EPSG:4326 |
| origin | (-180.0, 90.0) |
| value meaning | negative = ocean/lake depth（m below sea level），positive = land elevation（m above）|

### 5.7 处理伪代码（分块，避免全量内存）

```python
import tifffile, numpy as np
from scipy.ndimage import zoom

BASE = "external_raw/gebco/gebco_2026_sub_ice_topo_geotiff/"
OUT  = "external_processed_8k/gebco_2026_sub_ice_bathymetry_8192x4096.tif"

SCALE = 2048 / 21600  # per-tile scale factor

# Tile order: (filename_suffix, output_row, output_col)
TILES = [
    ("n90.0_s0.0_w-180.0_e-90.0", 0, 0),
    ("n90.0_s0.0_w-90.0_e0.0",    0, 1),
    ("n90.0_s0.0_w0.0_e90.0",     0, 2),
    ("n90.0_s0.0_w90.0_e180.0",   0, 3),
    ("n0.0_s-90.0_w-180.0_e-90.0",1, 0),
    ("n0.0_s-90.0_w-90.0_e0.0",   1, 1),
    ("n0.0_s-90.0_w0.0_e90.0",    1, 2),
    ("n0.0_s-90.0_w90.0_e180.0",  1, 3),
]

mosaic = np.full((4096, 8192), -32767, dtype=np.int16)

for suffix, orow, ocol in TILES:
    path = f"{BASE}gebco_2026_sub_ice_{suffix}_geotiff.tif"
    tile = tifffile.imread(path)              # (21600, 21600) int16, ~889 MB
    block = zoom(tile.astype(np.float32), SCALE, order=1)
    block = np.round(block).clip(-32767, 32767).astype(np.int16)
    mosaic[orow*2048:(orow+1)*2048, ocol*2048:(ocol+1)*2048] = block
    del tile, block  # 释放内存

tifffile.imwrite(OUT, mosaic, compression='lzw', extratags=[...])
```

---

## 6. Allen Coral Atlas Processing Plan

### 6.1 输入

```
external_raw/allen_coral_atlas/
  {29 regional ZIPs}/*.zip → 内含 Reef-Extent/reefextent.gpkg（主要层）
                              Geomorphic-Map/geomorphic.gpkg（次要层）
                              Benthic-Map/benthic.gpkg（可选层）
```

### 6.2 格式说明

- 所有数据为 **GeoPackage vector**（.gpkg = SQLite），非 raster
- 需要 rasterize（向量 → 栅格）才能生成 8K GeoTIFF
- 每个 ZIP 对应一个地理区域，需逐个处理后 merge

### 6.3 层级优先级与文件大小

| 层 | 文件 | 优先级 | Bermuda 大小 | Caribbean 大小 |
|----|------|--------|-------------|----------------|
| Reef Extent | `reefextent.gpkg` | ✅ 最高 | 0.6 MB | 35.9 MB |
| Geomorphic | `geomorphic.gpkg` | 🔵 中 | 14.4 MB | 2849 MB |
| Benthic | `benthic.gpkg` | 🟡 低 | 48.9 MB | 8385 MB |

> ⚠️ **Caribbean benthic.gpkg = 8.4 GB（解压后）**。提取和读取代价极高，对 8K raster 而言提供的细节会因大幅降采样而丢失。**建议 EXT-B 阶段优先处理 reef extent（reefextent.gpkg），geomorphic 作为次要，benthic 暂 deferred。**

### 6.4 Rasterize 策略

```
输出 raster 分辨率: 8192 × 4096
每像素 = 0.0439453125° ≈ 4.9 km at equator
珊瑚礁典型宽度: 10–100m to few km

→ 8K raster 只能表达礁体"存在/不存在"，无法表达礁体形态细节
→ 使用 burn value approach（1 = reef pixel, 0 = no reef）
→ 若礁体多边形与像素有任何重叠 → burn 1（all_touched=True）
```

### 6.5 处理流程（per region）

```python
# Requires: fiona, rasterio, rasterio.features
import zipfile, fiona, tempfile, numpy as np, rasterio
from rasterio.features import rasterize
from rasterio.transform import from_bounds

TARGET_TRANSFORM = from_bounds(-180, -90, 180, 90, 8192, 4096)
TARGET_SHAPE = (4096, 8192)

global_reef = np.zeros(TARGET_SHAPE, dtype=np.uint8)

for zip_path in sorted(regional_zips):
    with zipfile.ZipFile(zip_path) as z:
        # Extract only reefextent.gpkg to temp
        z.extract("Reef-Extent/reefextent.gpkg", path="/tmp/aca_tmp/")
    
    gpkg = "/tmp/aca_tmp/Reef-Extent/reefextent.gpkg"
    with fiona.open(gpkg) as src:
        shapes = [(geom, 1) for feat in src
                  for geom in [feat['geometry']] if geom is not None]
    
    burned = rasterize(
        shapes=shapes,
        out_shape=TARGET_SHAPE,
        transform=TARGET_TRANSFORM,
        fill=0,
        dtype=np.uint8,
        all_touched=True,   # include partial overlaps
    )
    global_reef = np.maximum(global_reef, burned)

# Write final output
tifffile.imwrite("external_processed_8k/allen_coral_atlas_reef_extent_8192x4096.tif",
                 global_reef, compression='lzw', extratags=[...])
```

### 6.6 输出规格

| 属性 | reef_extent | geomorphic（次要）| benthic（可选）|
|------|-------------|------------------|----------------|
| filename | `allen_coral_atlas_reef_extent_8192x4096.tif` | `allen_coral_atlas_geomorphic_8192x4096.tif` | `allen_coral_atlas_benthic_8192x4096.tif` |
| path | `external_processed_8k/` | `external_processed_8k/` | `external_processed_8k/` |
| dtype | uint8 | uint8 | uint8 |
| values | 0=no reef, 1=reef present | 0=no data, 1–N=class code | 0=no data, 1–N=class code |
| nodata | 0 | 0 | 0 |
| compression | LZW | LZW | LZW |
| processing status | 计划执行 | 计划执行（若 geomorphic 大小允许）| **deferred**（benthic gpkg 过大）|

---

## 7. Processing Order

**推荐执行顺序：**

| 顺序 | 源 | 原因 |
|------|----|----- |
| 1 | **Köppen-Geiger** | 最简单，12.5 MB 文件，直接从 ZIP 读，nearest-neighbor，无 license 限制，立即可执行 |
| 2 | **Global Aridity / PET** | 连续数据，需处理 405 MB LZW 提取，南极缺口填充；稍复杂，但逻辑清晰 |
| 3 | **GEBCO sub-ice topo** | 8 × 890 MB tiles，内存密集，需逐 tile 处理；正确后立即可用于 bathymetry mask |
| 4 | **Allen Coral Atlas** | 需 fiona + rasterio（可能需先安装），29 个 ZIP 逐个处理，时间长；reef/atoll mask 是 M1 enhancement，不阻塞 M1-B core |

**说明：**
- Köppen 先做：CC BY 4.0，复杂度最低，可建立 external_processed_8k 基础验证流程
- Aridity 第二：license 受限但 research 阶段允许，完成后即可派生 desert/arid zone mask
- GEBCO 第三：计算密集，但处理逻辑（tile 拼接 + 降采样）与 D3-R Copernicus stitch 思路相同，有经验
- ACA 最后：依赖 rasterio/fiona 安装，reef mask 不阻塞 core M1-B 执行

---

## 8. Tooling Requirements

### 8.1 当前可用

| 工具 | 状态 | 用途 |
|------|------|------|
| Python 3.x | ✅ 可用 | 全部 |
| tifffile | ✅ 可用 | GeoTIFF 读写（Phase 1 已验证）|
| numpy | ✅ 可用 | 数组操作 |
| imagecodecs | ✅ 可用 | LZW 解压（Phase 1 已验证）|
| scipy.ndimage.zoom | ✅ 可用（scipy 通常已安装）| 非整数比降采样 |
| zipfile（stdlib）| ✅ 可用 | ZIP 流式读取 |

### 8.2 需要安装（ACA rasterize 专用）

| 工具 | 安装命令 | 用途 |
|------|---------|------|
| fiona | `pip install fiona --break-system-packages` | 读取 .gpkg vector 文件 |
| rasterio | `pip install rasterio --break-system-packages` | rasterize vector → raster |

> ⚠️ fiona 和 rasterio 都依赖 GDAL C 库（libgdal）。在无 GDAL 的系统上 pip 安装可能失败。
>
> **Fallback（如 rasterio/fiona 安装失败）：**
> - 安装 gdal 命令行工具：`brew install gdal`（macOS）
> - 用 `gdal_rasterize` 直接处理每个 .gpkg
> - 或将 ACA 标记为 deferred，优先 core M1-B（reef mask 不是 M1 blockers）

### 8.3 NetCDF 工具（GEBCO_2026.nc 备用路径）

| 工具 | 安装命令 | 用途 |
|------|---------|------|
| netCDF4 | `pip install netCDF4 --break-system-packages` | 读取 .nc 文件 |
| xarray | `pip install xarray --break-system-packages` | 高层 nc 读取 API |

当前 GeoTIFF tile 路径优先，netCDF 工具暂不需要。

### 8.4 验证 scipy 可用性

在执行任何处理前，先运行：

```python
from scipy.ndimage import zoom
import numpy as np
test = zoom(np.ones((100,100)), 0.5, order=0)
assert test.shape == (50, 50), "scipy.ndimage.zoom OK"
```

---

## 9. Output Directory Policy

| 位置 | 用途 | 当前处于本阶段 |
|------|------|--------------|
| `external_raw/` | 原始下载数据，**不修改** | 只读 |
| `external_processed_8k/` | EXT-B 输出的 8K GeoTIFF | **写入目标** |
| `exported_8k/` | Phase 1 GEE 导出，**不写入** | 只读 |
| `supplemental_8k/` | Phase 1 supplemental GEE，**不写入** | 只读 |
| `pwa/` / `production/` / `candidates/` | 生产文件，**绝对禁止** | 不接触 |

`source_cache/` 整体不进入 git（`.git/info/exclude` 已配置）。

---

## 10. Import Test Plan After Processing

处理完成后执行 **B-6.2X-D3-S-EXT-C — External Processed 8K Import Test**：

```
external_processed_8k/
  global_aridity_index_8192x4096.tif
  global_pet_annual_8192x4096.tif
  koppen_geiger_1991_2020_8192x4096.tif
  gebco_2026_sub_ice_bathymetry_8192x4096.tif
  allen_coral_atlas_reef_extent_8192x4096.tif      （若 ACA 已完成）
  allen_coral_atlas_geomorphic_8192x4096.tif        （若 ACA geomorphic 已完成）
```

每个文件检查项：

| 检查项 | 预期值 |
|--------|--------|
| dimensions | 8192 × 4096 |
| CRS | EPSG:4326 |
| dtype | 各文件见 Section 3–6 |
| origin | (-180.0, 90.0) |
| pixel_size | 0.0439453125° |
| nodata | 各文件见 Section 3–6 |
| value range | 合理（见各源说明）|
| class histogram | Köppen 类需 1–30，无 31+ 异常值 |
| alignment | 与 Phase 1 grid 完全对齐（同 origin + pixel size）|
| north-up | ✅ |

---

## 11. Risks / Caveats

| ID | 类型 | 说明 |
|----|------|------|
| R1 | License | **Global Aridity / PET = research_only**，output 文件需标记 license 限制，禁止进入商业发布 |
| R2 | Data scope | **Köppen future SSP files (2041-2099) 绝对不用于 present-day RodiO** — 处理代码必须 hardcode `1991_2020` 路径 |
| R3 | GEBCO status | `gebco_2026_grid_ice_surface_geotiff.zip` 截断，不用。`gebco_2026_sub_ice_topo_geotiff.zip` ZIP 截断，不用。仅用已解压目录 |
| R4 | GEBCO memory | 每 tile 889 MB，单次内存需求高。不要 stack 多 tile，逐个处理 + del 释放 |
| R5 | GEBCO land/ocean | Sub-ice topo 同时含海洋负值和陆地正值。下游 mask 派生时用 ESA / JRC 限定海洋范围 |
| R6 | ACA rasterize | 需要 fiona + rasterio；Caribbean benthic = 8.4 GB，benthic 层 deferred |
| R7 | ACA coverage | 8K 分辨率（~4.9 km/pixel）无法表达礁体形态细节，只能表达礁体"存在" |
| R8 | ACA duplicate | `Central-South-Pacific-20230310003051 (1).zip` 为重复文件，处理时需去重（跳过含空格的 `(1)` 版本）|
| R9 | Aridity gap | 南纬 60° 以南无数据（683 行 nodata）。Antarctic 区域由 ESA ice mask 和极地 mask 独立覆盖，不依赖 aridity |
| R10 | scipy zoom | 非整数 scale factor 使用 scipy.ndimage.zoom；对 categorical 数据（Köppen）必须用 order=0，对连续数据用 order=1 |

---

## 12. Recommendation

**立即可执行，无需用户进一步操作：**

> **建议进入 EXT-C1 — Köppen-Geiger 8K Processing**

原因：
1. CC BY 4.0，无 license 阻塞
2. 文件只需从 ZIP 流式读取（12.5 MB），无需解压全量
3. nearest-neighbor 最简单，无数值运算误差风险
4. 输出 uint8 类别图，import test 简单明了
5. 完成后即可验证 external_processed_8k 目录流程是否正常

随后依次执行 Aridity → GEBCO → ACA（ACA 前需先确认 rasterio 可安装）。

**ACA 安装前置检查（在进入 ACA 处理前建议执行）：**

```bash
pip install fiona rasterio --break-system-packages
python3 -c "import fiona, rasterio; print('OK')"
```

若失败，执行 `brew install gdal` 后重试，或将 ACA 标记为 Phase 2 补充。

---

*Plan date: 2026-06-24*  
*No processing executed in this stage. No files extracted, resampled, or converted.*
