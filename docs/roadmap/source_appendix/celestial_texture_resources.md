# 天体系统 — Step 0：真实影像资源采集报告

> **任务范围**：#53/#54 天体系统 Phase 1 资源预置（独立一步，纯资源采集，不涉及轨道计算或渲染集成）
> **产出日期**：2026-07-20
> **验证状态**：✅ 原 14 个贴图文件已下载、RGB 实测；✅ 补充资源（太阳 + 木星/天王星/海王星环 + 月球 2K 升级）均已完成下载、实测并落地（详见第 8–10 节）

---

## 1. 总览表

| # | 天体 | 文件名 | 探测器 | NASA 图像编号 | 拍摄年份 | 版权状态 | 实测代表色 (R,G,B) | HEX |
|---|------|--------|--------|--------------|---------|----------|---------------------|-----|
| 1 | 水星 Mercury | `mercury_messenger_truecolor.jpg` | MESSENGER | 全球增强彩镶嵌图 | ~2011–2015 | NASA 公共领域 (PD) | (132, 129, 129) | `#848081` |
| 2 | 金星 Venus | `venus_mariner10_truecolor.jpg` | Mariner 10 | 经典云顶真彩图 | 1974 | NASA PD | (208, 206, 204) | `#D0CECC` |
| 3 | 火星 Mars | `mars_truecolor.jpg` | Viking / MRO | 全球真彩镶嵌 | ~1990s–2000s | NASA PD | (138, 105, 75) | `#8A694B` |
| 4 | 木星 Jupiter | `jupiter_pia01369.jpg` | **Voyager 2** | **PIA01369** | 1979 (重制 1998) | NASA PD | (172, 121, 68) | `#AB7944` |
| 5 | 土星 Saturn | `saturn_truecolor.jpg` | **Cassini** | **PIA12513** ("Stately Saturn") | 2009 | NASA PD | (119, 111, 82) | `#776F52` |
| 6 | 天王星 Uranus | `uranus_pia18182.jpg` | **Voyager 2** | **PIA18182** | 1986 | NASA PD | (180, 217, 221) | `#B3D9DD` |
| 7 | 海王星 Neptune | `neptune_pia01492.jpg` | **Voyager 2** | **PIA01492** (绿+橙滤光拼接) | 1989 (重制 1998) | NASA PD | (51, 72, 175) | `#3348AF` |
| 8 | 冥王星 Pluto | `pluto_pia19708.jpg` | **New Horizons** | **PIA19708** ("Big Heart in Color") | 2015-07-13 | NASA PD | (173, 141, 112) | `#AC8D70` |
| 9 | 木卫一 Io (主图) | `io_truecolor.jpg` | **Voyager 1** | **PIA00318** (~自然色镶嵌) | 1979 (重制 1998) | NASA PD | (163, 129, 76) | `#A3814C` |
| 10 | 木卫二 Europa | `europa_pia19048.jpg` | **Galileo** | **PIA19048** | 1996–1999 (重制 2014) | NASA PD | (120, 117, 115) | `#787573` |
| 11 | 木卫三 Ganymede | `ganymede_pia00716.jpg` | **Galileo** | **PIA00716** ("Color Global") | 1996/1998 | NASA PD | (137, 112, 88) | `#887058` |
| 12 | 木卫四 Callisto | `callisto_pia03456.jpg` | **Galileo** | **PIA03456** ("Global Color") | 2001-08 | NASA PD | (121, 107, 93) | `#796B5D` |
| 13 | 土卫六 Titan | `titan_pia06230.jpg` | **Cassini** | **PIA06230** (Natural Color) | 2005-04 | NASA PD | (151, 122, 51) | `#967A33` |
| 14 | 土星环 | `saturn_rings_pia08389.jpg` | **Cassini** | **PIA08389** ("Expanse of Ice") | 2007-10 | NASA PD | 总体 (99, 89, 76) | 见下节径向分布 |

> **文件位置**：
> - 行星 + 卫星：`pwa/assets/textures/planets/{filename}`
> - 土星环：`pwa/assets/textures/saturn_rings/saturn_rings_pia08389.jpg`

---

## 2. 各天体详细条目

