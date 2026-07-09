# Phase B-6.2S — Structure Mask Supplement Plan

**Date:** 2026-06-10
**Status:** PLANNING ONLY — no code changes, no mask generation
**Predecessor:** B-6.2P (polar patch) → B-6.3R (re-validation passed)
**Purpose:** Define which structural masks to add before d6 integration

---

## 1. Current State

### What Passed (B-6.2P + B-6.3R)

| Check | Result |
|---|---|
| Antarctica interior (0°, −80°) | land=1.0, ocean=0.0 ✓ |
| Greenland (−42°, 72°) | land=1.0 ✓ |
| Southern Ocean (0°, −55°) | ocean=1.0 ✓ |
| depth_on_land_pixels | 0 ✓ |
| antarctica_depth_mask_pixels | 0 ✓ |
| depth_mask_overlap_pixels | 0 ✓ |
| land+ocean mean | 1.000000 ✓ |
| ETOPO1/land disagreement | 1.60% (from 11.83%) ✓ |

### What's Still Missing

B-6.2P provides a correct global partition (land / ocean / depth bands) but lacks **structural selectivity** for the regions where Noon Air needs precision color corrections:

1. **Special seas**: Red Sea, Japan Sea, Yellow/East China Sea, Caribbean, Mediterranean — only identifiable by bbox, not by depth or GSHHG coastline shape
2. **Shallow banks**: Bahamas, Persian Gulf, North Sea shelf — ETOPO1 can approximate, but resolution and offset errors are known
3. **Island / reef / atoll proximity**: Maldives, Tuamotu, GBR, Coral Sea — not present in any available data at the needed resolution; GSHHG h-tier at 2K loses sub-pixel islands
4. **Consequence**: d6 cannot use these masks as structural selectors yet — risk of misapplication is higher than benefit

### Why B-5.3 Alone Is Insufficient

B-5.3's `apply_island_reef_floor` uses circular masks anchored to island centers (hard-coded). This is fine for known islands but:
- Cannot adapt to new region additions without manual edits
- Has no depth-gating (island halo bleeds into deep ocean)
- B-6.2S structure masks would provide a proper depth gate for B-5.3 halos

---

## 2. B-6.2S Target Masks

### Group A — Special Sea Water-Only Masks (P1)

Named geographic water-only selectors. Pure `ocean_mask × bbox_mask`. Low risk, high utility.

**Method:**
```python
special_sea_mask = ocean_mask * bbox_mask
# optional depth gate: × (z < -depth_threshold) or × (z >= -depth_threshold)
# all results must be float32 [0,1]
# land is already excluded via ocean_mask
```

All Group A masks must:
- Be named `*_water_mask` to signal water-only
- Record bbox in metadata
- Never be used on land pixels
- Not guarantee precise geographic containment (bbox edges will bleed into adjacent seas)

### Group B — Shallow Bank / Shelf Special Masks (P1/P2)

ETOPO1-derived depth-gated selectors within geographic bboxes.

**Method:**
```python
shelf_mask = ocean_mask * bbox_mask * (z >= -depth_shelf) * (z < 0)
```

Reliability depends on ETOPO1 resolution vs actual shelf geometry.

### Group C — Island / Reef / Atoll Proxy Masks (P2 / Experimental)

GSHHG-derived small island proximity OR ETOPO1 shallow anomaly.
Must be labelled `_proxy_mask` — not real reef data.

---

## 3. Feasibility Matrix

