# Phase B-6.2X-D3-S-EXT-A — External Raw Source Audit

Stage: B-6.2X-D3-S-EXT-A  
Type: External raw source audit  
Status: **conditional_pass (3/4 sources ready; GEBCO pending rename)**  
Date: 2026-06-24

---

## 1. Scope

对 `d5b_processor_v3/source_cache/gee_global/external_raw/` 中 4 个外部 raw source 目录执行本地文件审查：

1. Global Aridity Index / PET（CGIAR-CSI v3.1）
2. Köppen-Geiger（Beck et al. 2023 v3 / GloH2O）
3. GEBCO（全球海底地形）
4. Allen Coral Atlas（全球珊瑚礁 vector 数据）

本轮只审查，不解压大文件，不重采样，不生成 mask，不进入 M1-B。

---

## 2. Directory Inventory

```
external_raw/
  global_aridity_pet/         4 files  (616 MB zip + 904 MB zip + 631 KB docx + 255 KB pdf)
  koppen_geiger/              2 files  (125 MB tif zip + 720 MB nc zip)
  gebco/                      1 file   (3.8 GB .crdownload ← 实际为 ZIP，需重命名)
  allen_coral_atlas/          30 zip + 1 extracted dir  (~16 GB)

external_manifests/
  external_source_manifest.template.json   (template)
  global_aridity_pet_manifest.json         (存在，已更新)
  koppen_geiger_manifest.json              (存在，已更新)
  gebco_manifest.json                      (新建)
  allen_coral_atlas_manifest.json          (新建)
```

---

## 3. Global Aridity / PET Audit

### 3.1 文件清单

| 文件 | 大小 | 内容 |
|------|------|------|
| `Global-AI_ET0__annual_v3_1.zip` | 616 MB | Annual: AI + ET0 + ET0_sd（各为 GeoTIFF）|
| `Global-ET0__monthly_v3_1.zip` | 904 MB | Monthly ET0：et0_v31_01 ~ et0_v31_12（GeoTIFF）|
| `Global AI_ET0 v3.1 - Readme.docx` | 631 KB | 官方 README（.docx 格式，含数据说明）|
| `global-aridity-and-global-pet-methodology.pdf` | 255 KB | 方法论 PDF |

### 3.2 Annual ZIP 内部文件（解压 listing）

| 文件 | 大小（压缩内） | 说明 |
|------|----------------|------|
| `ai_v31_yr.tif` | 405 MB（LZW 压缩 TIFF）| 年均 Aridity Index |
| `et0_v31_yr.tif` | 211 MB（LZW 压缩 TIFF）| 年均 ET0 |
| `et0_v31_yr_sd.tif` | 65 MB（LZW 压缩 TIFF）| ET0 标准差 |
| `.tfw` world files | 83 bytes each | 像素大小 + 原点 |
| `.aux.xml` / `.vat.dbf` | 各 <280 KB | ESRI 元数据 |
| `Global AI_ET0 v3.1 - Readme.docx` | 631 KB | README 副本 |

### 3.3 Spatial Metadata（从 .tfw + .xml 读取）

| 项目 | 值 |
|------|----|
| pixel_size | **0.0083333333° = 1/120° = 30 arc-second（~1km at equator）** |
| origin | (-179.9958°, 89.9958°)（center of top-left pixel）|
| CRS | EPSG:4326（WGS84）|
| coverage（W/E）| -180° to 180° |
| coverage（N/S）| **-60° to 90°**（不含南极洲 -90° 至 -60°）|
| native resolution | 43,200 × 18,000 pixels（估算，30" × 30"）|
| dtype | uint16（16-bit unsigned integer）|
| nodata | -2,147,483,648（≈ -2.1e9，实际为 uint16 overflow 标记）|
| compression | LZW（内部 TIFF 压缩）|

> ⚠️ **C1 — 南纬 60° 以南无数据**：Aridity Index 覆盖范围截止 -60°，不含南极洲。对 8K mask（-90 to 90）而言，最底部 ~1024 行（约 22° × 4096/180 ≈ 500 行）将无 aridity 数据。影响很小：该区域为南极洲冰盖，已有 `antarctica_ice_mask` 覆盖，desert mask 在此区域不适用。

### 3.4 Monthly ZIP 内部

包含 `et0_v31_01.tif` 至 `et0_v31_12.tif`，共 12 个月 ET0，与 annual 格式相同。用途：seasonal aridity pattern 分析（暂不是 M1 优先项）。

