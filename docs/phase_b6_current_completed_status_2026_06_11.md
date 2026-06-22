# Phase B-6 Current Completed Status — 2026-06-11

This document records the current saved state of the RodiO B-6 Structure Mask / Global Source Cache work before the next implementation phase.

No production texture has been changed. `DAY_TEXTURE_VARIANT` remains untouched. d6 / Noon Air visual rebuild remains paused.

## 1. Current Strategic State

B-6 has moved from local patch-style structure masks toward a unified global source-cache route:

```text
GEE global source cache
→ local import / alignment
→ semantic mask derivation
→ validation
→ API / priority design
→ d6 / visual color application
```

The important strategic change is that future masks should be derived from a coherent source inventory instead of isolated RGB / luminance / bbox / circle-mask patches.

## 2. Completed / Documented Work

### Structure Mask Validation And Expansion

Completed documentation now covers:

- B-6.2S-1A special sea water-only mask validation;
- B-6.2G global surface feature taxonomy / gap audit;
- B-6.2G-SYS global semantic layer system audit;
- B-6.2G-1A inland water asset feasibility;
- B-6.2G-1C inland water / lake mask validation;
- B-6.2G-2A terrain / relief feasibility;
- B-6.2G-3A river / delta / wetland feasibility;
- B-6.2G-4A desert / arid / bare land feasibility;
- B-6.2G-4A-R desert / arid external dataset solution;
- B-6.2G-4D / D-1 / D-2 desert-arid data acquisition planning;
- B-6.2G-4D-2P-R 8K + 21.6K resource acquisition setup;
- B-6.2G-4D-2-R8K ESA WorldCover 8K import test update;
- B-6.2X GEE global source export batch plan.

### Structure Mask Generator

`scripts/generate_b6_structure_masks.py` now contains B-6 structure-layer generator updates through B-6.2G-3B-R:

- base land / ocean / bathymetry masks;
- polar land-ice supplement;
- 11 special sea water-only masks;
- lake / inland water masks from GSHHG L2/L3;
- terrain / relief proxy masks with post-feather land/inland-water clipping;
- WDBII L01 major river proxy baseline;
- WDBII L01+L02 river-network coverage supplement;
- metadata / metrics / preview support for the above.

Syntax-only validation was performed:

```text
ast.parse scripts/generate_b6_structure_masks.py: pass
```

The generator was not run during this save step.

### GEE Source Cache

`.gitignore` now ignores:

```text
d5b_processor_v3/source_cache/
```

This prevents manually downloaded / exported GEE source rasters, diagnostic files, and source-cache manifests from being committed accidentally.

The ESA WorldCover 8K export was imported into the gitignored source cache and diagnostic-only stats / preview were generated in the cache. These outputs remain untracked and must not be committed.

## 3. Commit-Eligible Files

The following are suitable to save in git as source / documentation state:

- `.gitignore`;
- `devlog.md`;
- `scripts/generate_b6_structure_masks.py`;
- B-6 docs under `docs/phase_b6_*`;
- this status document.

The following are not suitable for this commit:

- `d5b_processor_v3/d6_noon_air_earth_generator.py` — B-5 visual generator changes remain separate and should not be mixed into B-6 structure-layer commit;
- `d5b_processor_v3/source_cache/` — external source cache, gitignored;
- `d5b_processor_v3/d5b_output/` — generated structure masks, gitignored;
- root `previews/` — local review previews, not part of this commit;
- `pwa/`, `production/`, `candidates/` — must remain untouched.

## 4. Current Boundary

Still forbidden until explicitly re-opened:

- d6 integration;
- visual rebuild / 上色;
- production texture replacement;
- `pwa/assets/earth/candidates/` writes;
- `pwa/assets/earth/production/` writes;
- `DAY_TEXTURE_VARIANT` changes;
- committing exported rasters;
- committing generated structure masks;
- committing root preview folders.

## 5. Recommended Next Step

Proceed to:

```text
B-6.2X-D1 — Source Cache Setup / Gitignore Audit
```

Then:

```text
B-6.2X-D2 — GEE Export Script Draft
B-6.2X-D3 — 8K Import Test
```

Do not resume B-5.3 visual patching or d6 rebuild until the unified GEE-derived source/mask route has passed validation gates.
