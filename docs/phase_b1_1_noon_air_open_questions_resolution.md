# Phase B-1.1 — Noon Air Open Questions Resolution

> Created: 2026-06-09
> Status: Decisions recorded — awaiting authorization before Phase B-2 implementation begins
> Prerequisite: Phase B-1 Generator Script Design approved and pushed
> Resolves: 5 open questions from `docs/phase_b1_noon_air_generator_script_design.md` §12

---

## 1. Purpose

Phase B-1 identified 5 technical questions that must be resolved before `d6_noon_air_earth_generator.py` is created. This document records the authoritative answers to those questions as binding implementation constraints.

These decisions are:
- Not a suggestion — they are implementation prerequisites
- Not negotiable at Phase B-2 start without a new revision to this document
- Designed to minimize risk, preserve audit trail, and protect the d5z_b production baseline

This document does not authorize implementation. Phase B-2 (script creation and 2K dry-run) requires separate explicit authorization.

---

## 2. Decision Summary

| # | Question | Decision |
|---|---|---|
| Q1 | Color parameter system | HSL-delta primary + localized RGB blend for highlights only |
| Q2 | Mask and pipeline dependency | Standalone d6 parameters; no import of config.py or shared D5 state |
| Q3 | Baseline guard failure behavior | ABORT if d5z_b baseline missing; no silent skip |
| Q4 | Feathering method | Gaussian blur on mask (v1); distance field deferred to v2+ |
| Q5 | Island halo radius scaling | `scaled_px = base_px_at_8k × current_width / 8192` |

---

## 3. Q1 — Color Parameter System

**Question:** Should `NOON_AIR_OCEAN_REGIONS` use the `rgb_offset` approach from `config.py`, or adopt an HSL-delta system?

### Decision: HSL-delta primary + localized RGB blend for highlights

**Color adjustment hierarchy for `d6_noon_air_earth_generator.py`:**

| Layer | Method | When to use |
|---|---|---|
| Primary | HSL-delta | All large-region ocean, land, desert, polar adjustments |
| Secondary | Localized RGB blend with mask weight | Reef highlights, island shallow halos, narrow coastal zones |
| Prohibited | Direct pixel replacement with HEX | Never — HEX values are tonal targets only |
| Prohibited | Global single-channel offset | Never alone — always embedded in HSL or masked blend |

**HSL-delta parameter structure (replaces pure rgb_offset):**

```python
{
    "hue_shift":          float,   # degrees, -30 to +30; 0 = no hue change
    "saturation_delta":   float,   # -0.30 to +0.20; negative = desaturate
    "lightness_delta":    float,   # -0.20 to +0.15; negative = darken
    "apply_to_hue_range": (float, float),  # (min_hue, max_hue) in degrees; None = all hues
    "mask_weight":        float,   # 0.0 to 1.0; blend strength at mask center
    "feather_px":         int,     # Gaussian sigma for mask boundary smoothing
}
```

**Localized RGB blend (secondary, for reefs and shallow highlights only):**

```python
{
    "target_hex":   str,     # e.g. "#5FD3D8" — tonal target reference
    "blend_weight": float,   # 0.05 to 0.25; never > 0.30
    "mask_weight":  float,
    "feather_px":   int,
    "deep_gate":    bool,    # True = only apply outside deep ocean zone
}
```

**Why not pure rgb_offset:**
- RGB offset accumulates across passes and creates unpredictable color drift in mixed-tone regions (coastlines, desert-ocean edges)
- HSL separates hue/saturation/lightness concerns cleanly, matching how the Noon Air Earth spec describes targets
- Noon Air Earth forbids hard color replacements; HSL-delta naturally preserves texture while shifting tone
- Previous D5b pipeline used rgb_offset as a practical shortcut; Phase B is an opportunity to do this properly

**Hard constraint:** All HEX values in `rodio_day_earth_target_color_spec_and_benchmark_matrix.md` are tonal reference targets. The generator must never use them as pixel fill values or direct replacement targets.

