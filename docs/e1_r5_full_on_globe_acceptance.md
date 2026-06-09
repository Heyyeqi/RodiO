# E1-R5 Full On-globe Visual Acceptance

**Date:** 2026-06-09
**Primary candidate:** `d5z_b`
**Fallback candidate:** `d5z_a` (not pre-captured; execute only if d5z_b fails)
**Baseline comparison:** `d5b_design_v3_2_1` (5 key regions)
**DAY_TEXTURE_VARIANT:** unchanged (`bmng_d2`)
**Constraints:** DAY_TEXTURE_VARIANT unmodified · no production writes · no commit · no E1-R6 until RW authorization

---

## d5z_b — Primary Candidate

### Load Verification

| Check | Result |
|---|---|
| Console variant | `d5z_b` |
| Texture dimensions | 8192×4096 |
| Network HTTP status | 200 |
| earth3d.isReady | true |
| TUNE IN overlay dismissed | true |

All blocking checks **passed**.

### Geographic Screenshots (9 regions × 4 time modes)

| Region | morning | noon | afternoon | sunset |
|---|---|---|---|---|
| Sahara / Egypt | `e1r5_d5z_b_sahara_morning.png` (467KB) | `e1r5_d5z_b_sahara_noon.png` (472KB) | `e1r5_d5z_b_sahara_afternoon.png` (458KB) | `e1r5_d5z_b_sahara_sunset.png` (404KB) |
| Antarctica | `e1r5_d5z_b_antarctica_morning.png` (384KB) | `e1r5_d5z_b_antarctica_noon.png` (389KB) | `e1r5_d5z_b_antarctica_afternoon.png` (383KB) | `e1r5_d5z_b_antarctica_sunset.png` (320KB) |
| Greenland / Arctic | `e1r5_d5z_b_greenland_morning.png` (422KB) | `e1r5_d5z_b_greenland_noon.png` (427KB) | `e1r5_d5z_b_greenland_afternoon.png` (418KB) | `e1r5_d5z_b_greenland_sunset.png` (369KB) |
| Japan / East China Sea | `e1r5_d5z_b_japan_morning.png` (444KB) | `e1r5_d5z_b_japan_noon.png` (447KB) | `e1r5_d5z_b_japan_afternoon.png` (438KB) | `e1r5_d5z_b_japan_sunset.png` (395KB) |
| Mediterranean | `e1r5_d5z_b_mediterranean_morning.png` (466KB) | `e1r5_d5z_b_mediterranean_noon.png` (471KB) | `e1r5_d5z_b_mediterranean_afternoon.png` (458KB) | `e1r5_d5z_b_mediterranean_sunset.png` (411KB) |
| Caribbean | `e1r5_d5z_b_caribbean_morning.png` (423KB) | `e1r5_d5z_b_caribbean_noon.png` (427KB) | `e1r5_d5z_b_caribbean_afternoon.png` (417KB) | `e1r5_d5z_b_caribbean_sunset.png` (379KB) |
| Indian Ocean | `e1r5_d5z_b_indian_ocean_morning.png` (395KB) | `e1r5_d5z_b_indian_ocean_noon.png` (398KB) | `e1r5_d5z_b_indian_ocean_afternoon.png` (392KB) | `e1r5_d5z_b_indian_ocean_sunset.png` (350KB) |
| Pacific Islands | `e1r5_d5z_b_pacific_islands_morning.png` (325KB) | `e1r5_d5z_b_pacific_islands_noon.png` (332KB) | `e1r5_d5z_b_pacific_islands_afternoon.png` (328KB) | `e1r5_d5z_b_pacific_islands_sunset.png` (292KB) |
| Europe / Middle East (wide) | `e1r5_d5z_b_europe_middle_east_morning.png` (471KB) | `e1r5_d5z_b_europe_middle_east_noon.png` (475KB) | `e1r5_d5z_b_europe_middle_east_afternoon.png` (462KB) | `e1r5_d5z_b_europe_middle_east_sunset.png` (418KB) |

*Screenshots in `previews/e1_r5_full_acceptance/d5z_b/`*

### UI Integration Screenshots (standard player view)

| Time | File |
|---|---|
| morning | `e1r5_d5z_b_ui_player_morning.png` (453KB) |
| noon | `e1r5_d5z_b_ui_player_noon.png` (457KB) |
| afternoon | `e1r5_d5z_b_ui_player_afternoon.png` (444KB) |
| sunset | `e1r5_d5z_b_ui_player_sunset.png` (393KB) |

### Visual Assessment — Geographic Regions

