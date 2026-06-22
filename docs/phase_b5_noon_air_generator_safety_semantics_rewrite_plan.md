# Phase B-5 — Noon Air Generator Safety Semantics Rewrite Plan

> Created: 2026-06-10
> Status: Design document only — no code modified, no images generated, no generator executed
> Preceding audit: `docs/phase_b4_noon_air_calibration_failure_root_cause_audit.md`
> Subject: `d5b_processor_v3/d6_noon_air_earth_generator.py`
> Commits on record: edd816f (calibration mode), ca4d1d7 (audit doc)

---

## 1. Phase B-5 目标

本阶段**不是**追求最终 Noon Air 成图，也不是调参。目标是重写 generator 的工程安全语义，使下一次 2K calibration 在工程层面可信、可审查、不引入人工伪影。

具体目标：

- 下一次 2K calibration 输出不得出现可见矩形 patch
- 深海区域（全球）不得大面积趋近极暗/黑色
- Maldives、French Polynesia、Bahamas、Pacific Islands 的浅海 halo 不得被吞没
- `apply_final_harmony_guard` 在 calibration 模式下不得直接修改像素
- 所有经纬度 bbox mask 必须携带 feather，禁止 `feather_px=0`

持续禁令（所有阶段适用）：

- 禁止运行 8K（`--full-res`）
- 禁止复制任何输出到 `candidates/`
- 禁止修改前端（`pwa/`，`earth3d.js`，`DAY_TEXTURE_VARIANT`）
- 禁止修改 production texture
- calibration 输出不视为正式 candidate
- 禁止 commit / push（除非明确授权）

---

## 2. P0 必须修复项

以下七项是下一次 2K calibration 必须解决的最高优先级问题，任何一项未修复均会导致视觉审查失败。

### 2.1 `apply_final_harmony_guard`：从 image-mutating 改为 diagnostic-only

**问题**：当前实现在 guard FAIL 时对受保护区执行像素修改（`blend_back=0.70`，`feather_px=0`）。这直接产生矩形 patch，且无法解决 source-to-d5z_b 固有亮度差距。

**修复方向**：calibration 模式下，guard 只记录每个受保护区的 `rgb_delta` / `lum_delta` 数值，写入警告日志，不执行任何像素混合。guard 的作用应仅为诊断，而非试图自动修正。

### 2.2 protected region guard 不得执行 70% hard blend-back

**问题**：当前 `blend_back = min((excess - 1.0) * 0.4, 0.7)` 对 4 个受保护区全部钳位至 0.70。由于 source 比 d5z_b 本身偏暗约 90 rgb_delta，blend-back 无法达标，同时引入矩形边界。

**修复方向**：去除 blend-back 执行路径。如果未来需要局部回退，必须通过独立的、有 feather 的软权重实现，且仅在 production eligibility 阶段考虑，不在 calibration 阶段执行。

### 2.3 所有 bbox mask 必须有 feather，禁止 `feather_px=0`

**问题**：`apply_final_harmony_guard`（第 913 行）使用 `feather_px=0`，产生硬矩形边界。`region_mask_rect` 的 `feather` 参数支持羽化，但 guard 未传入。

**修复方向**：`apply_final_harmony_guard` 中所有 `region_mask_rect` 调用必须使用 `scale_feather(40, W)` 作为基准 feather（8K 下 40px，2K 下等比缩放约 10px）。若 guard 改为 diagnostic-only，则不再需要生成 mask，此条作为 mask 生成的最低要求，仅用于诊断区域 pixel 计数。

### 2.4 `apply_ocean_system` 不得基于已修改的 `out` 重算 `deep_ocean_px`

**问题**：priority loop 中每轮都通过 `deep_ocean_px(out)` 重新计算深海 mask，基于当前已修改的 `out`。Priority 0（`global_deep_base`）先压暗后，Priority 1 的区域扫描时部分原本"不是深海"的像素可能被重新归类，造成级联压暗。

**修复方向**：在 loop 开始前预计算一次 `deep_mask = deep_ocean_px(f32_original)`（基于 source 输入），所有 `deep_only` 区域共用此固定 mask，不再每轮重新计算。

### 2.5 增加 ocean / shallow sea / reef / island halo minimum luminance floor

**问题**：整个 pipeline 缺少最低亮度保护。极暗区域（lum < 0.18）完全不受任何模块增亮，raw BMNG 的暗值原样穿透。Maldives 深印度洋区域 lum ≈ 0.039，French Polynesia ≈ 0.071，均接近全黑。

