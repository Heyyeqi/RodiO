# Phase B-4 — Noon Air Earth Calibration Failure Root Cause Audit

> Created: 2026-06-10
> Status: Static analysis complete — no script executed, no images generated
> Subject: `d5b_processor_v3/d6_noon_air_earth_generator.py`
> Calibration run: `noon_air_v1_calibration_2048x1024.jpg` (401KB, NOON_AIR_INTENSITY=0.38)
> Baseline: `d5z_b_8192x4096.jpg`

---

## 0. 执行摘要

本报告通过纯静态代码审计（不运行脚本、不生成图片）定位 calibration 2K 输出的六类视觉问题的根因。

| 编号 | 问题 | 主要根因函数 | 严重程度 |
|---|---|---|---|
| P1 | 全局海洋过暗、接近黑蓝 | 无 minimum luminance floor；`apply_ocean_system` 累积负 lit_delta；raw source 本身偏暗 | 严重 |
| P2 | Maldives / French Polynesia 接近黑色 | island halo 有效强度趋近于零；deep_gate 抑制；无 floor | 严重 |
| P3 | 矩形 patch 可见 | `apply_final_harmony_guard` `feather_px=0` + blend_back=0.70 | 严重 |
| P4 | French Polynesia 上方亮带/下方黑区 | harmony guard 受保护区边界 lat=-15 无羽化，crop 跨越边界 | 严重 |
| P5 | Red Sea / Yellow Sea 过暗或色相异常 | sea_of_japan 有负 lit_delta；shallow sea 无专属 floor | 中 |
| P6 | Sahara / Tibetan Plateau 局部方向可参考 | desert_correction 行为基本正确，但 global 过暗掩盖效果 | 低 |

---

## 1. 全局过暗原因

### 1.1 哪些函数会显著降低亮度

**按影响大小排序：**

#### 1) `apply_final_harmony_guard`（Module 10）— 最大单点暗化

```python
# line 924-928
excess = max(rgb_delta / GUARD_THRESHOLDS["mean_rgb_delta"],
             lum_delta / GUARD_THRESHOLDS["luminance_delta"])
blend_back = min((excess - 1.0) * 0.4, 0.7)
...
blended = out * (1.0 - blend_back) + baseline_f32 * blend_back
out = out * (1.0 - rm3) + blended * rm3
```

- 4 个受保护区（Japan、Mediterranean、Caribbean、Pacific Islands）全部 excess >> 1.0，全部钳位至 `blend_back = 0.70`
- 在这些区域，70% 权重拉回 d5z_b，30% 保留 noon_air 处理结果
- 由于 raw BMNG source 比 d5z_b 暗 60+ rgb_delta，"30% noon_air + 70% d5z_b"结果仍然偏暗于 d5z_b（floor guard FAIL）
- **注：harmony guard 试图修正但无法关闭 source-to-d5z_b 的固有差距；同时由于 feather_px=0，它引入了矩形边界（见第 3 节）**

#### 2) `apply_ocean_system`（Module 2）— 累积负 lit_delta

```python
regions_sorted = sorted(NOON_AIR_OCEAN_REGIONS, key=lambda r: r["priority"])
for r in regions_sorted:
    ...
    if r.get("deep_only"):
        pixel_gate = deep_ocean_px(out)  # ← 每轮重新计算，基于当前 out
    ...
    out = apply_hsl_delta(out, combined,
                          hue_shift=r["hue_shift"] * i,
                          sat_delta=r["sat_delta"] * i,
                          lit_delta=r["lit_delta"] * i)  # ← i = 0.38
```

- `global_deep_base`：`lit_delta = -0.02 × 0.38 = -0.0076`（全球深海）
- `pacific_deep_north/south`：`lit_delta = -0.02 × 0.38 = -0.0076`（太平洋深海）
- `indian_ocean_deep`：`lit_delta = -0.02 × 0.38 = -0.0076`（印度洋深海）
- `atlantic_deep`：`lit_delta = -0.01 × 0.38 = -0.0038`（大西洋深海）
- `sea_of_japan`：`lit_delta = -0.03 × 0.38 = -0.0114`（日本海，`deep_only=False`，影响所有 ocean 像素）

单次 lit_delta 较小，但 **`deep_ocean_px(out)` 在每次迭代都重新计算于当前已处理的 `out`**。Priority 0（global）运行并略微压暗深海后，Priority 1 再次扫描——部分之前未被分类为"深海"的像素可能在新的较暗状态下满足 `B > 85` 等阈值，从而被重复压暗。这是累积效应，不是线性叠加。

#### 3) 无 minimum luminance floor — 暗区无保护

- `apply_shallow_water_shelf`（Module 3）的 shelf_threshold = 0.18：像素 lum < 0.18（即 < 45.9/255）时 `shallow_proxy = 0`，不受任何增亮
- 对于 raw BMNG 中亮度较低的区域（如深印度洋、深太平洋），luminance 值在约 0.12–0.16 范围，完全不触发增亮
- 全局没有任何模块设置最低亮度保护：一旦区域变暗，没有回弹机制

#### 4) `apply_atmosphere_overlay`（Module 11）— 极暗区的 soft-light 公式

```python
def soft_light(base, blend):
    return base + opacity * (2 * blend - 1) * (base - base ** 2)
```