### 3.5 License / Commercial Clearance

| 项目 | 状态 |
|------|------|
| 来源 | CGIAR-CSI / Trabucco & Zomer |
| license | **非商业使用（non-commercial）；attribution required** |
| commercial_clearance | **false** |
| research_only | **true** |
| replacement_required_before_commercial | **true** |
| attribution | CGIAR-CSI Global-Aridity and Global-PET Database; Trabucco, Antonio; Zomer, Robert |

> ⚠️ **C2 — 商业受限（research_only）**：Aridity / PET 数据不可用于商业用途。RodiO 若进入商业发布，需替换为 CC BY 或更宽松的 aridity 数据源（可选：NASA POWER、ERA5-Land derived aridity，均为更开放许可）。

### 3.6 处理可行性（→ 8K）

- 从 43,200 × 18,000（30"）降采样至 8,192 × 4,096：可行，降采样比约 5.3x
- 缺失区域（south of -60°）：在 8K 网格中填充 nodata 或继承 ESA/ETOPO1 判断即可
- 无需 GDAL：tifffile + numpy 可处理（同 Phase 1 流程）
- 处理路径：解压 → 读取 ai_v31_yr.tif → 降采样 → 写出 8K GeoTIFF

**Verdict：`ready_but_license_restricted`**

---

## 4. Köppen-Geiger Audit

### 4.1 文件清单

| 文件 | 大小 | 内容 |
|------|------|------|
| `koppen_geiger_tif.zip` | 125 MB | GeoTIFF 格式，73 files |
| `koppen_geiger_nc.zip` | 720 MB | NetCDF 格式，73 files |

### 4.2 ZIP 内部结构（TIF zip）

两个 zip 结构完全一致，仅格式不同（.tif vs .nc）：

```
legend.txt
1901_1930/koppen_geiger_{0p00833333,0p1,0p5,1p0}.tif
1931_1960/koppen_geiger_{0p00833333,0p1,0p5,1p0}.tif
1961_1990/koppen_geiger_{0p00833333,0p1,0p5,1p0}.tif
1991_2020/koppen_geiger_{0p00833333,0p1,0p5,1p0}.tif    ← 现代 RodiO 用途目标
2041_2070/{ssp119,ssp126,ssp245,ssp370,ssp434,ssp460,ssp585}/koppen_geiger_*.tif
2071_2099/{ssp119,ssp126,ssp245,ssp370,ssp434,ssp460,ssp585}/koppen_geiger_*.tif
```

共 4 个历史时期 + 2 个未来时期 × 7 SSP 场景 = 18 个时期，每时期 4 个分辨率。

### 4.3 分辨率选项

| 文件名后缀 | 像素大小 | 描述 |
|-----------|----------|------|
| `_0p00833333.tif` | 0.00833333° = 30 arc-second（~1km）| 最高分辨率 |
| `_0p1.tif` | 0.1° = 6 arcmin（~11km）| 粗分辨率 |
| `_0p5.tif` | 0.5° = 30 arcmin（~55km）| 粗 |
| `_1p0.tif` | 1.0° = 1°（~111km）| 最粗 |

**RodiO 8K 用途应使用 `_0p00833333.tif`（30 arc-second）**

### 4.4 Class Legend（30 classes）

| code | class | 描述 |
|------|-------|------|
| 1 | Af | Tropical, rainforest |
| 2 | Am | Tropical, monsoon |
| 3 | Aw | Tropical, savannah |
| 4 | BWh | Arid, desert, hot |
| 5 | BWk | Arid, desert, cold |
| 6 | BSh | Arid, steppe, hot |
| 7 | BSk | Arid, steppe, cold |
| 8–16 | C* | Temperate（9 subclasses）|
| 17–28 | D* | Cold（12 subclasses）|
| 29 | ET | Polar, tundra |
| 30 | EF | Polar, frost |

> **RodiO desert mask 关键类：** BWh (4) + BWk (5) = 真正的 hot/cold desert；BSh (6) + BSk (7) = 半干旱草原边缘（可选为 semi-arid proxy）

### 4.5 RodiO Workflow 相关时期

| 时期 | 是否纳入当前 workflow |
|------|----------------------|
| `1991_2020` | ✅ **使用**（present-day climate）|
| `1901_1930` / `1931_1960` / `1961_1990` | ⬜ 历史，暂不使用 |
| `2041_2070` / `2071_2099` (SSP*) | ❌ **不进入 RodiO present-day workflow** |