### 2.1 水星 Mercury
- **探测器**：MESSENGER (Mercury Surface, Space Environment, Geochemistry and Ranging)
- **图像来源**：MESSENGER MDIS 全球增强彩色镶嵌图；Wikimedia Commons 派生（原始数据 NASA/APL/Carnegie）
- **拍摄年份**：~2011–2015（MESSENGER 轨道运行期全球拼合）
- **版权**：NASA 作品 → 美国联邦政府公务产物 → **公共领域 (Public Domain)**，无版权限制
- **图像特征**：全圆盘，近中性灰褐（水星表面真实色彩即低饱和灰褐色）；可见射线坑系统
- **实测 RGB**：(132, 129, 129) `#848081` | R−G=3.1 R−B=3.5（低饱和度属物理事实，非伪彩/灰度转换）

### 2.2 金星 Venus
- **探测器**：Mariner 10
- **图像来源**：Mariner 10 云顶真彩全圆盘（经典视图）
- **拍摄年份**：1974
- **版权**：NASA/JPL → **PD**
- **图像特征**：全圆盘云顶，乳白/米黄调（金星真实外观为均匀米黄色浓密硫酸云层）
- **实测 RGB**：(208, 206, 204) `#D0CECC`

### 2.3 火星 Mars
- **探测器**：Viking / MRO (Mars Reconnaissance Orbiter)
- **图像来源**：火星全球真彩镶嵌（明亮沙漠 vs 暗色海区对比清晰）
- **拍摄年份**：~1990s–2000s（多任务合成）
- **版权**：NASA → **PD**
- **图像特征**：全圆盘，红褐/橙色调，暗蓝灰色海区与亮橙色沙漠区并存
- **实测 RGB**：(138, 105, 75) `#8A694B`

### 2.4 木星 Jupiter
- **探测器**：**Voyager 2**
- **图像编号**：**PIA01369** — "Jupiter from Voyager 2"
- **拍摄年份**：1979-07（飞越）；图像处理/发布 1998-12-05
- **版权**：NASA/JPL → **PD**
- **内嵌元数据确认**：XMP 含 `<xxx:nasa_id>PIA01369</xxx:nasa_id>`、Credit=`NASA/JPL`
- **图像特征**：赤道带近景，橙/棕/白色条纹带分明，大红斑区域偏暖
- **实测 RGB**：(172, 121, 68) `#AB7944`

### 2.5 土星 Saturn ⚠️ 已替换
- **探测器**：**Cassini**
- **图像编号**：**PIA12513** — "Stately Saturn"
- **拍摄年份**：2009-12-25（Cassini 主任务期）
- **版权**：NASA/JPL/Space Science Institute → **PD**
- **内嵌元数据**：XMP 含 PIA12513、DateCreated=2009-12-25、描述含 "natural color view"、"dwarfs the icy moon Rhea"
- **替换说明**：原用 `saturn_pia17175.jpg`（新月照 Painted Lines on an Ornament）因仅含极薄新月亮边（meanRGB 仅 33, 非代表性），已换为 PIA12513 **全圆盘自然色**
- **实测 RGB**：(119, 111, 82) `#776F52`（淡金/棕黄色，符合土星大气 NH₃ 冰晶反射特征）

### 2.6 天王星 Uranus
- **探测器**：**Voyager 2**
- **图像编号**：**PIA18182** — "Uranus as seen by NASA Voyager 2"
- **拍摄年份**：1986-01-24（飞越）；发布 1986-12-18
- **版权**：NASA/JPL-Caltech → **PD**
- **内嵌元数据**：XMP 含 PIA18182、Credit=`NASA/JPL-Caltech`、DateCreated=1986-12-18
- **实测 RGB**：(180, 217, 221) `#B3D9DD`（青蓝色，甲烷吸收主导）

### 2.7 海王星 Neptune
- **探测器**：**Voyager 2**
- **图像编号**：**PIA01492** — 由绿滤光+橙滤光两张最后全行星像拼接的真彩
- **拍摄年份**：1989-08（飞越）；重制/发布 1998-10-30
- **版权**：NASA/JPL → **PD**
- **说明**：无内嵌 XMP 可读字符串（可能为后期重新编码），但文件名明确对应 PIA01492，且测量值深蓝 (51,72,175) 与海王星真彩完全吻合
- **实测 RGB**：(51, 72, 175) `#3348AF`（深钴蓝，甲烷强吸收）