| Mask | Priority | Data Source | Method | Reliable Now? | Needs New Data? | Risk | Implement B-6.2S? |
|---|---|---|---|---|---|---|---|
| `red_sea_water_mask` | P1 | ocean_mask + bbox | bbox intersection | **Yes** | No | Low — bbox bleeds slightly into Gulf of Aden at south | **B-6.2S-1** |
| `yellow_sea_water_mask` | P1 | ocean_mask + bbox | bbox intersection | **Yes** | No | Low | **B-6.2S-1** |
| `east_china_sea_water_mask` | P1 | ocean_mask + bbox | bbox intersection | **Yes** | No | Low | **B-6.2S-1** |
| `japan_sea_water_mask` | P1 | ocean_mask + bbox | bbox intersection | **Yes** | No | Low — bbox clips Korea Strait | **B-6.2S-1** |
| `mediterranean_water_mask` | P1 | ocean_mask + bbox | bbox intersection | **Yes** | No | Low | **B-6.2S-1** |
| `aegean_sea_water_mask` | P1 | ocean_mask + bbox | bbox + depth | **Yes** | No | Low | **B-6.2S-1** |
| `caribbean_water_mask` | P1 | ocean_mask + bbox | bbox intersection | **Yes** | No | Medium — large bbox overlaps Atlantic | **B-6.2S-1** |
| `persian_gulf_water_mask` | P1 | ocean_mask + bbox | bbox intersection | **Yes** | No | Low | **B-6.2S-1** |
| `north_sea_water_mask` | P1 | ocean_mask + bbox | bbox + depth gate z ≥ -200 | **Yes** | No | Low | **B-6.2S-1** |
| `baltic_sea_water_mask` | P1 | ocean_mask + bbox | bbox intersection | **Yes** | No | Low | **B-6.2S-1** |
| `south_china_sea_water_mask` | P1 | ocean_mask + bbox | bbox intersection | **Yes** | No | Medium — large, overlaps Pacific | **B-6.2S-1** |
| `bahamas_bank_mask` | P1 | ocean_mask + bbox + ETOPO1 | z ≥ -50 AND ocean AND bbox | **Approximate** | No (ETOPO1 sufficient at 2K) | Medium — ETOPO1 at 1 arcmin may miss thin bank geometry | **B-6.2S-2** |
| `caribbean_shelf_mask` | P1 | ocean_mask + ETOPO1 | z ≥ -200 AND ocean AND bbox | **Approximate** | No | Low-medium | **B-6.2S-2** |
| `yellow_east_china_shelf_mask` | P1 | ocean_mask + ETOPO1 | z ≥ -200 AND ocean AND bbox | **Good** — Yellow Sea is very shallow overall | No | Low | **B-6.2S-2** |
| `persian_gulf_shallow_mask` | P1 | ocean_mask + ETOPO1 | z ≥ -100 AND ocean AND bbox | **Good** — Persian Gulf avg depth ~50m | No | Low | **B-6.2S-2** |
| `north_sea_shelf_mask` | P1 | ocean_mask + ETOPO1 | z ≥ -150 AND ocean AND bbox | **Good** — North Sea well-captured by ETOPO1 | No | Low | **B-6.2S-2** |
| `island_proximity_mask` | P2 | GSHHG f + EDT | small polygon area → EDT | **Partial** — GSHHG h loses islands at 2K; f tier needed | No new data, but uses f tier | Medium — at 2K, ~10 px radius ≈ 200 km; too coarse for Maldives | **B-6.2S-3 (experimental)** |
| `small_island_mask` | P2 | GSHHG f | polygon area filter < threshold | **Partial** — f tier only; h tier loses small islands | No | Medium | **B-6.2S-3 (experimental)** |
| `tropical_island_group_mask` | P2 | lat band + island proximity | (lat -25 to +25) AND island_proximity | **Proxy** | No | High — lat band alone too broad | **Defer** |
| `reef_or_atoll_proxy_mask` | P2 | shallow_sea + coastline_dist | shallow AND near coast | **Proxy only** | No | High — ETOPO1 resolution misses most reefs | **B-6.2S-3 (experimental)** |
| `maldives_proxy_mask` | P2 | GSHHG f + EDT | small island EDT, Maldives bbox | **Proxy** | No | Medium — GSHHG f has Maldivian atolls | **B-6.2S-3** |
| `tuamotu_proxy_mask` | P2 | GSHHG f + EDT | small island EDT, Tuamotu bbox | **Proxy** | No | Medium — GSHHG f has Tuamotu | **B-6.2S-3** |
| `great_barrier_reef_proxy_mask` | P2 | ETOPO1 shallow anomaly | z ≥ -50 AND ocean AND GBR bbox | **Poor** — GBR structure is at sub-ETOPO1 resolution | GEBCO or reef dataset | High | **Defer until GEBCO global** |
| `coral_sea_proxy_mask` | P3 | ocean_mask + bbox | bbox only | OK as water-only | No | Low if framed as water-only selector | **Defer or B-6.2S-1 scope extension** |

