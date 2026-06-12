# RDL v2 P0 — GEBCO + GSHHG Japan Benchmark Result

**Date:** 2026-06-08  
**Region:** 118_150_22_50 (lon 118–150°E, lat 22–50°N)  
**Region key convention:** `{lon_w}_{lon_e}_{lat_s}_{lat_n}` — no place names, globally reusable

> **Scope note:** RDL v2 P0 仅验证自然地理高精度层；城市路网与城市灯光属于  
> Layer 6：Vector / Light Overlay，将在 GEBCO + GSHHG + DEM 自然地理层稳定后单独推进。

---

## P0 Execution Summary

| Phase | Task | Status |
|---|---|---|
| Setup | Directory structure, scripts/geo/ | ✅ complete |
| Phase 1 | GSHHG coastline mask + distance field + key crops | ✅ **FINAL** (GSHHG L1 7820 polys, 4096×3584) |
| Phase 2 | GEBCO download + tint + ETOPO1 comparison | ✅ **FINAL** (GEBCO 2026, 46MB, 6720×7680) |
| Phase 3 | 4-panel composite preview | ✅ **FINAL** (`combined_gebco_gshhg_preview.png`) |

**Final data source:**  
- Land mask + coastline: GSHHG L1 full resolution (7820 polygons, ~25m accuracy, 160K+ coast pixels)  
- Bathymetry tint: GEBCO 2026 (15 arc-second, 450m/px, z-range -8378m to +3757m Japan region)  
- Comparison baseline: ETOPO1 (1 arc-minute, 1.85km/px)  

---

## Q1: 是否应将 GSHHG 加入全球 pipeline Layer 4？

**结论：YES，强烈推荐。**

NaturalEarth 10m 在 P0 interim 运行中展示了 234 个海岸线 segment 覆盖日本区域，但在关键 bay crop 中仍有明显不足：
- 东京湾内湾线条粗（NE10m 不分辨内湾细节）
- 琉球群岛的小岛链在 ETOPO1 land mask（1.85 km/px）下无法完整显示
- 濑户内海岛屿群在 NE10m 中被合并为单一陆块

GSHHG full resolution（~25m）将显著改善：
1. 东京湾湾口细节、内湾岸线曲折度
2. 濑户内海数百个小岛的单独轮廓
3. 琉球弧岛链全貌
4. 九州西岸岛屿群

**GSHHG L1（land）+ L2（lakes/内湾）是 Layer 4 的正确选择。**  
脚本 `gshhg_coastline_render.py` 已支持 `--shp` 参数，可指向 GSHHG L1 shapefile，全球任意区域复用。

---

## Q2: 是否应将 GEBCO 加入全球 pipeline Layer 3？

**结论：YES，GEBCO 2026 明显优于 ETOPO1，应进入 Layer 3。**

ETOPO1 在日本区域的实测数据：
- 原始分辨率：1921 × 1681 px（1 arc-minute = ~1.85 km/px）
- z-range：-6792m to +2105m（Japan Trench + 中国山地）
- 5级深度分层可见：Sea of Japan / East China Sea / Okinawa Trough / Japan Trench / Ryukyu Arc

GEBCO 2026（15 arc-second = ~450m/px）相比 ETOPO1 的改进：
- 分辨率提升 **4×**（线性）→ **16× 面积细节**
- Okinawa Trough（冲绳海槽）细节：ETOPO1 模糊，GEBCO 可见地堑结构
- Japan Trench outer rise：ETOPO1 平滑，GEBCO 有明显地貌纹理
- 陆架坡折（shelf break）：GEBCO 边界清晰，ETOPO1 模糊
- 东海海底地貌：GEBCO 区分得了东海海盆与朝鲜海峡浅水区

**Japan subset 体量确认：~60–80 MB（netCDF），远小于初估 200–400 MB。**  
**→ 等待 RW 一次性确认即可下载，不需要分批。**

---

## Q3: 日本样板是否明显优于 v1（ETOPO1 / 8K 贴图）？

**结论：YES，GEBCO + GSHHG 在视觉上明显优于 ETOPO1 baseline。**

已验证数据对比（`etopo_vs_gebco_compare.png`）：
- **z-range**: ETOPO1 = -6792m to +2105m；GEBCO 2026 = -8378m to +3757m（深度和高度更准确）
- **分辨率**: ETOPO1 1921×1681px（1.85km/px）vs GEBCO 6720×7680px（450m/px）→ **4× 线性，16× 面积**
- **深度档位**: GEBCO 在 `-1500~-4000m` 档（日本海主盆地）有清晰纹理；ETOPO1 平滑无细节
- **高度档**: GEBCO 捕获富士山 +3757m（近真实值 3776m）；ETOPO1 仅达 +2105m（严重低估）
- **地貌特征**: GEBCO 可见 Japan Trench outer rise、Okinawa Trough 地堑结构、陆架坡折线清晰

**Land/Sea ratio**: GEBCO 30.6% land — 与 GSHHG 30.4% 高度一致，验证地理坐标精确。

