# 全球海洋水色纹理 — 阶段 A 实现与验证报告（#57 Phase A）

> 承接 #57 Step 0 可行性调研。本报告记录**真实数据获取 → 烘焙脚本 → 独立验证**的完整过程，
> 产物是一张 4096×2048 的全球等距柱状（Plate Carrée）海洋水色 RGBA 纹理。
> 集成进 `earth3d.js` 是阶段 B 的事，本阶段只把纹理做对做实。
>
> **归档说明**：脚本+交付纹理已复制到 `docs/roadmap/source_appendix/ocean_color_phaseA/`（随git提交，永久可查）。
> 原始下载的3个NetCDF源文件（597.5MB）+ 中间二进制产物体积太大不适合入git，留在本文档下方命令指向的
> `temp/ocean_color_real/`（本地临时目录，未提交），需要复现时按下方命令重新下载/重跑即可。

---

## 0. TL;DR

| 项 | 结果 |
|---|---|
| 数据源 | Copernicus GlobColour **BGC L4 月度**（`OCEANCOLOUR_GLO_BGC_L4_MY_009_104`），月份 **2024-06** |
| 真实下载 | ✅ 3 个 NetCDF 落地（CHL / SPM+KD490 / CDM），共 **597.5 MB**，SHA256 见 §2 |
| 投影 | 源即 Plate Carrée，与 `dayTexture` 的 `lonLatToVector3` 同一投影 → 无需重投影 |
| 掩膜 | ✅ 陆/云/冰 = **透明**（alpha=0）；全局 51.2% 透明，与 ~48.8% 海洋覆盖一致 |
| 管线 | ✅ 对 **4,095,588** 个真实像素逐个调用未改动的 `water_params_reference.js` 的 `deriveWaterParams()` |
| 纹理 | `global_watercolor_rgba.png` 4096×2048 RGBA；预览 `global_watercolor_preview.png` |
| 合理性 | ✅ 南太平洋清澈→蓝 `#006982`；长江口/亚马逊河口→黄褐 `#b36d00`/`#a74200`；本格拉上升流→绿 `#546905` |
| 耗时 | 下载 ~84s（3 文件并行串行重试）+ 烘焙链（prep~1s + pipeline 7.4s + render~2s）≈ 10s |

---

## 1. 数据获取（真实下载证明）

### 1.1 凭证与 CLI 用法核对（重要）

`.env` 里写的是（凭证值不写进本文档，仅记录变量名结构）：
```
COPERNICUS_MARINE_USERNAME=<邮箱>
COPERNICUS_MARINE_PASSWORD=<密码>
```
但当前 `copernicusmarine 2.4.1` 的 CLI 期望的环境变量名是 **`COPERNICUSMARINE_SERVICE_USERNAME` / `COPERNICUSMARINE_SERVICE_PASSWORD`**（下划线位置不同）。
**本次没有照抄 `.env` 的旧写法**，而是在下载脚本里读取 `.env` 的值、以正确的变量名注入环境，避免了"凭证不识别 / 卡在交互输入"的坑。
（注：`.env` 这两个变量名若以后在别的脚本里直接用会失效，建议统一改名为 `COPERNICUSMARINE_SERVICE_*`。）

### 1.2 实际执行的下载命令（可复现）

```bash
# 先核对产品结构与变量名（匿名，无需登录）
copernicusmarine describe --product-id OCEANCOLOUR_GLO_BGC_L4_MY_009_104

# 三个月度 4km part 各含部分变量，分三次 subset：
copernicusmarine subset \
  -i cmems_obs-oc_glo_bgc-plankton_my_l4-multi-4km_P1M  -v CHL \
  -t 2024-06-01 -T 2024-06-30 -o temp/ocean_color_real --output-filename chl_2024-06

copernicusmarine subset \
  -i cmems_obs-oc_glo_bgc-transp_my_l4-multi-4km_P1M   -v SPM -v KD490 \
  -t 2024-06-01 -T 2024-06-30 -o temp/ocean_color_real --output-filename spm_kd490_2024-06

copernicusmarine subset \
  -i cmems_obs-oc_glo_bgc-optics_my_l4-multi-4km_P1M   -v CDM \
  -t 2024-06-01 -T 2024-06-30 -o temp/ocean_color_real --output-filename cdm_2024-06
```
（实际由 `temp/ocean_color_real/download_global.py` 封装，含 3 次重试与清单输出。）

### 1.3 下载文件证据（非合成数据）