---

## 4. Special Sea Mask Method Design

### 4.1 General Pattern

```python
def make_special_sea_mask(ocean_mask, lat_1d, lon_1d,
                          lat_s, lat_n, lon_w, lon_e,
                          depth_gate_min=None, depth_gate_max=None, z=None):
    LAT = lat_1d[:, np.newaxis]
    LON = lon_1d[np.newaxis, :]
    bbox = (LAT >= lat_s) & (LAT <= lat_n) & (LON >= lon_w) & (LON <= lon_e)
    mask = (ocean_mask > 0.5) & bbox
    if depth_gate_min is not None and z is not None:
        mask = mask & (z >= depth_gate_min)
    if depth_gate_max is not None and z is not None:
        mask = mask & (z < depth_gate_max)
    return mask.astype(np.float32)
```

All outputs are **water-only** by construction (ANDed with `ocean_mask`).

### 4.2 Bounding Boxes (Initial Proposal)

| Sea | lat_s | lat_n | lon_w | lon_e | Optional depth gate | Notes |
|---|---|---|---|---|---|---|
| Red Sea | 12.5 | 30.0 | 32.0 | 44.0 | z ≥ −2200 | Excludes Gulf of Aden; south edge cuts near Bab-el-Mandeb |
| Yellow Sea | 30.0 | 41.0 | 119.0 | 127.0 | z ≥ −100 (avg depth ~44m) | Excludes East China Sea |
| East China Sea | 23.0 | 34.0 | 120.0 | 131.0 | — | Overlaps Yellow Sea to north; use together |
| Japan Sea | 33.0 | 52.0 | 127.0 | 142.0 | — | Korea Strait at south is narrow; minor bleed |
| Mediterranean | 30.0 | 46.5 | −6.0 | 37.0 | — | Includes Aegean, Adriatic; sub-masks optional |
| Aegean Sea | 36.0 | 42.0 | 23.0 | 29.0 | — | Sub-region of Mediterranean |
| Caribbean | 8.0 | 25.0 | −87.0 | −58.0 | — | Large bbox; south bleeds into Venezuela coast |
| Persian Gulf | 22.5 | 30.5 | 47.5 | 57.0 | z ≥ −100 (avg depth ~50m) | Very enclosed |
| North Sea | 51.0 | 62.0 | −4.0 | 10.0 | z ≥ −200 | Includes Skagerrak; south bleeds into Channel |
| Baltic Sea | 53.5 | 66.0 | 9.5 | 31.0 | z ≥ −500 | Includes all sub-basins |
| South China Sea | 0.0 | 25.0 | 99.0 | 122.0 | — | Large; west includes Gulf of Thailand |

**Notes on bbox accuracy:**
- Bboxes are starting points; d6 must add feathering at edges (sigma ≥ 5px at 2K) to avoid hard color transitions
- Do NOT use bboxes as hard masks in color grading without feathering
- Named `*_water_mask`, not `*_color_correction_zone` — structural selector only

---

## 5. Island / Reef Proxy Method Design

### 5.1 Candidate Methods

| Method | Description | Applicability |
|---|---|---|
| GSHHG small island EDT | Filter GSHHG f/L1 polygons by area < threshold (e.g., < 500 km²); rasterize; compute EDT; output proximity field | Best for Maldives, Tuamotu — both have many small atoll polygons in GSHHG f |
| Tropical latitude band | Mask by lat −25 to +25 only | Too coarse; alone insufficient |
| shallow_sea + coastline_dist gating | ocean pixels where z ≥ −200 AND coastline_dist < threshold | Reasonable proxy for near-coast shallow water; misses open-ocean atolls |
| ETOPO1 shallow anomaly | z ≥ −50 inside otherwise deep ocean bbox | Can approximate Maldives (shallow atoll platform at z ~−30 to 0); fails for GBR internal structure |
| Manual anchor + EDT | Hard-code anchor points (island centers) and compute radial EDT; same as B-5.3 approach | Accurate for known islands; not data-driven |