- `blend = [ar, ag, ab]`，其中 ar=143/255=0.561，ag=196/255=0.769，ab=230/255=0.902
- 对于极暗像素（base ≈ 0.02–0.05），`(2 * blend - 1) > 0`（大气色偏亮），则 `(base - base^2) ≈ base`（很小）
- 结果：极暗像素几乎不受大气 overlay 影响，无法通过此模块恢复亮度
- 对中等亮度像素（base ≈ 0.5），大气蓝调增亮有效；对极暗区无效

### 1.2 执行顺序

```
Module 1  apply_global_base_adjustment    ← 轻微亮度/对比度调整，蓝通道微调
Module 2  apply_ocean_system              ← 深海累积负 lit_delta（最早暗化）
Module 3  apply_shallow_water_shelf       ← 仅 lum > 0.18 的浅海获得增亮
Module 4  apply_island_halos             ← 有效强度极弱（见第 2 节）
Module 5  apply_polar_correction         ← 两极冰盖处理，小幅降低冰面亮度
Module 6  apply_desert_correction        ← 仅陆地，小幅暗化沙漠高亮区
Module 7  apply_land_vegetation          ← 仅陆地，绿色 desaturation + 轻微暗化
Module 8  apply_mountains_plateaus       ← 仅陆地，极小调整
Module 9  apply_special_seas             ← 极小调整（±0.004–0.008 lit_delta）
Module 10 apply_final_harmony_guard      ← 4 个保护区 70% blend-back，无羽化
Module 11 apply_atmosphere_overlay       ← soft-light 大气叠加，对极暗区无效
```

### 1.3 重复压暗情况

存在三层重叠：

1. **Module 2 内部**：global_deep_base（priority 0）先压，然后 pacific/atlantic/indian（priority 1）再次压，且每次都重新计算 `deep_ocean_px(out)`
2. **Module 2 vs Module 3**：Module 2 压暗后，Module 3 的 `shelf_threshold=0.18` 门槛导致已被压暗至 lum<0.18 的浅海无法获得增亮
3. **Module 4 vs Module 10**：island halos（Module 4）的微弱增亮效果被 Module 10 的 70% blend-back 部分覆盖（在受保护区内）

### 1.4 `NOON_AIR_INTENSITY` 混合方向是否写反

**未发现方向写反。**

所有正向调整（增亮、增饱、正 hue_shift）均乘以 `i`，负向调整均乘以 `i` 后保持原符号。`NOON_AIR_INTENSITY = 0.38` 使所有调整整体缩至 38%，没有符号翻转。

但 0.38 的问题是：
- 增亮/增饱模块（module 3/4 的正 lit_delta，island halos 的正 lit_delta）被削弱至几乎无效
- 深海负 lit_delta 也被削弱，但 source-to-d5z_b 的固有亮度差距远大于这些小调整，所以结果仍然偏暗

### 1.5 目标色是否过暗且 blend 权重过高

Ocean 系统没有使用 "target_hex + blend" 模式，而是 HSL-delta，所以不存在直接 blend 至暗色目标的问题。

Island halos 使用 blend 参数，但有效强度极小（见第 2.5 节）。

特殊海域（special_seas）的 lit_delta 全为正数（Red Sea +0.02, Caribbean Deep +0.03），方向正确但效果过弱。

### 1.6 是否缺少 minimum luminance floor

**是。整个 pipeline 没有任何 minimum luminance floor。**

无论 lum 降到多低，没有模块会介入保护。对于 raw BMNG 中本就极暗的区域（如深印度洋、深太平洋），pipeline 几乎不做增亮，源值原样穿透到输出。

---

## 2. 海洋黑化原因

### 2.1 深海目标色是否被用于过大范围

`deep_ocean_px` 检测函数：

```python
def deep_ocean_px(f32: np.ndarray) -> np.ndarray:
    R, G, B = f32[:, :, 0], f32[:, :, 1], f32[:, :, 2]
    return ((R < 80) & (B > 85) & (B > R + 30) & (G < B * 0.65)).astype(np.float32)
```

**关键观察：`B > 85` 是深海分类的硬门槛。**

Raw BMNG 中许多深海区域的 B 通道天然低于 85（例如深太平洋典型像素约为 R=25, G=35, B=65–80）。这类像素 **无法通过 `B > 85` 门槛**，不会被 `global_deep_base` 或 `indian_ocean_deep` 等 `deep_only` 区域处理。

这是一把双刃剑：
- **好处**：`deep_only` 区域不会额外压暗这些本已极暗的像素
- **坏处**：这些区域也不受任何 shelf brightening（module 3 的 shelf_threshold 门槛过高），无人负责增亮

### 2.2 是否存在全海洋统一 darken

Ocean 系统没有一个统一的"全海洋变暗"模块。`global_deep_base` 仅作用于通过 `deep_ocean_px` 的像素（B>85 等条件），不是全海洋。

但 **所有深海区域的 lit_delta 均为负数**（-0.01 至 -0.02），没有任何深海区域使用正 lit_delta。这是系统性偏暗倾向。

### 2.3 是否区分 deep ocean / continental shelf / shallow sea / reef

区分存在，但效力不足：

| 层次 | 实现方式 | 问题 |
|---|---|---|
| Deep ocean | `deep_only=True` + `deep_ocean_px` 检测 | B>85 门槛可能将 BMNG 暗区误分为非深海 |
| Continental shelf | `ocean_only=True` priority 2 区域 + 正 lit_delta | 覆盖有限（Yellow Sea、East China Sea 等），无全球默认 |
| Shallow sea | Module 3（lum>0.18 才增亮）+ special_seas | shelf_threshold 过高；special_seas 调整过小 |
| Reef / island | island halos（圆形 mask + blend） | 有效强度趋近于零（见 2.5 节） |

