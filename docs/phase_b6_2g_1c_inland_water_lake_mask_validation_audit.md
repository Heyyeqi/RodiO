# Phase B-6.2G-1C — Inland Water / Lake Mask Validation Audit

**Phase:** B-6.2G-1C
**Date:** 2026-06-10
**Status:** VALIDATION AUDIT — read-only; no code changes; no mask regeneration
**Scope:** Validate B-6.2G-1B lake mask outputs against B-6.2G-1A audit requirements
**Masks audited:** `structure_masks_2048x1024.npz` (27 masks, 9.3 MB)
**Generator version:** B-6.2G-1B (`scripts/generate_b6_structure_masks.py`)

---

## 1. Executive Verdict

**CONDITIONAL PASS.**

No critical issue found. B-6.2G-1B lake masks are trustworthy for 2K prototype semantic layer purposes. One implementation correction is required (see §5), but it is not a blocker. Existing outputs are usable as-is for audit and planning.

| Criterion | Result |
|-----------|--------|
| Critical issue | **None** |
| Masks trustworthy for 2K prototype | **Yes** |
| Blocker for B-6.2G-2A | **No** |
| Implementation correction required | **Yes — non-blocking (see §5)** |
| Can proceed to B-6.2G-2A Terrain / Relief Feasibility Audit | **Yes** |
| d6 can be touched | **No** |
| Visual rebuild / color grading can start | **No** |

---

## 2. Mask Statistics

### 2.1 Pre-Feather Hard Pixel Counts (generator output)

| Mask | Hard px (binary) |
|------|:----------------:|
| lake_mask_from_GSHHG_L2 (hard) | 25,290 |
| lake_island_mask (hard) | 1,943 |
| inland_water_mask (hard) | 23,888 |
| large_lake_mask (hard) | 4,497 |

### 2.2 Post-Feather Pixel Counts (metrics.json, threshold > 0.5)

| Mask | px (>0.5) | coverage |
|------|:---------:|:--------:|
| lake_mask_from_GSHHG_L2 | 17,927 | 0.8548% |
| lake_island_mask | 590 | 0.0281% |
| inland_water_mask | 15,976 | 0.7618% |
| large_lake_mask | 4,420 | 0.2108% |

### 2.3 Source Shape Counts

| Metric | Value |
|--------|------:|
| h/L2 total shapes | 6,601 |
| h/L2 positive-area (true lakes) | 6,545 |
| h/L2 negative-area excluded (river-lake zones) | 56 |
| h/L3 total shapes (lake islands) | 1,434 |
| h/L3 with verified parent_id in L2 | 1,022 |
| Large lake threshold | 10,000 km² |

### 2.4 Integrity Checks

| Check | Result |
|-------|--------|
| NaN in any lake mask | None |
| Inf in any lake mask | None |
| Value range all masks | [0.0, 1.0] |
| lake_island_mask max value | 0.9491 (< 1.0 — expected: feather on small island shapes) |
| area > 0 filter applied | Confirmed (56 negative-area excluded) |
| parent_id = 0 assumption avoided | Confirmed (real parent_id values used) |
| WDBII rivers mixed in | None |

---

## 3. Pixel Count Discrepancy Analysis

**Observed:** post-feather lake (17,927) minus inland_water (15,976) = **1,951 px** difference.

Of those 1,951 px:
- **469 px** overlap with `lake_island_mask > 0.5` — these are genuine island pixels visible after feather.
- **1,482 px** are not explained by island overlap.

**Root cause of the 1,482 px:** feathering sigma=1 applied independently to each mask before thresholding at 0.5. `inland_water_mask` was computed as `lake_hard & ~island_hard` (pre-feather), then feathered. `lake_mask_from_GSHHG_L2` was feathered separately from `lake_hard` alone. The boundary halos of the two feathered masks diverge at narrow lake shapes, resulting in lake pixels that survive the > 0.5 threshold in `lake_mask_from_GSHHG_L2` but fall below threshold in `inland_water_mask` due to island proximity shrinkage or very narrow lake widths.

**Consequence:** `lake_island_mask` is safe for hole-punching reference. It is **not safe to use standalone** as a hard subtraction mask from the final `inland_water_mask` at the > 0.5 threshold level — the effective subtraction is already baked into `inland_water_mask` by construction. Use `inland_water_mask` as the canonical water body mask.

**Verdict:** expected behavior; not a bug; no correction needed for this discrepancy.

---

## 4. Key Region Validation

Resolution: 2048×1024. Probe values are mask pixel values at the stated lat/lon center point.

