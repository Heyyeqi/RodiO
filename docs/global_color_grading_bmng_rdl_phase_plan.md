# RodiO Day Earth Global Color Grading / BMNG-RDL Visual Upgrade Phase

> Created: 2026-06-09
> Status: Planning — awaiting review before any implementation begins
> Prerequisite: E1 Day Earth Master closed; d5z_b in production

---

## 1. Current Baseline

- `d5z_b` is the current default Day Texture in production (`DAY_TEXTURE_VARIANT = 'd5z_b'`).
- It is the stable 8K output of the E1 pipeline: polar brightness correction (Antarctica, Greenland), deep ocean desaturation (Indian Ocean, Pacific), and desert warmth correction (Sahara, Arabia).
- E1 is Production Verified and Closed. No further D5z iterations.
- `d5z_b` is not the final RodiO Earth. It is the current stable 8K baseline — the floor from which the next phase begins.
- Color temperature, regional hierarchy, ocean transparency, and global harmony remain unresolved at the level this phase targets.

---

## 2. Why D5z Phase Is Closed

D5z completed its mandate: stabilize the 8K baseline, correct the most visible regional defects, and pass full on-globe visual acceptance. That mandate is fulfilled.

Continuing to iterate on D5z would be the wrong move for the following reasons:

1. **Diminishing returns.** D5z corrections were targeted and surgical. Additional passes on the same source would be chasing noise rather than resolving structural problems.
2. **Source ceiling.** The underlying source material has a quality ceiling. Patch-level adjustments cannot substitute for a higher-quality global base layer.
3. **Wrong tool for the remaining problems.** The remaining gaps — ocean transparency hierarchy, deep-sea GIS feeling, land atmosphere, coastline precision — require a different pipeline architecture: better source data, region-aware compositing, and a global color grading system. A D5z_c would not provide these.
4. **The phase boundary is real.** Staying in D5z to avoid the complexity of BMNG/RDL is an anti-pattern. The work that matters next is structurally different, and it should be scoped, planned, and executed as its own phase.

D5z is archived. The next phase starts from it, not with it.

---

## 3. Visual Target

The target aesthetic is **RodiO Earth** — not Google Earth, not a GIS product, not a scientific reference map. It is an aesthetic-real Earth designed for continuous visual presence in an AI radio experience.

Reference aesthetic anchors: *Dawn FM*, *Rituals* (Nicola Conte), high-production travel cinematography, broadcast globe visuals.

**Ocean**
- Deep ocean: dark, calm, with directional depth — not turquoise-grey, not GIS blue-contour.
- Shallow water: layered transparency — Caribbean coral-sand gradients, Mediterranean azure-to-turquoise transition, Red Sea warmth, Southeast Asian reef clarity.
- Coastal fringe: distinct from open ocean; islands read as islands, not blobs.

**Land**
- Atmosphere: haze, aerial perspective, spatial depth — land should not look flat.
- Terrain: mountain ranges carry shadow and relief; ridgelines read clearly.
- Desert: warm, clean, slightly luminous — not bleached, not grey-brown, not washed out.
- Vegetation: green with variation and saturation controlled; not oversaturated, not dull.

**Polar**
- Controlled brightness — ice detail preserved, no blowout.
- Cold white, not warm grey, not neon.
- Arctic and Antarctic handled as distinct tonal zones.

**Coastlines and Islands**
- Coastline precision matters: island chains, peninsulas, deltas should be legible without being GIS-clean.
- Shallow reef zones around Pacific and Caribbean islands should be visible and beautiful.

**Global Harmony**
- No region should dominate or break the overall tonal balance.
- The globe should read as a coherent object at standard player view (lon=10, lat=20).
- Color consistency across time modes (morning, noon, afternoon, sunset).

**UI Integration**
- The earth must not compete with the RodiO player UI.
- Text, album art, and controls must remain readable against any globe region.
- Not a wallpaper. A presence.

---

## 4. Core Problems To Solve

1. **Ocean transparency and shallow-water hierarchy.** Current baseline lacks tonal differentiation between shallow reefs, mid-depth coastal zones, and open ocean. The Caribbean, Mediterranean, Red Sea, and Southeast Asian archipelagos all deserve distinct, layered water color.

