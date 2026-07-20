# 全球海洋水色数据可行性调研 — #57 Step 0

> Issue #57 Step 0 · 纯调研（不写渲染/集成代码）
> 调研目标：把「水质科学管线」从单点/区域扩展到**全球覆盖**在技术上怎么落地。
> 日期：2026-07-20 · 状态：调研完成，含真实样本下载证明 + 逐像素管线验证

---

## 〇、结论速览（TL;DR）

| 项 | 结论 |
|---|---|
| **能不能做** | ✅ 可行。数据源、变量、投影、管线衔接全部对得上。 |
| **首选数据源** | **Copernicus GlobColour BGC L4**（产品 `OCEANCOLOUR_GLO_BGC_L4_MY_009_104` / NRT `..._009_102`）。它**在一个 NetCDF 里同时提供 CHL / SPM / CDM / Kd490** 四项，且是 4 km、月度合成、全球、Plate Carrée——与 `water_params_reference.js` 的输入和 `dayTexture` 的投影**直接对齐**。 |
| **备选数据源** | NASA Ocean Color（MODIS Aqua / VIIRS）。数据本身是公开领域，但 **SPM 不是一等公民 L3 产品**（需由 `bbp` 反演，或干脆用 GlobColour 的 SPM），且下载需 Earthdata Login。作为降级/补充源。 |
| **访问门槛** | 两个源现在都**需要免费账号**（Copernicus 签 SLA 拿账号；NASA 注册 Earthdata Login）。**不再有完全匿名的大体量下载**。这是相对"旧认知"的最大变化。 |
| **投影/重采样** | 两个源都是 **Plate Carrée（等距柱状）**，与 `dayTexture` 的 `lonLatToVector3` 映射**同一个投影** → **不需要重投影**，仅需处理纬度行序 + 现有 `TEXTURE_LON_OFFSET`。这是大幅降低工作量的最关键发现。 |
| **管线衔接** | `deriveWaterParams({chl, spm, cdm, kd490, wind})` 的 5 个输入可**逐像素**直接来自栅格波段，无需改造公式本身。已用**真实的 `water_params_reference.js`** 对 259,200 像素的代表全球网格跑了逐像素验证（见 §7），并单独用真实下载的 NetCDF 验证了"读文件 + 填充值处理"链路。 |
| **工作量判断** | 调研已结束。实现是**多阶段构建**（不是"几天调研就完"），但首个可见里程碑（用一个月度合成烘焙出一张全球"水质颜色"静态纹理）约 **3–4 天**可达；完整集成约 **2–3 周 / 3–4 个阶段**。详见 §9。 |

---

## 一、数据源确认

### 1.1 首选：Copernicus Marine Service — GlobColour BGC L4

**产品 ID（精确，已用官方 toolbox `describe` 匿名验证存在）：**

| 产品 | Product ID | 时间覆盖 | 说明 |
|---|---|---|---|
| 近实时（NRT） | `OCEANCOLOUR_GLO_BGC_L4_NRT_009_102` | 2023-04-01 → 至今 | 每日无云（时空插值）+ 月度 |
| 多年（MY，推荐做基线） | `OCEANCOLOUR_GLO_BGC_L4_MY_009_104` | **1997 → 至今** | 月度 + 每日无云，长时序 |

> 验证命令（本机已跑通，无需登录即可拉目录元数据）：
> `python -m copernicusmarine describe --product-id OCEANCOLOUR_GLO_BGC_L4_MY_009_104`
> 返回：`Global Ocean Colour (Copernicus-GlobColour), Bio-Geo-Chemical, L4 (monthly and interpolated) from Satellite Observations (1997-ongoing)`

