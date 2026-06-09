# E1-R6 Production Decision

**Date:** 2026-06-09  
**Reviewer / Authorizing:** RW  
**DAY_TEXTURE_VARIANT after E1-R6:** `d5z_b`

---

## Decision Summary

`d5z_b_8192x4096.jpg` is promoted as the current **8K Stable Day Earth Master** and set as the default Day Texture for RodiO.

This does **not** represent final RodiO Earth color grading. Remaining refinements (ocean transparency, shallow-water layering, terrain atmosphere, overall richness) are deferred to the BMNG / RDL Global Color Grading phase.

---

## Promoted Candidate

| Field | Value |
|---|---|
| Candidate | `d5z_b` |
| Source file | `pwa/assets/earth/candidates/d5z_b_8192x4096.jpg` |
| Production file | `pwa/assets/earth/production/d5z_b_8192x4096.jpg` |
| File size | 7.6 MB |
| Dimensions | 8192×4096 |
| Fallback candidate | `d5z_a` (retained at `candidates/`, unchanged) |

---

## Upstream Verdict — E1-R5 Full On-globe Visual Acceptance

| Result | Value |
|---|---|
| Overall verdict | **Conditional Pass** |
| Partial criteria (2/14) | Antarctica/Greenland ice brightness (still slightly bright); Indian Ocean deep texture (slight GIS feel) |
| Protected regions | Japan / Mediterranean / Caribbean / Pacific Islands — no regression |
| Reviewer | RW |
| Date | 2026-06-09 |

Reference: `docs/e1_r5_full_on_globe_acceptance.md`

---

## D5z_b Correction Summary

| Correction | Target zone | Method |
|---|---|---|
| Polar brightness compress | Antarctica (lat < −65°) · Arctic/Greenland (lat > 65°) | Ice-pixel multiplicative scaling; sf=0.87 south / 0.90 north; 5° smooth transition |
| Deep ocean desaturate | Indian Ocean (lat −30…+15, lon 50…110) · Pacific deep (lat −45…0, lon 160…230°W) | sat×0.93, brightness×0.97, 20px feather |
| Sahara / Arabia brightness | Sahara (lat 15…35, lon −15…+45) · Arabia (lat 10…32, lon 35…65) | brightness×0.97; Mediterranean hard exclusion (no feather) |
| Color Harmony Guard | All protected regions | Post-process blend-back; activated 0 times |

---

## earth3d.js Changes

| Change | Before | After |
|---|---|---|
| `DAY_TEXTURE_VARIANT` (line 6) | `'bmng_d2'` | `'d5z_b'` |
| `d5z_b` path in `getDayTexturePaths()` | `candidates/d5z_b_8192x4096.jpg` | `production/d5z_b_8192x4096.jpg` |
| `d5z_a` path in `getDayTexturePaths()` | `candidates/d5z_a_8192x4096.jpg` | unchanged (fallback candidate) |

---

## Local Default Load Verification

**URL:** `http://localhost:8080/` (no query params — default load)  
**Result:** PASS

| Check | Expected | Actual |
|---|---|---|
| Console variant log | `d5z_b` | `d5z_b` ✓ |
| Texture path | `/assets/earth/production/…` | `/assets/earth/production/d5z_b_8192x4096.jpg` ✓ |
| HTTP status | 200 | 200 ✓ |
| Texture dimensions | 8192×4096 | 8192×4096 ✓ |
| earth3d.isReady | true | true ✓ |
| TUNE IN overlay dismissed | true | true ✓ |

**Screenshots:**

| Time | File | Size |
|---|---|---|
| noon | `e1r6_default_noon.png` | 458 KB |
| afternoon | `e1r6_default_afternoon.png` | 445 KB |

Screenshots in `previews/e1_r6_production_decision/`.

---

## Remaining Issues (deferred — not addressed in D5z)

| Issue | Planned stage |
|---|---|
| 当前色彩仍不是最终 RodiO Day Earth 目标风格 | Global Color Grading / BMNG-RDL phase |
| 海洋通透感、浅海层次、陆地空气感、整体高级感不足 | Global Color Grading / BMNG-RDL phase |
| 极地仍略偏亮（Antarctica / Greenland） | Global Color Grading / BMNG-RDL phase |
| 深海仍略有 GIS 感（Indian Ocean / Pacific deep） | Global Color Grading / BMNG-RDL phase |

D5z parameter tuning is now closed. No further D5z_c generation.

---

## Boundary

- E1-R6 Production Decision **does not** represent final Earth color grading completion
- **Does not** represent BMNG / RDL high-fidelity Earth completion  
- `DAY_TEXTURE_VARIANT` is now `'d5z_b'` — effective immediately on next deploy
- Not pushed to remote unless RW explicitly authorizes

---

## Production Deployment Verification

**Production URL:** `https://web-production-a5193.up.railway.app`  
**Verification Date:** 2026-06-09  
**Result:** PASS

| Check | Expected | Actual |
|---|---|---|
| Page HTTP status | 200 | 200 ✓ |
| Console variant log | `d5z_b` | `d5z_b` ✓ |
| Runtime texture path | `/assets/earth/production/d5z_b_8192x4096.jpg` | `/assets/earth/production/d5z_b_8192x4096.jpg` ✓ |
| Texture HTTP status | 200 | 200 ✓ |
| Texture dimensions | 8192×4096 | 8192×4096 ✓ |
| earth3d.isReady | true | true ✓ |
| TUNE IN overlay | dismissed | dismissed ✓ |
| Console errors | none | none ✓ |
| noon screenshot | normal | `production_default_noon.png` 458 KB ✓ |
| afternoon screenshot | normal | `production_default_afternoon.png` 445 KB ✓ |

Screenshots in `previews/e1_r6_production_deployment_verification/`.

**Final Status:**

E1 Day Earth Master is production verified.  
D5z_b is the current online 8K stable day texture.  
D5z phase is closed.  
Remaining color, ocean, terrain, and atmosphere refinements are deferred to the Global Color Grading / BMNG-RDL phase.

---

## Next Phase Recommendation

**Global Color Grading / BMNG-RDL Phase**

Goals: ocean transparency, shallow-water layering, terrain atmosphere, overall visual richness toward the final RodiO Day Earth target.  
Entry gate: separate RW authorization. No automatic entry from E1-R6.