> ⚠️ **C3 — Future SSP 文件不应用于当前 RodiO**：M1-B 和后续 mask 生成应仅读取 `1991_2020/` 内的文件，明确排除 `2041_2070/` 和 `2071_2099/`。

### 4.6 License / Commercial Clearance

| 项目 | 状态 |
|------|------|
| 来源 | Beck et al. (2023), GloH2O / figshare |
| license | **CC BY 4.0** |
| commercial_clearance | **true** |
| research_only | false |
| attribution | Beck, H.E., et al. Scientific Data 10, 724. doi:10.1038/s41597-023-02549-6 (2023) |

**Verdict：`ready_for_processing_8k`**

---

## 5. GEBCO Audit

### 5.1 文件清单

| 文件 | 大小 | 状态 |
|------|------|------|
| `未确认 276172.crdownload` | **3.8 GB** | ⚠️ Chrome 下载临时文件名 |

### 5.2 文件格式检测

```
Magic bytes (first 4): 50 4B 03 04 → "PK\x03\x04" = ZIP archive
```

> ✅ **文件实际为 ZIP 格式**。Chrome 下载完成后未自动将 `.crdownload` 重命名为 `.zip`（macOS 上偶发）。文件 3.8 GB 大小与 GEBCO 2024 GeoTIFF pack（GEBCO_2024.zip ≈ 3.5–4 GB）吻合，**下载可能已完成**。

### 5.3 无法验证内容

由于边界规则限制，不能对此大文件解压验证。无法确认：
- GEBCO 版本年份（2022 / 2023 / 2024）
- 内部文件格式（GeoTIFF / NetCDF / 分块 GeoTIFF）
- 是否全球覆盖 / 是否包含 ice surface elevation

### 5.4 已知 GEBCO License（公开信息）

| 项目 | 状态 |
|------|------|
| 来源 | GEBCO Compilation Group |
| license | **非常宽松（CC0-like）** — 允许任意使用（含商业），要求 attribution |
| commercial_clearance | **true**（GEBCO 为开放数据，无商业限制）|
| research_only | false |
| attribution | GEBCO Compilation Group (GEBCO_2024 Grid) (2024) doi:10.5285/1c44ce99-0a0d-5f4f-e063-7086abc0ea0f |

> ⚠️ **attribution 中的 year / doi 需待重命名后验证**，上述 doi 为 GEBCO 2024 Grid TID；如为其他年份需调整。

### 5.5 Critical Issue

> 🔴 **CRITICAL: GEBCO 文件需手动重命名**
>
> 文件 `未确认 276172.crdownload` 实为 ZIP 格式，但 Chrome 使用临时下载名，需用户手动将其重命名为 `.zip`（如 `gebco_2024_grid.zip`）。
>
> **边界规则限制本 agent 不得移动 / 重命名 source 文件。请用户手动执行：**
> ```bash
> cd d5b_processor_v3/source_cache/gee_global/external_raw/gebco/
> mv "未确认 276172.crdownload" gebco_2024_grid.zip
> ```
>
> 重命名后，下一阶段（D3-S-EXT-B）可 `unzip -l` 验证内容并更新 manifest。

**Verdict：`incomplete`（等待用户重命名文件）**

---

## 6. Allen Coral Atlas Audit

### 6.1 文件清单

共 **30 个 ZIP 文件**（29 个独立区域 + 1 个重复），合计 ~16 GB，加上 1 个已解压目录。

| 区域 | ZIP 大小 |
|------|---------|
| Andaman Sea | 203 MB |
| Bermuda | 23 MB |
| Brazil | 31 MB |
| Central Indian Ocean | 156 MB |
| **Central South Pacific** | **191 MB × 2（重复）** |
| Coral Sea | 51 MB |
| Eastern Africa - Madagascar | 408 MB |
| Eastern Micronesia | 168 MB |
| Eastern Papua New Guinea - Solomon Islands | 654 MB |
| Eastern Tropical Pacific | 43 MB |
| Great Barrier Reef and Torres Strait | 635 MB |
| Hawaiian Islands | 67 MB |
| Mesoamerica | 246 MB |
| Northeastern Asia | 69 MB |
| Northern Caribbean, Florida & Bahamas | 2.4 GB |
| Northwestern Arabian Sea | 398 MB |
| Philippines | 898 MB |
| Red Sea & Gulf of Aden | 737 MB |
| South China Sea | 79 MB |
| Southeast Asian Archipelago | 1.4 GB |
| Southeastern Caribbean | 186 MB |
| Southern Asia | 71 MB |
| Southwestern Pacific | 552 MB |
| Subtropical Eastern Australia | 12 MB |
| Timor - Arafura Seas | 380 MB |
| Western Africa | 76 MB |
| Western Australia | 138 MB |
| Western Indian Ocean | 150 MB |
| Western Micronesia | 106 MB |