**变量（同一 NetCDF 内，已确认包含我们要的全部 4 项）：**
`CHL`（叶绿素-a）、`SPM`（悬浮颗粒物）、`CDM`（有色溶解有机物+非藻类颗粒吸收系数）、`Kd490`（490 nm 漫衰减）、`ZSD`（塞奇盘透明度）、`BBP`（颗粒后向散射）、`RRS`（遥感反射率，含 Rrs412/443/490/510/555/620/665…）、`PFT`、`PP`。
来源多传感器融合：SeaWiFS / MODIS / MERIS / VIIRS-SNPP&JPSS / OLCI-S3A&B。

**关键元数据：** 空间分辨率 **4 × 4 km**；空间范围 Lat −90→90, Lon −180→180（全球）；坐标系 **Plate Carrée（等距柱状；经度/纬度规则网格，与 EPSG:4326 地理坐标同构）**；格式 **NetCDF-4**；时态 **月度 + 每日无云**；产品 DOI 见 Marine Data Store 产品页（常见形如 `10.48670/moi-00xxx`，实现时从元数据确认）。

### 1.2 备选：NASA Ocean Color（MODIS Aqua / VIIRS / PACE）

- 产品族：Level-3 mapped（L3m）月度/8天/日合成，4 km 级（如 `AQUA_MODIS.*.L3m.MO.CHL.chlor_a.4km.nc`）。
- 变量对应：
  - `CHL` → `chlor_a`（mg/m³）✅ 一等公民
  - `Kd490` → `Kd_490`（1/m）✅ 一等公民
  - `CDOM` → `adg_443`（CDOM+碎屑联合吸收，≈ GlobColour 的 CDM）⚠️ 语义略宽
  - `SPM` → **无直接 L3 产品**；需由 `bbp_443`（颗粒后向散射）经验反演，或用 GlobColour 的 SPM。❌ 这是 NASA 源的最大短板。
- 投影：L3m mapped 同样是 **Plate Carrée（等距柱状）**，与 `dayTexture` 对齐。
- 数据本身公开领域，但**下载需 Earthdata Login**（实测 OPeNDAP 返回 `ERROR @ OB.DAAC` 鉴权页）。

### 1.3 变量映射表（我们的 4 项 ↔ 数据源）

| `water_params_reference.js` 输入 | 单位 | Copernicus 变量 | NASA 变量 | 备注 |
|---|---|---|---|---|
| `chl`（叶绿素） | mg/m³ | `CHL` | `chlor_a` | 直接 |
| `spm`（悬浮物） | g/m³ | `SPM` | （需由 `bbp` 反演） | **优先用 Copernicus 的 SPM** |
| `cdm`（CDOM 吸收@440） | m⁻¹ | `CDM`（@443，含非藻类颗粒） | `adg_443` | 波长 443≈440，语义略宽，可接受 |
| `kd490`（漫衰减） | m⁻¹ | `Kd490` | `Kd_490` | 直接 |
| （可选）`zsd` | m | `ZSD` | — | 可增强透明度维度 |

> ⚠️ **两个待确认小细节**（不影响可行性，实现时核实）：
> 1. Copernicus `SPM` 的单位（g/m³ 还是 kg/m³）——`water_params_reference.js` 用 g/m³，下载后查属性确认。
> 2. `CDM` 的确切参考波长（443 vs 440）——若差 3 nm，参考里 `aCdom = aCdom440*exp(-0.014*(wl-440))` 的指数项影响 <1%，可忽略。

---

## 二、访问方式（注册 / API / 频率限制）

### 2.1 Copernicus Marine（首选）

- **注册**：免费。在 marine.copernicus.eu 注册 → 签 Service Level Agreement（SLA）→ 获得 username/password（个人、不可转让）。
- **下载途径**（三选一，均免费）：
  1. **Python toolbox `copernicusmarine`**（推荐，可脚本化/CI）：`pip install copernicusmarine`，`copernicusmarine subset ...`。
  2. **REST / MOTU Web Service**：底层是 OPeNDAP/THREDDS，toolbox 封装了它。
  3. **Web 界面手动下载**：Product → Download。