**修复方向**：在 `apply_ocean_system` 结束后增加独立 luminance floor 模块：
- 全局 ocean floor：lum 不低于 0.10（约 25.5/255）
- 浅海区域（由 `ocean_px` 且 lum < 0.25 判定）floor：0.13
- tropical shallow sea / reef / island halo 区域（Maldives、Polynesia、Bahamas、Caribbean、Hawaii 附近）：floor 不低于 0.16

Floor 修正以软混合方式施加（不硬钳制），避免引入灰雾。

### 2.6 shallow sea / island halo 必须移到后段保护，或在 final pass 后重新应用

**问题**：Module 4（island halos）在 Module 10（harmony guard）之前执行。harmony guard 的 blend-back 覆盖了 4 个受保护区内的所有 island halo 增亮（Bahamas、Hawaii、Fiji、French Polynesia 等）。Module 3（shallow_water_shelf）同理。

**修复方向**：一旦 harmony guard 改为 diagnostic-only，Module 10 不再修改像素，此覆盖问题自然消除。但如果未来任何 final pass 仍需执行全局调整，island halo 的增亮必须在 final pass 之后重新保护（或排除在 final pass 作用范围之外）。

### 2.7 Maldives / French Polynesia / Pacific Islands 必须有单独保护策略

**问题**：这三个区域在 `NOON_AIR_INTENSITY=0.38` 下，island halo 单像素 L 净增量约 0.0023（接近舍入误差），完全无法补偿深海黑化。

**修复方向**：引入 tropical deep ocean min-luminance 专项保护，通过区域化 floor 优先于全局 floor 生效。不依赖 island halo 混合强度，而是直接设定该区域 ocean 像素的亮度下限。Maldives 的 Indian Ocean、French Polynesia 的 South Pacific、Bahamas 的 Caribbean 各自设独立 floor 值。

---

## 3. P1 第二优先级修复项

### 3.1 desert correction 的 darken 公式 bug（第 746–748 行）

**问题（静态分析已确认）**：

```python
# 当前代码（第 746-748 行）
darken = 0.06 * i
out = out * (1.0 - apply_mask[:, :, np.newaxis] * darken) + \
      out * (1.0 - darken) * apply_mask[:, :, np.newaxis]
```

展开后等同于：`out × [1 + apply_mask × (1 - 2×darken)]`

当 `darken = 0.06 × 0.38 = 0.0228`，`(1 - 2×darken) = 0.954`，在 `apply_mask ≈ 1` 的极亮像素处有效乘数为 `1.954`，而不是预期的 `0.977`，产生增亮而非压暗。

**修复方向**：正确写法应为：

```python
out = out * (1.0 - apply_mask[:, :, np.newaxis] * darken)
```

同样的 bug 存在于 Arabia（第 758–759 行）。两处均需修正。

### 3.2 land vegetation 的 bbox feather 半径过小

`apply_land_vegetation` 的三个热带雨林矩形区域（Amazon、Congo、SEA）使用 `scale_feather(12, W)`，在 2K 下约 3px。对于大范围区域（跨越约 25° 纬度 × 30° 经度的 Amazon），3px feather 不足以消除边界感。

**修复方向**：热带雨林区域 feather 建议增至 `scale_feather(24, W)` 以上。

### 3.3 Red Sea / Yellow East China Sea 不能只用矩形 bbox 处理水体

Red Sea 水体形状高度非矩形（细长弯曲），Yellow Sea 含大量陆架泥沙。矩形 bbox 处理不可避免地覆盖周围陆地（阿拉伯半岛、中国海岸）。

**修复方向**：`apply_special_seas` 已使用 `ocean_px` 门控（`combined = rmask * ocean`），方向正确，但 feather_px 过小（Red Sea 约 3px）。建议将这些区域的 feather 增至 `scale_feather(24, W)`，同时引入 land mask 保护，确保陆地像素完全排除在处理之外。

### 3.4 protected region metrics 继续保留，但不得直接决定像素混合

当前 `run_baseline_floor_guard` 已将 metrics 计量与像素修改分离（仅记录，不修改），应保留并扩展。`apply_final_harmony_guard` 的 metrics 计算逻辑也应保留，但全部路径均改为写日志，不触发 `blended = out * ... + baseline_f32 * ...` 操作。

### 3.5 calibration mode、8K eligibility、production eligibility 必须分层

