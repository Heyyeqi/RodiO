# Phase B-5.3a — Codex Noon Air Generator Deep Architecture Audit

> Created: 2026-06-10
> Auditor: Codex, independent static architecture review
> Subject: `d5b_processor_v3/d6_noon_air_earth_generator.py`
> Scope: static analysis only; no generator execution; no image generation; no runtime/texture/production changes

## Executive Conclusion

The current generator's root problem is not one missing local tweak. It is a mismatch between the visual target and the available structure model.

The script is trying to derive a global Noon Air texture from a 21.6K source using only RGB/luminance classifiers, hand-coded geographic boxes, and hand-coded island centers. That is insufficient for stable global reef, shelf, coastline, and narrow-sea behavior. B-5.1 and B-5.2 correctly removed two severe engineering failure modes: image-mutating final guard and large tropical bbox floors. However, the remaining pipeline still cannot reliably distinguish deep ocean, shallow shelf, reef lagoon, turbid coast, dark land, and narrow water bodies without better masks.

B-5.3 is partially aimed at the symptoms that remain: island/reef under-visibility, weak shallow shelf recovery, and special-sea color failures. It is directionally relevant, but it is not a root-cause fix. It replaces one class of geographic patch (large rectangles) with another class of geographic patch (circles and more bboxes). That may be acceptable as a temporary calibration experiment only if split into small, measured stages with new metrics. It should not be implemented as one combined B-5.3 change.

Final recommendation: continue the current source-derived route only conditionally. First commit documentation and safety semantics, then implement at most B-5.3.1 island/reef-only as a calibration experiment with per-module and reef-zone metrics. Defer shelf-region expansion and special-sea aggressive changes until the metrics can isolate water-only effects. Begin planning a data-mask route using bathymetry/coastline/reef proxies for Phase C or for a Route C dual-source blend.

## Evidence Read

Primary files reviewed:

- `d5b_processor_v3/d6_noon_air_earth_generator.py`
- `docs/phase_b4_noon_air_calibration_failure_root_cause_audit.md`
- `docs/phase_b5_noon_air_generator_safety_semantics_rewrite_plan.md`
- `docs/phase_b5_3_noon_air_island_reef_shelf_recovery_plan.md`
- `docs/rodio_day_earth_target_color_spec_and_benchmark_matrix.md`
- `docs/phase_b_noon_air_candidate_generation_plan.md`
- `docs/phase_a_source_and_pipeline_feasibility_audit.md`
- Existing calibration log and metrics under `d5b_processor_v3/d5b_output/noon_air_candidates/calibration/`

Note: `RodiO_Noon_Air_Earth_地图配色工程执行方案_v1_1.md` was not found at the repo root or through filename search. This audit used the existing Noon Air spec and Phase B documents as the nearest available authority.

Working tree observation:

- `d5b_processor_v3/d6_noon_air_earth_generator.py` is tracked modified with B-5.1/B-5.2 style changes.
- `docs/phase_b5_3_noon_air_island_reef_shelf_recovery_plan.md` is untracked.
- This audit treats both as current local state, not as committed or validated truth.

## Root Questions

### 1. Current Generator Root Problem

Primary root problem:

The generator lacks stable semantic masks for the most important visual distinctions in Noon Air Earth: reef vs shelf vs deep ocean vs turbid coast vs land vs ice. It compensates with RGB/luminance proxies plus hand-coded geography. That combination is fragile because the source image's color already contains aesthetic and seasonal artifacts, so color-derived masks are not independent from the pixels being edited.

Secondary root problems:

- The route is source-derived, but important safety and comparison semantics remain d5z_b-relative.
- Several modules recompute classifiers from the current mutable `out`, creating feedback potential.
- Most modules share a single `NOON_AIR_INTENSITY=0.38`, even though global grading, reef floors, shelf lift, special seas, and atmosphere need different intensity semantics.
- Metrics are crop means and protected-region deltas, not structure-aware water metrics.
- 2K calibration cannot represent sub-pixel reef chains, narrow seas, or 8K/21.6K coastline structure.
- There is no per-module delta accounting, so fixes cannot be attributed or bounded.

### 2. Is B-5.3 Aimed at Root Cause?

Partly, but not fully.

B-5.3 correctly notices that island halos are too weak, shallow shelf gates are too high, and special seas need water-specific treatment. It also correctly avoids restoring the large tropical bbox floor that caused B-5.1 patches.

However, B-5.3 does not solve the underlying mask problem. Circle masks around island centers are not reef geometry. A linear island chain like Maldives, a broad shallow platform like Bahamas, and a dispersed archipelago like French Polynesia cannot all be represented safely by circular floors. The plan can improve review crops, but it may introduce new visible circle artifacts or over-brightened local bubbles at 8K.

### 3. Is The Current Script Still Worth Fixing?