---

## 4. Q2 — Mask and Pipeline Dependency Strategy

**Question:** Should `d6_noon_air_earth_generator.py` import `masks.py` from the D5b pipeline, or reproduce the mask logic inline?

### Decision: Standalone d6 parameters; algorithmic reuse permitted, state/import coupling prohibited

**Rules:**

1. **No import of `config.py`.** D5b's `OCEAN_REGIONS`, `ISLAND_HALOS`, and `OUTPUT` configs are specific to the D5b design system. Importing them would couple d6 to D5b assumptions and risk unintended behavioral inheritance.

2. **No import of `d5z_generator.py`.** D5z is a closed generation pass. D6 does not extend it.

3. **Conditional import of `masks.py` utility functions is permitted only if:**
   - The function is a pure utility with no side effects (e.g., `make_region_mask`, `make_ocean_mask_v2`)
   - Importing it does not pull in D5b configuration state
   - The imported function is clearly documented in d6's source header as a borrowed utility

4. **Preferred approach (v1):** Reproduce the ocean mask detection inline in d6. The logic is simple (pixel HSV thresholding), and having it inline makes d6 fully self-contained and auditable without reading masks.py.

5. **All color parameters** (region bounds, HSL deltas, island halo definitions, polar correction params) are defined as standalone dicts inside d6. They are Noon Air Earth parameters — not D5b parameters.

**Why independence matters:**
- If D5b pipeline is ever updated, d6 must not silently change behavior
- Phase B-2 reviewers should be able to understand d6 by reading one file
- Rollback of d6 must not require rollback of the shared D5b module

**What is permitted:**
```python
# OK — pure algorithmic utility, no D5b state imported
from d5b_processor_v3.masks import make_region_mask, lon_lat_to_uv

# OK — standard library and data science deps
import numpy as np
from PIL import Image
import json, os, sys, argparse
from pathlib import Path
```

**What is prohibited:**
```python
# NOT OK — imports D5b design configuration
from d5b_processor_v3.config import OCEAN_REGIONS, ISLAND_HALOS

# NOT OK — imports full D5b pipeline state
from d5b_processor_v3.main import main as d5b_main
```

---

## 5. Q3 — Baseline Guard Failure Behavior

**Question:** If `d5z_b_8192x4096.jpg` (the baseline file for the guard) is missing, should the guard degrade gracefully or abort?

### Decision: ABORT — no silent skip; baseline absence is a hard failure

**Behavior when baseline file is absent:**

```
[GUARD] ERROR: d5z_b baseline file not found.
  Expected: pwa/assets/earth/candidates/d5z_b_8192x4096.jpg
  The E1 / d5z_b baseline floor comparison cannot be performed.
  This candidate generation cannot be trusted without baseline verification.
  
  Resolution: Ensure d5z_b_8192x4096.jpg is present in pwa/assets/earth/candidates/.
  This file is gitignored; copy it from pwa/assets/earth/production/d5z_b_8192x4096.jpg.
  
  Aborting. Use --skip-baseline-guard to override (not recommended for v1).

SystemExit: 1
```

**Why ABORT, not warn-and-continue:**
- `d5z_b` is the current production texture and the E1-verified floor
- The baseline guard exists precisely because we cannot trust our eyes alone for regression detection
- A candidate that has not been compared against the production baseline is not a valid candidate — it is an unknown
- "Continue with warning" creates a path where developers habitually skip the guard by not having the baseline file present

**`--skip-baseline-guard` flag:**
- Reserved for future implementation only
- Not implemented in v1 of the generator
- If added in a future version, it must print a prominent warning and require a second confirmation:
  ```
  WARNING: Baseline floor guard skipped. This candidate is unverified against d5z_b.
  This output MUST NOT be promoted to production.
  ```

**Baseline file resolution instructions (to include in error message):**
```bash
# If d5z_b is not in candidates/, copy from production:
cp pwa/assets/earth/production/d5z_b_8192x4096.jpg \
   pwa/assets/earth/candidates/d5z_b_8192x4096.jpg
```
The production file is always authoritative. The candidates/ copy is the guard's comparison target.