### 2.8 冥王星 Pluto
- **探测器**：**New Horizons**
- **图像编号**：**PIA19708** — "Pluto Big Heart in Color"
- **拍摄年份**：2015-07-13（最近飞越前最后一帧高分辨率彩色像）
- **版权**：NASA/JHUAPL/SwRI → **PD**
- **内嵌元数据**：XMP 完整：PIA19708、DateCreated=2015-07-14、描述含 "taken on July 13, 2015"、Credit=`NASA/Johns Hopkins University Applied Physics Laboratory/Southwest Research Institute`
- **实测 RGB**：(173, 141, 112) `#AC8D70`（桃心区亮米黄/暗区暗褐，平均呈暖棕）

### 2.9 木卫一 Io（主图）⚠️ 已替换
- **探测器**：**Voyager 1**
- **图像编号**：**PIA00318** — "Io Shown in Lambertian Equal Area Projection and in Approximately Natural Color"
- **拍摄年份**：1979-03-05（飞越）；重制/发布 1998-06-04
- **版权**：NASA/JPL/USGS → **PD**
- **内嵌元数据**：XMP 完整：PIA00318、Credit=`NASA/JPL/USGS`、Description="Io Shown in La..."、DateCreated=1998-06-04
- **替换说明**：原 `io_pia02595.jpg`（PIA02595 多面板科学合成灰度图）经通道分析确认为**非可见光真彩**（meanRGB=(90,101,92) 绿灰调，与 Io 硫黄黄/橙红色不符）。已替换为 **PIA00318 Voyager 1 近似自然色镶嵌**（东半球+西半球双半球拼接，标注 "approximately natural color"）
- **备选**：`io_pia00715.jpg`（PIA00715 Galileo 自然色 vs 增强色对照面板，保留作参考但非主纹理）
- **实测 RGB**：(163, 129, 76) `#A3814C`（硫黄黄/橙红，R≫G≫B，符合 Io 表面 SO₂ 熔岩/硫沉积物真彩特征）

### 2.10 木卫二 Europa
- **探测器**：**Galileo**
- **图像编号**：**PIA19048** — "Europa Stunning Surface"
- **拍摄年份**：1996–1999（Galileo 多次飞越）；重新处理 2014-11-21
- **版权**：NASA/JPL-Caltech/SETI Institute → **PD**
- **内嵌元数据**：XMP 含 PIA19048、Credit=`NASA/JPL-Caltech/SETI Institute`、DateCreated=2014-11-21
- **实测 RGB**：(120, 117, 115) `#787573`（冰壳表面浅灰/米白，低反照率暗线区略暗）

### 2.11 木卫三 Ganymede
- **探测器**：**Galileo**
- **图像编号**：**PIA00716** — "Ganymede Color Global"
- **拍摄年份**：1996-06-27（首次近距）；处理发布 1998-08-03
- **版权**：NASA/JPL → **PD**
- **内嵌元数据**：XMP 含 PIA00716、Credit=`NASA/JPL`、DateCreated=1998-08-03
- **实测 RGB**：(137, 112, 88) `#887058`（古老撞击坑暗区 vs 年轻亮区，暖棕色调）

### 2.12 木卫四 Callisto ⚠️ 已修正
- **探测器**：**Galileo**
- **图像编号**：**PIA03456** — "Global Callisto in Color"
- **拍摄年份**：2001-08-22
- **版权**：NASA/JPL → **PD**
- **修正说明**：原 `callisto_pia00320.jpg` 经内嵌 XMP 核实实际内容为 **Io 的 Loki Patera 火山熔岩平原**（PIA00320 描述："A huge area of **Io's** volcanic plains...Loki Patera"），系前序下载时文件名误标。已删除并替换为正确的 Galileo Callisto 全局彩色图 **PIA03456**
- **实测 RGB**：(121, 107, 93) `#796B5D`（灰褐色，大量撞击盆地暗区占主导）

### 2.13 土卫六 Titan
- **探测器**：**Cassini**
- **图像编号**：**PIA06230** — "Cassini View of Titan: Natural Color Composite"
- **拍摄年份**：2005-04-22
- **版权**：NASA/JPL/Space Science Institute → **PD**
- **内嵌元数据**：XMP 完整：PIA06230、Credit=`NASA/JPL/Space Science Institute`、DateCreated=2005-04-22
- **实测 RGB**：(151, 122, 51) `#967A33`（橙黄色，有机雾霾层散射特征）