Conditional yes.

It is worth continuing only as a controlled calibration prototype and only if changes are split and instrumented. It is not yet a production-grade global texture generator. Its filesystem safety and calibration gating are good enough to continue 2K experiments. Its mask and metrics system are not good enough for promotion decisions.

### 4. Is There A Lower-Level Route Error?

There may be.

The source-derived route is conceptually valid for a full-spectrum aesthetic rethink, as Phase B intended. But the current script is not actually a full source-derived reconstruction system; it is a stack of color heuristics. For ocean/shallow/reef quality, d5z_b may contain better preserved shallow-water structure than the current source-derived output. A dual-source or d5z_b-ocean reference route may be more stable until real bathymetry/coast/reef masks exist.

## Complete Pipeline Dataflow

### Mode Branches

| Mode | Resolution Path | Guard Behavior | Writes Full JPG? | Writes Metrics/Crops? | Production/Candidates? |
|---|---|---|---|---|---|
| default | 2K only | baseline floor guard aborts on fail before normal output completion | yes only if guard passes | yes only after guard passes | no |
| `--calibration` | 2K only | guard fail warns but continues; output marked calibration only | yes unless `--preview-only` | yes | no |
| `--full-res` | 2K then 8K | guard fail aborts per resolution | yes if guard passes | yes if guard passes | no |
| `--preview-only` | selected mode's resolution(s) | same guard behavior | no full candidate JPG | yes | no |
| `--dry-run` | no processing | no image pipeline | no | log only | no |

`--calibration` and `--full-res` are mutually exclusive.

### Inputs And Outputs

| Asset | Path | Role |
|---|---|---|
| source | `pwa/assets/source/earth_day_source_21600x10800.jpg` | primary image input; resized to 2K or 8K |
| baseline | `pwa/assets/earth/candidates/d5z_b_8192x4096.jpg` by default | comparison baseline and guard reference; resized to current resolution |
| output dir | `d5b_processor_v3/d5b_output/noon_air_candidates/` | non-production output |
| calibration output dir | `d5b_processor_v3/d5b_output/noon_air_candidates/calibration/` | calibration-only outputs |
| crops | `<out_dir>/compare_crops/` | benchmark side-by-side crops |
| metrics | `<out_dir>/<prefix>_<res>_metrics.json` | summary metrics |
| safety json | calibration mode only | calibration warning metadata |
| log | `<out_dir>/<prefix>_log.txt` or guard fail log | processing log |

### Main Dataflow Table

| Step | Function | Input Array | Output Array | Mutates Pixels? | Mask Used | Risk |
|---|---|---|---|---|---|---|
| 0 | `validate_assets` | paths only | none | no | none | hard dependency on d5z_b even for source-derived route |
| 1 | `load_source` | source JPG | `source_arr` uint8 | no source mutation | none | PIL resize changes 21.6K signal for 2K calibration |
| 2 | `load_baseline_d5zb` | d5z_b JPG | `baseline_arr` uint8 | no | none | baseline resized by PIL; used for guard, not generation |
| 3 | `build_grids` | `h,w` | `LAT,LON` | no | global lat/lon grid | longitude endpoints include both -180 and 180; edge behavior is approximate |
| 4 | cast | `source_arr` | `f32` | no | none | source-derived route begins |
| 5 | cast | `baseline_arr` | `base_f32` | no | none | baseline kept separate |
| 6 | `apply_global_base_adjustment` | `f32` | new `out` assigned to `f32` | yes, returned copy | global HSL gates | applies global pass before regional work, while spec describes it as final-stage tuning |
| 7 | `apply_ocean_system` | current `f32` | new `out` | yes | `region_mask_rect`, `deep_ocean_px(f32)`, `ocean_px(out)` | fixed deep mask helps, but non-deep ocean gate still uses current `out` |
| 8 | `apply_ocean_luminance_floor` | current `f32` | new `out` | yes | `ocean_px(out)`, luminance shallow proxy | floor preserves hue by scaling RGB, but can create low-contrast dark blue/grey fields |
| 9 | `apply_shallow_water_shelf` | current `f32` | new `out` | yes | `ocean_px(out)`, luminance threshold | threshold 0.18 excludes dark reef/shelf zones |
| 10 | `apply_island_halos` | current `f32` | new `out` | yes | `circle_mask`, `deep_ocean_px(out)`, `ocean_px(out)` | deep gate can suppress reefs; circle geometry is not reef geometry |
| 11 | `apply_polar_correction` | current `f32` | new `out` | yes | `ice_px(out)`, latitude masks | global latitude masks acceptable but can touch high-lat water/ice ambiguity |
| 12 | `apply_desert_correction` | current `f32` | new `out` | yes | `land_px(out)`, `region_mask_rect`, brightness | Sahara/Arabia formula still appears algebraically wrong: can brighten instead of darken |
| 13 | `apply_land_vegetation` | current `f32` | new `out` | yes | `land_px(out)`, bbox vegetation masks | land classifier derived after ocean edits may misclassify dark water/land edges |
| 14 | `apply_mountains_plateaus` | current `f32` | new `out` | yes | `land_px(out)`, bbox masks | low risk but bbox-driven |
| 15 | `apply_special_seas` | current `f32` | new `out` | yes | `ocean_px(out)`, `region_mask_rect` | narrow seas and bbox masks can miss water or create soft rectangular influence |
| 16 | `compute_protected_region_diagnostics` | current `f32`, `base_f32` | diagnostics dict | no | feathered protected rects | diagnostic-only; still d5z_b-relative |
| 17 | `evaluate_calibration_safety` | diagnostics | safety dict | no | none | threshold `mean_lum < 0.05` is too weak; current near-black regions pass as safe |
| 18 | `apply_atmosphere_overlay` | current `f32` | new `out` | yes | none | final global pass can lower local contrast after reef/shelf edits |
| 19 | `run_baseline_floor_guard` | final `f32`, `base_f32` | guard dict | no | hard protected rects, feather 0 | diagnostic-only but hard masks differ from Module 10 diagnostics |
| 20 | `generate_preview_crops` | `noon_arr`, `baseline_arr` | JPG files | no array mutation | crop boxes | crop mean/visual can be dominated by land/deep ocean |
| 21 | `write_summary_report` | final arrays, guard dict | metrics JSON | no image mutation | benchmark crops | metrics too coarse |
| 22 | `write_calibration_warning_metadata` | diagnostics | safety JSON | no | none | good safety sidecar |
| 23 | save candidate JPG | `noon_arr` | JPG file | no array mutation | none | JPEG quality 92/subsampling 0 reasonable; still lossy |

