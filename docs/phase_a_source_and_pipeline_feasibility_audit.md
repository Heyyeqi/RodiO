# Phase A — Source and Pipeline Feasibility Audit

> Audit Date: 2026-06-09
> Status: Read-only assessment — no textures generated, no data downloaded, no runtime modified
> Auditor: Claude Code (Sonnet 4.6)
> Scope: Day Earth assets, pipeline scripts, data sources, Noon Air Earth compatibility

---

## 1. Executive Summary

**Verdict: Noon Air Earth candidate generation can begin from existing assets.**

The repository already contains:
- A 21.6K day source image (the master from which all D5-series candidates were generated)
- A mature, modular regional color-grading pipeline (`d5b_processor_v3`) with 98 named zones
- Full global ETOPO1 bathymetry (890MB)
- GSHHG full-resolution global coastline shapefiles
- GEBCO 2026 Japan-region bathymetry (partial, not global)
- 11 candidate textures + 1 production texture at 8K

**No new data download is required to begin the first Noon Air Earth candidate pass.**

The core work is: translate Noon Air Earth color targets from `rodio_day_earth_target_color_spec_and_benchmark_matrix.md` into updated `OCEAN_REGIONS` and `ISLAND_HALOS` parameters in a new grading configuration. The existing pipeline infrastructure can execute this directly.

**One gap:** Global GEBCO is not present — ETOPO1 (full global) is available as a substitute. If higher-precision shallow-water bathymetry is needed beyond Japan, a global GEBCO download will eventually be required, but not for the first candidate pass.

---

## 2. Current Runtime Day Texture State

**`DAY_TEXTURE_VARIANT`:** `'d5z_b'` (line 6, `pwa/earth3d.js`)

**`getDayTexturePaths()` — all defined variants:**

| Variant Key | Path | Role |
|---|---|---|
| `current` | *(implicit fallback)* | Legacy default |
| `bmng_b` | `candidates/bmng_b_8192x4096.jpg` | Early BMNG candidate |
| `bmng_c` | `candidates/bmng_c_8192x4096.jpg` | BMNG variant C |
| `bmng_d2` | `candidates/bmng_d2_8192x4096.jpg` | BMNG variant D2 |
| `d5a_bathy` | `candidates/d5a_bathy_8192x4096.jpg` | D5 + ETOPO1 bathymetry |
| `d5b_bathy` | `candidates/d5b_bathy_8192x4096.jpg` | D5b + bathymetry |
| `d5c_palette_v6_1_bathy` | `candidates/d5c_palette_v6_1_bathy_8192x4096.jpg` | D5c palette v6.1 |
| `d6_topo_blend` | `candidates/d6_topo_blend_8192x4096.jpg` | D6 topo blend experiment |
| `d5b_design_v3_1` | `candidates/d5b_design_v3_1_8192x4096.jpg` | D5b design v3.1 |
| `d5b_design_v3_2_1` | `candidates/d5b_design_v3_2_1_8192x4096.jpg` | D5b design v3.2.1 (E1 baseline) |
| `d5z_a` | `candidates/d5z_a_8192x4096.jpg` | D5z conservative pass |
| **`d5z_b`** | **`production/d5z_b_8192x4096.jpg`** | **PRODUCTION — current default** |

**URL override:** `?dayTexture=<variant>` in the browser URL switches variants for local testing without modifying `DAY_TEXTURE_VARIANT`. Does not affect production environment.

**Loading logic:** Primary path attempted first; falls back to `/assets/bluemarble.jpg` (low-res fallback) if primary 404s.

---

## 3. Texture Asset Inventory

### 3.1 Production

| File | Size | Resolution | Role |
|---|---:|---:|---|
| `pwa/assets/earth/production/d5z_b_8192x4096.jpg` | 7.6MB | 8192×4096 | **Current production Day Texture** |

### 3.2 Candidates (`pwa/assets/earth/candidates/`) — gitignored