当前三者混在一个函数中。分层原则：
- calibration 模式：只允许 2K 输出，只写诊断，不允许 8K
- 8K eligibility：独立评估函数，只在 calibration 通过人工审查后才调用
- production eligibility：双确认（数值 + 人工授权），只在 8K 结果通过审查后才允许

---

## 4. `apply_final_harmony_guard` 新语义设计

### 4.1 旧语义（当前实现）

| 方面 | 行为 |
|---|---|
| 触发条件 | `rgb_delta > 8.0` 或 `lum_delta > 0.04` |
| 像素修改 | 对受保护区执行 `blend_back = min(0.7, ...)` 的 70% 混合 |
| Feather | `feather_px=0`，硬矩形边界 |
| 后果 | 矩形 patch 可见；无法关闭 source-to-d5z_b 亮度差距；抹去前 9 个模块工作成果 |

### 4.2 新语义（Phase B-5 设计目标）

| 方面 | 行为 |
|---|---|
| calibration 模式 | 只记录 fail，不修改任何像素 |
| normal preview 模式 | 不允许硬矩形 blend；如有回退需求，仅通过 feathered mask + 低权重 + 局部连续性实现 |
| production eligibility | 只决定是否允许进入 8K / production，不修改图像 |
| 未来回退实现 | 若确实需要，只能通过 feathered mask（`scale_feather ≥ 40px`）+ weight ≤ 0.2 实现，当前阶段不实现 |

### 4.3 建议拆分为以下函数

```
compute_protected_region_diagnostics(f32, baseline_f32, LAT, LON, log)
    → 计算每个受保护区的 rgb_delta, lum_delta, pixel_count
    → 无像素修改，返回 dict

evaluate_calibration_safety(diagnostics, log)
    → 判断当前输出是否满足 2K calibration 最低要求
    → 返回 {pass: bool, warnings: [str]}
    → 不修改图像

evaluate_8k_eligibility(diagnostics, log)
    → 判断是否允许 --full-res
    → 只在人工审查后调用，不自动触发
    → 不修改图像

evaluate_production_eligibility(diagnostics, calibration_result, log)
    → 判断是否允许进入 pwa/assets/earth/production 或前端注册
    → 需要外部人工授权标志，不自动触发
    → 不修改图像

write_calibration_warning_metadata(diagnostics, calibration_result, output_path)
    → 将诊断结果写入 JSON / 文本摘要
    → 随 calibration 输出一起保存
```

**当前阶段**只允许实现 `compute_protected_region_diagnostics` 和 `evaluate_calibration_safety` + `write_calibration_warning_metadata`。8K 和 production eligibility 函数可作为存根留待后续。

---

## 5. Ocean system 修复方案

### 5.1 fixed-mask 替代 dynamic-mask

当前 `apply_ocean_system` 中 `deep_ocean_px(out)` 在 priority loop 的每次迭代中基于当前 `out` 重新计算。

**建议**：在函数入口预计算 `deep_mask_fixed = deep_ocean_px(f32_original)`，loop 内所有 `deep_only=True` 的区域使用此固定 mask，不再重新计算。这消除级联压暗的累积机制。

### 5.2 deep ocean 亮度方向调整

当前所有深海区域的 `lit_delta` 均为负数（-0.01 至 -0.02），系统性偏暗。raw BMNG 深海本身已比 d5z_b 暗约 60 rgb_delta，在此基础上继续压暗没有意义。

**建议**：将 `global_deep_base`、`pacific_deep_north`、`pacific_deep_south`、`atlantic_deep`、`indian_ocean_deep` 的 `lit_delta` 从负数调整为 0（保留 hue_shift 和 sat_delta 方向），`sea_of_japan` 的 `lit_delta=-0.03` 改为 0。仅通过色相和饱和度调整实现深海色调，不进行亮度压暗。

### 5.3 luminance floor 机制

在 `apply_ocean_system` 结束后，插入独立 `apply_ocean_luminance_floor` 模块：

- 全局 ocean floor：lum ≥ 0.10
- 浅海代理区域（shallow proxy > 0 的像素）：lum ≥ 0.13
- tropical 保护区（Maldives、Polynesia、Caribbean、Hawaii 经纬度范围）：lum ≥ 0.16

Floor 修正以软混合施加（建议混合权重 ≤ 0.6），保留原始色相，只提升亮度通道，避免灰雾。

### 5.4 shallow sea 保护优先级

