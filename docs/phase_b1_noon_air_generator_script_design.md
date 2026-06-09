# Phase B-1 — Noon Air Earth Generator Script Design

> Created: 2026-06-09
> Status: Design spec — not yet implemented
> Target file: `d5b_processor_v3/d6_noon_air_earth_generator.py`
> This document describes the intended design. The Python script does not exist yet.

---

## 1. Purpose

This document specifies the design of `d6_noon_air_earth_generator.py`: the standalone color grading script that will generate the first Noon Air Earth day texture candidate.

The script translates the Noon Air Earth color specification (`docs/rodio_day_earth_target_color_spec_and_benchmark_matrix.md`) into executable image processing operations applied to the existing 21.6K source image.

**Design philosophy:**
- Standalone correction pass — no imports from other generator scripts
- Safety-first: explicit assertions before any write operation
- Default behavior is dry-run (2K output only); 8K requires explicit opt-in
- Every module is independently testable
- Processing log saved alongside output for audit trail

---

## 2. Inputs and Outputs

### 2.1 Primary input

```
pwa/assets/source/earth_day_source_21600x10800.jpg
```

- Read-only. Never modified.
- Loaded once at script start; validated for resolution before processing.
- Downscaled to working resolution before any color operations.

### 2.2 Working resolutions

| Mode | Working Resolution | Downscale Factor |
|---|---:|---|
| 2K dry-run | 2048 × 1024 | ~10.5× from source |
| 8K candidate | 8192 × 4096 | ~2.6× from source |

All color processing operates at the target working resolution — not at 21.6K. The downscale happens first, then processing. This matches the D5b/D5z pipeline approach.

### 2.3 Outputs

| Output | Path | Condition |
|---|---|---|
| 2K dry-run candidate | `d5b_processor_v3/d5b_output/noon_air_candidates/noon_air_v1_2048x1024.jpg` | Always (default mode) |
| 8K candidate | `d5b_processor_v3/d5b_output/noon_air_candidates/noon_air_v1_8192x4096.jpg` | Explicit `--full-res` flag only |
| Processing log | `d5b_processor_v3/d5b_output/noon_air_candidates/noon_air_v1_{res}_log.txt` | Always |
| Metrics JSON | `d5b_processor_v3/d5b_output/noon_air_candidates/noon_air_v1_{res}_metrics.json` | Always |
| Global preview JPG | `d5b_processor_v3/d5b_output/noon_air_candidates/noon_air_v1_{res}_preview_global.jpg` | Always |
| Diff heatmap vs d5z_b | `d5b_processor_v3/d5b_output/noon_air_candidates/noon_air_v1_{res}_diff_vs_d5zb.jpg` | Always |
| Region crop comparisons | `d5b_processor_v3/d5b_output/noon_air_candidates/compare_crops/` | Always |

**Never writes to:**
```
pwa/assets/earth/production/    ← hard assertion
pwa/assets/earth/candidates/    ← not until copy step is separately authorized
pwa/assets/source/              ← source is read-only
```

---

## 3. Command-Line Interface

```
python3 d5b_processor_v3/d6_noon_air_earth_generator.py [OPTIONS]

Options:
  --full-res          Generate 8K output in addition to 2K dry-run
                      Default: off (2K only)
  --preview-only      Generate crops and metrics without saving full candidate
                      Default: off
  --skip-guard        Skip d5z_b baseline floor guard (for diagnostic use only)
                      Default: off
  --help              Show this message
```

Default invocation (2K dry-run only):
```bash
python3 d5b_processor_v3/d6_noon_air_earth_generator.py
```

Full 8K run (only after 2K approval):
```bash
python3 d5b_processor_v3/d6_noon_air_earth_generator.py --full-res
```

---

## 4. Script Structure

### 4.1 File layout