| File | Size | Notes |
|---|---:|---|
| `bmng_b_8192x4096.jpg` | 7.0MB | BMNG variant B (early exploration) |
| `bmng_c_8192x4096.jpg` | 7.3MB | BMNG variant C |
| `bmng_d2_8192x4096.jpg` | 7.5MB | BMNG variant D2 (pre-D5 era) |
| `d5a_bathy_8192x4096.jpg` | 9.3MB | D5a + ETOPO1 bathy composited |
| `d5b_bathy_8192x4096.jpg` | 9.3MB | D5b + bathy |
| `d5c_palette_v6_1_bathy_8192x4096.jpg` | 9.3MB | D5c palette v6.1 + bathy |
| `d6_topo_blend_8192x4096.jpg` | 9.4MB | D6 topo blend experiment |
| `d5b_design_v3_1_8192x4096.jpg` | 8.0MB | D5b v3.1 (formal 8K, RDL era) |
| `d5b_design_v3_2_1_8192x4096.jpg` | 8.0MB | D5b v3.2.1 (E1 baseline input) |
| `d5z_a_8192x4096.jpg` | 7.6MB | D5z conservative (polar+deep ocean) |
| `d5z_b_8192x4096.jpg` | 7.6MB | D5z balanced (same as production) |

### 3.3 Root-level Assets (`pwa/assets/`)

| File | Size | Role |
|---|---:|---|
| `earth_day_8k.jpg` | 4.6MB | Legacy day texture (pre-D5) |
| `earth_night_8k.jpg` | 3.5MB | Current night texture |
| `earth_night_8k_preview_color_grade.jpg` | 3.5MB | Night texture preview |
| `bluemarble.jpg` | 504KB | Low-res fallback (504KB, ~2K) |
| `blackmarble.jpg` | 776KB | Legacy |
| `earth_city_lights_alpha_preview_v2.png` | 11MB | City lights alpha |
| `earth_city_lights_alpha_preview_v3.png` | 4.9MB | City lights alpha v3 |

### 3.4 Source / Mother Images (`pwa/assets/source/`) — gitignored

| File | Size | Resolution | Role |
|---|---:|---:|---|
| `earth_day_source_21600x10800.jpg` | 20MB | 21600×10800 | **Master day source — input for all D5 series** |
| `earth_night_source_13500x6750.jpg` | 7.7MB | 13500×6750 | Night source |
| `earth_night_8k_before_color_match.jpg` | 3.0MB | 8K | Night processing intermediate |
| `earth_night_8k_before_color_grade_apply.jpg` | 3.0MB | 8K | Night processing intermediate |

### 3.5 Other Assets

| File | Size | Role |
|---|---:|---|
| `pwa/assets/earth/masks/ocean_mask_4096x2048_soft.png` | — | Ocean/land mask for compositing |
| `pwa/assets/earth/masks/ocean_mask_soft_preview.png` | — | Mask preview |
| `pwa/assets/earth/clouds/cloud_alpha_2048x1024_refined.png` | — | Cloud layer |
| `pwa/assets/earth/clouds/cloud_alpha_4096x2048_refined.png` | — | Cloud layer 4K |

---

## 4. Source / Mother Image Assessment

**Current working source:** `pwa/assets/source/earth_day_source_21600x10800.jpg` (20MB, 21.6K × 10.8K)

This is the master image from which all D5-series candidates were generated. It is a NASA-derived Blue Marble composite already at 21.6K resolution — the same effective source resolution as BMNG monthly composites (NASA distributes BMNG at 21600×10800). Every D5b and D5z candidate was produced by downscaling this to 8K and applying regional color grading.

**Key implication:** The "BMNG upgrade" described in `global_color_grading_bmng_rdl_phase_plan.md` does not necessarily require downloading fresh BMNG data. The existing 21.6K source is already BMNG-derived. The question is whether a different BMNG monthly variant (different season, different vegetation state) would be a better starting point for Noon Air Earth aesthetics.

**Assessment:**
- For the first Noon Air Earth candidate: use the existing 21.6K source — no download needed.
- For future refinement: evaluate whether a different BMNG month (e.g. October vs. current) produces better base coloring. This is a Phase A conclusion to document, not an immediate action.

---

## 5. Existing Script and Pipeline Inventory

### 5.1 Core Pipeline — `d5b_processor_v3/`

