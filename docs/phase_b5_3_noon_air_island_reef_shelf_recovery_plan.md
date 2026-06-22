# Phase B-5.3 — Noon Air Island / Reef / Shelf Recovery Plan

## 文档定位

本文档是 B-5.3 修复方案设计文档。B-5.2 成功移除了 B-5.1 引入的蓝色矩形 patch，但代价是热带岛礁、浅海大陆架和特殊海域恢复到视觉过暗状态。B-5.3 的目标是在不恢复任何矩形 bbox floor 的前提下，通过圆形近邻 floor、大陆架增强和 special seas 修正，重建局部可见性。

**本文档为方案设计，不包含代码实施。实施需人工授权后分步进行。**

上位约束文件：`RodiO_Noon_Air_Earth_地图配色工程执行方案_v1_1.md`

---

## 1. 确认保留项（来自 B-5.1 / B-5.2）

以下修改在 B-5.3 中必须继续保留，不得撤销：

| 修改项 | 状态 |
|---|---|
| `apply_final_harmony_guard` diagnostic-only，无 blend_back，无像素修改 | 保留 ✓ |
| 删除 `blend_back` + `blended` 混合回路 | 保留 ✓ |
| `deep_mask_fixed` 预计算（消灭 cascading 深海暗化）| 保留 ✓ |
| 所有 deep-basin `lit_delta → 0.0`（7 处）| 保留 ✓ |
| 删除 `_TROPICAL_FLOOR_ZONES`（5 个大 bbox zone）| 保留 ✓ |
| 删除 tropical floor Pass 3 | 保留 ✓ |
| `OCEAN_FLOOR_GLOBAL = 0.07`（B-5.2 降低后值）| 保留 ✓ |
| `OCEAN_FLOOR_SHALLOW = 0.10`（B-5.2 降低后值）| 保留 ✓ |
| `evaluate_calibration_safety`：`8k_eligible=False`，`production_eligible=False` 硬编码 | 保留 ✓ |
| `write_calibration_warning_metadata` | 保留 ✓ |
| floor 日志计数 bug 修正（`ocean_bool` 过滤）| 保留 ✓ |

---

## 2. B-5.2 失败原因分析

### 2.1 核心失败数据

| 区域 | B-5.1 lum（有矩形 patch）| B-5.2 lum（无矩形）| 目标区间 |
|---|---|---|---|
| Maldives | 0.1221 | **0.0585** | 0.10–0.14 |
| French Polynesia | 0.1125 | **0.0537** | 0.09–0.13 |
| Pacific Islands | 0.1212 | **0.0536** | 0.09–0.12 |
| Hawaii | 0.0969 | **0.0541** | 0.08–0.11 |
| Caribbean | 0.1277 | **0.0785** | 0.09–0.13 |
| Bahamas | 0.1200 | **0.0771** | 0.10–0.14 |

### 2.2 失败根因

**失败根因一：Island halo 在 NOON_AIR_INTENSITY=0.38 下力度不足**

Island halo 的 lit_delta 和 blend 均通过 NOON_AIR_INTENSITY 缩放：
- Maldives：`blend=0.20 × 0.38 = 0.076`，`lit_delta=0.08 × 0.38 = 0.03`
- French Polynesia：`blend=0.22 × 0.38 = 0.084`
- 有效 lift 约 +3% lit → 不足以将 lum 0.05 推至 0.11

Island halo 的本质是 HSL 色调调整，对极暗深色像素（lum < 0.10）的亮度作用非常有限，因为 HSL lit 调整在暗色区域的可感知效果极弱。

**失败根因二：Shallow water shelf 对极暗浅海不敏感**

Module 3 的 shelf threshold = 0.18：只有 lum > 0.18 的浅海像素才获得 shelf 增益。Caribbean/Maldives 区域的 ocean 像素 lum ≈ 0.05–0.09，远低于 0.18，shelf 模块几乎不起作用。