浅海（continental shelf）不得被 deep ocean 处理覆盖。在区域 priority 设计中，shelf 区域（Yellow Sea、East China Sea、Caribbean shelf 等）应在 priority loop 中明确标记为 `deep_only=False`，并在固定 deep_mask 计算后排除。浅海像素一旦通过 shelf 区域处理，不得再被 deep 逻辑覆盖。

### 5.5 Red Sea / Yellow East China Sea 专项保护

- Red Sea：`lit_delta` 从 +0.02 增至 +0.04，feather 从 ~3px 增至 `scale_feather(24, W)`
- Yellow Sea / East China Sea：调整 hue_shift 以修正绿泥色（当前 G=46.4 > B=38.8 > R=35.6），建议降低 G 通道的 sat_delta，或引入专项 hue 修正

---

## 6. Shallow sea / island halo 修复方案

### 6.1 执行顺序调整

Island halos（Module 4）和 shallow_water_shelf（Module 3）的增亮效果必须在 pipeline 最后一个修改像素的全局 pass 之后仍然有效。

当前危险顺序：`Module 3 → Module 4 → ... → Module 10（blend-back 覆盖）`

修复后（harmony guard 改为 diagnostic-only）：Module 10 不修改像素，覆盖问题自然消除。

若未来引入任何新的 final 全局 pass，island halo 保护必须在该 pass 之后重新执行，或在该 pass 中通过 island halo mask 排除 halo 区域。

### 6.2 必检 benchmark 区域

以下五个区域是每次 2K calibration 的强制视觉检查点：

| 区域 | 检查项 |
|---|---|
| Maldives (lon=73.5, lat=3.5) | 深印度洋 lum 不得接近黑色，岛礁 halo 必须可辨 |
| French Polynesia (lon=-149, lat=-17.5) | 不得出现上下硬切；上方不得有异常亮带 |
| Bahamas / Caribbean (lon=-77, lat=24) | 浅海层次（礁盘–深海过渡）必须可见 |
| Hawaii (lon=-156, lat=20) | 不得出现 Pacific Islands protected region 矩形边界 |
| Fiji (lon=178, lat=-17.5) | crop 跨反子午线时不得出现 edge padding 错误 |

### 6.3 halo 在 2K 下的最低可见性

2K 分辨率下 Maldives 岛礁仅约 1–3 像素。Island halo 半径在 2K 下约 5px（100km 对应），必须确保 halo mask 内像素在最终输出中 lum ≥ 0.18，不得因全局压暗被覆盖。

### 6.4 全局压暗禁止覆盖 island halo

任何全局 lit_delta 负值调整（包括 ocean system、atmosphere overlay）在 island halo mask 区域内应被排除，或 island halo 的 floor 保护在全局调整之后独立执行。

---

## 7. Bbox / feather 修复方案

### 7.1 所有 bbox 必须 feather

`apply_final_harmony_guard`（当前 `feather_px=0`）是唯一违反此规则的函数。其余模块（ocean、desert、vegetation、mountains、special_seas）均已使用 `scale_feather`，方向正确。

### 7.2 feather 缩放公式

所有 bbox mask 使用统一缩放公式（已在 generator 中实现为 `scale_feather(fpx_8k, W)`）：

```
feather_px = round(fpx_8k * W / 8192)
```

最低 feather floor：不得低于 `max(scale_feather(fpx_8k, W), 2)`，确保 2K 下也有最低 2px feather。

### 7.3 feather 半径参考值

| 区域类型 | 建议 `fpx_8k` | 2K 等效 |
|---|---|---|
| harmony guard 受保护区（大范围） | 40px | 10px |
| desert correction（Sahara/Arabia） | 24px | 6px（当前 16→建议 24） |
| land vegetation（热带雨林） | 24px | 6px（当前 12→建议 24） |
| special seas（Red Sea） | 24px | 6px（当前 12→建议 24） |
| mountain plateaus | 20px | 5px（当前合理） |
| island halos（圆形，非 bbox） | 已有羽化，无需修改 |

大区域 feather 必须明显大于小区域，避免视觉边界感。

### 7.4 跨经度区域处理

Pacific Islands 受保护区（lon 140–220，跨反子午线）使用 `cross_antimeridian` 路径，逻辑已实现，但在 diagnostic-only 模式下，mask 只用于计数，不用于混合，因此不影响视觉。

French Polynesia（lat=-17.5）超出 Pacific Islands 受保护区的 lat_min=-15，导致 French Polynesia crop 上部（行 571–597）被 blend-back 拉亮，下部（行 598–651）保持极暗，产生上下硬切。修复方案：在 harmony guard 改为 diagnostic-only 后，此问题自然消除，因为不再执行 blend-back。