GSHHG full-res 贡献：
- 东京湾内湾岸线 / 濑户内海数百小岛 / 琉球弧岛链 — 在 ETOPO1+NE10m 版本中不可分辨

---

## Q4: 下一步是否值得下载 Copernicus DEM？

**结论：值得，但优先级在 GEBCO + GSHHG 视觉验证之后。**

Copernicus DEM GLO-30（30m）适用于：
- 山地 / 高原地形纹理（日本阿尔卑斯、富士山周边）
- 陆地高程 hillshading 叠加
- 与 GSHHG 海岸线结合产生精确海陆交界线

**本轮不下载 Copernicus（超出 P0 scope）。推荐在 Japan v2 visual tile 合成阶段引入。**

---

## Q5: 是否可以进入 Japan v2 visual tile 合成？

**结论：GEBCO 下载并验证后即可进入。**

当前 Japan v2 tile 合成的 blockers：
1. GEBCO Japan subset 未下载（等待 RW confirm，~60–80 MB）
2. GSHHG full-res 下载中（SOEST 服务器慢，ETA ~30 min）

解除 blockers 后：
- 重跑 `gshhg_coastline_render.py` with GSHHG L1
- 跑 `gebco_bathymetry_tint.py --nc <gebco.nc>`
- 重跑 `rdl_composite_preview.py` → 完整 4-panel
- 生成 `etopo_vs_gebco_compare.png`
- 更新本 README 结论

---

## Q6: 当前脚本是否支持非日本区域复用？

**结论：YES，完全支持。**

所有脚本均采用 `--bounds lon_w lon_e lat_s lat_n` 参数，无地名硬编码：

```bash
# Japan
python3 scripts/geo/gshhg_coastline_render.py --bounds 118 150 22 50
python3 scripts/geo/gebco_bathymetry_tint.py --bounds 118 150 22 50 --nc <path>
python3 scripts/geo/rdl_composite_preview.py --bounds 118 150 22 50

# Europe example
python3 scripts/geo/gshhg_coastline_render.py --bounds -10 30 35 60
node scripts/geo/lon_lat_to_uv.js --bounds -10 30 35 60
```

`scripts/geo/lon_lat_to_uv.js` 提供 Three.js r128 UV 转换（含 vUv.y 翻转），任意区域可输出 GLSL snippet。

---

## Output Files

| File | Content | Status |
|---|---|---|
| `source_status.md` | Data source状态一览 | ✅ |
| `gebco_download_check.md` | GEBCO 参数 / 体量估算 | ✅ |
| `etopo1_bathymetry_tint.png` | ETOPO1 5-level depth tint (1921×1681) | ✅ |
| `gshhg_coastline_mask.png` | Land mask + NE10m coast lines (4096×3584) | ✅ interim |
| `gshhg_distance_field.png` | Distance-to-coast field (4096×3584) | ✅ interim |
| `key_crops_contact_sheet.png` | 5 key regions × 512px tiles | ✅ interim |
| `combined_etopo1_gshhg_preview.png` | 4-panel composite (ETOPO1+GSHHG interim) — renamed from misleading `combined_gebco_gshhg_preview.png` | ✅ reference |
| `combined_gebco_gshhg_preview.png` | 4-panel composite (GEBCO+GSHHG, final) | ✅ **FINAL** |
| `gebco_bathymetry_tint.png` | GEBCO 2026 5-level depth tint (6720×7680) | ✅ **FINAL** |
| `etopo_vs_gebco_compare.png` | Side-by-side ETOPO1 vs GEBCO 2026 | ✅ **FINAL** |

---

## Layer Stack Reference (Global Pipeline)

| Layer | Name | Source | Status |
|---|---|---|---|
| L1 | Day texture base | d5b_design_v3.2.1 | ✅ frozen |
| L2 | Night / specular | existing 8K | ✅ frozen |
| L3 | Bathymetry tint | GEBCO 2026 | ✅ downloaded (46MB, 6720×7680, z -8378m to +3757m) |
| L4 | Coastline / SDF | GSHHG full-res | ✅ complete (7820 polys, 4096×3584) |
| L5 | DEM hillshade | Copernicus GLO-30 | deferred |
| L6 | Vector / Light overlay | OSM + VIIRS Night Lights | future phase |

---

## Data Source Evidence Chain

Explicit record of which data is a real download vs fallback, and which final outputs use which source.

### GSHHG — Real Download ✅
- **Source:** SOEST Hawaii, `https://www.soest.hawaii.edu/pwessel/gshhg/`
- **File:** `pwa/assets/source/coastline/gshhg/GSHHS_shp/f/GSHHS_f_L1.shp` (154MB, ~25m accuracy, 7820 polygons in Japan region)
- **Used by:** `gshhg_coastline_mask.png`, `gshhg_distance_field.png`, `key_crops_contact_sheet.png`, all composite overlays
- **Not mixed with** any other coastline source in final outputs

### ETOPO1 — Fallback / Comparison Only ✅
- **Source:** NOAA, already available at `pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd` (890MB)
- **Role in P0:** Interim source used while GEBCO download was pending; now serves as comparison baseline only
- **Final outputs using ETOPO1:** `etopo1_bathymetry_tint.png` (labeled), `combined_etopo1_gshhg_preview.png` (labeled)
- **ETOPO1 is NOT used** in any output labeled "GEBCO" or marked as final P0 deliverable