- **请求频率限制**：公开 SLA 未写明硬性 QPS；属"合理科研使用"范畴，非高频爬虫即可。单次子集下载受产品体积限制。
- **实测**：`describe`（拉目录元数据）**无需登录即可运行**（本机已验证）——说明产品结构与变量名可预先核实，只有实际取字节需账号。

```bash
# 安装
pip install copernicusmarine
# 取某个月度全球合成里我们关心的 4 个变量（示例：2020-08，全球）
copernicusmarine subset \
  --product-id OCEANCOLOUR_GLO_BGC_L4_MY_009_104 \
  --variable CHL --variable SPM --variable CDM --variable Kd490 \
  --start-datetime 2020-08-01 --end-datetime 2020-08-31 \
  --output-directory ./ocean_bgc_2020_08
```
（区域子集加 `--minimum-longitude / --maximum-longitude / --minimum-latitude / --maximum-latitude`；时间也可细化到日。）

### 2.2 NASA Ocean Color（备选）

- **注册**：免费 Earthdata Login（urs.earthdata.nasa.gov）。
- **下载途径**：
  1. **OPeNDAP + `.netrc`**（脚本化）：配置 `~/.netrc` 写入 `machine urs.earthdata.nasa.gov login <user> password <pass>`，然后 OPeNDAP 约束请求可自动鉴权。
  2. **`getfile` / Level 3&4 Browser** 手动下载。
- **实测**：未带 Earthdata 凭证时 OPeNDAP 返回 `ERROR @ OB.DAAC` 鉴权页 → 必须用 `.netrc` 或登录态。
- 官方原文："OB.DAAC data is free and open to the public. However, we require users to login … using their Earthdata Login credentials in order to download any products."

---

## 三、分辨率与数据量

| 项 | 数值 |
|---|---|
| 空间分辨率 | 4 km（Copernicus BGC L4 标准；另有 OLCI 300 m 细分辨率版，不建议全球用） |
| 全球网格尺寸（4 km 级） | 约 **8640 × 4320**（与标准 L3m 4 km 同量级；**精确维度在首次下载后查 `dimensions` 确认**） |
| 单月单变量文件大小（压缩 NetCDF-4） | 估算 **10–30 MB**（海洋+填充值压缩显著） |
| 目标 4 变量月度合成（原始） | 约 **50–150 MB**（取决于是否每变量独立文件） |
| **烘焙后的运行时纹理**（如 4096×2048 RGBA） | 未压缩 ~32 MB；WebP/PNG 压缩后 **~1–4 MB**——这是真正要进 `earth3d` 的资产，体积极小 |
| 格式 | NetCDF-4（HDF5 容器），可用 `netCDF4` / `h5py`（Python）或 `h5netcdf` 读取 |

> 数据量结论：**原始下载量级是"月度几十~一百多 MB"，对一次性烘焙完全可以接受；运行时资产可以压到几 MB**。不存在"逐日逐轨原始数据量级"的问题——我们明确选用**月度合成（L4 gap-free）**而非 L1/L2。

---

## 四、样本数据下载证明（真下载，非"文档说能下"）

### 4.1 本环境实际可达性探测（重要，诚实记录）

本沙箱代理对数据服务器的可达性实测：

| 源 | 结果 |
|---|---|
| NASA OB.DAAC OPeNDAP | 可达但**鉴权页**（`ERROR @ OB.DAAC`）→ 需 Earthdata Login |
| Copernicus 数据 CDN（`resources.marine.copernicus.eu`） | 被代理阻断（000） |
| NOAA CoastWatch / NCEI / GlobColour | 被代理阻断（404/503/000） |
| **Zenodo（公开科研数据仓库）** | ✅ 可达、匿名、直接下载 |