---

## 8. Guard 分层设计

以下四层 guard 设计覆盖从 calibration 到 production 的完整路径：

### Layer 1：Diagnostic Guard（当前阶段实现）

- **目的**：量化每个受保护区相对于 d5z_b baseline 的差距
- **触发时机**：每次 calibration 输出时自动运行
- **行为**：只记录数值，不阻止输出，不修改任何像素
- **输出**：写入 calibration summary JSON 和文本报告
- **对应函数**：`compute_protected_region_diagnostics` + `run_baseline_floor_guard`

### Layer 2：Calibration Safety Guard（当前阶段实现）

- **目的**：判断当前 calibration 输出是否满足"允许人工视觉审查"的最低工程要求
- **触发时机**：diagnostic guard 完成后
- **行为**：评估是否通过，写入警告，**不修改图像**；允许 2K 输出写入 `calibration/` 目录
- **阻止条件**：不阻止 2K 输出，但若检测到极端问题（如全局 lum < 0.05）则写入 CRITICAL 标记
- **8K 阻止**：此 guard 同时阻止 `--full-res` 路径
- **对应函数**：`evaluate_calibration_safety`

### Layer 3：8K Eligibility Guard（仅在人工授权后调用）

- **目的**：判断是否允许执行 `--full-res` 8K 生成
- **触发时机**：人工审查 2K calibration 通过后，由外部标志激活
- **行为**：评估 8K 准入条件（数值 + 人工确认），不自动触发，不修改图像
- **当前阶段**：作为存根留待后续，不实现
- **对应函数**：`evaluate_8k_eligibility`

### Layer 4：Production Guard（仅在 8K 审查通过后调用）

- **目的**：判断是否允许将候选图注册到 `pwa/assets/earth/production/` 或前端
- **触发时机**：8K 输出通过人工视觉审查后，需双重确认（数值 + 显式人工授权）
- **行为**：检查所有 production 准入条件，不修改图像，输出授权报告
- **当前阶段**：不实现，不可触发
- **对应函数**：`evaluate_production_eligibility`

**当前 Phase B-5 只允许实现 Layer 1 和 Layer 2。Layer 3/4 禁止激活。**

---

## 9. 下一次 2K calibration 最低验收标准

以下 10 条是下一次 2K calibration 人工视觉审查的通过门槛，**全部必须满足**：

| # | 检查项 | 通过条件 |
|---|---|---|
| 1 | 矩形 patch | full candidate 不得出现任何可见矩形 patch（包括 Japan、Mediterranean、Caribbean、Pacific Islands 4 个区域） |
| 2 | 全局亮度 | 全局 luminance 不得大幅低于 d5z_b（rgb_delta 不得超过 40；当前为 50+，目标 ≤ 35） |
| 3 | Maldives | 深印度洋区域 lum 不得接近黑色（目标 lum > 0.10，当前 0.039） |
| 4 | French Polynesia | 不得出现上下硬切亮度边界；整体区域不得极暗（lum > 0.08） |
| 5 | Bahamas / Caribbean | 浅海–深海过渡层次必须可辨，礁盘浅蓝不得完全消失 |
| 6 | Yellow / East China Sea | 不得呈现绿泥色（B 通道不得显著低于 G 通道） |
| 7 | Red Sea | 不得成为黑沟（lum > 0.15），水体与陆地边界不得有硬矩形感 |
| 8 | Antarctica / Greenland | 不得死白过曝（lum < 0.90），保留纹理细节 |
| 9 | Sahara | 不得过曝（lum < 0.85），与周边区域过渡自然 |
| 10 | Japan | 不得出现矩形 patch（当前为最严重矩形之一，rgb_delta=18.50）；本州岛海岸线过渡自然 |

---

## 10. 建议 patch plan

以下顺序是后续代码修改的建议执行序列。**不在本轮执行，仅作为工程计划参考。**

