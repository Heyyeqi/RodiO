# Next Step Recommendation — Post-Prototype Decision Tree

**Date:** 2026-06-08  
**Prerequisite:** Fill in the verdict table in README_PROTOTYPE.md after visual inspection.

---

## Decision Tree

```
[Start: Visual inspection complete]
        │
        ▼
GEBCO ocean clearly better than ETOPO1?
  ├─ No  → Investigate GEBCO tint blend params; re-test at blend 0.45 or 0.50
  └─ Yes ─► GSHHG coastline clearly improves bays/islands?
               ├─ No  → Investigate coastal zone params; re-test at zone 15km / strength 0.20
               └─ Yes ─► GIS / map-style feel detected?
                            ├─ Yes → Reduce GSHHG strength; reduce GEBCO blend; isolate source
                            └─ No  ─► v2 tile clearly better than baseline?
                                         ├─ No  → Review composition logic
                                         └─ Yes ─► PROCEED TO STEP A
```

---

## Step A — Immediate: On-Globe Demo Validation

**Trigger:** All four above are Yes.  
**Action:** Build an independent on-globe HTML demo (NOT modifying earth3d.js) that:
- Loads the real d5b_v3.2.1 globe texture
- Applies Japan UV region blend using the v2 tile
- Tests at camera distances matching RodiO production globe (approx 1.25–1.50)
- Compares visual quality in the actual globe context (lighting, atmosphere)

**Why before earth3d.js integration:** The current prototype demo is a flat UV-blend validation. The production globe uses ShaderMaterial, possibly with atmosphere, specularity, or rotation — these need to be validated with the actual tile before committing to integration.

**Not-before criteria:**
- Do NOT integrate into earth3d.js until on-globe demo confirms the tile looks correct in 3D globe context
- Do NOT replace any formal texture

---

## Step B — Medium Priority: DEM Phase

**Trigger:** Step A validates tile looks correct on globe.  
**Action:** Download Copernicus GLO-30 (30m) or ALOS AW3D30 for Japan bounds.  
**What it adds:**
- True 30m-grade land terrain hillshade
- Mountain ridge detail (Japanese Alps, Mt. Fuji, Hokkaido range)
- Accurate land/sea transition elevation
- Hillshade layer blended on top of d5b base (land only)

**Scope note:** DEM Phase is independent of GEBCO/GSHHG. It can run in parallel with Step A.

---

## Step C — After DEM Stable: Formal earth3d.js Integration

**Trigger:** Both Step A (on-globe demo) and Step B (DEM hillshade) produce satisfactory visuals.  
**Action:** Plan formal integration into earth3d.js UV region blend pipeline.  
**Requires:**
- Final parameter freeze (blend, zone, strength)
- Tile format decision (PNG vs JPEG q=95; 2048 vs 4096)
- `regionalDetailConfig.js` structure design (globally reusable, not Japan-only)
- Globe renderer compatibility test (ShaderMaterial + atmosphere + rotation)
- No earth3d.js modification until this step is explicitly approved

---

## Step D — Deferred: Layer 6 (City Roads / City Lights)

**Trigger:** Natural geography layers (GEBCO + GSHHG + DEM) are stable and formally integrated.  
**Action:** Layer 6 = OSM road glow + VIIRS Night Lights overlay.  
**Why deferred:**
- Adding city lights before natural geography is stable creates compounding visual issues
- Layer 6 is a fundamentally different data type (vector/raster hybrid)
- OSM road data is not included in current P0/v2 pipeline
- Night lights (VIIRS Black Marble) need separate blend logic

**Recommendation:** Continue deferring Layer 6 until DEM Phase is complete.

---

## Step E — Global Rollout (Future)

**Trigger:** Japan benchmark validated end-to-end (Steps A–C).  
**Action:** Apply `rdl_tile_compositor.py --bounds ...` to all priority regions.  
**Priority tiers:**
- **Tier A (4096):** Japan, Korea, UK+Ireland, Western Mediterranean, US East Coast (high aesthetic interest)
- **Tier B (2048):** Southeast Asia, Indian subcontinent, Caribbean, Scandinavia, Great Barrier Reef
- **Tier C (global auto):** All remaining ocean/coast regions via batch `--tier C`

**Key constraint:** No region-specific hardcoding. All regions use the same script with `--bounds`.

---

## Parameter Freeze Recommendation (After Inspection)

*Fill in after visual review:*

| Parameter | Candidate | Confirmed |
|---|---|---|
| GEBCO blend | 0.35 | — |
| GSHHG zone | 10km | — |
| GSHHG strength | 0.15 | — |
| Visual texture blend | 0.30 | — |
| Tile size | 4096×3584 (Tier A) | — |

---

## What Must NOT Happen Next

1. Modifying earth3d.js before on-globe demo (Step A) is validated
2. Replacing pwa/assets/earth/ textures before Step C is explicitly approved
3. Committing generated PNG tiles to git
4. Claiming the current v2 tile resolves land terrain precision (it does not; that is DEM Phase)
5. Treating Japan v2 tile as a template to copy-paste for other regions; use `--bounds` parameter instead