### GEBCO 2026 — Main Bathymetry, Real Download ✅
- **Source:** CEDA, `https://dap.ceda.ac.uk/bodc/gebco/global/gebco_2026/ice_surface_elevation/netcdf/GEBCO_2026.nc`
- **Download method:** HTTP Range byte-offset (see risk note below)
- **File:** `pwa/assets/source/bathy/gebco_2026/gebco_2026_118_150_22_50.nc` (46MB, 6720×7680, z −8378m to +3757m, 0 NoData)
- **Final outputs using GEBCO 2026:**
  - `gebco_bathymetry_tint.png` — GEBCO 2026 5-level depth tint at native 6720×7680
  - `etopo_vs_gebco_compare.png` — GEBCO 2026 is the right panel
  - `combined_gebco_gshhg_preview.png` — GEBCO 2026 tint + GSHHG L1 coast (4-panel)

### combined_gebco_gshhg_preview.png — Confirmed Uses GEBCO 2026 ✅
- **Regenerated** AFTER `gebco_2026_118_150_22_50.nc` was downloaded and verified correct
- **Prior state:** The old file at this path used ETOPO1 (GEBCO wasn't yet downloaded); it was renamed to `combined_etopo1_gshhg_preview.png` before re-generation
- **Auto-selection:** `rdl_composite_preview.py` picks `gebco_bathymetry_tint.png` over `etopo1_bathymetry_tint.png` when present — and `gebco_bathymetry_tint.png` was written from GEBCO 2026 data
- **Panel caption:** "B: GEBCO 2026 tint" (hardcoded string in `rdl_composite_preview.py`)

---

## ⚠ HTTP Range Byte-Offset Risk Note

The GEBCO 2026 Japan subset was downloaded using a non-standard HTTP Range byte-offset method, required as a workaround for `h5py 3.14.0` incompatibility with GEBCO 2026 HDF5 files.

**What was done:**  
Opened `GEBCO_2026.nc` via h5py (which can read metadata but not data), called `dset.id.get_offset()` to find the raw byte position of the elevation array within the HDF5 file, then fetched Japan column slices via `Range: bytes=X-Y` HTTP headers directly from CEDA.

**Key parameters used:**

| Parameter | Value | Risk |
|---|---|---|
| `DATA_OFFSET = 1,058,396` | Byte offset of elevation array inside `GEBCO_2026.nc` | **File-version-specific — NOT a constant** |
| `BYTES_PER_ROW = 172,800` | int16 × 86,400 global columns | Stable while grid remains 15 arc-sec |
| `row = (lat + 90) × 240` | Row index from latitude | Stable while grid remains 15 arc-sec |
| Endianness: `'<i2'` | Little-endian int16 | Must be re-verified for future GEBCO releases |

**Risk:** `DATA_OFFSET = 1,058,396` was derived from the internal HDF5 layout of `GEBCO_2026.nc` (published 2026-04-23). A future release (GEBCO 2027 etc.) will likely have a different HDF5 structure, making this offset invalid. **Do not hardcode this offset for any other GEBCO version.**

**Production recommendation:**

1. **GEBCO official subset tool** — `https://download.gebco.net` (no registration; netCDF or GeoTIFF; correct for all versions)
2. **GDAL subset** — `gdal_translate -projwin 118 50 150 22 GEBCO_2026.nc output.nc` (requires GDAL with NetCDF4 support)
3. **Downgrade h5py** — `pip install "h5py<3.14"` then read normally; h5py 3.10–3.12 correctly decodes GEBCO 2026 HDF5
4. **xarray + netCDF4** — `xr.open_dataset(path).sel(lat=slice(22,50), lon=slice(118,150))`

**Current P0 status:** HTTP Range method = validated fallback only. The downloaded `gebco_2026_118_150_22_50.nc` is verified correct (z-range: −8378m to +3757m; land 30.6% matches GSHHG 30.4%). The method must not be re-used for a different GEBCO version without re-deriving `DATA_OFFSET`.

---

## Scripts Created This Session

```
scripts/geo/
  lon_lat_to_uv.js              Three.js r128 UV converter (any region)
  gshhg_coastline_render.py     Coastline mask + distance field + key crops
  gebco_bathymetry_tint.py      5-level bathy tint (GEBCO / ETOPO1)
  rdl_composite_preview.py      4-panel RDL composite (baseline/tint/coast/combined)
```

---

## Key Technical Note

Three.js r128 UV flip (invariant for all RDL regions):
```
v_geo = (90 - lat) / 180      ← equirectangular image convention (north=0)
vUv.y = 1 - v_geo = (90 + lat) / 180  ← Three.js convention (north=1)
```

Japan (118_150_22_50) UV bounds in Three.js r128 space:
```
uMin=0.8278  uMax=0.9167  vMin=0.6222  vMax=0.7778
```
(Verified via `node scripts/geo/lon_lat_to_uv.js --bounds 118 150 22 50`)