**失败根因三：Global floor 只能防近黑，不能塑造浅海**

`OCEAN_FLOOR_GLOBAL = 0.07` 的设计目的是"救接近黑色的像素"，不是"塑造浅海可见性"。将深海从 lum=0.04 推至 lum=0.07 依然是视觉上非常暗的颜色。

**失败根因四：小岛/环礁在 2K 下像素太少**

在 2K（2048×1024）下，1px ≈ 19.6km。Maldives 环礁最宽约 2–5km，在 2K 下不足 1/4 像素。单个环礁在 benchmark crop 中不可见，整个 crop 以深海像素为主。因此 crop-level lum 反映的是深海暗度，不是礁盘亮度。

然而即使如此，仍需对"岛礁附近"的海洋给予局部可见性保护，因为：
1. 8K 下这些细节会可见
2. 即使在 2K，一片完全均匀的深黑也会破坏地理识别度

**失败根因五：Red Sea / Yellow East China 需要 special sea 级别的色调修正**

这两个区域的问题不是亮度不够，而是：
- Red Sea：2K 下海域仅 3–5px 宽，lit_delta=+0.02 效力太弱，视觉不可见
- Yellow/East China：G(35.4) > B(27.6) = 绿泥色，需要 hue_shift 大幅向蓝偏移

---

## 3. B-5.3 修复原则

### 3.1 绝对禁止

- 不恢复 `_TROPICAL_FLOOR_ZONES` 或任何大 bbox floor
- 不使用 `region_mask_rect` 对海洋施加 floor（容易产生矩形边界）
- 不将整个加勒比、印度洋、南太平洋、西太平洋作为一个整体进行亮度调整
- 不使用任何形状为矩形的 ocean mask 进行 floor 操作

### 3.2 允许的修复工具

| 工具 | 适用场景 | 形状 | 产生矩形风险 |
|---|---|---|---|
| `circle_mask` 圆形 floor（新增 `apply_island_reef_floor`）| 岛礁可见性保护 | 圆形，有 feather | 无 |
| `apply_shallow_water_shelf` 参数微调 | 大陆架渐变增强 | 像素级亮度代理，无 bbox | 无 |
| `NOON_AIR_SPECIAL_SEAS` 参数修正 | Red Sea / Yellow East China | 有 feather 的 region_mask_rect | 极低（有 feather）|
| `NOON_AIR_OCEAN_REGIONS` 参数微调 | sea_of_japan / continental shelf | 有 feather，ocean_only | 低 |
| `NOON_AIR_ISLAND_HALOS` lit_delta 独立增强 | 岛礁 HSL 色调 | 圆形，有 feather | 无 |

### 3.3 核心设计约束

1. **所有新 mask 必须使用 circle_mask，不用 region_mask_rect**（除非是对 special_seas 进行微调，且 feather 足够）
2. **Floor 只保护"极暗"区域**（lum < 目标），不推高正常深海
3. **Island halo 和 reef floor 应配合**：halo 提供色调，reef floor 提供最低亮度保底
4. **深海包围感必须保留**：reef floor 的外边界之外，深海自然暗，不做全局提亮

---

## 4. Island / Reef Local Recovery 设计

### 4.1 新增模块：`apply_island_reef_floor`（Module 4.5）

在 Module 4（island_halos）之后、Module 5（polar_correction）之前，插入新函数。

**函数逻辑**：

```
对每个 _REEF_FLOOR_ZONES 中的 zone：
  1. 用 circle_mask 建立 inner_mask（半径 = inner_km）
  2. 用 circle_mask 建立 outer_mask（半径 = outer_km）
  3. transition_mask = outer_mask - inner_mask（圆环区域）
  4. 对 ocean * inner_mask 应用 _lift_floor(out, ..., inner_floor)
  5. 对 ocean * outer_mask 应用 _lift_floor(out, ..., outer_floor)
     （outer 包含 inner，顺序无所谓因为 floor 是 max 操作）
  6. 所有 mask 均带 feather，无硬边
```

