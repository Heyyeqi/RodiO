#!/usr/bin/env python3
"""
rdl_retuning.py — RDL Visual Retuning Pass

Converts GEBCO/GSHHG from GIS-data feel to natural globe aesthetics:
  - GEBCO: continuous depth darkening (no palette, no hard steps), blurred, monochrome
  - GSHHG coastal: smooth texture blend boost near coasts (no unsharp mask / edge lines)
  - Land: lighter visual blend (0.15 vs 0.30)

Loads cached layers from v2 prototype to skip the 200s 21.6K source load.
No new data downloads. No earth3d.js changes. No pwa/assets/earth writes. No commit.

Usage:
  python3 scripts/geo/rdl_retuning.py
"""

import os
import sys
import json
import time
from datetime import datetime, timezone

import numpy as np
import netCDF4 as nc
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, gaussian_filter

# ─── Paths ────────────────────────────────────────────────────────────────────

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROTO_LAYERS = os.path.join(ROOT, "previews/rdl_v2_japan_visual_tile_prototype/01_layers")
PROTO_TILES  = os.path.join(ROOT, "previews/rdl_v2_japan_visual_tile_prototype/02_tiles")

GEBCO_NC     = os.path.join(ROOT, "pwa/assets/source/bathy/gebco_2026/gebco_2026_118_150_22_50.nc")
GSHHG_MASK   = os.path.join(ROOT, "previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/gshhg_coastline_mask.png")

OUT_DIR      = os.path.join(ROOT, "previews/rdl_v2_japan_visual_retuning")

# ─── Region constants ─────────────────────────────────────────────────────────

LON_W, LON_E, LAT_S, LAT_N = 118.0, 150.0, 22.0, 50.0
TW4, TH4 = 4096, 3584   # Tier A
TW2, TH2 = 2048, 1792   # Tier B

def ppkm(tw):
    mid = (LAT_S + LAT_N) / 2
    return tw / ((LON_E - LON_W) * 111.0 * np.cos(np.radians(mid)))

PPK4 = ppkm(TW4)   # ~1.425 px/km at 4096

# ─── Utilities ────────────────────────────────────────────────────────────────

