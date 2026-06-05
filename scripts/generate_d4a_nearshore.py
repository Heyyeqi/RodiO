#!/usr/bin/env python3
"""
D4a: Conservative Nearshore Gradient Repair
Stage A-3 — Validate if D3 nearshore uniformity can be improved via conservative local processing.
"""

import numpy as np
from PIL import Image, ImageFilter
import os
import json
from datetime import datetime

BASE = os.path.expanduser("~/Projects/RodiO/pwa/assets/source/bmng_staging")
D3_PATH   = os.path.join(BASE, "bmng_processed_8192x4096_natural_d3.jpg")
REF_PATH  = os.path.join(BASE, "bmng_processed_8192x4096.jpg")
OUT_PATH  = os.path.join(BASE, "bmng_processed_8192x4096_natural_d4a_nearshore.jpg")
PREV_DIR  = os.path.join(BASE, "d4a_previews")
os.makedirs(PREV_DIR, exist_ok=True)

print(f"[{datetime.now().strftime('%H:%M:%S')}] Loading images...")
d3_img  = Image.open(D3_PATH).convert("RGB")
ref_img = Image.open(REF_PATH).convert("RGB")

W, H = d3_img.size
print(f"  Size: {W}x{H}")

d3  = np.array(d3_img,  dtype=np.float32)
ref = np.array(ref_img, dtype=np.float32)

# ── Helpers ──────────────────────────────────────────────────────────────────

def soft_mask(arr, radius):
    """Blur a float mask [0,1] with Gaussian-like PIL filter."""
    img = Image.fromarray((arr * 255).clip(0, 255).astype(np.uint8), mode="L")
    img = img.filter(ImageFilter.GaussianBlur(radius=radius))
    return np.array(img, dtype=np.float32) / 255.0