```python
d6_noon_air_earth_generator.py
│
├── ── PROHIBITIONS BLOCK ──────────────────────────
│   Docstring listing all hard prohibitions
│
├── ── IMPORTS ─────────────────────────────────────
│   os, sys, json, math, argparse, datetime
│   numpy, PIL (Image, ImageFilter), pathlib.Path
│
├── ── PATH CONSTANTS ──────────────────────────────
│   REPO_ROOT, SOURCE_PATH, BASELINE_PATH,
│   OUT_DIR, CROPS_DIR
│
├── ── SAFETY ASSERTIONS (module level) ────────────
│   assert "production" not in str(OUT_DIR)
│   assert not SOURCE_PATH == OUT_DIR / "..."
│   (others — see §5)
│
├── ── REGION DEFINITIONS ──────────────────────────
│   NOON_AIR_OCEAN_REGIONS   (deep, shelf, special seas)
│   NOON_AIR_ISLAND_HALOS    (tropical + high-lat)
│   NOON_AIR_POLAR_REGIONS   (Antarctica, Greenland, Arctic)
│   NOON_AIR_LAND_REGIONS    (desert, vegetation, mountain)
│   PROTECTED_REGIONS        (E1 guardrail: Japan, Med, Caribbean, Pacific)
│   BENCHMARK_CROPS          (16 regions for compare output)
│
├── ── MODULE FUNCTIONS ────────────────────────────
│   validate_assets()
│   load_source(res)
│   load_baseline_d5zb(res)
│   apply_global_base(arr)
│   apply_ocean_system(arr, masks)
│   apply_shallow_water(arr, masks)
│   apply_island_halos(arr, masks)
│   apply_polar(arr)
│   apply_desert(arr, masks)
│   apply_land_vegetation(arr, masks)
│   apply_mountain_plateau(arr)
│   apply_special_seas(arr, masks)
│   apply_atmosphere_overlay(arr)
│   run_baseline_floor_guard(arr, baseline_arr)
│   generate_preview_crops(arr, baseline_arr, out_dir)
│   generate_metrics(arr, baseline_arr)
│   save_outputs(arr, res, out_dir, log)
│
└── ── MAIN ENTRY POINT ────────────────────────────
    main(args)
```

### 4.2 Execution flow

```
main()
  │
  ├─ parse_args()
  ├─ validate_assets()              ← abort if source missing
  ├─ load_source(res)               ← downscale to working res
  ├─ load_baseline_d5zb(res)        ← for guard + diff output
  │
  ├─ apply_global_base(arr)
  ├─ apply_ocean_system(arr, masks)
  ├─ apply_shallow_water(arr, masks)
  ├─ apply_island_halos(arr, masks)
  ├─ apply_polar(arr)
  ├─ apply_desert(arr, masks)
  ├─ apply_land_vegetation(arr, masks)
  ├─ apply_mountain_plateau(arr)
  ├─ apply_special_seas(arr, masks)
  ├─ apply_atmosphere_overlay(arr)
  │
  ├─ run_baseline_floor_guard(arr, baseline)   ← warn/fail if regression
  │
  ├─ generate_preview_crops(arr, baseline, crops_dir)
  ├─ generate_metrics(arr, baseline)
  └─ save_outputs(arr, res, out_dir, log)
```

---

## 5. Module Design

### 5.1 Asset Validation (`validate_assets`)

Runs before any processing. Aborts with clear error if any check fails.

```
Checks:
  [ ] SOURCE_PATH exists and is readable
  [ ] SOURCE_PATH resolution is ≥ 21600 × 10800
  [ ] BASELINE_PATH (d5z_b candidate copy) exists and is readable
  [ ] OUT_DIR does not point to production/ or candidates/
  [ ] Disk space estimate: ~500MB free required for 8K run
```

### 5.2 Resolution Validation (inside `load_source`)

```
After downscale:
  [ ] Output array shape matches target (2048×1024 or 8192×4096)
  [ ] No NaN or inf values in array
  [ ] dtype is uint8, range [0, 255]
```

### 5.3 Output Path Safety (module-level assertions)

```python
# Hard assertions — evaluated at import time, not just at runtime
REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR   = REPO_ROOT / "d5b_processor_v3/d5b_output/noon_air_candidates"
PROD_DIR  = REPO_ROOT / "pwa/assets/earth/production"
CAND_DIR  = REPO_ROOT / "pwa/assets/earth/candidates"

assert "production" not in str(OUT_DIR)
assert OUT_DIR != CAND_DIR
assert OUT_DIR != PROD_DIR
assert not OUT_DIR.is_relative_to(PROD_DIR)
assert not OUT_DIR.is_relative_to(CAND_DIR)
```