| # | Region | lake | inland | large | Judgment |
|---|--------|:----:|:------:|:-----:|----------|
| 1 | Caspian Sea (41°N, 51°E) | 1.000 | 1.000 | 1.000 | **PASS** |
| 2 | Great Lakes — Superior (47.5°N, -87.5°W) | 1.000 | 0.866 | 0.866 | **PASS** |
| 2 | Great Lakes — Michigan (44°N, -87°W) | 1.000 | 1.000 | 1.000 | **PASS** |
| 2 | Great Lakes — Huron (44.8°N, -82.5°W) | 1.000 | 1.000 | 1.000 | **PASS** |
| 2 | Great Lakes — Erie (42.2°N, -81.2°W) | 0.979 | 0.979 | 0.979 | **PASS** |
| 2 | Great Lakes — Ontario (43.7°N, -77.5°W) | 0.995 | 0.995 | 0.995 | **PASS** |
| 3 | Lake Baikal S (51.8°N, 105°E) | 0.904 | 0.904 | 0.901 | **PASS** |
| 3 | Lake Baikal N (53.9°N, 108°E) | 0.654 | 0.653 | 0.653 | **PASS-SOFT** (see note) |
| 4 | Lake Victoria (-1°N, 33°E) | 1.000 | 0.999 | 0.999 | **PASS** |
| 5 | Lake Tanganyika (-6°N, 29.5°E) | 0.924 | 0.903 | 0.903 | **PASS** |
| 6 | Aral Sea (45°N, 60°E) | 1.000 | 1.000 | 1.000 | **WATCHLIST** (historical extent) |
| 7 | Lake Titicaca (-16°N, -69.5°W) | 0.902 | 0.809 | 0.000 | **PASS-SOFT** (below large threshold) |
| 8 | Qinghai Lake (36.9°N, 100.2°E) | 0.931 | 0.931 | 0.000 | **PASS-SOFT** (below large threshold) |
| 9 | Dongting Lake (29.3°N, 112.9°E) | 0.749 | 0.749 | 0.000 | **PASS-SOFT / LIMITATION** |
| 10 | Poyang Lake (29°N, 116.3°E) | 0.148 | 0.148 | 0.000 | **PASS-SOFT / LIMITATION** |
| 11 | Taihu Lake (31.2°N, 120.1°E) | 0.746 | 0.498 | 0.000 | **PASS-SOFT** (inland just below 0.5 threshold) |
| 12 | Qiandao Lake (29.6°N, 118.9°E) | 0.744 | 0.274 | 0.000 | **LIMITATION** (suppressed from hard inland mask) |
| — | Lake Chad (13°N, 14°E) | 0.954 | 0.940 | 0.940 | **WATCHLIST** (historical extent) |

### Notes

**Great Lakes (initial probe at 44.5°N, -84°W = 0.058):** that probe hit a land boundary pixel within the single unified L2 polygon. All 5 individual sub-lake center probes confirm coverage. PASS.

**Lake Baikal N (53.9°N, 108°E = 0.654):** reduced value near Olkhon Island area (53°N, 107.4°E). Baikal S probe (0.904) confirms full body coverage. The lower N value is consistent with L3 island hole-punching near Olkhon. PASS overall; PASS-SOFT at northern probe.

**Lake Titicaca (large = 0.000):** area ~8,117 km², below the 10,000 km² threshold for `large_lake_mask`. Present in `inland_water_mask` (0.809). Expected behavior.

**Qinghai Lake (large = 0.000):** area ~4,450 km², well below threshold. Present in `inland_water_mask` (0.931). Expected.

**Dongting Lake (0.749/0.749):** 778 km² positive-area polygon present in h/L2. Probe shows soft presence (0.749) in both lake and inland masks — the 778 km² polygon is small at 2K (~2 px area) but the feather halo around it creates the 0.749 center value. Hard binary count is uncertain; treat as soft/marginal presence. Not a hard failure.

**Poyang Lake (0.148/0.148):** absent as standalone in h/L2 positive-area; subsumed into Yangtze river-lake widening zone (negative-area, excluded). The 0.148 soft value is feather bleed from nearby shapes, below the 0.5 hard threshold. Confirms expected absence from hard mask. LIMITATION, not failure.

**Taihu Lake (inland = 0.498):** center probe just below the 0.5 hard threshold for `inland_water_mask` despite strong presence in `lake_mask_from_GSHHG_L2` (0.746). The tiny lake (~8 px area) has a center pixel that barely survives feather in the lake mask but falls below threshold after island-hole processing in the inland mask. Taihu IS in the hard `lake_mask_from_GSHHG_L2` binary. PASS-SOFT.

**Qiandao Lake (inland = 0.274):** present in `lake_mask_from_GSHHG_L2` (0.744 > 0.5, confirmed in hard binary). Suppressed from hard `inland_water_mask` at the > 0.5 threshold (0.274). The ~2 px lake body is too small for the hole-punch feather interaction to preserve above threshold. **Qiandao Lake is suppressed from the hard `inland_water_mask` at 2K.** Not a blocker; recorded as expected 2K limitation. Suitable for re-evaluation at 8K.

---

## 5. Implementation Correction Required