### Special Dataflow Findings

- `baseline_f32` is not used for pixel generation in current `main()`. It is used for diagnostics, guard, preview, and metrics.
- `apply_final_harmony_guard` still exists as a compatibility wrapper. It returns `f32.copy()` after diagnostics and is not called by `main()`.
- No current function is pretending to be diagnostic while modifying pixels, except the historical name `apply_final_harmony_guard` could mislead future callers. Its current implementation is non-mutating.
- Many modules return a copy rather than mutating the input array in place. `main()` reassigns `f32` after each module, so returned arrays are used.
- Classifier feedback remains present:
  - `apply_ocean_system` fixed `deep_mask_fixed` for `deep_only`, but `ocean_px(out)` is still computed from current mutated pixels for `ocean_only`.
  - `apply_island_halos`, `apply_desert_correction`, `apply_land_vegetation`, `apply_mountains_plateaus`, and `apply_special_seas` all compute masks from current `out`.
- Atmosphere overlay runs after island/shelf/special-sea modules and can reduce local contrast, though its opacity is only `0.06 * 0.38 = 2.28%`.

## Module Responsibility Boundary Audit

### A. Image Generation Modules

| Module | Design Responsibility | Actual Modification | Dependencies | Scope Fit | Boundary/Override Risk | Spec Fit |
|---|---|---|---|---|---|---|
| global base adjustment | soften contrast, reduce saturation, blue shift | multiplicative brightness, contrast around midpoint, blue boost, HSL desat | HSL hue gates from current pixels | global | applied before regional work, not final-stage as spec suggests | mostly aligned, order questionable |
| ocean system | basin-level ocean tone | HSL deltas inside ocean/region masks | `deep_ocean_px`, `ocean_px`, bbox masks | regional/global | fixed deep mask but mutable ocean mask; bbox seams possible | partially aligned |
| ocean luminance floor | near-black rescue | scales RGB where luminance below floors | `ocean_px`, lum proxy | global pixel-level | can lift deep ocean without structure; may grey/flatten if overused | safety aligned, not enough for reef hierarchy |
| shallow shelf | brighten visible shelf | multiplicative gain + HSL cyan shift for lum > 0.18 | `ocean_px`, luminance | should be structural/local | threshold excludes dark shelf/reef; no bathymetry | weak alignment |
| island halos | island/reef local glow | HSL shift in circular masks | `circle_mask`, `deep_ocean_px`, `ocean_px` | local | deep gate can remove target pixels; circles are not reef shapes | concept aligned, effect too weak |
| polar correction | preserve blue-white ice | brightness compression + HSL ice shift | `ice_px`, latitude | regional/global | latitude-only masks are coarse | broadly aligned |
| desert correction | reduce desert overexposure/warmth | intended darken plus HSL shifts | `land_px`, desert bbox, luminance | regional | Sahara/Arabia formula likely doubles contribution and can brighten | risky |
| land vegetation | low-saturation land | global land green desat and rainforest HSL darken | `land_px`, bbox masks | global/regional | land mask can include non-ocean dark pixels; bbox feather still coarse | aligned but coarse |
| mountains/plateaus | cool/suppress selected ranges | small HSL deltas | `land_px`, bbox masks | regional | low strength; bbox coarse | acceptable |
| special seas | correct named sea character | HSL deltas in sea bboxes gated by ocean | `ocean_px`, bbox masks | regional | narrow water bodies poorly represented; bbox can affect wrong water/edges | partially aligned |
| atmosphere overlay | final unifying air | soft-light RGB overlay | none | global final | may reduce local reef/shelf contrast | aligned if very restrained |