### 5.4 Global Base Adjustment (`apply_global_base`)

**Spec reference:** `rodio_day_earth_target_color_spec_and_benchmark_matrix.md` §4.1

Parameters (configurable at top of script):
```python
GLOBAL_BASE = {
    "brightness":      +0.04,   # +3% to +6%, midpoint
    "contrast":        -0.045,  # -3% to -6%, midpoint
    "saturation":      -0.06,   # -4% to -8%, midpoint
    "blue_channel":    +0.06,   # +4% to +8%, midpoint
    "green_sat":       -0.12,   # -8% to -15%, midpoint
    "yellow_sat":      -0.08,   # -5% to -12%, midpoint
}
```

Implementation approach:
- Convert to float32 [0,1] for all operations
- Brightness: multiply all channels
- Contrast: apply curve around midpoint 0.5
- Saturation: convert to HSV, scale S channel globally
- Channel-specific: convert to HSL, apply per-hue-range saturation scaling
- Convert back to uint8 after all global operations

Applied first, before any regional work.

### 5.5 Ocean System (`apply_ocean_system`)

**Spec reference:** §5.1–5.2

Region structure — each entry in `NOON_AIR_OCEAN_REGIONS`:
```python
{
    "name":               str,          # region identifier
    "bounds":             (lon_w, lon_e, lat_s, lat_n),
    "ocean_only":         bool,         # apply only to detected water pixels
    "deep_ocean_only":    bool,         # apply only to detected deep water
    "target_hex_main":    str,          # e.g. "#05395F" — tonal target
    "r_offset":           int,          # RGB channel nudge (-20 to +20)
    "g_offset":           int,
    "b_offset":           int,
    "saturation_factor":  float,        # 0.80 to 1.05
    "brightness_factor":  float,        # 0.85 to 1.10
    "feather_px":         int,          # boundary feather at working res
    "blur_px":            int,          # region interior smoothing
    "priority":           int,          # lower = applied first
    "cross_antimeridian": bool,         # for Pacific-spanning bounds
}
```

Key deep-ocean regions to define (derived from spec §5.1):
```
global_deep_ocean_base   — (#05395F main; global water layer, priority 0)
pacific_deep             — deep Pacific basin, north and south
atlantic_deep            — deep Atlantic
indian_ocean_deep        — (#05395F, desaturation correction from E1)
southern_ocean           — cold deep blue
arctic_ocean             — polar-toned deep (#0A4D72)
```

Implementation:
1. Compute ocean mask from pixel HSV analysis (same approach as `masks.py`)
2. For each region sorted by priority: compute region mask with feathering, apply adjustment within `ocean_mask AND region_mask`
3. All adjustments additive/multiplicative, never hard replace

### 5.6 Shallow Water / Continental Shelf (`apply_shallow_water`)

**Spec reference:** §5.2

Approach: depth-from-brightness proxy (no ETOPO1 at this stage for first pass)
- Lighter pixels in ocean zones → nearshore
- Medium pixels → shelf
- Dark pixels → deep
- Apply gradient: #0A5F84 → #197FA0 → #2FAAC0 from deep to shallow, using pixel luminance as depth proxy

Key shelf/nearshore regions: Bohai, Yellow Sea, East China Sea, South China Sea, Persian Gulf, Red Sea, Mediterranean coast, Caribbean outer, Australian shelf, North Sea, Baltic.

All transitions feathered; no hard edges.

### 5.7 Island Halos (`apply_island_halos`)

**Spec reference:** §6.1–6.5

Region structure — each entry in `NOON_AIR_ISLAND_HALOS`:
```python
{
    "name":            str,
    "center":          (lon, lat),
    "halo_radius_km":  float,       # radius of shallow halo zone
    "tropical":        bool,        # True = cyan-blue; False = cold blue-grey
    "r_offset":        int,
    "g_offset":        int,
    "b_offset":        int,
    "strength":        float,       # 0.0 to 1.0 blend weight
    "blur_px":         int,
    "deep_gate":       bool,        # True = only enhance if outside deep ocean
    "max_highlight":   str,         # HEX ceiling — never exceed this luminance
}
```