**不使用 NOON_AIR_INTENSITY 缩放 floor 值**：floor 是最低亮度保底，是绝对值，不是相对色调调整，不应被 intensity 衰减。

### 4.2 `_REEF_FLOOR_ZONES` 建议参数

各参数含义：
- `center`：(lon, lat)，与 NOON_AIR_ISLAND_HALOS 对应
- `inner_km`：礁盘核心半径（环礁、浅滩）
- `outer_km`：浅海过渡半径
- `inner_floor`：内圈最低亮度目标（[0,1]）
- `outer_floor`：外圈最低亮度目标（[0,1]）
- `feather_8k`：8K feather px（2K 下自动缩放）

#### 热带岛礁分组（高可见性需求）

| 区域 | center | inner_km | outer_km | inner_floor | outer_floor | feather_8k | 说明 |
|---|---|---|---|---|---|---|---|
| maldives | (73.5, 3.5) | 80 | 200 | 0.14 | 0.10 | 20 | 马尔代夫环礁链 |
| seychelles | (55.5, -4.5) | 60 | 150 | 0.13 | 0.09 | 16 | 塞舌尔 |
| tahiti | (-149.5, -17.5) | 80 | 220 | 0.13 | 0.09 | 22 | 塔希提核心 |
| tuamotu | (-142.0, -16.0) | 120 | 280 | 0.12 | 0.09 | 28 | 土阿莫土环礁群 |
| bahamas | (-76.5, 24.5) | 120 | 240 | 0.15 | 0.11 | 24 | 巴哈马浅滩 |
| lesser_antilles | (-62.5, 15.0) | 80 | 180 | 0.12 | 0.09 | 18 | 小安的列斯 |
| cuba_coast | (-79.5, 21.5) | 100 | 220 | 0.12 | 0.09 | 20 | 古巴附近浅海 |
| hawaii | (-156.0, 20.0) | 80 | 200 | 0.12 | 0.09 | 20 | 夏威夷 |
| fiji | (178.0, -18.0) | 100 | 220 | 0.13 | 0.09 | 20 | 斐济 |
| tonga_samoa | (-172.0, -17.0) | 80 | 200 | 0.12 | 0.09 | 20 | 汤加/萨摩亚 |
| micronesia_palau | (135.0, 7.5) | 120 | 260 | 0.13 | 0.09 | 24 | 密克罗尼西亚/帕劳 |
| solomon_vanuatu | (159.0, -12.0) | 100 | 240 | 0.12 | 0.09 | 22 | 所罗门/瓦努阿图 |
| indonesia_east | (132.0, -4.0) | 120 | 260 | 0.11 | 0.08 | 22 | 印尼东部群岛 |
| comoros | (43.5, -12.0) | 60 | 140 | 0.12 | 0.09 | 14 | 科摩罗 |
| mauritius | (57.5, -20.0) | 60 | 150 | 0.12 | 0.09 | 16 | 毛里求斯/留尼汪 |

#### 温带 / 中纬度岛礁（较弱保护）

| 区域 | center | inner_km | outer_km | inner_floor | outer_floor | feather_8k | 说明 |
|---|---|---|---|---|---|---|---|
| bermuda | (-64.7, 32.3) | 50 | 120 | 0.11 | 0.08 | 12 | 百慕大 |
| azores | (-27.5, 38.5) | 60 | 160 | 0.10 | 0.07 | 14 | 亚速尔 |
| canary_islands | (-15.5, 28.0) | 80 | 180 | 0.10 | 0.07 | 16 | 加那利群岛 |
| philippines_south | (122.0, 8.5) | 100 | 220 | 0.11 | 0.08 | 18 | 菲律宾中南部 |

### 4.3 Island Halo 参数调整建议（可选）