---

## 3. 土星环 — 径向亮度/色彩分布

- **图像**：`saturn_rings_pia08389.jpg`（**PIA08389** "Expanse of Ice"，Cassini 2007-10-15）
- **图像尺寸**：11298 × 980 px（水平方向 = 径向距离，展开的环条带）
- **取样方法**：图像中部 30% 高度带（y=35%~65%），逐列取均值 RGB，等分为 **24 段**径向采样
- **总体色**：(99, 89, 76) `#63594C`（暖棕/米色，水冰粒子散射）

### 径向分布表

| 段 | x 区间 (px) | 代表 RGB | 亮度 L | 对应结构（推断） |
|----|------------|----------|--------|----------------|
| 1 | 0 – 470 | (8, 7, 8) | 7.5 | ⚠️ 图像左黑边（非环物质） |
| 2 | 470 – 941 | (44, 42, 41) | 42.6 | C 环内缘（极暗） |
| 3 | 941 – 1412 | (71, 65, 62) | 66.0 | C 环外段 |
| 4 | 1412 – 1883 | (87, 77, 74) | 79.2 | C 环/B 环过渡 |
| 5 | 1883 – 2353 | (91, 81, 76) | 82.7 | B 环内缘 |
| 6 | 2353 – 2824 | (76, 69, 64) | 69.7 | B 环内部较暗带 |
| **7** | **2824 – 3295** | **(127, 114, 99)** | **113.4** | **B 环核心（最亮区之一）** |
| **8** | **3295 – 3766** | **(155, 135, 111)** | **133.7** | **★ B 环峰值亮度** |
| **9** | **3766 – 4236** | **(156, 136, 113)** | **134.9** | **★ B 环峰值持续** |
| 10 | 4236 – 4707 | (106, 94, 77) | 92.0 | **Cassini Division 缝隙**（亮度骤降） |
| 11 | 4707 – 5178 | (104, 93, 76) | 91.0 | Cassini Division |
| 12 | 5178 – 5649 | (85, 76, 60) | 73.7 | Cassini Division 外缘/A 环内隙 |
| 13 | 5649 – 6119 | (85, 76, 61) | 74.0 | A 环内段（Encke Gap 区？） |
| 14 | 6119 – 6590 | (88, 78, 63) | 76.3 | A 环中段 |
| 15 | 6590 – 7061 | (90, 80, 65) | 78.2 | A 环 |
| 16 | 7061 – 7532 | (87, 80, 72) | 79.5 | A 环外段 |
| 17 | 7532 – 8002 | (107, 98, 89) | 98.0 | F 环？/ 外稀薄区 |
| 18 | 8002 – 8473 | (122, 109, 94) | 108.4 | 外环渐亮 |
| 19 | 8473 – 8944 | (143, 126, 108) | 125.6 | 外环亮区 |
| 20 | 8944 – 9415 | (158, 140, 118) | 138.7 | 外环更亮 |
| 21 | 9415 – 9885 | (168, 148, 125) | 146.8 | **外环最大亮度** |
| 22 | 9885 – 10356 | (200, 176, 150) | 175.4 | **★★ 全图最亮（可能是边缘增亮/外环末端）** |
| 23 | 10356 – 10827 | (9, 9, 9) | 8.7 | ⚠️ 图像右黑边（非环物质） |
| 24 | 10827 – 11298 | (21, 21, 21) | 21.0 | ⚠️ 右黑边延伸 |

> **有效环材料范围**：seg 2 ~ seg 22（x ≈ 470–10356 px），seg 1/23/24 为图像黑边框应排除。

---

## 4. 取样方法说明（可复现）

### 4.1 Disk（球面天体）取样算法