| Region | morning | noon | afternoon | sunset | vs baseline |
|---|---|---|---|---|---|
| Sahara / Egypt | 暖色调，高亮可接受 | 高亮有所收敛，暖色保留 | 暖色沙漠质感稳定 | 低角度暖色自然 | 改善：高亮收敛，未灰化 |
| Antarctica | 冰盖亮度偏亮但可接受 | 亮度收敛，仍偏亮 | 冰面细节保留 | 低照度可接受 | Partial：仍偏亮，未脏化 |
| Greenland / Arctic | 雪地高亮偏亮但可接受 | 亮度收敛，仍偏亮 | 冰川质感保留 | 低照度可接受 | Partial：仍偏亮，未脏化 |
| Japan / East China Sea ⬡ | 保护区完好 | 保护区完好 | 保护区完好 | 保护区完好 | 无回退 |
| Mediterranean ⬡ | 保护区完好 | 保护区完好 | 保护区完好 | 保护区完好 | 无回退 |
| Caribbean ⬡ | 保护区完好 | 保护区完好 | 保护区完好 | 保护区完好 | 无回退 |
| Indian Ocean | 略有地图感 | 略有地图感 | 略有地图感 | 略有地图感 | 轻微改善，不构成阻断 |
| Pacific Islands ⬡ | 保护区完好 | 保护区完好 | 保护区完好 | 保护区完好 | 无回退 |
| Europe / Middle East (wide) | 无明显硬边界 | 无明显硬边界 | 无明显硬边界 | 无明显硬边界 | 通过 |

⬡ = Protected region (zero-regression required)

### Visual Assessment — UI Integration

| Criterion | morning | noon | afternoon | sunset |
|---|---|---|---|---|
| Waiting text / controls readable | Pass | Pass | Pass | Pass |
| Globe does not over-expose or overpower UI | Pass | Pass | Pass | Pass |
| Color harmony with light-blue UI background | Pass | Pass | Pass | Pass |
| Immersive background feel (not GIS map aesthetic) | Pass | Pass | Pass | Pass |

### Verdict — d5z_b

| Criterion | Pass / Fail / Partial | Notes |
|---|---|---|
| Antarctica / Greenland ice brightness improved | **Partial** | 亮度收敛，改善方向正确；仍偏亮，未见灰化或脏化 |
| Ice preserved near-neutral white (no grey / dirty) | **Pass** | channel spread delta 在可接受范围内，无灰化 |
| Sahara noon highlight reduced | **Pass** | 高亮有所收敛，暖色沙漠质感保留 |
| Sahara warm desert color preserved (not grey / green) | **Pass** | 未见灰化、绿化或过暗 |
| Indian Ocean deep texture reduced | **Partial** | 仍略有地图感；轻微改善，不构成阻断 |
| Europe / Middle East — no hard boundary at Sahara / Med border | **Pass** | 未见明显硬边界 |
| Cross-time-mode color consistency (no style jumps) | **Pass** | morning / noon / afternoon / sunset 跨 mode 整体稳定 |
| Japan no regression | **Pass** | 保护区无明显退步 |
| Mediterranean no regression | **Pass** | 保护区无明显退步 |
| Caribbean no regression | **Pass** | 保护区无明显退步 |
| Pacific Islands no regression | **Pass** | 保护区无明显退步 |
| UI Integration: controls readable, globe not over-exposed | **Pass** | 播放器标准视角四个 time mode 均可接受 |
| UI Integration: color harmony with light-blue background | **Pass** | 地球与浅蓝 UI 融合度可接受 |
| UI Integration: immersive, not GIS map feel | **Pass** | 整体呈现沉浸式背景感，非 GIS 截图感 |

**Partial count: 2 / 14 — 均在允许的极地亮度 / Indian Ocean 范畴内**

**Overall d5z_b: Conditional Pass**

**Reviewer:** RW  
**Date:** 2026-06-09  
**Authorized next step:** E1-R6 Production Decision only

---

## d5b_design_v3_2_1 — Baseline Comparison (5 key regions)

### Load Verification

| Check | Result |
|---|---|
| Console variant | `d5b_design_v3_2_1` |
| Texture dimensions | 8192×4096 |
| Network HTTP status | 200 |
| earth3d.isReady | true |

### Comparison Screenshots