Tropical islands to include (from spec §6.1–6.4):
```
hawaii, maldives, seychelles, mauritius_reunion, comoros,
lesser_antilles, bahamas, caribbean_cuba_yucatan,
fiji, tonga, samoa, french_polynesia, cook_islands,
micronesia, palau, solomon_islands, vanuatu,
indonesia_east, philippines_south,
bermuda, azores, canary_islands
```

High-latitude islands (from spec §6.5):
```
canadian_arctic, svalbard, franz_josef, greenland_peripheral,
south_georgia, south_shetland, falkland_islands, aleutian_islands
```

Key implementation rule: tropical and high-latitude island halos must use distinct color palettes. Never apply tropical cyan-blue (`#5FD3D8`) to high-latitude islands.

### 5.8 Polar Correction (`apply_polar`)

**Spec reference:** §7.1–7.3

**Antarctica:**
- Detect ice pixels: high luminance (L > 0.75) AND low saturation (S < 0.15) in polar lat zone (< −65°)
- Target main tone: `#DDECF2` (R=221, G=236, B=242)
- Compress brightness to prevent blowout: pixels above `#F2F8FA` are pulled down
- Preserve texture: apply brightness correction with gradient mask — full strength at center, reduced at edges and along detected ridgeline features
- Coastal transition: blend toward `#63AFC8` within 100km of shoreline at working res
- Crevasse/shadow pixels (L < 0.55 in ice zone): push toward `#9CB8C8` shadow tone

**Greenland:**
- Ice cap pixels (lat > 60°N, lon −60° to −15°): similar to Antarctica but lighter touch
- Target center: `#E2EFF3`; shadow: `#A8C4D2`; glacier flow: `#8FAFC0`
- Fjord coast pixels: push toward `#4FA6C2` cold sea tone
- Bare rock detection (medium luminance, higher saturation in coastal zones): preserve `#5E5C50` range

**Arctic sea ice:**
- Fragmented ice — apply lighter treatment than land ice
- Target `#A8DCE4` for thin ice, `#E6F2F5` for thicker ice
- Open polar ocean: `#0A4D72` main

### 5.9 Desert Correction (`apply_desert`)

**Spec reference:** §9.1–9.3

**Sahara / Arabia (spec §9.1):**
- Region bounds: Sahara (−10° to 35°E, 15° to 30°N) + Arabia (35° to 60°E, 12° to 30°N)
- Land pixels only (ocean mask inverse)
- Target main: `#C49B6F`; bright limit: `#D8BC91`; highlight cap: `#E6D0A8` (local only)
- Implementation: detect overly bright desert pixels (L > 0.82), pull down proportionally; do not flatten texture

**Central Asia / Tibetan Plateau edge (spec §9.2):**
- Target: grey-brown `#A3916E`, not warm sand
- Suppress over-yellowing of plateau region

**Australia outback (spec §9.3):**
- Slight reddening toward `#A96F4F`–`#B9825A` range
- Eastern coast green must be preserved

### 5.10 Land Vegetation (`apply_land_vegetation`)

**Spec reference:** §8.1–8.3

Global land saturation pass: after regional ocean work, apply additional green/yellow desaturation to all non-ocean, non-ice, non-desert land pixels.

Key targets:
- Temperate forests/plains: push toward `#6E8F63`–`#8FA77A` range (low-sat grey-green)
- Tropical rainforest (Amazon, Congo, SEA): deep olive `#2F5A3E`–`#4F7651`
- Savanna: `#8A8F61`–`#A3916E` (between green and sand)

Hard constraint: no pixel in Japan, Europe, or eastern China should exceed `#8FA77A` in green saturation after processing.

### 5.11 Mountain and Plateau (`apply_mountain_plateau`)

**Spec reference:** §10.1–10.2

- Himalayas: ensure snowline exists at altitude threshold; suppress over-yellowing of plateau
- Alps/Rockies/Andes: preserve relief; snow peaks `#E4ECEC`–`#F4F8F8` only at high lat/elevation

This module is lighter than polar/ocean/desert — mainly ensuring mountain relief is not flattened by the global desaturation pass.

### 5.12 Special Seas (`apply_special_seas`)

**Spec reference:** §11.1–11.4

Applied after global ocean processing to give each special sea its regional character:

| Sea | Target Main | Key Constraint |
|---|---:|---|
| Mediterranean | `#0A638A` | Deeper than Caribbean; Aegean may be lighter |
| Red Sea | `#0B7192` | Reef zones only near coast |
| Yellow Sea / Bohai | `#3A8EA5` | Grey-blue, not yellow-brown |
| East China Sea | `#197FA0` | Bluer and clearer than Yellow Sea |
| Sea of Japan | `#05395F`–`#07527A` | Distinctly deeper |
| Caribbean | `#0E789B` main | Permitted brighter; reef zones `#6ED9DE` |

### 5.13 Atmospheric Blue Overlay (`apply_atmosphere_overlay`)

**Spec reference:** §4.2

```python
ATMOSPHERE = {
    "color":   "#8FC4E6",   # R=143, G=196, B=230
    "mode":    "soft_light", # or "screen"
    "opacity": 0.06,        # 4% to 8%; must not exceed 10%
}
```

Applied last, after all regional work.

Implementation: create a flat layer filled with `#8FC4E6`, blend onto processed image using soft-light formula:
```
soft_light(base, blend) = base + blend_factor × (2×blend - 1) × (base - base²)
```
Clamp opacity to maximum 10%.

Verify after application: land must not appear grey; desert must not appear muddy; polar regions must not lose texture.

### 5.14 Baseline Floor Guard (`run_baseline_floor_guard`)

**Spec reference:** `rodio_day_earth_target_color_spec_and_benchmark_matrix.md` §15

Load `d5z_b` candidate at matching resolution. For each of the 4 protected regions:

```python
PROTECTED_REGIONS = {
    "japan":           dict(lat_min=30,  lat_max=46,  lon_min=128, lon_max=148),
    "mediterranean":   dict(lat_min=30,  lat_max=48,  lon_min=-10, lon_max=42),
    "caribbean":       dict(lat_min=10,  lat_max=28,  lon_min=-90, lon_max=-60),
    "pacific_islands": dict(lat_min=-15, lat_max=20,  lon_min=140, lon_max=-120),
}

GUARD_THRESHOLDS = {
    "mean_rgb_delta":  8.0,    # max allowed mean RGB shift per protected region
    "luminance_delta": 0.04,   # max allowed mean luminance shift
}
```

For each protected region:
- Crop both `noon_air_v1` and `d5z_b` to region bounds
- Compute mean RGB and luminance for each
- If `abs(delta_mean_rgb) > threshold` or `abs(delta_luminance) > threshold`: LOG WARNING with region name and delta values
- If `--skip-guard` is NOT set and any protected region exceeds threshold: ABORT with clear error message

The guard does not automatically accept — it generates a warning log even if within threshold, so the human reviewer can assess.

### 5.15 Preview Crop Generation (`generate_preview_crops`)

Generates side-by-side before/after crops for each benchmark region.

```python
BENCHMARK_CROPS = {
    "maldives":          dict(lon=73.5,   lat=3.5,   w=640, h=320),
    "bahamas":           dict(lon=-76.5,  lat=24.5,  w=640, h=320),
    "caribbean":         dict(lon=-75.0,  lat=18.0,  w=640, h=320),
    "antarctica":        dict(lon=0.0,    lat=-80.0, w=640, h=320),
    "greenland":         dict(lon=-42.0,  lat=72.0,  w=640, h=320),
    "yellow_east_china": dict(lon=123.0,  lat=32.0,  w=640, h=320),
    "japan":             dict(lon=136.0,  lat=37.0,  w=640, h=320),
    "sahara":            dict(lon=20.0,   lat=25.0,  w=640, h=320),
    "mediterranean":     dict(lon=16.0,   lat=39.0,  w=640, h=320),
    "red_sea":           dict(lon=38.0,   lat=21.0,  w=640, h=320),
    "french_polynesia":  dict(lon=-149.0, lat=-17.5, w=640, h=320),
    "hawaii":            dict(lon=-156.0, lat=20.0,  w=640, h=320),
    "tibetan_plateau":   dict(lon=90.0,   lat=33.0,  w=640, h=320),
    "amazon":            dict(lon=-60.0,  lat=-3.0,  w=640, h=320),
    "pacific_islands":   dict(lon=170.0,  lat=10.0,  w=640, h=320),
    "europe_wide":       dict(lon=15.0,   lat=50.0,  w=640, h=320),
}
```