```
Step 1. 重写 apply_final_harmony_guard 为 diagnostic-only
         - 移除所有 blend_back 和 rm3 混合逻辑
         - 提取为 compute_protected_region_diagnostics
         - 提取 evaluate_calibration_safety（仅写警告）

Step 2. 修复 bbox feather
         - apply_final_harmony_guard 中 feather_px=0 → scale_feather(40, W)
           （即使 guard 已是 diagnostic-only，mask 生成也须有 feather 以备未来复用）
         - desert_correction feather_px_8k: 16 → 24
         - land_vegetation feather_px_8k: 12 → 24
         - special_seas Red Sea feather_px_8k: 12 → 24

Step 3. 修复 ocean system fixed-mask 和 luminance floor
         - 预计算 deep_mask_fixed = deep_ocean_px(f32_original)
         - priority loop 中 deep_only 区域使用 deep_mask_fixed
         - 将所有深海 lit_delta 从负数调整为 0
         - 插入 apply_ocean_luminance_floor 模块

Step 4. 修复 shallow sea / island halo 顺序
         - 确认 Module 3/4 在 Module 10 之后是否有效（随 guard 改为 diagnostic-only 自然修复）
         - 如有新 final pass 引入，确保 island halo 在其后重新保护

Step 5. 修复 desert darken bug
         - 第 746-748 行：将双项公式改为单项 `out * (1.0 - apply_mask * darken)`
         - 同步修复第 758-759 行（Arabia）

Step 6. 增加 metrics 和 debug 输出
         - 每个模块前后记录 global lum mean
         - 记录每个 benchmark 区域在每个模块后的 lum 变化

Step 7. 只运行 2K calibration（--calibration 模式）
         - 禁止 --full-res
         - 输出到 calibration/ 子目录

Step 8. 人工视觉审查（按 §9 的 10 条标准逐一检查）

Step 9. 审查通过后再决定是否允许 8K
         - 需要明确授权，不自动触发
```

---

## 11. 风险提示

修复过程中存在以下工程风险，必须在每次 2K calibration 后仔细审查：

### 11.1 只修 guard 可能暴露 source-derived 原始暗底

`apply_final_harmony_guard` 改为 diagnostic-only 后，受保护区不再被 blend-back 拉向 d5z_b。由于 d5z_b 比 raw BMNG source 亮约 90 rgb_delta，移除 blend-back 后，这些区域可能**变得更暗**（因为不再借助 d5z_b 的亮度锚）。必须同步修复 ocean luminance floor，否则矩形 patch 消失但黑海问题加重。

### 11.2 只加亮度 floor 可能造成灰雾

如果 luminance floor 施加方式过强（如直接钳制至 floor 值，无软混合），极暗区域会整体变灰，失去深海应有的深色调。Floor 修正必须以软混合方式施加（混合权重 ≤ 0.6），保留原始色相，只在亮度极端不足时介入。

### 11.3 只增强浅海可能造成荧光

增加 island halo 或 shallow sea floor 时，如果 sat_delta 同步升高，在 2K 下浅海区域可能出现荧光蓝/绿色。Island halo 的 sat_delta 应保守（≤ +0.03），或与 lit_delta 的软混合权重挂钩，lit_delta 过大时自动降低 sat_delta。

### 11.4 bbox feather 过大可能造成区域污染

如果 feather 半径过大（例如 Sahara 的 feather 超过 30° 经纬度范围的 1/4），羽化区域可能覆盖到周边海洋（Mediterranean、Red Sea），将陆地处理效果渗入海洋区域。建议 feather 上限为区域长度的 1/8。

### 11.5 因此必须先 2K calibration，不得直接 8K

以上四条风险均会在 2K calibration 输出中可见，且可在人工审查时捕获。8K 输出在发现问题时代价远高于 2K。**任何修复后的第一次输出必须是 2K calibration 模式，不得跳过。**

---

## 附录：关键代码位置参考

| 函数 | 行号（1339 行文件） | 问题 |
|---|---|---|
| `apply_ocean_system` priority loop | 约第 300–420 行 | `deep_ocean_px(out)` 动态重算 |
| `apply_island_halos` | 约第 450–550 行 | 有效强度 × 0.076，接近无效 |
| `apply_desert_correction` | 第 730–779 行 | darken bug 第 746-748 行 |
| `apply_land_vegetation` | 第 786 行起 | feather 偏小 |
| `apply_final_harmony_guard` | 第 895–938 行 | `feather_px=0`，blend-back 70% |
| `run_baseline_floor_guard` | 第 945 行起 | 计量正确，不修改像素（保留） |

---

> 严格遵守以下禁止事项：
> - ✅ 未修改 `d5b_processor_v3/d6_noon_air_earth_generator.py`
> - ✅ 未运行 generator
> - ✅ 未生成任何 jpg / png
> - ✅ 未进入 8K
> - ✅ 未复制到 candidates/
> - ✅ 未修改前端
> - ✅ 未 commit
> - ✅ 未 push