### 2.4 浅海保护是否在后续模块中被覆盖

**是。** 存在两个覆盖路径：

1. **Module 3 增亮 → Module 10 (harmony guard) 部分撤销**：Hawaii、Caribbean、Japan、Pacific Islands 等区域内的浅海增亮，被 Module 10 以 70% 权重拉回 d5z_b。由于 d5z_b 本身更亮，这部分实际上是增亮而非抹除，但由于矩形边界，产生了视觉不连续。

2. **Module 4 island halos → Module 10 (harmony guard) 部分撤销**：Caribbean（Bahamas/Cuba halo）、Pacific Islands（French Polynesia、Fiji halos）等在受保护区内的 island halos，被 Module 10 以 70% 权重覆盖。

### 2.5 Maldives / French Polynesia 为什么接近黑色

**Maldives (lon=73.5, lat=3.5)：**

在 2K 分辨率下，`benchmark_crops` 中 Maldives 的 160×80 像素 crop 覆盖约 lon 60–88°E, lat -3–10°N。这片区域绝大部分是 **开放深印度洋**，Maldives 岛礁本身在 2K 下仅约 1–3 个像素。

跟踪典型深印度洋像素（raw BMNG: R=25, G=35, B=65）的命运：

1. Module 1 后：~(27, 37, 67)（微调）
2. `deep_ocean_px`：B=67 < 85 → 不是深海 → global_deep_base / indian_ocean_deep **不生效**
3. `ocean_px`：B=67 > R+15=42✓, B=67 > G+5=42✓, R=27<120✓ → 是 ocean，但无 priority 2 shelf 覆盖此位置
4. Module 3：lum ≈ 0.15 < shelf_threshold=0.18 → shallow_proxy=0 → **无增亮**
5. Module 4 island halo：radius_px = km_to_pixels(100, 2048) = 5px，feather_px = 3px，该像素位于 halo 范围外 → **无增亮**
6. Modules 5–9：仅影响陆地/极地/特殊海域
7. Module 10：Maldives 不在 4 个受保护区内 → **无 blend-back**

**结论：Maldives 区域像素几乎不被任何模块修改，原样输出 raw BMNG 极暗值。**

---

**Maldives island halo 有效强度计算：**

```python
# 在 apply_island_halos 中
effective = cmask * ocean
out = apply_hsl_delta(out, effective * halo["blend"] * i,
                      hue_shift=hue_shift * i,
                      sat_delta=halo["sat_delta"] * i,
                      lit_delta=halo["lit_delta"] * i)
```

- `halo["blend"] = 0.20`，`i = 0.38`
- 传入 `apply_hsl_delta` 的 mask 权重：`effective × 0.20 × 0.38 = effective × 0.076`
- `apply_hsl_delta` 内部：`out = out × (1 - mask3) + adjusted × mask3`
- lit_delta 参数：`0.08 × 0.38 = 0.0304`
- **单像素 L 净增量 ≈ 0.076 × 0.0304 = 0.0023（在 [0,1] 空间），约 0.6/255**

这个量接近舍入误差，对任何有意义的视觉亮度几乎没有影响。

---

**French Polynesia (lon=-149, lat=-17.5)：**

- 属于 `pacific_deep_south` 区域（cross_antimeridian，lon_w=140, lon_e=280，lon=-149 → 211 在范围内；lat -60 to 0，lat=-17.5 在范围内），但 `deep_only=True`，只影响 B>85 的深海像素
- lat=-17.5 低于 pacific_islands 受保护区的 lat_min=-15，不受 Module 10 的 70% 增亮 blend-back 保护
- 开放太平洋在此位置亦极暗，与 Maldives 问题相同

### 2.6 Red Sea 为什么出现问题

从 metrics 看：red_sea mean_rgb = [155.2, 133.7, 106.8]，luminance = 0.538。这并不是"接近黑色"——Red Sea 是全图亮度较高的区域之一（沙漠反射）。

**实际问题可能是**：Red Sea 的 special_seas 调整（`lit_delta=+0.02 × 0.38 = +0.008`）几乎无效，但周围陆地（阿拉伯半岛）极亮，对比下 Red Sea 水体显得偏暗。加上 Red Sea 本身在 BMNG 中有一定的泥沙色（偏暖黄），special_seas 的 `sat_delta=+0.01 × 0.38 = +0.004` 太小，不足以纠正色相。

**Yellow / East China Sea 的色相异常**：metrics 显示 yellow_east_china mean_rgb = [35.6, 46.4, 38.8]。注意 B=38.8 < G=46.4 < R=35.6——G 最高，B 第二，接近绿色调。这在视觉上呈现为绿泥色。原因：
1. Yellow Sea 在 raw BMNG 中含有大量泥沙，颜色本就偏绿黄
2. `yellow_sea_bohai` 和 `east_china_sea` 的 `hue_shift` 和 `sat_delta` 调整过弱（乘以 0.38 后效果微乎其微），无法覆盖原始色相
3. `sea_of_japan`：`lit_delta=-0.03 × 0.38 = -0.0114`（日本海有意压暗），与 yellow_east_china crop 的部分区域重叠

---

## 3. 矩形 patch 原因

### 3.1 哪些函数使用矩形 bbox