### 5.2 Region-by-Region Recommendation

**Maldives:**
- GSHHG f/L1 has Maldivian atoll islands (small polygons in Indian Ocean)
- Method: GSHHG f small island EDT within Maldives bbox (lat 1–8°N, lon 72–74°E)
- Reliability: **Medium** — GSHHG f captures major atolls; some micro-atolls missing
- Verdict: **Suitable for B-6.2S-3 (proxy, labelled)**

**Tuamotu (French Polynesia):**
- GSHHG f/L1 has Tuamotu atoll islands
- Method: GSHHG f small island EDT within Tuamotu bbox (lat −23 to −15°, lon −150 to −135°)
- Reliability: **Medium** — similar to Maldives
- Verdict: **Suitable for B-6.2S-3 (proxy, labelled)**

**Bahamas:**
- Bahamas bank is NOT primarily an island-proximity problem; it's a **shallow shelf** problem
- The Great Bahama Bank is a carbonate platform at z ~0 to −50m
- Method: ETOPO1 z ≥ −50 AND ocean AND Bahamas bbox (lat 21–28°N, lon −80 to −72°)
- ETOPO1 reliability: **Good enough at 2K** — Bahamas Bank is large (200×200 km)
- Verdict: **NOT island proximity; use shallow bank method — B-6.2S-2**

**Great Barrier Reef:**
- GBR internal reef structure is at 10–100m scale; ETOPO1 1 arcmin ≈ 1.85 km cannot resolve it
- ETOPO1 can identify the Coral Sea shelf zone (z ≥ −200 AND GBR bbox) but not reef geometry
- Method: shallow-sea proxy (z ≥ −200 AND GBR bbox) at best; actual reef structure needs GEBCO global (~464m) or Australian Reef Data
- Reliability: **Poor for reef; OK for shelf selector**
- Verdict: **Defer reef-specific mask; shelf proxy acceptable as water-only-shelf**

**Red Sea Reefs:**
- Red Sea has fringing reefs along both coasts, but their geometry is well below ETOPO1 resolution
- Coastline_dist proxy (ocean AND Red Sea bbox AND near coast) would give a rough fringing reef indicator
- Reliability: **Proxy only** — cannot distinguish reef from sandy coast
- Verdict: **Defer reef-specific; Red Sea water-only mask (B-6.2S-1) is sufficient for now**

---

## 6. B-6.2S Implementation Sequence

### B-6.2S-1 — Special Sea Water-Only Masks

**Scope:** 11 named water-only masks from Section 4.2
**Risk:** Low — pure bbox + ocean_mask; no depth-sensitive operations
**Implementation cost:** Low — single function, ~50 lines
**Deliverable:** `structure_masks_2048x1024.npz` updated with Group A masks
**Metadata requirement:** Each mask records its bbox, known bleed-over risk, water-only status
**Recommendation:** **Implement immediately**

### B-6.2S-2 — Shelf / Bank Masks

**Scope:** `bahamas_bank_mask`, `yellow_east_china_shelf_mask`, `persian_gulf_shallow_mask`, `north_sea_shelf_mask`, `caribbean_shelf_mask`
**Risk:** Medium — ETOPO1 depth thresholds have ±50m uncertainty at 2K; shelf edges may have ±1–2 pixel error
**Implementation cost:** Low — ETOPO1 z threshold + bbox + ocean_mask
**Deliverable:** Additional masks added to NPZ
**Metadata requirement:** Each mask notes ETOPO1 depth threshold and resolution limitation
**Recommendation:** **Implement in B-6.2S (after B-6.2S-1 validated)**
**Constraint:** Must be labelled `*_shelf_mask` or `*_bank_mask`, not `*_reef_mask`