---

## 6. Q4 — Feathering Method

**Question:** Should region boundary feathering use Gaussian blur on the region mask, or a distance-field approach?

### Decision: Gaussian blur on mask for v1; distance field deferred

**v1 implementation:**

```python
def feather_mask(mask: np.ndarray, feather_px: int) -> np.ndarray:
    """
    Apply Gaussian blur to a binary mask to produce a soft boundary.
    feather_px is the standard deviation of the Gaussian kernel.
    """
    from PIL import ImageFilter
    mask_img = Image.fromarray((mask * 255).astype(np.uint8))
    blurred = mask_img.filter(ImageFilter.GaussianBlur(radius=feather_px))
    return np.array(blurred).astype(np.float32) / 255.0
```

**Feather radius guidelines (at 8K = 8192px width):**

| Region type | feather_px (8K) | feather_px (2K) | Notes |
|---|---:|---:|---|
| Ocean basin boundary | 40–60 | 10–15 | Wide open-ocean transitions |
| Continental shelf | 20–32 | 5–8 | Medium blend zone |
| Coastline / nearshore | 12–20 | 3–5 | Tighter — preserve coastline character |
| Small island halo | 8–16 | 2–4 | Tight for small islands at globe scale |
| Desert / land region | 32–48 | 8–12 | Gradual land-to-land transitions |
| Polar ice boundary | 20–32 | 5–8 | Ice-to-ocean transition |

Feather radius scales with resolution: `feather_px_at_res = feather_px_at_8k × current_width / 8192`

**Why Gaussian blur for v1:**
- Simple, well-understood, reproducible
- Native PIL support — no additional dependencies
- Behavior is predictable and auditable from the processing log
- Gaussian blur feathering has been verified to work adequately in the D5b/D5z pipeline

**Why distance field is deferred:**
- Distance field feathering gives superior results near complex coastlines and island chains, where uniform Gaussian blur can bleed inland
- It is more computationally expensive and requires scipy or a custom implementation
- Phase B-1 priority is a correct, auditable v1 — not the most sophisticated feathering possible
- If v1 review shows visible Gaussian blur artifacts at coastlines, distance field can be introduced in v2 as a targeted improvement

---

## 7. Q5 — Island Halo Radius Scaling

**Question:** What is the correct formula for converting island halo radii from km to pixels at different output resolutions?

### Decision: Scale from 8K base using `scaled_px = base_px_at_8k × current_width / 8192`

**Formula:**

```python
def km_to_pixels(radius_km: float, image_width: int) -> int:
    """
    Convert a halo radius in km to pixels at a given equirectangular image width.
    
    Earth circumference at equator ≈ 40075 km.
    At 8192px width, 1 pixel ≈ 40075 / 8192 ≈ 4.89 km.
    """
    KM_PER_PIXEL_AT_8K = 40075.0 / 8192.0   # ≈ 4.89 km/px
    base_px_at_8k = radius_km / KM_PER_PIXEL_AT_8K
    return max(1, round(base_px_at_8k * image_width / 8192))
```

**Reference table for common halo sizes:**

| Island type | Halo radius | 8K px | 2K px | 21.6K px |
|---|---:|---:|---:|---:|
| Tiny atoll (Maldives) | 80 km | ~16 px | ~4 px | ~42 px |
| Small tropical island | 120 km | ~25 px | ~6 px | ~63 px |
| Medium island group | 160 km | ~33 px | ~8 px | ~84 px |
| Large archipelago | 300 km | ~61 px | ~15 px | ~158 px |

**Island halo rendering rules:**