def save_png(arr, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(arr.astype(np.uint8)).save(path)
    mb = os.path.getsize(path) / 1e6
    print(f"  saved: {os.path.relpath(path, ROOT)} ({mb:.1f}MB)")

def make_contact_sheet(images, labels, max_panel_w=1024):
    n = len(images)
    h, w = images[0].shape[:2]
    pw = min(max_panel_w, w)
    ph = round(pw * h / w)
    lh = 28
    canvas = np.full((ph + lh, pw * n, 3), 30, dtype=np.uint8)
    pil = Image.fromarray(canvas)
    draw = ImageDraw.Draw(pil)
    for i, (img, lbl) in enumerate(zip(images, labels)):
        panel = Image.fromarray(img.astype(np.uint8)).resize((pw, ph), Image.LANCZOS)
        pil.paste(panel, (i * pw, 0))
        draw.text((i * pw + 4, ph + 4), lbl, fill=(220, 220, 220))
    return np.array(pil)

def crop_in_tile(lon_l, lon_r, lat_b, lat_t, tw, th):
    left   = round((lon_l - LON_W) / (LON_E - LON_W) * tw)
    right  = round((lon_r - LON_W) / (LON_E - LON_W) * tw)
    top    = round((LAT_N - lat_t) / (LAT_N - LAT_S) * th)
    bottom = round((LAT_N - lat_b) / (LAT_N - LAT_S) * th)
    return (max(0, left), max(0, top), min(tw, right), min(th, bottom))

# ─── Data loaders ─────────────────────────────────────────────────────────────

def load_cached_layers(tw, th):
    """Load pre-processed L0 (d5b) and L1 (21.6K matched) from prototype."""
    print("[load] cached L0 (d5b base)...")
    l0 = np.array(Image.open(os.path.join(PROTO_LAYERS, "layer0_baseline_d5b_crop.png"))
                  .convert('RGB').resize((tw, th), Image.LANCZOS))
    print("[load] cached L1 (21.6K matched)...")
    l1 = np.array(Image.open(os.path.join(PROTO_LAYERS, "layer1_visual_texture_matched.png"))
                  .convert('RGB').resize((tw, th), Image.LANCZOS))
    return l0, l1

def load_gebco_depth_field(blur_sigma_px=20):
    """
    Load GEBCO NC elevation, compute continuous soft depth influence field.

    Returns:
        depth_field: float32 (6720, 7680), [0,1], 0=shallow/land, 1=deepest ocean
        ocean_nc:    bool    (6720, 7680), True where elevation < 0
    """
    print(f"[load] GEBCO NC → soft depth field (sigma={blur_sigma_px}px)...")
    ds = nc.Dataset(GEBCO_NC)
    elev = np.flipud(np.array(ds.variables['elevation'][:]).astype(np.float32))
    ds.close()

    ocean = elev < 0
    depth_m = np.where(ocean, -elev, 0.0)

    # Non-linear normalization: sqrt boosts mid-depth structure visibility
    # At 6000m depth_norm=1.0; shallower areas get sqrt(depth/6000)
    depth_norm = np.clip(depth_m / 6000.0, 0.0, 1.0)
    depth_remap = np.sqrt(depth_norm)
    depth_remap[~ocean] = 0.0   # land = zero influence

    # Gaussian blur: removes all hard edges from 15-arc-second resolution steps
    # sigma=20 at native 7680px ≈ 7.5km smoothing
    depth_blurred = gaussian_filter(depth_remap, sigma=blur_sigma_px)

    print(f"  depth_field: min={depth_blurred.min():.3f}, max={depth_blurred.max():.3f}, "
          f"ocean coverage={100*ocean.mean():.1f}%")
    return depth_blurred.astype(np.float32), ocean

def load_gshhg_masks(tw, th):
    """
    Load GSHHG mask PNG and decode RGB encoding.
    sea=(15,30,60), land=(120,105,85), coast_edge=(255,255,240)
    """
    print("[load] GSHHG land/ocean masks...")
    img = Image.open(GSHHG_MASK).convert('RGB')
    if img.size != (tw, th):
        img = img.resize((tw, th), Image.NEAREST)
    arr = np.array(img)
    red = arr[:, :, 0]
    coast_edge = red > 200
    land  = (red > 50) & ~coast_edge
    ocean = ~land & ~coast_edge
    print(f"  land {100*land.mean():.1f}%, ocean {100*ocean.mean():.1f}%, "
          f"coast_edge {100*coast_edge.mean():.2f}%")
    return land, ocean

# ─── Depth field resize ───────────────────────────────────────────────────────

def resize_depth_field(depth_field, tw, th):
    """Resize GEBCO depth field (6720×7680 native) to tile dimensions."""
    h_nc, w_nc = depth_field.shape
    if (w_nc, h_nc) == (tw, th):
        return depth_field
    img = Image.fromarray((depth_field * 255).astype(np.uint8))
    return np.array(img.resize((tw, th), Image.LANCZOS)) / 255.0

# ─── Coastal weight field ─────────────────────────────────────────────────────

def compute_coastal_weight(land, ppkm_val, band_km):
    """
    Smooth coastal weight [0,1]: 1.0 at coastline, 0.0 at band_km away.
    Applied symmetrically on both land side and ocean side.
    Gaussian-blurred to eliminate any visible falloff boundary.

    EDT semantics:
      distance_transform_edt(arr) → distance to nearest arr==0 pixel
      land (True=land/1, False=ocean/0):
        land pixels → dist to nearest ocean (nonzero)
        ocean pixels → 0 (they are the zeros)
      ~land (True=ocean/1, False=land/0):
        ocean pixels → dist to nearest land (nonzero)
        land pixels → 0 (they are the zeros)
    Sum gives correct coast distance for every pixel.
    """
    band_px = band_km * ppkm_val

    # land pixels: distance to nearest ocean; ocean pixels: 0
    land_side  = distance_transform_edt(land.astype(np.uint8)).astype(np.float32)
    # ocean pixels: distance to nearest land; land pixels: 0
    ocean_side = distance_transform_edt((~land).astype(np.uint8)).astype(np.float32)

    # Sum: exactly one term is nonzero per pixel → correct coast distance everywhere
    dist_from_coast = land_side + ocean_side

    # Squared linear falloff: gentler than hard cutoff
    weight = np.maximum(0.0, 1.0 - dist_from_coast / band_px) ** 2

    # Gaussian blur to smooth the outer boundary of the band
    blur_sigma = max(2.0, band_px * 0.15)
    weight = gaussian_filter(weight, sigma=blur_sigma)

    # Renormalize so max stays ~1.0
    wmax = weight.max()
    if wmax > 0:
        weight = np.clip(weight / wmax, 0.0, 1.0)

    return weight.astype(np.float32)

# ─── Composite ────────────────────────────────────────────────────────────────

def composite_soft(base, layer1, depth_r, land, ocean,
                   visual_blend, bathy_blend, coast_weight, coast_strength):
    """
    Soft composite — three components:

    1. L1 visual texture: global blend at visual_blend (both land + ocean)
    2. GEBCO depth: continuous brightness darkening on ocean pixels only
       - max ~20% darkening at deepest (6000m+) when bathy_blend=0.25
       - subtle blue tint at depth (+10 max at blend=0.25)
    3. GSHHG coastal: extra L1 blend within coast band (both sides)
       - brings natural satellite coastal/bay colors to foreground
       - no unsharp mask, no edge lines
    """
    result = base.astype(np.float32)
    l1f    = layer1.astype(np.float32)

    # Step 1: global L1 visual texture blend
    if visual_blend > 0:
        result = result * (1 - visual_blend) + l1f * visual_blend

    # Step 2: soft GEBCO depth darkening on ocean pixels
    if bathy_blend > 0:
        # dark_factor: 1.0 at surface, ~0.80 at deepest (bathy_blend=0.25)
        dark_factor = 1.0 - depth_r * bathy_blend * 0.80
        dark_factor = np.clip(dark_factor, 0.65, 1.0)

        result[ocean] *= dark_factor[ocean, np.newaxis]

        # Subtle blue shift at depth (max +10 at bathy_blend=0.25, depth=1.0)
        blue_add = depth_r * bathy_blend * 40.0
        result[ocean, 2] = np.clip(result[ocean, 2] + blue_add[ocean], 0, 255)

    # Step 3: coastal extra L1 blend (near coast: more satellite texture)
    if coast_strength > 0 and coast_weight is not None:
        extra = (l1f - result) * (coast_weight * coast_strength)[:, :, np.newaxis]
        result = result + extra

    return np.clip(result, 0, 255).astype(np.uint8)

# ─── Crop comparison ──────────────────────────────────────────────────────────

CROP_REGIONS = [
    ("retune_crop_tokyo_bay",        "Tokyo Bay",           138.5, 141.0, 34.5, 36.5),
    ("retune_crop_osaka_seto",       "Osaka/Seto",          132.0, 137.0, 33.0, 36.0),
    ("retune_crop_ryukyu",           "Ryukyu Islands",      123.0, 131.0, 24.0, 28.0),
    ("retune_crop_east_china_shelf", "East China Shelf",    119.0, 128.0, 25.0, 32.0),
    ("retune_crop_japan_trench",     "Japan Trench",        141.0, 149.0, 33.0, 40.0),
]

def make_crops(before, after, tw, th):
    """Generate before/after crop comparisons for 5 key regions."""
    for name, label, lon_l, lon_r, lat_b, lat_t in CROP_REGIONS:
        box = crop_in_tile(lon_l, lon_r, lat_b, lat_t, tw, th)
        bw = box[2] - box[0]
        bh = box[3] - box[1]
        if bw < 4 or bh < 4:
            print(f"  [crop] {name}: too small ({bw}×{bh}), skipping")
            continue
        panels = [before[box[1]:box[3], box[0]:box[2]],
                  after[box[1]:box[3], box[0]:box[2]]]
        sheet = make_contact_sheet(panels, ["v2_before", "retune_after"],
                                   max_panel_w=min(1280, bw))
        save_png(sheet, os.path.join(OUT_DIR, f"{name}.png"))
        print(f"  [crop] {name}: {bw}×{bh}px per panel")

# ─── README ───────────────────────────────────────────────────────────────────

def write_readme(params):
    text = f"""# Japan v2 Visual Retuning Pass — Results

**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
**Region:** 118–150°E, 22–50°N
**Generator:** `scripts/geo/rdl_retuning.py`
**Status:** Retuning pass only — no new data sources, no formal integration

---

## Changes vs v2 Prototype

| Component | v2 Prototype | Retuning |
|---|---|---|
| GEBCO approach | 5-level hard palette at blend=0.35 | Continuous depth darkening, blurred, monochrome |
| Coastal clarity | Unsharp mask (radius=1.5, amount=80%) | Extra L1 texture blend, feathered both sides |
| Land visual blend | 0.30 | {params['visual_blend']} |
| GEBCO blend | 0.35 | {params['bathy_blend']} (0.15/0.20/0.25 variants) |
| GSHHG zone | 10km unsharp zone | {params['coast_band_km']}km soft blend band |
| Coast strength | 0.15 (sharpening) | {params['coast_strength']} (texture blend boost) |

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
"""
    path = os.path.join(OUT_DIR, "README_RETUNING.md")
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(path, 'w') as f:
        f.write(text)
    print(f"  wrote: previews/rdl_v2_japan_visual_retuning/README_RETUNING.md")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()
    print("=" * 60)
    print("RDL Visual Retuning Pass")
    print(f"Output: previews/rdl_v2_japan_visual_retuning/")
    print("=" * 60)

    os.makedirs(OUT_DIR, exist_ok=True)

    # ── Load cached layers (4096 native) ────────────────────────────────────
    print("\n[Phase 1] Loading cached layers...")
    l0_4, l1_4 = load_cached_layers(TW4, TH4)
    print(f"  L0: {l0_4.shape}, L1: {l1_4.shape}")

    # ── Load and process GEBCO elevation ────────────────────────────────────
    print("\n[Phase 2] GEBCO depth field...")
    depth_field_nc, ocean_nc = load_gebco_depth_field(blur_sigma_px=20)

    # Resize depth field to 4096 tile resolution
    depth_r4 = resize_depth_field(depth_field_nc, TW4, TH4)
    print(f"  depth_r4: {depth_r4.shape}, "
          f"range [{depth_r4.min():.3f}, {depth_r4.max():.3f}]")

    # ── Load GSHHG masks ────────────────────────────────────────────────────
    print("\n[Phase 3] GSHHG land/ocean masks...")
    land4, ocean4 = load_gshhg_masks(TW4, TH4)

    # ── Compute coastal weight fields ────────────────────────────────────────
    print("\n[Phase 4] Coastal weight fields...")
    coast_w_10 = compute_coastal_weight(land4, PPK4, 10)
    print(f"  10km band: {100*(coast_w_10 > 0.1).mean():.1f}% pixels affected")
    coast_w_20 = compute_coastal_weight(land4, PPK4, 20)
    print(f"  20km band: {100*(coast_w_20 > 0.1).mean():.1f}% pixels affected")
    coast_w_30 = compute_coastal_weight(land4, PPK4, 30)
    print(f"  30km band: {100*(coast_w_30 > 0.1).mean():.1f}% pixels affected")

    # ── Bathy variants (coast off) ────────────────────────────────────────
    print("\n[Phase 5] Bathy variants (coast=off, visual=0.15)...")
    for blend in [0.15, 0.20, 0.25]:
        name = f"retune_bathy_soft_{int(blend*100):03d}"
        out = composite_soft(l0_4, l1_4, depth_r4, land4, ocean4,
                             visual_blend=0.15, bathy_blend=blend,
                             coast_weight=None, coast_strength=0)
        save_png(out, os.path.join(OUT_DIR, f"{name}.png"))

    # ── Coast variants (bathy=0.20, vary band) ────────────────────────────
    print("\n[Phase 6] Coast variants (bathy=0.20, strength=0.08)...")
    for band_km, cw in [(10, coast_w_10), (20, coast_w_20), (30, coast_w_30)]:
        name = f"retune_coast_soft_{band_km:03d}km"
        out = composite_soft(l0_4, l1_4, depth_r4, land4, ocean4,
                             visual_blend=0.15, bathy_blend=0.20,
                             coast_weight=cw, coast_strength=0.08)
        save_png(out, os.path.join(OUT_DIR, f"{name}.png"))

    # ── Final combined — recommended params ───────────────────────────────
    print("\n[Phase 7] Final combined (bathy=0.20, coast=20km, str=0.08, vis=0.15)...")
    final_4 = composite_soft(l0_4, l1_4, depth_r4, land4, ocean4,
                             visual_blend=0.15, bathy_blend=0.20,
                             coast_weight=coast_w_20, coast_strength=0.08)
    save_png(final_4, os.path.join(OUT_DIR, "retune_final_soft_4096.png"))

    # Downscale to 2048
    final_2 = np.array(Image.fromarray(final_4).resize((TW2, TH2), Image.LANCZOS))
    save_png(final_2, os.path.join(OUT_DIR, "retune_final_soft_2048.png"))

    # ── Before / after contact sheet ─────────────────────────────────────
    print("\n[Phase 8] Before/after contact sheet...")
    before_path = os.path.join(PROTO_TILES, "v2_gebco_gshhg_tile_4096.png")
    before_4 = np.array(Image.open(before_path).convert('RGB'))
    sheet = make_contact_sheet([before_4, final_4],
                               ["v2_before (5-level palette, unsharp coast)",
                                "retune_after (soft gradient, texture blend)"],
                               max_panel_w=2048)
    save_png(sheet, os.path.join(OUT_DIR, "retune_before_after_contact_sheet.png"))

    # ── Key region crops ──────────────────────────────────────────────────
    print("\n[Phase 9] Key region crops...")
    make_crops(before_4, final_4, TW4, TH4)

    # ── README ─────────────────────────────────────────────────────────────
    print("\n[Phase 10] Writing README_RETUNING.md...")
    write_readme({
        "visual_blend": 0.15,
        "bathy_blend": 0.20,
        "coast_band_km": 20,
        "coast_strength": 0.08,
    })

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"Retuning pass complete in {elapsed:.1f}s")
    print(f"Output: previews/rdl_v2_japan_visual_retuning/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