当前 island halo 的 lit_delta 被 NOON_AIR_INTENSITY=0.38 大幅衰减。可考虑为 island halo 引入独立的 `ISLAND_HALO_LIT_BOOST` 系数（不覆盖全局 intensity），专门用于保证礁盘的 HSL 色调效果：

```python
ISLAND_HALO_LIT_BOOST = 1.8   # 补偿 NOON_AIR_INTENSITY=0.38 对礁盘色调的过度衰减
# 应用时：lit_delta * i * ISLAND_HALO_LIT_BOOST
```

这样 Maldives 的有效 lit_delta = 0.08 × 0.38 × 1.8 ≈ 0.055（原 0.03），仍比较克制但可感知。

**注意**：只对 lit_delta 应用 boost，不对 blend 或 sat_delta 应用，避免过度饱和。

---

## 5. Shallow Shelf Recovery 设计

### 5.1 Shelf Threshold 降低

当前 Module 3 的 `shelf_threshold = 0.18`，低于此亮度的 ocean 像素不获得 shelf 增益。

**建议**：降低至 `shelf_threshold = 0.11`，使得 lum ≈ 0.07–0.11 的深蓝近岸海域也能被 shelf 模块轻微影响。

同时调整 shelf 渐变斜率：从 `clip((lum - 0.18)/0.25, 0, 1)` 改为 `clip((lum - 0.11)/0.22, 0, 1)`。

这样：
- lum=0.07：gate = 0 → 不受影响（仍为深海）
- lum=0.11：gate = 0 → 刚好边界
- lum=0.18：gate ≈ 0.32 → 轻微增益
- lum=0.25：gate ≈ 0.64 → 正常 shelf 效果

### 5.2 Shelf brightening gain 调整

当前 `shelf_gain = shallow_proxy * 0.06 * i`，有效值 = 0.06 × 0.38 = 0.023。

**建议**：增加独立的 `SHELF_GAIN_BOOST` 系数（类似 island halo boost）：

```python
SHELF_GAIN_BOOST = 2.5
# shelf_gain = shallow_proxy * 0.06 * i * SHELF_GAIN_BOOST = 0.057
```

这会使浅海获得约 5.7% 的 gain（原 2.3%），仍然克制，不会产生荧光感。

### 5.3 Caribbean / Bahamas 专项

Caribbean 和 Bahamas 不在现有 NOON_AIR_OCEAN_REGIONS 中有专项浅海处理。建议：

**在 NOON_AIR_OCEAN_REGIONS 中新增两个低优先级区域**（priority=2），仅对较亮 ocean（non-deep）应用轻微正向 lit_delta：

```python
dict(name="caribbean_shelf", lon_w=-90, lon_e=-60, lat_s=10, lat_n=28,
     hue_shift=+3, sat_delta=+0.02, lit_delta=+0.03,
     feather_px_8k=30, ocean_only=True, deep_only=False, priority=2, cross_am=False),
dict(name="bahamas_shelf",   lon_w=-82, lon_e=-72, lat_s=20, lat_n=28,
     hue_shift=+4, sat_delta=+0.03, lit_delta=+0.04,
     feather_px_8k=20, ocean_only=True, deep_only=False, priority=2, cross_am=False),
```

**关键点**：`deep_only=False` 但 `ocean_only=True`，且 priority=2 在 global_deep_base（priority=0）之后运行。加上 reef_floor_zones 中的 Bahamas/Caribbean circular floors，两者协同作用：ocean_regions 提供色调调整，circular floor 提供最低亮度保底。

---

## 6. Special Seas 修正设计

### 6.1 Red Sea — 去黑沟

**当前问题**：`lit_delta=+0.02, feather_px_8k=12`；有效 lit_delta = 0.02 × 0.38 = 0.0076，极弱；2K 下红海仅 3–5px 宽。

**修复方案**：

