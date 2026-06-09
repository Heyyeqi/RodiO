# E1-R2.7 Source-derived 8K Preview

## Scope
- Input: `pwa/assets/source/earth_day_source_21600x10800.jpg`
- Comparison targets: `pwa/assets/earth/candidates/bmng_d2_8192x4096.jpg`, `pwa/assets/earth/candidates/d5b_design_v3_2_1_8192x4096.jpg`
- Output only to `previews/e1_r2_7/`; no candidates, no code changes.

## Input Confirmation
| 文件 | 尺寸 | 体积 | 色彩模式 | 是否可读取 | 用途 |
|---|---:|---:|---|---|---|
| `earth_day_source_21600x10800.jpg` | 21600x10800 | 21206743 | RGB | yes | high-res source |
| `bmng_d2_8192x4096.jpg` | 8192x4096 | 7909709 | RGB | yes | baseline comparison |
| `d5b_design_v3_2_1_8192x4096.jpg` | 8192x4096 | 8409768 | RGB | yes | current target comparison |

## Preview Generation
| 项目 | 值 |
|---|---|
| 算法 | Lanczos downsample (`PIL.Image.Resampling.LANCZOS`) |
| 输入尺寸 | 21600x10800 |
| 输出尺寸 | 8192x4096 |
| 输出体积 | 6346462 bytes |
| 是否可打开 | yes |

## Region Comparison Method
- All regions are cropped from the same lat/lon anchor on the three 8K images.
- Crop size: 640x320 per region.
- Metrics are computed on the crop window only.
- `edge_density` uses a grayscale gradient threshold; `local_contrast` uses grayscale std; `Lab L*` uses sRGB → XYZ → CIELab conversion.

## Region Verdict Summary
| Region | source vs d5b | source vs bmng | edge gain | L* delta | Verdict |
|---|---|---|---:|---:|---|
| A1 Boracay | mixed | reference-adjacent | -0.0348 | -29.660 | 变化有限 |
| A2 Maldives | mixed | reference-adjacent | -0.0210 | -32.208 | 变化有限 |
| A4 Bahamas | mixed | reference-adjacent | -0.0251 | -29.046 | 变化有限 |
| A3 GreatBarrierReef | mixed | reference-adjacent | 0.0054 | -27.141 | 略有改善 |
| A7 Palau | mixed | reference-adjacent | -0.0487 | -27.037 | 变化有限 |
| A8 Hawaii | mixed | reference-adjacent | -0.0145 | -19.841 | 变化有限 |
| B1 PersianGulf | mixed | reference-adjacent | -0.0328 | -13.143 | 略有改善 |
| C1 YellowSea | mixed | reference-adjacent | -0.0283 | -25.895 | 略有改善 |
| D1 PacificDeep | mixed | reference-adjacent | -0.0171 | -19.187 | 变化有限 |
| D2 IndianDeep | mixed | reference-adjacent | -0.0309 | -27.162 | 变化有限 |
| E1 Sahara | mixed | reference-adjacent | -0.0196 | -5.847 | 变化有限 |
| E2 ArabianDesert | mixed | reference-adjacent | -0.0297 | -14.004 | 略有改善 |
| F1 Antarctica | mixed | reference-adjacent | 0.0030 | 4.952 | 更清晰但偏亮 |
| F3 Greenland | mixed | reference-adjacent | 0.0036 | -1.886 | 变化有限 |
| H1 AmazonRainforest | mixed | reference-adjacent | -0.0120 | -11.263 | 变化有限 |
| G1 TibetanPlateau | mixed | reference-adjacent | -0.0651 | -8.030 | 变化有限 |

## Notable Outcomes
- No region crossed the strongest-improvement threshold.
- The source-derived preview is generally darker than `d5b_design_v3_2_1` in the coastal and island windows that matter most for E1.
- Most island / shallow-water regions lose readability rather than gain it.
- Only the polar windows show a limited benefit, and even there the gain is not strong enough to justify a source swap.
- Deep ocean regions remain intentionally conservative; the new source does not create a bathymetry solution by itself.

## Route Impact
| 路线 | 继续 d5b_v3_2_1 | 切换 source-derived | 判断 |
|---|---|---|---|
| E1-R3 Day Master Candidate | Yes | No | keep `d5b_v3_2_1` as the current better working input; source-derived is not an upgrade |
| D5z Nearshore Shallow Water | Yes | No | do not switch the nearshore route to this source |
| E1-R1 metrics baseline | Keep current baseline | No rebase yet | only rebase if a better source appears |
| E1-R4A Regional Visual Preview | Keep current compare set | No | the current source-derived preview is only a negative check, not a new ladder |
| Phase 4 Texture Fidelity | Keep current reference | No | fidelity target should stay on the current 8K route |
| Phase 7 Runtime | Keep current runtime path | No direct change | runtime atmosphere is still a separate problem |

## Final Judgment
- Source preview generated from 21.6K master: `previews/e1_r2_7/source_21600_to_8k_preview.jpg`
- The 21.6K source is not recommended as the new Day Master input source.
- It regresses the regions that matter most for this phase: islands, shallow-water gradients, and coastline readability.
- Its only visible upside is limited high-latitude / ice-sheet clarity, which is not enough to justify a source swap.
- D5z should stay paused, and the current `d5b_v3_2_1` route should remain the working baseline.

## Generated Files
- Source preview: `previews/e1_r2_7/source_21600_to_8k_preview.jpg`
- Region compares: `previews/e1_r2_7/regions` (16 files)

## Notes
- This is a temporary preview artifact only.
- No production/candidate texture was modified.
- No commit was created.
