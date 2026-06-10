# Phase B-6.2G-3B-R — Major River Proxy L01+L02 Coverage Supplement

**Phase:** B-6.2G-3B-R
**Date:** 2026-06-11
**Status:** COMPLETE — generator run successful; L01+L02 variant masks generated
**Triggered by:** B-6.2G-3C validation finding Nile / Mississippi / Danube = 0 in L01 baseline
**Scope:** Add `major_river_proxy_l01_l02` and `river_buffer_proxy_l01_l02` as coverage supplement variants alongside existing L01 baseline masks

---

## 1. Background and Trigger

B-6.2G-3C validation of the B-6.2G-3B output revealed that three major rivers had **zero coverage** in the `major_river_proxy` (L01 baseline):

| River | L01 shapes | L02 shapes |
|-------|:----------:|:----------:|
| Nile | 0 | ~90 |
| Mississippi | 0 | ~81 |
| Danube | 0 | ~100 |

**Root cause:** WDBII h/L01 contains only 55 shapes covering the most globally dominant waterways. The Nile, Mississippi, and Danube are defined at L02 level (2371 shapes total) in GSHHG 2.3.7.

**Decision:** Keep the L01 baseline intact and add a dedicated L01+L02 variant as a CANDIDATE coverage supplement. Do not replace L01; keep both variants in the NPZ for independent validation.

---

## 2. Implementation

### 2.1 New Masks Added

| Mask | Variant | Description |
|------|---------|-------------|
| `major_river_proxy_l01_l02` | L01+L02 | 1px rasterized polyline, L01+L02 pixel-wise max |
| `river_buffer_proxy_l01_l02` | L01+L02 | 3px dilation corridor of the above |

Both masks share the same domain semantics as L01 baseline:
- Post-feather soft land clip × `land_mask`
- Post-feather hard inland_water exclusion via `inland_water_mask > 0.5`
- NOT merged into `inland_water_mask`
- NOT available in d6 before B-6.4 API design

### 2.2 Rasterization Method

- L01 and L02 rasterized separately using `PIL ImageDraw.line(width=1)`
- Combined as `raw_combined = np.maximum(raw_l01, raw_l02_only)` (pixel-wise max)
- `_rasterize_wdbii_level()` helper shared by both levels
- `_make_pair()` inner function shared by L01 baseline and L01+L02 variant

### 2.3 Domain Clip Policy

Identical to B-6.2G-2B-P terrain masks:
- Land: soft multiply by float `land_mask` after feather
- Inland water: hard binary exclusion using `(inland_water_mask > 0.5)` after feather
- Feathered threshold used to prevent halo overlap (not raw binary)

---

## 3. Generator Output (2048×1024)

### 3.1 Source Counts

| Level | Shapes | Points |
|-------|-------:|-------:|
| WDBII h/L01 | 55 | 22,889 |
| WDBII h/L02 | 2,371 | 56,972 |

### 3.2 Mask Statistics

| Mask | raw px | post-clip px | ocean∩ | iw∩ | variant |
|------|-------:|-------------:|:------:|:---:|---------|
| major_river_proxy | 3,063 | 1,890 | **0** | **0** | L01 baseline |
| river_buffer_proxy | 8,243 | 8,014 | **0** | **0** | L01 baseline |
| major_river_proxy_l01_l02 | 12,256 | 5,458 | **0** | **0** | L01+L02 |
| river_buffer_proxy_l01_l02 | 35,009 | 34,282 | **0** | **0** | L01+L02 |

- **NPZ total:** 35 masks, 13,204 KB
- **Growth (L01 → L01+L02):** major ×2.89, buffer ×4.28
- **Domain integrity:** all 4 masks PASS (∩ ocean = 0, ∩ inland_water = 0)

### 3.3 Density Check (L01+L02 buffer px / land px per region)

| Region | L01 | L01+L02 | Flag |
|--------|----:|--------:|------|
| Europe | 0.1% | 7.7% | ok |
| China | 1.3% | 11.2% | ok |
| India | 1.6% | 9.8% | ok |
| N_America | 0.5% | 6.7% | ok |
| S_America | 2.6% | 9.3% | ok |
| Africa | 1.1% | 5.7% | ok |
| SE_Asia | 2.7% | 11.3% | ok |
| Siberia | 3.5% | 7.8% | ok |