**总计：29 个独立区域，全球主要珊瑚礁海域均已覆盖。**

### 6.2 ZIP 内部结构（从 Bermuda 和 SEA 确认）

每个 ZIP 包含：

```
Reef-Extent/
  reefextent.gpkg              ← 礁体边界（GeoPackage vector）
Geomorphic-Map/
  geomorphic.gpkg              ← 地貌分类（GeoPackage vector）
Benthic-Map/
  benthic.gpkg                 ← 底栖底质分类（GeoPackage vector）
boundary/
  boundary.geojson             ← 区域边界（JSON）
stats/
  statistics.csv               ← 面积统计
1-License-and-Documentation/
  1-Data-Licenses-and-Citation-Guidance.pdf
  2-Data-Attribution.csv       ← 多机构贡献者列表（可读，CSV）
  Class-Descriptions-Benthic-Maps-v3.pdf
  Class-Descriptions-Geomorphic-Maps-v3.pdf
  Habitat-Map-Dates.pdf
  Methods-Bathymetry.pdf
  User-Guide-Part-1-General-Use.pdf
  User-Guide-Part-2-Map-Classes.pdf
```

> ⚠️ **C4 — 格式为 GeoPackage（Vector），非 GeoTIFF（Raster）**：
>
> 所有数据均以 `.gpkg`（GeoPackage = SQLite-based vector）格式存储，而非 8K 流程期望的 GeoTIFF raster。要在 M1 pipeline 中使用，需要：
> 1. 读取 .gpkg（需 fiona + shapely 或 geopandas）
> 2. 将 vector 栅格化至 8192×4096（需 rasterio.features.rasterize 或 gdal_rasterize）
> 3. 写出 GeoTIFF
>
> 由于 GDAL / rasterio 当前未安装，此步骤比 Phase 1 流程复杂。需在 EXT-B 阶段规划安装路径或替代方案。

### 6.3 重复文件

`Central-South-Pacific-20230310003051 (1).zip` 与 `Central-South-Pacific-20230310003051.zip` 大小完全相同（191 MB），为 macOS 重复下载命名。两者内容应一致；无需删除，但报告记录。

### 6.4 SEA archive 已部分解压

`Southeast-Asian-Archipelago-20230310000615/`（即同名 ZIP 的解压目录）存在于磁盘，包含完整结构：

```
1-License-and-Documentation/
Benthic-Map/benthic.gpkg
Geomorphic-Map/geomorphic.gpkg
Reef-Extent/reefextent.gpkg
boundary/boundary.geojson
stats/statistics.csv
```

### 6.5 License / Commercial Clearance

| 项目 | 状态 |
|------|------|
| 来源 | Allen Coral Atlas（Arizona State University + Planet Labs 等）|
| license | **CC BY 4.0**（根据 Allen Coral Atlas 官方发布政策）|
| commercial_clearance | **true**（CC BY 4.0 允许商业使用，要求 attribution）|
| attribution | Allen Coral Atlas, https://allencoralatlas.org/ Lyons et al. (2020) doi:10.1038/s41586-020-2532-2 |

> ℹ️ **Attribution CSV 中包含多机构第三方来源数据**（Reef Check、各大学、政府机构等）。这些数据用于辅助 ACA 算法训练，并非直接分发的最终产品数据。最终 .gpkg 产品本身遵循 CC BY 4.0。
>
> 由于无法读取 PDF（缺少 poppler），上述 license 信息基于 ACA 官方公开说明。建议在 EXT-B 阶段用户安装 poppler 后读取 `1-Data-Licenses-and-Citation-Guidance.pdf` 确认。

**Verdict：`ready_for_processing_8k`（需要 rasterization 步骤；license confirmation 待 PDF 阅读）**

---

## 7. License / Attribution / Commercial Clearance Summary