| 函数 | bbox 类型 | feather 是否存在 | 备注 |
|---|---|---|---|
| `apply_ocean_system` | NOON_AIR_OCEAN_REGIONS 经纬度矩形 | ✅ 有（`feather_px_8k` 缩放） | 14 个区域 |
| `apply_shallow_water_shelf` | 全图（无 bbox） | N/A | 基于像素分类 |
| `apply_island_halos` | 圆形 mask（非矩形） | ✅ 有 | 不是矩形 |
| `apply_polar_correction` | 纬度带（LAT 直接阈值） | ✅ 有（GaussianBlur） | 非完整矩形 |
| `apply_desert_correction` | 4 个经纬度矩形 | ✅ 有（`feather_px` 缩放） | Sahara/Arabia/Plateau/Australia |
| `apply_land_vegetation` | 3 个经纬度矩形（热带雨林） | ✅ 有（`feather_px` 缩放） | Amazon/Congo/SEA |
| `apply_mountains_plateaus` | 4 个经纬度矩形 | ✅ 有（`feather_px` 缩放） | Himalayas/Alps/Rockies/Andes |
| `apply_special_seas` | 3 个经纬度矩形 | ✅ 有（`feather_px` 缩放） | Med/Red Sea/Caribbean |
| `apply_final_harmony_guard` | 4 个受保护区矩形 | **❌ 无**（`feather_px=0`） | **主因** |

### 3.2 `apply_final_harmony_guard` — 主因分析

```python
# line 910-913
rm = region_mask_rect(LAT, LON,
                      lat_min=bounds["lat_min"], lat_max=bounds["lat_max"],
                      lon_min=bounds["lon_min"], lon_max=bounds["lon_max"],
                      feather_px=0)   # ← 无羽化，硬矩形边界
```

4 个受保护区，全部 `feather_px=0`：

| 区域 | 经纬度矩形 | blend_back |
|---|---|---|
| japan | lat 30–46, lon 128–148 | 0.70（上限） |
| mediterranean | lat 30–48, lon -10–42 | 0.70（上限） |
| caribbean | lat 10–28, lon -90–-60 | 0.70（上限） |
| pacific_islands | lat -15–20, lon 140–220（跨反子午线） | 0.70（上限） |

blend_back 计算过程：

```python
excess = max(rgb_delta / 8.0, lum_delta / 0.04)
blend_back = min((excess - 1.0) * 0.4, 0.7)
```

- Japan: rgb_delta=63.42 / 8.0 = 7.93, excess=7.93 → blend_back = min(2.77, 0.7) = **0.70**
- Mediterranean: rgb_delta=44.57 / 8.0 = 5.57 → blend_back = **0.70**
- Caribbean: rgb_delta=66.05 / 8.0 = 8.26 → blend_back = **0.70**
- Pacific Islands: rgb_delta=54.17 / 8.0 = 6.77 → blend_back = **0.70**

**全部钳位至最大值 0.70。矩形区域内 70% 权重强制拉向 d5z_b，矩形外保持原始输出。由于无羽化，边界处产生瞬变，视觉上为清晰可见的矩形框。**

最终混合：
```python
blended = out * (1.0 - blend_back) + baseline_f32 * blend_back  # = out*0.3 + d5zb*0.7
out = out * (1.0 - rm3) + blended * rm3  # 矩形内: blended; 矩形外: 原始
```

在矩形边界处，`rm3` 从 1 突变到 0（因为 `feather_px=0`），输出值产生不连续跳变。

### 3.3 四个受保护区可见矩形的像素位置（2K 坐标）

```
Japan:         lat 30–46 → row 484–648;  lon 128–148 → col 1750–1855
Mediterranean: lat 30–48 → row 466–684;  lon -10–42  → col 944–1270
Caribbean:     lat 10–28 → row 700–910;  lon -90–-60 → col 512–683
Pacific Islands: lat -15–20 → row 398–597; lon 140–220（含跨反子午线）
```

对应 calibration 输出中可见的矩形 patch 位置。

### 3.4 French Polynesia 上方亮带/下方黑区的像素级分析

French Polynesia benchmark crop 中心：(lon=-149, lat=-17.5)，2K 像素坐标：
- `cx = int((-149+180)/360 × 2048) = 176`
- `cy = int((90-(-17.5))/180 × 1024) = 611`
- crop 范围：x=[96, 256]，y=[571, 651]

pacific_islands 受保护区（lat -15 to 20）的像素下边界：
- lat=-15 → `cy = int((90-(-15))/180 × 1024) = int(105/180 × 1024) = 597`

**因此，在 French Polynesia compare crop 内：**
- 像素行 0–26（绝对行 571–597）：**位于 pacific_islands 受保护区内**，被 70% blend-back 向 d5z_b 拉近（d5z_b 比 noon_air 更亮）→ 上方亮带
- 像素行 27–79（绝对行 598–651）：**位于受保护区外**，保留 noon_air 极暗输出 → 下方黑区

这与全 candidate 图中 Pacific 中部可见的水平矩形边界是同一根因：在 lat=-15 处有一条横跨太平洋的硬水平线。

### 3.5 local crop-within-feather → 贴回边界问题

除 `apply_final_harmony_guard` 外，其余有 feather 的模块（desert、vegetation、mountains、special_seas、ocean）均在全图上进行操作（不做 local crop 再贴回），因此不存在"局部 crop 内 feather 后贴回全图导致边界仍可见"的问题。

