# Phase B — Noon Air Earth Candidate Generation Plan

> Created: 2026-06-09
> Status: Plan — awaiting authorization before any execution begins
> Prerequisite: Phase A closed; d5z_b in production; existing 21.6K source + D5/D5z pipeline confirmed sufficient

---

## 1. Purpose

Phase B translates the Noon Air Earth color specification into a concrete candidate image generation plan.

**What Phase B is:**
- A planned pipeline run against the existing 21.6K source with updated color parameters derived from `rodio_day_earth_target_color_spec_and_benchmark_matrix.md`
- A staged process: 2K dry-run → human review → 8K candidate → preview → Three.js local validation → acceptance decision

**What Phase B is not:**
- A direct replacement of `d5z_b` in production
- A modification of `DAY_TEXTURE_VARIANT`
- An authorization to push any new texture to `production/`
- An authorization to begin until this plan is explicitly approved

**Invariants that hold throughout Phase B:**
- `d5z_b` remains the live production texture until explicitly promoted away
- No candidate bypasses the preview → Three.js local validation → human acceptance gate
- Any candidate that regresses below the d5z_b baseline floor is rejected

---

## 2. Inputs and Baseline

### 2.1 Production baseline (floor, not ceiling)

```
pwa/assets/earth/production/d5z_b_8192x4096.jpg
```

This is the E1-verified stable baseline. All Phase B candidates must meet or exceed it on:
- Default load stability
- UI readability
- Standard player view overall impression (lon=10, lat=20, all time modes)
- Global coverage completeness
- Multi time-mode stability
- No regression in E1 protected regions: Japan, Mediterranean, Caribbean, Pacific Islands

`d5z_b` is the floor, not the target. The target is Noon Air Earth.

### 2.2 Primary source image

```
pwa/assets/source/earth_day_source_21600x10800.jpg   (20MB, 21.6K×10.8K)
```

This is the master from which all D5 series candidates were generated. It is a NASA Blue Marble Next Generation derivative already at 21.6K resolution. Phase B uses this as the canonical input.

**Why start from 21.6K source rather than from d5z_b or d5b_design_v3_2_1:**
Noon Air Earth is a full-spectrum rethink of ocean, land, polar, and desert color. Starting from a previous correction pass means inheriting its assumptions and limitations. Starting fresh from the source allows Noon Air Earth parameters to be applied without accumulated prior-pass drift.

### 2.3 Reference candidates (for comparison only, not for editing)

| Candidate | Role in Phase B |
|---|---|
| `d5b_design_v3_2_1_8192x4096.jpg` | E1 formal baseline — before/after reference |
| `d5z_b_8192x4096.jpg` (candidates copy) | Production baseline — before/after reference |

### 2.4 Pipeline reference implementations

| File | Role |
|---|---|
| `d5b_processor_v3/main.py` | Full regional pipeline architecture reference |
| `d5b_processor_v3/config.py` | 98-region parameter system (OCEAN_REGIONS + ISLAND_HALOS) |
| `d5b_processor_v3/d5z_generator.py` | Standalone correction pass template |
| `d5b_processor_v3/enhancement.py` | Global base parameter system |
| `d5b_processor_v3/metrics.py` | Regional metrics and acceptance checking |
| `d5b_processor_v3/preview.py` | Compare crop and preview generation |
| `d5b_processor_v3/make_small.py` | 2K downscale utility for dry-run |

---

## 3. Candidate Naming

### 3.1 Output file names

**2K dry-run:**
```
noon_air_v1_2048x1024.jpg
```

**8K candidate (only after 2K passes):**
```
noon_air_v1_8192x4096.jpg
```

Naming convention: `noon_air_v<major>_<width>x<height>.jpg`

Major version increments when the color system design changes substantially (e.g., v1 → v2 means a fundamentally different approach, not a minor tweak). Tweaks within the same design system use sub-runs documented in the processing log.

### 3.2 Output directories

**Processing output:**
```
d5b_processor_v3/d5b_output/noon_air_candidates/
```

All intermediate, dry-run, compare crop, metrics, and log files go here. This directory is gitignored (covered by `d5b_processor_v3/d5b_output/` in `.gitignore`).

**Preview output:**
```
previews/noon_air_v1_2k/
```