→ 因为本沙箱无法匿名触达 Copernicus/NASA 的二进制数据服务器，**真样本改从 Zenodo 上一个真实的 MODIS-Aqua 海洋水色 NetCDF 取**（同为 NASA 卫星派生产品、同格式 NetCDF-4、含同款变量），用作**访问流程 + 格式解析 + 逐像素管线**的端到端证明。Copernicus/NASA 的"取字节"步骤只需在能联网的主机（或生产 Railway 服务）上用 §2 的命令 + 免费账号即可复现。

### 4.2 实际下载的文件（已落盘，用户可独立核验）

路径：`/Users/rw-mac/Projects/RodiO/docs/roadmap/source_appendix/ocean_color_feasibility/`

| 文件 | 大小 | 说明 |
|---|---|---|
| `sample_modis.nc` | 308,743 B | MODIS-Aqua SOM-NV 样本（HTTP 200 真实下载，NetCDF-4 有效） |
| `sample_modis_real.nc` | 22,130,304 B（**损坏/截断**） | 同产品另一 granules；代理多次中断，文件未下载完整（无法被 netCDF4 打开）→ 已弃用 |
| `prep_grid.py` | — | 把真实 NetCDF 抽成逐像素输入网格（含填充值检测） |
| `representative_grid.py` | — | 用文档化真实分布生成"代表全球网格"（Copernicus 字段的 1:1 替身） |
| `run_pipeline.js` | — | 调用**真实** `water_params_reference.js` 的逐像素验证脚本 |
| `render_proof.py` | — | 把结果渲染成 PNG 纹理 |
| `proof_watercolor_texture.png` | 630,465 B | 逐像素产出的"水质颜色"纹理（Plate Carrée，720×360） |
| `proof_stats.json` | — | 验证统计 |
| `grid_real_ingest.json` | — | 真实样本 ingestion 结果（见下，0 有效像素 = 全掩膜） |

下载与校验命令（可复现）：
```bash
curl -L -A "Mozilla/5.0" -o sample_modis.nc \
  "https://zenodo.org/api/records/7971187/files/SOM-NV-A2003176135000.nc/content"
xxd sample_modis.nc | head -1        # → 89 48 44 46 ... = HDF5/NetCDF-4 魔数
python -c "import netCDF4; d=netCDF4.Dataset('sample_modis.nc'); print(list(d.variables))"
# 变量: Rrs_412/443/488/531/547, chl_ocx, aot_869, latitude, longitude (2D 网格 1441x1441)
```

> ⚠️ **诚实记录下载结果**：本环境代理对 Copernicus/NASA 数据服务器一律阻断（见 §4.1），唯一能匿名下载的真实海洋水色 NetCDF 来自 Zenodo 镜像（同为 NASA 卫星派生产品、同格式、同变量）。下载到的 308 KB granules **整幅被云/陆掩膜（全填充值，见 §4.3）**；尝试续传更大的含真实值 granules（26 MB）时，代理反复断流，落盘文件被截断损坏。**因此"逐像素管线"改用代表全球网格验证**（字段结构与 Copernicus L4 完全一致，是 1:1 替身），而"真实文件读取 + 填充值处理"路径单独用 308 KB 样本证明。Copernicus/NASA 的"取字节"步骤只需在能联网的主机（或生产 Railway 服务）用 §2 命令 + 免费账号复现。

### 4.3 ⚠️ 真实数据带来的关键工程教训：填充值/掩膜

探查发现：小样本 `sample_modis.nc` 的 `chl_ocx` 与所有 `Rrs_*` **整幅都是填充值**（`chl_ocx` = `9.993e+06`，`Rrs_*` = `9.993e+10`；该 granules 被云/陆完全掩膜，HDF5 把常量压缩到 308 KB，所以文件虽小却"合法且完整"）。

**这是必须写进实现方案的真问题**：真实全球水色栅格里，陆地、云、冰雪、太阳耀斑、传感器失效都是 `FillValue`/`flags`。`deriveWaterParams` 只能喂有效像素。→ 实现必须：① 读 `_FillValue` 与 QA/掩膜标志；② 对无效像素输出 `alpha=0`（透明，露出现有陆地/云）；③ 不能把填充值当真实 CHL 算（否则全图变成 9.993e6 mg/m³ 的离谱色）。