### B-6.2S-3 — Island / Reef Proxy Masks

**Scope:** `island_proximity_mask`, `small_island_mask`, `maldives_proxy_mask`, `tuamotu_proxy_mask`, `reef_or_atoll_proxy_mask`
**Risk:** High — requires GSHHG f tier (vs h used currently); at 2K resolution, island EDT is coarse; misleading accuracy claims risk
**Implementation cost:** Medium — requires switching to f tier for island detection (slower, ~30s more)
**Deliverable:** Experimental additional masks; must be clearly labelled `_proxy_`
**Metadata requirement:** Explicit caveat: "proxy based on GSHHG f polygon area filter at 2K; not reef data; accuracy ±20km"
**Recommendation:** **Experimental — implement B-6.2S-3 after B-6.2S-1 + B-6.2S-2 validated**
**Constraint:** `great_barrier_reef_proxy_mask` deferred; `coral_sea_proxy_mask` OK as water-only

### Deferred (Not B-6.2S)

| Mask | Reason | Unblock path |
|---|---|---|
| `great_barrier_reef_proxy_mask` | ETOPO1 resolution insufficient; GBR internal structure ~10–100m | Global GEBCO (15 arcsec) + ALA Reef dataset |
| `red_sea_reef_mask` | Sub-ETOPO1 resolution; coastline-dist proxy too coarse | GEBCO global |
| Reef-accurate masks globally | No dataset at current resolution | GEBCO 2023+ global (7.8 GB, not downloaded) |

---

## 7. B-6.4 API Design Timing

### Can we draft B-6.4 API now?

**Answer: Draft yes, freeze no.**

Rationale:
- B-6.2S-1 (special sea masks) will add 11 named masks with known semantics → these will be stable API entries
- B-6.2S-2 (shelf masks) will add 5 more → also stable
- B-6.2S-3 proxy masks may be renamed or consolidated → freeze AFTER B-6.2S-3

### API Design Principles (Draft, Not Final)

```python
# Proposed mask accessor API for d6 integration
def load_structure_masks(npz_path, required=None, optional=None):
    """
    Load structure masks from NPZ.
    required: list of mask names that must exist (raises on missing)
    optional: list of mask names to load if present (returns None if missing)
    Returns: dict[str, np.ndarray | None]
    """
```

- All masks are float32 [0,1]; d6 callers should not hard-threshold them (use as blend weights)
- Special sea masks: use with gaussian feather σ≥5px before color grading
- Proxy masks: must be gated by `_proxy_` naming convention in d6

### d6 Integration Gate

**d6 must NOT load masks until:**
1. B-6.2S-1 validated ✓ (B-6.4 API drafted)
2. B-6.2S-2 validated ✓
3. B-6.4 API frozen (after B-6.2S-3)
4. B-5.3 implemented (island floor fix) ✓
5. Combined 2K calibration run reviewed

**Can proceed to B-6.4 draft?** Yes, in parallel with B-6.2S-1 implementation.
**Can integrate d6?** No — not until all above gates cleared.

---

## 8. Can B-5.3 Resume?

**Answer: Yes — B-5.3 can resume independently of B-6.2S.**

Rationale:
- B-5.3 (`apply_island_reef_floor`, circular proximity masks) does not depend on structure masks
- B-5.3 was deferred because of B-5.2 visual failure (tropical near-black), not because of B-6 blockers
- B-6.2S-1 structure masks would later provide a depth gate to improve B-5.3 halos, but that is a B-6.3 integration task
- B-5.3 can proceed with its own anchor-based implementation; the B-6 structure gate is an enhancement, not a prerequisite

**Recommended parallel track:**
```
B-5.3 implementation ──────────────────────────────────→ calibration → 8K
         ↕ (independent)
B-6.2S-1 ──→ B-6.2S-2 ──→ B-6.2S-3 ──→ B-6.4 API ──→ d6 integration
```