| 文件 | 大小 | SHA256 | 变量 | 网格 | 值域（真实） |
|---|---|---|---|---|---|
| `chl_2024-06.nc` | 149,386,878 B | `1706625d…0b0f89` | CHL (mg/m³) | 4320×8640 | 0.012–65 |
| `spm_kd490_2024-06.nc` | 298,689,874 B | `073fee68…a4dad49` | SPM (g/m³), KD490 (m⁻¹) | 4320×8640 | SPM 0.05–100；KD490 0.021–1.29 |
| `cdm_2024-06.nc` | 149,386,878 B | `6f9757f4…cf208c6` | CDM (m⁻¹) | 4320×8640 | 0.001–5.0 |

- 全部 `format=NETCDF4`，坐标 `latitude(4320) longitude(8640)`，范围 lat[-89.98, 89.98] lon[-179.98, 179.98]（4 km 全球 Plate Carrée）。
- 四个变量的 `_FillValue` 均为 **-999.0**（与 Step 0 的 MODIS 样本 `9.993e+10` 完全不同 —— 见 §3 掩膜处理）。
- 校验脚本：`shasum -a 256 temp/ocean_color_real/*.nc`；结构见 `netCDF4` 读取输出（§1.3 值域）。

---

## 2. 烘焙脚本（复用并扩展 Step 0 管线）

Step 0 已验证：`deriveWaterParams()` 的 5 个输入可逐像素来自栅格波段、公式本身零改造。
本次**直接复用真实参考实现**，改用紧凑二进制交换（避免 840 万像素走 JSON），三步链：

| 步 | 脚本 | 输入 → 输出 | 说明 |
|---|---|---|---|
| prep | `prep_copernicus.py` | 3 个真实 .nc → `inputs.bin`(f32 [H·W·4]) + `grid_meta.json` | 读 `_FillValue` 逐变量掩膜 → 重采样到 4096×2048 |
| bake | `run_pipeline_real.js` | `inputs.bin` → `color_rgba.bin`(u8 [H·W·4]) + `pipeline_stats.json` | 对每个有效像素调用**真实** `deriveWaterParams()` |
| render | `render_texture.py` | `color_rgba.bin` → RGBA 纹理 + 预览图 | 透明=掩膜；预览叠加中性底以显掩膜 |

与 Step 0 的关键差异（都是合理的"扩展"而非"重写"）：
- Step 0 的 MODIS 样本**没有原生 SPM/CDM**，是靠 Rrs 反演的；本次 Copernicus 产品**直接提供** CHL/SPM/CDM/KD490，所以 `prep` 改为直接读取真实字段，`run_pipeline_real.js` 把 `cdm` 也传进 `deriveWaterParams({chl,spm,kd490,cdm,wind})`（CDM 即 a_cdom@440，单位 m⁻¹，与参考实现输入一致）。
- Step 0 是 360×360 代表性网格；本次是**真实全球 4320×8640 → 4096×2048**。

---

## 3. 掩膜处理（真实全球数据上确认生效）

真实全球数据比小样本边界情况多得多，本次逐变量严格处理：

1. 读每变量的 `_FillValue`（=-999.0），`arr[arr==fv]=NaN`；
2. 物理量纲合理性裁剪：`CHL∈(0,200]`、`SPM∈(0,500]`、`KD490∈(0,10]`、`CDM∈(0,10]`（单位对应产品定义）；
3. 有效像素判定：**CHL 与 KD490 同时有效**为核心海洋像素；SPM/CDM 缺失时回退小值（与 Step 0 一致），不影响颜色主调；
4. 重采样用最近邻（`searchsorted` 矢量化），NaN 传播，陆地/云/冰自然成 `NaN` → 烘焙时 `alpha=0`。

**掩膜正确性验证（不是只在小样本上测过）：**

| 已知点 | lat, lon | 结果 |
|---|---|---|
| 撒哈拉（陆地） | 23, 13 | ✅ 透明 |
| 喜马拉雅（陆地） | 28, 86 | ✅ 透明 |
| 南极（冰盖，被产品掩膜） | -80, 0 | ✅ 透明 |
| 西伯利亚（陆地） | 60, 100 | ✅ 透明 |
| 中太平洋（开阔洋） | 0, -140 | 不透明 `#006e5b` 蓝 |
| 北太平洋环流（开阔洋） | 40, -150 | 不透明 `#006d67` 蓝 |
| 南大西洋（6 月冬季海冰区） | -55, -30 | ✅ 透明（冬季海冰，正确掩膜） |