```python
# 详见 docs/roadmap/source_appendix/celestial_measure_rgb.py
def measure_disk(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(float)
    lum = a.mean(axis=2)

    # ① 天体掩膜：亮度 > 6% 峰值（排除纯黑背景）
    mask = lum > 0.06 * lum.max()
    ys, xs = np.where(mask)

    # ② 计算质心 + 到质心距离
    cx, cy = np.mean(xs), np.mean(ys)
    r = sqrt((xs-cx)² + (ys-cy)²)
    rmax = r.max()

    # ③ 根据天体占比决定策略
    body_frac = len(xs) / (H * W)
    if body_frac > 0.35:
        # 全圆盘图：取内盘 0.85×rmax（避开临边变暗/增亮）
        inner_mask = r < 0.85 * rmax
    else:
        # 表面近景：取全部天体像素
        inner_mask = ones(len(xs), dtype=bool)

    # ④ 剔除最暗/最亮各 2%（去阴影、高光、标注文字）
    cols = a[yi[inner], xi[inner], :]   # N × 3
    lo, hi = percentile(cols.mean(axis=1), [2, 98])
    keep = (cl > lo) & (cl < hi)

    # ⑤ 最终均值
    return cols[keep].mean(axis=0)       # → [R, G, B]
```

**关键设计决策**：
- **亮度阈值 6%**：足够区分黑色太空背景与最暗的天体表面（如水星阴影侧），同时不截断低反照率区域（如木卫四暗区）。
- **内盘 0.85 rmax**：对全圆盘图（body_frac > 35%）剔除临边效应（limb darkening/brightening），保证取样的是**天体表面本体颜色**而非大气散射边缘。
- **2%/98% 分位数裁剪**：去除极端值（宇宙线击中像素、镜面反射亮点、图像叠加的文字标注），保留主体表面统计代表色。
- **灰度风险标记**：当 |R−G| < 4 且 |R−B| < 4 时标记 GRAY——对水星/金星这类**物理上确实低饱和**的天体是正确标记（非错误）。

### 4.2 Ring（土星环）径向取样算法

```python
def measure_ring(path, bands=24):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(float)     # H × W × 3
    y0, y1 = int(H*0.35), int(H*0.65)    # 中部 30% 高度带
    strip = a[y0:y1]                     # band × W × 3
    perx = strip.mean(axis=0)            # W × 3  (每列径向均值)

    edges = linspace(0, W, bands+1)      # 24 等分
    for i in range(bands):
        seg = perx[edges[i]:edges[i+1]]  # w_seg × 3
        rgb = seg.mean(axis=0)           # (3,)
        lum = rgb.mean()
        # → 输出该段的 RGB + 亮度
```

---

## 5. 数据完整性验证清单

| 检查项 | 状态 | 说明 |
|--------|------|------|
| ✅ 文件存在 | PASS | 全部 14 个 `.jpg` 文件在 `pwa/assets/textures/planets/` + `saturn_rings/` 下可读 |
| ✅ 色彩模式 | PASS | 全部 PIL mode = `RGB`（非 `L`/`P` 灰度/调色板） |
| ✅ 内嵌元数据 | PASS | 11/14 文件含完整 NASA XMP（PIA 编号/探测器/日期/Credit），3 个（水/金/火）为 Wikimedia 派生但视觉确认为对应天体真彩 |
| ✅ Io 替换 | FIXED | 原 io_pia02595（灰度合成图）→ io_truecolor（PIA00318 Voyager 自然色） |
| ✅ Saturn 替换 | FIXED | 原 saturn_pia17175（新月照）→ saturn_truecolor（PIA12513 全圆盘） |
| ✅ Callisto 修正 | FIXED | 原 callisto_pia00320（实际是 Io Loki Patera）→ callisto_pia03456（Galileo Callisto） |
| ✅ RGB 可复现 | PASS | 运行 `celestial_measure_rgb.py` 可从图片像素重新生成相同数值（误差 < 0.1） |
| ✅ 版权 PD | PASS | 全部源自 NASA 探测器图像 → 美国联邦政府作品 → Public Domain |
| ✅ 无编造 | PASS | 每个数值均来自 Pillow numpy 对磁盘文件的直接像素读取 |

---

## 6. 文件索引