但 `apply_desert_correction` 中 Sahara 区域使用了两步叠加（正常写法中有冗余）：

```python
# line 746-748 — darken 逻辑有冗余
out = out * (1.0 - apply_mask[:, :, np.newaxis] * darken) + \
      out * (1.0 - darken) * apply_mask[:, :, np.newaxis]
```

这等同于：`out = out × [1 - apply_mask × darken + (1 - darken) × apply_mask]`
= `out × [1 - apply_mask × darken + apply_mask - apply_mask × darken]`
= `out × [1 + apply_mask × (1 - 2×darken)]`

当 `darken = 0.06` 时：`1 + apply_mask × 0.88` ≠ 预期行为。这是一个**计算 bug**：正确写法应为 `out × (1 - apply_mask × darken)`，而当前写法引入了额外增亮项 `out × (1 - darken) × apply_mask`。实际效果视 apply_mask 的值而定，对于 apply_mask 较小的区域（bright_mask 在边缘渐变为零），误差极小；但对 apply_mask ≈ 1 的区域（极亮沙漠像素），darken=0.06 时有效乘数变为 `1 + 0.88 = 1.88` 而非预期的 `0.94`，这实际上**在高亮沙漠像素上产生了增亮**而非预期的压暗。

该 bug 在视觉上可能表现为 Sahara 最亮处未被完全压暗，但不是矩形 patch 的成因。

---

## 4. 模块顺序审计

### 4.1 完整执行顺序

```
main()
├─ validate_assets()
├─ ensure_safe_output_path()
├─ for res in resolutions:
│   ├─ load_source()
│   ├─ load_baseline_d5zb()
│   ├─ build_grids()
│   ├─ f32 = source.astype(float32)
│   │
│   ├─ [1] apply_global_base_adjustment()    brightness/contrast/blue_boost/sat
│   ├─ [2] apply_ocean_system()              深海+大陆架 HSL delta，14 个区域
│   ├─ [3] apply_shallow_water_shelf()       浅海代理增亮（lum>0.18 门槛）
│   ├─ [4] apply_island_halos()             圆形 halo，26 个岛群
│   ├─ [5] apply_polar_correction()         南极/格陵兰冰盖
│   ├─ [6] apply_desert_correction()        沙漠/高原
│   ├─ [7] apply_land_vegetation()          陆地植被绿化 desaturation
│   ├─ [8] apply_mountains_plateaus()       山地抑制
│   ├─ [9] apply_special_seas()             地中海/红海/Caribbean Deep
│   ├─ [10] apply_final_harmony_guard()     保护区 blend-back（无羽化）
│   ├─ [11] apply_atmosphere_overlay()      大气蓝调 soft-light
│   │
│   ├─ noon_arr = clip(f32).astype(uint8)
│   ├─ run_baseline_floor_guard()           仅计量，calibration 模式不 abort
│   ├─ generate_preview_crops()
│   ├─ write_summary_report()
│   └─ save noon_air_v1_calibration_2048x1024.jpg
```

### 4.2 顺序问题分析

| 问题 | 位置 | 后果 |
|---|---|---|
| shallow_water_shelf（Module 3）在 deep ocean（Module 2）**之后** | 正确顺序 | 若 Module 2 将某区域压暗至 lum<0.18，Module 3 增亮失效 |
| island_halos（Module 4）在 final_harmony_guard（Module 10）**之前** | 危险顺序 | 4 个受保护区内的 island halos 被 Module 10 部分覆盖 |
| special_seas（Module 9）在 final_harmony_guard（Module 10）**之前** | 危险顺序 | mediterranean / caribbean_deep 的 special_seas 调整被 Module 10 覆盖 |
| polar_correction（Module 5）在 global_base（Module 1）**之后** | 合理 | 无问题 |
| desert_correction（Module 6）在 global_base（Module 1）**之后** | 合理 | 无问题 |

**核心顺序问题：** `apply_final_harmony_guard` 是全链路最后一个内容处理模块（第 10 步），它的 70% blend-back 会覆盖 Modules 1–9 在受保护区内的全部工作成果。然而，由于 source-to-d5z_b 的固有差距，guard 仍然 FAIL——也就是说，Module 10 抹掉了前面的工作，但仍无法达标，同时还引入了矩形伪影。

### 4.3 final pass 是否又统一压暗了所有区域

`apply_atmosphere_overlay`（Module 11）是最终全局 pass。对于非极暗区（lum ≈ 0.3–0.7），soft-light 的大气蓝调有轻微亮化效果（blend 颜色偏亮，`2 * blend - 1 > 0`，`base - base^2 > 0`）。

对于极暗区（lum ≈ 0.02–0.05），`base - base^2 ≈ base`（极小），大气 overlay 效果几乎为零，无法弥补暗化。

**Module 11 不是统一压暗的成因，但也无法挽救极暗区域。**

---

## 5. 跨经度 / crop / mask bug 审计

### 5.1 经纬度到像素转换

```python
def extract_crop(arr, lon, lat, w, h):
    H, W = arr.shape[:2]
    cx = int((lon + 180) / 360 * W)
    cy = int((90 - lat) / 180 * H)
    x0, x1 = cx - w // 2, cx + w // 2
    y0, y1 = cy - h // 2, cy + h // 2
    ...
    crop = arr[max(0, y0):min(H, y1), max(0, x0):min(W, x1)]
    if pad_l or pad_r or pad_t or pad_b:
        crop = np.pad(crop, ((pad_t, pad_b), (pad_l, pad_r), (0, 0)), mode="edge")
```