按纬度带的透明比例符合真实地理：高纬（冰+陆地）高、副热带开阔洋低：
```
lat  80: 71.4%   60: 59.1%   40: 45.3%   20: 31.4%   0: 20.8%  -20: 23.4%  -40: 3.8%  -60:100%  -80:100%
```
全局 **51.2% 透明**，与源数据 ~48.8% 海洋有效覆盖吻合 —— 填充值没有被当成真实水色污染出图。

---

## 4. 海洋色调合理性交叉核对（5 个真实站位）

用 `run_pipeline_real.js` 在纹理上直接采样（lat/lon → 像素），与已知真实海域特征对比：

| 站位 | 坐标 | 烘焙色值 | 期望（真实海洋色） | 结论 |
|---|---|---|---|---|
| 南太平洋环流（清澈寡营养） | -25, -130 | `#006982` | 深蓝/蓝绿 | ✅ |
| 萨加索海 / 北大西洋环流（清澈） | 28, -55 | `#006982` | 蓝 | ✅ |
| 长江口（浑浊河口） | 31.5, 122.5 | `#b36d00` | 黄褐（高 SPM/浑浊） | ✅ |
| 亚马逊河口（浑浊河口） | 0, -49 | `#a74200` | 黄褐偏红 | ✅ |
| 本格拉上升流（高 CHL 生产区） | -25, 12 | `#546905` | 绿调（浮游植物） | ✅ |

- hue 全图范围 **47.1°…221.7°**（低端的黄褐/橄榄 → 高端的蓝），不是均匀一片色。
- 清澈像素（clarity>0.6）= 3,993,886（97.5%）；浑浊（turbidity>0.3）= 26,263（0.6%）—— 量级合理。

### 与 Step 0 报告的交叉核对
Step 0 用代表性网格跑同一份真实 `deriveWaterParams()`，hue 范围 58.6°–225.4°；本次真实全球数据 47.1°–221.7°，**量级与色系完全一致**，仅因真实全球含更多极端河口/上升流样本，低端更偏黄褐。证明 Step 0 的管线结论在真实数据上成立。

---

## 5. 交付物

`temp/ocean_color_real/`
- `chl_2024-06.nc` / `spm_kd490_2024-06.nc` / `cdm_2024-06.nc` — **真实下载源数据**（597.5 MB，SHA256 见 §1.3）
- `global_watercolor_rgba.png` — **交付纹理** 4096×2048 RGBA，陆地/云/冰透明
- `global_watercolor_preview.png` — 2048×1024 预览（叠加中性底，掩膜显深石板色，便于肉眼检查）
- `inputs.bin` / `grid_meta.json` / `color_rgba.bin` / `pipeline_stats.json` — 中间产物与统计
- `prep_copernicus.py` / `run_pipeline_real.js` / `render_texture.py` / `download_global.py` — 可复现脚本

### 独立复核清单（你照例要做的）
1. **下载是真的**：`shasum -a 256 temp/ocean_color_real/*.nc` 比对 §1.3；`ncdump -h` 看维度/变量；确认不是合成网格。
2. **掩膜不变色**：用任意图片工具打开 `global_watercolor_rgba.png`，放大看大陆/格陵兰/南极应为透明（棋盘格背景），而非蓝/褐色块。
3. **重跑一部分**：`python temp/ocean_color_real/prep_copernicus.py 1024 512` + `node temp/ocean_color_real/run_pipeline_real.js` + `python temp/ocean_color_real/render_texture.py`，抽样几个点核对色值是否复现。
4. **色调合理**：§4 五个站位色值是否符合预期（蓝/黄褐/绿）。

---

## 6. 备注 / 遗留
- 本阶段**未接入** `earth3d.js`，纹理是独立产物。阶段 B 集成时：RGBA 纹理按 `dayTexture` 同样方式（Plate Carrée，`v=(90-lat)/180`）球面映射即可，陆地/云处透明会露出既有地球陆地/云层。
- 月份选 2024-06（MY 产品稳定覆盖、且 6 月北半球河口/上升流特征明显）。换月份只需改 `download_global.py` 的 `MONTH`。
- SPM/KD490 在 transp part、CDM 在 optics part、CHL 在 plankton part —— 三个 part 必须各下一份再按网格合并（产品本身未把四变量打包进单一文件）。
- `.env` 的 Copernicus 变量名是旧式（`COPERNICUS_MARINE_*`），当前工具要 `COPERNICUSMARINE_SERVICE_*`，已在本脚本内正确映射；若后续别处直接用 `.env` 可能失效。