2. **Deep ocean GIS feeling.** Uniform or subtly-banded deep-ocean coloring reads as a bathymetric chart. The target is calm, directional depth — dark without being flat, blue without being informational.

3. **Land atmosphere and terrain depth.** Flat land textures lack aerial perspective. Mountain ranges, plateaus, and coastal plains need tonal layering to convey depth and scale.

4. **Desert warmth and highlight control.** Sahara, Arabian Peninsula, and Central Asian deserts trend towards washed-out or dusty-grey. The target is warm, luminous, clean — sand, not cement.

5. **Polar brightness and detail.** Antarctica and Greenland ice can blow out or grey-flatten under lighting. The target preserves cold-white with texture and avoids over-correction into neutrality.

6. **Coastline and island precision.** Small islands, coral atolls, river deltas, and fjord systems lack sharpness or readable contrast. A composited coastline/shoreline layer is needed to correct this without imposing a GIS look.

7. **Global color harmony.** Regional corrections risk creating a patchwork. The pipeline must maintain overall tonal consistency: a hue shift in one ocean should not create a discontinuous seam at a regional boundary.

8. **Runtime UI integration.** The globe rotates continuously at standard player view. Visual quality must hold across full rotation, not only at selected benchmark angles. Time-of-day lighting modes must remain visually stable.

---

## 5. Non-Goals

The following are explicitly out of scope for this phase — including for this planning document:

- Generating any new image or texture file.
- Downloading BMNG, GEBCO, GSHHG, DEM, OSM, VIIRS, or any external dataset.
- Replacing or modifying the production texture (`pwa/assets/earth/production/`).
- Modifying `DAY_TEXTURE_VARIANT` in `earth3d.js`.
- Committing runtime code changes.
- Treating Japan as the final goal. Japan is a benchmark region, not the destination.
- Building single-region specialist patches (the lesson from E1 is that regional patches without a global system create inconsistency).
- Importing OSM, VIIRS, or city-light layers. These are post-Phase options.
- Treating `d5z_b` as the final earth — it is the baseline, not the destination.

---

## 6. Data / Pipeline Direction

The following data sources and pipeline components are candidates for this phase. None are downloaded or implemented yet.

**Base Layer**
- **BMNG (Blue Marble Next Generation, NASA):** Monthly composites at up to 86400×43200. Candidate for a new global base layer with higher radiometric quality and color fidelity than the current source.
- **BMNG variant selection:** Different months capture different seasonal vegetation and snowline states. Month selection is an aesthetic decision, not a data-accuracy decision.

**Ocean Enhancement**
- **GEBCO / ETOPO bathymetry:** Seafloor depth grids for generating synthetic shallow-water transparency gradients and deep-ocean depth cues.
- **Custom bathymetry tinting:** Use depth contours to drive hue/saturation layering, not to reproduce a bathymetric chart.

**Coastline and Shoreline**
- **GSHHG (Global Self-consistent Hierarchical High-resolution Geography):** Shoreline polygons at multiple resolutions. Use as mask for coastline sharpening and island isolation — not as an overlay.

**Terrain**
- **SRTM / DEM (Digital Elevation Model):** Elevation data for synthetic hillshading, aerial-perspective haze, and mountain-ridge contrast enhancement on land.

**Regional Detail**
- **RDL (Regional Detail Layer):** Custom compositing passes for selected benchmark regions that need precision beyond what a global base layer provides. Built on top of BMNG+GEBCO+GSHHG, not as a standalone patch.

**Deferred (Post-Phase)**
- OSM road/city data — for future urban detail if needed.
- VIIRS night lights — for potential nightside enhancement.
- Human-activity or land-use overlays.

The pipeline architecture should be: `BMNG base → bathymetry-driven ocean grading → DEM-driven terrain enhancement → GSHHG coastline sharpening → RDL regional passes → global color harmony guard → output`.

---

## 7. Benchmark Regions

The following regions serve as benchmarks across the full development cycle. Japan is one of twelve — it is the method-validation region from RDL MVP work, not the final target.