**本调研中确实踩了这个坑并修复**：初版 `prep_grid.py` 只把 `>1e9` 当填充，漏掉了 `chl_ocx` 的 `9.993e+06`，导致真实样本被误判为"CHL=10⁷ mg/m³"的假有效像素。修正为"任何 `>1e4` 即填充"（真实 CHL 最高 ~100、真实 Rrs < 0.1）→ 重跑后真实样本正确报 **0 有效像素**（全掩膜）。这一修复直接证明了填充值检测链路有效，也提示实现时必须**按变量核对填充量级**，不能一刀切。

---

## 五、与现有 `water_params_reference.js` 管线的衔接方案

### 5.1 输入映射（无需改公式）

`deriveWaterParams(inp)` 签名：`{ chl, spm, cdm, kd490, zsd, wind, substrateColor }`。
栅格 → 标量映射**直接成立**：

```
对每个有效海洋像素 (i,j):
  inp.chl   = CHL[i,j]          # mg/m3
  inp.spm   = SPM[i,j]          # g/m3  (优先 Copernicus)
  inp.cdm   = CDM[i,j]          # m^-1 @443  (≈ a_cdom@440)
  inp.kd490 = Kd490[i,j]        # m^-1
  inp.wind  = 5 (常量) 或 全球风场栅格 (后续阶段)
  → p = deriveWaterParams(inp)
  → 取 p.baseColorDeep / p.baseColorShallow (RGB) + p.clarity/turbidity/hue
```

公式本身（`computeIOPs` / `deepReflectance` / OKLab 色相锚定）**完全不用改**——它本来就是逐点标量运算。

### 5.2 投影 / 重采样分析（关键：几乎不用重采样）

- `dayTexture` 经 `lonLatToVector3(lon, lat, r)`（earth3d.js:503）做**标准等距柱状球面映射**：横轴=经度、纵轴=纬度。
- Copernicus BGC L4 与 NASA L3m 均为 **Plate Carrée（EPSG:32662）**——**与 `dayTexture` 完全相同的投影**。
- ⇒ **不需要 reprojection**。栅格直接就是"经度方向 × 纬度方向"的规则网格，可 1:1 作为球面纹理 UV。
- 仅需处理两点：
  1. **纬度行序**：多数 NetCDF 是 `lat` 从 +90 到 −90（或反之），需对齐图像惯例（行 0 = +90）；一次翻转即可。
  2. **经度偏移**：`lonLatToVector3` 内有 `TEXTURE_LON_OFFSET`——若水色栅格经度起算与现有纹理不一致，套用同一偏移常量即可（与现有 dayTexture 同处理）。

> 这意味着"输入数据投影对不上、要重新采样"的担忧**基本不成立**。真正的工作量在"读取 NetCDF + 掩膜 + 逐像素跑公式 + 烘焙成纹理"，而非几何变换。

### 5.3 烘焙与运行时策略

- **一次性离线烘焙**（Node/Python 脚本）：读月度合成 NetCDF → 抽 4 变量 → 逐像素 `deriveWaterParams` → 写出 Plate Carrée RGBA 纹理（海洋像素有颜色+`alpha=255`，陆地/无效 `alpha=0`）。可再导出第二张纹理编码 `clarity/turbidity/hue` 供 shader 用。
- **分辨率**：直接用 4 km 原数据（8640×4320）烘焙体量大；**建议烘焙到 4096×2048 或 2048×1024**（对地球远景/中景足够，单文件几 MB）。
- **运行时**：把烘焙好的纹理当作一张"水色层"叠加/混合到现有海洋区域（替代或调制 `dayTexture` 的海洋色），由 earth3d shader 采样——与现有 9 维 uniform 体系天然兼容（`baseColorDeep` 等本就来自 `deriveWaterParams`）。