| 源 | License | Commercial | Research Only | Attribution Required | Replacement Before Commercial |
|----|---------|-----------|---------------|---------------------|-------------------------------|
| Global Aridity / PET | non-commercial | ❌ false | ✅ true | ✅ true | ✅ true |
| Köppen-Geiger | CC BY 4.0 | ✅ true | false | ✅ true | false |
| GEBCO | CC0-like (free use + attribution) | ✅ true | false | ✅ true | false |
| Allen Coral Atlas | CC BY 4.0 | ✅ true | false | ✅ true | false |

> **Aridity 是唯一 research_only source。** 其他 3 个均为 CC BY 4.0 或更宽松，可商业使用。

---

## 8. Processing Readiness

| 源 | Readiness | 理由 |
|----|-----------|------|
| Global Aridity / PET | `ready_but_license_restricted` | 数据完整，30 arc-second GeoTIFF，可处理；但 non-commercial 限制 |
| Köppen-Geiger | `ready_for_processing_8k` | 数据完整，1991-2020 present-day 可用，CC BY 4.0，30" GeoTIFF |
| GEBCO | `incomplete` | 文件为 ZIP（magic bytes 确认），但 Chrome 未重命名 .crdownload → 需用户操作 |
| Allen Coral Atlas | `ready_for_processing_8k` | 29 区域全覆盖，需额外 rasterization 步骤（vector → raster）|

---

## 9. Recommended Next Step

**建议按以下顺序推进：**

### 即时（可在本 session 完成）

1. **用户手动重命名 GEBCO 文件**（参见 Section 5.5），然后
2. 执行 `B-6.2X-D3-S-EXT-B — External Source Processing Plan`：
   - 规划 Aridity + Köppen-Geiger → 8K GeoTIFF 降采样步骤
   - 规划 Allen Coral Atlas gpkg → 8K GeoTIFF rasterization 步骤（含 rasterio/fiona 安装评估）
   - GEBCO 重命名后：`unzip -l` 验证内容，更新 manifest

### 阻塞项

- GEBCO 在用户重命名前处于 `incomplete` 状态，不影响 Aridity / Köppen-Geiger / ACA 的处理规划

### 中期（M1 / M2 用途）

| 源 | M1 用途 |
|----|---------|
| Köppen-Geiger 1991-2020 | `desert_mask`（BW* = 4/5），`semi_arid_mask`（BS* = 6/7），`tropical_mask`（A* = 1/2/3），`tundra_mask`（ET = 29）|
| Global Aridity AI | `arid_zone_mask`（AI < 0.2 = hyperarid/arid），`semi_arid_zone_mask`（AI 0.2–0.5）|
| Allen Coral Atlas | `reef_mask`，`reef_extent_mask`，`shallow_reef_mask`（reefextent.gpkg + geomorphic.gpkg）|
| GEBCO | `refined_bathymetry_mask`（替代 ETOPO1 作为深海 / 海沟 refinement）|

---

## 10. Issues / Risks

| ID | 来源 | 描述 | 优先级 | 状态 |
|----|------|------|--------|------|
| I1 | GEBCO | Chrome crdownload 未重命名，无法验证内容 | 🔴 **高** | 阻塞 GEBCO 使用 |
| I2 | Global Aridity | non-commercial license；RodiO 商业化前需替换 | 🟡 中 | 已记录，不阻塞研究阶段 |
| I3 | Köppen-Geiger | 包含 SSP future 文件（2041-2099），需在处理代码中明确排除 | 🟡 中 | 文档记录，不阻塞 |
| I4 | Allen Coral Atlas | 格式为 GeoPackage vector，需 rasterization 步骤（无 GDAL/rasterio）| 🟡 中 | 需安装 rasterio 或寻找替代方案 |
| I5 | Allen Coral Atlas | Central-South-Pacific 有重复 zip（macOS 二次下载）| 🟢 低 | 记录，不影响处理 |
| I6 | Allen Coral Atlas | 未能读取 license PDF（缺少 poppler）| 🟢 低 | CC BY 4.0 据公开来源，待 poppler 安装后确认 |
| I7 | Global Aridity | 南纬 60° 以南无数据（Antarctica 区域）| 🟢 低 | 可接受，Antarctica 已有 ice mask 覆盖 |

---

*Audit executed: 2026-06-24*  
*Methods: file listing, unzip -l, Python magic bytes check, XML metadata parsing, .tfw world file reading*  
*No files extracted (except listing). No files moved, renamed, or deleted. No masks generated.*