| Script | Purpose | Input | Output | Reusable for Noon Air Earth | Risk |
|---|---|---|---|---|---|
| `main.py` | Full regional ocean color grading pipeline | Any JPG (21.6K or 8K) | Color-graded 8K JPG | ✅ High — architecture directly suits Noon Air Earth | Low — well-tested, modular |
| `config.py` | 98 named region definitions (OCEAN_REGIONS + ISLAND_HALOS + METRICS_BOUNDS) | — | Imported by main.py | ✅ High — params to be updated per Noon Air Earth spec | Low — adding/editing region entries is safe |
| `adjustments.py` | Per-region HSL/RGB apply logic | Region masks + numpy array | Modified image array | ✅ High — logic is generic | Low |
| `masks.py` | Ocean mask, conservative water mask, deep ocean mask, island halo mask | Input image | Binary masks | ✅ High | Low |
| `enhancement.py` | Full enhancement (global brightness, contrast, saturation) | Image array | Modified array | ✅ Medium — global params need Noon Air Earth tuning | Low |
| `metrics.py` | Regional metrics: mean RGB, luminance delta, PSNR, diff | Two images + region bounds | JSON metrics | ✅ High — needed for acceptance | Low |
| `preview.py` | Saves compare crops, global previews, heatmaps | Image arrays | JPG previews | ✅ High | Low |
| `d5z_generator.py` | Standalone correction pass (polar + deep ocean + desert) | `d5b_design_v3_2_1` candidate | D5z_a, D5z_b to `d5b_output/d5z_candidates/` | ✅ Medium — arch reusable; params need update | Low — safety assertions built in |
| `formal_8k_v3_2_1.py` | Formal 8K run script for v3.2.1 | 21.6K source | 8K formal output | ✅ Medium — template for new formal run | Low |
| `make_small.py` | Resize to 2K for dry-run | Any | Small preview | ✅ High — useful for dry-run iteration | Low |

### 5.2 Generation Scripts — `scripts/`

| Script | Purpose | Reusable |
|---|---|---|
| `generate_d5a_bathy.py` | D5a + ETOPO1 bathy blend | ✅ Arch reference for bathy compositing |
| `generate_d5b_bathy.py` | D5b + ETOPO1 bathy | ✅ Same |
| `generate_d5c_palette_v6_1.py` | D5c palette v6.1 | ⚠️ Specific to D5c palette — review params |
| `generate_d6_topo_blend.py` | D6 topo blend | ✅ Topo blend approach reusable |
| `generate_d5y_regional_ocean_bathy.py` | Japan-region GEBCO/GSHHG bathy | ⚠️ Japan-only by default |
| `earth_night_color_grade_preview.py` | Night texture preview | ❌ Night-only |
| `generate_ocean_specular_mask.py` | Ocean specular mask | ⚠️ Speculative use |
| `validate_etopo1_bathy.py` | ETOPO1 validation | ✅ Useful for verifying ETOPO1 data |

### 5.3 Geo Pipeline Scripts — `scripts/geo/`

| Script | Purpose | Input | Output | Reusable | Notes |
|---|---|---|---|---|---|
| `gebco_bathymetry_tint.py` | GEBCO depth → 5-level color tint layer | GEBCO `.nc` + bounds | PNG tint layer | ✅ High — parametric bounds | Japan defaults; works globally with `--bounds` flag |
| `gshhg_coastline_render.py` | GSHHG → land mask + distance field | GSHHG L1 shapefile + bounds | `gshhg_coastline_mask.png`, `gshhg_distance_field.png` | ✅ High — key for island precision | Japan defaults; crop spec in KEY_CROPS needs update for global use |
| `rdl_retuning.py` | RDL visual retuning: GEBCO + GSHHG → natural globe compositing | GEBCO NC + GSHHG mask (from prior run) | Regional composite to `previews/` | ✅ Medium — needs regionalization | Japan-only; requires cached layer outputs from prior run |
| `rdl_tile_compositor.py` | Tiles compositor | Regional layers | Composite tile | ✅ Medium | Japan-only |
| `rdl_composite_preview.py` | Preview composite | Layers | Preview JPG | ✅ Medium | Japan-only |
| `lon_lat_to_uv.js` | Lon/lat → UV texture coordinate utility | lon, lat | u, v | ✅ High — coordinate math utility | Generic |

---

## 6. Existing Data Source Assessment