```python
# NOON_AIR_SPECIAL_SEAS 中修改 red_sea：
dict(name="red_sea", lon_w=32, lon_e=44, lat_s=12, lat_n=30,
     hue_shift=+3, sat_delta=+0.03, lit_delta=+0.10, feather_px_8k=16)
# lit_delta: +0.02 → +0.10（有效值 0.10 × 0.38 = 0.038）
# feather_px_8k: 12 → 16（2K 下 3px → 4px，轻微柔化）
```

同时，在 reef_floor_zones 中可加入红海南北两端 halo（可选）：

```python
dict(name="red_sea_n", center=(34.5, 28.0), inner_km=60, outer_km=150, inner_floor=0.12, outer_floor=0.09, feather_8k=14),
dict(name="red_sea_s", center=(42.0, 14.0), inner_km=60, outer_km=150, inner_floor=0.12, outer_floor=0.09, feather_8k=14),
```

**预期效果**：红海水体 lum 从接近 0.04 推至约 0.08–0.10，与两岸沙漠（lum ≈ 0.55）形成更清晰冷暖对比。

### 6.2 Yellow Sea / East China Sea — 去绿泥

**当前问题**：benchmark Yellow/East China rgb=[28.5, 35.4, 27.6]，G > B，绿泥色。规范要求灰蓝/青蓝（#3A8EA5 → R=58, G=142, B=165 → B > G）。

**根因分析**：
- BMNG source 黄海/东海含大量泥沙悬浮物，原始像素偏绿黄
- 当前 `hue_shift=+4`（yellow_sea_bohai）和 `+3`（east_china_sea），力度不足以逆转绿偏
- `east_china_sea` 的 `sat_delta=+0.01` 为正值，反而增强了绿饱和度

**修复方案**：

```python
# NOON_AIR_OCEAN_REGIONS 修改：
dict(name="yellow_sea_bohai", lon_w=117, lon_e=127, lat_s=28, lat_n=42,
     hue_shift=+8,  sat_delta=-0.06, lit_delta=+0.05,
     feather_px_8k=20, ocean_only=True, deep_only=False, priority=2, cross_am=False),
     # hue_shift: +4 → +8（强推向蓝绿方向）
     # sat_delta: -0.02 → -0.06（进一步降绿饱和度）

dict(name="east_china_sea",   lon_w=118, lon_e=132, lat_s=24, lat_n=34,
     hue_shift=+7,  sat_delta=-0.04, lit_delta=+0.06,
     feather_px_8k=20, ocean_only=True, deep_only=False, priority=2, cross_am=False),
     # hue_shift: +3 → +7
     # sat_delta: +0.01 → -0.04（从增饱和改为减饱和，抑制绿）
```

**目标色阶参考**：
- 黄海：`#3A8EA5`（R=58, G=142, B=165）→ 灰蓝调，B > G
- 东海：`#197FA0`（R=25, G=127, B=160）→ 清蓝，B >> G
- 在 NOON_AIR_INTENSITY=0.38 下，效果为目标的 38%，接受

### 6.3 Japan Sea — 深蓝但不近黑

**当前问题**：`sea_of_japan` lit_delta=0.0（B-5.1 从 -0.03 修正为 0），hue_shift=+2，sat_delta=-0.04。Japan 区域 mean_lum=0.0718，接近黑。

**修复方案**：

```python
dict(name="sea_of_japan", lon_w=128, lon_e=142, lat_s=34, lat_n=52,
     hue_shift=+3, sat_delta=-0.03, lit_delta=+0.03,
     feather_px_8k=20, ocean_only=True, deep_only=False, priority=2, cross_am=False),
     # lit_delta: 0.0 → +0.03（有效 0.011，轻推向蓝）
     # hue_shift: +2 → +3（略微偏蓝）
     # sat_delta: -0.04 → -0.03（不过度去饱和）
```

**注意**：规范要求日本海应"明显偏深，接近 #05395F 至 #07527A"，因此不应提亮太多。lum 目标约 0.09–0.10 即可。

### 6.4 Mediterranean — 深蓝清透，爱琴海有层次