Boundary concerns:

- Ocean, shelf, island, and special sea modules all edit the same water pixels without explicit ownership or exclusion masks.
- Later modules can overwrite or dilute earlier modules because all operate on final RGB without per-module masks preserved.
- There is no "protected reef/shelf mask" after final atmosphere.
- Global base adjustment is a broad aesthetic operation but executes before local recovery, contrary to the spec's "final-stage tuning" language.

### B. Safety / Guard Modules

| Module | Diagnostic Only? | Image Mutation? | Can Abort? | Source-Derived Fit | Hidden d5z_b Assumption |
|---|---:|---:|---:|---|---|
| `validate_assets` | yes | no | yes, if source/baseline missing | mixed | requires d5z_b even for source-derived calibration |
| `compute_protected_region_diagnostics` | yes | no | no | useful as reference | thresholds assume d5z_b-small-delta route |
| `evaluate_calibration_safety` | yes | no | no | weak | near-black threshold allows bad outputs |
| `write_calibration_warning_metadata` | yes | no | no | good | none beyond diagnostics |
| `apply_final_harmony_guard` wrapper | yes | no | no | okay but misleading name | still named as if a guard pass |
| `run_baseline_floor_guard` | yes | no | yes outside calibration | questionable for source-derived route | hard d5z_b delta threshold |

Safety conclusion:

The former image-mutating final guard has been removed from `main()`. That is a valid safety improvement. But the guard philosophy still carries a d5z_b patch-route assumption: `mean_rgb_delta <= 8` and `lum_delta <= 0.04` are unrealistic for a source-derived aesthetic route whose global mean RGB is currently far from baseline. This guard is suitable as a "do not promote" warning, not as a calibration success metric.

### C. Metrics / Preview Modules

Current metrics are insufficient for decisions.

- Region crop `mean_lum` is misleading for Maldives/French Polynesia because a 2K crop is mostly deep ocean, while the actual target is sub-pixel or few-pixel reef visibility.
- Red Sea crop is dominated by adjacent desert, so whole-crop lum hides water failure.
- Yellow/East China needs channel-ratio and hue metrics (`B_over_G`, `B_minus_G`), not only luminance.
- Protected-region deltas vs d5z_b will fail by design in a source-derived route.
- No metric reports affected pixel count per module.
- No metric reports patch artifacts, circular artifacts, or per-zone delta maps.

### D. Output / Filesystem Modules

Output safety is good.

- Module-level assertions prevent `OUT_DIR` from being production or candidates.
- `ensure_safe_output_path` repeats production/candidates checks.
- The script does not modify `pwa/earth3d.js`, production textures, candidates, or git.
- Hidden side effects are limited to writing output/log/metrics under output dirs when run. This audit did not run it.

Risk:

- `--output-dir` can still be user-provided. It is checked against production and candidates but not against every possible sensitive repo path. That is acceptable for current use but not a full sandbox.

## Mask / Classifier Deep Audit