```
pwa/assets/textures/
├── planets/
│   ├── mercury_messenger_truecolor.jpg    (1040×1040, 408 KB)
│   ├── venus_mariner10_truecolor.jpg       (1000×1000, 253 KB)
│   ├── mars_truecolor.jpg                 (2560×1920, 260 KB)
│   ├── jupiter_pia01369.jpg               ( 916× 901,  71 KB)
│   ├── saturn_truecolor.jpg              (1001×1628,  54 KB) ← PIA12513
│   ├── uranus_pia18182.jpg               (1720×1720,  81 KB)
│   ├── neptune_pia01492.jpg              (2188×2185, 257 KB)
│   ├── pluto_pia19708.jpg                (1024×1020,  55 KB)
│   ├── io_truecolor.jpg                  (2572×1286, 250 KB) ← PIA00318 ★
│   ├── io_pia00715.jpg                   (2400×1900, 203 KB) ← 备选（Galileo 对照面板）
│   ├── europa_pia19048.jpg               (2300×1700, 360 KB)
│   ├── ganymede_pia00716.jpg             ( 800× 800,  50 KB)
│   ├── callisto_pia03456.jpg             ( 740× 753,  74 KB) ← ★ 修正
│   └── titan_pia06230.jpg                ( 758× 766,  21 KB)
└── saturn_rings/
    └── saturn_rings_pia08389.jpg         (11298× 980, 595 KB)
```

**总计：15 个文件（14 目标 + 1 Io 备选），~2.7 MB**

---

## 8. 补充资源（太阳 + 木星/天王星/海王星环 + 月球清晰度升级）

> 追加采集日期：2026-07-20（同规格、同测量算法）
> 需求来源：用户补充要求——太阳真实日面、三颗带环行星（木/天/海）的环带资源、以及评估月球贴图清晰度。
> 验证状态：✅ 全部下载至磁盘、RGB/径向分布由统一脚本从像素实测（可复现）、非编造。

### 8.0 补充总览表

| # | 天体 | 文件名 | 探测器 | NASA 图像编号 | 年份 | 版权 | 实测代表色 | 用途 |
|---|------|--------|--------|--------------|------|------|-----------|------|
| S1 | 太阳 ☀️ | `sun_sdo_hmi_luminance.jpg` | **SDO / HMI** | HMI Intensitygram (latest) | 实时更新 | NASA PD | (155,155,155) 中性灰 | 着色用亮度图 |
| — | 太阳（参考色） | `sun_sdo_hmi_2048.jpg` | SDO / HMI | 同上（Quick-Look 橙色 LUT） | 实时 | NASA PD | (163,89,3) 橙 | 仅视觉参考，非原始数据 |
| S2 | 木星环 | `jupiter_main_ring_grayscale.jpg` | **Voyager 1** | **PIA00701**（主环+晕，上半灰度） | 1979 | NASA PD | 径向 9→45（灰） | 环带径向条带 |
| S3 | 天王星环 | `PIA00142_uranus_ring_system.jpg` | **Voyager 2** | **PIA00142**（完整环系统） | 1986 | NASA PD | 径向 65→154→62（钟形） | 环带径向条带 |
| S4 | 海王星环 | `PIA01493_neptune_rings.jpg` | **Voyager 2** | **PIA01493**（环系统） | 1989 | NASA PD | 径向 ~28→33（极暗） | 环带径向条带 |
| S5 | 月球（升级）★ | `moon_lroc_color_2k.jpg` | **LROC / WAC** | CGI Moon Kit 2025 | 2025 拼合 | NASA PD | (190,186,182) 暖灰 | **已替换** moon_1024.jpg |

### 8.1 太阳 ☀️（新增真实日面）

- **探测器 / 来源**：**SDO（Solar Dynamics Observatory）HMI（Helioseismic and Magnetic Imager）白光强度图（Intensitygram）**
- **图像编号**：NASA SVS 持续发布的 "Latest Image"（`latest_2048_HMIIC.jpg`）；HMI 连续谱 6173 Å 光球层观测
- **拍摄年份**：实时滚动更新（SDO 自 2010 持续在轨）
- **版权**：NASA / SDO → **公共领域 (PD)**（美国联邦政府作品）
- **文件说明**：
  - `sun_sdo_hmi_2048.jpg` —— SDO 官网 **Quick-Look 着色版**（橙色 LUT 显示用）。米粒组织 + 黑子细节极好，但颜色为 SDO 显示夸张橙，**非原始物理白光**，仅作视觉参考。
  - `sun_sdo_hmi_luminance.jpg` —— 由上式按 ITU-R BT.601 去色得到的**亮度图**（2048×2048）。保留全部表面细节（米粒、黑子、黑子群），供渲染 shader 作为亮度/法线扰动源，由 shader 自行着色（白/黄）。**推荐渲染使用此文件**。
