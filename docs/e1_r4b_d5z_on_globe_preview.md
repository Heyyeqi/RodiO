# E1-R4B D5z On-globe Preview Report

**Date:** 2026-06-09
**Variants tested:** d5z_b (primary), d5z_a (fallback reference)
**DAY_TEXTURE_VARIANT:** unchanged (`bmng_d2`)
**Constraints:** earth3d.js DAY_TEXTURE_VARIANT unmodified · no production writes · no commit

---

## d5z_b

### Load Verification

| Check | Result |
|---|---|
| Console variant | `d5z_b` |
| Texture dimensions | 8192×4096 |
| Network HTTP status | 200 |
| earth3d.isReady | true |
| TUNE IN overlay dismissed | true |

All blocking checks **passed**.

### Screenshots

| Region | noon | afternoon |
|---|---|---|
| Sahara / Egypt | `e1r4b_d5z_b_sahara_noon.png` (493KB) | `e1r4b_d5z_b_sahara_afternoon.png` (481KB) |
| Antarctica | `e1r4b_d5z_b_antarctica_noon.png` (404KB) | `e1r4b_d5z_b_antarctica_afternoon.png` (399KB) |
| Greenland / Arctic | `e1r4b_d5z_b_greenland_noon.png` (445KB) | `e1r4b_d5z_b_greenland_afternoon.png` (437KB) |
| Pacific Islands | `e1r4b_d5z_b_pacific_islands_noon.png` (347KB) | `e1r4b_d5z_b_pacific_islands_afternoon.png` (344KB) |
| Japan / East China Sea | `e1r4b_d5z_b_japan_noon.png` (462KB) | `e1r4b_d5z_b_japan_afternoon.png` (454KB) |
| Mediterranean | `e1r4b_d5z_b_mediterranean_noon.png` (491KB) | `e1r4b_d5z_b_mediterranean_afternoon.png` (479KB) |
| Caribbean | `e1r4b_d5z_b_caribbean_noon.png` (444KB) | `e1r4b_d5z_b_caribbean_afternoon.png` (434KB) |
| Indian Ocean | `e1r4b_d5z_b_indian_ocean_noon.png` (414KB) | `e1r4b_d5z_b_indian_ocean_afternoon.png` (408KB) |

*Screenshots in `previews/e1_r4b_d5z_on_globe_preview/d5z_b/`*

### Visual Assessment

| Region | noon | afternoon | vs d5b_design_v3_2_1 baseline |
|---|---|---|---|
| Sahara / Egypt | 正午高亮有所降低 | 暖色沙漠质感保留 | 改善，不过暗，未变灰 |
| Antarctica | 冰盖亮度收敛 | 斜光下可见冰面细节 | 改善，无明显灰化 |
| Greenland / Arctic | 雪地高亮降低 | 冰川质感保留 | 改善，未变脏 |
| Pacific Islands | 岛礁色调自然 | 保护区未见误伤 | 无回退 |
| Japan / East China Sea | 海岸线清晰，无误伤 | 保护区完好 | 无回退 |
| Mediterranean | 蓝色海域正常 | 保护区完好 | 无回退 |
| Caribbean | 岛礁与浅海色调正常 | 保护区完好 | 无回退 |
| Indian Ocean | 深海仍略有地图感 | 略有改善 | 轻微改善，不构成阻断 |

### Verdict

| Criterion | Pass / Fail / Partial | Notes |
|---|---|---|
| Antarctica / Greenland ice not over-bright | **Pass** | 亮度收敛，−12.7% / −7.7% |
| Ice detail preserved, not grey / dirty | **Pass** | channel spread delta −0.42 / −0.16，更趋中性 |
| Sahara warm desert color preserved | **Pass** | −2.79% 降亮，暖色调保留 |
| Sahara not over-darkened / not grey | **Pass** | 未见灰化，沙漠质感完好 |
| Indian Ocean deep texture reduced | **Partial** | −4.28% 去饱和，仍略有地图感，不构成阻断 |
| Overall globe not noticeably darker than baseline | **Pass** | 极地冰盖收敛明显，其余区域无显著整体暗化 |
| Japan / Mediterranean / Caribbean / Pacific Islands no regression | **Pass** | PSNR ∞ / diff 0（Japan / Med / Caribbean），Pacific Islands 63 dB |

**Overall: Conditional Pass**