| Mask | Input | Output Type | Hard/Soft | Resolution Adaptive? | Uses Current Out? | Used By | Failure Risk |
|---|---|---|---|---:|---:|---|---|
| `ocean_px` | RGB | float binary | hard | yes by image size only | often yes | ocean system, floor, shelf, halos, special seas | can miss green/turbid/shallow water; can classify dark blue land/shadow as water |
| `deep_ocean_px` | RGB | float binary | hard | yes by image size only | sometimes yes | ocean system, island halos | `B > 85` misses very dark deep ocean; can swallow valid reef if blue enough |
| `land_px` | RGB | float binary | hard | yes | yes | desert, vegetation, mountains | not inverse of `ocean_px`; inconsistent thresholds create ambiguous pixels |
| `ice_px` | RGB/lum/spread | float binary | hard | yes | yes | polar | snow/cloud/desert salt ambiguity; misses blue-shadow ice |
| `desert_px` | RGB/lum + land | float binary | hard | yes | yes | currently helper only | warm bright land proxy; not robust globally |
| shallow proxy in floor | `ocean_px * clip((lum_after_g - 0.06)/0.20)` | float soft | soft | yes | yes | ocean floor pass 2 | brightness is not depth; dark shallow water is ignored |
| shallow proxy in shelf | `ocean_px * clip((lum - 0.18)/0.25)` | float soft | soft | yes | yes | shelf | threshold too high for failed regions |
| `region_mask_rect` | LAT/LON | float hard or blurred | hard then soft | feather scales with width | no | ocean, land, seas, guards | rectangular artifacts; high-lat distortion; cross-antimeridian partial support |
| `circle_mask` | LAT/LON center + pixel radius | float hard or blurred | hard then soft | radius scales with width | no | island halos; proposed reef floor | circles in pixel space distort km scale by latitude; no antimeridian wrap |
| `feather_mask` | binary mask | float soft | Gaussian | radius scales if caller scales | no | all soft masks | blur in pixel space, not geodesic |
| `scale_feather` | 8K px | int px | n/a | width-scaled | no | bbox/circle feather | ignores latitude and height-specific distortions |
| benchmark crop | lon/lat center + px dimensions | array crop | hard crop | width-scaled | no | previews/metrics | crop can be dominated by irrelevant land/deep ocean |
| protected region masks | LAT/LON rect | hard in guard, soft in diagnostics | mixed | yes | no | guards | diagnostic and guard use different feathering |

Specific answers:

- `ocean_px` can misjudge. It keys on blue dominance; dark non-ocean shadows may pass, while turbid yellow/green shallow water may fail.
- `deep_ocean_px` can swallow shallow blue water and can also miss truly deep but very dark water because of `B > 85`.
- The shallow proxy fails on dark source imagery because it uses current luminance as a depth proxy.
- `region_mask_rect` is no longer used for broad tropical floor mutation, but it is still used for ocean regions, land regions, special seas, and guards.
- Special seas bbox is safer only because it is ocean-gated and feathered; it is not safe enough for narrow seas or coast-dominated crops.
- `circle_mask` does not account for equirectangular latitude distortion. A pixel circle corresponds to very different real-world longitude distance at high latitudes.
- `circle_mask` has no explicit antimeridian wrap; centers near -172 or +178 can fail for halos crossing the image edge.
- 2K/8K/21.6K mask radius scales by width, but feature visibility does not scale linearly for sub-pixel reefs, narrow seas, and JPEG-resized source detail.
- High-lat bbox/circle masks are geometrically distorted.

Critical answer:

No, RGB/luminance proxy plus hand-coded island centers is not sufficient to support the Noon Air global target. It can produce a prototype, but not a robust global generator.

Regions likely to remain unstable without bathymetry/coast/reef data:

- Maldives and other linear atoll chains
- Tuamotu/French Polynesia and dispersed Pacific atolls
- Bahamas and Caribbean banks
- Indonesia/Philippines/Solomon/Vanuatu complex archipelagos
- Red Sea and Persian Gulf narrow/coastal waters
- Yellow Sea/East China turbid shelf
- Arctic/Greenland coastal ice-water transitions
- Any region crossing the antimeridian, especially Fiji/Tonga/Samoa/Aleutians

## Color Mathematics Audit

| Color Operation | Module | Purpose | Risk | Recommendation |
|---|---|---|---|---|
| RGB multiplicative brightness | global base | brighten source | can lift noise and alter later classifiers | keep but consider moving after regional modules |
| contrast around 127.5 | global base | reduce hard contrast | early contrast change affects classifiers | separate classifier input from display output |
| blue channel boost | global base | Noon Air blue bias | pushes masks toward ocean/deep classification | compute masks from original/source-independent data |
| HSL saturation reduction | global/land/ocean | lower harsh colors | HSL on sRGB is perceptual approximation, not linear | acceptable for small deltas |
| HSL hue shift | ocean/special/land | regional color steering | weak for dark pixels; hue unstable near grey/black | use channel-ratio correction for turbid seas |
| HSL lit_delta | ocean/shelf/halo/special | lighten/darken | very weak once masked and intensity-scaled; can clip | split intensities by module |
| `_lift_floor` RGB scaling | ocean floor | minimum luminance rescue | preserves RGB ratios approximately, but saturation perception can change; no true hard floor | keep for rescue, not as reef modeling |
| floor softness 0.55 | ocean floor | avoid hard clamp | target floor is approached, not reached; may leave zones too dark | report actual post-floor lum distribution |
| shelf multiplicative gain | shelf | brighten shallow water | only affects already-bright water; misses dark reef/shelf | replace or augment with bathymetry/coast proxy |
| atmosphere soft light | final | air unification | can lower local contrast and does little for near-black pixels | keep last but exclude/protect reef contrast if needed |
| clipping to 0..255 | all modules | valid RGB | hides overcorrection in metrics if not counted | add clipped-pixel metrics |
| JPEG output | final | artifact/size | quality 92/subsampling 0 is reasonable; still lossy | evaluate metrics before JPEG and visual after JPEG |