---

## 9. Final Recommendation

```
Final Recommendation:
─────────────────────────────────────────────────────────────────────

Implement B-6.2S now? SPLIT — B-6.2S-1 immediately, B-6.2S-2 after, B-6.2S-3 experimental

First implementation target:
  B-6.2S-1 — 11 special sea water-only masks (bbox + ocean_mask)
  Estimated cost: low (~50 lines, <5 min generation)
  Risk: low

Must defer:
  great_barrier_reef_proxy_mask  — needs GEBCO global (7.8 GB, not downloaded)
  red_sea_reef_mask              — needs GEBCO global
  Any mask claiming reef accuracy — not achievable with ETOPO1 at 2K

Can proceed to B-6.4 API draft? YES (in parallel with B-6.2S-1)
  Freeze API only after B-6.2S-3 is settled

Can integrate d6? NO
  Gates: B-6.2S-1 + B-6.2S-2 validated, B-6.4 API frozen, B-5.3 implemented

Can resume B-5.3? YES — independent track, can start immediately
  B-5.3 does not require B-6 structure masks
  B-6 structure gate for B-5.3 halos is an enhancement, added in B-6.3 integration

Next smallest safe action (choose one):
  Option A (colour-fix first): Implement B-5.3 apply_island_reef_floor
            → run 2K calibration → visual review → if pass, proceed 8K
  Option B (structure first):  Implement B-6.2S-1 special sea water-only masks
            → validate → proceed B-6.2S-2 → B-6.4 API draft
  Option C (parallel):         Assign B-5.3 and B-6.2S-1 to same session
            → B-5.3 calibration first, B-6.2S-1 generation second (non-blocking)
  RECOMMENDED: Option A — visual correctness (B-5.3) is the highest-value
            unblocked action; B-6 structure integration requires visual baseline
            to be acceptable first. Fix the texture, then add the structure layer.
```

---

## Appendix A: ETOPO1 Depth Statistics for Special Sea Regions

| Sea | ETOPO1 representative depth | Depth gate recommendation |
|---|---|---|
| Red Sea | avg −490m, max −2211m | None (use full depth range) |
| Yellow Sea | avg −44m, max −100m | z ≥ −100 to gate shelf only |
| East China Sea | avg −350m | None |
| Japan Sea | avg −1750m | None (deep) |
| Mediterranean | avg −1500m | None |
| Persian Gulf | avg −50m, max −90m | z ≥ −100 for shallow gate |
| North Sea | avg −94m, max −200m | z ≥ −200 for shelf |
| Baltic Sea | avg −55m | z ≥ −500 (nearly all water in range) |
| Caribbean | avg −2200m | None (deep basin) |
| South China Sea | avg −1140m | None |

---

## Appendix B: B-6.2S vs B-5.3 Dependency Map

```
B-5.3  apply_island_reef_floor
  ← Does NOT require B-6 structure masks
  ← Needs: human authorization, code implementation, calibration run
  → Output: tropical island/reef luminance floor (circular masks)
  → Independent of B-6.2S

B-6.2S-1  special sea water-only masks
  ← Requires: current B-6.2P masks (READY)
  ← Needs: human authorization, ~50 lines code addition
  → Output: 11 named water-only masks in NPZ

B-6.2S-2  shelf / bank masks
  ← Requires: B-6.2S-1 validated
  → Output: 5 depth-gated shelf/bank masks

B-6.2S-3  island / reef proxy masks
  ← Requires: B-6.2S-2 validated
  ← Requires: GSHHG f tier (already available)
  → Output: experimental proxy masks (not reef data)

B-6.3 integration
  ← Requires: B-6.2S-1+2+3 validated
  ← Requires: B-5.3 calibration passed
  ← Requires: B-6.4 API frozen
  → Output: d6 reads structure masks for structural color grading

B-5.3 → [calibration] → [8K] → B-6.3 integration
B-6.2S-1 → B-6.2S-2 → B-6.2S-3 → B-6.4 API → B-6.3 integration
```
