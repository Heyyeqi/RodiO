# E1-R4A Regional Visual Preview — d5b_design_v3_2_1

**Date:** 2026-06-09
**Test target:** d5b_design_v3_2_1_8192x4096.jpg
**Load method:** `?dayTexture=d5b_design_v3_2_1` (localhost only)
**Constraints:** earth3d.js unmodified · DAY_TEXTURE_VARIANT unchanged · no texture writes · no commit

---

## Load Verification

| Check | Result |
|---|---|
| Console variant | `d5b_design_v3_2_1` |
| Texture dimensions | 8192×4096 |
| Network HTTP status | 200 |
| earth3d.isReady | true |
| TUNE IN overlay dismissed | true |

All blocking checks **passed**.

---

## Regional Screenshots

| Region | noon | afternoon | Issues |
|---|---|---|---|
| Sahara / Egypt | `e1r4a_sahara_noon.png` | `e1r4a_sahara_afternoon.png` | — |
| Antarctica | `e1r4a_antarctica_noon.png` | `e1r4a_antarctica_afternoon.png` | — |
| Greenland / Arctic | `e1r4a_greenland_noon.png` | `e1r4a_greenland_afternoon.png` | — |
| Pacific Islands | `e1r4a_pacific_islands_noon.png` | `e1r4a_pacific_islands_afternoon.png` | — |
| Japan / East China Sea | `e1r4a_japan_noon.png` | `e1r4a_japan_afternoon.png` | — |
| Mediterranean | `e1r4a_mediterranean_noon.png` | `e1r4a_mediterranean_afternoon.png` | — |
| Caribbean | `e1r4a_caribbean_noon.png` | `e1r4a_caribbean_afternoon.png` | — |
| Indian Ocean | `e1r4a_indian_ocean_noon.png` | `e1r4a_indian_ocean_afternoon.png` | — |

*Screenshots in `previews/e1_r4a_d5b_design_v3_2_1_rerun/`*

---

## Visual Assessment

### Global observations
- **Overall color tone:** Warmer and more saturated than bmng_d2; ocean depth layering visible; natural land-sea contrast
- **Land / ocean contrast:** Clear distinction globally; coastal halos present and effective
- **Polar regions (Antarctica, Greenland):** Ice/snow highlights too bright under noon lighting; retain texture detail but exceed acceptable brightness ceiling
- **noon vs afternoon difference:** Visible lighting angle shift confirmed; afternoon shows expected warm-toned raking light
- **Style consistency with d5b design line:** Consistent; no style regressions from prior d5b iterations

### Per-region notes

| Region | noon | afternoon |
|---|---|---|
| Sahara / Egypt | Noon highlight risk — broad bright zone, desaturation towards white at peak; not fatal | Acceptable — warm desert tone preserved |
| Antarctica | Ice too bright; high-luminosity region exceeds threshold; texture detail still readable | Acceptable — reduced specular under oblique light |
| Greenland / Arctic | Snow too bright; no polar compress applied to north lat currently | Acceptable — oblique light reduces peak brightness |
| Pacific Islands | Pass — island halos clear, ocean blue well-graduated | Pass |
| Japan / East China Sea | Pass — coastal detail intact, Seto Inland Sea legible | Pass |
| Mediterranean | Pass — blue tones accurate, coastline well defined | Pass |
| Caribbean | Pass — island halos crisp, ocean graduation natural | Pass |
| Indian Ocean | Seafloor texture too strong — deep basin shows visible pattern, "map feel" at central zone | Partial — afternoon slightly better but still map-textured |

---

## Verdict

| Criterion | Pass / Fail / Partial | Notes |
|---|---|---|
| No artifacts (black/white patches, seams) | **Pass** | No blocking artifacts observed |
| Land/ocean clearly distinguishable | **Pass** | Contrast intact globally |
| Polar regions acceptable | **Partial** | Antarctica + Greenland/Arctic too bright; not fatal |
| noon/afternoon theme difference visible | **Pass** | Clear lighting angle shift |
| Style consistent with d5b design line | **Pass** | No style regression |
| Ready to set as DAY_TEXTURE_VARIANT default | **Partial** | Requires D5z corrections first |

**Overall: Conditional Pass**

---

## Boundary Conditions

- 本结论只说明 `d5b_design_v3_2_1` 可以作为 **E1-R3 / D5z candidate generation** 的输入基线
- 本结论**不构成** production acceptance
- 本结论**不允许**修改 `DAY_TEXTURE_VARIANT`
- 本结论**不允许** commit
- 本结论**不等同于** E1-R5 On-globe Visual Acceptance

---

## Next Step

Result: **Conditional Pass → proceed to E1-R3 / D5z Candidate Generation**

Correction targets for D5z (priority order):
1. Antarctica / Greenland / Arctic — reduce ice brightness; preserve detail; must not turn grey/dirty
2. Sahara / Egypt / Arabian Peninsula — reduce noon highlight; preserve warm desert color
3. Indian Ocean / Pacific deep — reduce seafloor texture prominence; preserve depth layering

Protected regions (must not degrade): Japan · Mediterranean · Caribbean · Pacific Islands

`DAY_TEXTURE_VARIANT` remains `'bmng_d2'` until E1-R5 On-globe Visual Acceptance passes.