| Source | Status | Location | Size | Coverage | Quality Assessment |
|---|---|---|---|---|---|
| **Day source (BMNG-derived)** | ✅ Present | `pwa/assets/source/earth_day_source_21600x10800.jpg` | 20MB | Global | 21.6K; working master for all D5 series |
| **ETOPO1 bathymetry** | ✅ Present | `pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd` | 890MB | Global | 1 arc-minute resolution; suitable for depth-driven ocean grading |
| **ETOPO1 (compressed)** | ✅ Present | `pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd.gz` | 377MB | Global | Same as above, archived |
| **GEBCO 2026** | ⚠️ Partial | `pwa/assets/source/bathy/gebco_2026/gebco_2026_118_150_22_50.nc` | 46MB | Japan/East Asia only (118–150°E, 22–50°N) | 15 arc-second; higher precision than ETOPO1 for Japan |
| **GSHHG coastline** | ✅ Present | `pwa/assets/source/coastline/gshhg/` | ~750MB total | Global | Full resolution (f-level) + high (h-level) + intermediate (i-level) + low (l-level) |
| **GSHHG (archived)** | ✅ Present | `gshhg/gshhg-shp-2.3.7.zip` | 142MB | Global | Archive |
| **DEM (terrain elevation)** | ❌ Not present | — | — | — | ETOPO1 includes elevation data; dedicated DEM not downloaded |
| **BMNG monthly raw** | ❌ Not present | — | — | — | 21.6K source is already a BMNG derivative |
| **OSM** | ❌ Not present | — | — | — | Out of scope Phase A |
| **VIIRS night lights** | ❌ Not present | — | — | — | Out of scope Phase A |
| **RDL prototype (Japan)** | ⚠️ Partial | `previews/rdl_v2_*` (untracked) | — | Japan only | Regional detail layer exists as preview output only; not a reusable compositable layer yet |

---

## 7. Noon Air Earth Compatibility Matrix

Based on `docs/rodio_day_earth_target_color_spec_and_benchmark_matrix.md`.