For each crop:
- Extract region from `noon_air_v1` array
- Extract same region from `d5z_b` baseline array
- Stack horizontally: `[baseline | noon_air_v1]`
- Save as `compare_crops/{region}_d5zb_vs_noon_air_v1.jpg`

Also save:
- `global_preview.jpg` — full downscaled image (max 1024px wide)
- `diff_heatmap.jpg` — absolute pixel difference heatmap (noon_air vs d5z_b), normalized and false-colored

### 5.16 Summary Report (`generate_metrics`)

Outputs `noon_air_v1_{res}_metrics.json`:

```json
{
  "version": "noon_air_v1",
  "resolution": "2048x1024",
  "timestamp": "...",
  "source": "earth_day_source_21600x10800.jpg",
  "global": {
    "mean_rgb": [R, G, B],
    "mean_luminance": 0.xxx,
    "vs_d5zb_mean_rgb_delta": [dR, dG, dB],
    "vs_d5zb_luminance_delta": 0.xxx
  },
  "protected_regions": {
    "japan":         {"mean_rgb": [...], "luminance": 0.xxx, "delta_vs_d5zb": {...}, "guard_pass": true},
    "mediterranean": {...},
    "caribbean":     {...},
    "pacific_islands": {...}
  },
  "benchmark_regions": {
    "maldives":    {"mean_rgb": [...], "luminance": 0.xxx},
    ...
  },
  "guard_result": {
    "pass": true,
    "warnings": []
  }
}
```

---

## 6. 2K Dry-run Stage Logic

The default run (`no --full-res flag`) executes:

```
1. validate_assets()
2. load_source(res=2048)             ← downscale 21.6K → 2K
3. load_baseline_d5zb(res=2048)
4. [all processing modules at 2K]
5. run_baseline_floor_guard()
6. generate_preview_crops()
7. generate_metrics()
8. save_outputs(res=2048)            ← saves 2K JPG only
```

Expected run time at 2K: < 60 seconds on standard hardware.
Expected output size: ~1–3MB JPG + ~50MB preview crops total.

The 2K dry-run exists to validate color decisions cheaply before committing to an 8K run (~10–20 minutes).

---

## 7. 8K Candidate Stage Logic

Only executed with explicit `--full-res` flag, after 2K dry-run has passed human review.

```
1. validate_assets()
2. load_source(res=8192)             ← downscale 21.6K → 8K
3. load_baseline_d5zb(res=8192)
4. [all processing modules at 8K]   ← same logic, higher resolution
5. run_baseline_floor_guard()
6. generate_preview_crops()
7. generate_metrics()
8. save_outputs(res=8192)            ← saves 8K JPG
```

Expected run time at 8K: 10–20 minutes depending on hardware.
Expected output size: ~7–9MB JPG candidate.

---

## 8. Processing Log Format

```
=== Noon Air Earth Generator v1 ===
Timestamp: 2026-xx-xx HH:MM:SS UTC
Mode: DRY-RUN (2048x1024)
Source: pwa/assets/source/earth_day_source_21600x10800.jpg (21600x10800)
Baseline: pwa/assets/earth/candidates/d5z_b_8192x4096.jpg

[SAFETY] Output path: d5b_processor_v3/d5b_output/noon_air_candidates/
[SAFETY] Production path assertion: PASS
[SAFETY] Candidates path assertion: PASS

[LOAD] Source loaded: 21600x10800
[LOAD] Downscaled to: 2048x1024 in 3.2s

[MODULE 1] global_base ... done (2.1s)
[MODULE 2] ocean_system ... 48 regions processed (8.3s)
[MODULE 3] shallow_water ... done (1.9s)
[MODULE 4] island_halos ... 23 halos processed (3.1s)
[MODULE 5] polar ... Antarctica done, Greenland done (4.2s)
[MODULE 6] desert ... Sahara done, Arabia done, Plateau done (2.8s)
[MODULE 7] land_vegetation ... done (2.4s)
[MODULE 8] mountain_plateau ... done (1.1s)
[MODULE 9] special_seas ... 6 regions done (1.8s)
[MODULE 10] atmosphere_overlay ... opacity=6.0% done (0.4s)

[GUARD] Protected region check:
  japan:           mean_rgb_delta=[1.2, -0.8, 2.1]  luminance_delta=0.008  PASS
  mediterranean:   mean_rgb_delta=[-0.3, 1.1, -1.4] luminance_delta=0.005  PASS
  caribbean:       mean_rgb_delta=[0.9, 1.7, -0.6]  luminance_delta=0.007  PASS
  pacific_islands: mean_rgb_delta=[1.1, 0.4, 2.3]   luminance_delta=0.009  PASS
  OVERALL: PASS

[OUTPUT] Saving noon_air_v1_2048x1024.jpg ... done (1.2s, 1.8MB)
[OUTPUT] Saving global preview ... done
[OUTPUT] Saving diff heatmap ... done
[OUTPUT] Saving 16 region compare crops ... done
[OUTPUT] Saving metrics.json ... done

=== COMPLETE ===
Total time: 34.6s
Output: d5b_processor_v3/d5b_output/noon_air_candidates/
```