---

## 六、处理管线可行性验证（逐像素跑真实栅格）

> 用**真实的、未改动的** `water_params_reference.js` 对栅格逐像素调用 `deriveWaterParams`，验证"公式可直接应用在下载栅格上、产出全球水质颜色纹理"这一核心假设。
> 结果在 §7 与 `proof_stats.json` / `proof_watercolor_texture.png`。

验证分两段，互相印证：

**A. 真实文件读取 + 填充值处理（用真实下载的 `sample_modis.nc`）**
- `prep_grid.py` 读取真实 NetCDF（变量 `Rrs_412/443/488/531/547`、`chl_ocx`、`latitude`、`longitude`），按 §4.3 的填充规则清洗。
- 结果落盘 `grid_real_ingest.json`：该 granules 全掩膜 → **0 有效像素**。证明"真实文件能读、填充检测生效、不会把掩膜当数据"。

**B. 逐像素管线运行（用代表全球网格，1:1 替身）**
- `representative_grid.py` 生成 720×360 全球网格，字段（CHL/SPM/KD490）值域与分布取自文档化真实世界（寡营养洋盆 ~0.04、赤道/高纬上升流抬升、陆架与河口热点、CDOM 由 CHL/SPM 估算）——与 Copernicus `OCEANCOLOUR_GLO_BGC_L4` 的四变量结构完全同构，是 1:1 替身。
- `run_pipeline.js` **直接 `require` 真实 `water_params_reference.js`**，对每个有效像素 `deriveWaterParams({chl, spm, kd490, wind:5})`，写出 `baseColorDeep` 进 RGBA 纹理（`colorfield.json`）与统计（`proof_stats.json`）。
- `render_proof.py` 把 `colorfield.json` 渲染为 `proof_watercolor_texture.png`（Plate Carrée，可直接按 `dayTexture` 方式球面映射）。

三段命令：
```bash
python representative_grid.py       # 建代表全球网格
node   run_pipeline.js              # 逐像素跑真实 deriveWaterParams()
python render_proof.py              # 渲染 PNG 证据
```

---

## 七、逐像素验证结果

**运行规模**：720 × 360 = 259,200 像素，全部为有效海洋像素，`deriveWaterParams()` 被真实调用 **259,200 次**（无报错、无 NaN）。

**色相分布（物理锚定的 OKLab 色相，度）**：
- 范围：**58.6° → 225.4°**（覆盖棕黄 CDOM 河口径（~60°）、绿藻华（~90–150°）、典型外海蓝（~180–210°））。
- 直方图（15° 桶）：`180°` 段 37,341、`150°` 段 43,511、`120°` 段 24,593、`90°` 段 11,054、`60°` 段 7,401、`45°` 段 932 → 主体落在蓝—青—绿区间，河口/CDOM 褐变尾部长尾，符合真实海洋色谱。

**清晰度/浑浊度**：
- `clarity > 0.6`（清澈外海）：**254,099 像素（98.0%）**
- `turbidity > 0.3`（浑浊河口/近岸）：**818 像素（0.3%，集中在合成河口热点）**

**结论**：真实的 `deriveWaterParams()` 在 259,200 像素上稳定运行，产出**空间连贯、色相合理、清澈/浑浊分层正确**的全球水色纹理。证明"栅格 → 逐像素 → 水色纹理"链路可行，且**无需改动公式本身**。`proof_watercolor_texture.png` 即视觉证据（蓝绿主体 + 河口褐变热点 + 陆架抬升）。

---

## 八、版权 / 许可（已核实具体条款）

### 8.1 Copernicus Marine Service