| Region | Primary Challenge |
|---|---|
| **Japan / East China Sea** | Coastline precision, shallow-sea clarity, land-ocean contrast |
| **Mediterranean** | Shallow-water hierarchy, blue-green gradient, coastal warmth |
| **Caribbean** | Coral-reef transparency, island legibility, turquoise layering |
| **Red Sea / Arabian Peninsula** | Desert warmth, warm-water tinting, coastal sharpness |
| **Indian Ocean (central)** | Deep-ocean calm, avoiding GIS banding |
| **Pacific Islands (Polynesia)** | Atoll legibility, isolated-island readability, deep-Pacific depth |
| **Sahara / Egypt** | Desert luminosity, warmth control, Nile delta contrast |
| **Greenland / Arctic** | Polar brightness, ice detail, land-ice boundary |
| **Antarctica** | Polar blowout control, texture preservation, cold-white tone |
| **Southeast Asia / Indonesia** | Dense archipelago, shallow reef, tropical atmosphere |
| **Europe / Middle East wide** | Multi-zone harmony, land-sea balance, global tone anchor |
| **South Pacific (Tahiti, Fiji, Tonga)** | Deep-blue ocean with island jewel contrast |

Each benchmark region gets a defined set of acceptance crops and time modes. No region is treated as the sole target. All twelve regions must pass before phase acceptance.

---

## 8. Acceptance Criteria

A candidate output passes this phase when all of the following hold:

**Standard Player View (lon=10, lat=20, all time modes)**
- Globe reads as a coherent, beautiful object.
- No region dominates, breaks tone, or draws the eye away from the player UI.
- Text, album art, and controls remain readable against any globe region.

**Ocean**
- Shallow-water zones in benchmark regions show tonal layering (at minimum: reef / coastal / open-ocean differentiation).
- Deep ocean does not exhibit visible GIS contour banding.
- No ocean region appears fluorescent or oversaturated.

**Land**
- Desert regions (Sahara, Arabia) read as warm and clean, not washed-out or grey.
- Mountain ranges carry visible relief.
- Vegetation zones are not flat.

**Polar**
- Antarctica and Greenland ice preserves texture and detail.
- No blowout. No grey-flatten.
- Brightness is controlled: visually bright but not dominant.

**Coastlines and Islands**
- Islands and archipelagos are legible.
- No hard GIS-edge artifacts.
- Coastal fringe is distinct from open ocean and from land.

**Global Consistency**
- No visible seam between regional correction zones.
- Color tone is globally coherent across all twelve benchmark regions.
- All four time modes (morning, noon, afternoon, sunset) are visually stable.

**RodiO Aesthetic**
- The globe feels like a presence, not a map.
- It is compatible with the radio / accompaniment / introspective character of RodiO.
- It would not look out of place in a *Dawn FM* or *Rituals* visual context.

---

## 9. Phase Breakdown

This is a directional breakdown. Scope and sequencing will be refined at the start of each sub-phase.

**Phase A: Source and Pipeline Feasibility Assessment**
- Evaluate BMNG monthly variants as base layer candidates: global coverage, resolution (up to 86400×43200), radiometric quality, licensing, file size, and processing cost.
- Evaluate GEBCO / ETOPO bathymetry for ocean grading feasibility: depth-to-color mapping potential, coverage at benchmark regions.
- Evaluate GSHHG coastline data: resolution tiers, polygon quality at standard globe scale, mask applicability.
- Evaluate SRTM / DEM for terrain enhancement: hillshading approach, aerial perspective feasibility.
- Assess alignment with RodiO visual targets at each benchmark region — not as production output, but as source qualification.
- Define month selection criteria for BMNG (aesthetic, not seasonal accuracy).
- **Boundaries:** No data is downloaded. No new textures are generated. No pipeline code is executed. No benchmark crops or previews are produced. Phase A is desk research and feasibility judgment only. Phase A output is a written source selection decision and feasibility verdict. Small-scale prototype validation (a single benchmark region crop, no globe output) is only permitted after Phase A is closed and explicitly authorized.