Specific answers:

- `_lift_floor` scales all RGB channels by the same factor, so it mostly preserves hue and RGB saturation ratios. It does not preserve HSL saturation exactly, and if applied broadly it can produce a flat, dark-grey/blue haze because all under-floor pixels are scaled similarly.
- HSL `lit_delta` on extremely dark pixels has weak practical effect after mask weights and `NOON_AIR_INTENSITY`; a nominal +0.08 can become near invisible.
- `NOON_AIR_INTENSITY=0.38` over-weakens island halo and shelf modules because those already use small masks/blends. A single global intensity is structurally wrong.
- Intensity should be split at least into `GLOBAL_INTENSITY`, `OCEAN_TONE_INTENSITY`, `SHELF_INTENSITY`, `ISLAND_HALO_INTENSITY`, `REEF_FLOOR_INTENSITY` or no intensity for absolute floors, `SPECIAL_SEA_INTENSITY`, and `ATMOSPHERE_INTENSITY`.
- Deep ocean negative `sat_delta` can make ocean grey-blue, especially when paired with floors and low contrast.
- Yellow/East China likely needs channel-level or target-ratio correction, not just HSL hue shift, because the problem is `G > B` muddy water.
- Red Sea at 2K is too narrow for a whole-crop HSL/lum metric; water-only mask is required.

## Failure History Root-Cause Review

### B-4

Observed: black seas, rectangular patch, French Polynesia hard cut, shallow/island effects covered.

Likely causes:

- Image-mutating final harmony guard with unfeathered protected rectangles caused visible patch/hard cut.
- Dynamic deep mask and negative deep lit deltas contributed to cascading darkening.
- No luminance floor let source-dark ocean pass through.
- Source/d5z_b mismatch made a d5z_b delta guard unsuitable as an auto-corrector.
- Module order let final guard override island/shelf work.

### B-5.1

Observed: black seas improved; large blue rectangular patch appeared.

Likely causes:

- Tropical bbox floor was a false fix: it lifted broad geographic rectangles rather than water structures.
- Floor threshold/target was high enough and feather weak enough to show region boundaries.
- The bbox scheme itself was wrong for reef/island recovery because it represented review regions, not physical structures.

### B-5.2

Observed: rectangles disappeared; Maldives/French Polynesia/Pacific/Hawaii/Caribbean became too dark; Bahamas/Caribbean shelf weak; Red Sea and Yellow/East China unresolved.

Likely causes:

- Removing tropical bbox floor removed the only strong local lift.
- Island halos are too weak under shared intensity and blend scaling.
- Shelf threshold 0.18 ignores dark shallow/shelf candidates.
- Global floor 0.07 only prevents deepest near-black; it does not create reef/shelf hierarchy.
- Source ocean floor is intrinsically too dark relative to desired target in several regions.
- Missing reef/shelf/coast structure masks makes proxy-based recovery unstable.

### Root Cause Tree

Primary root causes:

- No independent bathymetry/coast/reef/shallow-water masks.
- Source-derived pipeline uses color proxies from the same pixels it mutates.
- d5z_b-relative guard semantics do not match source-derived aesthetic generation.
- Metrics do not measure the structures being fixed.

Secondary root causes:

- Single global intensity across unrelated modules.
- Module order and lack of protected structure masks.
- 2K calibration underrepresents sub-pixel reefs and narrow seas.
- Geographic primitives are rectangles and pixel circles, not real water geometry.

Symptoms:

- Dark Maldives/French Polynesia/Hawaii/Pacific Islands.
- Weak Bahamas/Caribbean shelf.
- Red Sea water hidden by desert-dominated crop.
- Yellow/East China green/muddy channel ratio.
- Patch artifacts when geographic floors are too broad.

False fixes:

- Large tropical bbox floor.
- Final harmony guard pixel blend-back.
- Whole-crop mean_lum as a pass/fail for reef visibility.

Valid fixes:

- Diagnostic-only guards.
- Fixed deep mask for deep-only ocean pass.
- Removal of broad tropical bbox floor.
- Adding water-only, reef-local, and per-module metrics.
- Introducing real bathymetry/coast/reef masks or dual-source ocean references.

Unresolved risks:

- Circle artifacts.
- Special-sea bbox artifacts.
- False ocean/land classification.
- 8K visibility of artifacts not apparent at 2K.
- Current source-derived ocean may lack enough shallow structure without external data.

## B-5.3 Adversarial Review

### Proposal Scoring