**Threshold:** 30%. **Result: USABLE — no OVERDENSE region.**

---

## 4. Assessment

### 4.1 L01+L02 Assessment: USABLE

All 8 regions below the 30% density threshold. L01+L02 variant does not produce systematic noise patterns at 2K resolution. The 2371 L02 shapes primarily add medium-order river networks (Nile, Mississippi, Danube, and regional tributaries), which at 2K (≈19 km/px) appear as isolated 1-3px corridor segments rather than dense cross-hatching.

### 4.2 Domain Integrity: PASS

All four masks satisfy the strict zero-overlap domain constraints:
- `major_river_proxy_l01_l02 ∩ ocean = 0`
- `major_river_proxy_l01_l02 ∩ inland_water = 0`
- `river_buffer_proxy_l01_l02 ∩ ocean = 0`
- `river_buffer_proxy_l01_l02 ∩ inland_water = 0`

### 4.3 Coverage Gaps Fixed (Pending Verification)

The L01+L02 variant is expected to fill Nile / Mississippi / Danube gaps based on L02 shape counts (90 / 81 / 100 shapes respectively). **Geographic spot-check by bbox is required in B-6.2G-3C-R** — WDBII has no name field; verification is by geographic corridor only.

---

## 5. Known Limitations

| # | Limitation |
|---|-----------|
| L-1 | WDBII has no name field — river identification by bbox/geographic corridor only; cannot query by name |
| L-2 | L01 baseline: Nile / Mississippi / Danube absent; covered by L01+L02 variant |
| L-3 | 1px polyline at 2K ≈ 19 km/px — thin tributaries may have sampling gaps |
| L-4 | Buffer corridor (~3px raw ≈ 60 km) is NOT proportional to real river width |
| L-5 | River mouth / estuary handling deferred to B-6.2G-3C-R or later |
| L-6 | L03–L11 not used; including lower levels would cause global line network over-density |
| L-7 | `inland_water_mask` takes priority: corridor pixels near large lakes are zeroed by domain clip |
| L-8 | L01+L02 is a coverage supplement; L02 level assignment is NOT proof of true hydrological hierarchy |
| L-9 | L01+L02 variant marked CANDIDATE pending B-6.2G-3C-R geographic spot-check |

---

## 6. Pending: B-6.2G-3C-R Validation

B-6.2G-3C-R must confirm:

| Check | Target | Method |
|-------|--------|--------|
| Nile coverage | non-zero pixels in NE Africa corridor (30°E–36°E, 0°–30°N) | bbox probe |
| Mississippi coverage | non-zero pixels in central N America (87°W–93°W, 29°N–47°N) | bbox probe |
| Danube coverage | non-zero pixels in C Europe (13°E–30°E, 44°N–49°N) | bbox probe |
| Amazon baseline | L01 coverage confirmed in S America | bbox probe |
| Yangtze / Yellow River | L01+L02 coverage in China | bbox probe |
| No false ocean rivers | zero or near-zero in ocean-interior probe points | sanity check |

---

## 7. Safety Confirmations

| Item | Status |
|------|--------|
| `d6_noon_air_earth_generator.py` modified | NO |
| `pwa/` modified | NO |
| `pwa/assets/earth/candidates/` written | NO |
| `pwa/assets/earth/production/` written | NO |
| WDBII L03+ used | NO |
| River proxy merged into `inland_water_mask` | NO |
| git push performed | NO |
| NPZ committed | NO |

---

## 8. Revision Status

| Item | Status |
|------|--------|
| `scripts/generate_b6_structure_masks.py` updated | YES |
| Generator run at 2048×1024 | YES |
| 35-mask NPZ generated | YES |
| `devlog.md` appended | YES |
| This doc created | YES |
| B-6.2G-3C-R validation audit | PENDING |
| Script committed | PENDING |

---

*B-6.2G-3B-R — coverage supplement only. L01 baseline preserved. No d6 changes. No pwa changes.*