**Phase B: Ocean Grading System**
- Build bathymetry-driven shallow-water transparency pipeline.
- Establish deep-ocean tonal target.
- First test on Japan / Caribbean / Mediterranean as benchmark trio.

**Phase C: Land and Terrain System**
- DEM-driven hillshading and aerial perspective.
- Desert warmth correction at global scale.
- Vegetation saturation normalization.

**Phase D: Coastline and Island Precision**
- GSHHG-based coastline sharpening pass.
- Island legibility at standard globe scale.
- No GIS artifacts.

**Phase E: Global Color Harmony Guard**
- Full benchmark-region audit across all twelve regions.
- Color harmony verification: seam detection, saturation balance, tonal anchor.
- Protected regions locked before any further pass.

**Phase F: On-Globe Acceptance**
- Puppeteer / browser-based screenshot review across all benchmark regions × all time modes.
- Human visual acceptance (same E1-R5 protocol, extended to all twelve regions).
- Conditional Pass threshold: max 2 Partial, only ocean depth or polar tone.

**Phase G: Production Promotion**
- Replace `pwa/assets/earth/production/` with accepted output.
- Update `DAY_TEXTURE_VARIANT`.
- Commit, push, deploy.

---

## 10. Risks and Guardrails

**Risk: Source quality ceiling**
BMNG, while higher quality, still has radiometric and color inconsistencies across months and regions. Blind trust in the source is not appropriate. Every phase output requires visual review.

**Risk: Regional patch accumulation**
The failure mode of E1 was accumulating region-specific patches without a global system. This phase must build the system first, then apply it globally. No single-region patches without a global pass.

**Risk: Over-processing**
More processing layers mean more opportunities for artifacts, seams, and tonal drift. Each pipeline stage needs a reversibility plan and a diff-comparison step.

**Risk: D5z regression**
Any new candidate must be compared against `d5z_b` at all twelve benchmark regions. No region that passed E1 acceptance should regress.

**Risk: UI readability**
Earth visual quality must never be pursued at the cost of UI legibility. Player text and controls are the primary interface. The earth is the background.

**Guardrail: Protected regions (inherited from E1)**
Japan, Mediterranean, Caribbean, Pacific Islands — these passed E1 clean. Any future correction that causes detectable regression in these regions triggers a rollback.

**Guardrail: No production change without full acceptance**
`DAY_TEXTURE_VARIANT` and production textures are not modified until Phase F acceptance is complete and explicitly authorized.

**Guardrail: No large binaries in repo**
All candidate and output textures go to `pwa/assets/earth/candidates/` (gitignored). Only accepted production textures go to `pwa/assets/earth/production/`.

**Guardrail: E1 / d5z_b baseline floor**
Any BMNG / RDL / Global Color Grading candidate must meet or exceed `d5z_b` across all of the following dimensions. Regression on any dimension is a blocker — not a Partial:
- Default load stability (HTTP 200, correct variant confirmed, 8192×4096 resolved).
- UI readability: player text, controls, and album art remain legible against any globe region.
- Standard player view overall impression (lon=10, lat=20, all time modes).
- Global coverage completeness: no missing regions, no rendering voids.
- Multi time-mode stability: no blowout, no grey-flatten, no color shift across morning / noon / afternoon / sunset.
- No introduction of over-exposure, desaturation/graying, dirty color, GIS feeling, or visible seams that are worse than `d5z_b`.
- No regression in the four E1 protected regions: Japan, Mediterranean, Caribbean, Pacific Islands.

---

## 11. Next Action

This document is the phase entry point. No implementation has begun.

**Awaiting:** RW / Evan review and approval of this plan before any Phase A work begins.

**On approval, first step:** Phase A — Source and Pipeline Feasibility Assessment. Desk research only: assess BMNG monthly variants, GEBCO, GSHHG, and DEM against RodiO visual targets. No data downloads, no pipeline execution, no output textures. Phase A closes with a written source selection decision and feasibility verdict.

**Not starting yet:**
- No data downloads.
- No pipeline scripts.
- No texture generation.
- No runtime changes.
- No commits beyond this document.
