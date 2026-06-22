# Phase B-6.1 — Asset Audit Task Brief

## 文档定位

本文档是 B-6.1 阶段的执行任务说明。B-6.1 的唯一目标是**静态资产审计与依赖确认**，不生成任何 mask，不修改 d6 generator，不进入前端。

上位规划文档：`docs/phase_b6_global_earth_structure_mask_layer_plan.md`

---

## B-6.1 总目标

在生成任何 structure mask 之前，锁定以下内容：

1. ETOPO1 文件路径、格式、尺寸、完整性 hash
2. GSHHG 文件路径、可用层级、完整性 hash
3. GEBCO 文件路径、覆盖范围确认（仅 Japan subset or global）
4. Python 依赖可用性（netCDF4 / h5py / shapefile / geopandas / rasterio / scipy / PIL / numpy）
5. 判断 B-6.2 是否可直接生成 2K structure masks，还是需要先补充数据

**严格禁止**：不修改 d6，不生成贴图，不进入前端，不 commit。

---

## 任务 1：ETOPO1 文件审计

### 1.1 查找 ETOPO1 文件

在项目目录下搜索所有可能的 ETOPO1 相关文件：

```bash
find . -iname "*etopo*" -o -iname "*topo*" -o -iname "*bathymetry*" | grep -v ".git"
find . -name "*.nc" -o -name "*.grd" -o -name "*.tif" | grep -v ".git"
```

也搜索标准下载位置：

```bash
ls ~/Downloads/ | grep -i etopo
ls ~/data/ 2>/dev/null | grep -i etopo
ls /Volumes/ 2>/dev/null
```

### 1.2 锁定信息

对找到的文件记录：

| 字段 | 内容 |
|---|---|
| 文件路径 | 绝对路径 |
| 格式 | NetCDF4 / GeoTIFF / Binary |
| 变量名 | 如 `z`（ETOPO1 标准）|
| 尺寸 | 行×列（ETOPO1 global = 21601×10801 @ 1 arcmin）|
| CRS / 投影 | EPSG:4326 expected |
| 数值范围 | min / max（meters，负数=深海，正数=陆地）|
| 文件大小 | bytes |
| MD5 hash | `md5 <file>` |

### 1.3 格式优先级

- 优先使用：`ETOPO1_Ice_g_gmt4.grd`（NetCDF4，ice surface）或 `ETOPO1_Bed_g_gmt4.grd`（bedrock）
- 备选：GeoTIFF 格式（`ETOPO1_Ice_g_geotiff.tif`）
- 不接受：仅有 ASCII / binary grid 而无 NetCDF/GeoTIFF

---

## 任务 2：GSHHG 文件审计

### 2.1 查找 GSHHG 文件

```bash
find . -iname "*gshhg*" -o -iname "*gshhs*" -o -iname "*.shp" | grep -v ".git" | head -40
find . -name "*.shp" | grep -v ".git"
```

### 2.2 需要确认的层级

GSHHG 分为 5 个分辨率（`f`=full / `h`=high / `i`=intermediate / `l`=low / `c`=crude）
以及 5 个层级（L1=海岸线 / L2=湖泊 / L3=湖中岛 / L4=冰下湖 / L5=南极冰架）。

B-6 所需：**L1（海岸线）** 的至少 `f`（full）或 `h`（high）分辨率。

记录：

| 文件名 | 层级 | 分辨率 | 要素数量 | 大小 | 路径 |
|---|---|---|---|---|---|
| gshhs_f_L1.shp | L1 | full | — | — | — |
| gshhs_h_L1.shp | L1 | high | — | — | — |

### 2.3 验证 shapefile 可读

用 Python 快速验证：

```python
import shapefile
sf = shapefile.Reader("path/to/gshhs_f_L1.shp")
print(len(sf.shapes()), "shapes")
print(sf.bbox)  # global bbox should be [-180, -90, 180, 90]
```

---

## 任务 3：GEBCO 文件审计

### 3.1 确认 GEBCO 覆盖范围

当前 devlog / 历史文档指出 GEBCO 数据仅为 Japan subset。需要确认：

```bash
find . -iname "*gebco*" | grep -v ".git"
```

对找到的文件，用 ncdump 或 Python 确认 bbox：

```python
import netCDF4 as nc
ds = nc.Dataset("path/to/gebco.nc")
print(ds.variables['lat'][:].min(), ds.variables['lat'][:].max())
print(ds.variables['lon'][:].min(), ds.variables['lon'][:].max())
```

### 3.2 判断 GEBCO 用途

- 如果是 global GEBCO（-180 to 180, -90 to 90）：可作为 ETOPO1 的替代或补充
- 如果仅为 Japan subset：只用于 Japan / East Asia 区域的高精度深度 mask
- 如果不存在：B-6.2 仅依赖 ETOPO1 + GSHHG

---

## 任务 4：Python 依赖审计

逐一验证以下依赖是否可用：