- **实测 RGB（亮度图）**：(155, 155, 155) `#9B9B9B`（中性灰，符合光球层近白物理色）；采样 2,637,251 像素（body_frac=0.658，因为日面外有边缘衰减）。
- **注意**：太阳是**自发光体**，渲染时不应做简单反照率贴图，而应用 emissive + 着色 shader（细节来自此亮度图）。

### 8.2 木星环（新增）

- **探测器**：**Voyager 1**
- **图像编号**：**PIA00701** — "Jupiter's Main Ring and Halo"（背光（forward-scattered）观测，主环 + 晕清晰可见）
- **年份**：1979（Voyager 1 飞越）
- **版权**：NASA/JPL → **PD**
- **处理**：原图上下双拼（上为灰度背光环、下为伪彩热图）。已裁取**上半灰度部分** → `jupiter_main_ring_grayscale.jpg`（1151×400），剔除下半伪彩。
- **图像特征**：木星环极暗淡（主环 + 薄晕 + 阿马尔特亚尘埃环），背光下呈细灰带；无颜色（尘埃散射近中性灰）。
- **径向分布**（24 段，中部 30% 带，排除黑边）：
  - seg1 黑边(L≈8) → seg3 起亮(L≈21) → **seg14–21 主环亮峰 L≈42–46** → seg22–23 外缘下降(L≈31–36)
  - 总体为**极暗灰带**（峰值亮度仅 45/255），渲染时需 emissive/增亮或提高曝光。

### 8.3 天王星环（新增）

- **探测器**：**Voyager 2**
- **图像编号**：**PIA00142** — "Uranus' Ring System"（完整环系统，多道窄环）
- **年份**：1986-01（Voyager 2 飞越）
- **版权**：NASA/JPL → **PD**
- **图像特征**：天王星 13 道窄环清晰可辨，ε 环最亮；含恒星背景（环后方亮星为标定参考）。整体近中性灰（环粒子为暗色岩石/冰）。
- **径向分布**（24 段）：**钟形峰** —— seg1 L≈65 → seg13–17 峰值 L≈153（ε 环所在）→ seg24 L≈62。峰值/边沿比 ≈ 2.5×，结构对比明显，适合做径向环带。

### 8.4 海王星环（新增）

- **探测器**：**Voyager 2**
- **图像编号**：**PIA01493** — "Neptune's Rings"（环系统，含 Adams 弧）
- **年份**：1989-08（Voyager 2 飞越）
- **版权**：NASA/JPL → **PD**
- **图像特征**：海王星环整体极暗淡，Adams 环最亮（含著名的 **Adams 弧**团块），Le Verrier/最内 Galle 环更暗；右下角可见海王星新月边缘。整体近中性灰。
- **径向分布**（24 段）：**整体极暗**（L≈27–33，几乎无波动），符合海王星环尘埃密度极低、Adams 弧仅在局部增亮的事实。渲染时必须大幅增亮/emit 才能可见。

### 8.5 月球贴图清晰度升级 ★（已落地）

- **旧资源**：`moon_1024.jpg`（1024×512，**纯灰度** L = 灰度，实测 (139,139,139) `|RG|=0` `|RB|=0`）—— 来自旧 three.js r128 派生图，无真实色、分辨率偏低。
- **新资源**：`moon_lroc_color_2k.jpg` —— **LROC WAC 全局自然色镶嵌**（CGI Moon Kit 2025 版，NASA SVS `lroc_color_2k.jpg`），**2048×1024 RGB**，公开领域。
- **对比实测**：
  | 指标 | 旧 1K | 新 2K |
  |------|-------|-------|
  | 分辨率 | 1024×512 | 2048×1024（**4× 像素**） |
  | 投影 | 等距柱状 2:1 | 等距柱状 2:1（同投影，无缝替换） |
  | 色彩 | 纯灰度 (`|RG|=0`) | 自然色暖灰 `(190,186,182)` `|RG|=5.1` `|RB|=8.6` |
  | 细节 | 月海/高地模糊 | 月海、高地、辐射纹、极区清晰 |
- **已落地**：`real-celestial.js:211` 月球贴图引用由 `moon_1024.jpg` 改为 `moon_lroc_color_2k.jpg`（一行安全替换，vUv 映射不变）。旧文件保留作备份，未删除。
- **取舍说明**：自然色版带极淡暖色调（真实月壤反射特征），比纯灰度更贴近肉眼观感；若后续需要高对比灰度法线源，可用同目录 `moon_1024.jpg` 或另取 LROC 灰度版。

