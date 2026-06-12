# Japan v2 Visual Retuning Pass — Results

**Date:** 2026-06-09
**Region:** 118–150°E, 22–50°N
**Generator:** `scripts/geo/rdl_retuning.py`
**Status:** Retuning pass only — no new data sources, no formal integration

---

## Changes vs v2 Prototype

| Component | v2 Prototype | Retuning |
|---|---|---|
| GEBCO approach | 5-level hard palette at blend=0.35 | Continuous depth darkening, blurred, monochrome |
| Coastal clarity | Unsharp mask (radius=1.5, amount=80%) | Extra L1 texture blend, feathered both sides |
| Land visual blend | 0.30 | 0.15 |
| GEBCO blend | 0.35 | 0.2 (0.15/0.20/0.25 variants) |
| GSHHG zone | 10km unsharp zone | 20km soft blend band |
| Coast strength | 0.15 (sharpening) | 0.08 (texture blend boost) |

---

## Output Files

### Bathy variants (coast off, vary depth blend only)
- `retune_bathy_soft_015.png` — depth darkening at blend=0.15
- `retune_bathy_soft_020.png` — depth darkening at blend=0.20
- `retune_bathy_soft_025.png` — depth darkening at blend=0.25

### Coast variants (bathy=0.20, vary band width only)
- `retune_coast_soft_010km.png` — coastal texture band 0–10km
- `retune_coast_soft_020km.png` — coastal texture band 0–20km
- `retune_coast_soft_030km.png` — coastal texture band 0–30km

### Final combined
- `retune_final_soft_4096.png` — recommended params, 4096×3584
- `retune_final_soft_2048.png` — recommended params, 2048×1792
- `retune_before_after_contact_sheet.png` — v2 vs retune side-by-side

### Crops (before vs after, 5 regions)
- `retune_crop_tokyo_bay.png`
- `retune_crop_osaka_seto.png`
- `retune_crop_ryukyu.png`
- `retune_crop_east_china_shelf.png`
- `retune_crop_japan_trench.png`

---

## Verdict Table (Fill After Visual Review)

| Question | Verdict | Notes |
|---|---|---|
| GIS feel reduced vs v2 prototype? | — | Compare retune_before_after_contact_sheet.png |
| Ocean depth still visible and readable? | — | Check retune_crop_japan_trench.png, east_china_shelf |
| Coastline transition more natural (no edge lines)? | — | Check retune_crop_tokyo_bay.png, osaka_seto |
| Better visual fit for RodiO globe aesthetic? | — | Overall impression on retune_final_soft_4096.png |
| Recommended bathy blend? | — | Compare retune_bathy_soft_015/020/025.png |
| Proceed to isolated on-globe demo? | — | Only if all above are Yes or Partial-positive |

---

## Recommended Parameters (Candidate)

Based on design intent (not yet visually confirmed):

| Parameter | Recommended | Range Tested |
|---|---|---|
| visual_blend | 0.15 | fixed |
| bathy_blend | 0.20 | 0.15 / 0.20 / 0.25 |
| coast_band_km | 20km | 10 / 20 / 30km |
| coast_strength | 0.08 | implicit (fixed per band) |

The 0.20/20km/0.08 combination prioritizes subtlety: ocean depth is readable
without a scientific-map appearance, and coastal bays gain structure from the
21.6K satellite colors blended near shore.

---

## Technical Notes

### Depth gradient approach
Instead of mapping elevation to 5 discrete color bands, depth is converted to
a monochrome brightness influence field:
- Normalize depth to [0,1] at 6000m (covers Japan region max depth)
- Apply sqrt remap (boosts shallow shelf structure visibility)
- Gaussian blur sigma=20px at native GEBCO resolution (~7.5km spatial smoothing)
- Apply as darkening factor on ocean pixels: max ~20% darker at deepest (bathy_blend=0.25)
- Add very subtle blue shift (+10 max blue value at deepest)

No color palette is used. The d5b ocean color palette is preserved; only brightness
and a tiny blue tint vary with depth.

### Coastal texture approach
Instead of unsharp mask (which creates halos at coastline edges), the 21.6K
satellite source is blended more strongly within the coastal band:
- Compute distance from coast using scipy EDT
- Apply squared falloff (softer than linear), Gaussian-blurred
- Near coast (weight≈1.0): L1 blend increased by coast_strength
- This brings satellite coastal colors (shallow bay turquoise, shallow shelf)
  into the composite more strongly near coasts, improving bay readability
  without drawing any visible edge or border

### Constraints maintained
- No earth3d.js modification
- No pwa/assets/earth/ writes
- No DEM / OSM / VIIRS download
- No commit
- All layers loaded from cached P0 and prototype outputs