**跨反子午线的 crop：** 当 lon 接近 180 或 -180 时，cx 接近 W（右边缘）或 0（左边缘），crop 会跨越图像边界。`np.pad(..., mode="edge")` 用边缘像素填充，这会用图像最右侧（或最左侧）像素填充溢出部分，而不是正确的环绕坐标。

- **Hawaii (lon=-156, lat=20)**：cx = int(24/360 × 2048) = 136，crop 不跨边界 ✓
- **French Polynesia (lon=-149, lat=-17.5)**：cx = 176，crop 不跨边界 ✓
- **Tonga/Samoa (lon=-172)**：cx = int(8/360 × 2048) = 45，crop 左侧可能溢出至负 x0，用 edge padding 代替环绕 ← 潜在错误
- **Fiji (lon=178)**：cx = int(358/360 × 2048) = 2042，crop 右侧明显溢出 ← edge padding 代替环绕

**对 Fiji、Tonga/Samoa 的 compare crops 可能显示图像边缘而非真实 Pacific 内容。** 但 benchmark 中这些区域不在 BENCHMARK_CROPS 内（仅作为 island halos），因此不直接影响输出的 16 张 crop 图。

### 5.2 lon/lat 顺序是否反写

**`build_grids`：**

```python
def build_grids(h: int, w: int):
    lat = np.linspace(90, -90, h, dtype=np.float32)     # 从 90° 到 -90°（从北到南，行方向）
    lon = np.linspace(-180, 180, w, dtype=np.float32)   # 从 -180° 到 180°（从西到东，列方向）
    LON, LAT = np.meshgrid(lon, lat)
    return LAT, LON
```

LAT 是行方向（北→南），LON 是列方向（西→东）。这是标准等矩形投影方向，**无 lon/lat 反写错误**。

**`circle_mask`：**

```python
cx = (center_lon + 180.0) / 360.0 * W
cy = (90.0 - center_lat) / 180.0 * H
```

与 `extract_crop` 的坐标系一致，无反写。

**`region_mask_rect`：**

```python
m = (LAT >= lat_min) & (LAT <= lat_max) & (LON >= lon_min) & (LON <= lon_max)
```

LAT/LON 传入顺序一致，无反写。

### 5.3 跨经度区域处理

`region_mask_rect` 的跨反子午线处理：

```python
if cross_antimeridian or lon_max > 180:
    lon_max_wrap = lon_max if lon_max <= 180 else lon_max - 360
    m = (LAT >= lat_min) & (LAT <= lat_max) & (
        (LON >= lon_min) | (LON <= lon_max_wrap)
    )
```

当 `lon_max > 180`（如 pacific_deep_south 的 lon_e=280）：
- `lon_max_wrap = 280 - 360 = -80`
- 条件：`(LON >= 140) | (LON <= -80)` → 覆盖西太平洋（140°E+）和东太平洋（-80°至-180°）

**Pacific Islands 受保护区（lon_min=140, lon_max=220）：**
- `lon_max_wrap = 220 - 360 = -140`
- 条件：`(LON >= 140) | (LON <= -140)` → 覆盖 Hawaii (lon=-156 ≤ -140 ✓)、French Polynesia (lon=-149 ≤ -140 ✓)

**这解释了为何 Hawaii 和 French Polynesia 的部分区域受 Module 10 的 pacific_islands 保护区 blend-back 影响。** Hawaii 完整在 lat 20°（lat_max=20）内，French Polynesia 的 lat=-17.5 超出 lat_min=-15，仅 crop 上部受影响（见第 3.4 节）。

### 5.4 compare crop 拼接错误分析

`generate_preview_crops` 的拼接逻辑：

```python
canvas.paste(Image.fromarray(crop_base), (0, label_h))       # 左：d5z_b
canvas.paste(Image.fromarray(crop_noon), (cw + gap, label_h)) # 右：noon_air
```

拼接方向正确：左侧 d5z_b，右侧 noon_air。label_h=26px 为标题栏。

**潜在问题：** `crop_base` 和 `crop_noon` 使用相同的 `extract_crop` 调用（相同的 lon/lat/w/h）。如果边界 crop 溢出并被 edge-padded，两者都被同样填充，对比的是同等条件下的两图，不产生错误对比。

**full candidate 中的 patch 是真实来自 candidate 图本身**（`apply_final_harmony_guard` 的矩形 blend），不是 compare 图拼接错误。

---

## 6. d5z_b Baseline Guard 语义问题

### 6.1 为什么对 source-derived calibration 不适合作为 hard abort

d5z_b 是由 raw BMNG source 经过 D5a → D5b → D5z 完整处理链（多步亮度增强、色彩分级、区域调整）生成的。d5z_b 比 raw BMNG source 亮约 90 rgb_delta（global 层面）。

d6 generator 从 raw BMNG source 直接读取并处理。无论 `NOON_AIR_INTENSITY` 多低，都无法仅凭色彩调整关闭 raw source 与 d5z_b 之间的亮度鸿沟——因为 D5a/D5b/D5z pipeline 做的是从物理层面重塑图像，而非色彩校正。

当前 guard 阈值 `mean_rgb_delta ≤ 8.0` 是为"d5z_b 小幅修正方案"（如局部色彩重调）设计的，**对 source-derived candidate 永远触发 hard abort**，失去 guard 的意义。