Regional before/after crops, difference maps, metrics summary for human review. This directory is gitignored (covered by `previews/**/*.png` and `previews/**/*.jpg`).

**8K candidate (if approved):**
```
pwa/assets/earth/candidates/noon_air_v1_8192x4096.jpg
```

Gitignored. Not promoted to `production/` until full acceptance.

**Must never write to:**
```
pwa/assets/earth/production/   ← production only, never during Phase B
pwa/assets/source/             ← source images, read-only
```

---

## 4. Generator Design

### 4.1 New file to create (Phase B execution only, not this planning turn)

```
d5b_processor_v3/d6_noon_air_earth_generator.py
```

**Architecture:** Standalone correction pass — same pattern as `d5z_generator.py`:
- Self-contained, no import of other generator passes
- Does not inherit state from any prior pass
- Explicit path assertions: never writes to `production/`, never touches `earth3d.js`
- Dry-run flag: `--dry-run` outputs 2K only, skips 8K
- Preview flag: `--preview-only` generates crops and metrics without saving the full candidate
- Processing log saved to output directory

### 4.2 Design principles for the generator

- Reads `earth_day_source_21600x10800.jpg` (21.6K); downscales to 8K working resolution before processing
- All operations on the 8K working array; no processing at 21.6K (memory constraint)
- For 2K dry-run: downscale source to 2K first, then apply same processing
- Region definitions as a standalone config dict inside the generator (not imported from `config.py`, to avoid coupling to D5b design assumptions)
- Each processing module is a named function with clear input/output contract
- Protected region diff guard runs at end: compares Japan, Mediterranean, Caribbean, Pacific Islands against d5z_b baseline

### 4.3 Safety assertions (must be in the generator)

```python
assert "production" not in str(OUTPUT_PATH)
assert str(OUTPUT_PATH) != str(REPO_ROOT / "pwa/assets/earth/candidates")
assert not OUTPUT_PATH.parts[-1].startswith("d5z_")   # don't overwrite d5z series
```

---

## 5. Processing Strategy

The processing pipeline follows the priority order from `rodio_day_earth_target_color_spec_and_benchmark_matrix.md` §13.

### 5.1 Module sequence