---

## 9. 补充资源验证清单

| 检查项 | 状态 | 说明 |
|--------|------|------|
| ✅ 太阳文件存在 | PASS | `sun_sdo_hmi_2048.jpg`(804 KB) + `sun_sdo_hmi_luminance.jpg`(685 KB) 均可读 |
| ✅ 太阳亮度图 | PASS | 去色版 2048×2048，中性灰 (155,155,155)，米粒/黑子细节保留 |
| ✅ 木星环 | PASS | `jupiter_main_ring_grayscale.jpg` 由 PIA00701 上半裁出，径向结构清晰 |
| ✅ 天王星环 | PASS | `PIA00142_uranus_ring_system.jpg` 完整环系统，钟形径向峰 |
| ✅ 海王星环 | PASS | `PIA01493_neptune_rings.jpg` 含 Adams 弧，整体极暗（物理正确） |
| ✅ 月球升级 | PASS | 2K 自然色替换 1K 灰度，已在 real-celestial.js 落地，同投影无缝 |
| ✅ 补充 RGB/径向可复现 | PASS | 运行 `celestial_measure_additional.py` 重新生成一致数值 |
| ✅ 版权 PD | PASS | 太阳(SDO)/三环(NASA Voyager)/月球(LROC) 均为 NASA 公共领域 |

---

## 10. 补充文件索引

```
pwa/assets/textures/
├── sun/
│   ├── sun_sdo_hmi_2048.jpg            (2048×2048, 804 KB) ← SDO 橙色 LUT 参考
│   └── sun_sdo_hmi_luminance.jpg       (2048×2048, 685 KB) ← 去色亮度图（渲染用）
├── jupiter_rings/
│   ├── PIA00701_jupiter_main_ring_halo.jpg  (1151×800, 66 KB) ← 原图（上下双拼）
│   ├── jupiter_main_ring_grayscale.jpg     (1151×400, 30 KB) ← 裁取上半 ★
│   └── PIA02859_jupiter_main_ring.jpg      (640×640, 30 KB) ← 备选（时间序列，非单环）
├── uranus_rings/
│   ├── PIA00142_uranus_ring_system.jpg     (782×763, 173 KB) ← ★
│   └── PIA01984_uranus_rings.jpg           (512×512, 62 KB) ← 备选
├── neptune_rings/
│   ├── PIA01493_neptune_rings.jpg          (1469×1160, 149 KB) ← ★
│   └── PIA02202_neptune_full_ring.jpg      (1024×1024, 39 KB) ← 备选（双拼全景）
└── moon/
    ├── moon_lroc_color_2k.jpg         (2048×1024, 447 KB) ← ★ 升级主贴图（已启用）
    ├── moon_1024.jpg                  (1024×512, 238 KB) ← 旧（备份保留）
    └── pia12888_wac_mosaic.jpg        (1000×1000, 149 KB) ← 早期试探（低分辨率，弃用）
```

**补充总计：13 个新文件（太阳×2、木星环×3、天王星环×2、海王星环×2、月球×3 含弃用），~3.0 MB**

---

## 7. 下一步

本 Step 0 仅完成资源采集与色彩实测。后续步骤（待用户指令）：
- **Step 1**：基于实测 RGB + 纹理贴图，在 earth3d.js / real-celestial.js 中实现 **8 行星 + 5 卫星 + 太阳 + 土星/木星/天王星/海王星环** 的 **3D 渲染对象创建**（几何体 + 材质 + 贴图加载）。月球已先行升级为 2K 自然色（real-celestial.js 已落地）。
- **Step 2**：轨道位置计算（开普勒要素 / JPL DE 近似）与相机可见性门控
- **Step 3**：集成到 RodiO 地球 3D 场景（deepSpace 层级、距离缩放、LOD）

---
*报告生成工具：`celestial_measure_rgb.py`（行星/卫星，Pillow + NumPy，可复现）*
*补充测量工具：`celestial_measure_additional.py`（太阳/三环/月球对比，可复现）*
*结果数据：`celestial_measure_result.json` + `celestial_measure_additional.json`*