| Target | Existing Support | Gap | Suggested Next Step |
|---|---|---|---|
| **Deep ocean clarity** (#03243F–#126B92) | ✅ Strong — `config.py` `global_deep_ocean_base` + per-basin region passes already control deep ocean HSL | Param values don't match Noon Air Earth targets yet | Update `global_deep_ocean_base` + major basin configs in config.py |
| **Shallow water hierarchy** (deep→shelf→nearshore) | ✅ Strong — `OCEAN_REGIONS` has Bohai, Yellow Sea, East China Sea, South China Sea, Persian Gulf, Red Sea, Mediterranean, Caribbean, etc. | Color targets differ from Noon Air Earth spec | Translate Noon Air Earth §5.2 HEX targets into config.py rgb_offset + saturation params |
| **Island / reef visibility** | ✅ Strong — `ISLAND_HALOS` has 25+ islands: Hawaii, Maldives, Seychelles, Lesser Antilles, Bermuda, Azores, Canary, Falkland, Aleutian; Caribbean deep-gate logic | Missing: Fiji, Tonga, Samoa, French Polynesia in ISLAND_HALOS (present in METRICS_BOUNDS only); Bahamas not in ISLAND_HALOS | Add missing island halos; tune halo params to Noon Air Earth §6 |
| **Polar brightness and texture** | ✅ Present — `d5z_generator.py` has Antarctica + Greenland polar compress; E1 protection guardrails exist | d5z_generator targets are conservative (d5z_b pass); Noon Air Earth has more specific tonal targets | New polar pass targeting §7 color tables: #DDECF2 main, #9CB8C8 shadow, transition to #63AFC8 coast |
| **Desert warmth and highlight control** | ✅ Present — `d5z_generator.py` D5z_b has Sahara/Arabia darken correction B | Applied on top of d5b_design_v3_2_1; may need rebase on fresh Noon Air Earth pass | New desert pass targeting §9.1: #C49B6F main, #D8BC91 max, suppress highlights |
| **Land atmosphere / low saturation** | ✅ Medium — `full_enhance()` in `enhancement.py` applies global saturation reduction | No per-region land tuning for forests/grasslands; Noon Air Earth has specific biome targets | New land section in config.py: temperate/tropical/savanna per §8 |
| **Coastline / island precision** | ⚠️ Partial — GSHHG data present + `gshhg_coastline_render.py` exists | Scripts are Japan-region defaults; not yet run globally | Extend `gshhg_coastline_render.py` to global run; output distance field for compositing |
| **Global color harmony** | ✅ Medium — `metrics.py` has protected-region diff checking; d5z_generator has Color Harmony Guard | Guard only applied in d5z pass; Noon Air Earth needs full 12-region coverage | Extend metrics to all 12 benchmark regions; run guard at end of full pass |
| **Three.js on-globe validation** | ✅ Strong — puppeteer screenshot pipeline used in E1-R5; `?dayTexture=` URL override works | No automation script yet for Noon Air Earth 12-region × 4 time-mode matrix | Copy E1-R5 approach; extend to 12 benchmark regions |

---

## 8. Gaps and Blockers

### Blockers (must resolve before production promotion)

None that block starting candidate generation. The following are required before final acceptance:

1. **Three.js on-globe acceptance:** Same protocol as E1-R5, extended to 12 benchmark regions. Not a blocker for candidate generation, but required for promotion.
2. **d5z_b baseline floor verification:** Any Noon Air Earth candidate must pass all 6 E1 guardrail dimensions before promotion.

### Gaps (not blocking candidate generation, but track)

| Gap | Severity | Notes |
|---|---|---|
| Global GEBCO not present | Medium | ETOPO1 (full global) is an adequate substitute for first pass. Global GEBCO (15 arc-sec) would improve shallow-water precision. Download decision is Phase B/C. |
| ISLAND_HALOS missing Fiji, Tonga, Samoa, French Polynesia, Palau, Solomon, Vanuatu | Low | Can add entries to config.py (no data download needed). Required for Noon Air Earth §6 |
| GSHHG rendering scripts Japan-only by default | Low | The data is present; scripts need `--bounds` parameter extension for global output |
| d5b_processor_v3 ocean color params not yet Noon Air Earth tuned | — | This is the Phase B work, not a gap |
| RDL prototype (Japan) not compositable globally | Low | Japan-only preview outputs. Global RDL is Phase D work |
| No BMNG monthly variant comparison | Low | The 21.6K source is a processed BMNG derivative. Phase A should confirm if a different month is needed before Phase B begins |

---

## 9. Recommended Next Step

**Phase A closes with this verdict: existing assets are sufficient to begin candidate generation.**

**Recommended Phase B entry point:**

1. **Create `d6_noon_air_earth_generator.py`** — modeled on `d5z_generator.py` — as a standalone correction pass on the existing `d5b_design_v3_2_1` baseline (or directly from the 21.6K source via `main.py`).
   - Recommended base input: **21.6K source → fresh 8K downscale** (not stacked on d5z_b). The Noon Air Earth color system is a full-spectrum rethink, not a patch on d5z_b.
   - Alternative: **d5b_design_v3_2_1 as input** if starting from scratch is judged too risky.

2. **Update `config.py`** — translate Noon Air Earth §4–§11 HEX targets into updated OCEAN_REGIONS rgb_offset / saturation_factor / brightness_factor parameters. Add missing ISLAND_HALOS entries.

3. **Dry-run at 2K first** using `make_small.py` → human visual check against Noon Air Earth spec → iterate → formal 8K run.

4. **Add 12-region benchmark crops** to `metrics.py` / `preview.py` aligned with `rodio_day_earth_target_color_spec_and_benchmark_matrix.md`.

**Do not authorize this yet** — this is the Phase A recommendation. Await explicit authorization before entering Phase B.

---

## 10. Strict Non-Execution Confirmation

The following was confirmed throughout this audit:

| Prohibition | Status |
|---|---|
| BMNG / GEBCO / GSHHG / DEM / OSM / VIIRS downloaded | ✅ Not executed |
| New texture generated | ✅ Not executed |
| Image or preview generated | ✅ Not executed |
| Python image-processing scripts run | ✅ Not executed |
| `pwa/earth3d.js` modified | ✅ Not modified |
| `DAY_TEXTURE_VARIANT` modified | ✅ Not modified (`'d5z_b'` unchanged) |
| Production texture modified or copied | ✅ Not modified |
| Candidates directory modified | ✅ Not modified |
| commit executed | ✅ Not executed |
| push executed | ✅ Not executed |

This document is a read-only assessment. All findings are based on file system inspection and static code reading only.