### 6.2 guard FAIL 仍然有审查价值的原因

1. **方向验证**：guard FAIL 可以量化候选图与 d5z_b 的差距（现为 12–19 rgb_delta），确认候选图没有意外压暗至不可接受程度（如 > 40 rgb_delta 则说明有参数 bug）
2. **区域一致性检查**：4 个受保护区的 delta 分布揭示了哪些区域偏差最大（Caribbean=19.27 > Japan=18.50 > Pacific=15.77 > Mediterranean=12.81）
3. **作为回归基准**：如果某次调整使某区域 delta 骤增（如从 18 到 35），即使仍然 FAIL，也说明引入了新问题

### 6.3 后续 guard 拆分建议

| Guard 类型 | 目的 | 触发条件 | 行为 |
|---|---|---|---|
| **safety_guard** | 防止写入 production/candidates | 输出路径校验 | 任何违规 → 立即 hard abort，不可覆盖 |
| **regression_guard（d5z_b floor）** | 确保候选图不比 d5z_b 更差 | rgb_delta > threshold（需重新校准） | source-derived 候选阈值 ≠ d5z_b 修正候选阈值；需分档 |
| **calibration_diagnostic_guard** | 量化差距供人工审查 | 始终运行 | 记录 delta，输出报告，不 abort；calibration 模式即为此 |
| **production_eligibility_guard** | 最终 promotion 前的综合检查 | 候选图进入 candidates/ 前 | 视觉 + 数值双确认 + 人工授权 |

**regression_guard 的阈值需要分档：**
- 对于"d5z_b 小幅修正"方案（如仅调整某区域色彩）：`mean_rgb_delta ≤ 8.0`（当前阈值合理）
- 对于"source-derived 全新候选"方案（如 d6 generator）：阈值应参考同等处理管线下的参考 delta，建议通过 2–3 次人工验证后确定，而非固定数值

---

## 7. 初步修复建议（仅建议，不实施）

### 7.1 增加 ocean luminance floor

在 `apply_ocean_system` 结束后（或作为独立 module）：

```python
# 伪代码建议（不实施）
ocean_mask = ocean_px(out)
lum = luminance(out) / 255.0
floor = 0.12  # minimum luminance for ocean areas
deficit = np.clip(floor - lum, 0.0, floor)
correction = deficit[:, :, np.newaxis] * ocean_mask[:, :, np.newaxis]
out = np.clip(out + correction * 255.0 * 0.6, 0, 255)  # partial correction, blended
```

目标：open Indian Ocean / Pacific 等极暗区域 lum 不低于 0.10–0.12。

### 7.2 将 shallow sea / island halo 移到后段保护，或增加 post-guard 保护

问题：island halos（Module 4）的增亮效果被 Module 10（harmony guard）的 70% blend-back 覆盖。

建议：
- 将 island halos 移至 Module 10 之后执行（11 之前），或
- Module 10 的 blend-back 不作用于 island halo 圆形 mask 内的像素（通过 combined mask 排除）

### 7.3 降低 deep ocean darkening，或去除全局深海负 lit_delta

当前设计使深海统一偏暗，但 raw source 深海本身已暗于 d5z_b。

建议：
- 将 `global_deep_base` 的 `lit_delta` 从 -0.02 改为 0 或 +0.01
- 将 `pacific_deep_north/south`、`atlantic_deep`、`indian_ocean_deep` 的 `lit_delta` 同样从负改为 0 或微正
- 目标是保留色相和饱和度调整（hue_shift、sat_delta），仅取消亮度压暗

### 7.4 禁止直接大面积趋近极暗目标色

当前 ocean 系统不使用极暗 target_hex，使用 HSL delta，这一点设计合理。但 `deep_ocean_px` 分类的 B>85 门槛导致 BMNG 天然暗区（B=65-80）无法获得任何 deep 处理，建议：

- 改为动态门槛：参考当前帧 ocean 中位值的百分位，而非固定 85
- 或完全取消 `deep_only` 分层，改为基于 luminance 百分位的渐变 mask

### 7.5 所有 bbox 区域必须使用强 feather

**最高优先级修复：**

`apply_final_harmony_guard` 必须从 `feather_px=0` 改为使用缩放 feather：

```python
# 建议（不实施）
fpx = scale_feather(40, W)  # 8K 基准 40px feather
rm = region_mask_rect(LAT, LON,
                      lat_min=bounds["lat_min"], lat_max=bounds["lat_max"],
                      lon_min=bounds["lon_min"], lon_max=bounds["lon_max"],
                      feather_px=fpx)   # ← 有羽化，消除矩形边界
```

建议 feather_px_8k ≥ 40px（消除大范围矩形 patch）。

### 7.6 区域处理必须结合 sea / land / ice mask

`apply_final_harmony_guard` 目前不区分海陆冰，在保护区内对所有像素统一 blend-back。建议引入 `ocean_px`、`land_px`、`ice_px` 限制 blend-back 范围，避免陆地区域（如 Japan 的本州岛）被混入。

### 7.7 special seas 不得直接矩形覆盖

`apply_special_seas` 已使用 `ocean_px` 门控（`combined = rmask * ocean`），方向正确。但 feather_px 在 0.38 强度下极小（Red Sea：`scale_feather(12, 2048)` = 3px），建议：
- 增大 `feather_px_8k`（Red Sea 建议 ≥ 24px）
- 加入 land mask 保护，确保陆地（阿拉伯半岛）不受影响