1. A halo of 1–4 pixels at the working resolution is the target for small atolls — this corresponds to ~5–20 km at 8K.
2. Halos must not form visible ring artifacts or sharp boundaries — the feather must be ≥ 25% of the halo radius.
3. At 2K dry-run resolution, some tiny halos may be too small to see clearly — this is expected. The 2K pass is for color correctness, not fine island detail. 8K is where island visibility is evaluated.
4. The `deep_gate` mechanism must be applied for all island halos: do not enhance shallow-water color in zones that are already confirmed deep ocean by the ocean mask. This prevents halos from appearing in the middle of open ocean.

**Distinct color palettes required by island type:**

| Type | Shallow color target | Notes |
|---|---:|---|
| Tropical (Maldives, Bahamas, Fiji…) | `#2FAAC0` → `#5FD3D8` | Cyan-blue; warm |
| High-latitude (Svalbard, Canadian Arctic…) | `#63AFC8` → `#A8DCE4` | Cold blue-grey; muted |

Never use tropical cyan-blue (`#5FD3D8`) for high-latitude island halos. Never use cold grey-blue (`#63AFC8`) for tropical island halos. These are hard constraints, not preferences.

---

## 8. Implementation Constraints for Phase B-2

When `d5b_processor_v3/d6_noon_air_earth_generator.py` is created, the following constraints from this document are binding:

| Constraint | Source | Binding Rule |
|---|---|---|
| HSL-delta primary | Q1 | All large-region adjustments use hue/saturation/lightness delta |
| RGB blend localized only | Q1 | Max blend_weight 0.30; always masked; deep_gate for islands |
| HEX as tonal reference only | Q1 | No pixel replacement, no fill, no direct mapping |
| d6 params standalone | Q2 | No import of config.py; NOON_AIR_* dicts defined inside d6 |
| masks.py import conditional | Q2 | Only pure utilities; no config state imported |
| d5z_b absent → ABORT | Q3 | Hard abort, not warning; no silent skip in v1 |
| Gaussian blur feather | Q4 | `ImageFilter.GaussianBlur(radius=feather_px)` |
| feather_px resolution-scaled | Q4 | `feather_px_at_res = feather_px_at_8k × width / 8192` |
| halo radius resolution-scaled | Q5 | `km_to_pixels(km, width)` using earth circumference formula |
| Tropical / high-lat separate | Q5 | Different target HEX tables; never share palettes |
| Default: 2K dry-run only | Phase B plan | `--full-res` required for 8K |
| No production writes | Phase B plan | Module-level assertions; OUT_DIR must not contain production/ |
| No runtime file changes | Phase B plan | No writes outside d5b_output/noon_air_candidates/ and previews/ |

---

## 9. Files Not To Touch

These files must not be modified during Phase B-2 (script creation and 2K dry-run):

| File / Directory | Reason |
|---|---|
| `d5b_processor_v3/config.py` | D5b design config — d6 parameters are independent |
| `d5b_processor_v3/d5z_generator.py` | D5z is closed; d6 is its successor, not a continuation |
| `pwa/earth3d.js` | No runtime changes until Three.js testing stage |
| `DAY_TEXTURE_VARIANT` | Stays `'d5z_b'` until full acceptance and explicit promotion |
| `pwa/assets/earth/production/` | Production-only; never written during candidate generation |
| `pwa/assets/source/` | Read-only inputs |
| Any existing candidate JPG | No overwriting; d5z_a and d5z_b are archived |

---

## 10. Strict Non-Execution Confirmation

This document is design-only. The following was confirmed during its creation:

| Prohibition | Status |
|---|---|
| `d6_noon_air_earth_generator.py` created | ✅ Not created |
| `config.py` modified | ✅ Not modified |
| `d5z_generator.py` modified | ✅ Not modified |
| `pwa/earth3d.js` modified | ✅ Not modified |
| `DAY_TEXTURE_VARIANT` modified | ✅ Not modified (`'d5z_b'` unchanged) |
| Production texture modified | ✅ Not modified |
| Python executed | ✅ Not executed |
| 2K or 8K image generated | ✅ Not generated |
| Data downloaded | ✅ Not downloaded |
| commit executed | ✅ Not executed |
| push executed | ✅ Not executed |