| Region | morning | noon | afternoon | sunset |
|---|---|---|---|---|
| Sahara / Egypt | `e1r5_d5b_design_v3_2_1_sahara_morning.png` (459KB) | `e1r5_d5b_design_v3_2_1_sahara_noon.png` (464KB) | `e1r5_d5b_design_v3_2_1_sahara_afternoon.png` (450KB) | `e1r5_d5b_design_v3_2_1_sahara_sunset.png` (398KB) |
| Antarctica | `e1r5_d5b_design_v3_2_1_antarctica_morning.png` (390KB) | `e1r5_d5b_design_v3_2_1_antarctica_noon.png` (396KB) | `e1r5_d5b_design_v3_2_1_antarctica_afternoon.png` (385KB) | `e1r5_d5b_design_v3_2_1_antarctica_sunset.png` (338KB) |
| Greenland / Arctic | `e1r5_d5b_design_v3_2_1_greenland_morning.png` (419KB) | `e1r5_d5b_design_v3_2_1_greenland_noon.png` (424KB) | `e1r5_d5b_design_v3_2_1_greenland_afternoon.png` (415KB) | `e1r5_d5b_design_v3_2_1_greenland_sunset.png` (368KB) |
| Mediterranean | `e1r5_d5b_design_v3_2_1_mediterranean_morning.png` (458KB) | `e1r5_d5b_design_v3_2_1_mediterranean_noon.png` (463KB) | `e1r5_d5b_design_v3_2_1_mediterranean_afternoon.png` (450KB) | `e1r5_d5b_design_v3_2_1_mediterranean_sunset.png` (404KB) |
| Indian Ocean | `e1r5_d5b_design_v3_2_1_indian_ocean_morning.png` (390KB) | `e1r5_d5b_design_v3_2_1_indian_ocean_noon.png` (393KB) | `e1r5_d5b_design_v3_2_1_indian_ocean_afternoon.png` (387KB) | `e1r5_d5b_design_v3_2_1_indian_ocean_sunset.png` (345KB) |

*Screenshots in `previews/e1_r5_full_acceptance/d5b_design_v3_2_1/`*

---

## d5z_a — Fallback (not pre-captured)

Execute only if d5z_b Overall verdict = **Fail**.
Run with same 9 regions × 4 time modes. Assess against same E1-R5 criteria.

---

## Pass / Conditional Pass / Fail Criteria

### Pass (all criteria met)
All Verdict rows = Pass.

### Conditional Pass (enter E1-R6 with annotation)
- At most **2 criteria = Partial**
- Partial may only appear on: Antarctica / Greenland ice brightness, Indian Ocean deep texture, Pacific deep
- The following criteria **must be Pass** (Partial not allowed):
  - All 4 protected regions (Japan / Mediterranean / Caribbean / Pacific Islands)
  - Sahara warm color preserved (not grey / green)
  - Europe / Middle East — no hard boundary
  - Cross-time-mode color consistency
  - All 4 UI Integration criteria

### Fail (blocked, triggers fallback or D5z_c)
Any one of:
- Any protected region shows visible subjective regression vs d5b_design_v3_2_1
- Sahara appears grey, green, or noticeably over-darkened
- Antarctica / Greenland ice appears grey or dirty (not just darker)
- Hard boundary line visible in Europe / Middle East wide view
- Visible color jump or style discontinuity between time modes
- Any UI Integration criterion = Fail (UI unreadable, over-exposed)

---

## Fallback Procedure (if d5z_b Fails)

1. Document specific fail reason (region, time mode, criterion)
2. Execute d5z_a: `node e1r5_full_acceptance.js --variant=d5z_a` (or run equivalent script)
3. Assess d5z_a under same E1-R5 criteria
4. If d5z_a passes: use d5z_a as E1-R6 candidate; note D5z_b fail reason in report
5. If both fail: blocked — return to D5z_c parameter tuning; document fail points

---

## Remaining Issues (recorded for future phases)

| Issue | Severity | Planned stage |
|---|---|---|
| 当前配色非最终 RodiO Day Earth 目标风格 | Low — non-blocking | BMNG / RDL / Global Color Grading |
| 海洋通透感、浅海层次、陆地空气感、整体高级感不足 | Low — non-blocking | Global Color Grading phase |
| 极地仍偏亮（Antarctica / Greenland） | Low — Partial，已记录 | 后续全局调色阶段处理 |
| 深海仍略有 GIS 感（Indian Ocean / Pacific） | Low — Partial，已记录 | 后续全局调色阶段处理 |

以上问题**不在 D5z 阶段继续调参**。D5z 调参阶段在本次 E1-R5 Conditional Pass 后正式结束。

---

## Next Step

**E1-R5 Conditional Pass → RW 明确授权后进入 E1-R6 Production Decision。**

E1-R6 operations (all blocked until RW explicitly authorizes):
- Modify `DAY_TEXTURE_VARIANT` from `'bmng_d2'` to `'d5z_b'`
- Copy `d5z_b_8192x4096.jpg` from `candidates/` to `production/`
- Commit with standardized message
- Verify production default loads correctly on localhost

**边界：**
- E1-R5 Conditional Pass 不代表最终配色完成
- 不代表 BMNG / RDL 高精地球完成
- 不允许在本步骤直接修改 `DAY_TEXTURE_VARIANT`
- 不允许直接 commit
- 不允许直接 production 化

`DAY_TEXTURE_VARIANT` 保持 `'bmng_d2'`，直至 E1-R6 明确授权执行。