### 7.8 French Polynesia / Maldives / Pacific Islands 需单独保护

这三个区域在 2K/0.38 强度下几乎无法通过 island halos 增亮：

- 建议增加"tropical shallow ocean min-luminance"专用模块
- 使用更大半径的圆形 mask（French Polynesia 已是 300km，但 blend 权重 × intensity 太小）
- 或增加 `NOON_AIR_INTENSITY` 专门针对 island halo 类模块的局部 override

### 7.9 calibration 输出和 production eligibility 继续分离

当前 `--calibration` 模式机制正确（guard 运行但不 abort，输出到 `calibration/` 子目录，明确标记 CALIBRATION ONLY），应保留。

建议补充：calibration 模式自动输出一份人工审查清单（当前已有 compare crops 和 metrics），后续可考虑输出每个模块的中间结果（module debug dump）以辅助审查。

---

## 8. 审计结论

### 8.1 审计报告路径

```
docs/phase_b4_noon_air_calibration_failure_root_cause_audit.md
```

### 8.2 最可能导致全局过暗的前三个函数

| 排名 | 函数 | 机制 |
|---|---|---|
| 1 | `apply_final_harmony_guard`（Module 10） | 4 个受保护区 70% blend-back 覆盖前 9 个模块工作成果；raw source 比 d5z_b 本就偏暗，blend 结果仍暗 |
| 2 | 无 minimum luminance floor（缺失功能） | 极暗区域（lum<0.18）无任何模块增亮；`apply_shallow_water_shelf` 的 `shelf_threshold=0.18` 门槛使暗区完全不受增亮 |
| 3 | `apply_ocean_system`（Module 2）内的累积负 lit_delta | priority 0→1 两轮负 lit_delta，且每次重新计算 `deep_ocean_px(out)` 可能使更多像素被分类为深海 |

### 8.3 最可能导致矩形 patch 的前三个函数

| 排名 | 函数 | 机制 |
|---|---|---|
| 1 | `apply_final_harmony_guard`（Module 10） | `feather_px=0`，blend_back=0.70，4 个大型保护区矩形的硬边界 |
| 2 | `apply_desert_correction`（Module 6） | 使用矩形 bbox + feather，当 feather_px 在 2K 较小时（Sahara: scale_feather(16,2048)=4px），边界可能仍可见；加之 darken 逻辑存在计算 bug（第 3.5 节） |
| 3 | `apply_land_vegetation`（Module 7） | 三个热带雨林矩形区域（Amazon/Congo/SEA），与 desert_correction 类似，feather 在 2K 偏小 |

### 8.4 `NOON_AIR_INTENSITY` 混合方向是否疑似错误

**未发现方向错误。**

所有增亮/增饱调整乘以 `i` 后方向正确（仍为正向效果，只是强度降低）。`NOON_AIR_INTENSITY = 0.38` 的问题是：
- 使亮化效果（island halos、shallow shelf、arctic +lit_delta）弱到近似无效
- 使暗化效果（deep ocean -lit_delta）同步削弱，但 source-to-d5z_b 固有差距远大于任何调整，导致整体偏暗

### 8.5 是否发现 shallow sea / island halo 被后续模块覆盖

**是，确认两条覆盖路径：**

1. **island halos（Module 4）→ final_harmony_guard（Module 10）**：4 个受保护区（Caribbean/Pacific Islands 含 Bahamas/Hawaii/Fiji halos）的 island halo 增亮被 Module 10 以 70% 权重部分抹除。由于 d5z_b 更亮，blend-back 实际使受保护区比 noon_air 独立输出更亮——但这是利用 d5z_b 作为"亮度锚"，而非 noon_air 自身的增亮成果。

2. **shallow_water_shelf（Module 3）→ deep ocean mask 动态变化**：Module 3 将 lum 在 0.18–0.43 之间的浅海像素增亮后，Module 2 的后续 priority 区域（如有覆盖）可能重新分类该像素。但由于 Module 2 先于 Module 3 执行（顺序 2→3），实际上是 Module 2 先暗化，Module 3 后增亮，Module 3 在受保护区内的成果随后被 Module 10 部分覆盖。

### 8.6 git status

```
M d5b_processor_v3/d6_noon_air_earth_generator.py
```

脚本有未提交的本地修改（NOON_AIR_INTENSITY=0.38、--calibration 模式、PIL fix）。本审计期间未产生任何新修改，git status 与审计开始时一致。

---

## 附录：关键数值参考

| 指标 | d5z_b baseline | noon_air calibration | delta |
|---|---|---|---|
| Global luminance | 0.388 | 0.202 | -0.186（-48%） |
| Global mean R | 84.0 | 48.9 | -35 |
| Global mean G | 103.1 | 51.8 | -51 |
| Global mean B | 116.8 | 56.9 | -60 |
| Maldives luminance | — | 0.039 | （极暗警示） |
| French Polynesia lum | — | 0.071 | （极暗） |
| Japan guard rgb_delta | — | 18.50 | FAIL (limit 8.0) |
| Caribbean guard rgb_delta | — | 19.27 | FAIL (limit 8.0) |

---

> 严格遵守以下禁止事项：
> - ✅ 未运行 generator
> - ✅ 未生成任何 jpg / png
> - ✅ 未修改脚本
> - ✅ 未修改前端
> - ✅ 未复制到 candidates/
> - ✅ 未进入 8K
> - ✅ 未 commit
> - ✅ 未 push