```bash
python3 -c "import netCDF4; print('netCDF4', netCDF4.__version__)"
python3 -c "import h5py; print('h5py', h5py.__version__)"
python3 -c "import shapefile; print('pyshp', shapefile.__version__)"
python3 -c "import geopandas; print('geopandas', geopandas.__version__)"
python3 -c "import rasterio; print('rasterio', rasterio.__version__)"
python3 -c "import scipy; print('scipy', scipy.__version__)"
python3 -c "import PIL; print('Pillow', PIL.__version__)"
python3 -c "import numpy; print('numpy', numpy.__version__)"
python3 -c "import skimage; print('scikit-image', skimage.__version__)"
```

对每个依赖记录：

| 库 | 版本 | 可用 | B-6 用途 |
|---|---|---|---|
| netCDF4 | — | Y/N | 读取 ETOPO1 / GEBCO .nc 文件 |
| h5py | — | Y/N | GEBCO HDF5 格式备选 |
| shapefile (pyshp) | — | Y/N | 读取 GSHHG .shp 文件 |
| geopandas | — | Y/N | shapefile rasterization（可选）|
| rasterio | — | Y/N | GeoTIFF 读取（ETOPO1 备选格式）|
| scipy | — | Y/N | 距离变换（coastline feather）|
| Pillow | — | Y/N | 输出 mask 图像 |
| numpy | — | Y/N | 所有 array 操作 |
| scikit-image | — | Y/N | 形态学操作（可选）|

如有缺失，记录安装命令：`pip3 install <package>`（不在审计阶段安装）。

---

## 任务 5：B-6.2 可行性判断

根据以上审计结果，输出以下判断：

### 5.1 ETOPO1 就绪状态

- [ ] ETOPO1 文件存在且格式可读
- [ ] 文件为 global coverage（-180 to 180, -90 to 90）
- [ ] 数值范围合理（陆地 > 0，深海 < -6000）
- [ ] netCDF4 或 rasterio 可读取

### 5.2 GSHHG 就绪状态

- [ ] L1 shapefile 存在（full 或 high 分辨率）
- [ ] shapefile 可通过 pyshp 读取
- [ ] bbox 覆盖全球

### 5.3 依赖就绪状态

- [ ] netCDF4 或 rasterio 可用（二选一）
- [ ] pyshp 可用
- [ ] scipy 可用
- [ ] numpy + Pillow 可用

### 5.4 综合判断

| 判断结论 | 条件 |
|---|---|
| **B-6.2 可直接实施** | ETOPO1 + GSHHG + 核心依赖全部就绪 |
| **B-6.2 需先补充数据** | ETOPO1 缺失 → 需下载；GSHHG 缺失 → 需下载 |
| **B-6.2 需先安装依赖** | netCDF4 / pyshp / scipy 缺失 |
| **B-6.2 降级方案** | 仅用 GSHHG 生成 land mask，ETOPO1 缺失时跳过 depth mask |

---

## 任务 6：ETOPO1 / GSHHG 下载信息（如需补充）

### ETOPO1 标准下载来源

```
来源：NOAA NCEI
格式：NetCDF4 (.nc) 或 GeoTIFF (.tif)
大小：约 450MB（NetCDF4 全球 1 arcmin）
用途：全球海深 / 陆地高程，用于生成 depth_mask 和 elevation_mask
```

### GSHHG 标准下载来源

```
来源：NOAA / Paul Wessel (GMT)
格式：Shapefile (.shp) 或 binary (.b)
推荐版本：GSHHG-shp-2.3.7 (full + high resolution)
大小：约 200MB（full resolution）
用途：海岸线向量，用于生成 coastline_mask 和 island_proximity_mask
```

---

## 任务 7：输出格式要求

B-6.1 审计完成后，输出以下格式的总结：

```
=== B-6.1 Asset Audit Summary ===

ETOPO1:
  path: <绝对路径 or "NOT FOUND">
  format: <NetCDF4 / GeoTIFF / NOT FOUND>
  size: <rows x cols or "N/A">
  md5: <hash or "N/A">
  status: READY / MISSING / WRONG_FORMAT

GSHHG:
  L1_full_path: <绝对路径 or "NOT FOUND">
  L1_high_path: <绝对路径 or "NOT FOUND">
  shapes_count: <int or "N/A">
  status: READY / MISSING / PARTIAL

GEBCO:
  path: <绝对路径 or "NOT FOUND">
  coverage: GLOBAL / JAPAN_ONLY / NOT FOUND
  status: SUPPLEMENTAL / NOT_NEEDED / MISSING

Dependencies:
  netCDF4: <version or MISSING>
  h5py: <version or MISSING>
  shapefile: <version or MISSING>
  geopandas: <version or MISSING>
  rasterio: <version or MISSING>
  scipy: <version or MISSING>
  Pillow: <version or MISSING>
  numpy: <version or MISSING>

B-6.2 Verdict: READY_TO_PROCEED / NEED_DATA / NEED_DEPS / DEGRADED_MODE
```

---

## 禁止项

- 不生成任何 mask 文件
- 不修改 `d6_noon_air_earth_generator.py`
- 不运行 generator
- 不生成贴图
- 不进入前端
- 不 commit
- 不 push
- 不安装任何依赖（仅审计可用性，记录缺失）