---

## 9. Safety Boundary Summary

| Prohibition | Mechanism |
|---|---|
| Never overwrite source image | Source loaded read-only; OUT_DIR assertions exclude source path |
| Never write to production/ | Module-level `assert "production" not in str(OUT_DIR)` |
| Never write to candidates/ directly | `assert OUT_DIR != CAND_DIR` |
| Never modify `earth3d.js` | Script has no file-write operations outside OUT_DIR |
| Never modify `DAY_TEXTURE_VARIANT` | Script has no file-write operations outside OUT_DIR |
| Never auto-commit | No subprocess calls to git |
| Never auto-push | No subprocess calls to git |
| Default is 2K only | `--full-res` flag required for 8K |
| 8K requires explicit opt-in | Default behavior checked at start; clear warning if `--full-res` detected |

---

## 10. Files To Create (Phase B Execution — Not This Turn)

| File | Purpose |
|---|---|
| `d5b_processor_v3/d6_noon_air_earth_generator.py` | Main generator script |
| `d5b_processor_v3/d5b_output/noon_air_candidates/` | Output directory (auto-created by script) |
| `previews/noon_air_v1_2k/` | 2K dry-run preview crops (auto-created) |

---

## 11. Files Not To Touch

| File / Directory | Why |
|---|---|
| `pwa/earth3d.js` | No runtime changes until Three.js testing stage |
| `d5b_processor_v3/config.py` | D5b design config; Phase B uses standalone config inside new script |
| `d5b_processor_v3/d5z_generator.py` | Reference only; do not modify |
| `pwa/assets/source/` | Read-only |
| `pwa/assets/earth/production/` | Production-only |
| `pwa/assets/earth/candidates/` | Not touched until copy step is separately authorized |
| Any existing candidate JPG | No overwriting |

---

## 12. Open Questions for Review

Before creating the generator script, the following should be confirmed:

1. **Color param strategy:** Should NOON_AIR_OCEAN_REGIONS reuse the `rgb_offset` + `saturation_factor` approach from `config.py`, or adopt a different HSL-delta system? The existing approach is proven; deviating adds implementation risk.

2. **Ocean mask method:** `masks.py` uses pixel-color-based heuristic to detect ocean. For the standalone generator, should we reproduce that logic inline, or import `masks.py` directly? Importing reduces code duplication but couples the generator to the D5b module.

3. **Island halo radius units:** `config.py` uses `halo_radius_km`. The conversion to pixels depends on working resolution. The formula is `radius_px = halo_radius_km / (earth_circumference_km / image_width)`. This needs to be explicit in the generator.

4. **d5z_b baseline path:** The guard compares against `pwa/assets/earth/candidates/d5z_b_8192x4096.jpg`. If this file is absent (gitignored on a fresh clone), the guard should degrade gracefully rather than abort. Confirm preferred behavior: skip guard, warn, or use production copy.

5. **Feather implementation:** Previous scripts use Gaussian blur on the region mask. For Phase B, should we use the same approach, or switch to distance-field-based feathering (which gives more control near complex coastlines)?