| Step | Module | Spec Reference | Method |
|---|---|---|---|
| 1 | Global base adjustment | §4.1 | Global brightness +3–6%, contrast -3–6%, saturation -4–8%, blue channel +4–8%, green sat -8–15%, yellow sat -5–12% |
| 2 | Deep ocean | §5.1 | Regional HSL targeting #05395F main, per-basin darkening/lightening, feathered boundaries |
| 3 | Continental shelf / shallow water | §5.2 | Gradient from deep (#0A5F84) → shelf (#197FA0) → nearshore (#2FAAC0); continuous, no hard edges |
| 4 | Islands and reefs | §6.1–6.5 | Per-island halo system; tropical vs. high-latitude separate treatment; deep-gate guard |
| 5 | Polar regions | §7.1–7.3 | Antarctica: compress to #DDECF2 main; Greenland: terrain-aware with fjord detail; Arctic sea ice: thin-ice treatment |
| 6 | Desert and dryland | §9.1–9.3 | Sahara/Arabia: #C49B6F main, suppress to #D8BC91 max; plateau: grey-brown not yellow; Australia: red-brown |
| 7 | Land vegetation | §8.1–8.3 | Temperate: desaturate to #6E8F63 max; rainforest: deep olive #2F5A3E; savanna: between green and sand |
| 8 | Mountains and plateaus | §10.1–10.2 | Himalaya snowline preservation; Alps/Rockies/Andes relief |
| 9 | Special seas | §11.1–11.4 | Mediterranean (#0A638A main); Red Sea; Yellow/East China; Caribbean |
| 10 | Atmospheric blue overlay | §4.2 | #8FC4E6 soft-light/screen 4–8% opacity, max 10% |
| 11 | E1/d5z_b baseline floor guard | Spec §15 | Diff check on 4 protected regions; reject if any exceed threshold |

### 5.2 Implementation constraints

- HEX values are tonal targets, not pixel replacement values.
- All adjustments use HSL/curve/local blend/mask-weighted approach.
- No single LUT applied globally.
- No hard edges — all region boundaries feathered minimum 20px at 8K (≈ 10px at 2K).
- Original texture, coastlines, terrain, seafloor, glacier, desert detail must be preserved.
- Turbid seas (Yellow Sea, Bohai, Bengal Bay, Amazon delta) must NOT be treated as tropical clear water.

---

## 6. 2K Dry-run Stage

**This stage is mandatory before any 8K generation.**

### 6.1 What gets generated

```
d5b_processor_v3/d5b_output/noon_air_candidates/noon_air_v1_2048x1024.jpg
d5b_processor_v3/d5b_output/noon_air_candidates/noon_air_v1_2k_processing_log.txt
previews/noon_air_v1_2k/
  ├── global_preview.jpg
  ├── global_diff_vs_d5zb.jpg
  ├── metrics_summary.json
  ├── before_after_maldives.jpg
  ├── before_after_bahamas.jpg
  ├── before_after_caribbean.jpg
  ├── before_after_antarctica.jpg
  ├── before_after_greenland.jpg
  ├── before_after_yellow_sea_east_china.jpg
  ├── before_after_japan.jpg
  ├── before_after_sahara.jpg
  ├── before_after_mediterranean.jpg
  ├── before_after_red_sea.jpg
  ├── before_after_french_polynesia.jpg
  ├── before_after_hawaii.jpg
  ├── before_after_tibetan_plateau.jpg
  ├── before_after_amazon.jpg
  ├── before_after_pacific_islands.jpg
  └── before_after_europe_middle_east.jpg
```

### 6.2 Human review checklist at 2K

Before approving 8K generation, verify against `rodio_day_earth_target_color_spec_and_benchmark_matrix.md` §16:

```
[ ] Deep ocean is clear blue, not black
[ ] Shallow water has layered cyan-blue, not fluorescent
[ ] Tropical islands are identifiable with shallow halo
[ ] Maldives / Bahamas / Fiji: fine-grained reef highlights
[ ] High-latitude islands use cold blue-grey, not tropical cyan
[ ] Antarctica: ice texture preserved, no dead-white
[ ] Greenland: fjord, bare rock, glacier flow line preserved
[ ] Sahara / Arabia: highlights suppressed, warm not washed-out
[ ] Tibetan Plateau: cool grey-brown, not desert yellow
[ ] China East / Japan / Europe: no map-app green
[ ] Amazon / Congo / SE Asia: deep olive, not bright green
[ ] Yellow Sea / Bohai: slightly grey-blue, not yellow-brown
[ ] Mediterranean / Caribbean / Sea of Japan: regional differentiation
[ ] Overall: transparent, bright, unified, geographic identity preserved
[ ] No hard edge artifacts at any regional boundary
[ ] Not worse than d5z_b on any dimension
```

### 6.3 Decision gate after 2K review

| Outcome | Action |
|---|---|
| Pass | Authorize 8K candidate generation |
| Conditional Pass (minor issues) | Iterate parameters, re-run 2K dry-run |
| Fail | Stop; diagnose; revise processing strategy |

---

## 7. 8K Candidate Stage

**Only executed after 2K dry-run receives explicit Pass or Conditional Pass.**

### 7.1 Output

```
d5b_processor_v3/d5b_output/noon_air_candidates/noon_air_v1_8192x4096.jpg
d5b_processor_v3/d5b_output/noon_air_candidates/noon_air_v1_8k_metrics.json
d5b_processor_v3/d5b_output/noon_air_candidates/noon_air_v1_8k_processing_log.txt
d5b_processor_v3/d5b_output/noon_air_candidates/noon_air_v1_8k_diff_vs_d5zb.jpg
```

### 7.2 Copy to candidates (only after 8K review approval)

```
pwa/assets/earth/candidates/noon_air_v1_8192x4096.jpg
```

This copy step requires separate authorization. The 8K output in `d5b_output/noon_air_candidates/` is a processing artifact. The copy to `pwa/assets/earth/candidates/` is the step that enables Three.js testing.

### 7.3 Register in earth3d.js (only after copy approval)

Add to `getDayTexturePaths()`:
```javascript
noon_air_v1: ['/assets/earth/candidates/noon_air_v1_8192x4096.jpg', '/assets/bluemarble.jpg'],
```

This is a additive change — does not change `DAY_TEXTURE_VARIANT`. Enables `?dayTexture=noon_air_v1` testing only.

---

## 8. Regional Preview and Comparison

### 8.1 Benchmark regions for Phase B

All 12 regions from `rodio_day_earth_target_color_spec_and_benchmark_matrix.md` §12, plus the Noon Air Earth execution checklist additions:

| Region | Priority | Noon Air Earth Key Challenge |
|---|---|---|
| Maldives | High | Atoll ring highlights, deep-ocean contrast |
| Bahamas / Caribbean | High | Shallow shelf transparency, hard-edge risk |
| Fiji / French Polynesia | High | Pacific deep + high-island contrast |
| Antarctica | High | Blowout control, texture preservation |
| Greenland / Arctic | High | Fjord detail, bare rock, ice margin |
| Sahara / Egypt / Arabia | High | Highlight suppression, warmth |
| Yellow Sea / Bohai / East China Sea | High | Turbid-sea treatment, no over-brightening |
| Japan / East Sea | Medium | Coastline, temp-forest desaturation |
| Mediterranean | Medium | Deep-blue transparency, Aegean shallows |
| Red Sea | Medium | Warm-cold desert-ocean contrast |
| Amazon / Congo | Medium | Deep olive, river texture |
| Tibetan Plateau / Himalayas | Medium | Cold grey-brown, snowline |
| Hawaii | Medium | Deep Pacific surrounding |
| Europe / Middle East wide | Medium | Multi-zone harmony |
| Pacific Islands wide | Medium | Global harmony anchor |
| SE Asia / Indonesia | Medium | Dense archipelago, turbid-vs-clear |

**Japan is one of sixteen — it is the method-validation region from prior RDL work, not the final target.**

---

## 9. Three.js Local Validation

### 9.1 Setup

1. Copy approved 8K candidate to `pwa/assets/earth/candidates/noon_air_v1_8192x4096.jpg`
2. Add `noon_air_v1` key to `getDayTexturePaths()` in `earth3d.js`
3. Do NOT change `DAY_TEXTURE_VARIANT`
4. Test via: `http://localhost:8080?dayTexture=noon_air_v1`

### 9.2 Screenshot protocol

For each of the 12 benchmark regions × 4 time modes:
- morning (golden hour), noon (direct light), afternoon (warm angle), sunset (low angle)
- Standard player view: lon=10, lat=20 (full-globe orientation shot)
- Region-specific zoom angles for detail shots

Minimum 48 screenshots (12 × 4). Plus UI integration shots at standard player view.

### 9.3 Comparison baseline

Side-by-side with `d5z_b` screenshots from E1-R5 archive (`previews/e1_r5_full_acceptance/`).

### 9.4 Decision gate after Three.js validation

| Outcome | Action |
|---|---|
| Pass | Proceed to production promotion (requires separate authorization) |
| Conditional Pass | Document Partial regions; if ≤2 Partial and only ocean/polar, may proceed |
| Fail | Return to parameter adjustment; no production promotion |

---

## 10. Acceptance Criteria

A Phase B candidate is accepted for production promotion when all of the following hold:

**Baseline floor (inherited from E1, non-negotiable):**
- Default load: HTTP 200, `noon_air_v1` variant resolves at 8192×4096
- UI readability: player text, controls, album art legible at all benchmark angles
- Not worse than `d5z_b` on any E1 protected region (Japan, Mediterranean, Caribbean, Pacific Islands)
- Multi time-mode stability: no blowout, grey-flatten, or color shift across 4 modes

**Noon Air Earth targets (positive requirements):**
- Deep ocean: clear blue at #05395F–#126B92 range — not black, not grey
- Shallow water: visible layered hierarchy — reef / shelf / open ocean differentiated
- Islands: tropical island groups identifiable with shallow halo at globe scale
- Antarctica / Greenland: texture preserved, blue-white tone, no dead-white
- Desert (Sahara/Arabia): warm sand tone, highlights suppressed
- Land: no map-app saturated green in Japan / Europe / China East
- Special seas: Mediterranean / Caribbean / Red Sea / Yellow Sea show regional character
- Overall: transparent, restrained, noon-air aesthetic — not GIS, not NASA black-blue

---

## 11. Rollback / Stop Conditions

Stop and do not proceed to the next stage if any of the following are observed:

```
× 2K dry-run is visually worse than d5z_b in any significant region
× Any E1 protected region shows detectable regression
× Deep ocean approaches black in any basin
× Shallow ocean shows fluorescent or cyber-blue
× Any region shows hard color-block seam from regional correction boundary
× Antarctica or Greenland shows dead-white or texture erasure
× Sahara / Arabia shows grey, dirty, or overexposed result
× Any region (Japan, Europe, China East) shows map-app saturated green
× UI readability degraded at standard player view
× Three.js shows severe color shift, tiling artifacts, or load failure
× Global color harmony broken — one region's correction creates visible seam
```

On stop: document the failure mode specifically, return to §5 Processing Strategy, revise the affected module, re-run 2K dry-run.

---

## 12. Files To Create

These files will be created during Phase B execution. **None are created in this planning turn.**

| File | Stage | Purpose |
|---|---|---|
| `d5b_processor_v3/d6_noon_air_earth_generator.py` | Phase B start | Main generator script |
| `d5b_processor_v3/d5b_output/noon_air_candidates/noon_air_v1_2048x1024.jpg` | 2K dry-run | 2K visual review candidate |
| `previews/noon_air_v1_2k/*.jpg` | 2K dry-run | Before/after region crops |
| `d5b_processor_v3/d5b_output/noon_air_candidates/noon_air_v1_8192x4096.jpg` | 8K stage (post-2K pass) | Full-resolution candidate |
| `pwa/assets/earth/candidates/noon_air_v1_8192x4096.jpg` | Three.js testing (post-8K approval) | Candidate for local validation |

---

## 13. Files Not To Touch

These files must not be modified during Phase B:

| File / Directory | Reason |
|---|---|
| `pwa/earth3d.js` | No runtime changes until Three.js testing stage authorizes variant key addition |
| `DAY_TEXTURE_VARIANT` | Stays `'d5z_b'` until production promotion |
| `pwa/assets/earth/production/` | Production-only; never written during candidate generation |
| `pwa/assets/source/` | Source images are read-only inputs |
| `d5b_processor_v3/config.py` | D5b design config; Phase B uses standalone config in new generator |
| `d5b_processor_v3/d5z_generator.py` | D5z reference; do not modify |
| `pwa/assets/earth/candidates/d5z_*` | D5z series is archived; do not overwrite |
| Any existing candidate JPG | No overwriting prior candidates |
| `devlog.md` | Updated only on task completion |

---

## 14. Phase B Execution Boundaries

Phase B is gated at every major transition. Each gate requires explicit authorization before proceeding:

```
[Plan approved]           ← This document
       ↓
[Create generator script]
       ↓
[2K dry-run]
       ↓
[Human visual review of 2K]
       ↓
[Authorize 8K generation]
       ↓
[8K candidate generated]
       ↓
[8K regional preview review]
       ↓
[Authorize copy to candidates/]
       ↓
[Register variant in earth3d.js]
       ↓
[Three.js local validation]
       ↓
[Human acceptance decision]
       ↓
[Authorize production promotion]  ← Phase C (not Phase B)
```

**Phase B scope ends at "Human acceptance decision."**
Production promotion is Phase C and requires a separate explicit authorization.

---

## 15. Next Action

This document is the Phase B plan. It is awaiting RW / Evan review.

**On approval, Phase B execution begins with:**
1. Create `d5b_processor_v3/d6_noon_air_earth_generator.py`
   - Architecture based on `d5z_generator.py`
   - Standalone config dict translating §4–§11 of Noon Air Earth spec
   - Dry-run flag, preview-only flag, processing log
   - Safety assertions: no production writes, no earth3d.js changes

2. Run 2K dry-run:
   ```
   python3 d5b_processor_v3/d6_noon_air_earth_generator.py --dry-run
   ```

3. Review 2K output against Noon Air Earth spec and d5z_b baseline.

4. Await authorization before 8K run.

**Not starting yet:**
- No generator script created
- No Python run
- No 2K or 8K image generated
- No runtime changes
- No production changes