---

## d5z_a

### Load Verification

| Check | Result |
|---|---|
| Console variant | `d5z_a` |
| Texture dimensions | 8192×4096 |
| Network HTTP status | 200 |
| earth3d.isReady | true |
| TUNE IN overlay dismissed | true |

All blocking checks **passed**.

### Screenshots

| Region | noon | afternoon |
|---|---|---|
| Sahara / Egypt | `e1r4b_d5z_a_sahara_noon.png` (493KB) | `e1r4b_d5z_a_sahara_afternoon.png` (481KB) |
| Antarctica | `e1r4b_d5z_a_antarctica_noon.png` (404KB) | `e1r4b_d5z_a_antarctica_afternoon.png` (399KB) |
| Greenland / Arctic | `e1r4b_d5z_a_greenland_noon.png` (445KB) | `e1r4b_d5z_a_greenland_afternoon.png` (436KB) |
| Pacific Islands | `e1r4b_d5z_a_pacific_islands_noon.png` (347KB) | `e1r4b_d5z_a_pacific_islands_afternoon.png` (343KB) |
| Japan / East China Sea | `e1r4b_d5z_a_japan_noon.png` (462KB) | `e1r4b_d5z_a_japan_afternoon.png` (454KB) |
| Mediterranean | `e1r4b_d5z_a_mediterranean_noon.png` (491KB) | `e1r4b_d5z_a_mediterranean_afternoon.png` (479KB) |
| Caribbean | `e1r4b_d5z_a_caribbean_noon.png` (444KB) | `e1r4b_d5z_a_caribbean_afternoon.png` (434KB) |
| Indian Ocean | `e1r4b_d5z_a_indian_ocean_noon.png` (414KB) | `e1r4b_d5z_a_indian_ocean_afternoon.png` (408KB) |

*Screenshots in `previews/e1_r4b_d5z_on_globe_preview/d5z_a/`*

### Visual Assessment

| Region | noon | afternoon | vs d5b_design_v3_2_1 baseline |
|---|---|---|---|
| Sahara / Egypt | 正午高亮与 D5z_b 相当（无 Sahara 校正） | 暖色保留 | 与 baseline 差异小于 D5z_b |
| Antarctica | 同 D5z_b（极地校正相同） | 同 D5z_b | 与 D5z_b 等效 |
| Greenland / Arctic | 同 D5z_b | 同 D5z_b | 与 D5z_b 等效 |
| Pacific Islands | 保护区完好 | 保护区完好 | 无回退 |
| Japan / East China Sea | 保护区完好 | 保护区完好 | 无回退 |
| Mediterranean | 保护区完好 | 保护区完好 | 无回退 |
| Caribbean | 保护区完好 | 保护区完好 | 无回退 |
| Indian Ocean | 与 D5z_b 等效（深海校正相同） | 等效 | 轻微改善 |

### Verdict

| Criterion | Pass / Fail / Partial | Notes |
|---|---|---|
| Antarctica / Greenland ice not over-bright | **Pass** | 与 D5z_b 等效 |
| Ice detail preserved, not grey / dirty | **Pass** | 与 D5z_b 等效 |
| Sahara warm desert color preserved | **N/A** | D5z_a 不含 Sahara 校正 |
| Sahara not over-darkened / not grey | **Pass** | 无操作，无风险 |
| Indian Ocean deep texture reduced | **Partial** | 与 D5z_b 等效 |
| Overall globe not noticeably darker than baseline | **Pass** | 与 D5z_b 等效 |
| Japan / Mediterranean / Caribbean / Pacific Islands no regression | **Pass** | 与 D5z_b 等效 |

**Overall: Conservative fallback — preserved for D5z_b 失败时启用**

---

## Next Step

**D5z_b: Conditional Pass → 进入 E1-R5 Full On-globe Visual Acceptance**

- 主候选：`d5z_b`
- Fallback 备选：`d5z_a`（极地 + 深海校正，不含 Sahara）

**边界条件：**
- 本结论**只允许**进入 E1-R5，不允许修改 `DAY_TEXTURE_VARIANT`
- 不允许 commit
- 不允许 production 化
- E1-R5 通过后，才进入 E1-R6 Production Decision

`DAY_TEXTURE_VARIANT` 保持 `'bmng_d2'`，直至 E1-R5 正式通过。