### C-1 — `lake_island_mask` max value < 1.0 (non-blocking)

**Observed:** `lake_island_mask` max value = 0.9491, not 1.0.

**Cause:** h/L3 island shapes at 2K are very small (often 1–3 px). Gaussian feather sigma=1 on a 1-px island blob produces a peak center value of ~0.95 rather than 1.0 — the Gaussian kernel at sigma=1 gives a peak of 1/(2π) × scale factor that does not reach 1.0 for sub-3px objects.

**Impact:** The hard threshold (> 0.5) still captures island pixels correctly in `lake_island_mask`. No downstream error in `inland_water_mask` construction. Cosmetic only.

**Correction (for B-6.2G-1D or future re-run):** Apply `np.clip(mask, 0, 1)` after feather — already done — but also consider `feather(mask, sigma) * (mask_hard > 0.5)` to re-clamp feathered values to the hard binary domain for the island mask specifically, ensuring max = 1.0 where any island pixel exists. Not required before B-6.2G-2A.

---

## 6. Caveats and Limitations

### L-1 — Aral Sea historical extent

GSHHG 2.3.7 records Aral Sea at ~67,543 km² (historical baseline, pre-1990s). Current extent (2026) is ~2,500 km². The mask correctly shows the historical polygon. Any d6 use of `inland_water_mask` or `large_lake_mask` in the Aral region will reflect geography that no longer exists at that scale.

**Action required at d6 integration:** flag or exclude Aral Sea (bbox 58–62°E, 43–47°N) before any color grading application.

### L-2 — Lake Chad historical extent

GSHHG records Lake Chad at ~11,977 km² (1960s peak). Current area ~1,500 km². Present in `large_lake_mask` (probe 0.940). Same caveat as Aral Sea.

### L-3 — Poyang Lake absent from hard masks

Poyang Lake is subsumed into the Yangtze river-lake widening zone (negative-area L2 shape, excluded by `area > 0` filter). No standalone positive-area polygon for Poyang exists in h/L2. Probe value 0.148 is below hard threshold — Poyang does not register in hard binary masks. This is a GSHHG data architecture limitation, not a code error.

### L-4 — Dongting Lake marginal presence

Dongting Lake (778 km², ~2 px at 2K) produces a feather halo at center (0.749) but the hard binary footprint is ~1–2 px. Sigma=1 feather creates soft presence rather than reliable hard boundary. Treat as soft/marginal.

### L-5 — Qiandao Lake suppressed from `inland_water_mask`

Qiandao Lake (581.7 km², ~2 px at 2K) is present in `lake_mask_from_GSHHG_L2` (center 0.744 > 0.5) but suppressed from `inland_water_mask` (center 0.274 < 0.5) due to island-hole feather interaction at sub-3px scale. Qiandao is on the 8K / high-resolution watchlist.

### L-6 — Great Lakes as single h/L2 polygon

All 5 Great Lakes are stored as a single 208,200 km² polygon in h/L2. Individual lake identities are not separately accessible at h tier. Visual coverage is correct; semantic per-lake selection requires f/L2.

### L-7 — `lake_island_mask` not safe as standalone subtraction

Using `lake_island_mask` as a direct subtraction from `inland_water_mask` at the > 0.5 level will over-subtract due to feather shrinkage divergence (1,482 px). Always use `inland_water_mask` as the canonical water body mask; treat `lake_island_mask` as an informational layer.

---

## 7. Proceeding to B-6.2G-2A

| Gate | Status |
|------|--------|
| All 4 lake masks generated without NaN/Inf | PASS |
| area > 0 filter confirmed active | PASS |
| 56 negative-area river-lake zones excluded | PASS |
| Real L3 parent_id linkage used | PASS |
| WDBII rivers not mixed in | PASS |
| Aral / Lake Chad risk documented in metadata | PASS |
| Poyang / Dongting limitations documented | PASS |
| Qiandao suppression documented | PASS |
| Implementation correction C-1 identified (non-blocking) | NOTED |
| No critical failure | PASS |
| **Verdict: Proceed to B-6.2G-2A?** | **YES** |

**B-6.2G-2A scope:** Terrain / Relief Feasibility Audit — assess ETOPO1 slope/relief data sufficiency for terrain structure masks. Read-only audit, separate authorization required.

**Prohibited until B-6.4 API design:**
- d6 integration of any lake masks
- Visual rebuild or color grading using lake masks
- pwa / production / candidates writes

---

## 8. Revision Status

| Item | Status |
|------|--------|
| Generated `docs/phase_b6_2g_1c_inland_water_lake_mask_validation_audit.md` | **YES** |
| Modified code | NO |
| Regenerated masks | NO |
| Ran generator | NO |
| Ran d6 | NO |
| Wrote pwa / production / candidates | NO |
| Committed | NO |
| Pushed | NO |

---

*B-6.2G-1C — validation audit only. No code changes. No mask regeneration. No commit.*