| Proposal | Benefit | Risk | Implement Now? | Safer Alternative |
|---|---|---|---|---|
| `apply_island_reef_floor` circular inner/outer floors | directly addresses dark island/reef zones without large rectangles | visible circular spots; wrong geometry for chains/platforms; antimeridian issues | split only as B-5.3.1 | start with 3-5 worst zones, low floors, per-zone affected pixels |
| many `_REEF_FLOOR_ZONES` at once | broad coverage | impossible attribution; many circle artifacts | no | minimal pilot list: Maldives, French Polynesia/Tuamotu, Bahamas, Hawaii, Fiji |
| floors not scaled by `NOON_AIR_INTENSITY` | floor semantics should be absolute | can overpower visual style | conditional | add cap on affected pixels and post-floor lum percentile |
| `ISLAND_HALO_LIT_BOOST=1.8` | compensates weak HSL lift | can create cyan glow/fluorescence; still geometry-blind | not with first floor run | add after reef floor if metrics show hue not lift is missing |
| shelf threshold 0.18 -> 0.11 | helps darker shelf candidates | may affect deep ocean/turbid water; no structural mask | defer | collect shelf water-only histograms first |
| `SHELF_GAIN_BOOST=2.5` | makes shelf visible | broad multiplicative lift can flatten water | defer | smaller boost after threshold-only test |
| Caribbean/Bahamas ocean regions | recovers known shallow banks | new bboxes can recreate B-5.1-like regional patches | defer | use Bahamas reef floor pilot first |
| Red Sea lit_delta +0.10 | may make water visible at 2K | bbox plus narrow sea can create odd color sliver; whole-crop metric misleading | defer | add water-only Red Sea metrics first; test lower +0.04/+0.06 |
| Yellow Sea hue +8 / sat -0.06 | targets muddy green | HSL may not guarantee `B > G`; could grey out | defer | channel-ratio correction or B/G metric-led small steps |
| East China sat -0.04 | reduces green mud | can desaturate into grey | defer | water-only `B_over_G`, hue histogram |
| Japan Sea lit +0.03 | raises near-black Japan water | may violate desired deeper Japan Sea | defer | water-only Japan Sea target lum 0.085-0.10 |
| Mediterranean lit +0.01 | removes tiny darkening | small benefit | low priority | leave unchanged unless visual issue appears |

### B-5.3 Specific Risk Notes

- Circle masks can produce circular stains, especially in open ocean around isolated islands.
- Multiple adjacent circles can create a bead/spot cluster at 8K.
- Maldives is linear; one circle misrepresents the north-south chain.
- Tuamotu/French Polynesia is dispersed; one large circle overpaints deep ocean.
- Bahamas is a bank/platform; a circle is a poor approximation.
- Hawaii should not be bright like a tropical lagoon; it needs restrained island legibility.
- Pacific Islands need multiple small zones, but too many small zones risk dotted artifacts.
- Lowering shelf threshold to 0.11 could let dark open ocean enter shelf recovery if `ocean_px` and lum proxy are wrong.
- Adding Caribbean/Bahamas ocean bboxes reintroduces rectangular geography, albeit ocean-gated.
- Red Sea and Yellow/East China corrections must be water-only, not crop-level.

## Alternative Routes

| Route | Reliability | Visual Potential | Engineering Cost | Global Scalability | Recommendation |
|---|---|---|---|---|---|
| A. Continue source-derived generator and implement B-5.3 | medium-low short term | medium if carefully tuned | low-medium | weak without better masks | conditional; split and instrument |
| B. Use d5z_b as direct baseline and apply light aesthetic adjustment | high for stability | medium; may inherit d5z limitations | low | good for near-term | seriously consider as fallback or parallel control |
| C. Dual-source fusion: source for land/polar/desert, d5z_b or old candidate for ocean/shallow/islands | medium-high if masked well | high | medium | good if ocean-only masks are improved | recommended as next architecture experiment |
| D. Add real bathymetry/coastline/reef data: GEBCO/GSHHG/Natural Earth/reef proxies | high | high | high | best long-term | plan for Phase C; required for robust global target |
| E. Manual master polish then back-solve params | medium for visual target | high as reference | high/manual | poor unless back-solved | useful as visual target only, not production source |

Route B may be more stable than current source-derived for ocean/island visuals because d5z_b is already production-verified and preserves accepted shallow/reef behavior better than the current calibration output. Its downside is that it may limit the full Noon Air aesthetic rethink.

Route C is the strongest pragmatic architecture: keep source-derived land/polar/desert advantages, but borrow ocean/shallow/island structure from d5z_b or an earlier accepted candidate. It needs an ocean-only blend mask and seam control. Without a better mask, seams are likely.

Route D is the real root-cause route. Bathymetry/coastline/reef data is the right way to model shelf/reef/coastal water independent of source RGB. It is probably too large for immediate B-5, but should not be postponed indefinitely if Noon Air Earth remains a global target.

## Metrics System Redesign