**当前状况**：`lit_delta=-0.01`（有效 -0.0038），mean_lum=0.178，基本可接受。

**轻微调整**：将 `lit_delta=-0.01` 改为 `lit_delta=+0.01`（去除微小暗化），保持其他不变。爱琴海群岛可通过 island halo 增强（已有 `svalbard` 等高纬 halo，但缺少爱琴海条目）。

**可选**：在 reef_floor_zones 添加爱琴海区域：

```python
dict(name="aegean", center=(25.0, 37.0), inner_km=200, outer_km=350, inner_floor=0.11, outer_floor=0.08, feather_8k=30),
```

---

## 7. B-5.3 验收标准

以下所有条件必须在 B-5.3 2K calibration 视觉审查中通过：

### P0（矩形 patch — 必须通过）

1. `diff_vs_d5zb.jpg` heatmap **无任何矩形高亮区块**，分布均匀或呈圆形放射状
2. `preview_global.jpg` 全图无可见矩形边界感
3. South Pacific / Indian Ocean / Caribbean 各区域色调连续，无人工切割线

### P1（区域可见性 — 主要验收）

| 区域 | 通过标准 |
|---|---|
| Maldives | 可见细碎环礁结构；不是全黑；不是整片亮蓝 |
| French Polynesia | 有少量青蓝礁盘痕迹；深海保持包围感 |
| Pacific Islands | 能看到群岛方位；不是均匀深黑块 |
| Hawaii | 岛屿可见；周边有轻微浅海过渡 |
| Bahamas | 有浅海层次；不是矩形蓝块；不是均匀深黑 |
| Caribbean | 深浅有自然差异；古巴/尤卡坦沿岸可见 |
| Red Sea | 不像黑沟；与两岸沙漠形成冷暖对比 |
| Yellow / East China | **B > G**（不再绿泥）；灰蓝/青蓝调 |
| Japan Sea | 深蓝但 lum ≥ 0.085；不似黑色 |
| Mediterranean | 清透深蓝；爱琴海局部有浅海层次 |

### P2（整体基调 — 参考性）

- 全图保持 Noon Air 冷蓝清透风格
- 深海不变成"一整片均匀灰蓝"
- 陆地/沙漠/冰原稳定（不受 ocean 修改影响）
- Antarctica / Greenland / Sahara lum 与 B-5.2 基本相同

### 数字目标（参考，不是硬性 guard）

| 区域 | 目标 lum 范围 |
|---|---|
| Maldives (benchmark) | 0.07–0.11 |
| French Polynesia (benchmark) | 0.06–0.10 |
| Pacific Islands (benchmark) | 0.06–0.09 |
| Bahamas (benchmark) | 0.09–0.13 |
| Caribbean (benchmark) | 0.09–0.12 |
| Japan (benchmark) | 0.08–0.11 |
| Yellow/East China (benchmark) | 0.11–0.15，**B > G** |
| Global mean lum | 0.19–0.23 |

---

## 8. 实施顺序

### Step 1：增强 Island Halo + 新增 apply_island_reef_floor

**改动范围**：
- 新增 `_REEF_FLOOR_ZONES` 常量（§4.2 建议参数）
- 新增 `apply_island_reef_floor` 函数（Module 4.5）
- 可选：新增 `ISLAND_HALO_LIT_BOOST = 1.8`，修改 `apply_island_halos` 中 lit_delta 的应用

**插入位置**：main() pipeline 中 `apply_island_halos` 之后

**预期效果**：消除 Maldives/French Polynesia/Pacific Islands/Hawaii 过暗；差异局限在圆形区域内，无矩形

### Step 2：修复 Shallow Shelf

**改动范围**：
- `apply_shallow_water_shelf`：shelf_threshold 降至 0.11，新增 SHELF_GAIN_BOOST
- `NOON_AIR_OCEAN_REGIONS`：新增 `caribbean_shelf` 和 `bahamas_shelf` 条目