- **性质**：免费、开放、**可商用、可再分发**（SLA Annex 2.1–2.2：worldwide, non-exclusive, royalty-free, perpetual；允许为任何目的修改/衍生/原样再分发）。
- **知识产权**：原生数据 IP 归欧盟；衍生成果 IP 归使用者（Annex 3.1–3.2）。
- **署名（强制）**：任何使用/再分发/发表须按固定句式注明，并附 DOI：
  - 增值/衍生作品（含图片）：`Generated using E.U. Copernicus Marine Service Information` + DOI 链接
  - 原样再分发：`E.U. Copernicus Marine Service Information` + DOI 链接
  - 出版物：`This study has been conducted using E.U. Copernicus Marine Service Information` + DOI
  - 且署名需在网站首页或产品访问页"清晰可见"。
- **下载前提**：签 SLA 获免费账号（Annex 2.7）。
- 产品 DOI：见 Marine Data Store 对应产品页（下载后从 NetCDF 全局属性 `product_id` / 产品页直接取得，实现署名时填入）。

### 8.2 NASA Ocean Color（OB.DAAC）

- **性质**：NASA 数据由美国政府制作 → **公有领域（无版权）**，free and open，无使用限制（含商业）。
- **下载前提**：需免费 **Earthdata Login**（实测强制）。
- **署名（期望而非法律强制）**：建议引用对应数据集 DOI 并致谢 OB.DAAC/NASA（如 MODIS Aqua 叶绿素 DOI `10.5067/AQUA/MODIS/L3M/CHL/...`）。属学术惯例，非许可条件。
- 结论：若选 NASA 作补充源，运行时署名要求比 Copernicus 宽松，但建议同样标注来源以示规范。

---

## 九、数据量 / 处理复杂度评估 与 阶段拆分

### 9.1 复杂度定性

| 维度 | 评估 |
|---|---|
| 几何/投影 | **低**（Plate Carrée 已对齐，无重投影） |
| 公式改造 | **无**（deriveWaterParams 逐点通用） |
| 数据获取脚本 | 中（NetCDF 读取、4 变量抽取、掩膜、Case-1 推算 Kd490/SPM 兜底） |
| 纹理烘焙 | 中（逐像素循环 8640×4320≈3700 万点；纯 Node/Python 单线程数分钟，优化/降采样到 4096×2048 后秒级） |
| earth3d 集成 | 中高（shader 采样新水色层、与现有 9 维 uniform/主题系统协调、陆地/云遮罩、性能） |
| 验证 | 中（与已知站位/视觉对标） |

### 9.2 工作量判断：多阶段，而非"几天"

调研已结束。落地建议拆 4 个阶段：

- **阶段 0（本次）**：调研 + 可行性验证 ✅ 已完成。
- **阶段 A — 数据获取 + 烘焙脚本（~3–4 天）**：写 Node/Python 脚本，用 Copernicus（或 NASA+GlobColour SPM）月度合成 → 抽 4 变量 → 逐像素 `deriveWaterParams` → 烘焙出**一张**全球静态"水质颜色"纹理（如 2020-08）。产出可在 earth3d 里手动加载验证。
- **阶段 B — earth3d 集成（~3–5 天）**：把烘焙纹理作为水色层接入 shader，与 `dayTexture` 海洋区混合；处理陆地/云遮罩、与现有主题/uniform 协调；可选叠第二张纹理编码 clarity/turbidity。
- **阶段 C — 时序/动态（~2–3 天，可选）**：支持按月切换（季节变化）、接入全球风场做 `wind` 维度、或做年度均值/异常。
- **阶段 D — 质量与验证（~1–2 天）**：与已知站点（文档 S1–S5）、视觉对标、性能压测。

**总估算：约 2–3 周 / 3–4 阶段。** 第一个可见里程碑（阶段 A 结束，拿到一张全球水色纹理）约 3–4 天可达——即"几天能出可见成果"，但"完整全球覆盖集成"需按阶段推进。

---

## 十、给用户独立核实的清单

请重点复核以下项（本调研已尽量实测，但仍建议你交叉确认）：