| Metric | Object | Mask Needed | Target / Use | Hard Guard? | Misleading Risk |
|---|---|---|---|---:|---|
| global mean RGB/lum | full image | none | broad drift only | no | hides local failures |
| ocean mean lum | water pixels | improved ocean mask | avoid global black ocean | review | ocean mask may be wrong |
| deep ocean lum percentiles | deep water | deep mask or bathymetry | maintain clear dark blue, not black | review | RGB deep mask biased |
| shallow shelf lum percentiles | shelf | bathymetry/coast proxy | shelf visible but not fluorescent | review | proxy can include deep/turbid water |
| `reef_inner_mean_lum` | reef core zones | reef/zone mask | zone-specific floor validation | review | circle masks do not equal reefs |
| `reef_outer_mean_lum` | reef transition | reef outer mask | preserve deep-water falloff | review | too broad if circles |
| `reef_local_contrast` | inner vs outer vs surrounding deep | reef masks | must not flatten | review | bad zones create false pass |
| `affected_pixel_count` | per module and per zone | module delta mask | bound patch size | yes for experiments | needs instrumentation |
| `B_minus_G` | turbid seas | water-only mask | Yellow/East China should trend B >= G | review/hard for target | no if land included |
| `yellow_east_china_B_over_G` | water-only Yellow/East China | water-only | >1.0 for target blue bias | review | source mud may be intentional locally |
| `water_only_red_sea_lum` | Red Sea water | narrow water mask | water visible despite desert | review | hard at 2K |
| polar ice lum/spread | ice | ice mask | texture preserved, no blowout | hard for promotion | clouds/snow ambiguity |
| desert max/percentile lum | Sahara/Arabia land | land/desert mask | no overexposure | review/hard | formula bug can distort |
| patch_artifact_score | output/diff | connected components/edge-energy | detect rectangles/circles | hard for experiments | needs baseline thresholds |
| per_module_delta | each module output delta | stored intermediate metrics | attribution | review/hard for large deltas | requires instrumentation |
| clipped_pixel_count | final and per module | none | avoid clipping | hard | small highlights allowed |

Immediate metric additions before next calibration:

- `reef_inner_mean_lum`
- `reef_outer_mean_lum`
- `reef_local_contrast`
- per-zone `affected_pixel_count`
- `water_only_red_sea_lum`
- `yellow_east_china_B_over_G`
- `B_minus_G`
- `patch_artifact_score`
- `per_module_delta`

## Final Answers

1. Current root cause is substantially confirmed: insufficient semantic masks and mismatched source-derived vs d5z_b-relative guard/metrics semantics.
2. B-5.3 is partially aligned with symptoms, not fully with root cause.
3. Do not implement B-5.3 as one combined change.
4. If implemented, split into:
   - B-5.3.1 island reef only
   - B-5.3.2 shelf only
   - B-5.3.3 special seas only
5. Must defer: shelf threshold/gain boost, Caribbean/Bahamas bboxes, aggressive Red Sea +0.10, Yellow/East China large HSL changes, broad reef zone list.
6. Yes, consider a d5z_b baseline route as a serious fallback/control.
7. Yes, real bathymetry/coastline/reef data is needed for robust global production quality.
8. Do not commit generator changes solely because B-5.1/B-5.2 removed major failures; commit only if the project wants to checkpoint safety semantics while acknowledging output still fails visual goals.
9. Prefer committing docs first, not generator, unless explicitly checkpointing B-5.1/B-5.2 engineering safety.
10. Next smallest safe action: add/commit this audit doc and then add metrics instrumentation before any new calibration run.

## Final Recommendation

- Continue current source-derived route? Conditional.
- Implement B-5.3 now? Split.
- First implementation target: B-5.3.1 island/reef-only pilot with minimal zones and new reef/affected-pixel metrics.
- Must not implement yet: shelf gain boost, new Caribbean/Bahamas ocean bboxes, aggressive Red Sea/Yellow/East China changes, full reef-zone list.
- Metrics to add before next calibration: reef inner/outer lum, reef local contrast, affected pixel count, B_minus_G, Yellow/East China B_over_G, water-only Red Sea lum, patch artifact score, per-module delta.
- Commit recommendation: commit docs first; do not commit generator as production-progress evidence. If generator safety changes are committed, label them as calibration-safety only, not visual acceptance.
- Risk level: high for production, medium for controlled 2K calibration.
- Next command for Claude Code: `git add docs/phase_b5_3a_codex_noon_air_generator_deep_architecture_audit.md && git commit -m "docs: audit noon air generator architecture"`

## Non-Execution Confirmation

- Code modified: no generator/runtime code modified.
- Generator run: no.
- New image generated: no.
- Calibration run: no.
- Full-res run: no.
- Candidates/production/front-end modified: no.
- Commit/push performed: no.