**预期效果**：Caribbean/Bahamas 浅海层次恢复；大陆架区域可感知渐变

### Step 3：修正 Special Seas

**改动范围**：
- `NOON_AIR_SPECIAL_SEAS`：红海 lit_delta 提升（+0.02→+0.10），feather 增加（12→16）
- `NOON_AIR_OCEAN_REGIONS`：yellow_sea_bohai hue_shift +8，sat_delta -0.06；east_china_sea hue_shift +7，sat_delta -0.04；sea_of_japan lit_delta +0.03；mediterranean lit_delta +0.01
- 可选：reef_floor_zones 中增加红海南北端 halo

**预期效果**：Red Sea 不再是黑沟；Yellow/East China B > G；Japan Sea lum ≥ 0.085

### Step 4：运行 2K calibration（需人工授权）

```bash
python3 d5b_processor_v3/d6_noon_air_earth_generator.py --calibration
```

禁止 `--full-res`，禁止复制到 candidates/，禁止 commit

### Step 5：人工视觉审查

按 §7 验收标准逐条检查。重点看：
1. diff heatmap 是否无矩形
2. Maldives / French Polynesia 细碎礁盘是否可见
3. Red Sea / Yellow East China 色调是否修正

### Step 6：决定是否 commit

- 如果 P0 + P1 全通过 → 可以 commit B-5.1 + B-5.2 + B-5.3 的累计改动，一次性入库
- 如果 P1 仍有问题 → 进入 B-5.4，继续局部参数调整
- 如果 P0 出现新矩形 → 必须先解决矩形再 commit

---

## 9. 已知风险与预案

| 风险 | 可能性 | 预案 |
|---|---|---|
| reef_floor_zone 的圆形边界仍可见（圆圈感）| 低（feather 充足）| 增大 feather_8k；降低 floor 强度 |
| island halo boost 导致荧光感 | 低（NOON_AIR_INTENSITY 仍在缩放）| 降低 ISLAND_HALO_LIT_BOOST |
| Yellow Sea hue_shift+8 过度偏蓝 | 中等 | 从 +6 开始逐步测试 |
| Red Sea lit_delta+0.10 仍然不够（2K 下水体太窄）| 中等 | 2K 下接受；等待 8K 验证 |
| Caribbean shelf ocean_region 与 reef_floor 重叠导致过亮 | 低（floor 是 max 保底，不叠加）| 检查 lum 上限 |
| 2K benchmark crop lum 提升不明显（crop 以深海为主）| 高 | 接受；以视觉感知而非数字为准 |

---

## 10. 与配色规范的对应关系

| 规范原则（v1.1） | B-5.3 措施 |
|---|---|
| 深海要清澈，不要黑（§0）| global floor 0.07 保底；deep ocean lit_delta 保持 0 |
| 浅海要发光，但不要荧光（§0）| reef floor inner 0.13–0.15；ISLAND_HALO_LIT_BOOST 轻推；无荧光青 |
| 群岛要有浅海光晕，不要只剩小点（§0）| apply_island_reef_floor 圆形保护；island halos 色调辅助 |
| 禁止大面积亮蓝色块（§15）| 所有 floor 使用 circle_mask，无 region_mask_rect |
| 浅滩边缘必须柔化（§8.2）| 所有 circle_mask 带 feather；reef floor 使用 softness |
| 不允许把整个马尔代夫区域涂成一片浅蓝（§8.3）| reef zone 半径 ≤ 200km，深海包围 |
| 群岛密集区域应形成细碎青蓝层次（§8.1）| 多个独立圆形 zone，各自为政 |
| 黄海不能变黄褐（§13.3）| hue_shift 大幅增加，sat_delta 转负 |
| 红海两岸冷暖对比（§13.2）| lit_delta 大幅增强，保持水体与沙漠对比 |
| 日本海明显偏深（§13.3）| lit_delta +0.03，目标 lum 0.09–0.10，不做过度提亮 |