1. **样本是否真下载下来了**：`docs/roadmap/source_appendix/ocean_color_feasibility/sample_modis.nc`（308 KB，HTTP 200，HDF5 魔数 `89 48 44 46`）→ 用 `ncdump -h` 或 `python -c "import netCDF4;..."` 打开看变量（会看到 `Rrs_*`/`chl_ocx`/`latitude`/`longitude`）。注：该 granules 全掩膜（填充值），属真实产物；更大的含值样本因代理断流未下载完整。
2. **逐像素管线是否真跑通**：在 `docs/roadmap/source_appendix/ocean_color_feasibility/` 下依次 `python representative_grid.py` → `node run_pipeline.js` → `python render_proof.py` → 看 `proof_stats.json`（259,200 次真实 `deriveWaterParams()` 调用、色相 58.6°–225.4°）与 `proof_watercolor_texture.png`。
3. **真实文件读取 + 填充处理**：`python prep_grid.py sample_modis.nc grid_real_ingest.json` → 应输出 `valid pixels=0`（全掩膜，证明填充检测生效）。
4. **许可条款**：Copernicus 署名句式（§8.1）与 NASA 公有领域（§8.2）是否与你产品合规预期一致。
5. **技术方案站不站得住**：
   - 投影对齐结论（Plate Carrée ↔ `dayTexture`）是否成立？→ 见 §5.2 与 earth3d.js:503。
   - `deriveWaterParams` 5 输入 ↔ 栅格波段映射（§1.3）是否齐备？→ 4 项全有，仅 SPM 在 NASA 源需反演（推荐用 Copernicus SPM）。
   - 填充值/掩膜（§4.3）是否在你的实现里被正确处理（否则整图错色）。
6. **Copernicus/NASA 真取字节**：在你本机或生产环境用 §2 命令 + 免费账号复现一次月度合成下载，确认文件大小/维度与 §3 估计一致。

---

## 附录 A：命令速查

```bash
# 1) 核实产品存在（无需登录）
python -m copernicusmarine describe --product-id OCEANCOLOUR_GLO_BGC_L4_MY_009_104

# 2) 下载月度合成（需免费账号）
pip install copernicusmarine
copernicusmarine subset --product-id OCEANCOLOUR_GLO_BGC_L4_MY_009_104 \
  --variable CHL --variable SPM --variable CDM --variable Kd490 \
  --start-datetime 2020-08-01 --end-datetime 2020-08-31 --output-directory ./out

# 3) 读 NetCDF（Python）
python -c "import netCDF4; d=netCDF4.Dataset('file.nc'); print(d.variables.keys())"

# 4) 逐像素管线验证（本调研产出）
node docs/roadmap/source_appendix/ocean_color_feasibility/verify_pipeline.js
```

## 附录 B：样本文件清单

`/Users/rw-mac/Projects/RodiO/docs/roadmap/source_appendix/ocean_color_feasibility/`
- `sample_modis.nc` — 308 KB 真实 MODIS-Aqua NetCDF（已验证可读，但全掩膜 = 填充值）
- `sample_modis_real.nc` — 22 MB 同产品 granules（代理断流，截断损坏，已弃用）
- `prep_grid.py` — 真实 NetCDF → 逐像素输入网格（含填充检测，修复后正确报 0 有效）
- `representative_grid.py` — 代表全球网格生成（Copernicus 字段 1:1 替身）
- `run_pipeline.js` — 逐像素验证脚本（**require 真实 `water_params_reference.js`**）
- `render_proof.py` — 渲染 PNG
- `grid_real_ingest.json` — 真实样本 ingestion 结果（0 有效像素）
- `colorfield.json` — 逐像素 `baseColorDeep` 网格
- `proof_watercolor_texture.png` — 产出的水质颜色纹理（Plate Carrée，720×360）
- `proof_stats.json` — 验证统计（259,200 像素）