def rgb_to_hsv(rgb):
    r, g, b = rgb[...,0]/255.0, rgb[...,1]/255.0, rgb[...,2]/255.0
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    delta = mx - mn
    h = np.zeros_like(mx)
    s = np.where(mx > 0, delta / mx, 0.0)
    v = mx
    mask_r = (mx == r) & (delta > 0)
    mask_g = (mx == g) & (delta > 0)
    mask_b = (mx == b) & (delta > 0)
    h[mask_r] = ((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6
    h[mask_g] = (b[mask_g] - r[mask_g]) / delta[mask_g] + 2
    h[mask_b] = (r[mask_b] - g[mask_b]) / delta[mask_b] + 4
    h = h / 6.0
    return h, s, v

print(f"[{datetime.now().strftime('%H:%M:%S')}] Computing HSV...")
R, G, B = d3[...,0], d3[...,1], d3[...,2]
H_ch, S_ch, V_ch = rgb_to_hsv(d3)

# ── Mask 1: ocean_base_relaxed ───────────────────────────────────────────────
print(f"[{datetime.now().strftime('%H:%M:%S')}] Building ocean_base_relaxed mask...")

snow_mask    = (R > 210) & (G > 210) & (B > 210) & (S_ch < 0.12)
# Vegetation: high G relative to R and B, not too bright
veg_mask     = (G > R + 5) & (G > B + 3) & (V_ch < 0.72) & (~snow_mask)
# High-saturation desert / bare: high R, not blue-dominant
desert_mask  = (R > G + 10) & (R > B + 10) & (V_ch > 0.45) & (~snow_mask)

ocean_hard = (
    (B > 40) &
    ((B.astype(np.int16) - R) > 8) &
    (V_ch < 0.78) &
    (~snow_mask) &
    (~veg_mask) &
    (~desert_mask)
)
ocean_base_relaxed = ocean_hard.astype(np.float32)
ocean_base_relaxed = soft_mask(ocean_base_relaxed, radius=2)
ocean_base_relaxed = (ocean_base_relaxed > 0.5).astype(np.float32)

# ── Mask 2: land_hard (complement of ocean for dilation) ────────────────────
land_hard = (~ocean_hard) & (~snow_mask)

# ── Mask 3: nearshore_100km (~20px at 8192 wide) ───────────────────────────
print(f"[{datetime.now().strftime('%H:%M:%S')}] Building nearshore masks...")

land_hard_img = Image.fromarray(land_hard.astype(np.uint8) * 255, mode="L")
land_dil_20   = land_hard_img.filter(ImageFilter.MaxFilter(size=41))  # ~20px radius
land_dil_35   = land_hard_img.filter(ImageFilter.MaxFilter(size=71))  # ~35px radius

ld20 = np.array(land_dil_20, dtype=np.float32) / 255.0
ld35 = np.array(land_dil_35, dtype=np.float32) / 255.0

nearshore_100_raw = ocean_base_relaxed * (ld20 > 0.5).astype(np.float32)
nearshore_170_raw = ocean_base_relaxed * (ld35 > 0.5).astype(np.float32)

nearshore_100 = soft_mask(nearshore_100_raw, radius=10)
nearshore_170 = soft_mask(nearshore_170_raw, radius=16)

# ── Mask 4: shelf ────────────────────────────────────────────────────────────
shelf_raw = ocean_base_relaxed * (V_ch > 0.48).astype(np.float32) * (~snow_mask).astype(np.float32)
shelf     = soft_mask(shelf_raw, radius=14)

# ── Mask 5: island shelf ─────────────────────────────────────────────────────
# Higher V, inside nearshore_170, G relatively high vs pure blue
island_raw = (
    ocean_base_relaxed *
    (nearshore_170_raw > 0.3).astype(np.float32) *
    (V_ch > 0.50).astype(np.float32) *
    ((G / (B + 1)) > 0.70).astype(np.float32)
)
island_shelf = soft_mask(island_raw, radius=12)

# ── Mask 6: polar nearshore ──────────────────────────────────────────────────
# High latitude (top/bottom ~25% of image) near ocean
polar_lat_mask = np.zeros((H, W), dtype=np.float32)
polar_lat_mask[:int(H * 0.25), :] = 1.0
polar_lat_mask[int(H * 0.75):, :] = 1.0
polar_raw = ocean_base_relaxed * polar_lat_mask * (nearshore_170_raw > 0.2).astype(np.float32)
polar_nearshore = soft_mask(polar_raw, radius=16)

# ── Detail layer from reference BMNG ────────────────────────────────────────
print(f"[{datetime.now().strftime('%H:%M:%S')}] Computing detail layer...")

# detail = luminance difference (ref - d3), signed, kept small
ref_lum = 0.299*ref[...,0] + 0.587*ref[...,1] + 0.114*ref[...,2]
d3_lum  = 0.299*d3[...,0]  + 0.587*d3[...,1]  + 0.114*d3[...,2]
detail_lum = ref_lum - d3_lum  # signed float

# Compute result starting from D3
result = d3.copy()

# ── Apply zone-by-zone ────────────────────────────────────────────────────────
print(f"[{datetime.now().strftime('%H:%M:%S')}] Applying zone corrections...")

def apply_zone(result, mask, detail_strength, sat_mult, bright_add_pct, dR, dG, B_mult):
    """Apply correction to result array in-place, weighted by mask."""
    m = mask[..., np.newaxis]  # (H,W,1)
    base = result.copy()

    # Detail from luminance
    if detail_strength > 0:
        dl = np.clip(detail_lum * detail_strength, -8, 8)
        dl3 = np.stack([dl, dl, dl], axis=-1)
        base = base + dl3

    # Channel adjustments
    base[...,0] = base[...,0] + dR
    base[...,1] = base[...,1] + dG
    base[...,2] = base[...,2] * B_mult

    # Brightness
    if bright_add_pct != 0:
        base = base * (1.0 + bright_add_pct / 100.0)

    # Saturation: operate in HSV space approximately
    if abs(sat_mult - 1.0) > 0.0001:
        lum = 0.299*base[...,0] + 0.587*base[...,1] + 0.114*base[...,2]
        lum3 = np.stack([lum,lum,lum], axis=-1)
        base = lum3 + (base - lum3) * sat_mult

    base = np.clip(base, 0, 255)

    result[:] = (base * m + result * (1 - m)).clip(0, 255)

# Zone A: Yellow Sea / East China Sea / North Sea / Sea of Okhotsk
# lat 20-65N (rows), relevant longitudes — use a broad nearshore mask in those areas
apply_zone(result, nearshore_100, detail_strength=0.12, sat_mult=0.995,
           bright_add_pct=0.5, dR=1, dG=1, B_mult=0.998)
apply_zone(result, nearshore_170, detail_strength=0.07, sat_mult=0.997,
           bright_add_pct=0.3, dR=0, dG=0, B_mult=0.999)

# Zone B: Shelf detail (Taiwan Strait / South China Sea / shelf areas)
apply_zone(result, shelf, detail_strength=0.12, sat_mult=1.000,
           bright_add_pct=0.8, dR=0, dG=1, B_mult=1.000)

# Zone C: Island shelf (Philippines / Indonesia / Caribbean / Australia)
apply_zone(result, island_shelf, detail_strength=0.12, sat_mult=0.995,
           bright_add_pct=0.5, dR=0, dG=1, B_mult=0.998)

# Zone G: Polar nearshore
apply_zone(result, polar_nearshore, detail_strength=0.07, sat_mult=0.995,
           bright_add_pct=0.3, dR=0, dG=1, B_mult=0.998)

# ── Safety rails ──────────────────────────────────────────────────────────────
# 1. Protect snow pixels: restore original values
snow_m = snow_mask[..., np.newaxis].astype(np.float32)
result  = (d3 * snow_m + result * (1 - snow_m)).clip(0, 255)

# 2. Protect land pixels: restore original values
land_m = land_hard[..., np.newaxis].astype(np.float32)
result  = (d3 * land_m + result * (1 - land_m)).clip(0, 255)

# 3. Clamp high-saturation ocean pixels to not exceed D3 by more than 3%
H_ch2, S_ch2, V_ch2 = rgb_to_hsv(result.astype(np.float32))
high_sat_d3   = S_ch > 0.55
high_sat_new  = S_ch2 > S_ch * 1.03
over_sat_mask = (high_sat_d3 | high_sat_new) & ocean_hard
over_sat_m    = over_sat_mask[..., np.newaxis].astype(np.float32)
result = (d3 * over_sat_m + result * (1 - over_sat_m)).clip(0, 255)

result = result.astype(np.uint8)

# ── Save output ───────────────────────────────────────────────────────────────
print(f"[{datetime.now().strftime('%H:%M:%S')}] Saving D4a...")
out_img = Image.fromarray(result, mode="RGB")
out_img.save(OUT_PATH, "JPEG", quality=95, subsampling=0)
print(f"  Saved: {OUT_PATH}")

# ── Validation metrics ────────────────────────────────────────────────────────
print(f"[{datetime.now().strftime('%H:%M:%S')}] Computing validation metrics...")

# Geographic zones: (name, row_start, row_end, col_start, col_end)
# Map: 8192 wide = 360°, 4096 tall = 180°
# row 0 = 90°N, row 4096 = 90°S
# col 0 = 180°W (or 0° depending on projection) — BMNG uses 0°=col 4096
# lon_col = (lon + 180) / 360 * 8192

def lonlat_to_rc(lon, lat):
    col = int((lon + 180) / 360 * W)
    row = int((90 - lat) / 180 * H)
    return max(0, min(H-1, row)), max(0, min(W-1, col))

def zone_bbox(lon_w, lon_e, lat_s, lat_n, pad=0):
    r1, c1 = lonlat_to_rc(lon_w, lat_n)
    r2, c2 = lonlat_to_rc(lon_e, lat_s)
    r1 = max(0, r1 - pad); r2 = min(H, r2 + pad)
    c1 = max(0, c1 - pad); c2 = min(W, c2 + pad)
    return r1, r2, c1, c2

zones = [
    ("Yellow Sea",        119, 127, 31, 38),
    ("East China Sea",    119, 128, 24, 32),
    ("Taiwan Strait",     117, 123, 22, 26),
    ("South China Sea N", 108, 122, 16, 24),
    ("South China Sea C", 109, 120, 7,  16),
    ("Philippines",       116, 128, 5,  18),
    ("Indonesia",         105, 140, -8,  5),
    ("Caribbean",         -85, -60, 10, 24),
    ("Bahamas",           -80, -72, 22, 28),
    ("Gulf of Mexico",    -97, -80, 18, 30),
    ("Australia North",   127, 140, -20, -10),
    ("Great Barrier Reef",145, 154, -24, -15),
    ("Persian Gulf",       48,  57,  23, 30),
    ("Red Sea",            32,  44,  12, 28),
    ("North Sea",          -4,  10,  51, 60),
    ("Mediterranean",       0,  36,  30, 46),
    ("Bering Sea",        165, 200,  53, 65),
    ("Sea of Okhotsk",    140, 162,  47, 60),
    ("Southern Ocean",    -180, 180, -60, -50),
    ("Arctic fringe",     -180, 180,  70,  80),
]

metrics = {}
print(f"\n{'Zone':<25} {'R':>5} {'G':>5} {'B':>5} {'B/G':>5} {'B_std':>6} {'Sat':>5} {'V':>5} {'HiSat%':>7} | D3→D4a dB_std")
print("-" * 95)

for (name, lon_w, lon_e, lat_s, lat_n) in zones:
    r1, r2, c1, c2 = zone_bbox(lon_w, lon_e, lat_s, lat_n)
    if lon_w == -180 and lon_e == 180:
        # Full latitude band
        patch_d3  = d3[r1:r2, :, :]
        patch_new = result[r1:r2, :, :].astype(np.float32)
    else:
        patch_d3  = d3[r1:r2, c1:c2, :]
        patch_new = result[r1:r2, c1:c2, :].astype(np.float32)

    # Restrict to ocean pixels in patch
    if lon_w == -180 and lon_e == 180:
        om = ocean_base_relaxed[r1:r2, :]
    else:
        om = ocean_base_relaxed[r1:r2, c1:c2]

    if om.sum() < 100:
        continue

    def zone_stats(arr, mask):
        mr = arr[...,0][mask > 0.5]
        mg = arr[...,1][mask > 0.5]
        mb = arr[...,2][mask > 0.5]
        if len(mr) == 0:
            return None
        Rm, Gm, Bm = mr.mean(), mg.mean(), mb.mean()
        Bstd = mb.std()
        BG = Bm / (Gm + 1e-6)
        # approximate saturation
        mx = np.maximum(np.maximum(mr, mg), mb)
        mn = np.minimum(np.minimum(mr, mg), mb)
        sat = np.where(mx > 0, (mx - mn) / mx, 0).mean()
        V   = (mx / 255.0).mean()
        hi_sat = (sat > 0.35).mean() if hasattr(sat, '__len__') else float(sat > 0.35)
        # per-pixel sat
        per_sat = np.where(mx > 0, (mx - mn) / mx, 0)
        hi_sat_pct = (per_sat > 0.35).mean() * 100
        return Rm, Gm, Bm, BG, Bstd, sat, V, hi_sat_pct

    s_d3  = zone_stats(patch_d3,  om)
    s_new = zone_stats(patch_new, om)
    if s_d3 is None or s_new is None:
        continue

    Rm,Gm,Bm,BG,Bstd,sat,V,hsp = s_new
    dBstd = s_new[4] - s_d3[4]

    metrics[name] = {
        "d3":  {"R":round(s_d3[0],1),"G":round(s_d3[1],1),"B":round(s_d3[2],1),
                 "BG":round(s_d3[3],3),"B_std":round(s_d3[4],2),"sat":round(s_d3[5],4),
                 "V":round(s_d3[6],4),"hi_sat_pct":round(s_d3[7],2)},
        "d4a": {"R":round(Rm,1),"G":round(Gm,1),"B":round(Bm,1),
                 "BG":round(BG,3),"B_std":round(Bstd,2),"sat":round(sat,4),
                 "V":round(V,4),"hi_sat_pct":round(hsp,2)},
        "delta_Bstd": round(dBstd, 3),
        "delta_Bstd_pct": round(dBstd / (s_d3[4] + 1e-6) * 100, 1),
    }
    print(f"{name:<25} {Rm:>5.1f} {Gm:>5.1f} {Bm:>5.1f} {BG:>5.3f} {Bstd:>6.2f} {sat:>5.3f} {V:>5.3f} {hsp:>7.2f}% | {dBstd:+.3f} ({metrics[name]['delta_Bstd_pct']:+.1f}%)")

# Save JSON report
report_path = os.path.join(PREV_DIR, "d4a_metrics.json")
with open(report_path, "w") as f:
    json.dump(metrics, f, indent=2, ensure_ascii=False)
print(f"\nMetrics saved: {report_path}")

# ── Generate preview images ───────────────────────────────────────────────────
print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Generating preview images...")

PREV_W = 2048
PREV_H = 1024

d3_prev  = d3_img.resize((PREV_W, PREV_H), Image.LANCZOS)
d4a_prev = out_img.resize((PREV_W, PREV_H), Image.LANCZOS)

# Global side-by-side
comp_global = Image.new("RGB", (PREV_W * 2, PREV_H + 20), (20, 20, 20))
comp_global.paste(d3_prev,  (0, 20))
comp_global.paste(d4a_prev, (PREV_W, 20))
comp_global.save(os.path.join(PREV_DIR, "global_compare_d3_vs_d4a.jpg"), quality=88)

# Regional crops
regional_crops = [
    ("yellow_east_china_sea",  119, 128, 22, 40),
    ("taiwan_strait",          115, 125, 20, 28),
    ("south_china_sea",        105, 125,  5, 25),
    ("philippines",            115, 132,  4, 20),
    ("indonesia",              100, 145, -12,  8),
    ("caribbean_bahamas",      -88, -60,  10, 28),
    ("australia_gbr",          120, 158, -26, -8),
    ("persian_gulf_red_sea",    30,  60,  10, 32),
    ("north_sea",               -8,  12,  49, 62),
    ("bering_sea",             160, 200,  50, 67),
    ("southern_ocean",         -60,  60, -65, -45),
]

for (tag, lon_w, lon_e, lat_s, lat_n) in regional_crops:
    r1, r2, c1, c2 = zone_bbox(lon_w, lon_e, lat_s, lat_n)
    if r2 <= r1 or c2 <= c1:
        continue
    crop_d3  = d3_img.crop((c1, r1, c2, r2))
    crop_d4a = out_img.crop((c1, r1, c2, r2))
    cw = c2 - c1
    ch = r2 - r1
    comp = Image.new("RGB", (cw * 2, ch), (20, 20, 20))
    comp.paste(crop_d3,  (0, 0))
    comp.paste(crop_d4a, (cw, 0))
    comp.save(os.path.join(PREV_DIR, f"crop_{tag}.jpg"), quality=90)
    print(f"  Saved crop: {tag} ({cw}x{ch} px each side)")

# ── Mask coverage report ──────────────────────────────────────────────────────
total_px = W * H
print(f"\n── Mask coverage ──")
print(f"  ocean_base_relaxed : {ocean_base_relaxed.sum()/total_px*100:.1f}% of image")
print(f"  nearshore_100km    : {(nearshore_100 > 0.1).sum()/total_px*100:.1f}%")
print(f"  nearshore_170km    : {(nearshore_170 > 0.1).sum()/total_px*100:.1f}%")
print(f"  shelf              : {(shelf > 0.1).sum()/total_px*100:.1f}%")
print(f"  island_shelf       : {(island_shelf > 0.1).sum()/total_px*100:.1f}%")
print(f"  polar_nearshore    : {(polar_nearshore > 0.1).sum()/total_px*100:.1f}%")
print(f"  snow_protected     : {snow_mask.sum()/total_px*100:.1f}%")
print(f"  land_protected     : {land_hard.sum()/total_px*100:.1f}%")

print(f"\n[{datetime.now().strftime('%H:%M:%S')}] D4a complete.")
print(f"Output : {OUT_PATH}")
print(f"Previews: {PREV_DIR}/")
print("\nReminder: earth3d.js NOT modified. dayTexture NOT replaced. No commit made.")
